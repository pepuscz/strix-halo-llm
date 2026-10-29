# Strix Halo LLM

![Illustration of the BOSGAME M5 with two OCuLink-connected RX 7900 XTX cards, external USB4 SSD, and a floor-mounted GPU power supply](docs/strix-halo-frankenstein.png)

A **BOSGAME M5 / Ryzen AI Max+ 395** with **two RX 7900 XTX cards** runs DeepSeek-V4.1-Flash-1017 and GLM-5.3-Flash locally. This repository contains the installable recipes, measured results, and pinned sources.

## Dual RX 7900 XTX setup

Both models run on the same hardware ([list below](#hardware)):
- **Two RX 7900 XTX cards**, 48 GB of VRAM together, each on its own PCIe 4.0 ×4 M.2-to-OCuLink link.
- **The M5's Radeon 8060S**, which computes the routed experts the cards can't hold from a pool in system RAM.
- **An NVMe over USB4**, from which the rest of the model streams when a prompt or an answer needs it.

Each model runs one conversation with up to **512K tokens of context**. Values are tokens per second, and every retrieval prompt found all five values.

### DeepSeek-V4.1-Flash-1017 GSQ-RCO IQ2_XS (production)

**Maya DS4 HIP GSQ-RCO IQ2_XS dual RX 7900 XTX** runs [ISTA-DASLab's GSQ-RCO IQ2_XS quant](https://huggingface.co/ISTA-DASLab/DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF) (155 GB, MIT) on Maya v1.1.36's native engine with three Python serving fixes. The hybrid pack reads 522 dense tensors directly from their original Q5_K shards; only the embedding and head use Q8_0. DSpark uses confidence 0.35, suffix drafting is off, and the expert ring keeps its default size.

It passed **30/30 quality cases** (the math_08 reference is corrected to 20/3), with teacher perplexity **7.3686** on 23 sequences of 2,048 tokens. Quality covers 10 coding and 20 maths cases. Every point in the retrieval ladder found all five phrases, through 491,520 input tokens; a separate 520,000-token needle found 5/5. Measured at a 524,288-token allocation with the same benchmark procedure and pinned inputs as the comparison recipes:

| Test | Decode | Prefill |
|---|---:|---:|
| `maya.py --bench` (three 256-token answers; 2K / 8K prompts) | **58.8** | **206 / 525** |
| Public five-phrase prompt, 2K (2,040 input tokens) | 55.9 | 250 |
| 32K (30,720) | 55.1 | 1,108 |
| 128K (122,879) | 53.9 | 1,532 |
| 480K (491,520) | 50.4 | 1,180 |
| Real code, 130,048 tokens: cold / prompt cached | **50.3 / 60.6** | **1,400** |

### DeepSeek-V4.1-Flash-1017 Maya-S IQ2_XXS (alternative)

**Maya DS4 HIP Maya-S IQ2_XXS dual RX 7900 XTX** (`STRIX_SYSTEM=maya-ds4-dual-xtx`) runs the 178 GB model with these settings:
- the two cards as one tensor-parallel group;
- a 95 GB expert pool on the 8060S;
- the DSpark drafter's blocks split across the cards.

It passed **30/30 quality cases**, found all five phrases at every length up to 491,520 input tokens, and found all five values in a 520,000-token deep-needle test. Measured on the installed release at 524,288 tokens:

| Test | Decode | Prefill |
|---|---:|---:|
| `maya.py --bench`, Project Maya's speed test (three 256-token answers; 2K / 8K prompts) | **41.3** | **180 / 482** |
| Public five-phrase prompt, 2K (2,040 input tokens) | 29.7 | 212 |
| 32K (30,720) | 31.7 | 1,053 |
| 128K (122,879) | 31.8 | 1,514 |
| 480K (491,520) | 29.9 | 1,164 |
| Real code, 130,048 tokens: cold / prompt cached | **36.2 / 46.1** | **1,291** |

Decode on the five-phrase prompts is one cold 64-token answer, so it is noisy; `--bench` and the real-code prompt are the steadier decode figures.

The release's engine changes are proposed to Project Maya in [issue #510](https://github.com/mw00/project-maya/issues/510). The `--bench` and real-code rows are that issue's measurements, the changes ported to Maya v1.1.28. They matched the release's own engine within 2 % when the two ran side by side.

A 1,048,576-token allocation also works. Measured on the engine before its decode trims, it found five of five values in a 1,040,000-token prompt and read it at 779 tok/s. Answers there are about 7 % slower than at 524,288, so 512K is the qualified setting.

### GLM-5.3-Flash Maya-M IQ2_S

**Maya HIP Maya-M IQ2_S dual RX 7900 XTX** runs the model with these settings:
- its layers split across the cards;
- the model's own MTP layer drafting.

It passed **28/30 quality cases** (two maths misses). Each row below is one cold request; input tokens are GLM's own counts of the same prompt bytes.

| Test | Decode | Prefill |
|---|---:|---:|
| Public five-phrase prompt, 2K (1,886 input tokens) | 56.0 | 183 |
| 32K (28,517) | 56.8 | 691 |
| 128K (114,093), on the installed 512K service | **54.9** | **891** |
| Real code, the 130,048-token DeepSeek prompt (124,103 GLM tokens): cold / prompt cached | **54.2 / 55.4** | **652** |

The 2K and 32K rows ran at a 131,072-token allocation; the rest at the release's 524,288. Our measurements on more prompt lengths, parallel requests and quality are in [issue #458](https://github.com/mw00/project-maya/issues/458).

[Pinned snapshot of the public 2K/32K/128K results](benchmarks/project-maya-issue-458.json)

### Hardware

| Hardware | Quantity | Connection / role |
|---|---:|---|
| BOSGAME M5 / Sixunited AXB35-02, Ryzen AI Max+ 395, Radeon 8060S, 128 GiB RAM, 2 TB internal SSD | 1 | Host and integrated GPU |
| GIGABYTE Radeon RX 7900 XTX GAMING OC 24G | 1 | External GPU on PCIe 4.0 ×4 M.2-to-OCuLink |
| SAPPHIRE NITRO+ AMD Radeon RX 7900 XTX Vapor-X 24G | 1 | External GPU on PCIe 4.0 ×4 M.2-to-OCuLink |
| [M.2-to-OCuLink SFF-8612 riser and cable kit](https://allegro.pl/oferta/karta-adaptera-riser-oculink-sff-8612-m-2-pci-e-x16-4-0-rtx-5060-kabel-18681419859) | 2 | One kit per external GPU |
| ADATA XPG CORE REACTOR II 1000W | 1 | External GPU power supply |
| Samsung 990 PRO 1 TB M.2 NVMe SSD | 1 | External storage over USB4 |
| [AXAGON EEM2-40G USB4 40 Gbps enclosure](https://www.alza.cz/axagon-eem2-40g-m-2-nvme-ssd-enclosure-usb-c-40gbps-armored-aluminum-d13390080.htm) | 1 | Holds the Samsung SSD |
| Swissten USB 4.0 USB-C 240W 0.5 m cable | 1 | Connects the enclosure to the M5 |

The two GPUs occupy M.2 connections through OCuLink; the external SSD connects over USB4. The exact card, SSD, enclosure, power-supply and cable models come from the owner's order list.

### Our recorded dual-card measurements

Our chart retains the full cold five-phrase retrieval curves for DeepSeek (both quantizations) and GLM. The models read the same text, but their tokenizers count different numbers of tokens; their speeds are **not** a matched model-to-model comparison. Comparisons with Project Maya's own releases are in [issue #510](https://github.com/mw00/project-maya/issues/510) (DeepSeek) and [issue #458](https://github.com/mw00/project-maya/issues/458) (GLM); the chart below records our installation and context-scaling runs, including a different context allocation for the 512K GLM service.

![GLM-5.3-Flash and DeepSeek-V4.1-Flash-1017 reading and answer-writing speeds with two RX 7900 XTX cards and a Radeon 8060S helper](docs/benchmark-dual-xtx.svg)

[DeepSeek measurements](docs/BENCHMARKS.md#dual-rx-7900-xtx-deepseek-v41-flash-1017) · [GLM measurements](docs/BENCHMARKS.md#dual-rx-7900-xtx-glm-53-flash) · [Exact result data](benchmarks/results.json)

### Install

The recipes use the same service name and port; install one at a time. Select the DeepSeek GSQ-RCO recipe below, `STRIX_SYSTEM=maya-ds4-dual-xtx` for DeepSeek on the Maya-S quant, or `STRIX_SYSTEM=maya-glm-dual-xtx` for GLM.

```bash
git clone https://github.com/pepuscz/strix-halo-llm.git
cd strix-halo-llm
cp ansible/inventory/hosts.example.yml ansible/inventory/hosts.yml
$EDITOR ansible/inventory/hosts.yml
python3 -m venv .venv
.venv/bin/pip install --require-hashes -r requirements.lock
export STRIX_SYSTEM=maya-ds4-gsq-dual-xtx
bin/strixctl validate
bin/strixctl install --allow-reboot
bin/strixctl verify
```

The [GLM recipe](ansible/releases/maya-glm-dual-xtx-512k.yml) needs about 240 GB free; the [DeepSeek GSQ-RCO recipe](ansible/releases/maya-ds4-gsq-dual-xtx-512k.yml) about 335 GB (155 GB of shards, the 111 GB Engram file, the 8 GB drafter, an 8 GB converted side file (only embedding and head select it), and the release folder) and the [DeepSeek Maya-S recipe](ansible/releases/maya-ds4-dual-xtx-512k.yml) about 470 GB. Both use kernel `7.0.0-38-generic`, isolated ROCm 7.2.4 userspace, and a rocBLAS build with the [mixed-architecture Tensile fix](https://github.com/ROCm/rocm-libraries/pull/4781). The installer verifies the hardware and pinned artifacts, builds the runtime, and enables `strix-halo-inference.service` on `127.0.0.1:18109`.

## BOSGAME M5 only

These measurements record Qwen3.8-Flash-Next and DeepSeek-V4-Flash-0731 on the M5's Radeon 8060S and 128 GiB RAM, without the external cards. They use **different models, quantizations and hardware** from the dual-card GLM and DeepSeek-V4.1 results above, so the speeds are not a before/after comparison.

The speed test hides five labelled phrases in a long input and asks the model to return them. Every plotted request found all five. Each point is one request; the chart shows input-reading speed above answer-writing speed. A **slot** is capacity for one active conversation. Quality uses 10 coding and 20 maths questions.

| Model | Stack | Conversation limit | Quality | Recipe / measurement settings |
|---|---|---|---:|---|
| Qwen3.8-Flash-Next | **Strata HIP UD-Q4_K_XL** | 4 conversations × 256K tokens | 30/30 | [strata-qwen-q4xl-4x256k.yml](ansible/releases/strata-qwen-q4xl-4x256k.yml) |
| Qwen3.8-Flash-Next | Strix Halo llama.cpp Vulkan UD-Q4_K_XL | 1 conversation, up to 256K in speed tests | 30/30 | [Measurement settings](docs/BENCHMARKS.md#qwen-context-scaling) |
| DeepSeek-V4-Flash-0731 | **Strix Halo llama.cpp Vulkan IQ3_XXS** | 1 conversation × 512K tokens | 30/30 | [vulkan-iq3xxs-512k.yml](ansible/releases/vulkan-iq3xxs-512k.yml) |
| DeepSeek-V4-Flash-0731 | Lucebox ROCm ROCmFPX | 1 conversation × 128K tokens | 29/30 | [rocm-rocmfpx-128k.yml](ansible/releases/rocm-rocmfpx-128k.yml) |

At 114,089 Qwen input tokens, the four-conversation **Strata HIP UD-Q4_K_XL** profile took **168.3 seconds**, versus **329.4 seconds** for the Qwen Vulkan comparison setup (1.96× faster). The four slots were also tested with four simultaneous 228,244-token conversations.

![BOSGAME M5-only Qwen and DeepSeek reading and answer-writing speeds](docs/benchmark.svg)

[Measurements and method](docs/BENCHMARKS.md#bosgame-m5-only) · [Exact result data](benchmarks/results.json)

For the single-box Qwen recipe, omit `STRIX_SYSTEM` in the install commands above; it is the controller default. Select the single-box DeepSeek recipe with `STRIX_SYSTEM=vulkan-iq3xxs` or the Lucebox comparison with `STRIX_SYSTEM=rocm-rocmfpx`.

## Host requirements and operations

The host runs Ubuntu 26.04 LTS with swap and Secure Boot disabled and the BIOS/large-GTT settings in [HOST-PLATFORM.md](docs/HOST-PLATFORM.md). The single-box Qwen recipe uses kernel `7.0.0-31-generic`; its DeepSeek recipes use `7.0.0-29-generic`. The dual-card recipes use `7.0.0-38-generic`.

[OPERATIONS.md](docs/OPERATIONS.md) covers service controls and updates. [ARCHITECTURE.md](docs/ARCHITECTURE.md) describes runtime settings and limits. [SOURCES.md](docs/SOURCES.md) records upstream provenance.

## License

The orchestration, scripts, and documentation are MIT licensed. Models, runtimes, libraries, drivers, and build dependencies retain their upstream licenses and terms. See [NOTICE.md](NOTICE.md).
