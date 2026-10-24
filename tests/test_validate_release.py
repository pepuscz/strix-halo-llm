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
DUMMY_HEX64 = "0123456789abcdef" * 4
# Typed dummies where the validator requires a type other than a 64-hex digest.
DUMMIES = {"tag_object": "0123456789abcdef0123456789abcdef01234567",
           "coding": 10, "gsm8k": 10, "math": 10, "total": 30, "largest_input_tokens": 122880}


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

    def test_glm_draft_fails_on_its_pending_installer_run(self) -> None:
        self.assertEqual(VALIDATOR.pending_fields(self.glm()), ["strix_qualification.qualified_configuration"])
        self.assert_fails(self.glm(), "draft release: 1 value(s) are PENDING")

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
            (lambda d: d["strix_target"].update(total_size=d["strix_target"]["total_size"]
                                                - d["strix_target"]["files"].pop()["size"]), "three Maya-M shards"),
            (lambda d: d["strix_target"]["files"][2].update(size=1), "target file total"),
        ):
            broken = copy.deepcopy(data)
            mutate(broken)
            with self.subTest(expect=message):
                self.assert_fails(broken, message)


if __name__ == "__main__":
    unittest.main()
