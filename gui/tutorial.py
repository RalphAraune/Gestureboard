from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class TutorialPage(QWidget):
    """Card-based introduction to GestureBoard's three main tools."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("tutorialPage")
        self.setStyleSheet("""
            QWidget#tutorialPage { background: #F5FEFF; }
            QFrame#tutorialCard {
                background: #FFFFFF; border: 1px solid #AAC0E1; border-radius: 18px;
            }
            QLabel { background: transparent; color: #0E2F76; }
            QLabel#eyebrow { color: #AAC0E1; font-size: 12px; font-weight: 700; }
            QLabel#title { font-size: 28px; font-weight: 800; color: #0E2F76; }
            QLabel#description { color: #5A6B93; font-size: 14px; }
            QFrame#gestureRow {
                background: #EFF4FC; border: 1px solid #AAC0E1; border-radius: 8px;
            }
            QLabel#gestureName { color: #0E2F76; font-size: 13px; }
            QLabel#gestureAction { color: #2C55A6; font-size: 12px; font-weight: 600; }
            QLabel#pageDot { color: #AAC0E1; font-size: 18px; }
            QLabel#pageDotActive { color: #0E2F76; font-size: 18px; }
            QPushButton {
                background: #0E2F76; color: #F5FEFF; border: none; border-radius: 9px;
                padding: 11px 22px; min-width: 110px; font-size: 13px; font-weight: 700;
            }
            QPushButton:hover { background: #1B4499; }
            QPushButton#backButton { background: #F5FEFF; color: #5A6B93; border: 1px solid #AAC0E1; }
            QPushButton#backButton:hover { background: #EFF4FC; color: #0E2F76; }
            QPushButton#backButton:disabled { color: #AAC0E1; background: #F5FEFF; border-color: #CDDBF0; }
            QLabel#footer { color: #AAC0E1; font-size: 11px; }
        """)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_page(
            page_index=0,
            number="01", title="Presentation Navigation",
            description="Navigate your slides naturally with clear hand gestures detected by your webcam.",
            visual_icon="☝", visual_caption="Gesture navigation",
            gestures=[("Open palm", "Start presentation"), ("Swipe right", "Next slide"),
                      ("Swipe left", "Previous slide"), ("Closed fist", "End presentation")],
        ))
        self.stack.addWidget(self._build_page(
            page_index=1,
            number="02", title="Virtual Mouse Control",
            description="Control your computer cursor naturally using hand gestures detected by your webcam.",
            visual_icon="✋", visual_caption="Index finger controls cursor",
            gestures=[("Point up", "Move cursor"), ("Pinch", "Left click"),
                      ("Two fingers", "Right click"), ("Open hand", "Scroll mode")],
        ))
        self.stack.addWidget(self._build_page(
            page_index=2,
            number="03", title="Whiteboard & Annotation",
            description="Draw and annotate freely on the whiteboard using your regular computer mouse.",
            visual_icon="✎", visual_caption="Mouse-based drawing",
            gestures=[("Left mouse button", "Draw / annotate"), ("Mouse wheel", "Change canvas view"),
                      ("Eraser tool", "Remove marks")],
            mouse_only=True,
        ))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 12)
        layout.addStretch()
        layout.addWidget(self.stack, 0, Qt.AlignCenter)
        layout.addStretch()
        footer = QLabel("GestureBoard  •  Powered by OpenCV, MediaPipe & Computer Vision")
        footer.setObjectName("footer")
        footer.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer)

    def _build_page(self, page_index, number, title, description, visual_icon, visual_caption, gestures, mouse_only=False):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("tutorialCard")
        card.setMinimumSize(480, 360)
        card.setMaximumSize(560, 435)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 20, 22, 14)
        card_layout.setSpacing(12)

        eyebrow = QLabel(f"{number}  •  {'MOUSE TOOLS' if mouse_only else 'GESTURE CONTROLS'}")
        eyebrow.setObjectName("eyebrow")
        card_layout.addWidget(eyebrow)

        content = QHBoxLayout()
        content.setSpacing(16)

        visual = QFrame()
        visual.setObjectName("gestureRow")
        visual.setMinimumSize(145, 170)
        visual.setMaximumSize(185, 210)
        visual.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        visual_layout = QVBoxLayout(visual)
        visual_layout.setContentsMargins(14, 16, 14, 14)
        icon = QLabel(visual_icon)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size: 64px; color: #0E2F76;")
        caption = QLabel(visual_caption)
        caption.setAlignment(Qt.AlignCenter)
        caption.setWordWrap(True)
        caption.setStyleSheet("font-size: 11px; color: #8A94A6;")
        visual_layout.addStretch()
        visual_layout.addWidget(icon)
        visual_layout.addStretch()
        visual_layout.addWidget(caption)

        details = QVBoxLayout()
        details.setSpacing(8)
        heading = QLabel(title)
        heading.setObjectName("title")
        heading.setWordWrap(True)
        body = QLabel(description)
        body.setObjectName("description")
        body.setWordWrap(True)
        details.addWidget(heading)
        details.addWidget(body)
        details.addSpacing(3)
        for name, action in gestures:
            details.addWidget(self._gesture_row(name, action))
        details.addStretch()

        content.addWidget(visual)
        content.addLayout(details, 1)
        card_layout.addLayout(content)
        card_layout.addStretch()
        card_layout.addLayout(self._dots(page_index))
        card_layout.addLayout(self._buttons(page_index))

        page_layout.addWidget(card, 0, Qt.AlignCenter)
        return page

    def _gesture_row(self, name, action):
        row = QFrame()
        row.setObjectName("gestureRow")
        row.setFixedHeight(34)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 0, 10, 0)
        name_label = QLabel(name)
        name_label.setObjectName("gestureName")
        action_label = QLabel(action)
        action_label.setObjectName("gestureAction")
        layout.addWidget(name_label)
        layout.addStretch()
        layout.addWidget(action_label)
        return row

    def _dots(self, active_index):
        dots = QHBoxLayout()
        dots.setSpacing(5)
        dots.addStretch()
        for index in range(3):
            dot = QLabel("●")
            dot.setObjectName("pageDotActive" if index == active_index else "pageDot")
            dots.addWidget(dot)
        dots.addStretch()
        return dots

    def _buttons(self, page_index):
        buttons = QHBoxLayout()
        back = QPushButton("← Back")
        back.setObjectName("backButton")
        # On the first page, disable Back to avoid a broken route/loop.
        back.setEnabled(page_index > 0)
        next_button = QPushButton("Get started" if page_index == 2 else "Next →")
        skip_button = QPushButton("Skip")
        skip_button.setObjectName("backButton")
        back.clicked.connect(self.previousPage)
        next_button.clicked.connect(self.nextPage)
        skip_button.clicked.connect(self.finishTutorial)
        buttons.addWidget(back)
        buttons.addStretch()
        buttons.addWidget(skip_button)
        buttons.addWidget(next_button)
        return buttons

    def nextPage(self):
        current = self.stack.currentIndex()
        if current < self.stack.count() - 1:
            self.stack.setCurrentIndex(current + 1)
        else:
            self.finishTutorial()

    def previousPage(self):
        current = self.stack.currentIndex()
        if current > 0:
            self.stack.setCurrentIndex(current - 1)

    def finishTutorial(self):
        if self.parent_window:
            self.parent_window.showCameraSetup()
