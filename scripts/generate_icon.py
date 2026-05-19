"""Generate a placeholder app icon for super-dl.

Renders a flat-color square with a "DL" glyph at multiple sizes, packs
them into a Windows .ico (PNG-encoded entries) at super_dl/resources/icon.ico.

Replace with a real designed icon by overwriting that file.

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

SIZES = (16, 32, 48, 64, 128, 256)
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


def main() -> int:
    QApplication(sys.argv)
    pngs = {s: render(s) for s in SIZES}
    out = Path(__file__).resolve().parent.parent / "super_dl" / "resources" / "icon.ico"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(pack_ico(pngs))
    print(f"Wrote {out} ({out.stat().st_size} bytes, sizes={list(SIZES)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
