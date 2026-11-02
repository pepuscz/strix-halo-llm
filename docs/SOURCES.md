# Sources and provenance

## Maya HIP Maya-M IQ2_S dual RX 7900 XTX

Every source and setting below is pinned from the qualified host. The
from-scratch 512K installation and verification are recorded in the release
manifest.

| Component | Pinned source |
|---|---|
| Runtime | [`pepuscz/project-maya`](https://github.com/pepuscz/project-maya) commit `3e054700b4fbfc9d31499f4f1c5f2a1c0399b9b4`, [tag `maya-glm-dual-xtx-512k-20261024`](https://github.com/pepuscz/project-maya/tree/maya-glm-dual-xtx-512k-20261024), tree `b5d18000fc985e468dbcda999e868b206fb52b5f`: [`mw00/project-maya`](https://github.com/mw00/project-maya) `v1.1.25` (commit `94878e25e3860e22ea29b4fff506ade8c477a57b`) plus the expert helper beside a layer split, its load-time self-check, the tuned RDNA IQ2_S expert kernel and the take-two decode-attention kernels for the indexer scores and MLA |
| Pack tool | The engine source's own `tools/iq_pack.py` (SHA-256 pinned), run without a GPU with `--compat-bf16` |
| Python | 3.14 with the engine's packages hash-locked ([lock](../ansible/roles/maya_runtime/files/requirements-glm.lock)): the wheels the qualified host's pip cache held for its installed versions |
| GGML | [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp/tree/3cf03257f219afbe7334045ff7c6a06ac68c627d), commit `3cf03257f219afbe7334045ff7c6a06ac68c627d`, archive SHA-256 and tree fingerprint pinned |
| ROCm | The same AMD ROCm 7.2.4 runfile userspace as the DeepSeek GSQ-RCO recipe below |
| rocBLAS | The same `rocm-7.2.4` rocBLAS as the DeepSeek GSQ-RCO recipe below |
| Target | [`peasantsmith/GLM-5.3-Flash-Maya-GGUF`](https://huggingface.co/peasantsmith/GLM-5.3-Flash-Maya-GGUF), revision `f16ee4ba50d8fd2bb726ea1862ca6ca14ba188da`, Maya-M IQ2_S (3 shards) |
| Draft | None: the engine drafts with the model's own MTP layer |
| Expert profile | `data/expert-profile-glm.bin` in the engine source, SHA-256 and size pinned; the engine only reads it |

[`maya-glm-dual-xtx-512k.yml`](../ansible/releases/maya-glm-dual-xtx-512k.yml) records every identity. The engine compiles for the host CPU, so an installation seals its own executable; the pack is checked against the qualified pack's hashes, and its `compat-bf16.json`, which names the model shard it was packed from, against a digest with that path normalized.

## Maya DS4 HIP GSQ-RCO IQ2_XS dual RX 7900 XTX

| Component | Pinned source |
|---|---|
| Runtime | [pepuscz/project-maya](https://github.com/pepuscz/project-maya/tree/maya-ds4-gsq-idxtc-512k-20261102), annotated tag `maya-ds4-gsq-idxtc-512k-20261102` (object `1c2025b2e909d136a179cca27d2db4b90e676d7e`), commit `8463e3c9c1e843dc13aeca5fea6c71374d26c6a6`, tree `435d7df008729debc4c4da71f6b27a4334ffc673`: [upstream v1.1.48](https://github.com/mw00/project-maya/tree/v1.1.48) plus the RDNA 3 indexer. `DS4_INDEX_TC=1`; explicit 32,768-token prefill chunks |
| Pack tool | Commit `c87b26c96031f11b5ae1df126629aea200698a8c`’s `tools/ds4/pack_gguf.py` (the unchanged v1.1.36 pack tool), then [`convert-dense-q8_0.py`](../ansible/roles/maya_runtime/files/convert-dense-q8_0.py), both SHA-256 pinned. The hybrid retains 522 original Q5_K dense tensors and uses Q8_0 only for `embed.weight` and `head.weight`. The complete qualified side-file layout (8,236,072,960 bytes) is reproduced; the other converted entries are unused. Routed experts and Engram tables stay in the downloaded files. [Pack metadata equivalence](../benchmarks/gsq-pack-equivalence.json) |
| GGML | [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp/tree/3cf03257f219afbe7334045ff7c6a06ac68c627d), commit `3cf03257f219afbe7334045ff7c6a06ac68c627d`, archive SHA-256 and tree fingerprint pinned |
| ROCm | AMD ROCm 7.2.4 runfile installer for Ubuntu 24.04 (`repo.radeon.com`), byte size and SHA-256 pinned; 97 userspace components copied into the release; Ubuntu 24.04 `libicu74` and `libxml2` extracted for its linker |
| rocBLAS | [`ROCm/rocm-libraries`](https://github.com/ROCm/rocm-libraries) tag `rocm-7.2.4`, commit `dabb6df2b988f8eabed1e2fecefaaf4e818bc7ef`, with [PR 4781](https://github.com/ROCm/rocm-libraries/pull/4781) backported ([patch](../patches/rocblas-rocm724-4781-per-gfx-backport.patch)) |
| Target | [`ISTA-DASLab/DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF`](https://huggingface.co/ISTA-DASLab/DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF), revision `653a9874aa38c356233c5f3cc8c96b19a43b57eb`, IQ2_XS (4 shards, 155 GB; MIT, as the base model). Made with GSQ (Gumbel-Softmax quantization) and RCO (Riemannian constrained optimization) by IST Austria's Distributed Algorithms and Systems Lab; its card asks that both papers be cited |
| Engram | The same repository and revision, `DeepSeek-V4.1-Flash-Engram-IQ4_NL.gguf` (110.6 GB) |
| Draft | `peasantsmith/DeepSeek-V4.1-Flash-1017-Maya-GGUF`, revision `276e0badcfb4a6d8f6c2b9d4da1b468cd339c221`, DSpark |
| Expert profile | The frozen [profile seed](../ansible/roles/maya_runtime/files/expert-profile-maya-s.bin) used for qualification (SHA-256 pinned); every fresh load starts from it |
| Benchmark inputs | The [fixed-input driver](../benchmarks/maya_bench.py) and [token IDs](../benchmarks/maya-bench-inputs.json), SHA-256 `0c9ad680a6081cc8d4894d019db357b501c560d0d1721469e5a1b9dc41039bcf`. Questions and input text come from Project Maya `v1.1.28` at `6afa525bbabc3a8f5fd165f89e9bc72155d9bd39`; all 21 source-document digests verified. [MIT license](../benchmarks/PROJECT-MAYA-LICENSE) |

[`maya-ds4-gsq-dual-xtx-512k.yml`](../ansible/releases/maya-ds4-gsq-dual-xtx-512k.yml) records every identity. The pack is checked against the qualified pack's hashes (its `tensors.txt` after the conversion included); the converted side file is checked at its pinned size and sealed with the pack by the digest the install produced.

## Benchmark-only comparisons

Maya-S IQ2_XXS and Maya-XS v2 IQ1_S use the GSQ production engine tag above and its environment. These entries are measurements, with no installer. The file digests below are published Hugging Face LFS oids at revision `c33d87b8c7a3b7d55e71324dc82395587a870b0b`; sizes match the verified download receipts.

Source: [peasantsmith/DeepSeek-V4.1-Flash-1017-Maya-GGUF](https://huggingface.co/peasantsmith/DeepSeek-V4.1-Flash-1017-Maya-GGUF/tree/c33d87b8c7a3b7d55e71324dc82395587a870b0b).

| File | Bytes | SHA-256 / LFS oid |
|---|---:|---|
| `Maya-S/DeepSeek-V4.1-Flash-1017-Maya-S-IQ2_XXS-00001-of-00006.gguf` | 47,887,697,312 | `1f3437f57042e69f94c141ffbcba0d5610dab63feb07244fb468be4940d6763f` |
| `Maya-S/DeepSeek-V4.1-Flash-1017-Maya-S-IQ2_XXS-00002-of-00006.gguf` | 47,669,578,400 | `66501fee8702ffd54e6f065323ab54bb3150d20b10b01922c589e7462c7b5ba6` |
| `Maya-S/DeepSeek-V4.1-Flash-1017-Maya-S-IQ2_XXS-00003-of-00006.gguf` | 47,103,347,360 | `3195b23f33337c46a07c48583946d99147c3635412bc4adc6acdc4cf42bf30ad` |
| `Maya-S/DeepSeek-V4.1-Flash-1017-Maya-S-IQ2_XXS-00004-of-00006.gguf` | 35,532,532,032 | `d60dba35fac9601cd5c6026439dd980c457a5bb1c009192ea539b220108ea0db` |
| `Maya-XS/DeepSeek-V4.1-Flash-1017-Maya-XS-IQ1_S-00004-of-00005.gguf` | 80,641,295,472 | `0d93315942c523d82f6dbc0a6e0e1751548e309f3963f96b82f92e8f9bc52e36` |
| `Maya-XS/DeepSeek-V4.1-Flash-1017-Maya-XS-IQ1_S-00005-of-00005.gguf` | 80,643,503,412 | `39bbc8cde8b17604fed9a7ba7fc6bc9c5e72e34733657943ac049b4b9ca2d340` |
| `dspark/dspark.bin` | 7,967,616,768 | `42df65159f980a9189d80597e42b30012c7b10e0dd385a47051f3b2fd659bb7b` |
| `Maya-XS/DeepSeek-V4.1-Flash-1017-Maya-XS-v2-IQ1_S-00001-of-00003.gguf` | 47,993,866,016 | `9d92dd13d4603dbf07720845419963693f4c07ae098e55a5aae2f207dd44d04d` |
| `Maya-XS/DeepSeek-V4.1-Flash-1017-Maya-XS-v2-IQ1_S-00002-of-00003.gguf` | 47,421,853,600 | `b7f26bae6d6fccfb256c911f645289c0aec8459766ef83f6a04d7ed47c7e06c8` |
| `Maya-XS/DeepSeek-V4.1-Flash-1017-Maya-XS-v2-IQ1_S-00003-of-00003.gguf` | 21,422,979,296 | `62b98172562543126204fa2ff18f7d72d75353445ff93f4135d037355b409f35` |
| `dspark/dspark-xs2.bin` | 4,251,725,568 | `8dfe21082a6cb320f334fddb454630c241c6d44e0463eef4f8b0b07334511779` |

Both archived packs record tools fingerprint `4cc23a1faf4595ca`, matching the official source's `source_hash(DS4_GGUF_PACK_TOOLS)`. Its two inputs are `tools/ds4/pack_gguf.py` (SHA-256 `f45c5c16cbd59d5aa1ad5b22d07f082818d4d806cfa9254b66bc173d9a458859`) and `tools/ds4/chat_template.jinja` (`e9f7db2fa773233bdfd0c5f21cf5d300283aad08fd6d056593634a5a375306fa`). Both packs use official v1.1.48 `tools/ds4/pack_gguf.py` at `465a981579ff5e91b19ff023721c6661f3c6030b`. The Q6_K pair supplies Engram; vision is retained. Packing arguments below use relative paths.

Maya DS4 HIP Maya-S IQ2_XXS dual RX 7900 XTX

```bash
python3 tools/ds4/pack_gguf.py --model Maya-S --out pack --vision vision --engram Engram-Q6_K --drafter dspark/dspark.json --shards DeepSeek-V4.1-Flash-1017-Maya-S-IQ2_XXS-00001-of-00006.gguf DeepSeek-V4.1-Flash-1017-Maya-S-IQ2_XXS-00002-of-00006.gguf DeepSeek-V4.1-Flash-1017-Maya-S-IQ2_XXS-00003-of-00006.gguf DeepSeek-V4.1-Flash-1017-Maya-S-IQ2_XXS-00004-of-00006.gguf --without DeepSeek-V4.1-Flash-1017-Maya-S-IQ2_XXS-00005-of-00006.gguf DeepSeek-V4.1-Flash-1017-Maya-S-IQ2_XXS-00006-of-00006.gguf
```

Maya DS4 HIP Maya-XS v2 IQ1_S dual RX 7900 XTX

```bash
python3 tools/ds4/pack_gguf.py --model Maya-XS-v2 --out pack --vision vision --engram Engram-Q6_K --drafter dspark/dspark-xs2.json --shards DeepSeek-V4.1-Flash-1017-Maya-XS-v2-IQ1_S-00001-of-00003.gguf DeepSeek-V4.1-Flash-1017-Maya-XS-v2-IQ1_S-00002-of-00003.gguf DeepSeek-V4.1-Flash-1017-Maya-XS-v2-IQ1_S-00003-of-00003.gguf
```

## BOSGAME M5 only

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

## Shared host components

| Component | Pinned source |
|---|---|
| RyzenAdj | [`FlyGoat/RyzenAdj`](https://github.com/FlyGoat/RyzenAdj), commit `5775fc3e6dbb25c7030ee2d100a1bdd6e8bf2d0a` |
| AXB35 driver | [`cmetz/ec-su_axb35-linux`](https://github.com/cmetz/ec-su_axb35-linux), commit `7a9f372edcaa99e562dece70204c4f609692a778` |

This repository downloads models and upstream runtime archives directly from
their publishers. The Vulkan system has no repository-owned binary
overlay.
