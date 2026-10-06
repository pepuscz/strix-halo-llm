# Architecture

The winning setups are Strata HIP UD-Q4_K_XL for Qwen and Strix Halo llama.cpp Vulkan IQ3_XXS for DeepSeek. This table describes the three published Ansible recipes; the measured Qwen Vulkan baseline settings are recorded in [BENCHMARKS.md](BENCHMARKS.md#qwen-context-scaling).

| Layer | Winning Qwen setup / Strata HIP UD-Q4_K_XL | Winning DeepSeek setup / Strix Halo llama.cpp Vulkan IQ3_XXS | DeepSeek comparison baseline / Lucebox ROCm ROCmFPX |
|---|---|---|---|
| Runtime | Strata v0.1.40, unmodified pinned source | Official strix-halo-llamacpp v0.7.0 portable release | Unmodified Lucebox commit `5eb4fbe` |
| GPU | HIP gfx1151, isolated ROCm 7.14.1 SDK | Bundled Mesa RADV / Vulkan | Ubuntu ROCm 7.1, HIP gfx1151, rocWMMA |
| Target | Native UD-Q4_K_XL expert/PLE tensors; BF16-compatible dense pack | Unsloth UD-IQ3_XXS | ROCmFPX MIX |
| Draft | Q2_0 routed MTP experts; Q8_0/BF16/F32 dense pack; runtime Q4 projection/head | DSpark Q2_K/Q8_0 | DSpark Q4RMFP4 dense-F16 |
| KV | int8 | q8_0 K/V | q4_0 K/V |
| Context | 4 × 262,144 | 1 × 524,288 | 1 × 131,072 |
| Speculation | Solo MTP length 4; lookup chain 3; batched MTP disabled | DSpark maximum length 4 | Q=4 fused verification |
| Prefill | 8,192; borrowing disabled | Qualified upstream tuning | Sparse chunk 3,072 |
| MemoryHigh / MemoryMax | 123G / 125G | 118G / 120G | 118G / 120G |
| CPU boost / GPU DPM | Off / auto | Off / auto | On / high |
| Cooling | GPU-demand governor | GPU-demand governor | Maximum while active |

## Strata runtime

Native expert mmap and a 24 GiB expert cache preserve the target's UD-Q4_K_XL representation. `iq_pack --compat-bf16` prepares compatible dense tensors. Derived tensors and tokenizer files are checked against the qualified SHA-256 values. The 31 MTP tensors are fetched from an immutable BF16 model revision and checked individually before conversion.

The serving profile follows the pinned upstream gfx1151 fast paths: fused/GEMM prefill, WMMA selection, HC upmix/Q8, and the upstream hipBLASLt tuning file. `STRATA_QFUSE=0` avoids the [batched-GDN quantization issue](https://github.com/Niko1221/Strata/issues/1139). Batched MTP remains disabled pending [upstream support](https://github.com/Niko1221/Strata/issues/1121); solo MTP remains enabled. Prefill borrowing is disabled in the qualified four-slot profile. `--pcie-frac 0` and `--adapt-every 1000000` hold expert placement stable.

Four independent long-context conversations pass. Strict token parity for one interleaved continued conversation is a current limit of the fast numerical profile; answer quality is graded separately. Structured outputs use prompt-and-validate rather than constrained decoding. Higher slot counts are unqualified.

## Vulkan runtime

The DeepSeek stack uses the official v0.7.0 archive unchanged. Launcher, server, Vulkan backend, RADV driver, and libraries are pinned by SHA-256. The upstream environment includes `GGML_VK_MMID_M128=1` and `GGML_VK_FA_WAVE32=1`.

## Lucebox runtime

The pinned clean source includes gfx1151 split-KV indexed MLA, Q4 MMVF projection, ROCmFP2/3 Wave32 kernels, four-row activation reuse, sparse verifier attention, incremental verification masks, and exact block-radix top-k selection. Server, feature-gate, DeepSeek 4, ROCmFPX numerical, grouped-dispatch, and top-k tests run during the build.

## Host and service

Ansible owns pinned artifacts, runtime builds, GRUB settings, the reversible hardware-policy controller, cooling driver, and systemd units. Each model service uses the same 120 W package envelope, 2 GHz minimum CPU frequency, disabled swap, and large-GTT settings. `strix-halo-inference.service` is enabled at boot and binds to `127.0.0.1:18109`. The GPU-demand fan controller reads sysfs once per second.
