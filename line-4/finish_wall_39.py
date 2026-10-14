#!/usr/bin/env python3
"""Keep inherited wall pixels while conserving the new pigment and making outputs."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import zlib

ROOT = Path.cwd().resolve()
WALL = ROOT / 'artifacts/line-4/wall.png'
OUTPUT = ROOT / 'artifacts/line-4/wall-v19.png'
THUMB = ROOT / 'dist/line-4/39.jpg'
RECORD = ROOT / 'dist/line-4/39.json'
PATCH = (825, 515, 965, 623)
ANCESTOR = '2e2969dd3b8fed281a0564f6a68a05cfb9d4353e4706dd5aded0dee695eac9eb'


def chunk(kind, data):
    return (struct.pack('>I', len(data)) + kind + data +
            struct.pack('>I', zlib.crc32(kind + data)))


def main():
    assert hashlib.sha256(WALL.read_bytes()).hexdigest() == ANCESTOR
    assert not THUMB.exists() and not RECORD.exists()
    spec = importlib.util.spec_from_file_location(
        'codec39', ROOT / 'line-4/tools/call-rehearsal/thumbnail.py')
    codec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(codec)
    width, height, old = codec.png_rgb(WALL)
    sw, sh, generated = codec.png_rgb(OUTPUT)
    assert (width, height) == (sw, sh) == (1254, 1254)
    generated_hash = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    left, top, right, bottom = PATCH
    rows = [bytearray(row) for row in old]
    for y in range(top, bottom):
        for x in range(left, right):
            i = 3*x
            previous = old[y][i:i+3]
            red, green, blue = generated[y][i:i+3]
            difference = sum(abs(previous[c] - (red, green, blue)[c]) for c in range(3))
            ochre = red > 1.26*green and red-green > 29 and green > blue
            charcoal = red < 131 and green < 101 and blue < 86
            chalk = red > 174 and green > 151 and blue > 119
            # The tiny inherited red trails begin below the new ember; never
            # replace their strokes with regenerated pixels.
            ancestor_trail = y >= 614 and x < 916 and previous[0] > 1.35*previous[1] and previous[0]-previous[1] > 37
            if difference > 75 and (ochre or charcoal or chalk) and not ancestor_trail:
                rows[y][i:i+3] = generated[y][i:i+3]
    inside = outside = 0
    for y in range(height):
        for x in range(width):
            i = 3*x
            if rows[y][i:i+3] != old[y][i:i+3]:
                if left <= x < right and top <= y < bottom:
                    inside += 1
                else:
                    outside += 1
    assert inside > 1000 and outside == 0
    png = (b'\x89PNG\r\n\x1a\n' +
           chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) +
           chunk(b'IDAT', zlib.compress(b''.join(b'\0' + bytes(row) for row in rows), 9)) +
           chunk(b'IEND', b''))
    jpeg = codec.jpeg(codec.resize(width, height, rows, 512))
    assert len(jpeg) < 100_000
    OUTPUT.write_bytes(png)
    WALL.write_bytes(png)
    THUMB.write_bytes(jpeg)
    checks = {
        'ancestor_sha256': ANCESTOR, 'generated_sha256': generated_hash,
        'wall_sha256': hashlib.sha256(png).hexdigest(),
        'wall': {'width': width, 'height': height, 'format': 'PNG',
                 'mode': 'RGB', 'bytes': len(png)},
        'thumbnail': {'width': 512, 'height': 512, 'format': 'JPEG', 'bytes': len(jpeg)},
        'addition_rectangle': list(PATCH), 'changed_pixels_inside': inside,
        'changed_pixels_outside': outside,
        'unmet_visual_requirements': [
            'Inherited tiny three-pronged trail motifs cannot be certified as five-digit handprints; preserved unchanged.'
        ],
    }
    (ROOT / 'line-4/delivery-checks-39.json').write_text(json.dumps(checks, indent=2) + '\n')
    record = {
        'name': 'The Ember Measure',
        'image': 'https://api.imd.fun/artifacts/' + checks['wall_sha256'],
        'attributes': [
            {'trait_type': 'Cave', 'value': 'Moss'},
            {'trait_type': 'Wall', 'value': 'Line 4'},
            {'trait_type': 'Number', 'value': 39},
            {'trait_type': 'Left behind', 'value': 'Gas Lens'},
            {'trait_type': 'Meaning', 'value': 'An arched charcoal stroke gauges an ochre ember before the work begins.'},
            {'trait_type': 'One thing', 'value': 'Rehearse Ethereum contract calls before submission'},
        ],
    }
    RECORD.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(checks, indent=2))


if __name__ == '__main__':
    main()
