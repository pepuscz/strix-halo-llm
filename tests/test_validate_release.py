"""The release validator: every published release passes, and a draft release (PENDING pins) fails until the
qualified host supplies them. A draft's structure is checked by substituting well-formed dummy pins."""

from __future__ import annotations

import copy
import hashlib
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
GLM = ROOT / "ansible/releases/maya-glm-dual-xtx-128k.yml"
DUMMY_HEX64 = "0123456789abcdef" * 4
# Typed dummies where the validator requires a type other than a 64-hex digest.
DUMMIES = {"tag_object": "0123456789abcdef0123456789abcdef01234567",
           "coding": 10, "gsm8k": 10, "math": 10, "total": 30, "largest_input_tokens": 122880}


def with_dummy_pins(node: object, key: str = "") -> object:
    if isinstance(node, dict):
        return {name: with_dummy_pins(value, name) for name, value in node.items()}
    if isinstance(node, list):
        return [with_dummy_pins(value, key) for value in node]
    return DUMMIES.get(key, DUMMY_HEX64) if node == VALIDATOR.PENDING else node


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

    def test_glm_draft_fails_on_its_pending_pins(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            VALIDATOR.validate_manifest(GLM, ROOT)
        message = str(raised.exception)
        for field in ("strix_platform.kernel", "strix_runtime.tag_object", "strix_runtime.server_sha256",
                      "strix_maya.requirements_sha256", "strix_maya.pack_compat_bf16_normalized_sha256",
                      "strix_qualification.answer_quality.total"):
            self.assertIn(field, message)
        self.assertIn("build input missing: ansible/roles/maya_runtime/files/requirements-glm.lock", message)

    def test_glm_dummy_pins_still_report_the_missing_python_lock(self) -> None:
        self.assert_fails(with_dummy_pins(self.glm()),
                          "Maya build input missing: ansible/roles/maya_runtime/files/requirements-glm.lock")

    def test_glm_structure_validates_with_dummy_pins_and_lock(self) -> None:
        data = with_dummy_pins(self.glm())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / "patches", root / "patches")
            shutil.copytree(ROOT / VALIDATOR.MAYA_FILES, root / VALIDATOR.MAYA_FILES)
            lock = root / VALIDATOR.MAYA_FILES / "requirements-glm.lock"
            lock.write_text("# dummy\n", encoding="utf-8")
            data["strix_maya"]["requirements_sha256"] = hashlib.sha256(lock.read_bytes()).hexdigest()
            self.assertEqual(self.validate(data, root)["strix_system"]["id"], "maya-glm-dual-xtx")
            for mutate, message in (
                (lambda d: d["strix_maya"]["server"]["env"].update(MAYA_GLM_SPLIT="24"), "environment drifted: MAYA_GLM_SPLIT"),
                (lambda d: d["strix_maya"]["server"]["args"].remove("--kv-streaming"), "arguments drifted"),
                (lambda d: d["strix_service"].update(context=262144), "allocate exactly 131072 tokens"),
                (lambda d: d["strix_service"].update(memory_high="118G"), "cgroup memory envelope drifted"),
                (lambda d: d["strix_maya"].pop("family"), "does not match maya-glm-dual-xtx"),
                (lambda d: d["strix_maya"]["pack_files"].update({"compat-bf16.json": DUMMY_HEX64}), "pack file set"),
                (lambda d: d["strix_maya"]["server"].update(gpu=[0, 1]), "server identity"),
                (lambda d: d["strix_qualification"]["answer_quality"]["output_caps"].update(math=4096), "output caps"),
                (lambda d: d["strix_qualification"]["retrieval_ladder"].update(points=10), "seven points"),
                (lambda d: d["strix_target"].update(total_size=d["strix_target"]["total_size"]
                                                    - d["strix_target"]["files"].pop()["size"]), "three Maya-M shards"),
                (lambda d: d["strix_target"]["files"][2].update(size=1), "target file total"),
            ):
                broken = copy.deepcopy(data)
                mutate(broken)
                with self.subTest(expect=message):
                    self.assert_fails(broken, message, root)


if __name__ == "__main__":
    unittest.main()
