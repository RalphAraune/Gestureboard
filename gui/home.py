from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout
from PyQt5.QtCore import Qt


class HomeScreen(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("GestureBoard")
        self.setFixedSize(1000, 600)

        self.setStyleSheet("""
            QWidget{
                background:#111827;
            }

            QLabel{
                color:white;
            }

            QPushButton{
                background:#2563EB;
                color:white;
                border:none;
                border-radius:10px;
                padding:12px;
                font-size:15px;
            }

            QPushButton:hover{
                background:#3B82F6;
            }
        """)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("GestureBoard")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size:40px;
            font-weight:bold;
        """)

        subtitle = QLabel("Welcome to GestureBoard")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            font-size:18px;
            color:#9CA3AF;
        """)

        self.startButton = QPushButton("Start Camera")

        layout.addStretch()

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(30)
        layout.addWidget(self.startButton)

        layout.addStretch()

        self.setLayout(layout)