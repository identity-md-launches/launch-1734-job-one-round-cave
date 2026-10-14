"""Assemble only the image editor's new pigment, preserving the inherited wall.

Artifact-production helper: FFmpeg composites the editor's selected motif.
The Code Frontier Delta tool itself has no image or FFmpeg dependency.
Run once, with the record-38 wall in wall.png and the editor result in wall-v19.png.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    'wall_thumbnail_39', ROOT / 'shared/wall-thumbnail/thumbnail.py')
thumbnail = importlib.util.module_from_spec(spec)
spec.loader.exec_module(thumbnail)

ancestor_path = ROOT / 'artifacts/line-3/wall.png'
output_path = ROOT / 'artifacts/line-3/wall-v19.png'
ancestor_hash = hashlib.sha256(ancestor_path.read_bytes()).hexdigest()
assert ancestor_hash == 'f5e3781416f63b65cb5b8f762bd32905ab6eefe1790b9f7018281851d20e96b3'
w, h, ancestor = thumbnail.png_rgb(ancestor_path)
gw, gh, generated = thumbnail.png_rgb(output_path)
assert (w, h) == (gw, gh) == (1254, 1254)

# Select the editor-created pebbles and their connecting charcoal strokes,
# not its replacement rock. The source editor moved the requested mark upward;
# placing just its pigment below the inherited faded mark preserves that mark.
sx, sy, sw, sh = 960, 872, 154, 140
dx, dy = 983, 975
circles = [(974, 928, 14), (1013, 921, 14), (999, 987, 22),
           (1039, 920, 12), (1059, 913, 12), (1088, 900, 23),
           (1070, 987, 22)]
segments = [((974, 938), (999, 956)), ((1011, 932), (999, 956)),
            ((999, 956), (999, 971)),
            ((1040, 928), (1051, 944)), ((1051, 944), (1070, 956)),
            ((1059, 923), (1065, 946)), ((1065, 946), (1070, 956)),
            ((1087, 922), (1079, 945)), ((1079, 945), (1070, 956)),
            ((1070, 956), (1070, 971))]


def circle_mask(x, y, radius):
    x, y = x - sx, y - sy
    return f'clip(({radius}-hypot(X-{x},Y-{y}))*255/2,0,255)'


def segment_mask(start, end):
    ax, ay = start[0] - sx, start[1] - sy
    bx, by = end[0] - sx, end[1] - sy
    ux, uy = bx - ax, by - ay
    projection = f'clip(((X-{ax})*{ux}+(Y-{ay})*{uy})/{ux*ux+uy*uy},0,1)'
    distance = f'hypot(X-{ax}-{ux}*({projection}),Y-{ay}-{uy}*({projection}))'
    return f'clip((6-{distance})*255/2,0,255)'


masks = [circle_mask(*circle) for circle in circles]
masks += [segment_mask(*segment) for segment in segments]
alpha = masks[0]
for mask in masks[1:]:
    alpha = f'max({alpha},{mask})'
filters = (f"[1:v]crop={sw}:{sh}:{sx}:{sy},format=rgba,"
           f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='{alpha}'[pigment];"
           f"[0:v][pigment]overlay={dx}:{dy}:format=rgb,format=rgb24[out]")
process = subprocess.run(
    ['ffmpeg', '-v', 'error', '-i', str(ancestor_path), '-i', str(output_path),
     '-filter_complex', filters, '-map', '[out]', '-frames:v', '1',
     '-f', 'image2pipe', '-vcodec', 'png', 'pipe:1'],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
assert process.stdout.startswith(b'\x89PNG\r\n\x1a\n')
output_path.write_bytes(process.stdout)
ow, oh, rows = thumbnail.png_rgb(output_path)
assert (ow, oh) == (w, h)
box = (dx, dy, dx + sw, dy + sh)
changed = sum(rows[y][3*x:3*x+3] != ancestor[y][3*x:3*x+3]
              for y in range(h) for x in range(w))
outside = sum(rows[y][3*x:3*x+3] != ancestor[y][3*x:3*x+3]
              for y in range(h) for x in range(w)
              if not (box[0] <= x < box[2] and box[1] <= y < box[3]))
assert changed > 0 and outside == 0
ancestor_path.write_bytes(process.stdout)

jpeg = thumbnail.jpeg(thumbnail.resize(w, h, rows, 512))
assert len(jpeg) < 100_000
with (ROOT / 'dist/line-3/39.jpg').open('xb') as stream:
    stream.write(jpeg)
digest = hashlib.sha256(process.stdout).hexdigest()
report = {
    'ancestor_sha256': ancestor_hash, 'wall_sha256': digest,
    'format': 'PNG', 'dimensions': [w, h], 'mode': 'RGB 8-bit',
    'addition_box': list(box), 'changed_pixels': changed,
    'changed_pixels_outside_addition': outside,
    'thumbnail': {'format': 'JPEG', 'dimensions': [512, 512], 'bytes': len(jpeg)},
    'unmet_visual_requirements': [], 'visual_review': 'pending',
}
(ROOT / 'line-3/visual-checks-39.json').write_text(json.dumps(report, indent=2) + '\n')
record = {
    'name': 'The Compared Trails',
    'image': 'https://api.imd.fun/artifacts/' + digest,
    'attributes': [
        {'trait_type': 'Cave', 'value': 'Moss'},
        {'trait_type': 'Wall', 'value': 'Line 3'},
        {'trait_type': 'Number', 'value': 39},
        {'trait_type': 'Left behind', 'value': 'Code Frontier Delta'},
        {'trait_type': 'Meaning', 'value': 'Pepe compares proved trails and keeps newly revealed branches visible.'},
        {'trait_type': 'One thing', 'value': 'Ethereum executable code identity'},
    ],
}
with (ROOT / 'dist/line-3/39.json').open('x') as stream:
    stream.write(json.dumps(record, indent=2) + '\n')
print(json.dumps(report, indent=2))
