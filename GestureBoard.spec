# PyInstaller build for GestureBoard: one windowed .exe that runs on a
# Windows PC with nothing else installed.
#
#   pip install -r requirements.txt
#   pyinstaller --noconfirm --clean GestureBoard.spec
#
# The result is dist/GestureBoard.exe.
#
# Notes
# - The phone camera page is embedded in core/phone_page.py, so it
#   needs no data file. Its certificate is written to
#   %APPDATA%/GestureBoard at run time, never into the bundle.
# - MediaPipe's model files and aiohttp's modules are collected by
#   hand: this PyInstaller setup has no hooks for them.

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

datas = [("assets", "assets")]
datas += collect_data_files("mediapipe")
datas += collect_data_files("cv2_enumerate_cameras")

binaries = collect_dynamic_libs("mediapipe")

hiddenimports = []
hiddenimports += collect_submodules("aiohttp")
hiddenimports += [
    "multidict",
    "yarl",
    "frozenlist",
    "aiosignal",
    "propcache",
    "aiohappyeyeballs",
    "qrcode",
    "qrcode.image.pil",
    "cryptography.hazmat.primitives.asymmetric.rsa",
    "cryptography.x509",
    "psutil",
    "cv2_enumerate_cameras",
    "fitz",
    "pymupdf",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib.tests", "numpy.tests"],
    noarchive=False,
)

# --------------------------------------------------------------
# Microsoft C++ runtime
# --------------------------------------------------------------
# PyQt5 ships an old MSVCP140.dll (14.26) in PyQt5/Qt5/bin, and
# PyInstaller's PyQt5 hook puts that folder on the DLL search path
# before main.py runs. MediaPipe's _framework_bindings.pyd needs a
# newer runtime, so with the old copy it fails with "DLL
# initialization routine failed" and the app exits at startup.
# The runtime is backward compatible, so bundle this PC's
# up-to-date System32 copies everywhere instead (top level and
# in PyQt5/Qt5/bin).
#
# ucrtbase.dll and api-ms-win-*.dll are part of Windows 10/11, so
# don't bundle the old copies found on PATH (Windows Kits).

import os

_SYS32 = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
_VC_RUNTIME = [
    "msvcp140.dll",
    "msvcp140_1.dll",
    "msvcp140_2.dll",
    "vcruntime140.dll",
    "vcruntime140_1.dll",
    "concrt140.dll",
]


def _fix_runtime(binaries):
    fixed = []
    for entry in binaries:
        dest, src, kind = entry
        name = os.path.basename(dest).lower()
        if name == "ucrtbase.dll" or name.startswith("api-ms-win-"):
            continue
        if name in _VC_RUNTIME and os.path.exists(os.path.join(_SYS32, name)):
            src = os.path.join(_SYS32, name)
        fixed.append((dest, src, kind))

    present = {d.lower() for d, _, _ in fixed}
    for name in _VC_RUNTIME:
        path = os.path.join(_SYS32, name)
        if name not in present and os.path.exists(path):
            fixed.append((name, path, "BINARY"))
    return fixed


a.binaries = _fix_runtime(a.binaries)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="GestureBoard",
    icon="assets/logo/app_icon.ico",
    console=False,
    upx=False,
    runtime_tmpdir=None,
)
