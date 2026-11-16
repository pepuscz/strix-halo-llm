#!/usr/bin/env python3
"""Render the per-model charts, README tables and DeepSeek-V4.1 benchmark details from the published aggregates."""
import argparse
import html
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'benchmarks/results.json'
M5 = 'BOSGAME M5 (Ryzen AI Max+ 395, Radeon 8060S, 128 GiB RAM)'
# One chart per model: its file, the hardware in plain words, its curves (system, colour, dashed) and an optional note.
CHARTS = [
    ('docs/benchmark-deepseek-v41.svg', f'{M5} with two RX 7900 XTX cards, or one',
     [('maya-ds4-exl3-dual-xtx', '#cf222e', False), ('maya-ds4-exl3-single-xtx', '#cf222e', True),
      ('maya-ds4-gsq-dual-xtx', '#8250df', False), ('maya-ds4-maya-s-dual-xtx', '#0969da', False),
      ('maya-ds4-maya-xs-dual-xtx', '#bc4c00', False)],
     'EXL3: 1M allocation · other quants: 512K · runtime versions and full protocol in BENCHMARKS.md'),
    ('docs/benchmark-glm.svg', f'{M5} with two RX 7900 XTX cards', [('maya-glm-dual-xtx', '#1a7f37', False)],
     'Allocation: the smallest of 128K, 256K and 512K that holds the input · full protocol in BENCHMARKS.md'),
    ('docs/benchmark-qwen.svg', f'{M5} alone',
     [('strata-qwen-q4xl', '#0969da', False), ('qwen-vulkan-q4xl', '#008577', False)], None),
    ('docs/benchmark-deepseek-v4-0731.svg', f'{M5} alone',
     [('vulkan-iq3xxs', '#8957e5', False), ('rocm-rocmfpx', '#bc4c00', False)], None),
]
# DeepSeek-V4.1-Flash-1017: the EXL3 2.25 bpw setup on each hardware option, and the quants compared on two cards
EXL3_HARDWARE = [('maya-ds4-exl3-dual-xtx', '2 × RX 7900 XTX'), ('maya-ds4-exl3-single-xtx', '1 × RX 7900 XTX')]
QUANTS = [('maya-ds4-exl3-dual-xtx', 'EXL3 2.25 bpw'), ('maya-ds4-gsq-dual-xtx', 'GSQ-RCO IQ2_XS'),
          ('maya-ds4-maya-s-dual-xtx', 'Maya-S IQ2_XXS'), ('maya-ds4-maya-xs-dual-xtx', 'Maya-XS v2 IQ1_S')]
SINGLE = 'maya-ds4-exl3-single-xtx'
STYLE = ('<style>text{font-family:Arial,sans-serif;fill:#24292f}.title{font-size:26px;font-weight:700}'
         '.sub{font-size:15px;fill:#57606a}.label{font-size:16px}.tick{font-size:13px;fill:#57606a}'
         '.panel{font-size:18px;font-weight:700}.grid{stroke:#d8dee4;stroke-dasharray:3 5}'
         '.value{font-size:14px;font-weight:700}</style>')
DASH = ' stroke-dasharray="8 5"'


def nice_max(values):
    """The smallest axis maximum at or above every value whose quarter steps are round numbers."""
    top = max(values)
    unit = 10 ** math.floor(math.log10(top / 4))
    return next(round(4 * step * unit, 6) for step in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 7.5, 10) if 4 * step * unit >= top)


def spread(labels, top, bottom):
    """Label heights at least 16 px apart, centred on their points and kept inside the panel."""
    placed = []
    for desired, *_ in labels:
        placed.append(max(desired, placed[-1] + 16) if placed else desired)
    shift = sum(y - item[0] for y, item in zip(placed, labels)) / len(placed)
    placed = [y - shift for y in placed]
    placed = [y + max(0, top + 8 - placed[0]) for y in placed]
    return [y - max(0, placed[-1] - bottom - 8) for y in placed]


def chart(data, hardware, series, note):
    """Prefill and decode against input length for one model's setups, the winning setup bold in the legend."""
    systems = data['systems']
    model = systems[series[0][0]]['model']
    left, right, height, xmin, xmax = 80, 1020, 165, 1800, 524288
    first = 139 + 24 * len(series)   # the first panel's top, below the legend
    end = first + 245 + height       # the second panel's bottom
    total = end + (155 if note else 130)

    def x(tokens):
        return left + math.log(tokens / xmin) / math.log(xmax / xmin) * (right - left)

    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 {total}" role="img" aria-labelledby="title desc">',
             f'<title id="title">{model} throughput</title>',
             f'<desc id="desc">Reading and answer-writing speeds of {model} on the {html.escape(hardware)}. The test asks the '
             'model to find five labelled phrases placed in a long text. Every run found all five correctly. Each point '
             'measures one request at the input length shown. Each horizontal tick doubles the input length.</desc>',
             STYLE, f'<rect width="1100" height="{total}" fill="white"/>',
             f'<text x="70" y="40" class="title">{model}</text>',
             f'<text x="70" y="67" class="sub">{html.escape(hardware)} · thinking off</text>']
    for i, (sid, color, dashed) in enumerate(series):
        yy = 99 + i * 24
        weight = 700 if sid in data['winning_setups'].values() else 400
        lines += [f'<line x1="70" y1="{yy}" x2="98" y2="{yy}" stroke="{color}" stroke-width="3"{DASH if dashed else ""}/>',
                  f'<text x="110" y="{yy+5}" class="label" style="font-weight:{weight}">{html.escape(systems[sid]["name"])}</text>']
    for title, key, top in (('Reading the input (tokens/second) · higher is better', 'prefill_tokens_per_second', first),
                            ('Writing the answer (tokens/second) · higher is better', 'decode_tokens_per_second', first + 245)):
        curves = [(color, dashed, [p for p in systems[sid]['context_scaling'] if isinstance(p.get(key), (int, float))])
                  for sid, color, dashed in series]
        maximum = nice_max([p[key] for *_, points in curves for p in points])
        bottom = top + height

        def y(value):
            return bottom - value / maximum * height
        lines.append(f'<text x="80" y="{top-20}" class="panel">{title}</text>')
        for fraction in [0, .25, .5, .75, 1]:
            yy = y(maximum * fraction)
            lines += [f'<line class="grid" x1="80" y1="{yy:.2f}" x2="1020" y2="{yy:.2f}"/>',
                      f'<text class="tick" x="68" y="{yy+4:.2f}" text-anchor="end">{maximum*fraction:g}</text>']
        for exp in range(1, 10):
            xx = x(1024 * 2**exp)
            lines += [f'<line class="grid" x1="{xx:.2f}" y1="{top}" x2="{xx:.2f}" y2="{bottom}"/>',
                      f'<text class="tick" x="{xx:.2f}" y="{bottom+22}" text-anchor="middle">{2**exp}K</text>']
        labels = []
        for color, dashed, points in curves:
            coords = [(x(p['actual_input_tokens']), y(p[key])) for p in points]
            path = ' '.join(('M' if i == 0 else 'L') + f'{xx:.2f} {yy:.2f}' for i, (xx, yy) in enumerate(coords))
            lines.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.7"{DASH if dashed else ""}/>')
            for p, (xx, yy) in zip(points, coords):
                lines.append(f'<circle cx="{xx:.2f}" cy="{yy:.2f}" r="4" fill="{color}"><title>{p["actual_input_tokens"]:,} tokens: {p[key]:.2f}</title></circle>')
            labels.append((coords[-1][1] + 4, *coords[-1], points[-1][key], color))
        # end-of-line values: the curves that end in the same column share it, spread apart
        groups = []
        for label in sorted(labels, key=lambda label: label[1]):
            if groups and label[1] - groups[-1][0][1] < 60:
                groups[-1].append(label)
            else:
                groups.append([label])
        for group in groups:
            group.sort()
            for label_y, (_, xx, yy, value, color) in zip(spread(group, top, bottom), group):
                lines += [f'<line x1="{xx:.2f}" y1="{yy:.2f}" x2="{xx+23:.2f}" y2="{label_y-4:.2f}" stroke="{color}" stroke-width="1"/>',
                          f'<text class="value" x="{xx+31:.2f}" y="{label_y:.2f}" text-anchor="start" style="fill:{color}">{value:.1f}</text>']
    lines += [f'<text x="550" y="{end+55}" text-anchor="middle" class="label">Input length (tokens; each tick doubles)</text>',
              f'<text x="550" y="{end+90}" text-anchor="middle" class="label">Test: find five phrases hidden in a long text. Every run found all five correctly.</text>']
    if note:
        lines.append(f'<text x="550" y="{end+120}" text-anchor="middle" class="tick">{html.escape(note)}</text>')
    return '\n'.join(lines + ['</svg>', ''])


def reading(value, digits=1):
    return f'{value:,.{digits}f}' if isinstance(value, (int, float)) else str(value)


def at(system, tokens=122879):
    return next(p for p in system['context_scaling'] if p['actual_input_tokens'] == tokens)


def bench(system):
    return system['maya_bench']['this_release']


def table(data, corner, columns, rows):
    """One column per (system, heading), the winning setup's heading bold; one row per (label, cell function)."""
    winners = set(data['winning_setups'].values())
    systems = [data['systems'][sid] for sid, _ in columns]
    head = [f'**{name}**' if sid in winners else name for sid, name in columns]
    return (['| ' + ' | '.join([corner, *head]) + ' |', '|---' + '|---:' * len(columns) + '|'] +
            ['| ' + ' | '.join([label, *map(cell, systems)]) + ' |' for label, cell in rows])


def longest(system):
    return '1M' if system['context_allocation'] == 1048576 else '512K'


SPEED_ROWS = [('Decode, short prompt', lambda v: f"{bench(v)['decode_mean_tokens_per_second']:.0f}"),
              ('Decode, 128K input', lambda v: f"{at(v)['decode_tokens_per_second']:.0f}"),
              ('Prefill, 8K input', lambda v: f"{bench(v)['prefill_tokens_per_second']['8192']:,.0f}"),
              ('Prefill, 128K input', lambda v: f"{at(v)['prefill_tokens_per_second']:,.0f}")]


def hardware_table(data):
    return table(data, 'EXL3 2.25 bpw', EXL3_HARDWARE, SPEED_ROWS + [
        ('Real code, 130K tokens: prefill / decode',
         lambda v: f"{v['long_context']['prefill_tokens_per_second']:,.0f} / {v['long_context']['decode_tokens_per_second']:.0f}"),
        ('Ansible recipe', lambda v: f"[recipe]({v['manifest']})")])


def comparison_table(data):
    return table(data, '2 × RX 7900 XTX', QUANTS, [
        ('Longest input', longest),
        ('Model size, excluding Engram', lambda v: f"{v['target']['model_bytes']/1e9:.0f} GB"),
        ('Perplexity (lower is better)', lambda v: f"{v['quality']['perplexity']['value']:.2f}"),
        ('Quality checks passed', lambda v: f"{v['quality']['total']}/30"), *SPEED_ROWS])


def render_readme(data, text):
    for name, body in (('exl3-hardware-table', '\n'.join(hardware_table(data))), ('quant-comparison-note', xs_summary(data)),
                       ('quant-comparison-table', '\n'.join(comparison_table(data)))):
        start = '<!-- ' + name + ' -->'
        end = '<!-- /' + name + ' -->'
        before, rest = text.split(start, 1)
        _, after = rest.split(end, 1)
        text = before + start + '\n' + body + '\n' + end + after
    return text


def at_128k(system):
    return at(system)['decode_tokens_per_second']


def xs_summary(data):
    x = data['systems']['maya-ds4-exl3-dual-xtx']
    g = data['systems']['maya-ds4-gsq-dual-xtx']
    lead = ("EXL3 supports 1M context and decodes faster than GSQ-RCO at long inputs; " if at_128k(x) > at_128k(g)
            else "EXL3 supports 1M context. GSQ-RCO decodes faster at long inputs; ")
    xs = data['systems']['maya-ds4-maya-xs-dual-xtx']

    def pre(v):
        return bench(v)['prefill_tokens_per_second']['8192'], at(v)['prefill_tokens_per_second']
    if all(a > b for a, b in zip(pre(x), pre(xs))):   # (EXL3 reads prompts faster at 8K and 128K: XS keeps decode only)
        return lead + "it also reads prompts fastest. Maya-XS v2 decodes fastest, with higher perplexity."
    return lead + "Maya-XS v2 is the fastest, with higher perplexity."


def same_exl3_engine(data):
    """Whether the one-card and two-card EXL3 releases run the same engine tag."""
    systems = data['systems']
    return systems[SINGLE]['runtime']['release_tag'] == systems[SINGLE.replace('single', 'dual')]['runtime']['release_tag']


def fork_version(system):
    return re.search(r'v\d+\.\d+\.\d+', system['runtime']['upstream']).group(0)


def stock_version(system):
    return re.search(r'v\d+\.\d+\.\d+', system['upstream_benchmark']['procedure']).group(0)


def detailed_table(data):
    def five(v, tokens):
        return reading(at(v, tokens)['decode_tokens_per_second']) + ' / ' + reading(at(v, tokens)['prefill_tokens_per_second'], 0)

    def prefill(v):
        return ' / '.join(reading(bench(v)['prefill_tokens_per_second'][n], 0) for n in ('2048', '8192'))
    return table(data, '2 × RX 7900 XTX', QUANTS, [
        ('Context allocation', longest),
        ('Model shards, excluding Engram', lambda v: f"{v['target']['model_bytes']/1e9:.0f} GB"),
        ('Perplexity (23 × 2,048 tokens; lower is better)', lambda v: reading(v['quality']['perplexity']['value'], 4)),
        ('Quality', lambda v: f"{v['quality']['total']}/30"),
        ('520K retrieval', lambda v: f"{v['deep_needle']['needle_passes']}/5"),
        ('1.04M retrieval', lambda v: f"{v['near_capacity_needle']['needle_passes']}/5" if v.get('near_capacity_needle') else '—'),
        ('Fixed-input Maya benchmark: decode', lambda v: reading(bench(v)['decode_mean_tokens_per_second'])),
        ('Fixed-input Maya benchmark: prefill 2K / 8K', prefill),
        ('128K five-phrase: decode / prefill', lambda v: five(v, 122879)),
        ('480K five-phrase: decode / prefill', lambda v: five(v, 491520)),
        ('Real code, 130,048 tokens: prefill', lambda v: reading(v['long_context']['prefill_tokens_per_second'], 0)),
        ('Real code: decode cold / prompt cached', lambda v: reading(v['long_context']['decode_tokens_per_second']) + ' / ' +
         reading(v['long_context']['reused_prompt']['decode_tokens_per_second']))])


def detailed_summary(data):
    x = data['systems']['maya-ds4-exl3-dual-xtx']
    xs = data['systems']['maya-ds4-maya-xs-dual-xtx']
    g = data['systems']['maya-ds4-gsq-dual-xtx']
    faster = (f"It also decodes faster at long context ({at_128k(x):.1f} against GSQ-RCO's {at_128k(g):.1f} tokens/s at 128K). "
              if at_128k(x) > at_128k(g) else
              f"GSQ-RCO decodes faster at long context ({at_128k(g):.1f} against {at_128k(x):.1f} tokens/s at 128K). ")
    return (f"EXL3 supports 1M context and has the lowest measured perplexity ({x['quality']['perplexity']['value']:.4f}). "
            f"{faster}"
            f"Maya-XS v2 has the fastest recorded decode, with higher perplexity ({xs['quality']['perplexity']['value']:.4f}).")


def scaling_rows(system):
    return (['| Input tokens | Prefill (tok/s) | Decode (tok/s) | Values |', '|---:|---:|---:|---:|'] +
            [f"| {x['actual_input_tokens']:,} | {reading(x['prefill_tokens_per_second'])} | {reading(x['decode_tokens_per_second'])} | {x['needle_passes']}/5 |"
             for x in system['context_scaling']])


def render_deepseek_details(data, text):
    """The DeepSeek-V4.1-Flash-1017 chapter of BENCHMARKS.md: two cards, its quants, then one card."""
    systems = data['systems']
    e = systems[QUANTS[0][0]]
    winners = set(data['winning_setups'].values())
    lines = ['## DeepSeek-V4.1-Flash-1017', '',
             '![DeepSeek-V4.1-Flash-1017 context scaling on two RX 7900 XTX cards and on one](benchmark-deepseek-v41.svg)', '',
             f"**{e['name']}** uses the qualified {fork_version(e)}-based fork{' with the full-rate HIP EXL3 decode kernels' if 'full-rate' in e['runtime']['upstream'] else ''}, original FP8 Engram, 16K prompt chunks and 1M context. [Ansible recipe](../{e['manifest']}).", '',
             'GSQ, Maya-S and Maya-XS measurements use the v1.1.48 indexer engine at 512K. EXL3 uses 1M. The eleven curve points share identical input bytes, zero cached input, thinking off and a 256-token cap; each load is fresh, from the frozen profile. All five values were found at every point.', '',
             *detailed_table(data), '', detailed_summary(data), '',
             'GSQ and EXL3 report medians of three loads per point; Maya-S and Maya-XS each report one load. Cached decode uses three consecutive answers per load. Different answer text and draft acceptance mean these decode rates do not isolate kernel speed.', '',
             '### Recorded context scaling', '']
    for sid, _ in QUANTS:
        v = systems[sid]
        lines += ['#### ' + (f"**{v['name']}**" if sid in winners else v['name']), '', *scaling_rows(v)]
        if v.get('near_capacity_needle'):
            x = v['near_capacity_needle']
            lines += ['', f"The separate **{x['actual_input_tokens']:,}-token** check found **{x['needle_passes']}/5** values with zero cached input: **{reading(x['prefill_tokens_per_second'])} prefill / {reading(x['decode_tokens_per_second'])} decode tok/s**."]
        lines.append('')
    lines += ['### Fixed-input Maya benchmark', '',
              'The [driver](../benchmarks/maya_bench.py) and [token fixture](../benchmarks/maya-bench-inputs.json) retain the public v1.1.28 benchmark procedure: three 256-token answers, greedy and thinking off, plus 2,048- and 8,192-token prompts. The comparison table above uses these same inputs for every quant.', '',
              f"### Upstream {stock_version(e)} benchmark at 1M", '',
              'A separate source-native `maya.py --bench` comparison used the same actual token IDs, a 1,048,576-token allocation and two cold loads per arm, in optimized EXL3 / GSQ / stock EXL3 order, repeated once. These documentation tokens differ from the fixed-input fixture above.', '',
              '| Setup | Decode mean (tok/s) | Prefill 2K / 8K (tok/s) |', '|---|---:|---:|']
    for arm, label in [('E+', '**Optimized EXL3 2.25**'), ('G', f'GSQ-RCO IQ2_XS, stock {stock_version(e)}'), ('E0', f'EXL3 2.25, stock {stock_version(e)}')]:
        m = e['upstream_benchmark']['arms'][arm]['mean']
        lines.append(f"| {label} | {reading(m['decode'])} | {reading(m['prefill']['2048'])} / {reading(m['prefill']['8192'])} |")
    lines += ['', "Optimized EXL3: this release's binary and recipe (a 109 GB helper pool with the drafter's leftover experts, ~5 GB read ahead). Stock EXL3: v1.1.56 with the stock reference recipe (a 95 GB pool, 14.9 GB read ahead, no DS4_HELPER_DRAFT). GSQ: its own recipe at 1M. Each decode mean covers three answers.", '',
              '### Quality and teacher comparison', '',
              f"Cold coding/maths suite: EXL3 {e['quality']['total']}/30; GSQ, Maya-S and Maya-XS 30/30 (math_08 scored against its corrected gold answer). Perplexity in the main table: 23 × 2,048 tokens.", '',
              'The separate Lucebox held-out set has eight 1,024-token sequences and 8,184 predictions. KL uses the teacher’s top 256 probabilities; lower is better. Top-1 is agreement with the teacher.', '',
              '| Quant | KL | Top-1 agreement | Held-out PPL |', '|---|---:|---:|---:|']
    for sid, label in [(QUANTS[0][0], f'**EXL3 2.25 ({fork_version(e)} fork)**'), (QUANTS[1][0], 'GSQ-RCO IQ2_XS (v1.1.50 indexer)')]:
        z = systems[sid]['quality']['lucebox_kl']['all']
        lines.append(f"| {label} | {z['kl_top256']:.4f} | {z['top1_agree']*100:.2f}% | {z['ppl']:.4f} |")
    lines += ['', "Maya-S and Maya-XS have no KL measurement. [Exact data and input hashes](../benchmarks/results.json).", '',
              *single_details(data)]
    a = text.index('\n## DeepSeek-V4.1-Flash-1017\n') + 1
    b = text.index('\n## GLM-5.3-Flash\n', a) + 1
    return text[:a] + '\n'.join(lines) + '\n' + text[b:]


def single_details(data):
    """The one-card release: its needles, real-code prompt, quality, curve and native --bench rows."""
    v = data['systems'][SINGLE]
    c = v['long_context']
    q = v['quality']
    b = bench(v)
    dual = data['systems'][SINGLE.replace('single', 'dual')]
    lines = ['### One RX 7900 XTX', '',
             (f"**{v['name']}** runs the same EXL3 2.25 bpw model and {fork_version(v)}-based engine as the dual recipe on one card, for a host without a second one." if same_exl3_engine(data) else
              f"**{v['name']}** runs the same EXL3 2.25 bpw model on one card, for a host without a second one, on the {fork_version(v)}-based engine tag `{v['runtime']['release_tag']}`. The two-card line in the chart is the dual release (engine tag `{dual['runtime']['release_tag']}`).") +
             f" The Radeon 8060S holds a 113 GB expert pool, prompts run in 8K chunks (one card lends the prompt path no VRAM, so its buffers stay), and the DSpark blocks' experts all sit in the pool. [Ansible recipe](../{v['manifest']}).", '',
             f"Quality **{q['total']}/30**, perplexity **{reading(q['perplexity']['value'],4)}** (23 × 2,048 tokens). The 130,048-token real-code prompt: **{reading(c['prefill_tokens_per_second'],0)}** prefill, **{reading(c['decode_tokens_per_second'])}** decode cold, **{reading(c['reused_prompt']['decode_tokens_per_second'])}** with the prompt cached. Fixed-input Maya benchmark: **{reading(b['decode_mean_tokens_per_second'])}** decode, **{reading(b['prefill_tokens_per_second']['2048'],0)} / {reading(b['prefill_tokens_per_second']['8192'],0)}** prefill at 2K / 8K.", '',
             'One fresh load per point, the same eleven prompts as the dual recipe, zero cached input, thinking off.', '',
             *scaling_rows(v)]
    for key, label in (('deep_needle', 'deep'), ('near_capacity_needle', 'near-capacity')):
        if v.get(key):
            x = v[key]
            lines += ['', f"The {label} **{x['actual_input_tokens']:,}-token** check found **{x['needle_passes']}/5** values with zero cached input: **{reading(x['prefill_tokens_per_second'])} prefill / {reading(x['decode_tokens_per_second'])} decode tok/s**."]
    lines += ['', f"#### Upstream {stock_version(v)} benchmark", '',
              'Source-native `maya.py --bench`, the same token IDs as the dual recipe\'s, two cold loads per arm, interleaved.', '',
              '| Setup | Decode mean (tok/s) | Prefill 2K / 8K (tok/s) |', '|---|---:|---:|']
    for arm, label in [('S+', '**This release**'), ('S0', f'Stock {stock_version(v)}, the same settings without DS4_HELPER_DRAFT')]:
        m = v['upstream_benchmark']['arms'][arm]['mean']
        lines.append(f"| {label} | {reading(m['decode'])} | {reading(m['prefill']['2048'])} / {reading(m['prefill']['8192'])} |")
    return lines + ['', 'On one card the release differs from stock by DS4_HELPER_DRAFT (#904).', '']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = json.loads(DATA.read_text())
    outputs = [(ROOT / path, chart(data, hardware, series, note)) for path, hardware, series, note in CHARTS]
    outputs += [(ROOT / 'README.md', render_readme(data, (ROOT / 'README.md').read_text())),
                (ROOT / 'docs/BENCHMARKS.md', render_deepseek_details(data, (ROOT / 'docs/BENCHMARKS.md').read_text()))]
    for output, expected in outputs:
        if args.check:
            if not output.exists() or output.read_text() != expected:
                raise SystemExit(f'{output.name} is stale; run scripts/render_benchmark.py')
        else:
            output.write_text(expected)


if __name__ == '__main__':
    main()
