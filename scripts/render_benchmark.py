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


def render(data):
    lines = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 775" role="img" aria-labelledby="title desc">',
             '<title id="title">Strix Halo LLM throughput: Qwen and DeepSeek</title>',
             '<desc id="desc">Matched cold five-key retrieval on a 128 GiB Ryzen AI Max+ 395. Four runtime curves show input and generation throughput. A diamond marks the four-slot Qwen Strata result. Prompt length uses a logarithmic axis.</desc>',
             '<style>text{font-family:Arial,sans-serif;fill:#24292f}.title{font-size:26px;font-weight:700}.sub{font-size:15px;fill:#57606a}.label{font-size:14px}.tick{font-size:12px;fill:#57606a}.panel{font-size:17px;font-weight:700}.grid{stroke:#d8dee4;stroke-dasharray:3 5}.value{font-size:13px;font-weight:700}</style>',
             '<rect width="1100" height="775" fill="white"/>',
             '<text x="70" y="40" class="title">Strix Halo LLM benchmarks</text>',
             '<text x="70" y="67" class="sub">Ryzen AI Max+ 395 · Radeon 8060S · 128 GiB RAM · 120 W · thinking off</text>']
    for i, (_, color, name) in enumerate(SERIES):
        yy = 99 + i * 24
        lines += [f'<line x1="70" y1="{yy}" x2="98" y2="{yy}" stroke="{color}" stroke-width="3"/>',
                  f'<text x="110" y="{yy+5}" class="label">{html.escape(name)}</text>']
    lines += ['<path d="M760 96 l6 6 -6 6 -6 -6 Z" fill="#0969da" stroke="white" stroke-width="2"/>',
              '<text x="775" y="107" class="label">Qwen Strata · 4 × 256K</text>',
              '<text x="752" y="133" class="value">128K workload: 1.96× faster · quality 30/30</text>']
    left, right, height = 80, 1020, 165
    xmin, xmax = 1800, 524288

    def x(tokens):
        return left + math.log(tokens / xmin) / math.log(xmax / xmin) * (right-left)

    panels = [('Input processing (tok/s) · higher is better', 'prefill_tokens_per_second', 235, 900),
              ('Generation (tok/s) · higher is better', 'decode_tokens_per_second', 480, 60)]
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
        for sid,color,_ in SERIES:
            points=[p for p in data['systems'][sid]['context_scaling'] if key in p]
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
        p=data['systems']['strata-qwen-q4xl']['four_slot_context_scaling'][0];xx,yy=x(p['actual_input_tokens']),y(p[key])
        lines.append(f'<path d="M{xx:.2f} {yy-7:.2f} l7 7 -7 7 -7 -7 Z" fill="#0969da" stroke="white" stroke-width="2"><title>4 × 256K: {p[key]:.2f}</title></path>')
        lines.append(f'<text class="value" x="{xx+13:.2f}" y="{yy + {'prefill_tokens_per_second': 5, 'decode_tokens_per_second': -25, 'server_seconds': 27}[key]:.2f}" style="fill:#0969da">{p[key]:.1f} · four-slot</text>')
    lines += ['<text x="550" y="700" text-anchor="middle" class="label">Actual input tokens · logarithmic scale · identical frozen prompt bytes at matched points</text>',
              '<text x="550" y="735" text-anchor="middle" class="tick">Qwen curves: 1 session, Strata prefill 16K. Four-slot marker: 4 sessions, prefill 8K, QFUSE=0, no prefill borrowing.</text>',
              '<text x="550" y="757" text-anchor="middle" class="tick">Every retrieval point: 5/5 exact values. Source revisions, exact counts, budgets and settings: benchmarks/results.json.</text>',
              '</svg>', '']
    return '\n'.join(lines)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    expected=render(json.loads(DATA.read_text()))
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text()!=expected:
            raise SystemExit('benchmark chart is stale; run scripts/render_benchmark.py')
    else:
        OUTPUT.write_text(expected)


if __name__=='__main__':
    main()
