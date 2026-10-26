# Strix Halo LLM

![Illustration of the BOSGAME M5 with two OCuLink-connected RX 7900 XTX cards, external USB4 SSD, and a floor-mounted GPU power supply](docs/strix-halo-frankenstein.png)

A **BOSGAME M5 / Ryzen AI Max+ 395** with **two RX 7900 XTX cards** runs GLM-5.3-Flash and DeepSeek-V4.1-Flash-1017 locally. Each card connects through its own PCIe 4.0 ×4 M.2-to-OCuLink link; the M5's Radeon 8060S helps compute experts held in system RAM. This repository contains the installable recipes, measured results, and pinned sources.

## Dual RX 7900 XTX setup

### GLM-5.3-Flash Maya-M IQ2_S

**Maya HIP Maya-M IQ2_S dual RX 7900 XTX** runs one conversation with up to **512K tokens of context**. The model's layers are split across the cards, the Radeon 8060S assists with routed experts, and the model's MTP layer drafts tokens. It found all five values in every cold retrieval test and passed **28/30 quality cases** (two maths misses).

The [public Project Maya benchmark](https://github.com/mw00/project-maya/issues/458) uses the same prompts for Maya v1.1.25 and our branch. **Prefill** is input-reading speed; **decode** is answer-writing speed. Input tokens are the actual GLM token counts, not the context allocation. Each row is one cold request; values are tokens per second.

| Public prompt | Maya v1.1.25 decode / prefill | Our branch decode / prefill |
|---|---:|---:|
| 2K (1,886 input tokens) | 29.0 / 178 | **56.0 / 183** |
| 32K (28,517) | 28.3 / 689 | **56.8 / 691** |
| 128K (114,093) | 27.5 / 906 | **55.8 / 907** |

At the 114,093-token public prompt, answer-writing speed rises from **27.5 to 55.8 tok/s**. On the installed 512K service, that prompt measured **54.9 decode / 891.2 prefill tok/s**; its larger context allocation makes it a separate measurement. The public issue also reports 160K–480K prompt lengths, parallel-request behavior, and the 30-case quality score.

[Pinned snapshot of the public 2K/32K/128K results](benchmarks/project-maya-issue-458.json)

### DeepSeek-V4.1-Flash-1017 Maya-S IQ2_XXS

**Maya DS4 HIP Maya-S IQ2_XXS dual RX 7900 XTX** runs one conversation with up to **512K tokens of context** (524,288).

The model is about 178 GB, and the box has 48 GB of VRAM and 128 GiB of RAM, so it is spread three ways:
- **The cards:** the two cards act as one tensor-parallel group, each holding a share of every layer and of the experts it keeps in VRAM.
- **The Radeon 8060S:** it computes the most-used remaining experts from a 95 GB pool in system RAM.
- **The NVMe:** everything else is read from it when a prompt or an answer needs it.

The DSpark drafter guesses the next few tokens, with its blocks split across the two cards.

The release passed **30/30 quality cases**. It found all five phrases at every measured length, up to 491,520 input tokens, and all five values in a 520,000-token deep-needle test.

Project Maya's own speed test, `maya.py --bench`, is the benchmark its maintainers compare setups with. It writes three 256-token answers and reads a 2,048- and an 8,192-token prompt. All three rows ran on this box with the same model, inputs and context allocation; values are tokens per second.

| `maya.py --bench` | Decode (mean of 3) | Prefill 2K | Prefill 8K |
|---|---:|---:|---:|
| Maya v1.1.28, as released | 37.2 | 70 | 241 |
| Maya v1.1.28 + our eight proposed pull requests | 41.4 | 161 | 486 |
| **This release** | **42.1** | **175** | **473** |

The same public five-phrase prompts as the GLM table, cold, at the 524,288-token allocation. Values are decode / prefill tokens per second; every point found five of five. Decode here is one cold 64-token answer, so it is noisy; `--bench` above is the steadier decode comparison.

| Public prompt | Maya v1.1.28 decode / prefill | This release decode / prefill |
|---|---:|---:|
| 2K (2,040 input tokens) | 39.1 / 87 | **29.7 / 212** |
| 32K (30,720) | 32.4 / 524 | **31.7 / 1,053** |
| 128K (122,879) | 31.7 / 750 | **31.8 / 1,514** |

**The v1.1.28 rows are what that release can do here:**
- `--tp 2` with the expert helper (merged upstream);
- without the uneven split, `--tp 2` gives each card its own layers on Maya-S, so the drafter stays where v1.1.28 places it.

This release runs the engine changes we are proposing to Project Maya, ported to v1.1.28.

A 1,048,576-token allocation also works on this box. Measured on the engine before its decode trims, it found five of five values in a 1,040,000-token prompt and read it at 779 tok/s. Answers there are about 7 % slower than at 524,288, so 512K is the qualified setting.

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

Our chart retains the full cold five-phrase retrieval curves for GLM and DeepSeek. The models read the same text, but their tokenizers count different numbers of tokens; their speeds are **not** a matched model-to-model comparison. The public Maya table above is the benchmark used in [issue #458](https://github.com/mw00/project-maya/issues/458); the chart below records our installation and context-scaling runs, including a different context allocation for the 512K GLM service.

![GLM-5.3-Flash and DeepSeek-V4.1-Flash-1017 reading and answer-writing speeds with two RX 7900 XTX cards and a Radeon 8060S helper](docs/benchmark-dual-xtx.svg)

[GLM measurements](docs/BENCHMARKS.md#dual-rx-7900-xtx-glm-53-flash) · [DeepSeek measurements](docs/BENCHMARKS.md#dual-rx-7900-xtx-deepseek-v41-flash-1017) · [Exact result data](benchmarks/results.json)

### Install

The two recipes use the same service name and port; install one at a time. Select GLM below, or set `STRIX_SYSTEM=maya-ds4-dual-xtx` for DeepSeek.

```bash
git clone https://github.com/pepuscz/strix-halo-llm.git
cd strix-halo-llm
cp ansible/inventory/hosts.example.yml ansible/inventory/hosts.yml
$EDITOR ansible/inventory/hosts.yml
python3 -m venv .venv
.venv/bin/pip install --require-hashes -r requirements.lock
export STRIX_SYSTEM=maya-glm-dual-xtx
bin/strixctl validate
bin/strixctl install --allow-reboot
bin/strixctl verify
```

The [GLM recipe](ansible/releases/maya-glm-dual-xtx-512k.yml) needs about 240 GB free; the [DeepSeek recipe](ansible/releases/maya-ds4-dual-xtx-512k.yml) needs about 470 GB. Both use kernel `7.0.0-38-generic`, isolated ROCm 7.2.4 userspace, and a rocBLAS build with the [mixed-architecture Tensile fix](https://github.com/ROCm/rocm-libraries/pull/4781). The installer verifies the hardware and pinned artifacts, builds the runtime, and enables `strix-halo-inference.service` on `127.0.0.1:18109`.

## BOSGAME M5 only — historical measurements

These measurements record Qwen3.8-Flash-Next and DeepSeek-V4-Flash-0731 on the M5's Radeon 8060S and 128 GiB RAM, without the external cards. They use **different models, quantizations and hardware** from the dual-card GLM and DeepSeek-V4.1 results above, so the speeds are not a before/after comparison.

The speed test hides five labelled phrases in a long input and asks the model to return them. Every plotted request found all five. Each point is one request; the chart shows input-reading speed above answer-writing speed. A **slot** is capacity for one active conversation. Quality uses 10 coding and 20 maths questions.

| Model | Stack | Conversation limit | Quality | Recipe / measurement settings |
|---|---|---|---:|---|
| Qwen3.8-Flash-Next | **Strata HIP UD-Q4_K_XL** | 4 conversations × 256K tokens | 30/30 | [strata-qwen-q4xl-4x256k.yml](ansible/releases/strata-qwen-q4xl-4x256k.yml) |
| Qwen3.8-Flash-Next | Strix Halo llama.cpp Vulkan UD-Q4_K_XL | 1 conversation, up to 256K in speed tests | 30/30 | [Measurement settings](docs/BENCHMARKS.md#qwen-context-scaling) |
| DeepSeek-V4-Flash-0731 | **Strix Halo llama.cpp Vulkan IQ3_XXS** | 1 conversation × 512K tokens | 30/30 | [vulkan-iq3xxs-512k.yml](ansible/releases/vulkan-iq3xxs-512k.yml) |
| DeepSeek-V4-Flash-0731 | Lucebox ROCm ROCmFPX | 1 conversation × 128K tokens | 29/30 | [rocm-rocmfpx-128k.yml](ansible/releases/rocm-rocmfpx-128k.yml) |

At 114,089 Qwen input tokens, the four-conversation **Strata HIP UD-Q4_K_XL** profile took **168.3 seconds**, versus **329.4 seconds** for the Qwen Vulkan comparison setup (1.96× faster). The four slots were also tested with four simultaneous 228,244-token conversations.

![Historical BOSGAME-only Qwen and DeepSeek reading and answer-writing speeds](docs/benchmark.svg)

[Historical measurements and method](docs/BENCHMARKS.md) · [Exact result data](benchmarks/results.json)

For the single-box Qwen recipe, omit `STRIX_SYSTEM` in the install commands above; it is the controller default. Select the single-box DeepSeek recipe with `STRIX_SYSTEM=vulkan-iq3xxs` or the Lucebox comparison with `STRIX_SYSTEM=rocm-rocmfpx`.

## Host requirements and operations

The host runs Ubuntu 26.04 LTS with swap and Secure Boot disabled and the BIOS/large-GTT settings in [HOST-PLATFORM.md](docs/HOST-PLATFORM.md). The single-box Qwen recipe uses kernel `7.0.0-31-generic`; its DeepSeek recipes use `7.0.0-29-generic`. The dual-card recipes use `7.0.0-38-generic`.

[OPERATIONS.md](docs/OPERATIONS.md) covers service controls and updates. [ARCHITECTURE.md](docs/ARCHITECTURE.md) describes runtime settings and limits. [SOURCES.md](docs/SOURCES.md) records upstream provenance.

## License

The orchestration, scripts, and documentation are MIT licensed. Models, runtimes, libraries, drivers, and build dependencies retain their upstream licenses and terms. See [NOTICE.md](NOTICE.md).
