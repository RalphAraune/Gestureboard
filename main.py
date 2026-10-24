import sys
from pathlib import Path

# ============================================================
# IMPORTANT:
# Load MediaPipe BEFORE PyQt5.
#
# On Windows, this can prevent a DLL initialization conflict
# between MediaPipe and Qt/PyQt5.
# ============================================================

try:
    import mediapipe as mp

    print(f"MediaPipe loaded successfully: {mp.__version__}")

except Exception as e:
    print("ERROR: MediaPipe could not be loaded.")
    print(e)
    sys.exit(1)


# ============================================================
# PyQt5
# ============================================================

from PyQt5.QtWidgets import QApplication


# ============================================================
# GestureBoard Main Window
# ============================================================

from gui.main_window import MainWindow


# ============================================================
# Application
# ============================================================

APP_ICON = Path(__file__).resolve().parent / "assets" / "logo" / "app_icon.ico"


def main():

    # --------------------------------------------------------
    # Own taskbar identity (Windows)
    # --------------------------------------------------------
    #
    # Without an AppUserModelID, Windows groups the window under
    # python.exe and shows the Python logo in the taskbar. Windows
    # caches the taskbar icon per ID, so bump the number after
    # changing app_icon.ico.
    #
    # --------------------------------------------------------

    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "GestureBoard.Desktop.3"
            )
        except Exception:
            pass

    app = QApplication(sys.argv)

    # GestureBoard logo (logo2 on a square tile) for the window,
    # taskbar and Alt+Tab instead of the Python icon.
    from PyQt5.QtGui import QIcon

    app.setWindowIcon(QIcon(str(APP_ICON)))

    # One font for every page (some pages set Segoe UI, others
    # fell back to the system default and looked different).
    from PyQt5.QtGui import QFont

    app.setFont(QFont("Segoe UI", 9))

    # --------------------------------------------------------
    # Create Main Window
    # --------------------------------------------------------

    window = MainWindow()

    # Frameless windows don't always inherit the app icon on Windows.
    window.setWindowIcon(app.windowIcon())

    # --------------------------------------------------------
    # Show the application maximized
    # --------------------------------------------------------
    #
    # This allows the TitleBar maximize/restore functionality
    # to control the window after startup.
    #
    # --------------------------------------------------------

    window.showMaximized()

    # --------------------------------------------------------
    # Start Qt Event Loop
    # --------------------------------------------------------

    exit_code = app.exec_()

    # --------------------------------------------------------
    # Make sure the process really ends
    # --------------------------------------------------------
    #
    # MediaPipe / OpenCV can leave background threads running,
    # which keeps Python (and the VS Code "Run") alive after the
    # window is closed. Flush output, then exit immediately.
    #
    # --------------------------------------------------------

    import os

    # Started from the desktop shortcut (pythonw.exe) there is no
    # console, so stdout / stderr are None.
    for stream in (sys.stdout, sys.stderr):
        if stream is not None:
            stream.flush()

    os._exit(exit_code)


# ============================================================
# Run Application
# ============================================================

if __name__ == "__main__":
    main()