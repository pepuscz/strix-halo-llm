# Repository policy

This public repository is the source for current qualified Strix Halo LLM setups.

- Present one winning setup for Qwen and one winning setup for DeepSeek. Bold their setup names in tables and chart legends; use normal text for the comparison setups. Do not add a Selection column or repeat the recommendation status in setup names.
- Keep one qualified Ansible configuration per supported stack and matched comparisons per model. The controller defaults to the winning Qwen setup.
- Use canonical stack names: **Strata HIP UD-Q4_K_XL**, **Strix Halo llama.cpp Vulkan UD-Q4_K_XL**, **Strix Halo llama.cpp Vulkan IQ3_XXS**, and **Lucebox ROCm ROCmFPX**. Identify the model alongside the stack.
- Pin and verify every public source, artifact, build input, and benchmark identity needed for reproduction.
- Explain the benchmark and capacity limits in plain language before presenting results. Define terms such as slots when needed; keep detailed build and test settings out of chart captions.
- Publish current qualified settings and sanitized measurement aggregates. Exclude rejected experiments, raw logs, private host data, reasoning timelines, and casual system names.
- Keep superseded configurations in Git releases or history, not the current setup path.
