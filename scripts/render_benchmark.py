#!/usr/bin/env python3
"""Render the model comparison from the published benchmark aggregates."""
import argparse
import html
import json
import math
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


def render(data, dual=False):
    series = SERIES if not dual else [('maya', '#0969da', data['system'])]
    lines = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 775" role="img" aria-labelledby="title desc">',
             '<title id="title">Strix Halo LLM throughput: Qwen and DeepSeek</title>',
             '<desc id="desc">Reading and answer-writing speeds on a 128 GiB Ryzen AI Max+ 395. The test asks each model to find five labelled phrases placed in a long text. Every run found all five correctly. The winning setup for Qwen and the winning setup for DeepSeek are shown with their respective comparison baselines. Each point measures one request at the input length shown. Each horizontal tick doubles the input length.</desc>',
             '<style>text{font-family:Arial,sans-serif;fill:#24292f}.title{font-size:26px;font-weight:700}.sub{font-size:15px;fill:#57606a}.label{font-size:16px}.tick{font-size:13px;fill:#57606a}.panel{font-size:18px;font-weight:700}.grid{stroke:#d8dee4;stroke-dasharray:3 5}.value{font-size:14px;font-weight:700}</style>',
             '<rect width="1100" height="775" fill="white"/>',
             '<text x="70" y="40" class="title">Strix Halo LLM benchmarks</text>',
             '<text x="70" y="67" class="sub">Ryzen AI Max+ 395 · Radeon 8060S · 128 GiB RAM · 120 W · reasoning mode disabled</text>']
    if dual:
        lines[1] = '<title id="title">DeepSeek-V4.1-Flash-1017: dual RX 7900 XTX throughput</title>'
        lines[2] = '<desc id="desc">Cold five-phrase retrieval on two RX 7900 XTX cards with a Radeon 8060S expert helper. Ten fresh loads at 262144-token capacity, from 2040 to 245760 input tokens; every answer found all five phrases. Each answer used 64 tokens. Each horizontal tick doubles the input length.</desc>'
        lines[-2] = '<text x="70" y="40" class="title">DeepSeek-V4.1-Flash-1017 · dual RX 7900 XTX</text>'
        lines[-1] = '<text x="70" y="67" class="sub">Ryzen AI Max+ 395 · 128 GiB RAM · Radeon 8060S helper · 256K capacity · thinking off</text>'
    for i, (sid, color, name) in enumerate(series):
        yy = 99 + i * 24
        weight = 700 if dual or sid in data["winning_setups"].values() else 400
        lines += [f'<line x1="70" y1="{yy}" x2="98" y2="{yy}" stroke="{color}" stroke-width="3"/>',
                  f'<text x="110" y="{yy+5}" class="label" style="font-weight:{weight}">{html.escape(name)}</text>']
    left, right, height = 80, 1020, 165
    xmin, xmax = 1800, 262144 if dual else 524288

    def x(tokens):
        return left + math.log(tokens / xmin) / math.log(xmax / xmin) * (right-left)

    panels = [('Reading the input (tokens/second) · higher is better', 'prefill_tokens_per_second', 235, 900),
              ('Writing the answer (tokens/second) · higher is better', 'decode_tokens_per_second', 480, 60)]
    if dual:
        panels = [(title, key, top, maximum) for (title, key, top, _), maximum in zip(panels, (250, 40))]
    for title, key, top, maximum in panels:
        bottom = top + height
        def y(value):
            return bottom - value / maximum * height
        lines.append(f'<text x="80" y="{top-20}" class="panel">{title}</text>')
        for fraction in [0, .25, .5, .75, 1]:
            yy = y(maximum*fraction)
            lines.extend([f'<line class="grid" x1="80" y1="{yy:.2f}" x2="1020" y2="{yy:.2f}"/>',
                          f'<text class="tick" x="68" y="{yy+4:.2f}" text-anchor="end">{maximum*fraction:g}</text>'])
        for exp in range(1,9 if dual else 10):
            tokens=1024*2**exp;xx=x(tokens)
            lines.extend([f'<line class="grid" x1="{xx:.2f}" y1="{top}" x2="{xx:.2f}" y2="{bottom}"/>',
                          f'<text class="tick" x="{xx:.2f}" y="{bottom+22}" text-anchor="middle">{2**exp}K</text>'])
        for sid,color,_ in series:
            rows = data['points'] if dual else data['systems'][sid]['context_scaling']
            points=[p for p in rows if key in p]
            if not points:
                continue
            coords=[(x(p['actual_input_tokens']),y(p[key])) for p in points]
            path=' '.join(('M' if i==0 else 'L')+f'{xx:.2f} {yy:.2f}' for i,(xx,yy) in enumerate(coords))
            lines.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.7"/>')
            for p,(xx,yy) in zip(points,coords):
                lines.append(f'<circle cx="{xx:.2f}" cy="{yy:.2f}" r="4" fill="{color}"><title>{p["actual_input_tokens"]:,} tokens: {p[key]:.2f}</title></circle>')
            xx,yy=coords[-1];value=points[-1][key]
            offset=-12 if sid in ('strata-qwen-q4xl','vulkan-iq3xxs') or (sid == 'qwen-vulkan-q4xl' and key != 'decode_tokens_per_second') else 21
            lines.append(f'<text class="value" x="{xx:.2f}" y="{yy+offset:.2f}" text-anchor="end" style="fill:{color}">{value:.1f}</text>')
    lines += ['<text x="550" y="700" text-anchor="middle" class="label">Input length (tokens; each tick doubles)</text>',
              '<text x="550" y="735" text-anchor="middle" class="label">Test: find five phrases hidden in a long text. Every run found all five correctly.</text>',
              '</svg>', '']
    return '\n'.join(lines)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    for source, output, dual in ((DATA, OUTPUT, False),
            (ROOT / 'benchmarks/maya-dual-xtx-context.json', ROOT / 'docs/benchmark-dual-xtx.svg', True)):
        expected=render(json.loads(source.read_text()), dual)
        if args.check:
            if not output.exists() or output.read_text()!=expected:
                raise SystemExit(f'{output.name} is stale; run scripts/render_benchmark.py')
        else:
            output.write_text(expected)


if __name__=='__main__':
    main()
