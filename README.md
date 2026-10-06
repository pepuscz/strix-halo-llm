# Strix Halo LLM

Qualified local LLM setups, benchmarks, and pinned Ansible recipes for a **128 GiB AMD Ryzen AI Max+ 395 / Radeon 8060S** Strix Halo box (BOSGAME M5 / Sixunited AXB35-02).

**Winning setup for Qwen:** Qwen3.8-Flash-Next with **Strata HIP UD-Q4_K_XL**, four 256K slots, and 30/30 quality.

**Winning setup for DeepSeek:** DeepSeek-V4-Flash-0731 with **Strix Halo llama.cpp Vulkan IQ3_XXS**, one 512K slot, and 30/30 quality.

The matched 128K Qwen retrieval workload completes in **168.3 seconds versus 329.4 seconds** with the Qwen Vulkan baseline: **1.96× faster** with four slots.

## Setups in the comparison

The table and chart show the same four setups: one winning setup and one comparison baseline for each model.

| Selection | Model | Stack | Context | Quality | Recipe / measurement settings |
|---|---|---|---:|---:|---|
| **Winning setup for Qwen** | Qwen3.8-Flash-Next | **Strata HIP UD-Q4_K_XL** | **4 × 262,144** | **30/30** | [strata-qwen-q4xl-4x256k.yml](ansible/releases/strata-qwen-q4xl-4x256k.yml) |
| Qwen comparison baseline | Qwen3.8-Flash-Next | Strix Halo llama.cpp Vulkan UD-Q4_K_XL | 1 × 262,144 measured curve | 30/30 | [Measurement settings](docs/BENCHMARKS.md#qwen-context-scaling) |
| **Winning setup for DeepSeek** | DeepSeek-V4-Flash-0731 | **Strix Halo llama.cpp Vulkan IQ3_XXS** | **1 × 524,288** | **30/30** | [vulkan-iq3xxs-512k.yml](ansible/releases/vulkan-iq3xxs-512k.yml) |
| DeepSeek comparison baseline | DeepSeek-V4-Flash-0731 | Lucebox ROCm ROCmFPX | 1 × 131,072 | 29/30 | [rocm-rocmfpx-128k.yml](ansible/releases/rocm-rocmfpx-128k.yml) |

## Benchmarks

![Matched Qwen and DeepSeek single-session input-processing and generation throughput on Strix Halo](docs/benchmark.svg)

All retrieval points recover five of five values exactly. The chart compares single-session context curves for both winning setups and their respective baselines. Four-slot qualification is reported separately in the benchmark tables. [BENCHMARKS.md](docs/BENCHMARKS.md) contains every measurement, quality budgets, and the protocol; [results.json](benchmarks/results.json) contains the pinned identities and aggregates.

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

Every recipe applies 120 W package limits and model-scoped cooling. Qwen uses CPU boost off, GPU DPM auto, and systemd memory limits of 123G/125G. Its four-slot qualification retained **14.23 GiB effective non-CMA headroom**, recovered all four long prompts, and passed all four continued conversations.

[OPERATIONS.md](docs/OPERATIONS.md) covers service controls and updates. [ARCHITECTURE.md](docs/ARCHITECTURE.md) describes the runtime settings and current limits. [SOURCES.md](docs/SOURCES.md) records upstream provenance.

## License

The orchestration, scripts, and documentation are MIT licensed. Models, runtimes, libraries, drivers, and build dependencies retain their upstream licenses and terms. See [NOTICE.md](NOTICE.md).
