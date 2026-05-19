# PyInstaller spec — onefile, windowed (no console), bundles imageio-ffmpeg binary.
# Build:  pyinstaller super_dl.spec
import sys

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

datas = collect_data_files("imageio_ffmpeg")
datas += [("super_dl/resources/icon.ico", "super_dl/resources")]

a = Analysis(
    ["super_dl/__main__.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="super-dl",
    icon="super_dl/resources/icon.ico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="super-dl.app",
        bundle_identifier="dev.super-dl.app",
        info_plist={
            "CFBundleShortVersionString": "0.1.0",
            "CFBundleVersion": "0.1.0",
            "NSHighResolutionCapable": True,
        },
    )
