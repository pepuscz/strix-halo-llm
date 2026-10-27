# Architecture

## Dual RX 7900 XTX

The current dual-card setup runs one recipe at a time. Each RX 7900 XTX has its own PCIe 4.0 ×4 M.2-to-OCuLink link; the Radeon 8060S serves routed experts held in the M5's RAM. An external SSD connects over USB4.

| Model | Stack | Context | Parallel work |
|---|---|---:|---|
| DeepSeek-V4.1-Flash-1017 GSQ-RCO IQ2_XS | **Maya DS4 HIP GSQ-RCO IQ2_XS dual RX 7900 XTX** | 1 × 512K | Tensor parallel across the cards; DSpark drafter split across them; the quant's dense matrices converted to Q8_0 at install |
| DeepSeek-V4.1-Flash-1017 Maya-S IQ2_XXS | **Maya DS4 HIP Maya-S IQ2_XXS dual RX 7900 XTX** | 1 × 512K | The same engine settings on the Maya-S quant |
| GLM-5.3-Flash Maya-M IQ2_S | **Maya HIP Maya-M IQ2_S dual RX 7900 XTX** | 1 × 512K | Layers split across the cards; model MTP drafts tokens |

The [DeepSeek GSQ-RCO recipe](../ansible/releases/maya-ds4-gsq-dual-xtx-512k.yml), the [DeepSeek Maya-S recipe](../ansible/releases/maya-ds4-dual-xtx-512k.yml) and the [GLM recipe](../ansible/releases/maya-glm-dual-xtx-512k.yml) pin the runtime and serving settings.

### The DeepSeek engine's settings

The model (about 178 GB, plus a 203 GB Engram shard read in place) is far larger than the cards' 48 GB, so the work is where the bytes are. The recipe turns on these Maya settings; each is checked by the engine when it loads.

- **Placement.** The two cards are one tensor-parallel group (`DS4_TP_GGUF_UNEVEN`: each takes whole 256-value blocks of every expert), and each keeps its part of about 2,750 experts in VRAM. The Radeon 8060S holds the next ~8,300 most-used experts in a 95 GB pool and computes them (`DS4_HELPER`), keeping a few recently repeated ones in reserved slots (`DS4_HELPER_RECENT`). The rest are read from the NVMe. The DSpark drafter's first block runs on the second card (`DS4_DRAFT_DEV`).
- **Reading a prompt.** A long prompt is read in 32,768-token chunks. Its experts reach the cards over their PCIe 4.0 ×4 links, so the recipe cuts those bytes:
  - experts the 8060S already holds are copied from its pool rather than read from the disk (`DS4_FLOW_HELPER`);
  - each card receives only its own columns of an expert's down projection, and the disk read is shared (`DS4_FLOW_DOWN_PART`, `DS4_FLOW_DOWN_SHARE`);
  - the cards lend their least-used expert slots to the prompt while it runs (`DS4_TP_BORROW`), and the exact long-prompt skip runs on the group (`DS4_YOCO_TP`);
  - the cards' partial sums meet in a pipelined all-reduce (`DS4_AR2`).
- **Writing an answer.** Each step verifies the drafter's guesses in one pass of about 1,600 kernel launches on the lead card. The recipe fuses the small ones (`DS4_HC_FUSE`, `DS4_ROUTE_FUSE`, `DS4_DECODE_TRIM`) and routes the step's all-reduces through the same pipelined kernel (`DS4_AR2_DECODE`). All four give the same bits as the unfused path; the engine compares them at every load.
- **Kept conversations.** A conversation set aside for another is saved to disk (up to 16 of them in 16 GB) and comes back without re-reading its prompt.

## BOSGAME M5 only

The single-box comparison selected Strata HIP UD-Q4_K_XL for Qwen and Strix Halo llama.cpp Vulkan IQ3_XXS for DeepSeek. This table describes the three published Ansible recipes; the measured Qwen Vulkan baseline settings are recorded in [BENCHMARKS.md](BENCHMARKS.md#qwen-context-scaling).

| Layer | **Qwen / Strata HIP UD-Q4_K_XL** | **DeepSeek / Strix Halo llama.cpp Vulkan IQ3_XXS** | DeepSeek / Lucebox ROCm ROCmFPX |
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
