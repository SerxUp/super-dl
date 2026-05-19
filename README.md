<div align="center">

[<img src="super_dl/resources/icon.ico" width="128" alt="super-dl">](#readme)

# Super DL

Lightweight cross-platform GUI wrapper around [yt-dlp](https://github.com/yt-dlp/yt-dlp). Paste a URL, pick a format, download. No system ffmpeg required.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue?style=for-the-badge)](#requirements "Requirements")
[![PySide6](https://img.shields.io/badge/UI-PySide6-green?style=for-the-badge)](#stack "Stack")
[![License: LGPL](https://img.shields.io/badge/license-LGPL-lightgrey?style=for-the-badge)](LICENSE "License")
[![Release](https://img.shields.io/github/v/release/sergioadam/super-dl?color=brightgreen&label=Download&style=for-the-badge)](#installation "Installation")

[Features](#features) &bull; [Requirements](#requirements) &bull; [Installation](#installation) &bull; [Usage](#usage) &bull; [Development](#development) &bull; [Stack](#stack) &bull; [Roadmap](#roadmap) &bull; [License](#license)

</div>

## Features

- Paste any URL yt-dlp supports (YouTube, Twitch, SoundCloud, hundreds more)
- Format presets: best video+audio, audio-only, or custom yt-dlp format string
- Live progress bar with speed and ETA
- Cancel mid-download
- Bundled ffmpeg via `imageio-ffmpeg` — no system install needed
- Config persists between sessions (output folder, last-used format)

## Requirements

- Python 3.10 or later
- No system ffmpeg needed

## Installation

### Windows (recommended)

Download `super-dl-setup-X.Y.Z.exe` from the [latest release](https://github.com/SerxUp/super-dl/releases/latest) and run it. The wizard installs per-user — no admin rights required — and registers an uninstaller in *Apps & features*.

### macOS (Apple Silicon)

Download `super-dl-macos-arm64.zip` from the [latest release](https://github.com/SerxUp/super-dl/releases/latest), unzip, and drag `super-dl.app` to `/Applications`.

First launch is blocked by Gatekeeper because the build is unsigned. Either:

- **Right-click the app → Open**, then click **Open** in the dialog. macOS remembers the choice.
- Or strip the quarantine attribute from a terminal:

  ```bash
  xattr -dr com.apple.quarantine /Applications/super-dl.app
  ```

Intel Macs are not supported.

### From source

```powershell
git clone https://github.com/SerxUp/super-dl.git
cd super-dl
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

## Usage

```powershell
.\.venv\Scripts\python.exe -m super_dl
```

Or, if installed into a venv that's on your PATH:

```powershell
super-dl
```

1. Paste a URL into the URL field.
2. Choose a format preset (or enter a custom yt-dlp format string).
3. Pick an output folder.
4. Click **Download**.

## Development

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

# Run tests
.\.venv\Scripts\python.exe -m pytest

# Lint
.\.venv\Scripts\python.exe -m ruff check .

# Launch
.\.venv\Scripts\python.exe -m super_dl
```

## Stack

| Component | Library |
|-----------|---------|
| GUI | [PySide6](https://doc.qt.io/qtforpython/) |
| Downloader | [yt-dlp](https://github.com/yt-dlp/yt-dlp) |
| ffmpeg | [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg) |
| Config/log paths | [platformdirs](https://github.com/platformdirs/platformdirs) |

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the prioritized backlog.

## License

LGPL-2.1 (inherited from PySide6). See [LICENSE](LICENSE).
