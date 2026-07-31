import sys
from PyQt5.QtWidgets import QApplication
from gui.splash import SplashScreen


def main():
    app = QApplication(sys.argv)

    window = SplashScreen()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()