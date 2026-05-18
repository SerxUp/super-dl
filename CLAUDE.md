# super-dl

Lightweight cross-platform GUI wrapper around [yt-dlp](https://github.com/yt-dlp/yt-dlp), written in Python with PySide6.

## Stack
- Python 3.10+
- PySide6 (Qt for Python, LGPL)
- yt-dlp — imported as a library, not subprocessed
- imageio-ffmpeg — bundles a per-platform ffmpeg binary, no system install needed
- platformdirs — cross-platform config/log/cache paths
- pytest + pytest-qt; ruff for lint

## Dev workflow

One-time setup:
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Common commands:
```powershell
.\.venv\Scripts\python.exe -m pytest          # tests
.\.venv\Scripts\python.exe -m ruff check .    # lint
.\.venv\Scripts\python.exe -m super_dl         # launch the app
```

Run `pytest` and `ruff check` before every commit.

## Architecture

Layered package:
- `super_dl/core/` — GUI-agnostic, must be importable headless. Holds the yt-dlp worker, format selectors, config, paths, and logging setup.
- `super_dl/ui/` — Qt widgets. May import from `core/`.

**Hard rule: `core/` never imports from `ui/`.**

The download worker is a `QObject` (`YtDlpWorker`) moved onto a dedicated `QThread`. All communication between UI and worker is via Qt signals/slots — never direct cross-thread method calls. The one exception is `worker.cancel()`, which only sets a `threading.Event` (atomic, thread-safe). yt-dlp's progress hook checks the event and raises `DownloadCancelled` to abort cleanly.

## Conventions

- **Paths**: `pathlib.Path` everywhere; never string-concat or use `os.path.join` for new code.
- **User directories**: go through `core/paths.py` (which wraps `platformdirs`). Never hardcode `~/.config`, `%APPDATA%`, etc.
- **Resource loading inside the package**: `importlib.resources.files("super_dl.resources")` — *not* `Path(__file__).parent / "resources"`, which breaks under PyInstaller `--onefile`.
- **Bundled binary paths** (ffmpeg, etc.): use `core/paths.py` helpers; `bundle_root()` knows about `sys._MEIPASS`.
- **Config persistence**: JSON in `platformdirs.user_config_dir()` via the `AppConfig` dataclass. No `QSettings`. Unknown keys in saved configs are silently dropped so old/new app versions coexist.
- **yt-dlp options**: pass options straight through to `YoutubeDL` rather than building wrapper helpers — yt-dlp's option surface is large and already documented upstream.
- **Error classification**: new exception types caught in the worker should be added to `_classify()` in `core/downloader.py` so the UI can show kind-specific hints (e.g. "yt-dlp may need an update" for extractor errors).

## Testing

- Unit tests must not hit the network. Network-dependent checks are deferred to manual testing for now.
- Anything constructing a `QObject` needs the `qtbot` fixture (it provides a `QApplication`).
- Tests live in `tests/` mirroring the package layout (`test_<module>.py`).

## Branch & commit naming

- Branches: `feat/short-description`, `fix/short-description`. No other prefixes for now (`chore/`, `docs/`, etc. can come later if the project grows).
- Commit subjects: imperative mood, ≤72 chars, no trailing period (e.g. `Wire up yt-dlp download flow`).
- Commit body: wrapped at ~72 cols, explains *why* not *what*.

## What to avoid

- Don't add wrapper helpers in `core/` for yt-dlp options that the library already exposes directly.
- Don't shell out to a `yt-dlp` binary or to `ffmpeg` unless the library API genuinely can't do what's needed — we picked the library-integration path on purpose.
- Don't introduce `QSettings`, `os.path`, or hardcoded platform paths.
- Don't add comments explaining what well-named code already says; only the *why* when it's non-obvious.
- Don't proactively push to `origin` — commits land locally first; pushing happens on explicit request.

## Packaging (planned, not yet implemented)

- PyInstaller per OS, built via GitHub Actions matrix (`windows-latest`, `macos-latest`, `ubuntu-latest`).
- Manual yt-dlp version bumps when extractors break — no automated release pipeline for v1.
