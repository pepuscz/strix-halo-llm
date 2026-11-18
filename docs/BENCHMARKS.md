# Benchmarks

Prefill means reading the input; decode means writing the answer. Input tokens are model-specific counts, while context allocation is the memory reserved for a conversation.

The cold retrieval test places five labelled phrases at different positions in an input and asks the model to find them. Every recorded speed-test request found all five. Each point measures one request with no cached input. Detailed sources, settings and result data are linked below.

## DeepSeek-V4.1-Flash-1017

### EXL3 2.25 bpw on each hardware option

![DeepSeek-V4.1-Flash-1017 EXL3 2.25 bpw context scaling on each hardware option](benchmark-deepseek-v41-hardware.svg)

**Maya DS4 HIP EXL3 2.25 bpw** runs the same model files on the M5 alone, with one RX 7900 XTX, or with two: two cards and one card on the newer engine (`maya-ds4-exl3-1m-20261117`, shorter prompt reads), the M5 alone on `maya-ds4-exl3-1m-20261116`. Every request is a fresh cold load at a 1M allocation, thinking off, nothing read from a cache. Each cell gives the first run and the second run: the same request again in the same load after 60 s idle. With a card, the engine moves the experts the request used from the 8060S's pool into VRAM while idle; on the M5 alone the expert cache and the page cache warm up instead.

| First / second run | M5 alone | 1 × RX 7900 XTX | **2 × RX 7900 XTX** |
|---|---:|---:|---:|
| Maya `--bench` decode | 22.1 / 26.7 | 54.2 / 70.3 | 76.1 / 97.5 |
| Maya `--bench` prefill, 2K | 122 / 111 | 202 / 230 | 658 / 664 |
| Maya `--bench` prefill, 8K | 297 / 317 | 536 / 629 | 1,060 / 1,271 |
| 128K five-phrase: decode | 23.3 / 40.8 | 64.6 / 91.7 | 90.8 / 130.6 |
| 128K five-phrase: prefill | 576 / 598 | 1,251 / 1,303 | 1,992 / 2,057 |
| 480K five-phrase: decode | 23.2 / 38.6 | 63.7 / 93.9 | 84.2 / 125.1 |
| 480K five-phrase: prefill | 473 / 477 | 1,096 / 1,109 | 1,599 / 1,604 |
| Real code, 130,048 tokens: decode | 21.3 / 25.0 | 46.1 / 61.7 | 60.3 / 76.8 |
| Real code, 130,048 tokens: prefill | 535 / 553 | 900 / 916 | 1,685 / 1,751 |
| Expert picks served from GPU memory | 85 % / 88 % | 24 % / 65 % | 48 % / 87 % |

- **M5 alone** ([recipe](../ansible/releases/maya-ds4-exl3-apu-1m.yml)): the Radeon 8060S runs the whole model, with 20 GiB of RAM kept out of its expert budget; 16K prompt chunks.
- **1 × RX 7900 XTX** ([recipe](../ansible/releases/maya-ds4-exl3-single-xtx-1m.yml)): the card runs the model and the Radeon 8060S holds a 113 GB expert pool; 8K prompt chunks.
- **2 × RX 7900 XTX** ([recipe](../ansible/releases/maya-ds4-exl3-dual-xtx-1m.yml)): the two cards run the model tensor parallel and the Radeon 8060S holds a 109 GB expert pool; 16K prompt chunks.

On two cards the **1,040,000-token** check found **5/5** values: **1,128 prefill / 79.4 decode tok/s**. Perplexity with this engine: **7.1937** (23 × 2,048 tokens). The answer-quality score (**30/30**) and the Lucebox KL below were measured with this engine; the one-card recipe runs the same model files and engine, the M5-alone recipe the same model files on `maya-ds4-exl3-1m-20261116`.

#### Recorded context scaling

**M5 alone**

| Input tokens | Prefill, first / second run | Decode, first / second run | Values |
|---:|---:|---:|---:|
| 2,040 | 127.2 / 170.3 | 19.8 / 42.3 | 5/5 |
| 7,680 | 317.3 / 405.3 | 22.7 / 42.9 | 5/5 |
| 30,720 | 502.7 / 569.8 | 22.9 / 40.4 | 5/5 |
| 122,879 | 576.3 / 598.0 | 23.3 / 40.8 | 5/5 |
| 491,520 | 473.4 / 476.6 | 23.2 / 38.6 | 5/5 |

**1 × RX 7900 XTX**

| Input tokens | Prefill, first / second run | Decode, first / second run | Values |
|---:|---:|---:|---:|
| 2,040 | 223.5 / 276.6 | 65.2 / 104.4 | 5/5 |
| 7,680 | 595.4 / 748.5 | 63.8 / 106.0 | 5/5 |
| 30,720 | 1,035.7 / 1,147.5 | 64.3 / 100.2 | 5/5 |
| 122,879 | 1,250.7 / 1,302.8 | 64.6 / 91.7 | 5/5 |
| 491,520 | 1,095.8 / 1,108.8 | 63.7 / 93.9 | 5/5 |

**2 × RX 7900 XTX**

| Input tokens | Prefill, first / second run | Decode, first / second run | Values |
|---:|---:|---:|---:|
| 2,040 | 526.0 / 773.1 | 94.2 / 143.7 | 5/5 |
| 7,680 | 1,011.4 / 1,346.5 | 92.7 / 141.6 | 5/5 |
| 30,720 | 1,645.9 / 1,866.3 | 92.6 / 138.9 | 5/5 |
| 122,879 | 1,992.2 / 2,057.0 | 90.8 / 130.6 | 5/5 |
| 491,520 | 1,598.5 / 1,604.5 | 84.2 / 125.1 | 5/5 |

### Quants on two RX 7900 XTX

![DeepSeek-V4.1-Flash-1017 context scaling, four quants on two RX 7900 XTX cards](benchmark-deepseek-v41-quants.svg)

GSQ, Maya-S and Maya-XS were measured with the v1.1.48 indexer engine at 512K: eleven curve points, medians of three loads for GSQ and one load for Maya-S and Maya-XS, and the [fixed-input Maya benchmark](../benchmarks/maya_bench.py) ([token fixture](../benchmarks/maya-bench-inputs.json)). EXL3's column is the two-card release above (first runs, Maya's own `--bench` requests). Thinking off, zero cached input, a 256-token cap.

| 2 × RX 7900 XTX | **EXL3 2.25 bpw** | GSQ-RCO IQ2_XS | Maya-S IQ2_XXS | Maya-XS v2 IQ1_S |
|---|---:|---:|---:|---:|
| Context allocation | 1M | 512K | 512K | 512K |
| Model shards, excluding Engram | 159 GB | 155 GB | 178 GB | 117 GB |
| Perplexity (23 × 2,048 tokens; lower is better) | 7.1937 | 7.3695 | 7.2498 | 7.9435 |
| Quality | 30/30 | 30/30 | 30/30 | 30/30 |
| Deepest retrieval | 5/5 at 1.04M | 5/5 at 520K | 5/5 at 520K | 5/5 at 520K |
| Maya benchmark: decode | 76.1 | 60.9 | 41.7 | 80.7 |
| Maya benchmark: prefill 2K / 8K | 658 / 1,060 | 210 / 537 | 169 / 478 | 286 / 661 |
| 128K five-phrase: decode / prefill | 90.8 / 1,992 | 55.8 / 1,673 | 26.3 / 1,669 | 95.9 / 1,762 |
| 480K five-phrase: decode / prefill | 84.2 / 1,599 | 54.8 / 1,436 | 33.2 / 1,423 | 90.1 / 1,447 |
| Real code, 130,048 tokens: decode / prefill | 60.3 / 1,685 | 52.5 / 1,464 | 37.3 / 1,378 | 66.2 / 1,587 |

EXL3 supports 1M context and has the lowest measured perplexity (7.1937). It also decodes faster at long context (90.8 against GSQ-RCO's 55.8 tokens/s at 128K). Maya-XS v2 has the fastest recorded decode, with higher perplexity (7.9435).

Different answer text and draft acceptance mean these decode rates do not isolate kernel speed.

#### Maya DS4 HIP GSQ-RCO IQ2_XS dual RX 7900 XTX

| Input tokens | Prefill (tok/s) | Decode (tok/s) | Values |
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

#### Maya DS4 HIP Maya-S IQ2_XXS dual RX 7900 XTX

| Input tokens | Prefill (tok/s) | Decode (tok/s) | Values |
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

#### Maya DS4 HIP Maya-XS v2 IQ1_S dual RX 7900 XTX

| Input tokens | Prefill (tok/s) | Decode (tok/s) | Values |
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

### Quality and teacher comparison

Cold coding/maths suite: EXL3 30/30 (this release); GSQ, Maya-S and Maya-XS 30/30 (math_08 scored against its corrected gold answer). Perplexity in the tables: 23 × 2,048 tokens.

The separate Lucebox held-out set has eight 1,024-token sequences and 8,184 predictions. KL uses the teacher’s top 256 probabilities; lower is better. Top-1 is agreement with the teacher.

| Quant | KL | Top-1 agreement | Held-out PPL |
|---|---:|---:|---:|
| **EXL3 2.25** (this release) | 0.1654 | 83.26% | 9.1463 |
| GSQ-RCO IQ2_XS (v1.1.50 indexer) | 0.2272 | 80.51% | 9.6736 |

Maya-S and Maya-XS have no KL measurement. [Exact data and input hashes](../benchmarks/results.json).

## GLM-5.3-Flash

![GLM-5.3-Flash context scaling on two RX 7900 XTX cards](benchmark-glm.svg)

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

The installed 512K service read the 128K prompt (114,093 tokens) at 891.2 tok/s and wrote at 54.9, slightly below the 262,144-token row. The test text routes to few experts and reads faster than real documents. The DeepSeek row's 130,048-token real-code prompt (124,103 GLM tokens) read at 651.7 tok/s on that service. It wrote 768 tokens at 54.2 tok/s, and at 55.4 tok/s with that input already cached. Quality: 28/30 with the same coding and maths questions (math_08 and math_09 missed), measured at a 131,072-token allocation.

The service holds one conversation at a time. When another conversation arrives, the current one is set aside on disk, up to four of them in 32 GB, and dropped after seven days. In the qualification run, a 114,129-token conversation set aside this way came back for its next turn in 3.0 s (114,128 tokens from disk), and that turn took 10.7 s against 128.2 s cold. Set-aside conversations also survive a service restart. After a stop and start of the installed service, a 28,554-token conversation came back from disk in 0.1 s, and its next turn took 4.9 s.

## Qwen3.8-Flash-Next

![Qwen3.8-Flash-Next context scaling on the BOSGAME M5 alone](benchmark-qwen.svg)

**Winning setup for Qwen: Strata HIP UD-Q4_K_XL.** The comparison baseline is Strix Halo llama.cpp Vulkan UD-Q4_K_XL.

| Configuration | Exact input | Input processing | Generation | Request time | Quality |
|---|---:|---:|---:|---:|---:|
| Strix Halo llama.cpp Vulkan UD-Q4_K_XL | 114,089 | 347.96 tok/s | 34.69 tok/s | 329.35 s | 30/30 |
| Strata HIP UD-Q4_K_XL · one conversation | 114,089 | 790.40 tok/s | 42.40 tok/s | 145.79 s | 30/30 |
| **Strata HIP UD-Q4_K_XL · capacity for four conversations** | **114,089** | **683.50 tok/s** | **43.60 tok/s** | **168.31 s** | **30/30** |

The recipe with capacity for four conversations reduces request time by **48.9% (1.96× faster)** versus Vulkan. The one-conversation profile is **2.26× faster** at this matched workload.

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

![DeepSeek-V4-Flash-0731 context scaling on the BOSGAME M5 alone](benchmark-deepseek-v4-0731.svg)

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

Qwen uses kernel `7.0.0-31-generic`; DeepSeek-V4-Flash-0731 uses `7.0.0-29-generic`. Strata and Vulkan run with CPU boost off and GPU DPM auto. Lucebox runs with CPU boost on and GPU DPM high. The demand fan controller samples once per second, returns to firmware-auto after 300 idle seconds, and uses maximum cooling on failure. Its measured activation latency is 1.520 seconds; prefill/decode/end-to-end ratios against fixed fans are 1.0000/1.0018/1.0018.
