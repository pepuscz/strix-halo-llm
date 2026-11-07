#!/usr/bin/env python3
"""Render the model comparison from the published benchmark aggregates."""
import argparse
import html
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'benchmarks/results.json'
OUTPUT = ROOT / 'docs/benchmark.svg'
SERIES = [
    ('strata-qwen-q4xl', '#0969da', 'Qwen · Strata HIP UD-Q4_K_XL'),
    ('qwen-vulkan-q4xl', '#008577', 'Qwen · Strix Halo llama.cpp Vulkan UD-Q4_K_XL'),
    ('vulkan-iq3xxs', '#8957e5', 'DeepSeek · Strix Halo llama.cpp Vulkan IQ3_XXS'),
    ('rocm-rocmfpx', '#bc4c00', 'DeepSeek · Lucebox ROCm ROCmFPX'),
]
SINGLE = 'maya-ds4-exl3-single-xtx'
# the single-card chart: its curve against the dual recipe's, the same model, engine and prompts
SINGLE_SERIES = [(SINGLE, '#cf222e'), ('maya-ds4-exl3-dual-xtx', '#8c959f')]
DUAL_SERIES = [('maya-ds4-exl3-dual-xtx', '#cf222e'), ('maya-ds4-gsq-dual-xtx', '#8250df'), ('maya-ds4-maya-s-dual-xtx', '#0969da'), ('maya-ds4-maya-xs-dual-xtx', '#bc4c00'), ('maya-glm-dual-xtx', '#1a7f37')]


def render(data, dual=False, single=False):
    dual = dual or single
    pairs = SINGLE_SERIES if single else DUAL_SERIES
    series = SERIES if not dual else [(sid, color, f"{data['systems'][sid]['model']} · {data['systems'][sid]['name']}")
                                      for sid, color in pairs]
    lines = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 775" role="img" aria-labelledby="title desc">',
             '<title id="title">Strix Halo LLM throughput: Qwen and DeepSeek</title>',
             '<desc id="desc">Reading and answer-writing speeds on a 128 GiB Ryzen AI Max+ 395. The test asks each model to find five labelled phrases placed in a long text. Every run found all five correctly. The winning setup for Qwen and the winning setup for DeepSeek are shown with their respective comparison baselines. Each point measures one request at the input length shown. Each horizontal tick doubles the input length.</desc>',
             '<style>text{font-family:Arial,sans-serif;fill:#24292f}.title{font-size:26px;font-weight:700}.sub{font-size:15px;fill:#57606a}.label{font-size:16px}.tick{font-size:13px;fill:#57606a}.panel{font-size:18px;font-weight:700}.grid{stroke:#d8dee4;stroke-dasharray:3 5}.value{font-size:14px;font-weight:700}</style>',
             '<rect width="1100" height="775" fill="white"/>',
             '<text x="70" y="40" class="title">Strix Halo LLM benchmarks</text>',
             '<text x="70" y="67" class="sub">Ryzen AI Max+ 395 · Radeon 8060S · 128 GiB RAM · 120 W · reasoning mode disabled</text>']
    if dual:
        lines[0] = lines[0].replace('1100 775', '1100 850')
        lines[1] = '<title id="title">Dual RX 7900 XTX throughput: DeepSeek-V4.1-Flash-1017 and GLM-5.3-Flash</title>'
        lines[2] = '<desc id="desc">Cold five-phrase retrieval on two RX 7900 XTX cards with a Radeon 8060S expert helper. DeepSeek EXL3 uses a 1,048,576-token allocation; GSQ-RCO, Maya-S and Maya-XS v2 use 524,288. Each quant has one eleven-point curve on the same prompt bytes; every point found all five phrases. GLM uses its own tokenizer and recorded capacities. Each horizontal tick doubles the input length.</desc>'
        lines[-2] = '<text x="70" y="40" class="title">Dual RX 7900 XTX · DeepSeek-V4.1-Flash-1017 and GLM-5.3-Flash</text>'
        lines[-1] = '<text x="70" y="67" class="sub">Ryzen AI Max+ 395 · 128 GiB RAM · Radeon 8060S helper · one conversation · thinking off</text>'
    if single:
        lines[1] = '<title id="title">One RX 7900 XTX throughput: DeepSeek-V4.1-Flash-1017</title>'
        lines[2] = '<desc id="desc">Cold five-phrase retrieval with one RX 7900 XTX and the Radeon 8060S as the expert helper, against the same EXL3 2.25 bpw model and engine on two cards. Both use a 1,048,576-token allocation and the same prompt bytes; every point found all five phrases. Each horizontal tick doubles the input length.</desc>'
        lines[-2] = '<text x="70" y="40" class="title">One RX 7900 XTX · DeepSeek-V4.1-Flash-1017 EXL3 2.25 bpw</text>'
    for i, (sid, color, name) in enumerate(series):
        yy = 99 + i * 24
        weight = 700 if (sid == SINGLE if single else sid in data["winning_setups"].values()) else 400
        lines += [f'<line x1="70" y1="{yy}" x2="98" y2="{yy}" stroke="{color}" stroke-width="3"/>',
                  f'<text x="110" y="{yy+5}" class="label" style="font-weight:{weight}">{html.escape(name)}</text>']
    left, right, height = 80, 1020, 165
    xmin, xmax = 1800, 524288

    def x(tokens):
        return left + math.log(tokens / xmin) / math.log(xmax / xmin) * (right-left)

    panels = [('Reading the input (tokens/second) · higher is better', 'prefill_tokens_per_second', 235, 900),
              ('Writing the answer (tokens/second) · higher is better', 'decode_tokens_per_second', 480, 60)]
    if dual:
        fastest = max(p['prefill_tokens_per_second'] for sid, _ in pairs
                      for p in data['systems'][sid]['context_scaling'] if isinstance(p['prefill_tokens_per_second'], (int, float)))
        reading = next(m for m in (1200, 1600, 2000, 2400) if m >= fastest)
        writing = max(60, 20 * math.ceil(max(p['decode_tokens_per_second'] for sid, _ in pairs
                       for p in data['systems'][sid]['context_scaling'] if isinstance(p['decode_tokens_per_second'], (int, float))) / 20))
        panels = [(title, key, top + (-45 if single else 35), maximum)
                  for (title, key, top, _), maximum in zip(panels, (reading, writing))]
    for title, key, top, maximum in panels:
        bottom = top + height
        def y(value):
            return bottom - value / maximum * height
        lines.append(f'<text x="80" y="{top-20}" class="panel">{title}</text>')
        for fraction in [0, .25, .5, .75, 1]:
            yy = y(maximum*fraction)
            lines.extend([f'<line class="grid" x1="80" y1="{yy:.2f}" x2="1020" y2="{yy:.2f}"/>',
                          f'<text class="tick" x="68" y="{yy+4:.2f}" text-anchor="end">{maximum*fraction:g}</text>'])
        for exp in range(1,10):
            tokens=1024*2**exp;xx=x(tokens)
            lines.extend([f'<line class="grid" x1="{xx:.2f}" y1="{top}" x2="{xx:.2f}" y2="{bottom}"/>',
                          f'<text class="tick" x="{xx:.2f}" y="{bottom+22}" text-anchor="middle">{2**exp}K</text>'])
        end_labels = []
        for sid,color,_ in series:
            rows = data['systems'][sid]['context_scaling']
            points=[p for p in rows if isinstance(p.get(key), (int, float))]
            if not points:
                continue
            coords=[(x(p['actual_input_tokens']),y(p[key])) for p in points]
            path=' '.join(('M' if i==0 else 'L')+f'{xx:.2f} {yy:.2f}' for i,(xx,yy) in enumerate(coords))
            lines.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.7"/>')
            for p,(xx,yy) in zip(points,coords):
                lines.append(f'<circle cx="{xx:.2f}" cy="{yy:.2f}" r="4" fill="{color}"><title>{p["actual_input_tokens"]:,} tokens: {p[key]:.2f}</title></circle>')
            xx,yy=coords[-1];value=points[-1][key]
            offset=-12 if sid in ('strata-qwen-q4xl','vulkan-iq3xxs','maya-glm-dual-xtx') or (sid == 'qwen-vulkan-q4xl' and key != 'decode_tokens_per_second') else 21
            if dual and sid == 'maya-ds4-gsq-dual-xtx' and key == 'prefill_tokens_per_second':
                offset = -12
            if dual and sid == 'maya-ds4-maya-s-dual-xtx' and key == 'prefill_tokens_per_second':
                offset = 16
            if dual and sid == 'maya-glm-dual-xtx' and key == 'prefill_tokens_per_second':
                offset = 20
            if dual and sid == 'maya-ds4-exl3-dual-xtx':
                offset = 32 if key == 'prefill_tokens_per_second' else -28
            if dual and sid == 'maya-ds4-maya-xs-dual-xtx':
                offset = -32 if key == 'prefill_tokens_per_second' else -12
            if dual:
                end_labels.append((yy + 4, xx, yy, value, color))
            else:
                lines.append(f'<text class="value" x="{xx:.2f}" y="{yy+offset:.2f}" text-anchor="end" style="fill:{color}">{value:.1f}</text>')
        if dual:
            end_labels.sort()
            placed = []
            for desired, *_ in end_labels:
                placed.append(max(desired, placed[-1] + 16 if placed else desired))
            shift = sum(y - item[0] for y, item in zip(placed, end_labels)) / len(placed)
            placed = [y - shift for y in placed]
            if placed[0] < top + 8:
                placed = [y + top + 8 - placed[0] for y in placed]
            if placed[-1] > bottom + 8:
                placed = [y - (placed[-1] - bottom - 8) for y in placed]
            for label_y, (_, xx, yy, value, color) in zip(placed, end_labels):
                lines.append(f'<line x1="{xx:.2f}" y1="{yy:.2f}" x2="1032" y2="{label_y-4:.2f}" stroke="{color}" stroke-width="1"/>')
                lines.append(f'<text class="value" x="1040" y="{label_y:.2f}" text-anchor="start" style="fill:{color}">{value:.1f}</text>')
    if single:
        lines.append('<text x="550" y="765" text-anchor="middle" class="tick">Both: 1M allocation, the same engine and prompts · runtime versions and full protocol in BENCHMARKS.md</text>')
    elif dual:
        lines.append('<text x="550" y="765" text-anchor="middle" class="tick">EXL3: 1M allocation · other DeepSeek quants: 512K · runtime versions and full protocol in BENCHMARKS.md</text>')
    lines += ['<text x="550" y="700" text-anchor="middle" class="label">Input length (tokens; each tick doubles)</text>',
              '<text x="550" y="735" text-anchor="middle" class="label">Test: find five phrases hidden in a long text. Every run found all five correctly.</text>',
              '</svg>', '']
    if single:   # (two legend rows, not five: the panels and the notes sit 80 px higher than the dual chart's)
        lines = [line.replace('1100 850', '1100 770').replace('height="775"', 'height="770"')
                 .replace('y="700"', 'y="670"').replace('y="735"', 'y="705"').replace('y="765"', 'y="735"') for line in lines]
    elif dual:
        lines = [line.replace('y="700"', 'y="750"').replace('y="735"', 'y="785"').replace('y="765"', 'y="815"') for line in lines]
    return '\n'.join(lines)


def render_readme(data, text):
    return render_comparison_readme(data, text)


COMPARISONS = ('maya-ds4-exl3-dual-xtx', 'maya-ds4-gsq-dual-xtx', 'maya-ds4-maya-s-dual-xtx', 'maya-ds4-maya-xs-dual-xtx')


def reading(value, digits=1):
    return f'{value:,.{digits}f}' if isinstance(value, (int, float)) else str(value)


def comparison_table(data):
    headers=['**EXL3 2.25 bpw**','GSQ-RCO IQ2_XS','Maya-S IQ2_XXS','Maya-XS v2 IQ1_S']
    cols=[]
    for sid in COMPARISONS:
        v=data['systems'][sid];b=v['maya_bench']['this_release'];q=v['quality']
        at128=[x for x in v['context_scaling'] if x['actual_input_tokens']==122879][0]
        cols.append(['1M' if v['context_allocation']==1048576 else '512K', f"{v['target']['model_bytes']/1e9:.0f} GB",
                     f"{q['perplexity']['value']:.2f}", f"{q['total']}/30", f"{b['decode_mean_tokens_per_second']:.0f}",
                     f"{at128['decode_tokens_per_second']:.0f}", f"{b['prefill_tokens_per_second']['8192']:,.0f}",
                     f"{at128['prefill_tokens_per_second']:,.0f}"])
    labels=['Longest input','Model size, excluding Engram','Perplexity (lower is better)','Quality checks passed',
            'Decode, short prompt','Decode, 128K input','Prefill, 8K input','Prefill, 128K input']
    return ['| | '+' | '.join(headers)+' |','|---|---:|---:|---:|---:|']+['| '+label+' | '+' | '.join(c[i] for c in cols)+' |' for i,label in enumerate(labels)]


def single_table(data):
    """One card against two: the same model, engine, prompts and measures as the quant comparison's EXL3 column."""
    cols=[]
    for sid in (SINGLE, 'maya-ds4-exl3-dual-xtx'):
        v=data['systems'][sid];b=v['maya_bench']['this_release'];q=v['quality'];c=v['long_context']
        at128=[x for x in v['context_scaling'] if x['actual_input_tokens']==122879][0]
        cols.append(['1M' if v['context_allocation']==1048576 else '512K', f"{q['total']}/30", f"{q['perplexity']['value']:.2f}",
                     f"{b['decode_mean_tokens_per_second']:.0f}", f"{at128['decode_tokens_per_second']:.0f}",
                     f"{b['prefill_tokens_per_second']['8192']:,.0f}", f"{at128['prefill_tokens_per_second']:,.0f}",
                     f"{c['prefill_tokens_per_second']:,.0f} / {c['decode_tokens_per_second']:.1f}"])
    labels=['Longest input','Quality checks passed','Perplexity (lower is better)','Decode, short prompt','Decode, 128K input',
            'Prefill, 8K input','Prefill, 128K input','Real code, 130K tokens: prefill / decode']
    return ['| | **1 × RX 7900 XTX** | 2 × RX 7900 XTX |','|---|---:|---:|']+['| '+label+' | '+' | '.join(c[i] for c in cols)+' |' for i,label in enumerate(labels)]


def render_comparison_readme(data, text):
    blocks=[('quant-comparison-table','\n'.join(comparison_table(data))),('quant-comparison-note',xs_summary(data))]
    if SINGLE in data['systems'] and '<!-- single-xtx-table -->' in text:
        blocks.append(('single-xtx-table','\n'.join(single_table(data))))
    for name,body in blocks:
        start='<!-- '+name+' -->';end='<!-- /'+name+' -->';before,rest=text.split(start,1);_,after=rest.split(end,1);text=before+start+'\n'+body+'\n'+end+after
    return text


def at_128k(system):
    return [p for p in system['context_scaling'] if p['actual_input_tokens']==122879][0]['decode_tokens_per_second']


def xs_summary(data, detailed=False):
    x=data['systems']['maya-ds4-exl3-dual-xtx'];g=data['systems']['maya-ds4-gsq-dual-xtx']
    lead=("EXL3 supports 1M context and decodes faster than GSQ-RCO at long inputs; " if at_128k(x)>at_128k(g)
          else "EXL3 supports 1M context. GSQ-RCO decodes faster at long inputs; ")
    return lead+"Maya-XS v2 is the fastest, with higher perplexity."


def fork_version(system):
    import re
    return re.search(r'v\d+\.\d+\.\d+', system['runtime']['upstream']).group(0)


def stock_version(system):
    import re
    return re.search(r'v\d+\.\d+\.\d+', system['upstream_benchmark']['procedure']).group(0)


def comparison_table_detailed(data):
    headers=['**EXL3 2.25 bpw**','GSQ-RCO IQ2_XS','Maya-S IQ2_XXS','Maya-XS v2 IQ1_S']
    cols=[]
    for sid in COMPARISONS:
        v=data['systems'][sid];b=v['maya_bench']['this_release'];c=v['long_context'];q=v['quality'];rows={x['actual_input_tokens']:x for x in v['context_scaling']}
        cols.append(['1M' if v['context_allocation']==1048576 else '512K',f"{v['target']['model_bytes']/1e9:.0f} GB",reading(q['perplexity']['value'],4),f"{q['total']}/30",f"{v['deep_needle']['needle_passes']}/5",f"{v['near_capacity_needle']['needle_passes']}/5" if v.get('near_capacity_needle') else '—',reading(b['decode_mean_tokens_per_second']),reading(b['prefill_tokens_per_second']['2048'],0)+' / '+reading(b['prefill_tokens_per_second']['8192'],0),*[reading(rows[n]['decode_tokens_per_second'])+' / '+reading(rows[n]['prefill_tokens_per_second'],0) for n in [122879,491520]],reading(c['prefill_tokens_per_second'],0),reading(c['decode_tokens_per_second'])+' / '+reading(c['reused_prompt']['decode_tokens_per_second'])])
    labels=['Context allocation','Model shards, excluding Engram','Perplexity (23 × 2,048 tokens; lower is better)','Quality','520K retrieval','1.04M retrieval','Fixed-input Maya benchmark: decode','Fixed-input Maya benchmark: prefill 2K / 8K','128K five-phrase: decode / prefill','480K five-phrase: decode / prefill','Real code, 130,048 tokens: prefill','Real code: decode cold / prompt cached']
    return ['| | '+' | '.join(headers)+' |','|---|---:|---:|---:|---:|']+['| '+label+' | '+' | '.join(c[i] for c in cols)+' |' for i,label in enumerate(labels)]


def detailed_summary(data):
    x=data['systems']['maya-ds4-exl3-dual-xtx'];xs=data['systems']['maya-ds4-maya-xs-dual-xtx']
    g=data['systems']['maya-ds4-gsq-dual-xtx']
    at=at_128k
    faster=(f"It also decodes faster at long context ({at(x):.1f} against GSQ-RCO's {at(g):.1f} tokens/s at 128K). "
            if at(x)>at(g) else f"GSQ-RCO decodes faster at long context ({at(g):.1f} against {at(x):.1f} tokens/s at 128K). ")
    return (f"EXL3 supports 1M context and has the lowest measured perplexity ({x['quality']['perplexity']['value']:.4f}). "
            f"{faster}"
            f"Maya-XS v2 has the fastest recorded decode, with higher perplexity ({xs['quality']['perplexity']['value']:.4f}).")


def render_quant_details(data, text):
    systems=data['systems'];e=systems[COMPARISONS[0]]
    lines=['## Dual RX 7900 XTX: DeepSeek-V4.1-Flash-1017','',
           '![Dual RX 7900 XTX context scaling: DeepSeek-V4.1-Flash-1017 and GLM-5.3-Flash](benchmark-dual-xtx.svg)','',
           f"**Maya DS4 HIP EXL3 2.25 bpw dual RX 7900 XTX** uses the qualified {fork_version(e)}-based fork, original FP8 Engram, 16K prompt chunks and 1M context. [Ansible recipe](../ansible/releases/maya-ds4-exl3-dual-xtx-1m.yml).",'',
           'GSQ, Maya-S and Maya-XS measurements use the v1.1.48 indexer engine at 512K. EXL3 uses 1M. The eleven curve points share identical input bytes, zero cached input, thinking off and a 256-token cap; each load is fresh, from the frozen profile. All five values were found at every point.','',
           *comparison_table_detailed(data),'',detailed_summary(data),'',
           'GSQ and EXL3 report medians of three loads per point; Maya-S and Maya-XS each report one load. Cached decode uses three consecutive answers per load. Different answer text and draft acceptance mean these decode rates do not isolate kernel speed.','',
           '### Recorded context scaling','']
    for sid in COMPARISONS:
        v=systems[sid];name=v['name'];name='**'+name+'**' if sid==COMPARISONS[0] else name
        lines += ['#### '+name,'','| Input tokens | Prefill (tok/s) | Decode (tok/s) | Values |','|---:|---:|---:|---:|']
        for x in v['context_scaling']:lines.append(f"| {x['actual_input_tokens']:,} | {reading(x['prefill_tokens_per_second'])} | {reading(x['decode_tokens_per_second'])} | {x['needle_passes']}/5 |")
        if v.get('near_capacity_needle'):
            x=v['near_capacity_needle'];lines += ['',f"The separate **{x['actual_input_tokens']:,}-token** check found **{x['needle_passes']}/5** values with zero cached input: **{reading(x['prefill_tokens_per_second'])} prefill / {reading(x['decode_tokens_per_second'])} decode tok/s**."]
        lines.append('')
    lines += ['### Fixed-input Maya benchmark','',
              'The [driver](../benchmarks/maya_bench.py) and [token fixture](../benchmarks/maya-bench-inputs.json) retain the public v1.1.28 benchmark procedure: three 256-token answers, greedy and thinking off, plus 2,048- and 8,192-token prompts. The comparison table above uses these same inputs for every quant.','',
              f"### Upstream {stock_version(e)} benchmark at 1M",'',
              'A separate source-native `maya.py --bench` comparison used the same actual token IDs, a 1,048,576-token allocation and two cold loads per arm, in optimized EXL3 / GSQ / stock EXL3 order, repeated once. These documentation tokens differ from the fixed-input fixture above.','',
              '| Setup | Decode mean (tok/s) | Prefill 2K / 8K (tok/s) |','|---|---:|---:|']
    u=e['upstream_benchmark']
    for arm,label in [('E+','**Optimized EXL3 2.25**'),('G',f'GSQ-RCO IQ2_XS, stock {stock_version(e)}'),('E0',f'EXL3 2.25, stock {stock_version(e)}')]:
        v=u['arms'][arm]['mean'];lines.append(f"| {label} | {reading(v['decode'])} | {reading(v['prefill']['2048'])} / {reading(v['prefill']['8192'])} |")
    lines += ['',"The optimized arm is this release: its binary and recipe (the helper's 109 GB pool with the drafter's leftover experts, ~5 GB read ahead). The stock EXL3 arm keeps the retained stock reference recipe (a 95 GB pool, 14.9 GB read-ahead, no DS4_HELPER_DRAFT), so the rows compare the release with a stock reference, not binaries alone. GSQ uses its recipe at 1M. Each native decode mean covers three answers; changed text and draft acceptance prevent a stream-matched causal claim.",'',
              '### Quality and teacher comparison','',
              'All four DeepSeek quants scored 30/30 on the cold coding/maths suite. The established math_08 gold-answer correction is retained. The perplexity values in the main table use 23 × 2,048 tokens.','',
              'The separate Lucebox held-out set has eight 1,024-token sequences and 8,184 predictions. KL uses the teacher’s top 256 probabilities; lower is better. Top-1 is agreement with the teacher.','',
              '| Quant | KL | Top-1 agreement | Held-out PPL |','|---|---:|---:|---:|']
    for sid,label in [(COMPARISONS[0],f'**EXL3 2.25 ({fork_version(e)} fork)**'),(COMPARISONS[1],'GSQ-RCO IQ2_XS (v1.1.50 indexer)')]:
        z=systems[sid]['quality']['lucebox_kl']['all'];lines.append(f"| {label} | {z['kl_top256']:.4f} | {z['top1_agree']*100:.2f}% | {z['ppl']:.4f} |")
    lines += ['', 'The EXL3 dump/PPL consistency check differed by 0.27%, within the fixed 2% tolerance. Maya-S and Maya-XS were not measured with this KL driver. [Exact data and input hashes](../benchmarks/results.json).','']
    if SINGLE in systems:
        lines += single_details(data)
    a=text.index('## Dual RX 7900 XTX: DeepSeek-V4.1-Flash-1017');b=text.index('## Dual RX 7900 XTX: GLM-5.3-Flash',a)
    return text[:a]+'\n'.join(lines)+'\n'+text[b:]


def single_details(data):
    """The single-card release: its curve, needles, real-code prompt, quality and native --bench rows."""
    v=data['systems'][SINGLE];c=v['long_context'];q=v['quality'];b=v['maya_bench']['this_release']
    lines=['## Single RX 7900 XTX: DeepSeek-V4.1-Flash-1017','',
           '![One RX 7900 XTX context scaling against two, DeepSeek-V4.1-Flash-1017 EXL3 2.25 bpw](benchmark-single-xtx.svg)','',
           f"**{v['name']}** runs the same EXL3 2.25 bpw model and {fork_version(v)}-based engine as the dual recipe on one card, for a host without a second one. The Radeon 8060S holds a 113 GB expert pool, prompts run in 8K chunks (one card lends the prompt path no VRAM, so its buffers stay), and the DSpark blocks' experts all sit in the pool. [Ansible recipe](../ansible/releases/maya-ds4-exl3-single-xtx-1m.yml).",'',
           f"Quality **{q['total']}/30**, perplexity **{reading(q['perplexity']['value'],4)}** (23 × 2,048 tokens). The 130,048-token real-code prompt: **{reading(c['prefill_tokens_per_second'],0)}** prefill, **{reading(c['decode_tokens_per_second'])}** decode cold, **{reading(c['reused_prompt']['decode_tokens_per_second'])}** with the prompt cached. Fixed-input Maya benchmark: **{reading(b['decode_mean_tokens_per_second'])}** decode, **{reading(b['prefill_tokens_per_second']['2048'],0)} / {reading(b['prefill_tokens_per_second']['8192'],0)}** prefill at 2K / 8K.",'',
           'One fresh load per point, the same eleven prompts as the dual recipe, zero cached input, thinking off.','',
           '| Input tokens | Prefill (tok/s) | Decode (tok/s) | Values |','|---:|---:|---:|---:|']
    for x in v['context_scaling']:lines.append(f"| {x['actual_input_tokens']:,} | {reading(x['prefill_tokens_per_second'])} | {reading(x['decode_tokens_per_second'])} | {x['needle_passes']}/5 |")
    for key,label in (('deep_needle','deep'),('near_capacity_needle','near-capacity')):
        if v.get(key):
            x=v[key];lines += ['',f"The {label} **{x['actual_input_tokens']:,}-token** check found **{x['needle_passes']}/5** values with zero cached input: **{reading(x['prefill_tokens_per_second'])} prefill / {reading(x['decode_tokens_per_second'])} decode tok/s**."]
    u=v['upstream_benchmark']
    lines += ['',f"### Upstream {stock_version(v)} benchmark, one card",'',
              'Source-native `maya.py --bench`, the same token IDs as the dual recipe\'s, two cold loads per arm, interleaved.','',
              '| Setup | Decode mean (tok/s) | Prefill 2K / 8K (tok/s) |','|---|---:|---:|']
    for arm,label in [('S+','**This release**'),('S0',f'Stock {stock_version(v)}, the same settings without DS4_HELPER_DRAFT')]:
        m=u['arms'][arm]['mean'];lines.append(f"| {label} | {reading(m['decode'])} | {reading(m['prefill']['2048'])} / {reading(m['prefill']['8192'])} |")
    lines += ['','The lend of #867 runs on a tensor-parallel group only, so on one card the release differs from stock by DS4_HELPER_DRAFT (#904). Changed text and draft acceptance prevent a stream-matched causal claim.','']
    return lines


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    data = json.loads(DATA.read_text())
    outputs = [(OUTPUT, render(data)), (ROOT / 'docs/benchmark-dual-xtx.svg', render(data, True)),
               *([(ROOT / 'docs/benchmark-single-xtx.svg', render(data, single=True))] if SINGLE in data['systems'] else []),
               (ROOT / 'README.md', render_readme(data, (ROOT / 'README.md').read_text())),
               (ROOT / 'docs/BENCHMARKS.md', render_quant_details(data, (ROOT / 'docs/BENCHMARKS.md').read_text()))]
    for output, expected in outputs:
        if args.check:
            if not output.exists() or output.read_text()!=expected:
                raise SystemExit(f'{output.name} is stale; run scripts/render_benchmark.py')
        else:
            output.write_text(expected)


if __name__=='__main__':
    main()
