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
DUAL_SERIES = [('maya-ds4-gsq-dual-xtx', '#8250df'), ('maya-ds4-dual-xtx', '#0969da'), ('maya-glm-dual-xtx', '#1a7f37')]


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
        lines[2] = '<desc id="desc">Cold five-phrase retrieval on two RX 7900 XTX cards with a Radeon 8060S expert helper, the same prompt bytes for both models. GLM-5.3-Flash: twelve fresh loads, from 1886 to 456403 of its tokens, at 131072-, 262144- and 524288-token capacity. DeepSeek-V4.1-Flash-1017 on two quantizations, GSQ-RCO IQ2_XS and Maya-S IQ2_XXS: eleven fresh loads each at 524288-token capacity, from 2040 to 491520 of its tokens. Every answer found all five phrases. GSQ at 3840 tokens has two cold runs, both shown separately with a gap in the trend line. Each horizontal tick doubles the input length.</desc>'
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
                      for p in data['systems'][sid]['context_scaling'])
        reading = next(m for m in (1200, 1600, 2000, 2400) if m >= fastest)
        panels = [(title, key, top, maximum) for (title, key, top, _), maximum in zip(panels, (reading, 60))]
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
            points=[p for p in rows if key in p]
            if not points:
                continue
            coords=[(x(p['actual_input_tokens']),y(p[key])) for p in points]
            recheck = data['systems'][sid].get('cold_start_recheck')
            path, start = [], True
            for point, (xx, yy) in zip(points, coords):
                if recheck and point['actual_input_tokens'] == recheck['actual_input_tokens']:
                    start = True       # Two observations do not establish a reproducible dip in the trend.
                    continue
                path.append(('M' if start else 'L') + f'{xx:.2f} {yy:.2f}')
                start = False
            lines.append(f'<path d="{" ".join(path)}" fill="none" stroke="{color}" stroke-width="2.7"/>')
            for p,(xx,yy) in zip(points,coords):
                if recheck and p['actual_input_tokens'] == recheck['actual_input_tokens']:
                    ry = y(recheck[key])
                    lines.append(f'<line x1="{xx:.2f}" y1="{yy:.2f}" x2="{xx:.2f}" y2="{ry:.2f}" stroke="{color}" stroke-dasharray="3 4"/>')
                    lines.append(f'<circle cx="{xx:.2f}" cy="{yy:.2f}" r="4.5" fill="white" stroke="{color}" stroke-width="2"><title>{p["actual_input_tokens"]:,} tokens, initial cold run: {p[key]:.2f}</title></circle>')
                    diamond = f'{xx:.2f},{ry-5:.2f} {xx+5:.2f},{ry:.2f} {xx:.2f},{ry+5:.2f} {xx-5:.2f},{ry:.2f}'
                    lines.append(f'<polygon points="{diamond}" fill="{color}"><title>{p["actual_input_tokens"]:,} tokens, cold recheck: {recheck[key]:.2f}</title></polygon>')
                    if key == 'decode_tokens_per_second':
                        lines.append(f'<text x="{xx+12:.2f}" y="{yy+18:.2f}" class="tick" style="fill:{color}">{p[key]:.1f} initial</text>')
                        lines.append(f'<text x="{xx+12:.2f}" y="{ry-10:.2f}" class="tick" style="fill:{color}">{recheck[key]:.1f} recheck</text>')
                else:
                    lines.append(f'<circle cx="{xx:.2f}" cy="{yy:.2f}" r="4" fill="{color}"><title>{p["actual_input_tokens"]:,} tokens: {p[key]:.2f}</title></circle>')
            xx,yy=coords[-1];value=points[-1][key]
            offset=-12 if sid in ('strata-qwen-q4xl','vulkan-iq3xxs','maya-glm-dual-xtx') or (sid == 'qwen-vulkan-q4xl' and key != 'decode_tokens_per_second') else 21
            if dual and sid == 'maya-ds4-gsq-dual-xtx' and key == 'prefill_tokens_per_second':
                offset = -16
            if dual and sid == 'maya-ds4-dual-xtx' and key == 'prefill_tokens_per_second':
                offset = 34
            lines.append(f'<text class="value" x="{xx:.2f}" y="{yy+offset:.2f}" text-anchor="end" style="fill:{color}">{value:.1f}</text>')
    if dual:
        lines.append('<text x="550" y="760" text-anchor="middle" class="tick">GSQ 4K: open circle = initial cold run; diamond = cold recheck. Both shown; trend line interrupted.</text>')
    lines += ['<text x="550" y="700" text-anchor="middle" class="label">Input length (tokens; each tick doubles)</text>',
              '<text x="550" y="735" text-anchor="middle" class="label">Test: find five phrases hidden in a long text. Every run found all five correctly.</text>',
              '</svg>', '']
    return '\n'.join(lines)


def render_readme(data, text):
    """Keep the current DeepSeek recipe tables bound to their own published measurements."""
    for sid, quant in (('maya-ds4-gsq-dual-xtx', 'GSQ-RCO IQ2_XS'),
                       ('maya-ds4-dual-xtx', 'Maya-S IQ2_XXS')):
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
    return text


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    data = json.loads(DATA.read_text())
    outputs = [(OUTPUT, render(data)), (ROOT / 'docs/benchmark-dual-xtx.svg', render(data, True)),
               (ROOT / 'README.md', render_readme(data, (ROOT / 'README.md').read_text()))]
    for output, expected in outputs:
        if args.check:
            if not output.exists() or output.read_text()!=expected:
                raise SystemExit(f'{output.name} is stale; run scripts/render_benchmark.py')
        else:
            output.write_text(expected)


if __name__=='__main__':
    main()
