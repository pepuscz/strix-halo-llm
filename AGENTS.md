# Repository policy

This public repository is the source for current qualified Strix Halo LLM setups.

- Keep one qualified Ansible configuration per supported stack, matched comparisons per model, and one explicit default.
- Use canonical stack names: **Strata HIP UD-Q4_K_XL**, **Strix Halo llama.cpp Vulkan UD-Q4_K_XL**, **Strix Halo llama.cpp Vulkan IQ3_XXS**, and **Lucebox ROCm ROCmFPX**. Identify the model alongside the stack.
- Pin and verify every public source, artifact, build input, and benchmark identity needed for reproduction.
- Publish current qualified settings and sanitized measurement aggregates. Exclude rejected experiments, raw logs, private host data, reasoning timelines, and casual system names.
- Keep superseded configurations in Git releases or history, not the current setup path.
