# Contributing

Changes to a qualified setup must be deterministic and reviewable:

1. Pin every source revision, downloaded artifact, build input, and model identity in a release manifest. Never silently edit a published tag.
2. Preserve each recipe's qualified memory floor, cgroup limits, power envelope, and cooling policy.
3. Run the CI release validators, Ansible lint, template rendering, playbook syntax checks, chart freshness check, and fan-controller tests.
4. Qualify runtime or serving changes on the target host before promotion; publish matched aggregates with workload identity, settings, quality, and memory headroom.
5. Update the current documentation and regenerate `docs/benchmark.svg` from `benchmarks/results.json`.
6. Exclude private prompts, host logs, credentials, and model/runtime binaries. Keep rejected configurations in the private qualification source.

Matched comparisons use identical prompt bytes and quality fixtures on the same hardware. Record request budgets and engine settings alongside the results. Each supported stack has one current recipe; Qwen / Strata is the explicit default.
