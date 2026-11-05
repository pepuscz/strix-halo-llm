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
DUAL_SERIES = [('maya-ds4-exl3-dual-xtx', '#cf222e'), ('maya-ds4-gsq-dual-xtx', '#8250df'), ('maya-ds4-maya-s-dual-xtx', '#0969da'), ('maya-ds4-maya-xs-dual-xtx', '#bc4c00'), ('maya-glm-dual-xtx', '#1a7f37')]


def render(data, dual=False):
    series = SERIES if not dual else [(sid, color, f"{data['systems'][sid]['model']} · {data['systems'][sid]['name']}")
                                      for sid, color in DUAL_SERIES]
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
    for i, (sid, color, name) in enumerate(series):
        yy = 99 + i * 24
        weight = 700 if sid in data["winning_setups"].values() else 400
        lines += [f'<line x1="70" y1="{yy}" x2="98" y2="{yy}" stroke="{color}" stroke-width="3"/>',
                  f'<text x="110" y="{yy+5}" class="label" style="font-weight:{weight}">{html.escape(name)}</text>']
    left, right, height = 80, 1020, 165
    xmin, xmax = 1800, 524288

    def x(tokens):
        return left + math.log(tokens / xmin) / math.log(xmax / xmin) * (right-left)

    panels = [('Reading the input (tokens/second) · higher is better', 'prefill_tokens_per_second', 235, 900),
              ('Writing the answer (tokens/second) · higher is better', 'decode_tokens_per_second', 480, 60)]
    if dual:
        fastest = max(p['prefill_tokens_per_second'] for sid, _ in DUAL_SERIES
                      for p in data['systems'][sid]['context_scaling'] if isinstance(p['prefill_tokens_per_second'], (int, float)))
        reading = next(m for m in (1200, 1600, 2000, 2400) if m >= fastest)
        writing = max(60, 20 * math.ceil(max(p['decode_tokens_per_second'] for sid, _ in DUAL_SERIES
                       for p in data['systems'][sid]['context_scaling'] if isinstance(p['decode_tokens_per_second'], (int, float))) / 20))
        panels = [(title, key, top + 35, maximum) for (title, key, top, _), maximum in zip(panels, (reading, writing))]
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
    if dual:
        lines.append('<text x="550" y="765" text-anchor="middle" class="tick">EXL3: 1M allocation · other DeepSeek quants: 512K · runtime versions and full protocol in BENCHMARKS.md</text>')
    lines += ['<text x="550" y="700" text-anchor="middle" class="label">Input length (tokens; each tick doubles)</text>',
              '<text x="550" y="735" text-anchor="middle" class="label">Test: find five phrases hidden in a long text. Every run found all five correctly.</text>',
              '</svg>', '']
    if dual:
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
    labels=['Longest input','Model size','Perplexity (lower is closer to the original)','Quality checks passed',
            'Decode, short prompt','Decode, 128K input','Prefill, 8K input','Prefill, 128K input']
    return ['| | '+' | '.join(headers)+' |','|---|---:|---:|---:|---:|']+['| '+label+' | '+' | '.join(c[i] for c in cols)+' |' for i,label in enumerate(labels)]


def render_comparison_readme(data, text):
    for name,body in [('quant-comparison-table','\n'.join(comparison_table(data))),('quant-comparison-note',xs_summary(data))]:
        start='<!-- '+name+' -->';end='<!-- /'+name+' -->';before,rest=text.split(start,1);_,after=rest.split(end,1);text=before+start+'\n'+body+'\n'+end+after
    return text


def xs_summary(data, detailed=False):
    return ("EXL3 is the closest to the original model and the only one tested at 1M. "
            "GSQ-RCO decodes faster at long inputs. Maya-XS v2 is the fastest and the furthest from the original.")


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
    at=lambda sid_data:[p for p in sid_data['context_scaling'] if p['actual_input_tokens']==122879][0]['decode_tokens_per_second']
    return (f"EXL3 supports 1M context and has the lowest measured perplexity ({x['quality']['perplexity']['value']:.4f}). "
            f"GSQ-RCO decodes faster at long context ({at(g):.1f} against {at(x):.1f} tokens/s at 128K). "
            f"Maya-XS v2 has the fastest recorded decode, with higher perplexity ({xs['quality']['perplexity']['value']:.4f}).")


def render_quant_details(data, text):
    systems=data['systems'];e=systems[COMPARISONS[0]]
    lines=['## Dual RX 7900 XTX: DeepSeek-V4.1-Flash-1017','',
           '![Dual RX 7900 XTX context scaling: DeepSeek-V4.1-Flash-1017 and GLM-5.3-Flash](benchmark-dual-xtx.svg)','',
           '**Maya DS4 HIP EXL3 2.25 bpw dual RX 7900 XTX** uses the qualified v1.1.54-based fork, original FP8 Engram, 16K prompt chunks and 1M context. [Ansible recipe](../ansible/releases/maya-ds4-exl3-dual-xtx-1m.yml).','',
           'GSQ, Maya-S and Maya-XS measurements use the v1.1.48 indexer engine at 512K. EXL3 uses 1M. The eleven curve points share identical input bytes, zero cached input, thinking off and a 256-token cap; each point is one fresh load from the frozen profile. All five values were found at every point.','',
           *comparison_table_detailed(data),'',detailed_summary(data),'',
           'GSQ reports medians of three loads; EXL3, Maya-S and Maya-XS each report one load. Cached decode uses three consecutive answers per load. Different answer text and draft acceptance mean these decode rates do not isolate kernel speed.','',
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
              '### Upstream v1.1.54 benchmark at 1M','',
              'A separate source-native `maya.py --bench` comparison used the same actual token IDs, a 1,048,576-token allocation and two cold loads per arm, in optimized EXL3 / GSQ / stock EXL3 order, repeated once. These documentation tokens differ from the fixed-input fixture above.','',
              '| Setup | Decode mean (tok/s) | Prefill 2K / 8K (tok/s) |','|---|---:|---:|']
    u=e['upstream_benchmark']
    for arm,label in [('E+','**Optimized EXL3 2.25**'),('G','GSQ-RCO IQ2_XS, stock v1.1.54'),('E0','EXL3 2.25, stock v1.1.54')]:
        v=u['arms'][arm]['mean'];lines.append(f"| {label} | {reading(v['decode'])} | {reading(v['prefill']['2048'])} / {reading(v['prefill']['8192'])} |")
    lines += ['',"The two EXL3 arms use the same configuration with different binaries. GSQ uses its published recipe at 1M. Each native decode mean covers three answers; changed text and draft acceptance prevent a stream-matched causal claim.",'',
              '### Quality and teacher comparison','',
              'All four DeepSeek quants scored 30/30 on the cold coding/maths suite. The established math_08 gold-answer correction is retained. The perplexity values in the main table use 23 × 2,048 tokens.','',
              'The separate Lucebox held-out set has eight 1,024-token sequences and 8,184 predictions. KL uses the teacher’s top 256 probabilities; lower is better. Top-1 is agreement with the teacher.','',
              '| Quant | KL | Top-1 agreement | Held-out PPL |','|---|---:|---:|---:|']
    for sid,label in [(COMPARISONS[0],'**EXL3 2.25 (v1.1.54 fork)**'),(COMPARISONS[1],'GSQ-RCO IQ2_XS (v1.1.50 indexer)')]:
        z=systems[sid]['quality']['lucebox_kl']['all'];lines.append(f"| {label} | {z['kl_top256']:.4f} | {z['top1_agree']*100:.2f}% | {z['ppl']:.4f} |")
    lines += ['', 'The EXL3 dump/PPL consistency check differed by 0.38%, within the fixed 2% tolerance. Maya-S and Maya-XS were not measured with this KL driver. [Exact data and input hashes](../benchmarks/results.json).','']
    a=text.index('## Dual RX 7900 XTX: DeepSeek-V4.1-Flash-1017');b=text.index('## Dual RX 7900 XTX: GLM-5.3-Flash',a)
    return text[:a]+'\n'.join(lines)+'\n'+text[b:]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    data = json.loads(DATA.read_text())
    outputs = [(OUTPUT, render(data)), (ROOT / 'docs/benchmark-dual-xtx.svg', render(data, True)),
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
