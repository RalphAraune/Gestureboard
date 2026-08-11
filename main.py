import sys

from PyQt5.QtWidgets import QApplication

from gui.main_window import MainWindow

app = QApplication(sys.argv)

window = MainWindow()
# Keep maximization as the final show request so Windows does not restore the
# previously saved, smaller geometry.
window.showMaximized()

sys.exit(app.exec_())
