"""The DeepSeek pack's dense-matrix converter (ansible/roles/maya_runtime/files/convert-dense-q8_0.py): the Q5_K
blocks to float and ggml's Q8_0 rounding, checked against llama.cpp's gguf-py on sixteen real blocks of a GSQ-RCO
shared expert (tests/fixtures); the plan, the side file, the rewritten tensors.txt and the refusals on a fake pack."""

from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("convert_dense_q8_0",
                                              ROOT / "ansible/roles/maya_runtime/files/convert-dense-q8_0.py")
assert SPEC is not None and SPEC.loader is not None
CONVERT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONVERT)
FIXTURES = ROOT / "tests/fixtures"
Q5K = (FIXTURES / "q5k-16blocks.bin").read_bytes()          # (16 real Q5_K blocks: a [16][256] matrix)
Q8 = (FIXTURES / "q8_0-16blocks.bin").read_bytes()          # (them as Q8_0 by gguf-py)
try:
    import numpy as np
except ImportError:                                          # (the converter runs in the engine's venv, which has it)
    np = None


@unittest.skipIf(np is None, "numpy is not installed here")
class ConverterTest(unittest.TestCase):
    def test_q5k_to_float_matches_gguf_py(self) -> None:
        x = CONVERT.q5k_to_f32(Q5K, 256)
        self.assertEqual(x.shape, (16, 256))
        np.testing.assert_array_equal(x, np.load(FIXTURES / "f32-16blocks.npy").reshape(16, 256))

    def test_q8_0_matches_gguf_py_but_rounding_ties(self) -> None:
        q8 = CONVERT.f32_to_q8_0(CONVERT.q5k_to_f32(Q5K, 256))
        self.assertEqual(len(q8), 16 * 256 // 32 * 34)
        self.assertGreaterEqual(sum(a == b for a, b in zip(q8, Q8)), len(q8) - 4)
        blocks = np.frombuffer(q8, np.uint8).reshape(-1, 34)
        back = blocks[:, :2].copy().view(np.float16).astype(np.float32) * blocks[:, 2:].view(np.int8).astype(np.float32)
        self.assertLess(np.abs(back.reshape(16, 256) - CONVERT.q5k_to_f32(Q5K, 256)).max(), 0.004)

    def fake_pack(self) -> tuple[Path, Path]:
        t = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, t)
        model, pack = t / "models/IQ2_XS", t / "models/IQ2_XS/maya-ds4-dspark"
        pack.mkdir(parents=True)
        (model / "s2.gguf").write_bytes(b"\0" * 64 + Q5K)
        (pack / "tensors.txt").write_text(
            "file 0 s0.gguf\nfile 1 s1.gguf\nfile 2 s2.gguf\nfile 3 s3.gguf\nfile 4 ../Engram/engram.gguf\n"
            "file 5 ../dspark/dspark.bin\nt x BF16 0 0 2 1\nt layers.0.ffn.shared_experts.w1.weight Q5_K 2 64 2816 16 256\n"
            "t engram_table Q6_K 4 0 210 256\n")
        (pack / "ds4.txt").write_text("vocab_size 129280\ndspark_block_size 0\ndspark_target_layer_ids \nformat gguf\n"
                                      f"model_dir {model}\n")
        return model, pack

    def test_the_conversion(self) -> None:
        model, pack = self.fake_pack()
        geometry = {"dspark_block_size": "5", "dspark_target_layer_ids": "37,38,39", "dspark_markov_rank": "256"}
        res = CONVERT.convert(pack, model, "dense-q8_0.bin", 1, 4352, geometry=geometry)
        self.assertEqual((res["tensors"], res["bytes"], res["file"]), (1, 4352, str(model / "dense-q8_0.bin")))
        self.assertEqual(res["ds4_patched"], {"dspark_block_size": ("0", "5"), "dspark_target_layer_ids": ("", "37,38,39"),
                                              "dspark_markov_rank": (None, "256")})
        self.assertEqual((model / "dense-q8_0.bin").read_bytes(), Q8)
        self.assertEqual(oct((model / "dense-q8_0.bin").stat().st_mode & 0o777), oct(0o444))
        files, entries = CONVERT.read_tensors(pack / "tensors.txt")
        self.assertEqual(files[-1], "dense-q8_0.bin")
        by = {e["name"]: e for e in entries}
        self.assertEqual(by["layers.0.ffn.shared_experts.w1.weight"],
                         {"name": "layers.0.ffn.shared_experts.w1.weight", "dtype": "Q8_0", "file": 6, "off": 0,
                          "bytes": 4352, "dims": [16, 256]})
        self.assertEqual((by["x"]["dtype"], by["engram_table"]["dtype"]), ("BF16", "Q6_K"))
        ds4 = (pack / "ds4.txt").read_text().splitlines()
        self.assertEqual(ds4[:5], ["vocab_size 129280", "dspark_block_size 5", "dspark_target_layer_ids 37,38,39",
                                   "dspark_markov_rank 256", "format gguf"])
        # a second run on a rebuilt pack: the side file refuses without --replace, and is rewritten with it
        (pack / "tensors.txt").write_text((pack / "tensors.txt").read_text().replace(
            "t layers.0.ffn.shared_experts.w1.weight Q8_0 6 0 4352 16 256", "t layers.0.ffn.shared_experts.w1.weight Q5_K 2 64 2816 16 256")
            .replace("file 6 dense-q8_0.bin\n", ""))
        self.assertIn("already there", CONVERT.convert(pack, model, "dense-q8_0.bin", 1, 4352)["reasons"][0])
        self.assertEqual(CONVERT.convert(pack, model, "dense-q8_0.bin", 1, 4352, replace=True)["tensors"], 1)
        self.assertEqual((model / "dense-q8_0.bin").read_bytes(), Q8)

    def test_hybrid_preserves_native_ranges_and_uses_only_embed_and_head(self) -> None:
        model, pack = self.fake_pack()
        path = pack / "tensors.txt"
        path.write_text(path.read_text() +
                        "t embed.weight Q5_K 2 64 2816 16 256\n"
                        "t head.weight Q5_K 2 64 2816 16 256\n")
        files, entries = CONVERT.read_tensors(path)
        plan, total, why = CONVERT.convert_plan(files, entries)
        self.assertEqual(why, [])
        result = CONVERT.convert(pack, model, "dense-q8_0.bin", len(plan), total,
                                 active_names=["embed.weight", "head.weight"])
        self.assertNotIn("reasons", result)
        after_files, after = CONVERT.read_tensors(path)
        by = {e["name"]: e for e in after}
        self.assertEqual(by["layers.0.ffn.shared_experts.w1.weight"], entries[1])
        self.assertEqual(by["layers.0.ffn.shared_experts.w1.weight"]["dtype"], "Q5_K")
        for name in ("embed.weight", "head.weight"):
            self.assertEqual(by[name]["dtype"], "Q8_0")
            self.assertEqual(after_files[by[name]["file"]], "dense-q8_0.bin")
            side = (model / "dense-q8_0.bin").read_bytes()
            self.assertEqual(side[by[name]["off"]:by[name]["off"] + by[name]["bytes"]], Q8)

    def test_unknown_active_tensor_refuses_before_weight_writes(self) -> None:
        model, pack = self.fake_pack()
        before = (pack / "tensors.txt").read_bytes()
        result = CONVERT.convert(pack, model, "dense-q8_0.bin", 1, 4352, active_names=["missing.weight"])
        self.assertIn("active tensors", result["reasons"][0])
        self.assertFalse((model / "dense-q8_0.bin").exists())
        self.assertEqual((pack / "tensors.txt").read_bytes(), before)

    def test_the_refusals(self) -> None:
        model, pack = self.fake_pack()
        self.assertIn("the release pins 2 of 4352", CONVERT.convert(pack, model, "d.bin", 2, 4352)["reasons"][0])
        self.assertIn("the release pins 1 of 4000", CONVERT.convert(pack, model, "d.bin", 1, 4000)["reasons"][0])
        self.assertFalse((model / "d.bin").exists())
        text = (pack / "tensors.txt").read_text()
        (pack / "tensors.txt").write_text(text.replace("Q5_K 2 64 2816 16 256", "Q4_K 2 64 2304 16 256"))
        self.assertIn("no converter", CONVERT.convert(pack, model, "d.bin", 1, 4352)["reasons"][0])
        (pack / "tensors.txt").write_text(text.replace("2816 16 256", "2816 32 128"))
        self.assertIn("not whole 256-value blocks", CONVERT.convert(pack, model, "d.bin", 1, 4352)["reasons"][0])
        (pack / "tensors.txt").write_text(text)
        (pack / "ds4.txt").write_text("dspark_block_size 7\nformat gguf\n")
        with self.assertRaises(SystemExit):                       # (the GGUF sets a geometry value to something else)
            CONVERT.convert(pack, model, "d.bin", 1, 4352, geometry={"dspark_block_size": "5"})
        self.assertFalse((model / "d.bin").exists())

    def test_the_command_line(self) -> None:
        model, pack = self.fake_pack()
        self.assertEqual(CONVERT.main([str(pack), str(model), "--file", "d.bin", "--tensors", "1", "--bytes", "4352",
                                       "--ds4", "dspark_block_size=5"]), 0)
        self.assertEqual(CONVERT.main([str(pack), str(model), "--file", "d.bin", "--tensors", "1", "--bytes", "4352"]), 1)


if __name__ == "__main__":
    unittest.main()
