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
DUAL_SERIES = [('maya-ds4-gsq-dual-xtx', '#8250df'), ('maya-ds4-maya-s-dual-xtx', '#0969da'), ('maya-ds4-maya-xs-dual-xtx', '#bc4c00'), ('maya-glm-dual-xtx', '#1a7f37')]


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
        lines[1] = '<title id="title">Dual RX 7900 XTX throughput: DeepSeek-V4.1-Flash-1017 and GLM-5.3-Flash</title>'
        lines[2] = '<desc id="desc">Cold five-phrase retrieval on two RX 7900 XTX cards with a Radeon 8060S expert helper, the same prompt bytes for both models. GLM-5.3-Flash: twelve fresh loads, from 1886 to 456403 of its tokens, at 131072-, 262144- and 524288-token capacity. DeepSeek-V4.1-Flash-1017 on three quantizations, GSQ-RCO IQ2_XS, Maya-S IQ2_XXS and Maya-XS v2 IQ1_S: eleven fresh loads each at 524288-token capacity, from 2040 to 491520 of its tokens. Every answer found all five phrases. Each horizontal tick doubles the input length.</desc>'
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
        panels = [(title, key, top, maximum) for (title, key, top, _), maximum in zip(panels, (reading, writing))]
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
            if dual and sid == 'maya-ds4-maya-xs-dual-xtx':
                offset = -32 if key == 'prefill_tokens_per_second' else -12
            lines.append(f'<text class="value" x="{xx:.2f}" y="{yy+offset:.2f}" text-anchor="end" style="fill:{color}">{value:.1f}</text>')
    lines += ['<text x="550" y="700" text-anchor="middle" class="label">Input length (tokens; each tick doubles)</text>',
              '<text x="550" y="735" text-anchor="middle" class="label">Test: find five phrases hidden in a long text. Every run found all five correctly.</text>',
              '</svg>', '']
    return '\n'.join(lines)


def render_readme(data, text):
    """Keep the current DeepSeek recipe tables bound to their own published measurements."""
    for sid, quant in (('maya-ds4-gsq-dual-xtx', 'GSQ-RCO IQ2_XS'),):
        system = data['systems'][sid]
        bench = system['maya_bench']['this_release']
        rows = {row['actual_input_tokens']: row for row in system['context_scaling']}
        code = system['long_context']
        table = ['| Test | Decode | Prefill |', '|---|---:|---:|',
                 '| `maya.py --bench` (three 256-token answers; 2K / 8K prompts) | '
                 f'**{bench["decode_mean_tokens_per_second"]:.1f}** | '
                 f'**{bench["prefill_tokens_per_second"]["2048"]:,} / '
                 f'{bench["prefill_tokens_per_second"]["8192"]:,}** |']
        for label, count in (('Public five-phrase prompt, 2K (2,040 input tokens)', 2040),
                             ('32K (30,720)', 30720), ('128K (122,879)', 122879), ('480K (491,520)', 491520)):
            row = rows[count]
            table.append(f'| {label} | {row["decode_tokens_per_second"]:.1f} | '
                         f'{row["prefill_tokens_per_second"]:,.0f} |')
        table.append('| Real code, 130,048 tokens: cold / prompt cached | '
                     f'**{code["decode_tokens_per_second"]:.1f} / '
                     f'{code["reused_prompt"]["decode_tokens_per_second"]:.1f}** | '
                     f'**{code["prefill_tokens_per_second"]:,.0f}** |')
        heading = re.escape('### DeepSeek-V4.1-Flash-1017 ' + quant)
        section = re.compile(r'(' + heading + r'[^\n]*\n)(.*?)(?=\n### |\Z)', re.S)

        def replace(match):
            body, count = re.subn(r'^\| Test \| Decode \| Prefill \|\n(?:\|[^\n]*\n)+',
                                 '\n'.join(table) + '\n', match[2], count=1, flags=re.M)
            if count != 1:
                raise ValueError('missing README performance table: ' + sid)
            return match[1] + body
        text, count = section.subn(replace, text, count=1)
        if count != 1:
            raise ValueError('missing README setup section: ' + sid)
    return render_comparison_readme(data, text)


COMPARISONS = ('maya-ds4-gsq-dual-xtx', 'maya-ds4-maya-s-dual-xtx', 'maya-ds4-maya-xs-dual-xtx')


def reading(value, digits=1):
    return f'{value:,.{digits}f}' if isinstance(value, (int, float)) else str(value)


def render_comparison_readme(data, text):
    systems = [data['systems'][sid] for sid in COMPARISONS]
    def values(system):
        b=system['maya_bench']['this_release'];c=system['long_context']
        rows={r['actual_input_tokens']:r for r in system['context_scaling']}
        q=system['quality'];needle=system['deep_needle']['needle_passes']
        return [f"{system['target']['model_bytes']/1e9:.0f} GB",
                reading(q['perplexity']['value'],4),
                f"{q['total']}/30 · {needle}/5",
                reading(b['decode_mean_tokens_per_second']),
                reading(b['prefill_tokens_per_second']['2048'],0)+' / '+reading(b['prefill_tokens_per_second']['8192'],0),
                *[reading(rows[n]['decode_tokens_per_second'])+' / '+reading(rows[n]['prefill_tokens_per_second'],0) for n in (122879,491520)],
                reading(c['prefill_tokens_per_second'],0),
                reading(c['decode_tokens_per_second'])+' / '+reading(c['reused_prompt']['decode_tokens_per_second'])]
    cols=[values(system) for system in systems]
    labels=['Model weights, without the Engram tables','Perplexity (23 × 2,048 tokens; lower is better)',
            'Quality · 520K needle','`maya.py --bench` decode','`maya.py --bench` prefill, 2K / 8K',
            '128K five-phrase (122,879): decode / prefill','480K five-phrase (491,520): decode / prefill',
            'Real code, 130,048 tokens: prefill','Real code: decode cold / prompt cached']
    table=['| | **GSQ-RCO IQ2_XS** | Maya-S IQ2_XXS | Maya-XS v2 IQ1_S |','|---|---:|---:|---:|']
    table += ['| '+label+' | '+' | '.join(col[i] for col in cols)+' |' for i,label in enumerate(labels)]
    text = text.replace('<!-- quant-comparison-table -->'+text.split('<!-- quant-comparison-table -->')[1].split('<!-- /quant-comparison-table -->')[0]+'<!-- /quant-comparison-table -->',
                        '<!-- quant-comparison-table -->\n'+'\n'.join(table)+'\n<!-- /quant-comparison-table -->')

    note = xs_summary(data)
    start = '<!-- quant-comparison-note -->'
    end = '<!-- /quant-comparison-note -->'
    before, rest = text.split(start, 1)
    _, after = rest.split(end, 1)
    return before + start + '\n' + note + '\n' + end + after


def xs_summary(data):
    xs = data['systems'][COMPARISONS[2]]
    others = [data['systems'][sid] for sid in COMPARISONS[:2]]
    disk = xs['disk_read_mb_per_token']
    if not isinstance(disk['cold'], (int, float)):
        return 'PENDING-155'
    cached = sum(disk['cached']) / len(disk['cached'])
    fastest = all(xs['maya_bench']['this_release']['decode_mean_tokens_per_second'] > other['maya_bench']['this_release']['decode_mean_tokens_per_second']
                  and xs['long_context']['decode_tokens_per_second'] > other['long_context']['decode_tokens_per_second']
                  and xs['long_context']['reused_prompt']['decode_tokens_per_second'] > other['long_context']['reused_prompt']['decode_tokens_per_second']
                  and all(a['decode_tokens_per_second'] > b['decode_tokens_per_second'] for a,b in zip(xs['context_scaling'],other['context_scaling']))
                  for other in others)
    note = (f"Maya-XS v2 ({xs['target']['model_bytes']/1e9:.0f} GB) almost fits in VRAM + RAM: "
            f"{disk['cold']:.1f} MB read per generated token cold and about {round(cached,1):g} cached. ")
    if fastest:
        note += 'It is fastest of the three for decode'
    else:
        note += 'Its perplexity is'
    xp = xs['quality']['perplexity']['value']
    gp = others[0]['quality']['perplexity']['value']
    if fastest:
        note += ', with higher perplexity' if xp > gp else ', with perplexity'
    note += f" ({xp:.2f} vs GSQ {gp:.2f})."
    return note


def render_quant_details(data, text):
    lines=['### Other quants on the same engine (benchmark only)','',
           'Maya-S IQ2_XXS and Maya-XS v2 IQ1_S use the production engine source and environment, changing the pack, its drafter and its own frozen expert profile. Each has one full run, with fresh loads and zero cached input for the same five-phrase prompts (including 491,520 tokens). Both allocate 524,288 tokens. These comparisons have no installer; [the exact data](../benchmarks/results.json) pin the model files and packing inputs.','']
    for sid in COMPARISONS[1:]:
        v=data['systems'][sid];lines += ['#### '+v['name'],'','| Input tokens | Reading the input (tok/s) | Writing the answer (tok/s) | Phrases found |','|---:|---:|---:|---:|']
        for row in v['context_scaling']:
            lines.append('| '+f"{row['actual_input_tokens']:,}"+' | '+reading(row['prefill_tokens_per_second'])+' | '+reading(row['decode_tokens_per_second'])+' | '+str(row['needle_passes'])+'/5 |')
        c=v['long_context'];n=v['deep_needle'];q=v['quality'];lines += ['',f"Real code (130,048 input tokens, 768 output): **{reading(c['prefill_tokens_per_second'])} prefill / {reading(c['decode_tokens_per_second'])} decode tok/s**; with 130,047 input tokens cached, **{reading(c['reused_prompt']['decode_tokens_per_second'])} tok/s** (mean of three answers). The 520,000-token needle found {n['needle_passes']}/5: {reading(n['prefill_tokens_per_second'])} prefill / {reading(n['decode_tokens_per_second'])} decode. Quality **{q['total']}/30**; teacher perplexity **{reading(q['perplexity']['value'],4)}** on 23 × 2,048 tokens.",'']
    disk=data['systems'][COMPARISONS[2]]['disk_read_mb_per_token']
    maya_s = data['systems'][COMPARISONS[1]]
    sd = maya_s['disk_read_mb_per_token']
    speeds = [row['decode_tokens_per_second'] for row in maya_s['context_scaling']]
    lines += [f"Maya-S's {maya_s['target']['model_bytes']/1e9:.0f} GB of model weights exceed the combined 48 GB VRAM and 128 GiB RAM available to experts. Uncached experts stream from the NVMe: the engine's `maya:engine_disk_mb` counter recorded {reading(sd['cold'])} MB per generated token cold and {reading(min(sd['cached']),0)}–{reading(max(sd['cached']),0)} MB with the prompt cached. Decode also depends on the experts each answer selects ({reading(min(speeds),0)}–{reading(max(speeds),0)} tok/s across this curve). The retrieval filler routes to few experts and reads faster than real text.",'',
              xs_summary(data) + ' Maya-XS v2 disk reads per generated token: '+reading(disk['cold'])+' MB cold; '+ ' / '.join(reading(x) for x in disk['cached'])+' MB for the three cached answers. These are engine counters, not whole-drive traffic.','',
              "### Maya's own benchmark",'',
              "`maya.py --bench` writes three 256-token answers (greedy, thinking off; decode is their mean) and reads 2,048- and 8,192-token prompts from Maya's documentation. The [driver](../benchmarks/maya_bench.py) and [fixed token inputs](../benchmarks/maya-bench-inputs.json) publish the common workload. The fixture pins its public source and document hashes; the driver uses DeepSeek's explicit chat wrapper.",'',
              '| Quant | Decode mean | Three questions | Prefill 2,048 / 8,192 |','|---|---:|---|---:|']
    for sid in COMPARISONS:
        v=data['systems'][sid];b=v['maya_bench']['this_release'];qs=b['decode_question_tokens_per_second'];name=v['name'].split('Maya DS4 HIP ')[1].split(' dual')[0]
        if sid==COMPARISONS[0]:name='**'+name+'**'
        lines += ['| '+name+' | '+reading(b['decode_mean_tokens_per_second'])+' | '+' / '.join(reading(x) for x in qs)+' | '+reading(b['prefill_tokens_per_second']['2048'],0)+' / '+reading(b['prefill_tokens_per_second']['8192'],0)+' |']
    lines += ['',"GSQ reports the median of three per-load decode means and prefill from that median load. Maya-S and Maya-XS v2 each report one load. Generated text and draft acceptance differ; these decode rates do not isolate kernel speed.",'']
    a=text.index('### Other quants on the same engine (benchmark only)');b=text.index('## Dual RX 7900 XTX: GLM-5.3-Flash',a)
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
