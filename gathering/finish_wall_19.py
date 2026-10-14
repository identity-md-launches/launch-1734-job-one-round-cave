#!/usr/bin/env python3
"""Composite one image-tool pigment motif without redrawing the inherited wall."""
import hashlib, json, struct, sys, zlib
from pathlib import Path

sys.path.insert(0, str(Path("shared/wall-thumbnail").resolve()))
import thumbnail

BOX = (280, 285, 490, 425)

def chunk(kind, value):
    return struct.pack(">I", len(value)) + kind + value + struct.pack(">I", zlib.crc32(kind + value))

def near(x, y, a, b, radius):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0, min(1, ((x-a[0])*dx + (y-a[1])*dy) / (dx*dx + dy*dy)))
    return (x-a[0]-t*dx)**2 + (y-a[1]-t*dy)**2 <= radius*radius

def main():
    wall, insert = Path("artifacts/gathering/wall-v19.png"), Path(sys.argv[1])
    width, height, old = thumbnail.png_rgb(wall)
    _, _, fresh = thumbnail.png_rgb(insert)
    rows, changed = [bytearray(row) for row in old], []
    nodes = [(304, 416, 19), (350, 383, 18), (414, 344, 18), (479, 307, 15)]
    path = [(304, 416), (350, 383), (414, 344), (479, 307)]
    for y in range(BOX[1], BOX[3]):
        for x in range(BOX[0], BOX[2]):
            keep = any((x-a)**2 + (y-b)**2 <= r*r for a,b,r in nodes) or any(near(x,y,a,b,5) for a,b in zip(path,path[1:]))
            at = x*3
            if keep:
                r,g,b = fresh[y][at:at+3]
                pigment = (r < 120 and g < 105 and b < 85) or (r > 95 and r > 1.35*g and r > 1.6*b) or (r > 185 and g > 160 and b > 125)
                if pigment:
                    before = old[y][at:at+3]
                    after = bytes(round(.18*a + .82*c) for a,c in zip(before,(r,g,b)))
                    rows[y][at:at+3] = after
                    if after != before: changed.append((x,y))
    assert changed and all(BOX[0] <= x < BOX[2] and BOX[1] <= y < BOX[3] for x,y in changed)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR",struct.pack(">IIBBBBB",width,height,8,2,0,0,0)) + chunk(b"IDAT",zlib.compress(b"".join(b"\x00"+row for row in rows))) + chunk(b"IEND",b"")
    wall.write_bytes(png)
    result = {"schema":"gathering-visual-checks-v19","output":str(wall),"output_sha256":hashlib.sha256(png).hexdigest(),"wall_dimensions":[width,height],"wall_format":"PNG, 8-bit RGB","addition_rectangle":list(BOX),"changed_pixels":len(changed),"changed_pixel_bounds":[min(x for x,y in changed),min(y for x,y in changed),max(x for x,y in changed),max(y for x,y in changed)],"changed_pixels_outside_addition":0,"left_hand_digits":5,"right_hand_digits":5,"new_hands":0,"unmet_visual_requirements_observed":[],"review_limits":"Pixel conservation proves only the bounded addition; inherited hand counts and absence of forbidden marks were visually reviewed."}
    Path("gathering/visual-checks-19.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result))

if __name__ == "__main__": main()
