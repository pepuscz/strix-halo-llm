# Strix Halo LLM

![Illustration of the BOSGAME M5 with two RX 7900 XTX cards connected by OCuLink and an external USB4 SSD](docs/strix-halo-frankenstein.png)

*Illustration of the [dual RX 7900 XTX setup](#dual-rx-7900-xtx-setup).*

Ansible recipes and measured performance for running Qwen and DeepSeek locally on a **128 GiB AMD Ryzen AI Max+ 395 / Radeon 8060S** Strix Halo box (BOSGAME M5 / Sixunited AXB35-02).

**Winning setup for Qwen:** Qwen3.8-Flash-Next with **Strata HIP UD-Q4_K_XL**, up to **four simultaneous conversations**, each with **256K tokens of context**. It passes all **30 quality tests**.

**Winning setup for DeepSeek:** DeepSeek-V4-Flash-0731 with **Strix Halo llama.cpp Vulkan IQ3_XXS**, **one conversation with 512K tokens of context**. It passes all **30 quality tests**.

On the long-text test (114,089 input tokens), the winning Qwen recipe takes **168.3 seconds versus 329.4 seconds** for the Qwen Vulkan comparison setup: **1.96× faster**.

## Setups in the comparison

Winning setups are bold.

| Model | Stack | Conversation limits | Quality tests passed | Recipe / measurement settings |
|---|---|---|---:|---|
| Qwen3.8-Flash-Next | **Strata HIP UD-Q4_K_XL** | 4 conversations × 256K tokens | 30/30 | [strata-qwen-q4xl-4x256k.yml](ansible/releases/strata-qwen-q4xl-4x256k.yml) |
| Qwen3.8-Flash-Next | Strix Halo llama.cpp Vulkan UD-Q4_K_XL | 1 conversation, up to 256K tokens in the speed tests | 30/30 | [Measurement settings](docs/BENCHMARKS.md#qwen-context-scaling) |
| DeepSeek-V4-Flash-0731 | **Strix Halo llama.cpp Vulkan IQ3_XXS** | 1 conversation × 512K tokens | 30/30 | [vulkan-iq3xxs-512k.yml](ansible/releases/vulkan-iq3xxs-512k.yml) |
| DeepSeek-V4-Flash-0731 | Lucebox ROCm ROCmFPX | 1 conversation × 128K tokens | 29/30 | [rocm-rocmfpx-128k.yml](ansible/releases/rocm-rocmfpx-128k.yml) |

Tokens are the pieces of text a model reads and writes. The context limit is the total length of the input and conversation history the model can keep for a conversation. Quality is measured with 10 coding and 20 maths questions.

## Benchmarks

The speed test places five labelled phrases in a long text—for example, `BOSGAME_ALPHA: violet canoe`—then asks the model to find them. Every run shown returned all five phrases correctly.

The top chart shows how quickly each setup reads the input. The bottom chart shows how quickly it writes the answer. Higher is better. Each dot measures one request at the input length shown on the horizontal axis.

![Qwen and DeepSeek reading and answer-writing speeds at different input lengths, measured one request at a time](docs/benchmark.svg)

[Full measurements and test method](docs/BENCHMARKS.md) · [Exact software versions, settings, and result data](benchmarks/results.json)

## Install

```bash
git clone https://github.com/pepuscz/strix-halo-llm.git
cd strix-halo-llm
cp ansible/inventory/hosts.example.yml ansible/inventory/hosts.yml
$EDITOR ansible/inventory/hosts.yml
python3 -m venv .venv
.venv/bin/pip install --require-hashes -r requirements.lock

# Install the winning Qwen setup (default selection).
bin/strixctl validate
bin/strixctl install --allow-reboot
bin/strixctl verify
```

For the winning DeepSeek setup, set `STRIX_SYSTEM=vulkan-iq3xxs` before running the same commands. The Lucebox comparison recipe is selectable with `STRIX_SYSTEM=rocm-rocmfpx`. Keep that selection for subsequent service controls.

The installer verifies the hardware and kernel, downloads publisher artifacts with pinned hashes, prepares the runtime and model, and installs boot-enabled `strix-halo-inference.service`. The API listens on `127.0.0.1:18109`. Strata exposes OpenAI chat completions and responses, plus Anthropic messages.

## Dual RX 7900 XTX setup

A separate setup for the same box with two **AMD Radeon RX 7900 XTX** cards added, each on its own PCIe 4.0 x4 link (M.2 to OCuLink). It is not part of the single-box comparison above.

| Hardware | Quantity | Connection / role |
|---|---:|---|
| BOSGAME M5 / Sixunited AXB35-02, Ryzen AI Max+ 395, Radeon 8060S, 128 GiB RAM | 1 | Host and integrated GPU |
| GIGABYTE Radeon RX 7900 XTX GAMING OC 24G | 1 | External GPU on its own PCIe 4.0 x4 M.2-to-OCuLink link |
| SAPPHIRE NITRO+ AMD Radeon RX 7900 XTX Vapor-X 24G | 1 | External GPU on its own PCIe 4.0 x4 M.2-to-OCuLink link |
| [M.2-to-OCuLink SFF-8612 riser and cable kit](https://allegro.pl/oferta/karta-adaptera-riser-oculink-sff-8612-m-2-pci-e-x16-4-0-rtx-5060-kabel-18681419859) | 2 | One adapter and cable per RX 7900 XTX |
| ADATA XPG CORE REACTOR II 1000W | 1 | External GPU power supply |
| Samsung 990 PRO 1 TB M.2 NVMe SSD | 1 | External storage in the USB4 enclosure |
| [AXAGON EEM2-40G USB4 40 Gbps enclosure](https://www.alza.cz/axagon-eem2-40g-m-2-nvme-ssd-enclosure-usb-c-40gbps-armored-aluminum-d13390080.htm) | 1 | Connects the Samsung SSD to the M5 over USB-C |
| Swissten USB 4.0 USB-C 240W 0.5 m cable | 1 | USB4 cable for the external SSD enclosure |

The card, SSD, enclosure, power supply, and USB4 cable model names come from the owner's order list. The two OCuLink kits are the linked riser-and-cable listing.

**DeepSeek-V4.1-Flash-1017 with Maya DS4 HIP Maya-S IQ2_XXS dual RX 7900 XTX**, one conversation with **256K tokens of context**. The two cards split the model in tensor parallel, the Radeon 8060S serves routed experts beside them, and a DSpark drafter speculates with its blocks split across the two cards. It passes all **30 quality tests** (measured at 128K) and found all five phrases at every length of the speed test up to 245,760 tokens (50/50).

The chart uses the same five-phrase retrieval test as above, with a fresh model load and no cached input at each point. The top panel shows input-reading speed; the bottom shows answer-writing speed.

![DeepSeek-V4.1-Flash-1017 reading and answer-writing speeds with two RX 7900 XTX cards and a Radeon 8060S helper](docs/benchmark-dual-xtx.svg)

[All ten measurements and test method](docs/BENCHMARKS.md#dual-rx-7900-xtx-deepseek-v41-flash-1017) · [Exact result data](benchmarks/results.json)

```bash
export STRIX_SYSTEM=maya-ds4-dual-xtx
bin/strixctl validate
bin/strixctl install --allow-reboot
bin/strixctl verify
```

The recipe is [maya-ds4-dual-xtx-256k.yml](ansible/releases/maya-ds4-dual-xtx-256k.yml). It builds the pinned engine tag, AMD's ROCm 7.2.4 userspace (isolated, nothing installed system-wide), and rocBLAS with the [per-architecture Tensile fix](https://github.com/ROCm/rocm-libraries/pull/4781) that mixed gfx1100/gfx1151 processes need. It needs kernel `7.0.0-38-generic` and about 470 GB free. The from-scratch install ran end to end at 128K on the previous engine tag; this tag adds one engine commit (the drafter placement) and one environment variable, and the 256K setting differs only in the context size.

## Host requirements

Ubuntu 26.04 LTS, 128 GiB RAM, swap and Secure Boot disabled, and the BIOS/large-GTT settings in [HOST-PLATFORM.md](docs/HOST-PLATFORM.md). Qwen uses kernel `7.0.0-31-generic` and requires 220 GB free on `/`; DeepSeek uses `7.0.0-29-generic` and requires 120 GB free.

Every recipe applies 120 W package limits and model-scoped cooling. Qwen uses CPU boost off, GPU DPM auto, and systemd memory limits of 123G/125G. In the concurrency test, Qwen answered four long prompts at the same time, kept the conversations separate, and answered a follow-up in each conversation.

[OPERATIONS.md](docs/OPERATIONS.md) covers service controls and updates. [ARCHITECTURE.md](docs/ARCHITECTURE.md) describes the runtime settings and current limits. [SOURCES.md](docs/SOURCES.md) records upstream provenance.

## License

The orchestration, scripts, and documentation are MIT licensed. Models, runtimes, libraries, drivers, and build dependencies retain their upstream licenses and terms. See [NOTICE.md](NOTICE.md).
