from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt


class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("GestureBoard")
        self.resize(1000, 600)

        layout = QVBoxLayout()

        title = QLabel("GestureBoard")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size:40px;
            font-weight:bold;
            color:white;
        """)

        subtitle = QLabel("Gesture-Controlled Presentation System")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            font-size:18px;
            color:#AAAAAA;
        """)

        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch()

        self.setLayout(layout)

        self.setStyleSheet("""
            QWidget{
                background:#111827;
            }
        """)