# Sources and provenance

## Strata HIP UD-Q4_K_XL / Qwen

| Component | Pinned source |
|---|---|
| Runtime | [Niko1221/Strata](https://github.com/Niko1221/Strata), `v0.1.40`, commit `1735d6471df29b42c26170efaac1f1446a58640f`, tree `59acc26caded6c6c949f909bb7e4b96ff720c83e` |
| GGML | [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp/tree/3cf03257f219afbe7334045ff7c6a06ac68c627d), commit `3cf03257f219afbe7334045ff7c6a06ac68c627d`, archive SHA-256 pinned |
| ROCm SDK | [AMD gfx1151 ROCm 7.14.1 archive](https://repo.amd.com/rocm/tarball-multi-arch/therock-dist-linux-gfx1151-7.14.1.tar.gz), byte size and SHA-256 pinned |
| Target | [unsloth/Qwen3.8-Flash-Next-GGUF](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF), revision `c8b5954a88c2775c546b92593eda40ea041d3176`, UD-Q4_K_XL |
| MTP tensors | [Qwen/Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next), revision `de4b8e4d43b917e7706784d8bb445c9af86a3540`, 31 sealed tensor hashes |
| Host build | GCC 15.2.0, CMake 4.2.3, Python 3.14; pinned Ubuntu package versions |
| Packing tools | Pinned upstream tools and hash-locked Python dependencies |

[strata-qwen-q4xl-4x256k.yml](../ansible/releases/strata-qwen-q4xl-4x256k.yml) records every source, download, generated-tensor, and tokenizer identity. A portable installation verifies pinned inputs, the HIP self-test, and derived tensor hashes, then seals its local executable and serving configuration. Its reference executable hash identifies the measured build; absolute build paths can change a rebuilt executable's hash.

The Qwen Vulkan comparison uses official `strix-halo-llamacpp` v0.7.6.1, payload `b02cb35f2`, and the same UD-Q4_K_XL target revision. Its archive, server, MTP draft, and measurement settings are recorded in [results.json](../benchmarks/results.json).

## Strix Halo llama.cpp Vulkan IQ3_XXS

| Component | Pinned source |
|---|---|
| Runtime | [`Nathanw1014/strix-halo-llamacpp`](https://github.com/Nathanw1014/strix-halo-llamacpp), official release `v0.7.0`, commit `95c828eeb315a7ba6f50fcf632c29f8de2ec1a6e` |
| Target | [`unsloth/DeepSeek-V4-Flash-0731-GGUF`](https://huggingface.co/unsloth/DeepSeek-V4-Flash-0731-GGUF), revision `fbbb5b93fb787c21338159b0af3318bb3f4d9768`, UD-IQ3_XXS |
| Draft | [`alessandrobologna/DeepSeek-V4-Flash-DSpark-Drafter-GGUF`](https://huggingface.co/alessandrobologna/DeepSeek-V4-Flash-DSpark-Drafter-GGUF), revision `824190cb58c1469a603d9686107dd85ef11a5d51` |
| Vulkan loader | Ubuntu `libvulkan1` `1.4.341.0-1`, extracted inside the immutable release |

The exact upstream runtime archive, manifest, launcher, executable, Vulkan
backend, loader, and model identities are in
[`vulkan-iq3xxs-512k.yml`](../ansible/releases/vulkan-iq3xxs-512k.yml).

## Lucebox ROCm ROCmFPX

| Component | Pinned source |
|---|---|
| Runtime | [`Luce-Org/lucebox`](https://github.com/Luce-Org/lucebox), unmodified commit `5eb4fbe95e13944ad964bd7e42980bca518e3d5c` from [PR 667](https://github.com/Luce-Org/lucebox/pull/667) |
| Block-Sparse-Attention submodule | commit `49d6c39e4dc0303442cda3bb758b3925d4399c49` |
| rocWMMA headers | [`ROCm/rocWMMA`](https://github.com/ROCm/rocWMMA), tag `rocm-7.1.1`, commit `1ab208f49945c38626b79e3f0c284d65ac44a781` |
| Target | [`Lucebox/DeepSeek-V4-Flash-0731-ROCmFP3`](https://huggingface.co/Lucebox/DeepSeek-V4-Flash-0731-ROCmFP3), revision `39745d3f6f4b92ff1d764ada79a73616bc8903a5`, ROCmFPX MIX |
| Draft | [`Lucebox/DeepSeek-V4-Flash-0731-DSpark-GGUF`](https://huggingface.co/Lucebox/DeepSeek-V4-Flash-0731-DSpark-GGUF), revision `8e8bbf5bdb384b6e867d01ad3215be70b1d920c5` |

The enabled execution paths are listed in
[ARCHITECTURE.md](ARCHITECTURE.md#lucebox-runtime). The clean source-tree
identity, pinned Ubuntu ROCm package versions, absolute build paths, compiler
flags, output binary identity, and model identities are in
[`rocm-rocmfpx-128k.yml`](../ansible/releases/rocm-rocmfpx-128k.yml).

## Maya DS4 HIP Maya-S IQ2_XXS dual RX 7900 XTX

| Component | Pinned source |
|---|---|
| Runtime | [`pepuscz/project-maya`](https://github.com/pepuscz/project-maya/tree/maya-ds4-fd-dspark-128k-20261022), tag `maya-ds4-fd-dspark-128k-20261022`, commit `62e4b2afda2d17d777967a46bfff131d32f51b16`: [`mw00/project-maya`](https://github.com/mw00/project-maya) `v1.1.21` plus the dual-card tensor-parallel, expert-helper, and DSpark memory-cap changes |
| Pack tool | `pepuscz/project-maya` commit `1b8f5ec2bc4d1e4ba18c3d538fa5d44470c7296c` (`tools/ds4/pack_gguf.py`, the tool the qualified pack came from) |
| GGML | [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp/tree/3cf03257f219afbe7334045ff7c6a06ac68c627d), commit `3cf03257f219afbe7334045ff7c6a06ac68c627d`, archive SHA-256 and tree fingerprint pinned |
| ROCm | AMD ROCm 7.2.4 runfile installer for Ubuntu 24.04 (`repo.radeon.com`), byte size and SHA-256 pinned; 97 userspace components copied into the release; Ubuntu 24.04 `libicu74` and `libxml2` extracted for its linker |
| rocBLAS | [`ROCm/rocm-libraries`](https://github.com/ROCm/rocm-libraries) tag `rocm-7.2.4`, commit `dabb6df2b988f8eabed1e2fecefaaf4e818bc7ef`, with [PR 4781](https://github.com/ROCm/rocm-libraries/pull/4781) backported ([patch](../patches/rocblas-rocm724-4781-per-gfx-backport.patch)) |
| Target | [`peasantsmith/DeepSeek-V4.1-Flash-1017-Maya-GGUF`](https://huggingface.co/peasantsmith/DeepSeek-V4.1-Flash-1017-Maya-GGUF), revision `26c6aeaf5ecce88fe47103f780279bcc6f1f0d9b`, Maya-S IQ2_XXS (4 shards) |
| Engram | [`unsloth/DeepSeek-V4.1-Flash-1017-GGUF`](https://huggingface.co/unsloth/DeepSeek-V4.1-Flash-1017-GGUF), revision `c991b28e7c109eed10a55075ddb46f830b5b3059`, `UD-Q8_K_XL` shard 8 of 9 |
| Draft | `peasantsmith/DeepSeek-V4.1-Flash-1017-Maya-GGUF`, revision `276e0badcfb4a6d8f6c2b9d4da1b468cd339c221`, DSpark |
| Expert profile | Routing counts learned on the qualified host ([file](../ansible/roles/maya_runtime/files/expert-profile-maya-s.bin), SHA-256 pinned); the engine keeps updating its copy while serving |

[`maya-ds4-dual-xtx-256k.yml`](../ansible/releases/maya-ds4-dual-xtx-256k.yml) records every identity. The engine compiles for the host CPU, so an installation seals its own executable; the pack is checked against the qualified pack's hashes.

## Shared host components

| Component | Pinned source |
|---|---|
| RyzenAdj | [`FlyGoat/RyzenAdj`](https://github.com/FlyGoat/RyzenAdj), commit `5775fc3e6dbb25c7030ee2d100a1bdd6e8bf2d0a` |
| AXB35 driver | [`cmetz/ec-su_axb35-linux`](https://github.com/cmetz/ec-su_axb35-linux), commit `7a9f372edcaa99e562dece70204c4f609692a778` |

This repository downloads models and upstream runtime archives directly from
their publishers. The Vulkan system has no repository-owned binary
overlay.
