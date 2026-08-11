from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class TitleBar(QWidget):
    """Compact, draggable title bar for the frameless main window."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dragPos = QPoint()
        self.setFixedHeight(45)
        self.setStyleSheet("""
            QWidget { background: #0B1B32; }
            QLabel { color: white; font-size: 14px; }
            QPushButton {
                background: transparent; color: white; border: none; font-size: 18px;
                min-width: 45px; min-height: 45px;
            }
            QPushButton:hover { background: #173454; }
            QPushButton#closeButton:hover { background: #EF4444; }
        """)

        title = QLabel("GestureBoard")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        status = QLabel("●  System Ready")
        status.setStyleSheet("color: #45D99A; font-size: 12px;")
        self.minBtn = QPushButton("−")
        self.maxBtn = QPushButton("□")
        self.closeBtn = QPushButton("×")
        self.closeBtn.setObjectName("closeButton")
        self.minBtn.clicked.connect(lambda: self.window().showMinimized())
        self.maxBtn.clicked.connect(self.maximizeRestore)
        self.closeBtn.clicked.connect(lambda: self.window().close())

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(status)
        layout.addStretch()
        layout.addWidget(self.minBtn)
        layout.addWidget(self.maxBtn)
        layout.addWidget(self.closeBtn)

    def maximizeRestore(self):
        if self.window().isMaximized():
            self.window().showNormal()
            self.maxBtn.setText("□")
        else:
            self.window().showMaximized()
            self.maxBtn.setText("❐")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragPos = event.globalPos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and not self.window().isMaximized():
            self.window().move(self.window().pos() + event.globalPos() - self.dragPos)
            self.dragPos = event.globalPos()

    def mouseDoubleClickEvent(self, event):
        self.maximizeRestore()
