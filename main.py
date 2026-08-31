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

    sys.exit(app.exec_())


# ============================================================
# Run Application
# ============================================================

if __name__ == "__main__":
    main()