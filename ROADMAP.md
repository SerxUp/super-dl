# Roadmap

Current version: **0.1.0** (pre-release). Windows installer pipeline just landed; macOS/Linux ship as raw artifacts. Single-window Qt GUI; multi-URL batch downloads.

Items are globally ranked. Tier headings indicate horizon, not strict ordering — finishing a higher-tier item unblocks the next regardless of which heading it lives under.

---

## P0 — ship 0.1.0

Goal: cut the first real release that a non-developer can install.

1. **App icon.** No `.ico` today. Add `super_dl/resources/icon.ico`, wire into:
   - [super_dl.spec](super_dl.spec) — `EXE(..., icon="super_dl/resources/icon.ico")`
   - [installer/super-dl.iss](installer/super-dl.iss) — `SetupIconFile=..\super_dl\resources\icon.ico`
   - [super_dl/app.py](super_dl/app.py) — `QApplication.setWindowIcon(...)` loaded via `importlib.resources`
2. **End-to-end installer smoke test.** Tag `v0.1.0-rc1`, let CI build, run the produced setup.exe on a clean Windows VM, walk the checklist in the install plan. Fix anything that breaks. Then tag `v0.1.0`.
3. **Document SmartScreen workaround in README.** Unsigned installer trips Defender on first run. Add a "First-time install" note: "More info → Run anyway". Code signing deferred (see *Out of scope*).
4. **Keep on-disk dirs as `super-dl`.** Display name is now "Super DL" ([super_dl/__init__.py](super_dl/__init__.py)), but `PlatformDirs("super-dl", ...)` in [super_dl/core/paths.py](super_dl/core/paths.py) and `LOG_FILENAME` in [super_dl/core/logging_setup.py](super_dl/core/logging_setup.py) stay lowercase forever. Document the invariant in CLAUDE.md so a future rename PR doesn't break user data.

## P1 — core UX gaps (0.2.x)

Goal: make the app pleasant for someone who already installed it.

5. **Drag-and-drop URLs** onto the main window → append to the URL field.
6. **Per-URL row status in batch mode.** Multi-URL was added in [d2b979e](../../commit/d2b979e); confirm the UI surfaces per-item progress / status / error, not just an aggregate bar.
7. **Subtitles & metadata toggles.** Surface `writesubtitles`, `subtitleslangs`, `writethumbnail`, `embedmetadata` as checkboxes/inputs. Currently reachable only by hand-writing the format string.
8. **Cookies for gated content.** UI for `cookiesfrombrowser` (browser picker) or `cookiefile` (file picker). Unlocks members-only / age-gated downloads.
9. **Recent downloads list.** Persist last N completed jobs in `AppConfig`. Double-click → open the output folder.

## P2 — platform expansion (0.3.x)

Goal: stop being a Windows-only "real install".

10. **macOS DMG + notarization.** Replace the zipped `.app` with a signed/notarized DMG. Requires Apple Developer account ($99/yr) — gate this on whether we have demand.
11. **Linux AppImage** (preferred) **or `.deb`.** AppImage is one binary, no package manager. Update [.github/workflows/build.yml](.github/workflows/build.yml) Linux leg.
12. **Automated yt-dlp bump bot.** GitHub Action opens a weekly PR bumping the `yt-dlp>=` floor in [pyproject.toml](pyproject.toml). Manual bumps per CLAUDE.md don't scale once extractors start rotting.
13. **Self-update check on launch.** Compare `__version__` to latest GitHub Release tag; show a non-blocking banner. **No silent auto-update.**

## P3 — polish & tech debt (0.4.x+)

Goal: pay down debt before it compounds.

14. **UI tests with `pytest-qt`.** Currently `tests/` covers core only. Cover at least: URL validation, format-preset selection, cancel-mid-download.
15. **Split [super_dl/ui/main_window.py](super_dl/ui/main_window.py).** 300+ lines mixing layout, signals, and dialog handling. Extract `UrlPanel`, `FormatPanel`, `ProgressPanel`.
16. **Expand `_classify()` error hints** in [super_dl/core/downloader.py](super_dl/core/downloader.py) once real-world tracebacks accumulate via issue reports.

---

## Out of scope (for now)

- **Code signing.** Deferred. Revisit if user count grows or if SmartScreen friction generates complaints. Likely path when revisited: Azure Trusted Signing (~$10/mo, EV-equivalent trust).
- **Telemetry.** Not collecting any. Bug-report-driven prioritization until that changes.
- **Plugin system / extractor sideloading.** yt-dlp already handles this upstream; we'd just be wrapping its surface.
- **Auto-update binary replacement.** Banner-and-link only — actual replacement is fragile across permission models.
