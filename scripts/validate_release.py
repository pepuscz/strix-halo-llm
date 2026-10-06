#!/usr/bin/env python3
"""Validate immutable release pins and the public-data boundary."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml


HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_ARTIFACT_HOSTS = {"github.com", "huggingface.co", "archive.ubuntu.com", "repo.amd.com"}
TEXT_SUFFIXES = {"", ".cfg", ".in", ".j2", ".json", ".md", ".patch", ".py", ".sh", ".txt", ".yml", ".yaml"}
SYSTEMS = {
    "strata-qwen-q4xl": ("Strata HIP UD-Q4_K_XL", "strata"),
    "vulkan-iq3xxs": ("Strix Halo llama.cpp Vulkan IQ3_XXS", "vulkan"),
    "rocm-rocmfpx": ("Lucebox ROCm ROCmFPX", "rocm"),
}
FORBIDDEN_PUBLIC_PATTERNS = {
    "macOS home path": re.compile(r"/Users/[^/\s]+/"),
    "private IPv4 address": re.compile(r"(?<![0-9])(?:10|192\.168)\.(?:[0-9]{1,3}\.){2}[0-9]{1,3}(?![0-9])"),
    "SSH private key": re.compile(r"BEGIN (?:OPENSSH|RSA|EC|DSA) PRIVATE KEY"),
    "Ansible inline password": re.compile(r"ansible_(?:password|become_pass|ssh_pass)\s*:", re.I),
    "casual system label": re.compile(r"\bnathan\b", re.I),
    "competition-log label": re.compile(r"\b(?:winner|challenger)\b", re.I),
}


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def require_sha(value: object, label: str, pattern: re.Pattern[str] = HEX64) -> None:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        fail(f"{label} has an invalid digest")


def require_url(value: object, label: str) -> None:
    parsed = urlparse(str(value))
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_ARTIFACT_HOSTS:
        fail(f"{label} is not an allowed HTTPS publisher URL: {value}")


def validate_manifest(path: Path, root: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data.get("strix_release_schema") != 1:
        fail("unsupported strix_release_schema")

    system = data.get("strix_system", {})
    expected = SYSTEMS.get(system.get("id"))
    if expected != (system.get("name"), system.get("engine")):
        fail("non-canonical strix_system identity")

    service = data["strix_service"]
    required_context = {"vulkan": 524288, "rocm": 131072, "strata": 262144}[system["engine"]]
    if service["context"] != required_context:
        fail(f"{system['engine']} release must allocate exactly {required_context} tokens")
    if service["minimum_effective_non_cma_kib"] < 2 * 1024 * 1024:
        fail("effective non-CMA memory floor is below 2 GiB")
    envelope = ("123G", "125G") if system["engine"] == "strata" else ("118G", "120G")
    if (service["memory_high"], service["memory_max"]) != envelope:
        fail("cgroup memory envelope drifted")
    if service["memory_swap_max"] != 0:
        fail("swap must remain disabled")
    if system["engine"] == "vulkan" and service.get("sampling") != {
        "temperature": 1.0,
        "top_p": 0.95,
        "top_k": 0,
        "min_p": 0.0,
    }:
        fail("Vulkan server sampling defaults drifted from the qualified profile")

    target = data["strix_target"]
    files = target["files"]
    if not files or sum(item["size"] for item in files) != target["total_size"]:
        fail("target file total does not match declared total_size")
    for index, artifact in enumerate(files, start=1):
        require_sha(artifact["sha256"], f"target file {index}")
    if system["engine"] != "strata":
        require_sha(data["strix_draft"]["sha256"], "draft")
    require_sha(data["strix_ryzenadj"]["tested_binary_sha256"], "RyzenAdj binary")
    require_sha(data["strix_runtime"]["source_commit"], "runtime source commit", HEX40)
    require_sha(data["strix_runtime"]["server_sha256"], "runtime server")

    if system["engine"] == "vulkan":
        if len(files) != 4:
            fail("Strix Halo llama.cpp Vulkan IQ3_XXS requires four target files")
        runtime = data["strix_runtime"]
        require_url(runtime["archive_url"], "runtime archive_url")
        require_url(runtime["manifest_url"], "runtime manifest_url")
        if runtime["manifest_name"] != "MANIFEST.txt" or runtime["manifest_size"] <= 0:
            fail("runtime manifest metadata is invalid")
        require_url(data["strix_vulkan_loader"]["url"], "Vulkan loader URL")
        for key in ("archive_sha256", "manifest_sha256", "launcher_sha256"):
            require_sha(runtime[key], f"runtime {key}")
        require_sha(runtime["vulkan_backend_sha256"], "runtime Vulkan backend")
        if "patch" in runtime or "overlay_name" in runtime:
            fail("the official v0.7.0 Vulkan runtime must not use a local overlay")
        vulkan_environment = data.get("strix_vulkan_environment", {})
        if "GGML_VK_LIGHTNING_INDEXER_SMALL_CM" in vulkan_environment:
            fail("the official v0.7.0 indexer routing must not be overridden")
        if vulkan_environment.get("GGML_VK_MMID_M128") != "1":
            fail("the qualified M128 Vulkan tuning is not enabled")
        for key in ("sha256", "library_sha256"):
            require_sha(data["strix_vulkan_loader"][key], f"Vulkan loader {key}")
        governor = data["strix_fan"].get("governor", {})
        if governor != {
            "enabled": True,
            "implementation_sha256": '3747bd714c1614c937bc10b0b8694a59f5e44674e7f73283781b1ca4e36ae4ef',
            "interval_seconds": 1,
            "idle_seconds": 300,
            "busy_threshold_pct": 5,
            "fail_safe_state": "max",
        }:
            fail("demand-based fan governor drifted from the qualified policy")
        governor_path = root / "ansible/roles/fan/files/strix-fan-governor"
        require_sha(governor["implementation_sha256"], "fan governor")
        if hashlib.sha256(governor_path.read_bytes()).hexdigest() != governor["implementation_sha256"]:
            fail("fan governor implementation hash drifted")
    elif system["engine"] == "strata":
        if len(files) != 4 or service["parallel_slots"] != 4:
            fail("Strata requires four target shards and four sessions")
        runtime, native = data["strix_runtime"], data["strix_strata"]
        require_url(runtime["repository"], "Strata repository")
        require_sha(runtime["source_tree"], "Strata source tree", HEX40)
        require_sha(runtime["tag_object"], "Strata tag object", HEX40)
        if runtime["tag_object"] != runtime["source_commit"] or runtime["tag_object_type"] != "commit":
            fail("the qualified lightweight tag must identify its exact commit")
        require_sha(runtime["ggml_commit"], "ggml source", HEX40)
        require_sha(runtime["ggml_archive_sha256"], "ggml archive")
        require_url(runtime["ggml_archive_url"], "ggml archive")
        require_url(native["sdk_url"], "Strata ROCm SDK")
        require_sha(native["sdk_sha256"], "Strata ROCm SDK")
        for key in ("requirements_sha256", "pack_dense_sha256", "mtp_experts_sha256", "mtp_dense_sha256", "draft_vocab_sha256"):
            require_sha(native[key], key)
        lock = root / "ansible/roles/strata_runtime/files/requirements.lock"
        if hashlib.sha256(lock.read_bytes()).hexdigest() != native["requirements_sha256"]:
            fail("Strata Python lock digest drifted")
        tensors = root / "ansible/roles/strata_runtime/files" / data["strix_draft"]["tensor_manifest"]
        if hashlib.sha256(tensors.read_bytes()).hexdigest() != data["strix_draft"]["tensor_manifest_sha256"]:
            fail("MTP tensor manifest drifted")
        tensor_data = json.loads(tensors.read_text())
        if len(tensor_data) != 31:
            fail("MTP requires the 31 pinned tensors")
        for tensor in tensor_data:
            require_sha(tensor["sha256"], tensor["name"])
        cfg = native["server"]
        args = cfg["args"]
        expected = {"--prefill": "8192", "--expert-cache": "24576", "--kv": "int8", "--pcie-frac": "0", "--adapt-every": "1000000", "--max-context": "262144", "--mtp-q4": "all", "--spec": "4"}
        if cfg["parallel"] != 4 or cfg["env"]["STRATA_QFUSE"] != "0" or "--batch-mtp" in args or "--no-prefill-borrow" not in args:
            fail("Strata serving configuration differs from the qualified recipe")
        for flag, value in expected.items():
            if flag not in args or args[args.index(flag) + 1] != value:
                fail("qualified Strata option drifted: " + flag)
        for digest in native["tokenizer_sha256"].values():
            require_sha(digest, "tokenizer")
        if service["minimum_effective_non_cma_kib"] != 8 * 1024 * 1024:
            fail("Strata requires the qualified 8 GiB non-CMA floor")
        quality = data["strix_qualification"]["answer_quality"]
        if quality["total"] != 30 or quality["quality_checkpoint_max_prompt_tokens"] >= 8192:
            fail("Strata short-quality cap compatibility is invalid")
    else:
        if len(files) != 1:
            fail("Lucebox ROCm ROCmFPX requires one target file")
        runtime = data["strix_runtime"]
        rocm = data["strix_rocm"]
        require_url(runtime["repository"], "ROCm runtime repository")
        require_sha(runtime["submodule_commit"], "runtime submodule commit", HEX40)
        require_sha(runtime["source_diff_sha256"], "runtime source diff")
        require_sha(rocm["rocwmma_commit"], "rocWMMA commit", HEX40)
        qualified_paths = (
            rocm.get("qualified_source_path"),
            rocm.get("qualified_build_path"),
            rocm.get("qualified_rocwmma_path"),
        )
        if qualified_paths != (
            "/opt/m5/src/lucebox-050-pr667-5eb4fbe",
            "/opt/m5/src/lucebox-050-pr667-5eb4fbe/server/build-qualified",
            "/opt/m5/src/rocWMMA-rocm-7.1.1-public-v2",
        ):
            fail("ROCm absolute build paths drifted from the qualified ELF inputs")
        for patch in rocm["patches"]:
            require_sha(patch["sha256"], f"patch {patch['name']}")
            patch_path = root / "patches" / patch["name"]
            if not patch_path.is_file():
                fail(f"missing public patch: {patch['name']}")
            actual = hashlib.sha256(patch_path.read_bytes()).hexdigest()
            if actual != patch["sha256"]:
                fail(f"public patch hash drifted: {patch['name']}")

    if data.get("strix_artifact_seed_paths"):
        fail("public manifest contains machine-local artifact seeds")
    if data.get("strix_runtime_archive_seed_path"):
        fail("public manifest contains a machine-local runtime seed")
    if data.get("strix_runtime_manifest_seed_path"):
        fail("public manifest contains a machine-local runtime manifest seed")
    if data.get("strix_vulkan_loader_seed_path"):
        fail("public manifest contains a machine-local Vulkan loader seed")
    return data


def validate_benchmarks(root: Path) -> None:
    data = json.loads((root / "benchmarks/results.json").read_text())
    defaults = []
    for path in sorted((root / "ansible/releases").glob("*.yml")):
        manifest = yaml.safe_load(path.read_text())
        identity = manifest["strix_system"]["id"]
        system = data["systems"][identity]
        if system["name"] != manifest["strix_system"]["name"]:
            fail("benchmark stack name differs from manifest")
        if system["manifest_sha256"] != hashlib.sha256(path.read_bytes()).hexdigest():
            fail("benchmark manifest identity drifted: " + identity)
        if manifest["strix_system"]["selected_default"]:
            defaults.append(identity)
    if defaults != [data["default_system"]] or defaults != ["strata-qwen-q4xl"]:
        fail("the release set must select Qwen / Strata as its single default")
    baseline = data["systems"]["qwen-vulkan-q4xl"]["context_scaling"]
    strata = data["systems"]["strata-qwen-q4xl"]
    curve = strata["context_scaling"]
    if len(baseline) != 10 or len(curve) != 10:
        fail("Qwen must retain all ten measured context points")
    for a, b in zip(baseline, curve):
        keys = ("prompt_sha256", "actual_input_tokens", "cached_tokens")
        if any(a[k] != b[k] for k in keys) or a["cached_tokens"] != 0:
            fail("Qwen comparison workload identities differ")
        require_sha(a["prompt_sha256"], "Qwen prompt")
        for point in (a, b):
            require_sha(point["evidence_sha256"], "Qwen measurement evidence")
    four_slot = strata["four_slot_context_scaling"][0]
    if any(four_slot[k] != baseline[6][k] for k in ("prompt_sha256", "actual_input_tokens", "cached_tokens")):
        fail("four-slot point differs from the matched 128K workload")


def scan_public_tree(root: Path) -> None:
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if not path.is_file() or any(part in {".git", ".venv"} for part in relative.parts):
            continue
        if relative == Path("ansible/inventory/hosts.yml") or path.suffix not in TEXT_SUFFIXES:
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        if path.stat().st_size > 2_000_000:
            fail(f"unexpected large text file: {relative}")
        text = path.read_text(encoding="utf-8")
        for label, pattern in FORBIDDEN_PUBLIC_PATTERNS.items():
            if pattern.search(text):
                fail(f"possible {label} in {relative}")


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: validate_release.py RELEASE.yml")
    manifest = Path(sys.argv[1]).resolve()
    root = Path(__file__).resolve().parents[1]
    data = validate_manifest(manifest, root)
    scan_public_tree(root)
    validate_benchmarks(root)
    summary = {
        "release": data["strix_release_id"],
        "system": data["strix_system"]["name"],
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "target_bytes": data["strix_target"]["total_size"],
        "draft_bytes": data["strix_draft"].get("size"),
        "public_tree_scan": "passed",
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
