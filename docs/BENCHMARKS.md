# Benchmarks

The dual RX 7900 XTX setups and the BOSGAME M5-only setups use different models and hardware. Their speeds are not a matched comparison. Prefill means reading the input; decode means writing the answer. Input tokens are model-specific counts, while context allocation is the memory reserved for a conversation.

The cold retrieval test places five labelled phrases at different positions in an input and asks the model to find them. Every recorded speed-test request found all five. Each point measures one request with no cached input. Detailed sources, settings and result data are linked below.

## Dual RX 7900 XTX: DeepSeek-V4.1-Flash-1017

![Dual RX 7900 XTX context scaling: DeepSeek-V4.1-Flash-1017 and GLM-5.3-Flash](benchmark-dual-xtx.svg)

**Maya DS4 HIP GSQ-RCO IQ2_XS dual RX 7900 XTX** (production), on the pinned v1.1.48 engine with the RDNA 3 indexer with 32K prompt chunks and hybrid pack at 512K (524,288 tokens allocated):

Each retrieval point is a fresh load from the frozen expert profile, thinking off, a 256-token cap and zero cached input. It uses the same prompt bytes and frozen benchmark driver as the comparison recipes.

| Input tokens | Reading the input (tok/s) | Writing the answer (tok/s) | Phrases found |
|---:|---:|---:|---:|
| 2,040 | 258.3 | 59.1 | 5/5 |
| 3,840 | 418.2 | 56.7 | 5/5 |
| 7,680 | 587.0 | 55.7 | 5/5 |
| 15,359 | 901.7 | 55.2 | 5/5 |
| 30,720 | 1,112.3 | 54.5 | 5/5 |
| 59,933 | 1,438.4 | 59.1 | 5/5 |
| 122,879 | 1,672.8 | 55.8 | 5/5 |
| 163,840 | 1,710.8 | 50.6 | 5/5 |
| 212,992 | 1,670.2 | 55.4 | 5/5 |
| 245,760 | 1,667.0 | 53.1 | 5/5 |
| 491,520 | 1,435.6 | 54.8 | 5/5 |

The 130,048-token real-code prompt read at **1,464.1 tok/s** and wrote 768 tokens at **52.5 tok/s**. With 130,047 tokens cached, decode was **65.7 tok/s**. These are medians of three fresh loads; cached speed is the median of each load's three-answer mean. Fixed-input native decode was **60.9 tok/s**, the median of three per-load means; **210 / 537 tok/s** prefill comes from the load with that median. The 520,000-token needle found 5/5 values (**1,402.2 prefill / 53.4 decode**). Quality **30/30**; teacher perplexity **7.3695** over 47,081 scored tokens in 23 sequences.

The curve is one full run. All readings use the same pinned engine, 32K chunks, GSQ hybrid pack and frozen profile. Indexer scores can change the answer text and draft acceptance, so cold and cached decode changes do not isolate kernel speed. The API retains shared-prefix and turn checkpoints, with tail restore disabled. Quality cases are cold.

### Other quants on the same engine (benchmark only)

Maya-S IQ2_XXS and Maya-XS v2 IQ1_S use the production engine source and environment, changing the pack, its drafter and its own frozen expert profile. Each has one full run, with fresh loads and zero cached input for the same five-phrase prompts (including 491,520 tokens). Both allocate 524,288 tokens. These comparisons have no installer; [the exact data](../benchmarks/results.json) pin the model files and packing inputs.

#### Maya DS4 HIP Maya-S IQ2_XXS dual RX 7900 XTX

| Input tokens | Reading the input (tok/s) | Writing the answer (tok/s) | Phrases found |
|---:|---:|---:|---:|
| 2,040 | 216.6 | 41.7 | 5/5 |
| 3,840 | 367.1 | 41.0 | 5/5 |
| 7,680 | 596.4 | 40.7 | 5/5 |
| 15,359 | 896.4 | 32.3 | 5/5 |
| 30,720 | 1,182.0 | 37.9 | 5/5 |
| 59,933 | 1,478.6 | 26.2 | 5/5 |
| 122,879 | 1,669.2 | 26.3 | 5/5 |
| 163,840 | 1,692.9 | 36.8 | 5/5 |
| 212,992 | 1,665.0 | 26.0 | 5/5 |
| 245,760 | 1,654.6 | 31.5 | 5/5 |
| 491,520 | 1,423.0 | 33.2 | 5/5 |

Real code (130,048 input tokens, 768 output): **1,378.1 prefill / 37.3 decode tok/s**; with 130,047 input tokens cached, **49.4 tok/s** (mean of three answers). The 520,000-token needle found 5/5: 1,388.3 prefill / 26.0 decode. Quality **30/30**; teacher perplexity **7.2498** on 23 × 2,048 tokens.

#### Maya DS4 HIP Maya-XS v2 IQ1_S dual RX 7900 XTX

| Input tokens | Reading the input (tok/s) | Writing the answer (tok/s) | Phrases found |
|---:|---:|---:|---:|
| 2,040 | 342.8 | 99.0 | 5/5 |
| 3,840 | 535.1 | 98.0 | 5/5 |
| 7,680 | 809.2 | 99.0 | 5/5 |
| 15,359 | 1,100.9 | 98.4 | 5/5 |
| 30,720 | 1,320.4 | 98.5 | 5/5 |
| 59,933 | 1,595.6 | 98.0 | 5/5 |
| 122,879 | 1,762.3 | 95.9 | 5/5 |
| 163,840 | 1,778.5 | 95.2 | 5/5 |
| 212,992 | 1,727.3 | 94.1 | 5/5 |
| 245,760 | 1,703.0 | 94.2 | 5/5 |
| 491,520 | 1,447.3 | 90.1 | 5/5 |

Real code (130,048 input tokens, 768 output): **1,587.3 prefill / 66.2 decode tok/s**; with 130,047 input tokens cached, **68.0 tok/s** (mean of three answers). The 520,000-token needle found 5/5: 1,413.4 prefill / 89.6 decode. Quality **30/30**; teacher perplexity **7.9435** on 23 × 2,048 tokens.

Maya-S's 178 GB of model weights exceed the combined 48 GB VRAM and 128 GiB RAM available to experts. Uncached experts stream from the NVMe: the engine's `maya:engine_disk_mb` counter recorded 32.1 MB per generated token cold and 14–20 MB with the prompt cached. Decode also depends on the experts each answer selects (26–42 tok/s across this curve). The retrieval filler routes to few experts and reads faster than real text.

Maya-XS v2 (117 GB) almost fits in VRAM + RAM: the same counter recorded 0.6 MB per generated token cold and 0.1 / 0.0 / 0.0 MB for the three cached answers. It decodes fastest of the three, at a higher perplexity (7.94 vs GSQ 7.37). These are engine counters, not whole-drive traffic.

### Maya's own benchmark

`maya.py --bench` writes three 256-token answers (greedy, thinking off; decode is their mean) and reads 2,048- and 8,192-token prompts from Maya's documentation. The [driver](../benchmarks/maya_bench.py) and [fixed token inputs](../benchmarks/maya-bench-inputs.json) publish the common workload. The fixture pins its public source and document hashes; the driver uses DeepSeek's explicit chat wrapper.

| Quant | Decode mean | Three questions | Prefill 2,048 / 8,192 |
|---|---:|---|---:|
| **GSQ-RCO IQ2_XS** | 60.9 | 62.5 / 50.2 / 70.1 | 210 / 537 |
| Maya-S IQ2_XXS | 41.7 | 47.0 / 35.1 / 43.0 | 169 / 478 |
| Maya-XS v2 IQ1_S | 80.7 | 86.4 / 64.5 / 91.2 | 286 / 661 |

GSQ reports the median of three per-load decode means and prefill from that median load. Maya-S and Maya-XS v2 each report one load. Generated text and draft acceptance differ; these decode rates do not isolate kernel speed.

## Dual RX 7900 XTX: GLM-5.3-Flash

**Maya HIP Maya-M IQ2_S dual RX 7900 XTX**, on the same two cards and Radeon 8060S as the DeepSeek rows above, with the same five-phrase prompts (identical bytes, pinned by SHA-256). GLM's tokenizer counts about 7 % fewer tokens for the same text, so its input counts are lower at each length. The layers are split between the cards (0-24 on the first, the rest on the second). The 8060S computes each card's routed experts held in RAM, and the model's own MTP layer drafts the next token. Each point is a fresh load, with thinking off, a 256-token cap (answers used 52-61 tokens) and zero cached input. The release allocates 524,288 tokens; each point ran at the smallest of 131,072, 262,144 and 524,288 that holds it. At 128K the two smaller allocations read at 907.1 and 895.3 tok/s and both wrote at 55.8.

### Public Project Maya benchmark

[Project Maya issue #458](https://github.com/mw00/project-maya/issues/458) reports a public prompt ladder on this hardware. The Maya v1.1.25 and tuned-branch columns use the same prompt at each length. Values are decode / prefill tokens per second; all points found five of five values.

| Exact GLM input tokens | Maya v1.1.25 | Tuned branch |
|---:|---:|---:|
| 1,886 | 29.0 / 178 | 56.0 / 183 |
| 28,517 | 28.3 / 689 | 56.8 / 691 |
| 114,093 | 27.5 / 906 | 55.8 / 907 |

The issue also reports 152,129–456,403-token prompts and the 28/30 quality result. Its 114,093-token public point uses a smaller context allocation than the installed 512K service, which measured 54.9 decode / 891.2 prefill tok/s. The detailed table below preserves the context-scaling measurements from this repository.

[Pinned public issue snapshot](../benchmarks/project-maya-issue-458.json)

### Recorded context scaling

| Input tokens | Allocation | Reading the input (tok/s) | Writing the answer (tok/s) | Phrases found |
|---:|---:|---:|---:|---:|
| 1,886 | 131,072 | 183.1 | 56.0 | 5/5 |
| 3,557 | 131,072 | 294.7 | 57.7 | 5/5 |
| 7,123 | 131,072 | 464.1 | 56.1 | 5/5 |
| 14,253 | 131,072 | 644.8 | 56.5 | 5/5 |
| 28,517 | 131,072 | 691.2 | 56.8 | 5/5 |
| 55,644 | 131,072 | 728.6 | 56.7 | 5/5 |
| 114,093 | 262,144 | 895.3 | 55.8 | 5/5 |
| 152,129 | 262,144 | 972.8 | 55.1 | 5/5 |
| 197,770 | 262,144 | 1,012.8 | 54.7 | 5/5 |
| 228,197 | 262,144 | 1,032.3 | 53.4 | 5/5 |
| 456,403 | 524,288 | 1,021.3 | 50.1 | 5/5 |

The installed 512K service read the 128K prompt (114,093 tokens) at 891.2 tok/s and wrote at 54.9, slightly below the 262,144-token row. The test text routes to few experts and reads faster than real documents. The DeepSeek row's 130,048-token real-code prompt (124,103 GLM tokens) read at 651.7 tok/s on that service. It wrote 768 tokens at 54.2 tok/s, and at 55.4 tok/s with that input already cached. Quality: 28/30 with the same coding and maths questions (math_08 and math_09 missed), measured at a 131,072-token allocation. This is a different model and quantization from the DeepSeek rows, so it is not a matched comparison.

The service holds one conversation at a time. When another conversation arrives, the current one is set aside on disk, up to four of them in 32 GB, and dropped after seven days. In the qualification run, a 114,129-token conversation set aside this way came back for its next turn in 3.0 s (114,128 tokens from disk), and that turn took 10.7 s against 128.2 s cold. Set-aside conversations also survive a service restart. After a stop and start of the installed service, a 28,554-token conversation came back from disk in 0.1 s, and its next turn took 4.9 s.

## BOSGAME M5 only

The sections below compare the single-box setups on the Radeon 8060S, without the external cards. Qwen and DeepSeek-V4-Flash-0731 were benchmarked with different models and quantizations from the dual-card releases above.

## Qwen3.8-Flash-Next UD-Q4_K_XL

**Winning setup for Qwen: Strata HIP UD-Q4_K_XL.** The comparison baseline is Strix Halo llama.cpp Vulkan UD-Q4_K_XL.

| Configuration | Exact input | Input processing | Generation | Request time | Quality |
|---|---:|---:|---:|---:|---:|
| Strix Halo llama.cpp Vulkan UD-Q4_K_XL | 114,089 | 347.96 tok/s | 34.69 tok/s | 329.35 s | 30/30 |
| Strata HIP UD-Q4_K_XL · one conversation | 114,089 | 790.40 tok/s | 42.40 tok/s | 145.79 s | 30/30 |
| **Strata HIP UD-Q4_K_XL · capacity for four conversations** | **114,089** | **683.50 tok/s** | **43.60 tok/s** | **168.31 s** | **30/30** |

The recipe with capacity for four conversations reduces request time by **48.9% (1.96× faster)** versus Vulkan. The one-conversation profile is **2.26× faster** at this matched workload.

![Matched Qwen and DeepSeek single-session throughput curves](benchmark.svg)

### Qwen context scaling

| Workload | Exact Qwen input | Vulkan input tok/s | Strata input tok/s | Vulkan generation tok/s | Strata generation tok/s | Vulkan seconds | Strata seconds |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2K | 1,881 | 465.25 | 322.40 | 42.76 | 40.20 | 5.45 | 7.35 |
| 4K | 3,552 | 534.63 | 484.40 | 44.69 | 48.00 | 7.99 | 8.60 |
| 8K | 7,118 | 535.41 | 648.90 | 44.09 | 48.00 | 14.66 | 12.24 |
| 16K | 14,249 | 512.34 | 750.90 | 43.21 | 47.80 | 29.20 | 20.25 |
| 32K | 28,512 | 466.38 | 757.50 | 38.80 | 49.50 | 62.45 | 38.69 |
| 64K | 55,639 | 415.00 | 758.50 | 36.91 | 49.30 | 135.70 | 74.41 |
| 128K | 114,089 | 347.96 | 790.40 | 34.69 | 42.40 | 329.35 | 145.79 |
| 160K | 152,124 | 320.77 | 755.20 | 29.57 | 43.20 | 475.96 | 202.84 |
| 208K | 197,765 | 294.96 | 738.30 | 31.08 | 42.30 | 672.41 | 269.32 |
| 240K | 228,192 | 280.26 | 734.50 | 30.48 | 43.70 | 816.18 | 312.09 |

The curves use one session with 131,072-token allocation through the 128K workload and 262,144 thereafter. Strata uses a 16K prefill cap, native UD-Q4_K_XL expert/PLE tensors, BF16-compatible dense tensors, int8 KV, and MTP speculation. Vulkan uses q8_0 K/V, a 2,048-token batch, 256-token microbatch, and shared Q8_0 MTP draft with maximum draft length 2. The separate four-slot result uses four 262,144-token slots, an 8K prefill cap, QFUSE=0, and no prefill borrowing.

### Four simultaneous conversations

Four conversations each received a different long prompt containing 228,244 tokens. All four found their own requested phrases, kept their contents separate, and answered a follow-up correctly. All four generated answers simultaneously. At least 14,921,348 KiB (14.23 GiB) of memory remained available outside the reserved CMA pool. Four simultaneous conversations are tested; higher counts are not tested.

## DeepSeek-V4-Flash-0731

**Winning setup for DeepSeek: Strix Halo llama.cpp Vulkan IQ3_XXS.** The comparison baseline is Lucebox ROCm ROCmFPX.

| Stack | Exact input | Input processing | Generation | Quality |
|---|---:|---:|---:|---:|
| Strix Halo llama.cpp Vulkan IQ3_XXS | 122,879 | 226.82 tok/s | 35.73 tok/s | 30/30 |
| Lucebox ROCm ROCmFPX | 122,879 | 142.82 tok/s | 29.60 tok/s | 29/30 |

### DeepSeek context scaling

| Stack | Allocation | Exact input | Input processing | Generation |
|---|---:|---:|---:|---:|
| Strix Halo llama.cpp Vulkan IQ3_XXS | 131,072 | 2,040 | 245.23 tok/s | 40.04 tok/s |
| Strix Halo llama.cpp Vulkan IQ3_XXS | 131,072 | 3,840 | 260.12 tok/s | 38.98 tok/s |
| Strix Halo llama.cpp Vulkan IQ3_XXS | 131,072 | 7,680 | 254.07 tok/s | 37.70 tok/s |
| Strix Halo llama.cpp Vulkan IQ3_XXS | 131,072 | 15,359 | 254.94 tok/s | 40.09 tok/s |
| Strix Halo llama.cpp Vulkan IQ3_XXS | 131,072 | 30,720 | 250.59 tok/s | 39.48 tok/s |
| Strix Halo llama.cpp Vulkan IQ3_XXS | 131,072 | 59,933 | 244.19 tok/s | 37.90 tok/s |
| Strix Halo llama.cpp Vulkan IQ3_XXS | 131,072 | 122,879 | 226.82 tok/s | 35.73 tok/s |
| Strix Halo llama.cpp Vulkan IQ3_XXS | 262,144 | 163,840 | 218.56 tok/s | 34.12 tok/s |
| Strix Halo llama.cpp Vulkan IQ3_XXS | 262,144 | 212,992 | 206.65 tok/s | 32.77 tok/s |
| Strix Halo llama.cpp Vulkan IQ3_XXS | 262,144 | 245,760 | 200.21 tok/s | 31.77 tok/s |
| Strix Halo llama.cpp Vulkan IQ3_XXS | 524,288 | 491,520 | 163.23 tok/s | 25.02 tok/s |
| Lucebox ROCm ROCmFPX | 131,072 | 7,680 | 213.91 tok/s | 36.90 tok/s |
| Lucebox ROCm ROCmFPX | 131,072 | 30,720 | 201.68 tok/s | 32.00 tok/s |
| Lucebox ROCm ROCmFPX | 131,072 | 122,879 | 142.82 tok/s | 29.60 tok/s |

## Protocol and quality

Cold retrieval uses deterministic filler with five values near 2%, 20%, 50%, 80%, and 98% depth, temperature 0, top-k 1, top-p 1, and one cold request per point. The output cap is 80 tokens for Qwen and 256 for DeepSeek and GLM. Throughput is reported by each engine; request time is input-processing time plus generation time. Exact prompt SHA-256 values, output counts, and Qwen completion-count/time rates are in [results.json](../benchmarks/results.json). Different model tokenizers produce different token counts for the same prompt bytes.

Quality uses all ten coding, ten GSM8K-style, and ten MATH-style cases from the [pinned Lucebox harness](https://github.com/Luce-Org/lucebox/tree/90f85fa401c6a3c61d9e4d0e2da7fc48a5e8915e/harness). Coding answers execute against their tests; numeric scores use reviewed final answers. The corrected `math_08` reference is `20/3`; interval whitespace is normalized.

| Stack / model | Coding | GSM8K-style | MATH-style | Total |
|---|---:|---:|---:|---:|
| Strata HIP UD-Q4_K_XL / Qwen | 10/10 | 10/10 | 10/10 | 30/30 |
| Strix Halo llama.cpp Vulkan UD-Q4_K_XL / Qwen | 10/10 | 10/10 | 10/10 | 30/30 |
| Strix Halo llama.cpp Vulkan IQ3_XXS / DeepSeek | 10/10 | 10/10 | 10/10 | 30/30 |
| Lucebox ROCm ROCmFPX / DeepSeek | 10/10 | 10/10 | 9/10 | 29/30 |

Quality completion caps are 512 for coding, 1,024 for GSM8K-style, and 2,048 for MATH-style. Strata's `math_10` uses 4,096 tokens; it scores 29/30 with the original caps. Lucebox's `math_10` returns `998` against reference `997`.

The four-slot Strata quality checkpoint uses a 16K prefill cap and prompts of at most 141 tokens; those prompts fit wholly within the four-slot 8K cap. Its short-prompt batch test passes exact token parity. Interleave scenarios complete, while one continued-conversation case differs in strict token parity. Answer quality and four independent long conversations pass.

## Reproduction

[results.json](../benchmarks/results.json) contains source/model identities, prompt hashes, request parameters, exact token counts, all measured points, and qualification aggregates. Ansible manifests pin artifacts and build inputs. The published Strata recipe preserves the qualified serving flags and tensor hashes with portable installation paths; the reference executable hash identifies the measured build, and each portable build is sealed locally.

Qwen uses kernel `7.0.0-31-generic`; DeepSeek uses `7.0.0-29-generic`. Strata and Vulkan run with CPU boost off and GPU DPM auto. Lucebox runs with CPU boost on and GPU DPM high. The demand fan controller samples once per second, returns to firmware-auto after 300 idle seconds, and uses maximum cooling on failure. Its measured activation latency is 1.520 seconds; prefill/decode/end-to-end ratios against fixed fans are 1.0000/1.0018/1.0018.
