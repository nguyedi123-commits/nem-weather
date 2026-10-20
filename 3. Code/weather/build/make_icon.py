"""Draws build/icon.ico (yellow sun behind a white cloud on a blue rounded square). Plain Python, no extra libraries.
Adapted from NEM Trader's build/make_icon.py.

  python build/make_icon.py
"""
import struct
import zlib
from pathlib import Path

BLUE, YELLOW, WHITE = (30, 136, 229), (255, 196, 0), (250, 250, 250)
SUN = (0.40, 0.38, 0.22)                                                        # centre x, y, radius (0-1)
CLOUD = [(0.42, 0.66, 0.16), (0.60, 0.58, 0.20), (0.76, 0.68, 0.14), (0.58, 0.72, 0.14)]   # circles


def colour(px, py):
    if any((px - x) ** 2 + (py - y) ** 2 <= r * r for x, y, r in CLOUD):
        return WHITE
    x, y, r = SUN
    if (px - x) ** 2 + (py - y) ** 2 <= r * r:
        return YELLOW
    return BLUE


def pixel(x, y, n):
    """Colour of pixel (x, y) in an n x n icon, 4x4 supersampled for smooth edges."""
    r = n * 0.18   # corner radius
    total = [0, 0, 0, 0]
    for sy in range(4):
        for sx in range(4):
            px, py = x + (sx + 0.5) / 4, y + (sy + 0.5) / 4
            cx, cy = min(max(px, r), n - r), min(max(py, r), n - r)
            if (px - cx) ** 2 + (py - cy) ** 2 > r * r:
                continue   # outside the rounded square: transparent
            c = colour(px / n, py / n)
            total = [total[0] + c[0], total[1] + c[1], total[2] + c[2], total[3] + 255]
    a = total[3] / 16
    return tuple(round(v / (total[3] / 255)) if total[3] else 0 for v in total[:3]) + (round(a),)


def png(n):
    raw = b"".join(b"\0" + b"".join(bytes(pixel(x, y, n)) for x in range(n)) for y in range(n))
    chunk = lambda tag, data: struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", n, n, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def ico(sizes=(16, 24, 32, 48, 64, 128, 256)):
    images = [png(n) for n in sizes]
    head = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries = b""
    for n, img in zip(sizes, images):
        entries += struct.pack("<BBBBHHII", n % 256, n % 256, 0, 0, 1, 32, len(img), offset)
        offset += len(img)
    return head + entries + b"".join(images)


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    (here / "icon.ico").write_bytes(ico())
    (here / "icon.png").write_bytes(png(256))
    print("wrote", here / "icon.ico")
