"""Run this once to generate icon.ico for the PyInstaller build."""
import io
import math
import struct
from PIL import Image, ImageDraw

SIZE = 256
NAV  = (11,  15,  30)    # navy bg
WHT  = (255, 255, 255)   # doc white
BLU  = (79,  142, 247)   # #4f8ef7
PNK  = (224, 64,  251)   # #e040fb
L1   = (79,  142, 247)
L2   = (224, 64,  251)
L3   = (100, 200, 255)
L4   = (160, 100, 240)


def rrect(draw, x0, y0, x1, y1, r, rgb):
    draw.rectangle([x0+r, y0, x1-r, y1], fill=rgb)
    draw.rectangle([x0, y0+r, x1, y1-r], fill=rgb)
    draw.ellipse([x0, y0, x0+r*2, y0+r*2], fill=rgb)
    draw.ellipse([x1-r*2, y0, x1, y0+r*2], fill=rgb)
    draw.ellipse([x0, y1-r*2, x0+r*2, y1], fill=rgb)
    draw.ellipse([x1-r*2, y1-r*2, x1, y1], fill=rgb)


def sparkle(draw, cx, cy, ro, ri, rgb):
    pts = []
    for i in range(8):
        a = math.radians(i * 45 - 90)
        r = ro if i % 2 == 0 else ri
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    draw.polygon(pts, fill=rgb)


def make_frame(size: int) -> Image.Image:
    img  = Image.new("RGB", (size, size), NAV)
    draw = ImageDraw.Draw(img)
    s = size / SIZE

    def p(v): return int(v * s)

    rrect(draw, p(4), p(4), p(251), p(251), p(36), NAV)
    rrect(draw, p(46), p(54), p(186), p(214), p(14), WHT)

    for y, w, col in [(90,120,L1),(115,130,L2),(140,108,L3),(165,118,L4)]:
        h = max(p(11), 2)
        r = max(p(6), 1)
        draw.rounded_rectangle([p(68), p(y), p(68)+p(w), p(y)+h], radius=r, fill=col)

    sparkle(draw, p(196), p(66), p(50), p(20), BLU)
    sparkle(draw, p(196), p(66), p(28), p(11), PNK)

    return img


def build_ico(sizes):
    """Build a valid multi-size ICO file using BMP-encoded frames."""
    bmp_blobs = []
    for s in sizes:
        frame = make_frame(s)
        buf   = io.BytesIO()
        # Save as BMP then strip the 14-byte file header — ICO stores raw DIB
        frame.save(buf, format="BMP")
        bmp_blobs.append(buf.getvalue()[14:])

    n      = len(sizes)
    header = struct.pack("<HHH", 0, 1, n)

    offset = 6 + n * 16
    dirs   = b""
    for s, blob in zip(sizes, bmp_blobs):
        w = 0 if s == 256 else s
        h = 0 if s == 256 else s
        dirs += struct.pack("<BBBBHHII", w, h, 0, 0, 1, 24, len(blob), offset)
        offset += len(blob)

    return header + dirs + b"".join(bmp_blobs)


data = build_ico([16, 24, 32, 48, 64, 128, 256])
with open("icon.ico", "wb") as f:
    f.write(data)
print(f"icon.ico — {len(data) // 1024} KB, 7 sizes (BMP encoded)")
