from __future__ import annotations

from importlib.resources import as_file, files

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from super_dl import (
    APP_AUTHOR,
    APP_HOMEPAGE,
    APP_ISSUES_URL,
    APP_NAME,
    __version__,
)


def _load_icon_pixmap(size: int = 64) -> QPixmap:
    res = files("super_dl.resources").joinpath("icon.ico")
    with as_file(res) as path:
        pm = QPixmap(str(path))
    if pm.isNull():
        return pm
    return pm.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.setModal(True)

        root = QVBoxLayout(self)

        header = QHBoxLayout()
        icon_label = QLabel()
        pm = _load_icon_pixmap(48)
        if not pm.isNull():
            icon_label.setPixmap(pm)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        header.addWidget(icon_label)

        text = QLabel()
        text.setTextFormat(Qt.TextFormat.RichText)
        text.setOpenExternalLinks(True)
        text.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        text.setWordWrap(True)
        text.setText(
            f"<h2 style='margin:0'>{APP_NAME}</h2>"
            f"<p style='margin:4px 0'>Version <b>{__version__}</b></p>"
            "<p style='margin:4px 0'>Lightweight cross-platform GUI wrapper around "
            "<a href='https://github.com/yt-dlp/yt-dlp'>yt-dlp</a>.</p>"
            f"<p style='margin:8px 0 2px'>Created by <b>{APP_AUTHOR}</b></p>"
            "<p style='margin:2px 0'>"
            f"<a href='{APP_HOMEPAGE}'>Homepage</a> &nbsp;&middot;&nbsp; "
            f"<a href='{APP_ISSUES_URL}'>Report an issue</a> &nbsp;&middot;&nbsp; "
            f"<a href='{APP_HOMEPAGE}/releases'>Releases</a>"
            "</p>"
            "<p style='margin:8px 0 2px'><b>Credits</b></p>"
            "<ul style='margin:2px 0 0 16px;padding:0'>"
            "<li><a href='https://github.com/yt-dlp/yt-dlp'>yt-dlp</a> — download engine</li>"
            "<li><a href='https://doc.qt.io/qtforpython/'>PySide6</a> — GUI toolkit (LGPL)</li>"
            "<li><a href='https://github.com/imageio/imageio-ffmpeg'>imageio-ffmpeg</a> — "
            "bundled ffmpeg binary</li>"
            "<li><a href='https://github.com/platformdirs/platformdirs'>platformdirs</a> — "
            "cross-platform paths</li>"
            "</ul>"
            "<p style='margin:8px 0 0;color:gray;font-size:small'>"
            "Licensed under LGPL-2.1 (inherited from PySide6)."
            "</p>"
        )
        header.addWidget(text, 1)
        root.addLayout(header)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        root.addWidget(buttons)
