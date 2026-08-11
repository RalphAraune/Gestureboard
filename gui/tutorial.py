from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
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
            QWidget#tutorialPage { background: #071426; }
            QFrame#tutorialCard {
                background: #0F1E35; border: 1px solid #294263; border-radius: 18px;
            }
            QLabel { background: transparent; color: #F4F7FF; }
            QLabel#eyebrow { color: #71809C; font-size: 12px; font-weight: 700; }
            QLabel#title { font-size: 28px; font-weight: 700; }
            QLabel#description { color: #9DA8BF; font-size: 14px; }
            QFrame#gestureRow {
                background: #152842; border: 1px solid #284869; border-radius: 8px;
            }
            QLabel#gestureName { color: #DFE6F5; font-size: 13px; }
            QLabel#gestureAction { color: #4B8CFF; font-size: 12px; font-weight: 600; }
            QLabel#pageDot { color: #45506A; font-size: 18px; }
            QLabel#pageDotActive { color: #4381FF; font-size: 18px; }
            QPushButton {
                background: #3E7CF7; color: white; border: none; border-radius: 9px;
                padding: 11px 22px; min-width: 110px; font-size: 13px; font-weight: 700;
            }
            QPushButton:hover { background: #5790FF; }
            QPushButton#backButton { background: #152842; color: #B6C0D4; border: 1px solid #284869; }
            QPushButton#backButton:hover { background: #1B3555; }
            QLabel#footer { color: #59657E; font-size: 11px; }
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
        card.setFixedSize(560, 435)
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
        visual.setFixedSize(185, 210)
        visual_layout = QVBoxLayout(visual)
        visual_layout.setContentsMargins(14, 16, 14, 14)
        icon = QLabel(visual_icon)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size: 64px; color: #4B8CFF;")
        caption = QLabel(visual_caption)
        caption.setAlignment(Qt.AlignCenter)
        caption.setWordWrap(True)
        caption.setStyleSheet("font-size: 11px; color: #8390A9;")
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
        next_button = QPushButton("Get started" if page_index == 2 else "Next →")
        back.clicked.connect(self.previousPage)
        next_button.clicked.connect(self.nextPage)
        buttons.addWidget(back)
        buttons.addStretch()
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
            self.parent_window.showHome()
