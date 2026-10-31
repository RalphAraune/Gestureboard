"""Phone camera tutorial, for people with no webcam.

    PhoneTutorialDialog   one step per page (Back / Next / Skip), in the
                          same look as the main tutorial: navy step
                          rail, white sheet, the camera step's cyan.
    PhoneCameraPrompt     "No camera found" message with
                          Set up phone camera / Skip / Don't show again.
    maybe_prompt_phone_camera(camera_setup)
                          shows the prompt when Camera Setup opens and
                          no real webcam was found.
    open_phone_tutorial(camera_setup)
                          the tutorial; finishing it opens the phone's
                          QR code in Camera Setup.

Set GESTUREBOARD_NO_WEBCAM=1 to test the prompt on a computer that
has a webcam.
"""

import os

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import settings.preferences as prefs
from core.phone_camera import PHONE_CAMERA, PORT
from gui.tutorial import ACCENTS, NAVY, RAIL_WIDTH, SHEET, RailStep, draw_hand
from settings import theme as app_theme
from widgets import page_background


# Config key set by "Don't show again".
PROMPT_HIDDEN_KEY = "phone_camera_prompt_hidden"

# Address used in the pictures (the real one is shown in the QR dialog).
SAMPLE_URL = f"https://192.168.1.5:{PORT}/"

CYAN, CYAN_SOFT, CYAN_INK = ACCENTS["camera"]


# ==============================================================
# PICTURES
# Small mock-ups of what the user will see, so each step is
# recognisable on the phone.
# ==============================================================

def _card(object_name="mock"):
    frame = QFrame()
    frame.setObjectName(object_name)
    return frame


def _label(text, object_name, wrap=True):
    label = QLabel(text)
    label.setObjectName(object_name)
    label.setWordWrap(wrap)
    return label


def picture_connections():
    """Three ways to connect, side by side."""

    grid = QGridLayout()
    grid.setHorizontalSpacing(12)
    grid.setVerticalSpacing(12)

    options = [
        ("📶", "Same Wi-Fi", "Connect the phone and the laptop to the same Wi-Fi.",
         "Recommended, fastest"),
        ("📱", "Phone hotspot", "Turn on the hotspot on your phone, then connect the laptop to it.",
         None),
        ("🔌", "USB cable", "Plug in the phone and turn on USB tethering in its settings.",
         "May have a little delay"),
    ]

    for column, (icon, name, text, tag) in enumerate(options):

        card = _card("option")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(6)

        icon_label = QLabel(icon)
        icon_label.setObjectName("optionIcon")
        icon_label.setFixedSize(46, 46)
        icon_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(icon_label)
        layout.addWidget(_label(name, "optionName"))
        layout.addWidget(_label(text, "optionText"))

        if tag:
            tag_label = QLabel(tag)
            tag_label.setObjectName("tag")
            layout.addWidget(tag_label, 0, Qt.AlignLeft)

        layout.addStretch()
        grid.addWidget(card, 0, column)
        grid.setColumnStretch(column, 1)

    holder = QWidget()
    holder.setLayout(grid)
    return holder


def _qr(size=170):
    from gui.phone_camera_dialog import QrCode

    qr = QrCode()
    qr.setFixedSize(size, size)
    qr.set_text(SAMPLE_URL)
    return qr


def picture_choose_phone():
    """The camera list with Phone Camera picked, and the QR it opens."""

    row = QHBoxLayout()
    row.setSpacing(18)

    card = _card()
    layout = QVBoxLayout(card)
    layout.setContentsMargins(18, 16, 18, 18)
    layout.setSpacing(8)

    layout.addWidget(_label("Camera Setup", "mockCaption"))

    combo = QLabel("Phone Camera     ▾")
    combo.setObjectName("mockField")
    layout.addWidget(combo)

    test = QLabel("Test camera")
    test.setObjectName("mockButton")
    test.setAlignment(Qt.AlignCenter)
    layout.addWidget(test)
    layout.addStretch()

    arrow = QLabel("›")
    arrow.setObjectName("arrow")

    row.addWidget(card, 1)
    row.addWidget(arrow)
    row.addWidget(_qr(150))
    row.addStretch()

    holder = QWidget()
    holder.setLayout(row)
    return holder


def picture_scan():
    """The QR code with the address under it."""

    column = QVBoxLayout()
    column.setSpacing(8)
    column.addWidget(_qr(), 0, Qt.AlignLeft)

    url = QLabel(SAMPLE_URL)
    url.setObjectName("mockUrl")
    column.addWidget(url, 0, Qt.AlignLeft)

    holder = QWidget()
    holder.setLayout(column)
    return holder


def picture_warning():
    """The browser's "not private" page, with the two taps marked."""

    card = _card("browser")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(22, 18, 22, 20)
    layout.setSpacing(10)

    layout.addWidget(_label("⚠", "warningIcon", wrap=False))
    layout.addWidget(_label("Your connection is not private", "warningTitle"))
    layout.addWidget(_label(
        "Attackers might be trying to steal your information from 192.168.1.5.",
        "warningText",
    ))

    buttons = QHBoxLayout()
    buttons.setSpacing(10)

    advanced = QLabel("1  Advanced")
    advanced.setObjectName("tapTarget")
    back = QLabel("Back to safety")
    back.setObjectName("mockButtonDim")

    buttons.addWidget(advanced)
    buttons.addStretch()
    buttons.addWidget(back)
    layout.addLayout(buttons)

    proceed = QLabel("2  Proceed to 192.168.1.5 (unsafe)")
    proceed.setObjectName("tapTarget")
    layout.addWidget(proceed, 0, Qt.AlignLeft)

    return card


def picture_permission():
    """The browser asking to use the camera."""

    card = _card("browser")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(22, 18, 22, 20)
    layout.setSpacing(12)

    layout.addWidget(_label("192.168.1.5:8443 wants to", "warningText"))
    layout.addWidget(_label("📷  Use your camera", "warningTitle"))

    buttons = QHBoxLayout()
    buttons.setSpacing(10)
    buttons.addStretch()

    block = QLabel("Block")
    block.setObjectName("mockButtonDim")
    allow = QLabel("Allow")
    allow.setObjectName("tapTarget")

    buttons.addWidget(block)
    buttons.addWidget(allow)
    layout.addLayout(buttons)

    return card


def picture_keep_running():
    """Three things that keep the video going."""

    grid = QGridLayout()
    grid.setHorizontalSpacing(12)

    items = [
        ("🔆", "Screen on", "Don't lock the phone"),
        ("📌", "Page open", "Don't switch to another app"),
        ("🔋", "Charging", "Video uses battery quickly"),
    ]

    for column, (icon, name, text) in enumerate(items):

        card = _card("option")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        icon_label = QLabel(icon)
        icon_label.setObjectName("optionIcon")
        icon_label.setFixedSize(42, 42)
        icon_label.setAlignment(Qt.AlignCenter)

        text_box = QVBoxLayout()
        text_box.setSpacing(1)
        text_box.addWidget(_label(name, "optionName"))
        text_box.addWidget(_label(text, "optionText"))

        layout.addWidget(icon_label, 0, Qt.AlignTop)
        layout.addLayout(text_box, 1)

        grid.addWidget(card, 0, column)
        grid.setColumnStretch(column, 1)

    holder = QWidget()
    holder.setLayout(grid)
    return holder


class PhoneFrame(QWidget):
    """A phone standing up, with a tracked hand in its picture."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(150, 230)

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        body = QRectF(20, 6, 110, 196)
        painter.setPen(QPen(QColor(NAVY), 4))
        painter.setBrush(QColor("#F4F8FC"))
        painter.drawRoundedRect(body, 18, 18)

        screen = body.adjusted(9, 16, -9, -16)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(CYAN_SOFT))
        painter.drawRoundedRect(screen, 8, 8)

        draw_hand(painter, screen.adjusted(14, 26, -14, -26), QColor(CYAN_INK))

        # Stand
        painter.setPen(QPen(QColor(NAVY), 4, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(45, 222, 105, 222)
        painter.drawLine(75, 202, 75, 222)


def picture_placement():
    row = QHBoxLayout()
    row.setSpacing(20)
    row.addWidget(PhoneFrame())

    checks = QVBoxLayout()
    checks.setSpacing(10)
    for text in (
        "Steady: on a stand or leaning on something",
        "Facing you, about an arm's length away",
        "Both hands fit in the picture",
        "Good light on your hands, not behind you",
    ):
        checks.addWidget(_label("✓   " + text, "check"))
    checks.addStretch()

    row.addLayout(checks, 1)

    holder = QWidget()
    holder.setLayout(row)
    return holder


def picture_troubleshooting():
    """Problem -> what to do, one card each."""

    grid = QGridLayout()
    grid.setHorizontalSpacing(12)
    grid.setVerticalSpacing(12)

    problems = [
        ("The phone can't open the page", [
            "Check both are on the same Wi-Fi, hotspot or USB tethering.",
            "Allow GestureBoard in Windows Firewall (Private networks).",
            "Try another address from the Network list.",
        ]),
        ("Camera permission was denied", [
            "Allow the camera in the browser's site settings.",
            "Then reload the page.",
        ]),
        ("The video is laggy", [
            "Use Wi-Fi or the hotspot instead of USB.",
            "Move closer to the router.",
        ]),
        ("It disconnected", [
            "Open the page again, or scan the QR code again.",
        ]),
    ]

    for i, (title, fixes) in enumerate(problems):

        card = _card("option")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(6)

        layout.addWidget(_label(title, "optionName"))

        for fix in fixes:
            layout.addWidget(_label("•  " + fix, "optionText"))

        layout.addStretch()
        grid.addWidget(card, i // 2, i % 2)

    for column in range(2):
        grid.setColumnStretch(column, 1)

    holder = QWidget()
    holder.setLayout(grid)
    return holder


# ==============================================================
# CONTENT
# ==============================================================

PAGES = [
    {
        "rail": "Choose a connection",
        "title": "Choose how to connect",
        "body": [
            "Your phone and this computer need to be on the same network. "
            "None of these need the internet.",
        ],
        "picture": picture_connections,
    },
    {
        "rail": "Pick Phone Camera",
        "title": "Pick Phone Camera in GestureBoard",
        "body": [
            "In Camera Setup, choose Phone Camera from the camera list and "
            "press Test camera. A QR code appears.",
        ],
        "picture": picture_choose_phone,
    },
    {
        "rail": "Scan the QR code",
        "title": "Scan the QR code with your phone",
        "body": [
            "Point the phone's camera at the QR code and tap the link. It "
            "opens in the browser (Chrome or Safari).",
            "Can't scan it? Type the address shown under the QR code into "
            "the phone's browser.",
        ],
        "picture": picture_scan,
    },
    {
        "rail": "Security warning",
        "title": "Get past the security warning",
        "body": [
            "The first time, the browser says \"Your connection is not "
            "private\". Tap Advanced, then Proceed.",
            "This is safe: the page comes from your own laptop, not the "
            "internet. On iPhone, tap Show Details, then visit this website.",
        ],
        "picture": picture_warning,
    },
    {
        "rail": "Allow the camera",
        "title": "Allow the camera",
        "body": [
            "When the browser asks to use your camera, tap Allow.",
        ],
        "picture": picture_permission,
    },
    {
        "rail": "Keep it running",
        "title": "Keep the page open",
        "body": [
            "Don't lock the screen or switch apps while you use GestureBoard. "
            "Keep the phone charging if you can.",
        ],
        "picture": picture_keep_running,
    },
    {
        "rail": "Place the phone",
        "title": "Place the phone facing you",
        "body": [
            "Stand or lean the phone so it stays still, with your hands in "
            "the picture and good light on them.",
        ],
        "picture": picture_placement,
    },
    {
        "rail": "Troubleshooting",
        "title": "If something goes wrong",
        "body": [],
        "picture": picture_troubleshooting,
    },
]


# ==============================================================
# TUTORIAL DIALOG
# ==============================================================

class PhoneTutorialDialog(QDialog):
    """Accepted when the user finishes with "Set up phone camera"."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Use your phone as a camera")
        self.setModal(True)
        self.resize(1060, 700)
        self.setMinimumSize(860, 600)

        self.setStyleSheet(STYLE)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_rail())

        right = QVBoxLayout()
        right.setContentsMargins(40, 32, 40, 26)
        right.setSpacing(18)

        self.stack = QStackedWidget()

        for index, page in enumerate(PAGES):
            self.stack.addWidget(self._build_page(index, page))

        right.addWidget(self.stack, 1)
        right.addLayout(self._build_navigation())

        root.addLayout(right, 1)

        self.go_to(0)

    # ----------------------------------------------------------

    def _build_rail(self):

        rail = QFrame()
        rail.setObjectName("rail")
        rail.setFixedWidth(RAIL_WIDTH)

        layout = QVBoxLayout(rail)
        layout.setContentsMargins(20, 32, 20, 24)
        layout.setSpacing(0)

        title = QLabel("Phone camera")
        title.setObjectName("railTitle")

        hint = QLabel("No webcam? Your phone can be the camera. "
                      "No app or internet needed.")
        hint.setObjectName("railHint")
        hint.setWordWrap(True)

        layout.addWidget(title)
        layout.addSpacing(6)
        layout.addWidget(hint)
        layout.addSpacing(22)

        self.rail_group = QButtonGroup(self)
        self.rail_group.setExclusive(True)

        for index, page in enumerate(PAGES):

            button = RailStep(index + 1, page["rail"], CYAN)
            button.setMinimumHeight(50)
            button.first = index == 0
            button.last = index == len(PAGES) - 1
            button.clicked.connect(lambda _=False, i=index: self.go_to(i))

            self.rail_group.addButton(button, index)
            layout.addWidget(button)

        layout.addStretch()

        return rail

    def _build_page(self, index, page):

        content = QWidget()
        content.setObjectName("contentPage")

        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 12, 0)
        layout.setSpacing(10)

        count = QLabel(
            "Troubleshooting" if index == len(PAGES) - 1
            else f"Step {index + 1} of {len(PAGES) - 1}"
        )
        count.setObjectName("stepCount")

        title = QLabel(page["title"])
        title.setObjectName("title")
        title.setWordWrap(True)

        layout.addWidget(count)
        layout.addWidget(title)

        for paragraph in page["body"]:
            text = QLabel(paragraph)
            text.setObjectName("description")
            text.setWordWrap(True)
            text.setMaximumWidth(720)
            layout.addWidget(text)

        layout.addSpacing(14)
        layout.addWidget(page["picture"]())
        layout.addStretch()

        scroll = QScrollArea()
        scroll.setObjectName("contentScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(content)

        return scroll

    def _build_navigation(self):

        nav = QHBoxLayout()
        nav.setSpacing(10)

        self.back_button = QPushButton("Back")
        self.back_button.setObjectName("ghostButton")
        self.back_button.clicked.connect(lambda: self.go_to(self.stack.currentIndex() - 1))

        self.skip_button = QPushButton("Skip")
        self.skip_button.setObjectName("ghostButton")
        self.skip_button.clicked.connect(self.reject)

        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self._next)

        for button in (self.back_button, self.skip_button, self.next_button):
            button.setCursor(Qt.PointingHandCursor)

        nav.addWidget(self.back_button)
        nav.addStretch()
        nav.addWidget(self.skip_button)
        nav.addWidget(self.next_button)

        return nav

    # ----------------------------------------------------------

    def go_to(self, index):

        index = max(0, min(index, self.stack.count() - 1))

        self.stack.setCurrentIndex(index)
        self.stack.currentWidget().verticalScrollBar().setValue(0)

        for i, button in enumerate(self.rail_group.buttons()):
            button.set_state("done" if i < index else "current" if i == index else "next")

        self.rail_group.button(index).setChecked(True)

        last = index == self.stack.count() - 1

        self.back_button.setEnabled(index > 0)
        self.next_button.setText("Set up phone camera" if last else "Next")

    def _next(self):

        if self.stack.currentIndex() < self.stack.count() - 1:
            self.go_to(self.stack.currentIndex() + 1)
        else:
            self.accept()


# Same tokens as the main tutorial (gui/tutorial.py), light only.
STYLE = f"""
    QDialog {{ background: {SHEET}; }}
    QLabel {{ background: transparent; color: {NAVY}; }}

    QFrame#rail {{ background: {NAVY}; border: none; }}
    QLabel#railTitle {{ color: #FFFFFF; font-size: 20px; font-weight: 800; }}
    QLabel#railHint {{ color: #AFC2E4; font-size: 13px; }}

    QScrollArea#contentScroll, QWidget#contentPage {{ background: transparent; border: none; }}
    QScrollArea#contentScroll > QWidget > QWidget {{ background: transparent; }}
    QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px 0; }}
    QScrollBar::handle:vertical {{ background: #D3DDEB; border-radius: 4px; min-height: 40px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

    QLabel#stepCount {{ color: {CYAN_INK}; font-size: 14px; font-weight: 700; }}
    QLabel#title {{ font-size: 30px; font-weight: 800; }}
    QLabel#description {{ color: #46557A; font-size: 16px; }}

    QFrame#option {{ background: #F7F9FC; border: 1px solid #E2E8F1; border-radius: 14px; }}
    QLabel#optionIcon {{
        background: {CYAN_SOFT}; border-radius: 12px;
        font-family: "Segoe UI Emoji"; font-size: 22px;
    }}
    QLabel#optionName {{ font-size: 16px; font-weight: 700; }}
    QLabel#optionText {{ color: #4F5E82; font-size: 14px; }}
    QLabel#tag {{
        background: {CYAN_SOFT}; color: {CYAN_INK};
        border-radius: 8px; padding: 3px 9px; font-size: 13px; font-weight: 700;
    }}
    QLabel#check {{ color: #263B6A; font-size: 15px; }}

    QFrame#mock {{ background: #F7F9FC; border: 1px solid #E2E8F1; border-radius: 14px; }}
    QLabel#mockCaption {{ color: #4F5E82; font-size: 13px; font-weight: 700; }}
    QLabel#mockField {{
        background: #FFFFFF; border: 2px solid {CYAN}; border-radius: 9px;
        padding: 8px 12px; font-size: 15px; font-weight: 600;
    }}
    QLabel#mockButton {{
        background: {NAVY}; color: #F5FEFF; border-radius: 9px;
        padding: 9px; font-size: 15px; font-weight: 700;
    }}
    QLabel#mockUrl {{ font-size: 15px; font-weight: 700; }}
    QLabel#arrow {{ color: #AAB8CF; font-size: 34px; }}

    QFrame#browser {{
        background: #FFFFFF; border: 1px solid #D6DEEA; border-radius: 16px;
        max-width: 560px;
    }}
    QLabel#warningIcon {{ color: #C5372C; font-size: 28px; }}
    QLabel#warningTitle {{ color: #1F2937; font-size: 19px; font-weight: 700; }}
    QLabel#warningText {{ color: #4B5563; font-size: 14px; }}
    QLabel#tapTarget {{
        background: {CYAN_SOFT}; color: {CYAN_INK};
        border: 2px solid {CYAN}; border-radius: 9px;
        padding: 7px 14px; font-size: 15px; font-weight: 800;
    }}
    QLabel#mockButtonDim {{
        background: #EEF2F7; color: #6B7280; border-radius: 9px;
        padding: 9px 14px; font-size: 14px; font-weight: 600;
    }}

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
    QPushButton:focus {{ outline: none; border: 2px solid {CYAN}; }}
"""


# ==============================================================
# "NO CAMERA FOUND" PROMPT
# ==============================================================

class PhoneCameraPrompt(QDialog):
    """Accepted for "Set up phone camera"; dont_show_again() tells if
    the box was ticked."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("No camera found")
        self.setModal(True)
        self.setFixedWidth(500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 22)
        layout.setSpacing(12)

        icon = QLabel("📱")
        icon.setObjectName("promptIcon")
        icon.setFixedSize(56, 56)
        icon.setAlignment(Qt.AlignCenter)

        title = QLabel("No camera found")
        title.setObjectName("promptTitle")

        text = QLabel(
            "You can use your phone as a camera. It takes about a minute, "
            "and needs no app and no internet."
        )
        text.setObjectName("promptText")
        text.setWordWrap(True)

        self.dont_show = QCheckBox("Don't show this again")
        self.dont_show.setCursor(Qt.PointingHandCursor)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)

        skip = QPushButton("Skip")
        skip.setObjectName("ghost")
        skip.clicked.connect(self.reject)

        setup = QPushButton("Set up phone camera")
        setup.setObjectName("primary")
        setup.setDefault(True)
        setup.clicked.connect(self.accept)

        for button in (skip, setup):
            button.setCursor(Qt.PointingHandCursor)

        buttons.addWidget(self.dont_show)
        buttons.addStretch()
        buttons.addWidget(skip)
        buttons.addWidget(setup)

        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(text)
        layout.addSpacing(8)
        layout.addLayout(buttons)

        self._apply_style()

    def dont_show_again(self):
        return self.dont_show.isChecked()

    def _apply_style(self):

        c = page_background.page_colors()
        dark = app_theme.is_dark()

        sheet = "#17314F" if dark else "#FFFFFF"
        field = "#0F2038" if dark else "#F4F7FB"
        field_border = "#335B89" if dark else "#B9CCE4"
        hover = "#21416A" if dark else "#EAF1F9"
        icon_bg = "#21416A" if dark else CYAN_SOFT

        self.setStyleSheet(f"""
            QDialog {{ background: {sheet}; }}
            QLabel, QCheckBox {{ background: transparent; color: {c['text']}; }}
            QLabel#promptIcon {{
                background: {icon_bg}; border-radius: 16px;
                font-family: "Segoe UI Emoji"; font-size: 28px;
            }}
            QLabel#promptTitle {{ font-size: 22px; font-weight: 800; }}
            QLabel#promptText {{ font-size: 15px; color: {c['text_secondary']}; }}
            QCheckBox {{ font-size: 14px; color: {c['text_secondary']}; }}
            QPushButton {{
                border-radius: 10px; padding: 10px 18px;
                font-size: 15px; font-weight: 700;
            }}
            QPushButton#primary {{ background: {c['primary']}; color: {c['primary_text']}; border: none; }}
            QPushButton#primary:hover {{ background: {c['sidebar_hover']}; color: {c['sidebar_text']}; }}
            QPushButton#ghost {{ background: {field}; color: {c['text']}; border: 1px solid {field_border}; }}
            QPushButton#ghost:hover {{ background: {hover}; }}
            QPushButton:focus {{ outline: none; border: 2px solid {c['accent'] if dark else c['sidebar_hover']}; }}
        """)


# ==============================================================
# ENTRY POINTS (used by Camera Setup)
# ==============================================================

_prompted_this_session = False


def has_real_webcam(cameras):
    """True when `cameras` [(index, name), ...] has a real webcam.

    The phone entry and virtual cameras (OBS Virtual Camera and the
    like, which show nothing on their own) do not count.
    """

    if os.environ.get("GESTUREBOARD_NO_WEBCAM") == "1":
        return False

    return any(
        index is not None
        and index != PHONE_CAMERA
        and "virtual" not in str(name).lower()
        for index, name in cameras
    )


def open_phone_tutorial(camera_setup):
    """Show the tutorial; finishing it opens the phone's QR code."""

    dialog = PhoneTutorialDialog(camera_setup)

    if dialog.exec_() == QDialog.Accepted and hasattr(camera_setup, "use_phone_camera"):
        camera_setup.use_phone_camera()


def maybe_prompt_phone_camera(camera_setup, cameras):
    """"No camera found" prompt, once per run, unless turned off."""

    global _prompted_this_session

    if _prompted_this_session or not camera_setup.isVisible():
        return

    if prefs.load().get(PROMPT_HIDDEN_KEY) or has_real_webcam(cameras):
        return

    _prompted_this_session = True

    prompt = PhoneCameraPrompt(camera_setup)
    accepted = prompt.exec_() == QDialog.Accepted

    if prompt.dont_show_again():
        prefs.save({PROMPT_HIDDEN_KEY: True})

    if accepted:
        open_phone_tutorial(camera_setup)
