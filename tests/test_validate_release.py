"""The release validator: every published release passes, and a draft release (a PENDING pin or result, alone or in
a sentence) fails until the qualified host supplies it. A draft's structure is checked with the PENDING filled in."""

from __future__ import annotations

import copy
import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("validate_release", ROOT / "scripts/validate_release.py")
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)
GLM = ROOT / "ansible/releases/maya-glm-dual-xtx-512k.yml"
DS4 = ROOT / "ansible/releases/maya-ds4-dual-xtx-512k.yml"
GSQ = ROOT / "ansible/releases/maya-ds4-gsq-dual-xtx-512k.yml"
DUMMY_HEX64 = "0123456789abcdef" * 4
# Typed dummies where the validator requires a type other than a 64-hex digest.
DUMMIES = {"tag_object": "0123456789abcdef0123456789abcdef01234567",
           "coding": 10, "gsm8k": 10, "math": 10, "total": 30, "largest_input_tokens": 122880, "values": "55/55",
           "first_request_prefill_tokens_per_second": 1000.0, "first_request_decode_tokens_per_second": 40.0,
           "reused_prompt_decode_tokens_per_second": 45.0}


def without_pending(node: object, key: str = "") -> object:
    """The manifest with every PENDING filled: a whole value by a well-formed dummy, a word in a sentence by 'done'."""
    if isinstance(node, dict):
        return {name: without_pending(value, name) for name, value in node.items()}
    if isinstance(node, list):
        return [without_pending(value, key) for value in node]
    if node == VALIDATOR.PENDING:
        return DUMMIES.get(key, DUMMY_HEX64)
    if isinstance(node, str):
        return VALIDATOR.PENDING_WORD.sub("done", node)
    return node


class ReleaseValidatorTest(unittest.TestCase):
    def validate(self, data: dict, root: Path = ROOT) -> dict:
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "release.yml"
            manifest.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
            return VALIDATOR.validate_manifest(manifest, root)

    def assert_fails(self, data: dict, message: str, root: Path = ROOT) -> None:
        with self.assertRaises(SystemExit) as raised:
            self.validate(data, root)
        self.assertIn(message, str(raised.exception))

    def glm(self) -> dict:
        return yaml.safe_load(GLM.read_text(encoding="utf-8"))

    def test_every_release_validates_or_is_a_draft(self) -> None:
        for path in sorted((ROOT / "ansible/releases").glob("*.yml")):
            with self.subTest(release=path.name):
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
                if VALIDATOR.pending_fields(data):
                    with self.assertRaises(SystemExit) as raised:
                        VALIDATOR.validate_manifest(path, ROOT)
                    self.assertTrue(str(raised.exception).startswith("ERROR: draft release: "))
                else:
                    VALIDATOR.validate_manifest(path, ROOT)

    def test_glm_is_qualified(self) -> None:
        self.assertEqual(VALIDATOR.pending_fields(self.glm()), [])
        self.assertEqual(self.validate(self.glm())["strix_release_id"], "maya-glm-dual-xtx-512k-v1")

    def test_a_missing_python_lock_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / "patches", root / "patches")
            shutil.copytree(ROOT / VALIDATOR.MAYA_FILES, root / VALIDATOR.MAYA_FILES)
            (root / VALIDATOR.MAYA_FILES / "requirements-glm.lock").unlink()
            self.assert_fails(without_pending(self.glm()),
                              "Maya build input missing: ansible/roles/maya_runtime/files/requirements-glm.lock", root)

    def test_glm_validates_once_filled_and_rejects_drift(self) -> None:
        data = without_pending(self.glm())
        self.assertEqual(self.validate(data)["strix_system"]["id"], "maya-glm-dual-xtx")
        for mutate, message in (
            (lambda d: d["strix_maya"]["server"]["env"].update(MAYA_GLM_SPLIT="24"), "environment drifted: MAYA_GLM_SPLIT"),
            (lambda d: d["strix_maya"]["server"]["env"].update(MAYA_GLM_CKPTS="0"), "environment drifted: MAYA_GLM_CKPTS"),
            (lambda d: d["strix_maya"]["server"]["env"].update(MAYA_GLM_SLOT_DIR="/tmp/slots"), "MAYA_GLM_SLOT_DIR"),
            (lambda d: d["strix_maya"]["server"]["env"].pop("MAYA_GLM_SLOT_KEEP"), "MAYA_GLM_SLOT_KEEP"),
            (lambda d: d["strix_maya"]["server"]["args"].remove("--kv-streaming"), "arguments drifted"),
            (lambda d: d["strix_maya"]["server"]["args"].__setitem__(3, "131072"), "arguments drifted"),
            (lambda d: d["strix_service"].update(context=131072), "allocate exactly 524288 tokens"),
            (lambda d: d["strix_service"].update(memory_high="118G"), "cgroup memory envelope drifted"),
            (lambda d: d["strix_maya"].pop("family"), "does not match maya-glm-dual-xtx"),
            (lambda d: d["strix_maya"].update(requirements_sha256=DUMMY_HEX64), "build input drifted: requirements-glm.lock"),
            (lambda d: d["strix_maya"]["pack_files"].update({"compat-bf16.json": DUMMY_HEX64}), "pack file set"),
            (lambda d: d["strix_maya"]["server"].update(gpu=[0, 1]), "server identity"),
            (lambda d: d["strix_qualification"]["answer_quality"]["output_caps"].update(math=4096), "output caps"),
            (lambda d: d["strix_qualification"]["answer_quality"].update(total=30), "sum to the total"),
            (lambda d: d["strix_qualification"]["retrieval_ladder"]["allocations"][0].update(points=10), "7, 4 and 1"),
            (lambda d: d["strix_qualification"]["retrieval_ladder"].update(largest_input_tokens=1), "largest input"),
            (lambda d: d["strix_qualification"]["retrieval_ladder"]["allocations"][1]["decode_tokens_per_second"].pop(),
             "one decode_tokens_per_second per point"),
            (lambda d: d["strix_qualification"]["long_context"].pop("reused_prompt_cached_tokens"),
             "long-context record drifted"),
            (lambda d: d["strix_qualification"]["long_context"].update(allocation_tokens=131072),
             "long-context record must hold"),
            (lambda d: d["strix_qualification"]["long_context"].update(
                reused_prompt_cached_tokens=d["strix_qualification"]["long_context"]["input_tokens"]),
             "long-context record must hold"),
            (lambda d: d["strix_target"].update(total_size=d["strix_target"]["total_size"]
                                                - d["strix_target"]["files"].pop()["size"]), "three Maya-M shards"),
            (lambda d: d["strix_target"]["files"][2].update(size=1), "target file total"),
        ):
            broken = copy.deepcopy(data)
            mutate(broken)
            with self.subTest(expect=message):
                self.assert_fails(broken, message)


    def ds4(self) -> dict:
        return yaml.safe_load(DS4.read_text(encoding="utf-8"))

    def test_ds4_validates_once_filled_and_rejects_drift(self) -> None:
        data = without_pending(self.ds4())
        self.assertEqual(self.validate(data)["strix_release_id"], "maya-ds4-dual-xtx-512k-v4")
        env = data["strix_maya"]["server"]["env"]
        self.assertEqual((env["MAYA_DS4_SLOT_DIR"], env["DS4_DECODE_TRIM"]),
                         (data["strix_paths"]["state"] + "/ds4-slots", "15"))
        for mutate, message in (
            (lambda d: d["strix_maya"]["server"]["env"].update(DS4_DECODE_TRIM="7"), "environment drifted: DS4_DECODE_TRIM"),
            (lambda d: d["strix_maya"]["server"]["env"].update(DS4_FLOW_STATS="1"), "environment drifted: DS4_FLOW_STATS"),
            (lambda d: d["strix_maya"]["server"]["env"].pop("MAYA_DS4_SLOT_KEEP"), "MAYA_DS4_SLOT_KEEP"),
            (lambda d: d["strix_maya"]["server"]["env"].update(
                MAYA_DS4_SLOT_DIR=d["strix_paths"]["state"] + "/slots"), "MAYA_DS4_SLOT_DIR"),
            (lambda d: d["strix_maya"]["server"]["env"].update(DS4_HC_FUSE="1"), "environment drifted: DS4_HC_FUSE"),
            (lambda d: d["strix_maya"]["server"]["args"].__setitem__(3, "262144"), "arguments drifted"),
            (lambda d: d["strix_maya"]["server"]["args"].__delitem__(slice(-2, None)), "arguments drifted"),
            (lambda d: d["strix_service"].update(context=262144), "allocate exactly 524288 tokens"),
            (lambda d: d["strix_maya"]["server"].update(log="/tmp/native.log"), "server setting drifted: log"),
            (lambda d: d["strix_qualification"]["retrieval_ladder"].update(points=10), "eleven five-value points"),
            (lambda d: d["strix_qualification"]["retrieval_ladder"].update(values="50/50"), "eleven five-value points"),
            (lambda d: d["strix_qualification"]["long_context"].update(allocation_tokens=131072),
             "long-context record must hold"),
            (lambda d: d["strix_qualification"]["long_context"].update(reused_prompt_cached_tokens=130048),
             "long-context record must hold"),
            (lambda d: d["strix_qualification"].pop("deep_needle"), "qualification sections drifted"),
            (lambda d: d["strix_qualification"]["answer_quality"].update(total=29), "sum to the total"),
        ):
            broken = copy.deepcopy(data)
            mutate(broken)
            with self.subTest(expect=message):
                self.assert_fails(broken, message)

    def gsq(self) -> dict:
        data = without_pending(yaml.safe_load(GSQ.read_text(encoding="utf-8")))
        data["strix_qualification"]["deep_needle"]["values"] = "5/5"   # (the dummy "55/55" is the ladder's form)
        return data

    def test_gsq_validates_once_filled_and_rejects_drift(self) -> None:
        data = self.gsq()
        self.assertEqual(self.validate(data)["strix_release_id"], "maya-ds4-gsq-dual-xtx-512k-v3")
        maya = data["strix_maya"]
        self.assertEqual((maya["model_subdirectory"], maya["dense_q8_0"]["tensors"], maya["dense_q8_0"]["size"]),
                         ("IQ2_XS", 524, 8236072960))
        self.assertEqual(maya["server"]["env"], yaml.safe_load(DS4.read_text(encoding="utf-8"))["strix_maya"]["server"]["env"]
                         | {"ROCBLAS_TENSILE_LIBPATH": data["strix_paths"]["release"] + "/rocm/lib/rocblas/library",
                            "DS4_LT_STORE": data["strix_paths"]["state"] + "/lt-picks.txt",
                            "MAYA_DS4_SLOT_DIR": data["strix_paths"]["state"] + "/ds4-slots",
                            "MAYA_DS4_DSPARK_CUM": "0.35", "MAYA_DS4_RESTORE_TAIL": "0"})
        for mutate, message in (
            (lambda d: d["strix_maya"].update(model_subdirectory="Maya-S"), "strix_maya.model_subdirectory"),
            (lambda d: d["strix_target"]["files"][1].update(local_subdirectory="Maya-S"), "strix_maya.model_subdirectory"),
            (lambda d: d["strix_maya"]["dense_q8_0"].update(tensors=0), "dense_q8_0 drifted"),
            (lambda d: d["strix_maya"]["dense_q8_0"].update(converter_sha256="0" * 64), "build input drifted"),
            (lambda d: d["strix_maya"]["dense_q8_0"].pop("from"), "dense_q8_0 drifted"),
            (lambda d: d["strix_maya"]["dense_q8_0"].update(active_tensors=["head.weight"]), "dense_q8_0 drifted"),
            (lambda d: d["strix_maya"]["ds4_geometry"].update(dspark_block_size=5), "ds4_geometry"),
            (lambda d: d["strix_maya"]["server"]["env"].update(DS4_DECODE_TRIM="7"), "environment drifted: DS4_DECODE_TRIM"),
            (lambda d: d["strix_qualification"]["answer_quality"].update(math=9), "sum to the total"),
        ):
            broken = copy.deepcopy(data)
            mutate(broken)
            with self.subTest(expect=message):
                self.assert_fails(broken, message)

    def test_gsq_reporting_rejects_other_prompts_or_cache_counts(self) -> None:
        import json
        for mutate, message in (
            (lambda d: d["systems"]["maya-ds4-gsq-dual-xtx"]["context_scaling"][0].update(prompt_sha256="0" * 64),
             "retrieval workload identities differ"),
            (lambda d: d["systems"]["maya-ds4-gsq-dual-xtx"]["cold_start_recheck"].update(prompt_sha256="0" * 64),
             "cold recheck workload identity differs"),
            (lambda d: d["systems"]["maya-ds4-gsq-dual-xtx"]["long_context"]["reused_prompt"].update(cached_tokens=0),
             "release long-context readings differ"),
            (lambda d: d["systems"]["maya-ds4-gsq-dual-xtx"]["maya_bench"].update(inputs_sha256="0" * 64),
             "Maya benchmark inputs differ"),
        ):
            with self.subTest(message=message), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                shutil.copytree(ROOT / "benchmarks", root / "benchmarks")
                shutil.copytree(ROOT / "ansible/releases", root / "ansible/releases")
                path = root / "benchmarks/results.json"
                data = json.loads(path.read_text())
                mutate(data)
                path.write_text(json.dumps(data))
                with self.assertRaisesRegex(SystemExit, message):
                    VALIDATOR.validate_benchmarks(root)

    def test_a_draft_is_skipped_by_the_benchmark_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / "benchmarks", root / "benchmarks")
            shutil.copytree(ROOT / "ansible/releases", root / "ansible/releases")
            if VALIDATOR.pending_fields(self.ds4()):
                VALIDATOR.validate_benchmarks(root)   # (the draft's predecessor's results do not fail it)
            data = self.ds4()
            data["strix_system"]["selected_default"] = True
            (root / "ansible/releases" / DS4.name).write_text(yaml.safe_dump(
                data if VALIDATOR.pending_fields(data) else dict(data, strix_qualification="PENDING"), sort_keys=False))
            with self.assertRaises(SystemExit) as raised:
                VALIDATOR.validate_benchmarks(root)
            self.assertIn("a draft release cannot be the default", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
