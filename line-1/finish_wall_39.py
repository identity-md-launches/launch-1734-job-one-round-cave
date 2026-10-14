"""Lay only generated pigment onto the hash-verified record-38 wall.

One-shot artifact assembly. Before running, wall.png is the ancestor and
wall-v19.png contains the reviewed isolated white-background pigment motif.
Both are overwritten with the completed wall; no intermediate image is saved.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parent.parent
ANCESTOR = 'edd316e0efe31a3ca6b467346c7b6a13b8b87d05fead22bb9b5a1fbb16f2d609'
BOX = (855, 225, 1030, 302)


def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))


def main():
    spec = importlib.util.spec_from_file_location('thumbnail39', ROOT / 'shared/wall-thumbnail/thumbnail.py')
    thumbnail = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(thumbnail)
    wall = ROOT / 'artifacts/line-1/wall.png'
    motif = ROOT / 'artifacts/line-1/wall-v19.png'
    generated_bytes = motif.read_bytes()
    assert hashlib.sha256(wall.read_bytes()).hexdigest() == ANCESTOR
    width, height, old = thumbnail.png_rgb(wall)
    iw, ih, source = thumbnail.png_rgb(motif)
    assert (width, height) == (1254, 1254)
    paint = [(x, y) for y in range(ih) for x in range(iw)
             if min(source[y][3*x:3*x+3]) < 210]
    sx0, sy0 = min(x for x, y in paint), min(y for x, y in paint)
    sx1, sy1 = max(x for x, y in paint)+1, max(y for x, y in paint)+1
    x0, y0, x1, y1 = BOX
    rows = [bytearray(row) for row in old]
    for y in range(y0, y1):
        ya = sy0 + (y-y0)*(sy1-sy0)//(y1-y0)
        yb = sy0 + (y-y0+1)*(sy1-sy0)//(y1-y0)
        for x in range(x0, x1):
            xa = sx0 + (x-x0)*(sx1-sx0)//(x1-x0)
            xb = sx0 + (x-x0+1)*(sx1-sx0)//(x1-x0)
            samples = [source[yy][3*xx:3*xx+3] for yy in range(ya, yb) for xx in range(xa, xb)]
            # White is absent pigment. Keep the original rock in all worn gaps.
            weights = [max(0, min(1, (230-min(p))/80)) for p in samples]
            weight = sum(weights)
            if not weight:
                continue
            alpha = 0.67 * weight / len(samples)
            for channel in range(3):
                color = sum(p[channel]*w for p, w in zip(samples, weights)) / weight
                base = old[y][3*x+channel]
                rows[y][3*x+channel] = round(base*(1-alpha) + color*alpha)
    inside = sum(rows[y][3*x:3*x+3] != old[y][3*x:3*x+3]
                 for y in range(y0, y1) for x in range(x0, x1))
    outside = sum(rows[y][3*x:3*x+3] != old[y][3*x:3*x+3]
                  for y in range(height) for x in range(width)
                  if not (x0 <= x < x1 and y0 <= y < y1))
    assert inside > 1000 and outside == 0
    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(b''.join(b'\0'+row for row in rows), 9)) + chunk(b'IEND', b''))
    jpeg = thumbnail.jpeg(thumbnail.resize(width, height, rows, 512))
    assert len(jpeg) < 100000
    wall.write_bytes(png)
    motif.write_bytes(png)
    (ROOT / 'dist/line-1/39.jpg').write_bytes(jpeg)
    checks = {
        'ancestor_sha256': ANCESTOR,
        'generated_pigment_sha256': hashlib.sha256(generated_bytes).hexdigest(),
        'wall_sha256': hashlib.sha256(png).hexdigest(),
        'wall': {'width': width, 'height': height, 'format': 'PNG', 'mode': 'RGB', 'bytes': len(png)},
        'jpeg': {'width': 512, 'height': 512, 'format': 'JPEG', 'bytes': len(jpeg)},
        'addition_box': list(BOX), 'source_pigment_bounds': [sx0, sy0, sx1, sy1],
        'changed_pixels_inside': inside, 'changed_pixels_outside': outside,
        'visual_review': 'Pending final inspection', 'unmet_visual_requirements': [],
    }
    (ROOT / 'line-1/visual-checks-39.json').write_text(json.dumps(checks, indent=2)+'\n')
    print(json.dumps(checks, indent=2))


if __name__ == '__main__':
    main()
