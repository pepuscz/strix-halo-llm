# Third-party notices

This repository contains original orchestration, tests, and documentation. It
does not contain model weights. The superseded v1.2.0 GitHub
release asset contains one rebuilt Vulkan backend library plus its source
license and build manifest; current Vulkan releases use the official upstream
archive without a local binary overlay.

- `Nathanw1014/strix-halo-llamacpp`: the upstream portable runtime is downloaded
  from its GitHub release; llama.cpp and its included license are MIT.
- Strata and its bundled components retain their upstream licenses. The current Qwen system builds pinned upstream source.
- Qwen model weights, tokenizer, and MTP tensors retain their model-card terms.
- Lucebox: Apache-2.0. The current ROCm system builds an unmodified pinned
  upstream commit.
- llama.cpp and linked components retain the licenses shipped by their
  upstream distributions.
- Unsloth DeepSeek V4 Flash GGUF: MIT according to its model card.
- The DSpark and ROCmFPX model artifacts retain their model-card terms.
- rocWMMA: MIT.
- RyzenAdj: LGPL-3.0.
- `ec-su_axb35-linux`: GPL-2.0.
- Ubuntu, ROCm, Ansible, and build packages retain their respective licenses.

Exact links and revisions are in `docs/SOURCES.md` and the release
manifests. The absence of a component from this notice does not alter its
license.
