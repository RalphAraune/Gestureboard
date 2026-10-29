from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from gui.virtual_mouse import GESTURE_GUIDE as VIRTUAL_MOUSE_GESTURES


# ==============================================================
# TUTORIAL CONTENT
#
# Each step mirrors the gesture guide of the real page, so what
# the tutorial teaches is what the app actually does.
# ==============================================================

STEPS = [
    {
        "rail": "Presentation control",
        "title": "Run your slides with your hand",
        "description": (
            "Move through a slideshow, point at things and draw on "
            "your slides without touching the keyboard."
        ),
        "start": [
            "Open Presentation Control from the sidebar.",
            "Press Upload File and choose your slides.",
            "Press Start Presentation and face the camera.",
        ],
        "groups": [
            ("Slides", [
                ("🤘", "Rock sign", "Start the presentation"),
                ("👉", "Swipe open hand right", "Next slide"),
                ("👈", "Swipe open hand left", "Previous slide"),
                ("👍", "Thumbs up", "Full screen"),
                ("👎", "Thumbs down", "Exit full screen"),
            ]),
            ("Pointer and drawing", [
                ("☝️", "Index finger", "Pointer on the slide"),
                ("🖖", "Three fingers up", "Turn drawing on"),
                ("✌️", "Index and middle together", "Draw"),
                ("✌️", "Index and middle apart", "Stop drawing"),
                ("✋", "Open hand", "Move the cursor or pick a tool"),
                ("✊", "Closed hand", "Click"),
                ("👋", "Wave open hand side to side", "Clear this slide's drawing"),
                ("🤙", "Pinky finger up", "Close drawing (🖖 opens it again)"),
            ]),
        ],
        "tip": "Keep your hand about an arm's length from the camera, "
               "with your palm facing it.",
    },
    {
        "rail": "Virtual mouse",
        "title": "Use your hand as a mouse",
        "description": (
            "Move the cursor, click and scroll anywhere on your "
            "computer, even while GestureBoard is minimized."
        ),
        "start": [
            "Open Virtual Mouse from the sidebar.",
            "Press Start.",
            "Hold an open palm in front of the camera.",
        ],
        "groups": [
            ("Gestures", [
                (icon, name, action)
                for _key, icon, name, action in VIRTUAL_MOUSE_GESTURES
            ]),
        ],
        "tip": "Each closed hand or pinch clicks once. Open your hand "
               "again before the next click.",
    },
    {
        "rail": "Whiteboard",
        "title": "Draw on the whiteboard",
        "description": (
            "Write and sketch on a blank board with hand gestures, "
            "or with your regular mouse."
        ),
        "start": [
            "Start the Virtual Mouse first. The whiteboard uses its camera.",
            "Open Whiteboard from the sidebar.",
            "Close your hand on a tool or colour, then draw.",
        ],
        "groups": [
            ("Gestures", [
                ("🖐️", "Open palm", "Move the cursor"),
                ("✊", "Closed hand", "Click a tool, colour or button"),
                ("✌️", "Index and middle together", "Draw with the selected tool"),
                ("✌️", "Index and middle apart", "Lift the pen"),
            ]),
        ],
        "tip": "Use Undo, Redo and Save in the toolbar. "
               "A normal mouse works on the board as well.",
    },
]


# Card colour: "Marble", a cool off-white that suits the navy / cyan brand.
MARBLE = "#F2F8FC"


# ==============================================================
# BACKGROUND
#
# Faint hand-landmark "constellations" (dots joined by lines),
# the same visual language as the GestureBoard logo.
# ==============================================================

# One open hand, in a 0..1 box: wrist, then each finger base -> tip.
_HAND_POINTS = {
    "wrist": (0.50, 0.98),
    "thumb": [(0.30, 0.80), (0.16, 0.66), (0.06, 0.55)],
    "index": [(0.36, 0.52), (0.33, 0.30), (0.31, 0.10)],
    "middle": [(0.50, 0.48), (0.50, 0.24), (0.50, 0.00)],
    "ring": [(0.63, 0.51), (0.66, 0.30), (0.68, 0.12)],
    "pinky": [(0.75, 0.58), (0.81, 0.42), (0.86, 0.28)],
}


class ConstellationBackground(QWidget):

    CYAN = QColor(34, 195, 222)
    NAVY = QColor(14, 47, 118)

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setAttribute(Qt.WA_StyledBackground, True)

    def _draw_hand(self, painter, x, y, size, angle, color, alpha):

        painter.save()
        painter.translate(x, y)
        painter.rotate(angle)
        painter.translate(-size / 2, -size / 2)

        def pt(p):
            return QPointF(p[0] * size, p[1] * size)

        line = QColor(color)
        line.setAlpha(alpha)

        dot = QColor(color)
        dot.setAlpha(min(255, int(alpha * 1.8)))

        pen = QPen(line, max(1.5, size / 160))
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)

        wrist = pt(_HAND_POINTS["wrist"])
        bases = []

        for finger in ("thumb", "index", "middle", "ring", "pinky"):

            points = [pt(p) for p in _HAND_POINTS[finger]]

            painter.drawLine(wrist, points[0])

            for a, b in zip(points, points[1:]):
                painter.drawLine(a, b)

            bases.append(points[0])

        # Knuckle line across the palm
        for a, b in zip(bases[1:], bases[2:]):
            painter.drawLine(a, b)

        painter.setPen(Qt.NoPen)
        painter.setBrush(dot)

        radius = max(2.5, size / 70)

        painter.drawEllipse(wrist, radius * 1.3, radius * 1.3)

        for finger in ("thumb", "index", "middle", "ring", "pinky"):
            for p in _HAND_POINTS[finger]:
                painter.drawEllipse(pt(p), radius, radius)

        painter.restore()

    def paintEvent(self, event):

        # Same soft-blue page, dot grid and corner hand as Saved Files.
        # The tutorial is styled for light mode only, so it stays light.
        from widgets import page_background

        page_background.paint_page_background(
            self, page_background.page_colors(dark=False)
        )


# ==============================================================
# TUTORIAL PAGE
# ==============================================================

class TutorialPage(ConstellationBackground):
    """Three-step introduction to GestureBoard's main tools."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setObjectName("tutorialPage")

        from widgets import page_background

        self.setStyleSheet(page_background.LAYER_RULE + """
            QLabel { background: transparent; color: #0E2F76; }

            QFrame#tutorialCard {
                background: #F2F8FC;
                border: 1px solid #C9D6EA;
                border-radius: 20px;
            }

            /* ---------- step rail ---------- */
            QFrame#rail {
                background: #E4EEF6;
                border: none;
                border-top-left-radius: 20px;
                border-bottom-left-radius: 20px;
            }
            QLabel#railTitle { color: #0E2F76; font-size: 18px; font-weight: 800; }
            QLabel#railHint { color: #5A6B93; font-size: 13px; }
            QPushButton#railStep {
                background: transparent;
                color: #5A6B93;
                border: none;
                border-radius: 10px;
                padding: 12px 14px;
                text-align: left;
                font-size: 15px;
                font-weight: 600;
            }
            QPushButton#railStep:hover { background: #D9E6F1; color: #0E2F76; }
            QPushButton#railStep:checked {
                background: #0E2F76;
                color: #F5FEFF;
            }

            /* ---------- content ---------- */
            QScrollArea#contentScroll, QWidget#contentPage { background: transparent; border: none; }
            QScrollArea#contentScroll QScrollBar:vertical {
                background: transparent; width: 8px; margin: 2px 0;
            }
            QScrollArea#contentScroll QScrollBar::handle:vertical {
                background: #C9D6EA; border-radius: 4px; min-height: 40px;
            }
            QScrollArea#contentScroll QScrollBar::handle:vertical:hover { background: #AAC0E1; }
            QScrollArea#contentScroll QScrollBar::add-line:vertical,
            QScrollArea#contentScroll QScrollBar::sub-line:vertical { height: 0; }
            QScrollArea#contentScroll QScrollBar::add-page:vertical,
            QScrollArea#contentScroll QScrollBar::sub-page:vertical { background: transparent; }
            QLabel#stepCount { color: #2C9DB5; font-size: 14px; font-weight: 700; }
            QLabel#title { color: #0E2F76; font-size: 32px; font-weight: 800; }
            QLabel#description { color: #4A5679; font-size: 16px; }
            QLabel#section { color: #0E2F76; font-size: 16px; font-weight: 700; }

            QLabel#startNumber {
                background: #DDF4F8;
                color: #137A8E;
                border-radius: 13px;
                font-size: 13px;
                font-weight: 800;
            }
            QLabel#startText { color: #263B6A; font-size: 15px; }

            QFrame#gestureTile {
                background: #EAF3FA;
                border: 1px solid #D3E1EE;
                border-radius: 12px;
            }
            QLabel#gestureIcon {
                background: #DCE9F4;
                border-radius: 10px;
                font-family: "Segoe UI Emoji";
                font-size: 22px;
                color: #0E2F76;
                font-weight: 700;
            }
            QLabel#gestureName { color: #0E2F76; font-size: 15px; font-weight: 700; }
            QLabel#gestureAction { color: #4A5679; font-size: 14px; }

            QFrame#tip {
                background: #E6F6F9;
                border: none;
                border-left: 4px solid #22C3DE;
                border-radius: 8px;
            }
            QLabel#tipText { color: #1D4E5C; font-size: 14px; }

            /* ---------- navigation ---------- */
            QPushButton {
                background: #0E2F76; color: #F5FEFF; border: none; border-radius: 10px;
                padding: 12px 26px; min-width: 120px; font-size: 15px; font-weight: 700;
            }
            QPushButton:hover { background: #1B4499; }
            QPushButton#ghostButton {
                background: transparent; color: #5A6B93; border: 1px solid #AAC0E1;
            }
            QPushButton#ghostButton:hover { background: #E4EEF6; color: #0E2F76; }
            QPushButton#ghostButton:disabled { color: #B8C6DC; border-color: #D5E0EF; }
            QPushButton:focus { outline: none; border: 2px solid #22C3DE; }

            QLabel#footer { color: #8A9AB8; font-size: 12px; }
        """)

        # ------------------------------------------------------
        # CARD
        # ------------------------------------------------------

        self.card = QFrame()
        self.card.setObjectName("tutorialCard")
        self.card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        card_layout = QHBoxLayout(self.card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        card_layout.addWidget(self._build_rail())

        right = QVBoxLayout()
        right.setContentsMargins(40, 32, 40, 26)
        right.setSpacing(18)

        self.stack = QStackedWidget()

        # Gesture grids, re-flowed into 1-3 columns on resize.
        self.gesture_grids = []
        self._columns = 0

        for index, step in enumerate(STEPS):
            self.stack.addWidget(self._build_step(index, step))

        right.addWidget(self.stack, 1)
        right.addLayout(self._build_navigation())

        card_layout.addLayout(right, 1)

        # ------------------------------------------------------
        # PAGE
        # ------------------------------------------------------

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 16)
        layout.setSpacing(12)

        # Centre the card horizontally while letting it grow up to its
        # maximum width (an alignment flag would pin it to its size hint).
        card_row = QHBoxLayout()
        card_row.addStretch(1)
        card_row.addWidget(self.card, 100)
        card_row.addStretch(1)

        layout.addLayout(card_row, 1)

        footer = QLabel("GestureBoard uses your webcam with OpenCV and MediaPipe hand tracking.")
        footer.setObjectName("footer")
        footer.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer)

        self.reflow_gestures(2)
        self.goToPage(0)

        # Plain containers let the shared page background show through.
        page_background.clear_layers(self)

    # ==========================================================
    # LAYOUT PIECES
    # ==========================================================

    def _build_rail(self):

        rail = QFrame()
        rail.setObjectName("rail")
        rail.setFixedWidth(250)

        layout = QVBoxLayout(rail)
        layout.setContentsMargins(20, 32, 20, 24)
        layout.setSpacing(6)

        title = QLabel("Getting started")
        title.setObjectName("railTitle")

        hint = QLabel("Three tools, each controlled by your hand.")
        hint.setObjectName("railHint")
        hint.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addSpacing(18)

        self.rail_group = QButtonGroup(self)
        self.rail_group.setExclusive(True)

        for index, step in enumerate(STEPS):

            button = QPushButton(f"{index + 1}   {step['rail']}")
            button.setObjectName("railStep")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _=False, i=index: self.goToPage(i))

            self.rail_group.addButton(button, index)
            layout.addWidget(button)

        layout.addStretch()

        return rail

    def _build_step(self, index, step):

        page = QWidget()
        page.setObjectName("contentPage")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 12, 0)
        layout.setSpacing(10)

        count = QLabel(f"Step {index + 1} of {len(STEPS)}")
        count.setObjectName("stepCount")

        title = QLabel(step["title"])
        title.setObjectName("title")
        title.setWordWrap(True)

        description = QLabel(step["description"])
        description.setObjectName("description")
        description.setWordWrap(True)

        layout.addWidget(count)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addSpacing(10)

        # How to start (a real sequence, so it is numbered)
        layout.addWidget(self._section("How to start"))

        for number, text in enumerate(step["start"], start=1):
            layout.addLayout(self._start_row(number, text))

        # Gesture groups
        for group_title, gestures in step["groups"]:

            layout.addSpacing(12)
            layout.addWidget(self._section(group_title))

            grid = QGridLayout()
            grid.setHorizontalSpacing(12)
            grid.setVerticalSpacing(10)

            tiles = [
                self._gesture_tile(icon, name, action)
                for icon, name, action in gestures
            ]

            self.gesture_grids.append((grid, tiles))

            layout.addLayout(grid)

        # Tip
        layout.addSpacing(12)
        layout.addWidget(self._tip(step["tip"]))
        layout.addStretch()

        scroll = QScrollArea()
        scroll.setObjectName("contentScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(page)

        return scroll

    def _section(self, text):

        label = QLabel(text)
        label.setObjectName("section")

        return label

    def _start_row(self, number, text):

        row = QHBoxLayout()
        row.setSpacing(12)

        badge = QLabel(str(number))
        badge.setObjectName("startNumber")
        badge.setFixedSize(26, 26)
        badge.setAlignment(Qt.AlignCenter)

        label = QLabel(text)
        label.setObjectName("startText")
        label.setWordWrap(True)

        row.addWidget(badge, 0, Qt.AlignTop)
        row.addWidget(label, 1)

        return row

    def _gesture_tile(self, icon, name, action):

        tile = QFrame()
        tile.setObjectName("gestureTile")
        tile.setMinimumHeight(70)

        layout = QHBoxLayout(tile)
        layout.setContentsMargins(12, 10, 14, 10)
        layout.setSpacing(14)

        icon_label = QLabel(icon)
        icon_label.setObjectName("gestureIcon")
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignCenter)

        text = QVBoxLayout()
        text.setSpacing(2)

        name_label = QLabel(name)
        name_label.setObjectName("gestureName")
        name_label.setWordWrap(True)

        action_label = QLabel(action)
        action_label.setObjectName("gestureAction")
        action_label.setWordWrap(True)

        text.addWidget(name_label)
        text.addWidget(action_label)

        layout.addWidget(icon_label)
        layout.addLayout(text, 1)

        return tile

    def _tip(self, text):

        frame = QFrame()
        frame.setObjectName("tip")

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)

        label = QLabel(text)
        label.setObjectName("tipText")
        label.setWordWrap(True)

        layout.addWidget(label)

        return frame

    def _build_navigation(self):

        nav = QHBoxLayout()
        nav.setSpacing(10)

        self.back_button = QPushButton("Back")
        self.back_button.setObjectName("ghostButton")
        self.back_button.clicked.connect(self.previousPage)

        self.skip_button = QPushButton("Skip tutorial")
        self.skip_button.setObjectName("ghostButton")
        self.skip_button.clicked.connect(self.finishTutorial)

        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self.nextPage)

        for button in (self.back_button, self.skip_button, self.next_button):
            button.setCursor(Qt.PointingHandCursor)

        nav.addWidget(self.back_button)
        nav.addStretch()
        nav.addWidget(self.skip_button)
        nav.addWidget(self.next_button)

        return nav

    # ==========================================================
    # RESPONSIVE SIZE
    # ==========================================================

    def resizeEvent(self, event):

        super().resizeEvent(event)

        # Large card that fills most of the window, capped for readability.
        self.card.setMaximumWidth(min(1180, max(760, self.width() - 80)))

        # Content width = card width - rail - side padding.
        content = min(self.card.maximumWidth(), self.width() - 80) - 250 - 92

        if content >= 780:
            columns = 3
        elif content >= 460:
            columns = 2
        else:
            columns = 1

        self.reflow_gestures(columns)

    def reflow_gestures(self, columns):
        """Lay the gesture tiles out in the given number of columns."""

        if columns == self._columns:
            return

        self._columns = columns

        for grid, tiles in self.gesture_grids:

            for tile in tiles:
                grid.removeWidget(tile)

            for i, tile in enumerate(tiles):
                grid.addWidget(tile, i // columns, i % columns)

            for c in range(3):
                grid.setColumnStretch(c, 1 if c < columns else 0)

    # ==========================================================
    # NAVIGATION
    # ==========================================================

    def goToPage(self, index):

        self.stack.setCurrentIndex(index)

        self.rail_group.button(index).setChecked(True)

        last = index == self.stack.count() - 1

        self.back_button.setEnabled(index > 0)
        self.skip_button.setVisible(not last)
        self.next_button.setText("Set up camera" if last else "Next")

    def nextPage(self):
        current = self.stack.currentIndex()
        if current < self.stack.count() - 1:
            self.goToPage(current + 1)
        else:
            self.finishTutorial()

    def previousPage(self):
        current = self.stack.currentIndex()
        if current > 0:
            self.goToPage(current - 1)

    def finishTutorial(self):
        if self.parent_window:
            self.parent_window.showCameraSetup()
