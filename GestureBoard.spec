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
