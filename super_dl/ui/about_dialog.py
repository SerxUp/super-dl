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
        self.setWindowTitle(self.tr("About {app}").format(app=APP_NAME))
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
        version_html = self.tr("Version {version}").format(version=f"<b>{__version__}</b>")
        wrapper_html = self.tr(
            "Lightweight cross-platform GUI wrapper around {ytdlp_link}."
        ).format(ytdlp_link="<a href='https://github.com/yt-dlp/yt-dlp'>yt-dlp</a>")
        created_html = self.tr("Created by {author}").format(author=f"<b>{APP_AUTHOR}</b>")
        homepage_label = self.tr("Homepage")
        issue_label = self.tr("Report an issue")
        releases_label = self.tr("Releases")
        credits_label = self.tr("Credits")
        engine_label = self.tr("download engine")
        gui_label = self.tr("GUI toolkit (LGPL)")
        ffmpeg_label = self.tr("bundled ffmpeg binary")
        paths_label = self.tr("cross-platform paths")
        license_label = self.tr("Licensed under LGPL-2.1 (inherited from PySide6).")
        text.setText(
            f"<h2 style='margin:0'>{APP_NAME}</h2>"
            f"<p style='margin:4px 0'>{version_html}</p>"
            f"<p style='margin:4px 0'>{wrapper_html}</p>"
            f"<p style='margin:8px 0 2px'>{created_html}</p>"
            "<p style='margin:2px 0'>"
            f"<a href='{APP_HOMEPAGE}'>{homepage_label}</a> &nbsp;&middot;&nbsp; "
            f"<a href='{APP_ISSUES_URL}'>{issue_label}</a> &nbsp;&middot;&nbsp; "
            f"<a href='{APP_HOMEPAGE}/releases'>{releases_label}</a>"
            "</p>"
            f"<p style='margin:8px 0 2px'><b>{credits_label}</b></p>"
            "<ul style='margin:2px 0 0 16px;padding:0'>"
            f"<li><a href='https://github.com/yt-dlp/yt-dlp'>yt-dlp</a> — {engine_label}</li>"
            f"<li><a href='https://doc.qt.io/qtforpython/'>PySide6</a> — {gui_label}</li>"
            f"<li><a href='https://github.com/imageio/imageio-ffmpeg'>imageio-ffmpeg</a> — "
            f"{ffmpeg_label}</li>"
            f"<li><a href='https://github.com/platformdirs/platformdirs'>platformdirs</a> — "
            f"{paths_label}</li>"
            "</ul>"
            "<p style='margin:8px 0 0;color:gray;font-size:small'>"
            f"{license_label}"
            "</p>"
        )
        header.addWidget(text, 1)
        root.addLayout(header)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        root.addWidget(buttons)
