from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QHBoxLayout
)
from PyQt5.QtCore import Qt, QPoint


class TitleBar(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.parent_window = parent
        self.dragPos = QPoint()

        self.setFixedHeight(45)

        self.setStyleSheet("""
            QWidget{
                background:#1F2937;
            }

            QLabel{
                color:white;
                font-size:14px;
            }

            QPushButton{
                background:transparent;
                color:white;
                border:none;
                font-size:16px;
                min-width:45px;
                min-height:45px;
            }

            QPushButton:hover{
                background:#374151;
            }

            QPushButton#closeButton:hover{
                background:#EF4444;
            }
        """)

        # -----------------------------------
        # App Name
        # -----------------------------------

        title = QLabel("GestureBoard")
        title.setStyleSheet("""
            font-size:16px;
            font-weight:bold;
        """)

        # -----------------------------------
        # Status
        # -----------------------------------

        status = QLabel("🟢 Camera Ready")

        # -----------------------------------
        # Window Buttons
        # -----------------------------------

        self.minBtn = QPushButton("—")

        self.maxBtn = QPushButton("□")

        self.closeBtn = QPushButton("✕")
        self.closeBtn.setObjectName("closeButton")

        self.minBtn.clicked.connect(self.minimize)

        self.maxBtn.clicked.connect(self.maximizeRestore)

        self.closeBtn.clicked.connect(self.closeWindow)

        # -----------------------------------
        # Layout
        # -----------------------------------

        layout = QHBoxLayout()

        layout.setContentsMargins(15, 0, 0, 0)

        layout.addWidget(title)

        layout.addStretch()

        layout.addWidget(status)

        layout.addStretch()

        layout.addWidget(self.minBtn)

        layout.addWidget(self.maxBtn)

        layout.addWidget(self.closeBtn)

        layout.setSpacing(0)

        self.setLayout(layout)

    # =======================================================
    # Window Buttons
    # =======================================================

    def minimize(self):
        self.window().showMinimized()

    def maximizeRestore(self):

        if self.window().isMaximized():
            self.window().showNormal()
            self.maxBtn.setText("□")
        else:
            self.window().showMaximized()
            self.maxBtn.setText("❐")

    def closeWindow(self):
        self.window().close()

    # =======================================================
    # Drag Window
    # =======================================================

    def mousePressEvent(self, event):

        if event.button() == Qt.LeftButton:
            self.dragPos = event.globalPos()

    def mouseMoveEvent(self, event):

        if event.buttons() == Qt.LeftButton:

            if self.window().isMaximized():
                return

            self.window().move(
                self.window().pos() + event.globalPos() - self.dragPos
            )

            self.dragPos = event.globalPos()

    # =======================================================
    # Double Click = Maximize
    # =======================================================

    def mouseDoubleClickEvent(self, event):
        self.maximizeRestore()