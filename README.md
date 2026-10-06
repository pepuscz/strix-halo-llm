# Strix Halo LLM

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

## Host requirements

Ubuntu 26.04 LTS, 128 GiB RAM, swap and Secure Boot disabled, and the BIOS/large-GTT settings in [HOST-PLATFORM.md](docs/HOST-PLATFORM.md). Qwen uses kernel `7.0.0-31-generic` and requires 220 GB free on `/`; DeepSeek uses `7.0.0-29-generic` and requires 120 GB free.

Every recipe applies 120 W package limits and model-scoped cooling. Qwen uses CPU boost off, GPU DPM auto, and systemd memory limits of 123G/125G. In the concurrency test, Qwen answered four long prompts at the same time, kept the conversations separate, and answered a follow-up in each conversation.

[OPERATIONS.md](docs/OPERATIONS.md) covers service controls and updates. [ARCHITECTURE.md](docs/ARCHITECTURE.md) describes the runtime settings and current limits. [SOURCES.md](docs/SOURCES.md) records upstream provenance.

## License

The orchestration, scripts, and documentation are MIT licensed. Models, runtimes, libraries, drivers, and build dependencies retain their upstream licenses and terms. See [NOTICE.md](NOTICE.md).
