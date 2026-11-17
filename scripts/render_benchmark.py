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
    ('docs/benchmark-deepseek-v41-hardware.svg', f'EXL3 2.25 bpw · {M5} alone, or with one or two RX 7900 XTX cards',
     [('maya-ds4-exl3-dual-xtx', '#cf222e', False), ('maya-ds4-exl3-single-xtx', '#bc4c00', False),
      ('maya-ds4-exl3-apu', '#0969da', False)],
     '1M allocation · runtime versions and full protocol in BENCHMARKS.md', True),
    ('docs/benchmark-deepseek-v41-quants.svg', f'{M5} with two RX 7900 XTX cards',
     [('maya-ds4-exl3-dual-xtx', '#cf222e', False), ('maya-ds4-gsq-dual-xtx', '#8250df', False),
      ('maya-ds4-maya-s-dual-xtx', '#0969da', False), ('maya-ds4-maya-xs-dual-xtx', '#bc4c00', False)],
     'EXL3: 1M allocation · other quants: 512K · runtime versions and full protocol in BENCHMARKS.md', False),
    ('docs/benchmark-glm.svg', f'{M5} with two RX 7900 XTX cards', [('maya-glm-dual-xtx', '#1a7f37', False)],
     'Allocation: the smallest of 128K, 256K and 512K that holds the input · full protocol in BENCHMARKS.md', False),
    ('docs/benchmark-qwen.svg', f'{M5} alone',
     [('strata-qwen-q4xl', '#0969da', False), ('qwen-vulkan-q4xl', '#008577', False)], None, False),
    ('docs/benchmark-deepseek-v4-0731.svg', f'{M5} alone',
     [('vulkan-iq3xxs', '#8957e5', False), ('rocm-rocmfpx', '#bc4c00', False)], None, False),
]
# DeepSeek-V4.1-Flash-1017: the EXL3 2.25 bpw setup on each hardware option, and the quants compared on two cards
EXL3_HARDWARE = [('maya-ds4-exl3-apu', 'M5 alone'), ('maya-ds4-exl3-single-xtx', '1 × RX 7900 XTX'),
                 ('maya-ds4-exl3-dual-xtx', '2 × RX 7900 XTX')]
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


def second(point):
    """A point's second run (the same request again after 60 s idle, in the same load), as a point; None: not run."""
    run = point.get('second_run')
    return {**run, 'actual_input_tokens': point['actual_input_tokens']} if run else None


def chart(data, hardware, series, note, seconds=False):
    """Prefill and decode against input length for one model's setups, the winning setup bold in the legend;
    seconds: each setup's second runs as a dashed curve of its colour."""
    systems = data['systems']
    series = [x for x in series if x[0] in systems]   # (a hardware option without a release yet: no curve)
    seconds = seconds and any(second(p) for sid, *_ in series for p in systems[sid]['context_scaling'])
    if seconds:
        note = 'Solid: first run on a fresh load · dashed: the same request again after 60 s idle · ' + note
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
        if seconds:
            curves += [(color, True, [q for q in map(second, systems[sid]['context_scaling'])
                                      if q and isinstance(q.get(key), (int, float))])
                       for sid, color, _ in series]
            curves = [c for c in curves if c[2]]
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
    columns = [(sid, name) for sid, name in columns if sid in data['systems']]
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


def runs(first, again, fmt):
    """A cell: the first run, and the second run after 60 s idle when there is one."""
    return fmt(first) + (' / ' + fmt(again) if again is not None else '')


def hardware_table(data):
    """EXL3 2.25 bpw on each hardware option; first / second run where the release measured both."""
    two = any('second_run' in bench(data['systems'][sid]) for sid, _ in EXL3_HARDWARE if sid in data['systems'])
    b2 = lambda v: bench(v).get('second_run') or {}
    c2 = lambda v: v['long_context'].get('second_run') or {}
    a2 = lambda v: at(v).get('second_run') or {}
    whole = lambda x: f'{x:,.0f}'
    return table(data, 'EXL3 2.25 bpw' + (', first / second run' if two else ''), EXL3_HARDWARE, [
        ('Decode, short prompt', lambda v: runs(bench(v)['decode_mean_tokens_per_second'], b2(v).get('decode_mean_tokens_per_second'), whole)),
        ('Decode, 128K input', lambda v: runs(at(v)['decode_tokens_per_second'], a2(v).get('decode_tokens_per_second'), whole)),
        ('Decode, real code (130K tokens)', lambda v: runs(v['long_context']['decode_tokens_per_second'], c2(v).get('decode_tokens_per_second'), whole)),
        ('Prefill, 8K input', lambda v: runs(bench(v)['prefill_tokens_per_second']['8192'], (b2(v).get('prefill_tokens_per_second') or {}).get('8192'), whole)),
        ('Prefill, 128K input', lambda v: runs(at(v)['prefill_tokens_per_second'], a2(v).get('prefill_tokens_per_second'), whole)),
        ('Prefill, real code (130K tokens)', lambda v: runs(v['long_context']['prefill_tokens_per_second'], c2(v).get('prefill_tokens_per_second'), whole)),
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


HARDWARE_NOTES = {
    'maya-ds4-exl3-apu': 'the Radeon 8060S runs the whole model, with 20 GiB of RAM kept out of its expert budget; '
                         '16K prompt chunks',
    'maya-ds4-exl3-single-xtx': 'the card runs the model and the Radeon 8060S holds a 113 GB expert pool; 8K prompt chunks',
    'maya-ds4-exl3-dual-xtx': 'the two cards run the model tensor parallel and the Radeon 8060S holds a 109 GB expert pool; '
                              '16K prompt chunks',
}


def both(first, again, digits=1):
    return reading(first, digits) + (' / ' + reading(again, digits) if again is not None else '')


def exl3_details(data):
    """EXL3 2.25 bpw on each hardware option: first and second runs side by side."""
    systems = data['systems']
    cols = [(sid, name) for sid, name in EXL3_HARDWARE if sid in systems]
    e = systems['maya-ds4-exl3-dual-xtx']

    def point(tokens, key, digits):
        return lambda v: both(at(v, tokens)[key], (at(v, tokens).get('second_run') or {}).get(key), digits)
    b2 = lambda v: bench(v).get('second_run') or {}
    c2 = lambda v: v['long_context'].get('second_run') or {}
    rows = [
        ('Maya `--bench` decode', lambda v: both(bench(v)['decode_mean_tokens_per_second'], b2(v).get('decode_mean_tokens_per_second'))),
        ('Maya `--bench` prefill, 2K', lambda v: both(bench(v)['prefill_tokens_per_second']['2048'], (b2(v).get('prefill_tokens_per_second') or {}).get('2048'), 0)),
        ('Maya `--bench` prefill, 8K', lambda v: both(bench(v)['prefill_tokens_per_second']['8192'], (b2(v).get('prefill_tokens_per_second') or {}).get('8192'), 0)),
        ('128K five-phrase: decode', point(122879, 'decode_tokens_per_second', 1)),
        ('128K five-phrase: prefill', point(122879, 'prefill_tokens_per_second', 0)),
        ('480K five-phrase: decode', point(491520, 'decode_tokens_per_second', 1)),
        ('480K five-phrase: prefill', point(491520, 'prefill_tokens_per_second', 0)),
        ('Real code, 130,048 tokens: decode', lambda v: both(v['long_context']['decode_tokens_per_second'], c2(v).get('decode_tokens_per_second'))),
        ('Real code, 130,048 tokens: prefill', lambda v: both(v['long_context']['prefill_tokens_per_second'], c2(v).get('prefill_tokens_per_second'), 0)),
        ('Expert picks served from GPU memory', lambda v: both(v['placement']['vram_share_of_picks']['run1'] * 100, v['placement']['vram_share_of_picks']['run2'] * 100, 0).replace(' / ', ' % / ') + ' %' if v.get('placement') else '—'),
    ]
    lines = ['### EXL3 2.25 bpw on each hardware option', '',
             '![DeepSeek-V4.1-Flash-1017 EXL3 2.25 bpw context scaling on each hardware option](benchmark-deepseek-v41-hardware.svg)', '',
             (f"**Maya DS4 HIP EXL3 2.25 bpw** runs the same model files and {fork_version(e)}-based engine (`{e['runtime']['release_tag']}`) on the M5 alone, with one RX 7900 XTX, or with two."
              if same_exl3_engine(data) else
              f"**Maya DS4 HIP EXL3 2.25 bpw** runs the same model files on the M5 alone, with one RX 7900 XTX, or with two: two cards on the newer engine (`{e['runtime']['release_tag']}`, shorter prompt reads), one card and the M5 alone on `{systems[SINGLE]['runtime']['release_tag']}`.")
             + " Every request is a fresh cold load at a 1M allocation, thinking off, nothing read from a cache. Each cell gives the first run and the second run: the same request again in the same load after 60 s idle. With a card, the engine moves the experts the request used from the 8060S's pool into VRAM while idle; on the M5 alone the expert cache and the page cache warm up instead.", '',
             *table(data, 'First / second run', cols, rows), '']
    for sid, name in cols:
        v = systems[sid]
        lines.append(f"- **{name}** ([recipe](../{v['manifest']})): {HARDWARE_NOTES[sid]}.")
    n = e['near_capacity_needle']
    q = e['quality']
    lines += ['', f"On two cards the **{n['actual_input_tokens']:,}-token** check found **{n['needle_passes']}/5** values: **{reading(n['prefill_tokens_per_second'],0)} prefill / {reading(n['decode_tokens_per_second'])} decode tok/s**. "
              f"Perplexity with this engine: **{reading(q['perplexity']['value'],4)}** (23 × 2,048 tokens). The answer-quality score (**{q['total']}/30**) and the Lucebox KL below were measured with the 12 Nov engine; the one-card and M5-alone recipes run the same model files" + (" and engine." if same_exl3_engine(data) else f" on `{systems[SINGLE]['runtime']['release_tag']}`."), '',
              '#### Recorded context scaling', '']
    for sid, name in cols:
        v = systems[sid]
        lines += [f'**{name}**', '', '| Input tokens | Prefill, first / second run | Decode, first / second run | Values |', '|---:|---:|---:|---:|']
        for x in v['context_scaling']:
            r2 = x.get('second_run') or {}
            lines.append(f"| {x['actual_input_tokens']:,} | {both(x['prefill_tokens_per_second'], r2.get('prefill_tokens_per_second'))} | "
                         f"{both(x['decode_tokens_per_second'], r2.get('decode_tokens_per_second'))} | {x['needle_passes']}/5 |")
        lines.append('')
    return lines


def detailed_table(data):
    def five(v, tokens):
        return reading(at(v, tokens)['decode_tokens_per_second']) + ' / ' + reading(at(v, tokens)['prefill_tokens_per_second'], 0)

    def prefill(v):
        return ' / '.join(reading(bench(v)['prefill_tokens_per_second'][n], 0) for n in ('2048', '8192'))

    def deepest(v):
        x = v.get('near_capacity_needle') or v.get('deep_needle')
        return f"{x['needle_passes']}/5 at {x['actual_input_tokens']/1e6:.2f}M" if x and x['actual_input_tokens'] >= 1e6 else f"{x['needle_passes']}/5 at {x['actual_input_tokens']//1000}K"
    return table(data, '2 × RX 7900 XTX', QUANTS, [
        ('Context allocation', longest),
        ('Model shards, excluding Engram', lambda v: f"{v['target']['model_bytes']/1e9:.0f} GB"),
        ('Perplexity (23 × 2,048 tokens; lower is better)', lambda v: reading(v['quality']['perplexity']['value'], 4)),
        ('Quality', lambda v: f"{v['quality']['total']}/30"),
        ('Deepest retrieval', deepest),
        ('Maya benchmark: decode', lambda v: reading(bench(v)['decode_mean_tokens_per_second'])),
        ('Maya benchmark: prefill 2K / 8K', prefill),
        ('128K five-phrase: decode / prefill', lambda v: five(v, 122879)),
        ('480K five-phrase: decode / prefill', lambda v: five(v, 491520)),
        ('Real code, 130,048 tokens: decode / prefill', lambda v: reading(v['long_context']['decode_tokens_per_second']) + ' / ' +
         reading(v['long_context']['prefill_tokens_per_second'], 0))])


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
    """The DeepSeek-V4.1-Flash-1017 chapter of BENCHMARKS.md: EXL3 on each hardware option, then the quants on two cards."""
    systems = data['systems']
    e = systems[QUANTS[0][0]]
    winners = set(data['winning_setups'].values())
    lines = ['## DeepSeek-V4.1-Flash-1017', '', *exl3_details(data),
             '### Quants on two RX 7900 XTX', '',
             '![DeepSeek-V4.1-Flash-1017 context scaling, four quants on two RX 7900 XTX cards](benchmark-deepseek-v41-quants.svg)', '',
             "GSQ, Maya-S and Maya-XS were measured with the v1.1.48 indexer engine at 512K: eleven curve points, medians of three loads for GSQ and one load for Maya-S and Maya-XS, and the [fixed-input Maya benchmark](../benchmarks/maya_bench.py) ([token fixture](../benchmarks/maya-bench-inputs.json)). EXL3's column is the two-card release above (first runs, Maya's own `--bench` requests). Thinking off, zero cached input, a 256-token cap.", '',
             *detailed_table(data), '', detailed_summary(data), '',
             'Different answer text and draft acceptance mean these decode rates do not isolate kernel speed.', '']
    for sid, _ in QUANTS[1:]:
        v = systems[sid]
        lines += ['#### ' + (f"**{v['name']}**" if sid in winners else v['name']), '', *scaling_rows(v), '']
    lines += ['### Quality and teacher comparison', '',
              f"Cold coding/maths suite: EXL3 {e['quality']['total']}/30 (12 Nov engine); GSQ, Maya-S and Maya-XS 30/30 (math_08 scored against its corrected gold answer). Perplexity in the tables: 23 × 2,048 tokens.", '',
              'The separate Lucebox held-out set has eight 1,024-token sequences and 8,184 predictions. KL uses the teacher’s top 256 probabilities; lower is better. Top-1 is agreement with the teacher.', '',
              '| Quant | KL | Top-1 agreement | Held-out PPL |', '|---|---:|---:|---:|']
    for sid, label in [(QUANTS[0][0], '**EXL3 2.25** (12 Nov engine)'), (QUANTS[1][0], 'GSQ-RCO IQ2_XS (v1.1.50 indexer)')]:
        z = systems[sid]['quality']['lucebox_kl']['all']
        lines.append(f"| {label} | {z['kl_top256']:.4f} | {z['top1_agree']*100:.2f}% | {z['ppl']:.4f} |")
    lines += ['', "Maya-S and Maya-XS have no KL measurement. [Exact data and input hashes](../benchmarks/results.json).", '']
    a = text.index('\n## DeepSeek-V4.1-Flash-1017\n') + 1
    b = text.index('\n## GLM-5.3-Flash\n', a) + 1
    return text[:a] + '\n'.join(lines) + '\n' + text[b:]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = json.loads(DATA.read_text())
    outputs = [(ROOT / path, chart(data, hardware, series, note, seconds)) for path, hardware, series, note, seconds in CHARTS]
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
