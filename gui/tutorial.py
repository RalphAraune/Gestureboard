from PyQt5.QtCore import Qt, QPointF, QRectF, QSize
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QFrame,
    QGraphicsDropShadowEffect,
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
# the tutorial teaches is what the app actually does. Other pages
# reuse these lists: look a step up with step("key"), never by
# its position, so the order here can change freely.
# ==============================================================

# Drawing on slides in Presentation Control. One list, shown in the
# Presentation Control guide, Settings and both tutorial steps, so
# they always match what the page does.
ANNOTATION_GESTURES = [
    ("☝️", "Index finger", "Pointer"),
    ("🖖", "Three fingers up", "Turn drawing on"),
    ("✌️", "Index and middle together", "Draw"),
    ("✌️", "Index and middle apart", "Move the cursor"),
    ("✋", "Open hand", "Move the cursor"),
    ("✊", "Closed hand", "Click or pick a tool"),
    ("✊", "Closed hand on the circle, 1 s", "Move the circle"),
    ("👌", "OK sign, 1 s", "Clear this slide"),
    ("🤙", "Pinky finger up", "Close drawing"),
]


STEPS = [
    {
        "key": "camera",
        "rail": "Camera setup",
        "title": "Set up your camera first",
        "description": (
            "GestureBoard watches your hand through your webcam. "
            "Presentation Control, the Virtual Mouse, the Whiteboard and "
            "drawing on slides by hand all need it, so set it up before "
            "anything else."
        ),
        "flow": [
            ("📷", "Your webcam sees your hand",
             "Only your hand is used. Nothing is recorded or saved."),
            ("hand", "21 points are tracked",
             "Every knuckle and fingertip is followed as it moves."),
            ("⚡", "The shape becomes an action",
             "A thumbs up, a pinch or a swipe does something on screen."),
        ],
        "start_title": "How to set it up",
        "start": [
            "Open Camera Setup from the sidebar. This tutorial takes you "
            "there when you finish.",
            "Choose your webcam from the list. Press ⟳ if it is missing.",
            "Press Test camera and hold up your hand. Dots and lines appear "
            "on it when tracking works.",
            "Press Continue.",
        ],
        "groups": [
            ("What needs the camera", [
                ("🎞️", "Presentation Control", "Change slides and point by hand"),
                ("🖱️", "Virtual Mouse", "Move the cursor and click by hand"),
                ("🖍️", "Annotation", "Draw on your slides by hand"),
                ("✏️", "Whiteboard", "Uses the Virtual Mouse camera"),
            ]),
            ("For steady tracking", [
                ("💡", "Light from the front", "A bright window behind you hides your hand"),
                ("📏", "About an arm's length away", "Keep your whole hand in the picture"),
                ("🖐️", "Palm towards the camera", "Spread your fingers so each one shows"),
                ("🖼️", "A plain background", "Busy patterns make the tracking jumpy"),
            ]),
        ],
        "tip": "Changed webcams? Pick the new one in Camera Setup. "
               "GestureBoard remembers your choice for next time.",
    },
    {
        "key": "presentation",
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
            ("Pointer and drawing", ANNOTATION_GESTURES),
        ],
        "tip": "Keep your hand about an arm's length from the camera, "
               "with your palm facing it.",
    },
    {
        "key": "virtual_mouse",
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
        "key": "annotation",
        "rail": "Annotation",
        "title": "Draw on your slides while presenting",
        "description": (
            "Write, highlight and erase on your slides by hand during a "
            "presentation. You can also mark up any PDF with the mouse."
        ),
        "start": [
            "Open your slides in Presentation Control first.",
            "Open Annotation from the sidebar and press Start, or hold up "
            "three fingers 🖖 while presenting.",
            "A floating circle appears in the upper right of the slides. "
            "Close your hand on it to open the pen, marker, eraser, colours "
            "and sizes.",
        ],
        "groups": [
            ("Hand gestures", ANNOTATION_GESTURES),
            ("Annotation page buttons", [
                ("▶", "Start or Resume", "Show the floating circle on your slides"),
                ("❚❚", "Pause", "Hide the floating circle and keep the drawings"),
                ("■", "Stop", "End annotating and clear every slide"),
            ]),
            ("Mark up a PDF with the mouse", [
                ("Ctrl+O", "Open PDF", "Choose the file to mark up"),
                ("P", "Pen", "Write in thin ink"),
                ("H", "Marker", "Highlight words"),
                ("E", "Eraser", "Remove ink, never the page"),
                ("Ctrl+Z", "Undo", "Ctrl+Y brings it back"),
                ("Ctrl+S", "Save", "Save the page with its ink as an image"),
            ]),
        ],
        "tip": "Each slide keeps its own drawing. The floating circle also "
               "has Undo, Redo and Clear for the slide you are on.",
    },
    {
        "key": "whiteboard",
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


def step(key):
    """The tutorial step with this key ("presentation", "whiteboard", ...)."""

    return next(s for s in STEPS if s["key"] == key)


# ==============================================================
# COLOURS
#
# The rail is brand navy and the content sheet is white, so the
# card stands clear of the soft-blue page behind it. Each tool
# also has its own accent (strong, soft wash, readable ink) used
# for its rail node, icon chips, numbers and tip.
# ==============================================================

NAVY = "#0E2F76"
SHEET = "#FFFFFF"

ACCENTS = {
    "camera": ("#22C3DE", "#E3F7FB", "#0D7C92"),
    "presentation": ("#5B6CF0", "#ECEEFE", "#3644B8"),
    "virtual_mouse": ("#1FB892", "#E2F7F1", "#0D7D62"),
    "annotation": ("#E5487F", "#FDE9F0", "#B02A5B"),
    "whiteboard": ("#F2A91C", "#FEF3DC", "#8F5E00"),
}


# ==============================================================
# BACKGROUND
# ==============================================================

# One open hand, in a 0..1 box: wrist, then each finger base -> tip.
# The same "constellation" as the GestureBoard logo.
_HAND_POINTS = {
    "wrist": (0.50, 0.98),
    "thumb": [(0.30, 0.80), (0.16, 0.66), (0.06, 0.55)],
    "index": [(0.36, 0.52), (0.33, 0.30), (0.31, 0.10)],
    "middle": [(0.50, 0.48), (0.50, 0.24), (0.50, 0.00)],
    "ring": [(0.63, 0.51), (0.66, 0.30), (0.68, 0.12)],
    "pinky": [(0.75, 0.58), (0.81, 0.42), (0.86, 0.28)],
}

_FINGERS = ("thumb", "index", "middle", "ring", "pinky")


def draw_hand(painter, rect, color, line_alpha=150):
    """Draw the landmark hand (dots joined by lines) inside `rect`."""

    size = min(rect.width(), rect.height())
    x0 = rect.center().x() - size / 2
    y0 = rect.center().y() - size / 2

    def pt(p):
        return QPointF(x0 + p[0] * size, y0 + p[1] * size)

    line = QColor(color)
    line.setAlpha(line_alpha)

    pen = QPen(line, max(1.5, size / 26))
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)

    wrist = pt(_HAND_POINTS["wrist"])
    bases = []

    for finger in _FINGERS:

        points = [pt(p) for p in _HAND_POINTS[finger]]

        painter.drawLine(wrist, points[0])

        for a, b in zip(points, points[1:]):
            painter.drawLine(a, b)

        bases.append(points[0])

    # Knuckle line across the palm
    for a, b in zip(bases[1:], bases[2:]):
        painter.drawLine(a, b)

    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(color))

    radius = max(2.0, size / 18)

    painter.drawEllipse(wrist, radius * 1.2, radius * 1.2)

    for finger in _FINGERS:
        for p in _HAND_POINTS[finger]:
            painter.drawEllipse(pt(p), radius, radius)


class ConstellationBackground(QWidget):

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setAttribute(Qt.WA_StyledBackground, True)

    def paintEvent(self, event):

        # Same soft-blue page, dot grid and corner hand as Saved Files.
        # The tutorial is styled for light mode only, so it stays light.
        from widgets import page_background

        page_background.paint_page_background(
            self, page_background.page_colors(dark=False)
        )


# ==============================================================
# RAIL STEP
#
# One stop on the navy rail. The stops are joined by a line, like
# the joints of a tracked finger: steps already seen are filled
# with their tool's accent, the current one is ringed, the rest
# are hollow.
# ==============================================================

class RailStep(QAbstractButton):

    NODE = 30

    def __init__(self, number, text, accent, parent=None):

        super().__init__(parent)

        self.number = number
        self.label = text
        self.accent = QColor(accent)

        # "done", "current" or "next"; first / last hide a line end.
        self.state = "next"
        self.first = False
        self.last = False

        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumHeight(56)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setAccessibleName(f"Step {number}: {text}")

        # The focus ring is for keyboard users, not after a click.
        self._key_focus = False

    def sizeHint(self):
        return QSize(220, 56)

    def set_state(self, state):
        self.state = state
        self.update()

    def focusInEvent(self, event):
        self._key_focus = event.reason() in (
            Qt.TabFocusReason, Qt.BacktabFocusReason
        )
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self._key_focus = False
        super().focusOutEvent(event)

    def enterEvent(self, event):
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(self.rect())
        cx = 8 + self.NODE / 2
        cy = rect.height() / 2

        # Hover / keyboard focus wash behind the whole row.
        focused = self.hasFocus() and self._key_focus

        if self.underMouse() or focused:
            wash = QColor(255, 255, 255, 22 if self.underMouse() else 14)
            painter.setPen(Qt.NoPen)
            painter.setBrush(wash)
            painter.drawRoundedRect(rect.adjusted(0, 3, 0, -3), 12, 12)

        if focused:
            painter.setPen(QPen(QColor(self.accent), 1.5))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect.adjusted(1, 4, -1, -4), 11, 11)

        # Line through the node to the neighbouring steps.
        seen = QColor(255, 255, 255, 120)
        unseen = QColor(255, 255, 255, 45)

        painter.setPen(QPen(seen if self.state != "next" else unseen, 2))
        if not self.first:
            painter.drawLine(QPointF(cx, 0), QPointF(cx, cy - self.NODE / 2))

        painter.setPen(QPen(seen if self.state == "done" else unseen, 2))
        if not self.last:
            painter.drawLine(
                QPointF(cx, cy + self.NODE / 2), QPointF(cx, rect.height())
            )

        # Node
        node = QRectF(cx - self.NODE / 2, cy - self.NODE / 2, self.NODE, self.NODE)

        if self.state == "current":
            halo = QColor(self.accent)
            halo.setAlpha(70)
            painter.setPen(Qt.NoPen)
            painter.setBrush(halo)
            painter.drawEllipse(node.adjusted(-5, -5, 5, 5))

        if self.state == "next":
            painter.setPen(QPen(QColor(255, 255, 255, 110), 1.5))
            painter.setBrush(Qt.NoBrush)
            number_color = QColor(255, 255, 255, 170)
        else:
            painter.setPen(Qt.NoPen)
            painter.setBrush(self.accent)
            number_color = QColor(NAVY)

        painter.drawEllipse(node)

        font = QFont(self.font())
        font.setPixelSize(13)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(number_color)
        painter.drawText(
            node, Qt.AlignCenter, "✓" if self.state == "done" else str(self.number)
        )

        # Label
        font.setPixelSize(15)
        font.setWeight(QFont.Bold if self.state == "current" else QFont.DemiBold)
        painter.setFont(font)
        painter.setPen(
            QColor("#FFFFFF") if self.state == "current"
            else QColor(255, 255, 255, 205) if self.state == "done"
            else QColor(255, 255, 255, 150)
        )

        text_rect = QRectF(cx + self.NODE / 2 + 14, 0, rect.width(), rect.height())
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self.label)


# ==============================================================
# HAND GLYPH  (the "21 points" stage of How it works)
# ==============================================================

class HandGlyph(QWidget):

    def __init__(self, color, parent=None):

        super().__init__(parent)

        self.color = QColor(color)
        self.setFixedSize(48, 48)

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        draw_hand(painter, QRectF(self.rect()).adjusted(8, 6, -8, -6), self.color)


# ==============================================================
# TUTORIAL PAGE
# ==============================================================

RAIL_WIDTH = 264

# Annotation page button symbols, drawn as text rather than emoji.
BUTTON_SYMBOLS = ("▶", "❚❚", "■")


class TutorialPage(ConstellationBackground):
    """Camera setup first, then an introduction to each tool."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setObjectName("tutorialPage")

        from widgets import page_background

        self.setStyleSheet(page_background.LAYER_RULE + f"""
            QLabel {{ background: transparent; color: {NAVY}; }}

            QFrame#tutorialCard {{
                background: {SHEET};
                border: 1px solid #C4D3E8;
                border-radius: 22px;
            }}

            /* ---------- step rail ---------- */
            QFrame#rail {{
                background: {NAVY};
                border: none;
                border-top-left-radius: 22px;
                border-bottom-left-radius: 22px;
            }}
            QLabel#railTitle {{ color: #FFFFFF; font-size: 20px; font-weight: 800; }}
            QLabel#railHint {{ color: #AFC2E4; font-size: 13px; }}
            QLabel#railFoot {{ color: #8FA6D2; font-size: 12px; }}

            /* ---------- content ---------- */
            QScrollArea#contentScroll, QWidget#contentPage {{ background: transparent; border: none; }}
            QScrollArea#contentScroll QScrollBar:vertical {{
                background: transparent; width: 8px; margin: 2px 0;
            }}
            QScrollArea#contentScroll QScrollBar::handle:vertical {{
                background: #D3DDEB; border-radius: 4px; min-height: 40px;
            }}
            QScrollArea#contentScroll QScrollBar::handle:vertical:hover {{ background: #AAC0E1; }}
            QScrollArea#contentScroll QScrollBar::add-line:vertical,
            QScrollArea#contentScroll QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollArea#contentScroll QScrollBar::add-page:vertical,
            QScrollArea#contentScroll QScrollBar::sub-page:vertical {{ background: transparent; }}

            QLabel#stepCount {{ font-size: 14px; font-weight: 700; }}
            QLabel#title {{ color: {NAVY}; font-size: 32px; font-weight: 800; }}
            QLabel#description {{ color: #46557A; font-size: 16px; }}
            QLabel#section {{ color: {NAVY}; font-size: 16px; font-weight: 700; }}

            QLabel#startNumber {{
                border-radius: 13px;
                font-size: 13px;
                font-weight: 800;
            }}
            QLabel#startText {{ color: #263B6A; font-size: 15px; }}

            QFrame#gestureTile {{
                background: #F7F9FC;
                border: 1px solid #E2E8F1;
                border-radius: 14px;
            }}
            QLabel#gestureIcon {{
                border-radius: 12px;
                font-family: "Segoe UI Emoji";
                font-size: 22px;
                font-weight: 700;
            }}
            QLabel#keyIcon {{
                border-radius: 12px;
                font-size: 12px;
                font-weight: 800;
            }}
            QLabel#gestureName {{ color: {NAVY}; font-size: 15px; font-weight: 700; }}
            QLabel#gestureAction {{ color: #4F5E82; font-size: 14px; }}

            QFrame#flowStage {{
                border-radius: 16px;
            }}
            QLabel#flowIcon {{ font-family: "Segoe UI Emoji"; font-size: 28px; }}
            QLabel#flowTitle {{ color: {NAVY}; font-size: 15px; font-weight: 800; }}
            QLabel#flowText {{ color: #4F5E82; font-size: 13px; }}
            QLabel#flowArrow {{ color: #AAB8CF; font-size: 26px; font-weight: 300; }}

            QFrame#tip {{ border: none; border-radius: 10px; }}
            QLabel#tipText {{ color: #263B6A; font-size: 14px; }}

            /* ---------- navigation ---------- */
            QPushButton {{
                background: {NAVY}; color: #F5FEFF; border: none; border-radius: 10px;
                padding: 12px 26px; min-width: 120px; font-size: 15px; font-weight: 700;
            }}
            QPushButton:hover {{ background: #1B4499; }}
            QPushButton#ghostButton {{
                background: transparent; color: #4F5E82; border: 1px solid #C4D3E8;
            }}
            QPushButton#ghostButton:hover {{ background: #EEF3FA; color: {NAVY}; }}
            QPushButton#ghostButton:disabled {{ color: #B8C6DC; border-color: #E2E8F1; }}
            QPushButton:focus {{ outline: none; border: 2px solid #22C3DE; }}

            QLabel#footer {{ color: #7F90B0; font-size: 12px; }}
        """)

        # ------------------------------------------------------
        # CARD
        # ------------------------------------------------------

        self.card = QFrame()
        self.card.setObjectName("tutorialCard")
        self.card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # A soft navy shadow lifts the card off the page.
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(14, 47, 118, 40))
        self.card.setGraphicsEffect(shadow)

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

        for index, item in enumerate(STEPS):
            self.stack.addWidget(self._build_step(index, item))

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
        rail.setFixedWidth(RAIL_WIDTH)

        layout = QVBoxLayout(rail)
        layout.setContentsMargins(20, 32, 20, 24)
        layout.setSpacing(0)

        title = QLabel("Getting started")
        title.setObjectName("railTitle")

        hint = QLabel("Set up your camera, then learn each tool. "
                      "Pick any step to jump to it.")
        hint.setObjectName("railHint")
        hint.setWordWrap(True)

        layout.addWidget(title)
        layout.addSpacing(6)
        layout.addWidget(hint)
        layout.addSpacing(24)

        self.rail_group = QButtonGroup(self)
        self.rail_group.setExclusive(True)

        for index, item in enumerate(STEPS):

            button = RailStep(index + 1, item["rail"], ACCENTS[item["key"]][0])
            button.first = index == 0
            button.last = index == len(STEPS) - 1
            button.clicked.connect(lambda _=False, i=index: self.goToPage(i))

            self.rail_group.addButton(button, index)
            layout.addWidget(button)

        layout.addStretch()

        foot = QLabel("To see this again, turn on Tutorial on next start in Settings.")
        foot.setObjectName("railFoot")
        foot.setWordWrap(True)
        layout.addWidget(foot)

        return rail

    def _build_step(self, index, item):

        strong, soft, ink = ACCENTS[item["key"]]

        page = QWidget()
        page.setObjectName("contentPage")

        # This tool's accent on its numbers, icon chips and tip.
        page.setStyleSheet(f"""
            QLabel#stepCount {{ color: {ink}; }}
            QLabel#startNumber {{ background: {soft}; color: {ink}; }}
            QLabel#gestureIcon, QLabel#keyIcon {{ background: {soft}; color: {ink}; }}
            QFrame#flowStage {{ background: {soft}; border: none; }}
            QFrame#tip {{ background: {soft}; border-left: 4px solid {strong}; }}
        """)

        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 12, 0)
        layout.setSpacing(10)

        count = QLabel(f"Step {index + 1} of {len(STEPS)}")
        count.setObjectName("stepCount")

        title = QLabel(item["title"])
        title.setObjectName("title")
        title.setWordWrap(True)

        description = QLabel(item["description"])
        description.setObjectName("description")
        description.setWordWrap(True)
        description.setMaximumWidth(720)

        layout.addWidget(count)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addSpacing(10)

        # How it works (camera step): webcam -> hand points -> action.
        if "flow" in item:
            layout.addWidget(self._section("How it works"))
            layout.addLayout(self._flow(item["flow"], strong))
            layout.addSpacing(12)

        # How to start (a real sequence, so it is numbered)
        layout.addWidget(self._section(item.get("start_title", "How to start")))

        for number, text in enumerate(item["start"], start=1):
            layout.addLayout(self._start_row(number, text))

        # Gesture groups
        for group_title, gestures in item["groups"]:

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
        layout.addWidget(self._tip(item["tip"]))
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

    def _flow(self, stages, color):

        row = QHBoxLayout()
        row.setSpacing(8)

        for i, (icon, title, text) in enumerate(stages):

            if i:
                arrow = QLabel("›")
                arrow.setObjectName("flowArrow")
                arrow.setAlignment(Qt.AlignCenter)
                row.addWidget(arrow)

            stage = QFrame()
            stage.setObjectName("flowStage")
            stage.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

            stage_layout = QVBoxLayout(stage)
            stage_layout.setContentsMargins(16, 14, 16, 16)
            stage_layout.setSpacing(6)

            if icon == "hand":
                glyph = HandGlyph(color)
            else:
                glyph = QLabel(icon)
                glyph.setObjectName("flowIcon")
                glyph.setFixedSize(48, 48)
                glyph.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            title_label = QLabel(title)
            title_label.setObjectName("flowTitle")
            title_label.setWordWrap(True)

            text_label = QLabel(text)
            text_label.setObjectName("flowText")
            text_label.setWordWrap(True)

            stage_layout.addWidget(glyph)
            stage_layout.addWidget(title_label)
            stage_layout.addWidget(text_label)
            stage_layout.addStretch()

            row.addWidget(stage, 1)

        return row

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

        # Keyboard keys ("Ctrl+Z", "P") and button symbols get a key
        # cap in the accent ink instead of a colour emoji.
        is_key = icon.isascii() or len(icon) > 2 or icon in BUTTON_SYMBOLS

        icon_label = QLabel(icon)
        icon_label.setObjectName("keyIcon" if is_key else "gestureIcon")

        if icon in BUTTON_SYMBOLS:
            icon_label.setStyleSheet("font-size: 20px;")
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
        content = min(self.card.maximumWidth(), self.width() - 80) - RAIL_WIDTH - 92

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

        # Each step opens at its top.
        self.stack.currentWidget().verticalScrollBar().setValue(0)

        for i, button in enumerate(self.rail_group.buttons()):
            button.set_state(
                "done" if i < index else "current" if i == index else "next"
            )

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
