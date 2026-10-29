# Repository policy

This public repository is the source for current qualified Strix Halo LLM setups.

- Present one winning setup for Qwen and one winning setup for DeepSeek. Bold their setup names in tables and chart legends; use normal text for the comparison setups. Do not add a Selection column or repeat the recommendation status in setup names.
- Keep one qualified Ansible configuration per supported stack and matched comparisons per model. The controller defaults to the winning Qwen setup.
- Use canonical stack names: **Strata HIP UD-Q4_K_XL**, **Strix Halo llama.cpp Vulkan UD-Q4_K_XL**, **Strix Halo llama.cpp Vulkan IQ3_XXS**, **Lucebox ROCm ROCmFPX**, **Maya DS4 HIP Maya-S IQ2_XXS dual RX 7900 XTX**, and **Maya HIP Maya-M IQ2_S dual RX 7900 XTX**. Identify the model alongside the stack.
- Keep setups that need added hardware (the dual RX 7900 XTX setups) in their own README section; they are not compared with the single-box setups.
- Pin and verify every public source, artifact, build input, and benchmark identity needed for reproduction. A manifest may mark a value the qualified host has yet to supply as `PENDING`; such a draft fails validation until it is filled, and preflight refuses to install it while any install pin is `PENDING`.
- Explain the benchmark and capacity limits in plain language before presenting results. Define terms such as slots when needed; keep detailed build and test settings out of chart captions.
- Publish current qualified settings and sanitized measurement aggregates. Exclude rejected experiments, raw logs, private host data, reasoning timelines, and casual system names.
- Keep superseded configurations in Git releases or history, not the current setup path.
- Keep README descriptions and performance tables current with the qualified manifests and result data. Replace stale values and claims in place; put change history in GitHub release notes. Run `scripts/render_benchmark.py` after changing benchmark data; its `--check` gate also verifies the README tables.
