import sys

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

def main():

    app = QApplication(sys.argv)

    # One font for every page (some pages set Segoe UI, others
    # fell back to the system default and looked different).
    from PyQt5.QtGui import QFont

    app.setFont(QFont("Segoe UI", 9))

    # --------------------------------------------------------
    # Create Main Window
    # --------------------------------------------------------

    window = MainWindow()

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

    sys.stdout.flush()
    sys.stderr.flush()

    os._exit(exit_code)


# ============================================================
# Run Application
# ============================================================

if __name__ == "__main__":
    main()