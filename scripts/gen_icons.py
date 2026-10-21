#!/usr/bin/env python3
"""Generate the raster app-icon files and the QSS arrow images.

Run from the repository root with the project venv (needs only PyQt5 + QtSvg):

    QT_QPA_PLATFORM=offscreen .venv/Scripts/python.exe scripts/gen_icons.py

Writes (idempotent, overwritten on every run):
    resources/icons/obd.png            256x256 logo
    resources/icons/obd.ico            16,24,32,48,64,128,256 (PNG frames)
    resources/icons/obd.icns           PNG-based chunks ic07..ic14 + icp4/icp5
    resources/icons/chevron-{down,up}-{light,dark}[@2x].png   QSS arrows (14px / 28px)

Sources: resources/icons/app/ddt4all.svg (+ ddt4all-small.svg, a heavier simplified
mark used for renders <= SMALL_MAX px (32)) and resources/icons/svg/chevron-*.svg.
ICO and ICNS containers are written by hand: Qt's ico writer stores a single
size and has no icns writer on most builds.
"""
import os
import struct
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PyQt5.QtGui import QColor, QGuiApplication, QImage, QPainter
from PyQt5.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "resources" / "icons"
APP_SVG = ICONS / "app" / "ddt4all.svg"
SMALL_SVG = ICONS / "app" / "ddt4all-small.svg"
SMALL_MAX = 32  # use the simplified mark up to and including this size

# text_muted tokens from src/ddt4all/ui/theme/palette.py (LIGHT / DARK)
ARROW_COLORS = {"light": "#5b6470", "dark": "#9aa3ad"}
ARROW_PX = 14

ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
# (chunk type, pixel size)
ICNS_CHUNKS = (
    ("icp4", 16), ("icp5", 32),
    ("ic11", 32), ("ic12", 64),
    ("ic07", 128), ("ic13", 256),
    ("ic08", 256), ("ic14", 512),
    ("ic09", 512), ("ic10", 1024),
)


def _render_svg(renderer, size):
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
    renderer.render(p)
    p.end()
    return img


_logo_big = QSvgRenderer(str(APP_SVG))
_logo_small = QSvgRenderer(str(SMALL_SVG))


def logo(size):
    """Logo bitmap at ``size`` px (small mark for tiny sizes)."""
    return _render_svg(_logo_small if size <= SMALL_MAX else _logo_big, size)


def png_bytes(img):
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    buf.close()
    return bytes(ba)


def write(path, data):
    path.write_bytes(data)
    print("wrote %s (%d bytes)" % (path.relative_to(ROOT), len(data)))


def build_ico(sizes):
    frames = [png_bytes(logo(s)) for s in sizes]
    head = struct.pack("<HHH", 0, 1, len(frames))
    offset = 6 + 16 * len(frames)
    entries = b""
    for s, data in zip(sizes, frames):
        dim = 0 if s >= 256 else s  # 0 means 256 in ICONDIRENTRY
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    return head + entries + b"".join(frames)


def build_icns(chunks):
    body = b""
    cache = {}
    for kind, s in chunks:
        if s not in cache:
            cache[s] = png_bytes(logo(s))
        data = cache[s]
        body += kind.encode("ascii") + struct.pack(">I", len(data) + 8) + data
    return b"icns" + struct.pack(">I", len(body) + 8) + body


def render_arrow(svg_name, color, px):
    text = (ICONS / "svg" / svg_name).read_text(encoding="utf-8").replace("currentColor", color)
    r = QSvgRenderer(QByteArray(text.encode("utf-8")))
    return _render_svg(r, px)


def main():
    _app = QGuiApplication.instance() or QGuiApplication(sys.argv)  # noqa: F841

    write(ICONS / "obd.png", png_bytes(logo(256)))
    write(ICONS / "obd.ico", build_ico(ICO_SIZES))
    write(ICONS / "obd.icns", build_icns(ICNS_CHUNKS))

    for direction in ("down", "up"):
        for theme, color in ARROW_COLORS.items():
            for scale, suffix in ((1, ""), (2, "@2x")):
                img = render_arrow("chevron-%s.svg" % direction, color, ARROW_PX * scale)
                write(ICONS / ("chevron-%s-%s%s.png" % (direction, theme, suffix)), png_bytes(img))

    print()
    print("Next: recompile the Qt resources so the app picks the new files up:")
    print("    python scripts/gen_qrc.py --compile")


if __name__ == "__main__":
    main()
