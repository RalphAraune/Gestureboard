from pathlib import Path
import os

from PyQt5.QtCore import Qt, QRectF, QSize, QVariantAnimation
from PyQt5.QtGui import QColor, QIcon, QPainter, QPen
from PyQt5.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import settings.preferences as prefs
from settings import theme as app_theme
from widgets import page_background
from widgets.sidebar import nav_pixmap, sidebar_logo


# Section key, rail label, icon, one-line description under the title.
SECTIONS = [
    ("general", "General", "settings",
     "How GestureBoard looks."),
    ("camera", "Camera", "camera",
     "Which webcam GestureBoard watches, and how it captures."),
    ("gesture", "Gestures", "hand",
     "How readily your hand movements turn into actions."),
    ("presentation", "Presentation", "presentation",
     "Defaults for gesture-controlled slideshows."),
    ("storage", "Storage", "folder",
     "What GestureBoard keeps after you close a board."),
    ("about", "About", "info",
     "Version and the libraries behind hand tracking."),
]

# Saved in settings/config.json next to the theme and camera choice.
DEFAULTS = {
    "camera_resolution": "1280 × 720",
    "camera_fps": "30 FPS",
    "camera_preview": True,
    "gesture_sensitivity": 70,
    "cursor_sensitivity": 50,
    "click_delay_ms": 300,
    "presentation_mode": "Auto detect",
    "presentation_fullscreen": True,
    "save_annotations": True,
    "save_whiteboards": True,
}

CONTENT_MAX_WIDTH = 820


def settings_colors():
    """Shared page surfaces plus the tones used by fields and switches."""

    c = page_background.page_colors()

    if app_theme.is_dark():
        c.update(field=c["input_bg"], knob="#E6EEF8")
    else:
        c.update(field="#F5F9FD", knob="#FFFFFF")

    return c


# ==============================================================
# TOGGLE SWITCH
# A real on/off switch; the knob slides when it changes.
# ==============================================================

class ToggleSwitch(QAbstractButton):

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)

        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(46, 26)

        self._on = QColor("#0E2F76")
        self._off = QColor("#AAC0E1")
        self._knob = QColor("#FFFFFF")
        self._focus = QColor("#0E2F76")

        self._offset = 1.0 if checked else 0.0

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(140)
        self._anim.valueChanged.connect(self._set_offset)

        self.toggled.connect(self._animate)

    def set_colors(self, on, off, knob, focus):
        self._on, self._off = QColor(on), QColor(off)
        self._knob, self._focus = QColor(knob), QColor(focus)
        self.update()

    def sizeHint(self):
        return QSize(46, 26)

    def _set_offset(self, value):
        self._offset = value
        self.update()

    def _animate(self, checked):
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        t = self._offset
        track = QColor(
            int(self._off.red() + (self._on.red() - self._off.red()) * t),
            int(self._off.green() + (self._on.green() - self._off.green()) * t),
            int(self._off.blue() + (self._on.blue() - self._off.blue()) * t),
        )

        rect = QRectF(1, 1, self.width() - 2, self.height() - 2)

        if self.hasFocus():
            painter.setPen(QPen(self._focus, 2))
        else:
            painter.setPen(Qt.NoPen)

        painter.setBrush(track)
        painter.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)

        knob = rect.height() - 6
        x = rect.left() + 3 + (rect.width() - knob - 6) * t

        painter.setPen(Qt.NoPen)
        painter.setBrush(self._knob)
        painter.drawEllipse(QRectF(x, rect.top() + 3, knob, knob))

        painter.end()


# ==============================================================
# SETTINGS PAGE
# ==============================================================

class SettingsPage(QWidget):
    """
    GestureBoard Settings Page

    Designed to work with:
        MainWindow(self)

    MainWindow can also call:
        settings.setActiveCamera(index, name)
    """

    def __init__(self, main_window=None):
        super().__init__(main_window)

        self.main_window = main_window

        self.active_camera_index = None
        self.active_camera_name = "Default Webcam"

        self.values = {**DEFAULTS, **{
            k: v for k, v in prefs.load().items() if k in DEFAULTS
        }}

        self.toggles = []
        self.rail_buttons = {}
        self.section_icons = {}

        self.setObjectName("settingsPage")

        self.setup_ui()

        page_background.clear_layers(self)

        self.apply_theme()

        # Virtual Mouse is created before Settings, so the saved cursor
        # sensitivity can be handed to it straight away.
        self._push_cursor_sensitivity(self.values["cursor_sensitivity"])

        self.show_section("general")

    # ==========================================================
    # PREFERENCES
    # ==========================================================

    def _set_value(self, key, value):

        self.values[key] = value
        prefs.save({key: value})

    # ==========================================================
    # LAYOUT
    # ==========================================================

    def setup_ui(self):

        root = QVBoxLayout(self)
        root.setContentsMargins(36, 28, 36, 28)
        root.setSpacing(0)

        title = QLabel("Settings")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        subtitle = QLabel("Choose how GestureBoard looks, sees and responds.")
        subtitle.setObjectName("pageSubtitle")
        root.addWidget(subtitle)

        root.addSpacing(22)

        body = QHBoxLayout()
        body.setSpacing(24)
        root.addLayout(body, 1)

        body.addWidget(self._build_rail(), 0, Qt.AlignTop)

        scroll = QScrollArea()
        scroll.setObjectName("settingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        holder = QWidget()
        holder_layout = QVBoxLayout(holder)
        holder_layout.setContentsMargins(0, 0, 8, 0)
        holder_layout.setSpacing(0)

        self.stack = QStackedWidget()
        self.stack.setMaximumWidth(CONTENT_MAX_WIDTH)

        self.section_pages = {}

        for key, label, icon, text in SECTIONS:
            page = self._build_section(key, label, icon, text)
            self.section_pages[key] = page
            self.stack.addWidget(page)

        holder_layout.addWidget(self.stack, 0, Qt.AlignTop | Qt.AlignLeft)
        holder_layout.addStretch()

        scroll.setWidget(holder)
        body.addWidget(scroll, 1)

    # ----------------------------------------------------------

    def _build_rail(self):

        rail = QFrame()
        rail.setObjectName("rail")
        rail.setFixedWidth(220)

        layout = QVBoxLayout(rail)
        layout.setContentsMargins(10, 10, 10, 14)
        layout.setSpacing(4)

        self.rail_group = QButtonGroup(self)
        self.rail_group.setExclusive(True)

        for key, label, icon, _text in SECTIONS:

            button = QPushButton(label)
            button.setObjectName("railItem")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setIconSize(QSize(20, 20))
            button.clicked.connect(
                lambda checked=False, k=key: self.show_section(k)
            )

            self.rail_group.addButton(button)
            self.rail_buttons[key] = (button, icon)
            layout.addWidget(button)

        layout.addSpacing(14)

        note = QLabel("Changes save automatically.")
        note.setObjectName("railNote")
        note.setWordWrap(True)
        layout.addWidget(note)

        return rail

    # ----------------------------------------------------------

    def _build_section(self, key, label, icon, text):

        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        # Header: icon tile, title, one line of description
        header = QHBoxLayout()
        header.setSpacing(14)

        tile = QLabel()
        tile.setObjectName("sectionIcon")
        tile.setFixedSize(48, 48)
        tile.setAlignment(Qt.AlignCenter)
        self.section_icons[key] = (tile, icon)
        header.addWidget(tile, 0, Qt.AlignTop)

        heading = QVBoxLayout()
        heading.setSpacing(2)

        title = QLabel(label)
        title.setObjectName("sectionTitle")
        heading.addWidget(title)

        description = QLabel(text)
        description.setObjectName("sectionText")
        description.setWordWrap(True)
        heading.addWidget(description)

        header.addLayout(heading, 1)
        layout.addLayout(header)

        getattr(self, f"_fill_{key}")(layout)

        layout.addStretch()

        return page

    # ==========================================================
    # BUILDING BLOCKS
    # ==========================================================

    def _group(self, parent_layout):

        group = QFrame()
        group.setObjectName("group")

        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(0)

        parent_layout.addWidget(group)

        return layout

    def _row(self, group_layout, label, hint, control):

        if group_layout.count():
            divider = QFrame()
            divider.setObjectName("rowDivider")
            divider.setFixedHeight(1)
            group_layout.addWidget(divider)

        row = QWidget()

        layout = QHBoxLayout(row)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(24)

        text_box = QWidget()
        text_box.setMinimumWidth(280)
        text = QVBoxLayout(text_box)
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(3)

        name = QLabel(label)
        name.setObjectName("rowLabel")
        text.addWidget(name)

        hint_label = None

        if hint:
            hint_label = QLabel(hint)
            hint_label.setObjectName("rowHint")
            hint_label.setWordWrap(True)
            text.addWidget(hint_label)

        layout.addWidget(text_box, 1)

        if isinstance(control, QWidget):
            layout.addWidget(control, 0, Qt.AlignVCenter)
        elif control is not None:
            layout.addLayout(control)

        group_layout.addWidget(row)

        return hint_label

    def _combo(self, items, key=None, width=200):

        combo = QComboBox()
        combo.setFixedWidth(width)
        combo.setCursor(Qt.PointingHandCursor)
        combo.addItems(items)

        if key:
            found = combo.findText(self.values[key])
            if found >= 0:
                combo.setCurrentIndex(found)
            combo.currentTextChanged.connect(
                lambda text, k=key: self._set_value(k, text)
            )

        return combo

    def _toggle(self, key):

        toggle = ToggleSwitch(bool(self.values[key]))
        toggle.toggled.connect(lambda on, k=key: self._set_value(k, on))
        self.toggles.append(toggle)

        return toggle

    def _slider(self, key, minimum, maximum, step, unit, on_change=None):

        box = QHBoxLayout()
        box.setSpacing(12)

        slider = QSlider(Qt.Horizontal)
        slider.setFixedWidth(200)
        slider.setRange(minimum, maximum)
        slider.setSingleStep(step)
        slider.setPageStep(step * 2)
        slider.setCursor(Qt.PointingHandCursor)
        slider.setValue(int(self.values[key]))

        value = QLabel()
        value.setObjectName("rowValue")
        value.setFixedWidth(64)
        value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        def changed(v):
            if step > 1:
                v = round(v / step) * step
            value.setText(f"{v}{unit}")
            self._set_value(key, v)
            if on_change:
                on_change(v)

        slider.valueChanged.connect(changed)
        value.setText(f"{slider.value()}{unit}")

        box.addWidget(slider)
        box.addWidget(value)

        return box, slider

    def _button(self, text, callback, primary=False):

        button = QPushButton(text)
        button.setObjectName("primaryButton" if primary else "secondaryButton")
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(callback)

        return button

    # ==========================================================
    # SECTIONS
    # ==========================================================

    def _fill_general(self, layout):

        group = self._group(layout)

        self.theme_combo = self._combo(["Light", "Dark", "System Default"])
        self.theme_combo.setCurrentText(app_theme.current_name())
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)

        self._row(
            group, "Theme",
            "Switch between the light and dark look.",
            self.theme_combo,
        )

    def _fill_camera(self, layout):

        group = self._group(layout)

        picker = QHBoxLayout()
        picker.setSpacing(8)

        self.camera_combo = QComboBox()
        self.camera_combo.setFixedWidth(220)
        self.camera_combo.setCursor(Qt.PointingHandCursor)
        self.populate_camera_combo()
        self.camera_combo.currentIndexChanged.connect(self.on_camera_selected)
        picker.addWidget(self.camera_combo)

        refresh = self._button("Refresh", self.refresh_cameras)
        refresh.setToolTip("Look for cameras again")
        picker.addWidget(refresh)

        self._row(
            group, "Camera",
            "Used by every gesture feature.",
            picker,
        )

        self._row(
            group, "Resolution",
            "Higher is sharper but takes more processing.",
            self._combo(
                ["1280 × 720", "1920 × 1080", "640 × 480"],
                "camera_resolution",
            ),
        )

        self._row(
            group, "Frame rate",
            "Higher feels smoother if the camera supports it.",
            self._combo(["30 FPS", "60 FPS", "24 FPS"], "camera_fps"),
        )

        self._row(
            group, "Camera preview",
            "Show the live feed while you work.",
            self._toggle("camera_preview"),
        )

        group = self._group(layout)

        self._row(
            group, "Camera setup",
            "Test the camera and check that your hand is tracked.",
            self._button("Open camera setup", self._open_camera_setup, True),
        )

    def _fill_gesture(self, layout):

        group = self._group(layout)

        box, _ = self._slider("gesture_sensitivity", 0, 100, 1, "%")
        self._row(
            group, "Gesture sensitivity",
            "Higher reacts to smaller, quicker movements.",
            box,
        )

        box, self.cursor_slider = self._slider(
            "cursor_sensitivity", 10, 100, 1, "%",
            on_change=self._push_cursor_sensitivity,
        )
        self._row(
            group, "Cursor sensitivity",
            "How far the cursor moves for each hand movement. "
            "Matches the slider on the Virtual mouse page.",
            box,
        )

        box, _ = self._slider("click_delay_ms", 100, 1000, 50, " ms")
        self._row(
            group, "Click delay",
            "How long a closed hand is held before it counts as a click.",
            box,
        )

    def _fill_presentation(self, layout):

        group = self._group(layout)

        self._row(
            group, "File type",
            "Auto detect reads the type from the file you upload.",
            self._combo(["Auto detect", "Manual"], "presentation_mode"),
        )

        self._row(
            group, "Open full screen",
            "Start slideshows in full screen when you begin presenting.",
            self._toggle("presentation_fullscreen"),
        )

    def _fill_storage(self, layout):

        group = self._group(layout)

        self._row(
            group, "Save annotations",
            "Keep drawings made on top of slides.",
            self._toggle("save_annotations"),
        )

        self._row(
            group, "Save whiteboards",
            "Keep whiteboard pages to open again later.",
            self._toggle("save_whiteboards"),
        )

        group = self._group(layout)

        folder = Path(os.getcwd()) / "saved_files"

        hint = self._row(
            group, "Saved files folder",
            str(folder),
            self._button("Open saved files", self._open_saved_files),
        )
        hint.setTextInteractionFlags(Qt.TextSelectableByMouse)

    def _fill_about(self, layout):

        group = self._group(layout)

        card = QWidget()
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(18)

        self.about_logo = QLabel()
        self.about_logo.setFixedWidth(84)
        self.about_logo.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.about_logo, 0, Qt.AlignTop)

        text = QVBoxLayout()
        text.setSpacing(4)

        name = QLabel("GestureBoard")
        name.setObjectName("aboutName")
        text.addWidget(name)

        version = QLabel("Version 1.0")
        version.setObjectName("rowHint")
        text.addWidget(version)

        info = QLabel(
            "Control presentations, the mouse cursor and a whiteboard "
            "with your hand, using an ordinary webcam."
        )
        info.setObjectName("aboutText")
        info.setWordWrap(True)
        text.addSpacing(6)
        text.addWidget(info)

        card_layout.addLayout(text, 1)
        group.addWidget(card)

        group = self._group(layout)

        for label, value in self._library_versions():
            self._row(group, label, None, self._value_label(value))

    def _value_label(self, text):

        label = QLabel(text)
        label.setObjectName("rowValueText")
        return label

    @staticmethod
    def _library_versions():

        rows = []

        try:
            import cv2
            rows.append(("Camera capture", f"OpenCV {cv2.__version__}"))
        except Exception:
            rows.append(("Camera capture", "OpenCV not available"))

        try:
            import mediapipe
            rows.append(("Hand tracking", f"MediaPipe {mediapipe.__version__}"))
        except Exception:
            rows.append(("Hand tracking", "MediaPipe not available"))

        try:
            from PyQt5.QtCore import PYQT_VERSION_STR
            rows.append(("Interface", f"PyQt {PYQT_VERSION_STR}"))
        except Exception:
            pass

        return rows

    # ==========================================================
    # NAVIGATION
    # ==========================================================

    def show_section(self, key):

        self.current_section = key

        button, _icon = self.rail_buttons[key]
        button.setChecked(True)

        self.stack.setCurrentWidget(self.section_pages[key])

        # Keep the stack only as tall as the visible section.
        for k, page in self.section_pages.items():
            page.setSizePolicy(
                QSizePolicy.Preferred,
                QSizePolicy.Preferred if k == key else QSizePolicy.Ignored,
            )
        self.stack.adjustSize()

    # Kept for older callers that used section names.
    def change_section(self, section):

        self.show_section(section.lower())

    def _open_camera_setup(self):

        if self.main_window is not None and hasattr(
            self.main_window, "showCameraSetup"
        ):
            self.main_window.showCameraSetup()

    def _open_saved_files(self):

        if self.main_window is not None and hasattr(
            self.main_window, "showSavedFiles"
        ):
            self.main_window.showSavedFiles()

    # ==========================================================
    # VIRTUAL MOUSE SYNC
    # ==========================================================

    def _virtual_mouse_slider(self):

        vm = getattr(self.main_window, "virtual_mouse", None)
        return getattr(vm, "sensitivity_slider", None)

    def _push_cursor_sensitivity(self, value):

        slider = self._virtual_mouse_slider()

        if slider is not None and slider.value() != value:
            slider.setValue(value)

    def showEvent(self, event):

        super().showEvent(event)

        # The Virtual Mouse slider may have moved since the last visit.
        slider = self._virtual_mouse_slider()

        if slider is not None and slider.value() != self.cursor_slider.value():
            self.cursor_slider.setValue(slider.value())

    # ==========================================================
    # THEME
    # ==========================================================

    def on_theme_changed(self, name):

        app_theme.set_theme(name)

        # Ask the main window to re-apply the theme across the app
        # (shell + pages). Fall back to re-theming just this page.
        if (
            self.main_window is not None
            and hasattr(self.main_window, "apply_theme")
        ):
            self.main_window.apply_theme()

        else:
            self.apply_theme()

    def apply_theme(self):
        """Restyle the page in the current theme (no rebuild needed)."""

        c = self.colors = settings_colors()
        dark = app_theme.is_dark()

        focus = c["accent"] if dark else c["sidebar_hover"]

        self.setStyleSheet(page_background.LAYER_RULE + f"""
            QWidget#settingsPage {{
                background: transparent;
            }}

            QLabel {{
                background: transparent;
                color: {c['text']};
            }}

            QLabel#pageTitle {{
                font-size: 28px;
                font-weight: 800;
            }}

            QLabel#pageSubtitle {{
                font-size: 14px;
                color: {c['text_secondary']};
                margin-top: 4px;
            }}

            /* ---------- Section rail ---------- */

            QFrame#rail {{
                background: {c['card']};
                border: 1px solid {c['card_border']};
                border-radius: 16px;
            }}

            QPushButton#railItem {{
                text-align: left;
                background: transparent;
                color: {c['text_secondary']};
                border: none;
                border-radius: 10px;
                padding: 10px 12px;
                font-size: 14px;
                font-weight: 600;
            }}

            QPushButton#railItem:hover {{
                background: {c['button_hover']};
                color: {c['text']};
            }}

            QPushButton#railItem:checked {{
                background: {c['primary']};
                color: {c['primary_text']};
            }}

            QPushButton#railItem:focus {{
                outline: none;
            }}

            QLabel#railNote {{
                color: {c['text_secondary']};
                font-size: 12px;
                padding: 0 12px;
            }}

            /* ---------- Section header ---------- */

            QLabel#sectionIcon {{
                background: {c['primary']};
                border-radius: 14px;
            }}

            QLabel#sectionTitle {{
                font-size: 22px;
                font-weight: 800;
            }}

            QLabel#sectionText {{
                font-size: 14px;
                color: {c['text_secondary']};
            }}

            /* ---------- Groups and rows ---------- */

            QFrame#group {{
                background: {c['card']};
                border: 1px solid {c['card_border']};
                border-radius: 14px;
            }}

            QFrame#rowDivider {{
                background: {c['card_border']};
                border: none;
                margin: 0 20px;
            }}

            QLabel#rowLabel {{
                font-size: 14px;
                font-weight: 700;
            }}

            QLabel#rowHint {{
                font-size: 12px;
                color: {c['text_secondary']};
            }}

            QLabel#rowValue {{
                font-size: 13px;
                font-weight: 700;
                color: {c['text']};
            }}

            QLabel#rowValueText {{
                font-size: 13px;
                font-weight: 600;
                color: {c['text_secondary']};
            }}

            QLabel#aboutName {{
                font-size: 18px;
                font-weight: 800;
            }}

            QLabel#aboutText {{
                font-size: 13px;
                color: {c['text_secondary']};
            }}

            /* ---------- Controls ---------- */

            QComboBox {{
                background: {c['field']};
                color: {c['text']};
                border: 1px solid {c['input_border']};
                border-radius: 9px;
                padding: 7px 12px;
                font-size: 13px;
                min-height: 22px;
            }}

            QComboBox:hover,
            QComboBox:focus {{
                border: 1px solid {c['primary']};
            }}

            QComboBox::drop-down {{
                border: none;
                width: 26px;
            }}

            QComboBox QAbstractItemView {{
                background: {c['field']};
                color: {c['text']};
                border: 1px solid {c['input_border']};
                selection-background-color: {c['button_hover']};
                selection-color: {c['text']};
                outline: none;
            }}

            QPushButton#secondaryButton {{
                background: {c['field']};
                color: {c['text']};
                border: 1px solid {c['input_border']};
                border-radius: 9px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
            }}

            QPushButton#secondaryButton:hover {{
                background: {c['button_hover']};
            }}

            QPushButton#primaryButton {{
                background: {c['primary']};
                color: {c['primary_text']};
                border: none;
                border-radius: 9px;
                padding: 9px 18px;
                font-size: 13px;
                font-weight: 700;
            }}

            QPushButton#primaryButton:hover {{
                background: {c['sidebar_hover']};
                color: {c['sidebar_text']};
            }}

            QPushButton#secondaryButton:focus,
            QPushButton#primaryButton:focus {{
                border: 2px solid {focus};
            }}

            QSlider::groove:horizontal {{
                height: 5px;
                background: {c['input_border']};
                border-radius: 2px;
            }}

            QSlider::sub-page:horizontal {{
                background: {c['primary']};
                border-radius: 2px;
            }}

            QSlider {{
                background: transparent;
                border: none;
                min-height: 22px;
            }}

            QSlider::handle:horizontal {{
                width: 14px;
                height: 14px;
                margin: -6px 0;
                background: {c['knob']};
                border: 2px solid {c['primary']};
                border-radius: 9px;
            }}

            QSlider::handle:horizontal:hover {{
                border: 2px solid {focus};
            }}

            /* ---------- Scrolling ---------- */

            QScrollArea#settingsScroll QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 0;
            }}

            QScrollArea#settingsScroll QScrollBar::handle:vertical {{
                background: {c['input_border']};
                border-radius: 4px;
                min-height: 30px;
            }}

            QScrollArea#settingsScroll QScrollBar::add-line:vertical,
            QScrollArea#settingsScroll QScrollBar::sub-line:vertical,
            QScrollArea#settingsScroll QScrollBar::add-page:vertical,
            QScrollArea#settingsScroll QScrollBar::sub-page:vertical {{
                background: transparent;
                height: 0;
            }}
        """)

        # Rail icons: muted when idle, light on the selected item.
        for button, icon_name in self.rail_buttons.values():
            icon = QIcon()
            icon.addPixmap(
                nav_pixmap(icon_name, c["text_secondary"], 20),
                QIcon.Normal, QIcon.Off,
            )
            icon.addPixmap(
                nav_pixmap(icon_name, c["primary_text"], 20),
                QIcon.Normal, QIcon.On,
            )
            button.setIcon(icon)

        for tile, icon_name in self.section_icons.values():
            tile.setPixmap(nav_pixmap(icon_name, c["primary_text"], 26))

        for toggle in self.toggles:
            toggle.set_colors(c["primary"], c["input_border"], c["knob"], focus)

        self.about_logo.setPixmap(
            sidebar_logo(72, c["text"] if dark else None)
        )

        if hasattr(self, "theme_combo"):
            self.theme_combo.blockSignals(True)
            self.theme_combo.setCurrentText(app_theme.current_name())
            self.theme_combo.blockSignals(False)

        self.update()

    def paintEvent(self, event):

        page_background.paint_page_background(self, self.colors)

    # ==========================================================
    # CAMERA METHODS
    # ==========================================================

    def detect_cameras(self, force=False):

        # Detection can be slow (OpenCV probes each index), so the
        # result is cached until a refresh is forced.
        if force or not hasattr(self, "_detected_cameras"):

            try:

                from gui.camera_setup import find_named_cameras

                self._detected_cameras = find_named_cameras()

            except Exception as e:

                print(f"Settings camera detection warning: {e}")

                self._detected_cameras = []

        cameras = list(self._detected_cameras)

        # The active camera may be busy (in use) and missed by the
        # OpenCV probe; always keep it selectable.
        if (
            self.active_camera_index is not None
            and all(i != self.active_camera_index for i, _ in cameras)
        ):

            cameras.insert(
                0,
                (
                    self.active_camera_index,
                    self.active_camera_name
                    or f"Camera {self.active_camera_index}"
                )
            )

        return cameras

    def refresh_cameras(self):

        self.detect_cameras(force=True)
        self.populate_camera_combo()

    def populate_camera_combo(self):

        self.camera_combo.blockSignals(True)

        self.camera_combo.clear()

        cameras = self.detect_cameras()

        if not cameras:

            self.camera_combo.addItem(
                "No camera detected",
                None
            )

        for index, name in cameras:

            self.camera_combo.addItem(name, index)

        self._select_camera_in_combo()

        self.camera_combo.blockSignals(False)

    def _select_camera_in_combo(self):

        if self.active_camera_index is None:
            return

        found = self.camera_combo.findData(
            self.active_camera_index
        )

        if found >= 0:

            self.camera_combo.setCurrentIndex(found)

    def on_camera_selected(self, combo_index):

        index = self.camera_combo.itemData(combo_index)

        name = self.camera_combo.itemText(combo_index)

        if index is None or index == self.active_camera_index:
            return

        # MainWindow broadcasts the choice to every page and saves it.
        if self.main_window is not None and hasattr(
            self.main_window, "setActiveCamera"
        ):

            self.main_window.setActiveCamera(index, name)

        else:

            self.setActiveCamera(index, name)

    def setActiveCamera(self, index, name):

        self.active_camera_index = index

        self.active_camera_name = name

        # Rebuild so a camera missing from the list (e.g. one restored
        # from a previous session) is still shown.
        try:

            self.populate_camera_combo()

        except RuntimeError:

            pass

    # ==========================================================
    # OPTIONAL CAMERA NAME METHOD
    # ==========================================================

    def updateCameraName(self, name):

        if name:

            self.active_camera_name = name

        try:

            found_index = self.camera_combo.findText(
                self.active_camera_name
            )

            if found_index >= 0:

                self.camera_combo.blockSignals(True)

                self.camera_combo.setCurrentIndex(
                    found_index
                )

                self.camera_combo.blockSignals(False)

        except RuntimeError:

            pass
