from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget
)
from PyQt5.QtCore import Qt

from gui.home import HomeScreen


class TutorialScreen(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("GestureBoard Tutorial")
        self.resize(1000, 600)

        self.setStyleSheet("""
            QWidget{
                background:#111827;
                color:white;
            }

            QLabel{
                color:white;
            }

            QPushButton{
                background:#2563EB;
                color:white;
                border:none;
                border-radius:8px;
                padding:10px;
                min-width:120px;
                font-size:14px;
            }

            QPushButton:hover{
                background:#3B82F6;
            }
        """)

        self.stack = QStackedWidget()

        self.stack.addWidget(self.page1())
        self.stack.addWidget(self.page2())
        self.stack.addWidget(self.page3())

        mainLayout = QVBoxLayout()

        mainLayout.addWidget(self.stack)

        self.setLayout(mainLayout)

    # -------------------------
    # PAGE 1
    # -------------------------

    def page1(self):

        page = QWidget()

        layout = QVBoxLayout()

        layout.addStretch()

        title = QLabel("Welcome to GestureBoard")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:32px;font-weight:bold;")

        subtitle = QLabel(
            "Control presentations using simple hand gestures.\n\n"
            "This quick tutorial will show you the available features."
        )

        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size:18px;color:lightgray;")

        layout.addWidget(title)
        layout.addWidget(subtitle)

        layout.addStretch()

        buttons = QHBoxLayout()

        skip = QPushButton("Skip")
        nextBtn = QPushButton("Next")

        skip.clicked.connect(self.finishTutorial)
        nextBtn.clicked.connect(self.nextPage)

        buttons.addStretch()
        buttons.addWidget(skip)
        buttons.addWidget(nextBtn)

        layout.addLayout(buttons)

        page.setLayout(layout)

        return page

    # -------------------------
    # PAGE 2
    # -------------------------

    def page2(self):

        page = QWidget()

        layout = QVBoxLayout()

        layout.addStretch()

        title = QLabel("Virtual Mouse")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:32px;font-weight:bold;")

        info = QLabel(
            "• Move Cursor - Index Finger\n\n"
            "• Left Click - Thumb + Index Pinch\n\n"
            "• Right Click - Thumb + Middle Pinch\n\n"
            "• Scroll - Open Palm"
        )

        info.setAlignment(Qt.AlignCenter)
        info.setStyleSheet("font-size:18px;color:lightgray;")

        layout.addWidget(title)
        layout.addWidget(info)

        layout.addStretch()

        buttons = QHBoxLayout()

        back = QPushButton("Back")
        nextBtn = QPushButton("Next")

        back.clicked.connect(self.previousPage)
        nextBtn.clicked.connect(self.nextPage)

        buttons.addWidget(back)
        buttons.addStretch()
        buttons.addWidget(nextBtn)

        layout.addLayout(buttons)

        page.setLayout(layout)

        return page

    # -------------------------
    # PAGE 3
    # -------------------------

    def page3(self):

        page = QWidget()

        layout = QVBoxLayout()

        layout.addStretch()

        title = QLabel("Presentation Controls")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:32px;font-weight:bold;")

        info = QLabel(
            "• Start Presentation\n\n"
            "• Next Slide\n\n"
            "• Previous Slide\n\n"
            "• End Presentation"
        )

        info.setAlignment(Qt.AlignCenter)
        info.setStyleSheet("font-size:18px;color:lightgray;")

        layout.addWidget(title)
        layout.addWidget(info)

        layout.addStretch()

        buttons = QHBoxLayout()

        back = QPushButton("Back")
        finish = QPushButton("Finish")

        back.clicked.connect(self.previousPage)
        finish.clicked.connect(self.finishTutorial)

        buttons.addWidget(back)
        buttons.addStretch()
        buttons.addWidget(finish)

        layout.addLayout(buttons)

        page.setLayout(layout)

        return page

    # -------------------------

    def nextPage(self):

        index = self.stack.currentIndex()

        if index < self.stack.count()-1:
            self.stack.setCurrentIndex(index+1)

    # -------------------------

    def previousPage(self):

        index = self.stack.currentIndex()

        if index > 0:
            self.stack.setCurrentIndex(index-1)

    # -------------------------

    def finishTutorial(self):

        self.home = HomeScreen()
        self.home.show()

        self.close()