"""Generate placeholder app icons for super-dl.

Renders a flat-color square with a "DL" glyph at multiple sizes, packs
them into:

  - ``super_dl/resources/icon.ico`` (Windows / cross-platform Qt runtime)
  - ``super_dl/resources/icon.icns`` (macOS .app bundle metadata)

Replace with real designed icons by overwriting those files.

Usage:
    python scripts/generate_icon.py
"""

from __future__ import annotations

import struct
import sys
from io import BytesIO
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, QRect, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen
from PySide6.QtWidgets import QApplication

ICO_SIZES = (16, 32, 48, 64, 128, 256)
ICNS_SIZES = (16, 32, 128, 256, 512)

# Apple icns PNG-typed entry codes. Sizes without a mapping here are
# skipped when writing the .icns container.
ICNS_TYPE_CODES: dict[int, bytes] = {
    16: b"ic04",
    32: b"ic05",
    128: b"ic07",
    256: b"ic08",
    512: b"ic09",
}

BG = QColor("#2563eb")
FG = QColor("#ffffff")
ACCENT = QColor("#1e40af")


def render(size: int) -> bytes:
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    radius = max(2, size // 8)
    p.setBrush(BG)
    p.setPen(QPen(ACCENT, max(1, size // 32)))
    p.drawRoundedRect(QRect(0, 0, size - 1, size - 1), radius, radius)

    font = QFont()
    font.setBold(True)
    font.setPixelSize(max(6, int(size * 0.5)))
    p.setFont(font)
    p.setPen(FG)
    p.drawText(QRect(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, "DL")

    p.end()

    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return bytes(buf.data())


def pack_ico(pngs: dict[int, bytes]) -> bytes:
    out = BytesIO()
    out.write(struct.pack("<HHH", 0, 1, len(pngs)))
    offset = 6 + 16 * len(pngs)
    for size in sorted(pngs):
        data = pngs[size]
        dim = 0 if size == 256 else size
        out.write(
            struct.pack(
                "<BBBBHHII",
                dim, dim, 0, 0, 1, 32, len(data), offset,
            )
        )
        offset += len(data)
    for size in sorted(pngs):
        out.write(pngs[size])
    return out.getvalue()


def pack_icns(pngs: dict[int, bytes]) -> bytes:
    # icns container: 8-byte header (magic + total length, big-endian uint32),
    # then a sequence of typed chunks: 4-byte OSType + 4-byte big-endian uint32
    # length (including the 8-byte chunk header) + payload bytes.
    chunks = BytesIO()
    for size in sorted(pngs):
        code = ICNS_TYPE_CODES.get(size)
        if code is None:
            continue
        data = pngs[size]
        chunks.write(code)
        chunks.write(struct.pack(">I", 8 + len(data)))
        chunks.write(data)
    body = chunks.getvalue()
    total = 8 + len(body)
    return b"icns" + struct.pack(">I", total) + body


def main() -> int:
    QApplication(sys.argv)

    resources = Path(__file__).resolve().parent.parent / "super_dl" / "resources"
    resources.mkdir(parents=True, exist_ok=True)

    ico_pngs = {s: render(s) for s in ICO_SIZES}
    ico_path = resources / "icon.ico"
    ico_path.write_bytes(pack_ico(ico_pngs))
    print(f"Wrote {ico_path} ({ico_path.stat().st_size} bytes, sizes={list(ICO_SIZES)})")

    icns_pngs = {s: render(s) for s in ICNS_SIZES}
    icns_path = resources / "icon.icns"
    icns_path.write_bytes(pack_icns(icns_pngs))
    print(f"Wrote {icns_path} ({icns_path.stat().st_size} bytes, sizes={list(ICNS_SIZES)})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
