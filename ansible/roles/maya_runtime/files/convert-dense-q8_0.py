#!/usr/bin/env python3
"""The dense matrices of a Maya DS4 pack converted to Q8_0: a GGUF quant that keeps the matrices the engine reads as
BF16 / Q8_0 (the attention projections, the shared experts, engram_wkv, the embedding, the head) in a K-quant - GSQ-RCO
keeps them Q5_K - cannot load as packed. This rewrites those tensors into <model_dir>/<file> as Q8_0 (the Q5_K blocks to
float, then ggml's Q8_0 rounding, in numpy) and points their tensors.txt lines there; every other tensor stays in the
GGUFs. Q8_0 is finer than Q5_K, so the quant stays the GGUF's. It can also fill the DSpark geometry a GGUF leaves out
of ds4.txt (--ds4 key=value: a key the GGUF set to 0 / empty, or left out, takes the value; one set otherwise refuses).

    python3 -I convert-dense-q8_0.py <pack> <model_dir> --file dense-q8_0.bin --tensors 524 --bytes 8236072960
                                     [--replace] [--ds4 dspark_block_size=5 ...]

Refuses, before writing, a plan other than --tensors entries of --bytes in all, a K-quant it has no converter for
(Q5_K only), a tensor not in whole 256-value blocks along its rows, or an existing side file without --replace. Prints
one JSON line and exits 0 when the side file and tensors.txt are written. Checked against llama.cpp's gguf-py: the
floats exact, the Q8_0 bytes equal but rounding ties (see tests/test_convert_dense_q8_0.py)."""
import argparse
import json
import os
import sys
from pathlib import Path

K_QUANTS = ('Q2_K', 'Q3_K', 'Q4_K', 'Q5_K', 'Q6_K')      # (ggml's K-quants: the engine reads none of them)
Q5K_BYTES, Q8_BYTES = 176, 34                             # (a 256-value Q5_K block; a 32-value Q8_0 block)
SIDE_ALIGN = 4096
CHUNK_ROWS_BYTES = 256 << 20                              # (a conversion reads this much Q5_K at a time)


def q5k_to_f32(raw, n_in):
    """ggml Q5_K blocks (256 values: d f16, dmin f16, 12 bytes of 6-bit scales and mins, 32 bytes of high bits, 128
    bytes of low nibbles) -> float32 rows of n_in values, as ggml's dequantize_row_q5_K."""
    import numpy as np
    b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, Q5K_BYTES)
    d = b[:, 0:2].copy().view(np.float16).astype(np.float32)
    dmin = b[:, 2:4].copy().view(np.float16).astype(np.float32)
    sc = b[:, 4:16].astype(np.uint32)
    qh, ql = b[:, 16:48], b[:, 48:176]
    scales = np.empty((b.shape[0], 8), np.float32)
    mins = np.empty((b.shape[0], 8), np.float32)
    for j in range(8):                                     # (get_scale_min_k4)
        if j < 4:
            scales[:, j], mins[:, j] = sc[:, j] & 63, sc[:, j + 4] & 63
        else:
            scales[:, j] = (sc[:, j + 4] & 15) | ((sc[:, j - 4] >> 6) << 4)
            mins[:, j] = (sc[:, j + 4] >> 4) | ((sc[:, j] >> 6) << 4)
    out = np.empty((b.shape[0], 256), np.float32)
    for c in range(4):                                     # (64 values a chunk: low nibbles, then high, each + a qh bit)
        lo = ql[:, c * 32:(c + 1) * 32]
        v1 = (lo & 15).astype(np.float32) + ((qh >> (2 * c)) & 1) * 16
        v2 = (lo >> 4).astype(np.float32) + ((qh >> (2 * c + 1)) & 1) * 16
        out[:, c * 64:c * 64 + 32] = d * scales[:, 2 * c:2 * c + 1] * v1 - dmin * mins[:, 2 * c:2 * c + 1]
        out[:, c * 64 + 32:c * 64 + 64] = d * scales[:, 2 * c + 1:2 * c + 2] * v2 - dmin * mins[:, 2 * c + 1:2 * c + 2]
    return out.reshape(-1, n_in)


def f32_to_q8_0(x):
    """float32 rows -> ggml Q8_0 blocks (32 values: d f16, 32 int8), as ggml's quantize_row_q8_0_ref."""
    import numpy as np
    v = x.reshape(-1, 32).astype(np.float32)
    d = np.abs(v).max(axis=1) / 127.0
    inv = np.where(d > 0, 1.0 / np.where(d > 0, d, 1), 0.0).astype(np.float32)
    q = np.rint(v * inv[:, None]).clip(-128, 127).astype(np.int8)
    out = np.empty((v.shape[0], Q8_BYTES), np.uint8)
    out[:, 0:2] = d.astype(np.float16).view(np.uint8).reshape(-1, 2)
    out[:, 2:] = q.view(np.uint8)
    return out.reshape(-1).tobytes()


def read_tensors(path):
    """tensors.txt -> (the file names by index, the `t` entries in order)."""
    files, entries = [], []
    for ln in Path(path).read_text().splitlines():
        p = ln.split()
        if p[:1] == ['file']:
            i = int(p[1])
            files += [None] * (i + 1 - len(files))
            files[i] = ln.split(' ', 2)[2]
        elif p[:1] == ['t']:
            entries.append({'name': p[1], 'dtype': p[2], 'file': int(p[3]), 'off': int(p[4]), 'bytes': int(p[5]),
                            'dims': [int(x) for x in p[6:]]})
    return files, entries


def write_tensors(path, files, entries):
    with open(path, 'w') as f:
        for i, n in enumerate(files):
            f.write(f'file {i} {n}\n')
        for e in entries:
            f.write(f't {e["name"]} {e["dtype"]} {e["file"]} {e["off"]} {e["bytes"]} {" ".join(map(str, e["dims"]))}\n')


def convert_plan(files, entries):
    """The K-quant entries outside the Engram's file, each with its place in the side file; (plan, side bytes, why)."""
    plan, why, off = [], [], 0
    for e in entries:
        if e['dtype'] not in K_QUANTS or 'Engram' in (files[e['file']] or ''):
            continue
        n = 1
        for x in e['dims']:
            n *= x
        if e['dtype'] != 'Q5_K':
            why.append(f'{e["name"]}: {e["dtype"]} - no converter (Q5_K only)')
        elif not e['dims'] or e['dims'][-1] % 256 or e['bytes'] != n // 256 * Q5K_BYTES:
            why.append(f'{e["name"]}: Q5_K {e["bytes"]} bytes of {e["dims"]} - not whole 256-value blocks along the rows')
        else:
            plan.append({'entry': e, 'side_off': off, 'side_bytes': n // 32 * Q8_BYTES})
            off = (off + n // 32 * Q8_BYTES + SIDE_ALIGN - 1) // SIDE_ALIGN * SIDE_ALIGN
    total = plan[-1]['side_off'] + plan[-1]['side_bytes'] if plan else 0
    return plan, total, why


def write_side(plan, files, model, side):
    """The planned tensors, each read from its GGUF in row chunks, converted and written at its side offset."""
    with open(side, 'wb') as out:
        for item in plan:
            e, n_in = item['entry'], item['entry']['dims'][-1]
            row_q5, row_q8 = n_in // 256 * Q5K_BYTES, n_in // 32 * Q8_BYTES
            rows = e['bytes'] // row_q5
            step = max(1, CHUNK_ROWS_BYTES // row_q5)
            out.seek(item['side_off'])
            with open(Path(model) / files[e['file']], 'rb') as src:
                src.seek(e['off'])
                for r0 in range(0, rows, step):
                    k = min(step, rows - r0)
                    raw = src.read(k * row_q5)
                    if len(raw) != k * row_q5:
                        raise SystemExit(f'{e["name"]}: short read at row {r0}')
                    q8 = f32_to_q8_0(q5k_to_f32(raw, n_in))
                    assert len(q8) == k * row_q8
                    out.write(q8)
        out.truncate(max((i['side_off'] + i['side_bytes'] for i in plan), default=0))


def patch_ds4(text, geometry):
    """ds4.txt with the geometry set: a key the GGUF left 0 / empty (or absent) takes the value; one it set to another
    value refuses. (the patched text, {key: (before, after)})"""
    out, changed, seen = [], {}, set()
    for ln in text.splitlines():
        k, _, v = ln.partition(' ')
        v = v.strip()
        if k in geometry:
            seen.add(k)
            if v not in ('', '0', geometry[k]):
                raise SystemExit(f'ds4.txt: {k} {v} - the GGUF sets it, not to {geometry[k]}: not patched')
            if v != geometry[k]:
                changed[k] = (v, geometry[k])
            ln = f'{k} {geometry[k]}'
        out.append(ln)
    missing = [k for k in geometry if k not in seen]
    if missing:                                             # (absent: inserted before `format`)
        at = next((i for i, ln in enumerate(out) if ln.startswith('format ')), len(out))
        out[at:at] = [f'{k} {geometry[k]}' for k in missing]
        changed.update({k: (None, geometry[k]) for k in missing})
    return '\n'.join(out) + '\n', changed


def convert(pack, model, file, tensors, nbytes, replace=False, geometry=None):
    pack, model = Path(pack), Path(model)
    files, entries = read_tensors(pack / 'tensors.txt')
    plan, total, why = convert_plan(files, entries)
    if (len(plan), total) != (tensors, nbytes):
        why.append(f'the plan is {len(plan)} tensors of {total} bytes, the release pins {tensors} of {nbytes}')
    side = model / file
    if (side.exists() or side.is_symlink()) and not replace:
        why.append(f'{side}: already there (--replace rewrites it)')
    if why:
        return {'reasons': why}
    changed = {}
    if geometry:
        text, changed = patch_ds4((pack / 'ds4.txt').read_text(), geometry)
        (pack / 'ds4.txt').write_text(text)
    part = side.with_name(file + '.tmp')
    try:
        write_side(plan, files, model, part)
        if part.stat().st_size != total:
            raise SystemExit(f'{part}: {part.stat().st_size} bytes written, planned {total}')
        os.chmod(part, 0o444)
        if side.exists() or side.is_symlink():
            side.unlink()
        os.replace(part, side)
    finally:
        if part.exists():
            part.unlink()
    files.append(file)
    for item in plan:
        item['entry'].update(dtype='Q8_0', file=len(files) - 1, off=item['side_off'], bytes=item['side_bytes'])
    write_tensors(pack / 'tensors.txt', files, entries)
    left = [e['name'] for e in entries if e['dtype'] in K_QUANTS and 'Engram' not in (files[e['file']] or '')]
    assert not left, left
    return {'file': str(side), 'bytes': total, 'tensors': len(plan), 'ds4_patched': changed}


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('pack')
    ap.add_argument('model_dir')
    ap.add_argument('--file', required=True)
    ap.add_argument('--tensors', type=int, required=True)
    ap.add_argument('--bytes', type=int, required=True)
    ap.add_argument('--replace', action='store_true')
    ap.add_argument('--ds4', action='append', default=[], metavar='KEY=VALUE')
    a = ap.parse_args(argv)
    geometry = dict(x.split('=', 1) for x in a.ds4)
    res = convert(a.pack, a.model_dir, a.file, a.tensors, a.bytes, a.replace, geometry)
    print(json.dumps(res))
    return 1 if 'reasons' in res else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
