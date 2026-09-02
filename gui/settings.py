from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QSlider,
    QFrame,
    QSizePolicy,
    QMessageBox,
)

from PyQt5.QtCore import Qt


class SettingsPage(QWidget):
    """
    GestureBoard Settings Page

    Designed to work with:
        MainWindow(self)

    MainWindow can also call:
        settings.setActiveCamera(index, name)
    """

    # ==========================================================
    # COLORS
    # ==========================================================

    NAVY = "#163B82"
    NAVY_DARK = "#123575"

    BACKGROUND = "#F5FEFF"
    CARD = "#FBFEFF"
    BORDER = "#D7E4F2"

    TEXT = "#163B82"
    SECONDARY = "#6685B7"

    SELECTED = "#DCEAF7"
    LIGHT_BLUE = "#AFC7E8"

    WHITE = "#FFFFFF"

    GREEN = "#21C46B"

    # ==========================================================
    # INITIALIZATION
    # ==========================================================

    def __init__(self, main_window=None):
        super().__init__(main_window)

        self.main_window = main_window

        self.active_camera_index = None
        self.active_camera_name = "Default Webcam"

        self.current_section = "Camera"

        self.setup_ui()

    # ==========================================================
    # MAIN UI
    # ==========================================================

    def setup_ui(self):

        self.setObjectName("SettingsPage")

        self.setStyleSheet(
            f"""
            QWidget#SettingsPage {{
                background-color: {self.BACKGROUND};
                color: {self.TEXT};
            }}

            QLabel {{
                background: transparent;
                color: {self.TEXT};
            }}

            QPushButton {{
                border: none;
                background: transparent;
                color: {self.TEXT};
            }}

            QComboBox {{
                background-color: {self.WHITE};
                border: 1px solid #C5D8EC;
                border-radius: 8px;
                padding: 7px 12px;
                color: {self.TEXT};
                min-height: 28px;
            }}

            QComboBox:hover {{
                border: 1px solid #9CBCE0;
            }}

            QComboBox::drop-down {{
                border: none;
                width: 28px;
            }}

            QSlider::groove:horizontal {{
                height: 4px;
                background: #DCE8F3;
                border-radius: 2px;
            }}

            QSlider::handle:horizontal {{
                width: 12px;
                height: 12px;
                margin: -4px 0;
                background: {self.NAVY};
                border-radius: 6px;
            }}

            QSlider::sub-page:horizontal {{
                background: {self.LIGHT_BLUE};
                border-radius: 2px;
            }}
            """
        )

        # ======================================================
        # ROOT LAYOUT
        # ======================================================

        root_layout = QVBoxLayout(self)

        root_layout.setContentsMargins(
            42,
            30,
            42,
            30
        )

        root_layout.setSpacing(0)

        # ======================================================
        # PAGE TITLE
        # ======================================================

        title = QLabel("Settings")

        title.setStyleSheet(
            f"""
            QLabel {{
                color: {self.NAVY};
                font-size: 24px;
                font-weight: 700;
            }}
            """
        )

        root_layout.addWidget(title)

        # ======================================================
        # PAGE DESCRIPTION
        # ======================================================

        description = QLabel(
            "Configure camera, gesture, presentation, and storage preferences."
        )

        description.setStyleSheet(
            f"""
            QLabel {{
                color: {self.SECONDARY};
                font-size: 13px;
                margin-top: 2px;
            }}
            """
        )

        root_layout.addWidget(description)

        # ======================================================
        # MAIN CONTENT
        # ======================================================

        content_layout = QHBoxLayout()

        content_layout.setContentsMargins(
            0,
            25,
            0,
            0
        )

        content_layout.setSpacing(18)

        root_layout.addLayout(content_layout)

        # ======================================================
        # SETTINGS NAVIGATION
        # ======================================================

        self.settings_nav = QVBoxLayout()

        self.settings_nav.setContentsMargins(
            0,
            0,
            0,
            0
        )

        self.settings_nav.setSpacing(3)

        content_layout.addLayout(
            self.settings_nav,
            0
        )

        # Navigation buttons

        self.general_btn = self.create_nav_button(
            "General"
        )

        self.camera_btn = self.create_nav_button(
            "Camera"
        )

        self.gesture_btn = self.create_nav_button(
            "Gesture"
        )

        self.presentation_btn = self.create_nav_button(
            "Presentation"
        )

        self.storage_btn = self.create_nav_button(
            "Storage"
        )

        self.about_btn = self.create_nav_button(
            "About"
        )

        self.settings_nav.addWidget(
            self.general_btn
        )

        self.settings_nav.addWidget(
            self.camera_btn
        )

        self.settings_nav.addWidget(
            self.gesture_btn
        )

        self.settings_nav.addWidget(
            self.presentation_btn
        )

        self.settings_nav.addWidget(
            self.storage_btn
        )

        self.settings_nav.addWidget(
            self.about_btn
        )

        self.settings_nav.addStretch()

        # ======================================================
        # CONNECTIONS
        # ======================================================

        self.general_btn.clicked.connect(
            lambda: self.change_section("General")
        )

        self.camera_btn.clicked.connect(
            lambda: self.change_section("Camera")
        )

        self.gesture_btn.clicked.connect(
            lambda: self.change_section("Gesture")
        )

        self.presentation_btn.clicked.connect(
            lambda: self.change_section("Presentation")
        )

        self.storage_btn.clicked.connect(
            lambda: self.change_section("Storage")
        )

        self.about_btn.clicked.connect(
            lambda: self.change_section("About")
        )

        # ======================================================
        # RIGHT CONTENT
        # ======================================================

        self.settings_content = QVBoxLayout()

        self.settings_content.setContentsMargins(
            0,
            0,
            0,
            0
        )

        self.settings_content.setSpacing(14)

        content_layout.addLayout(
            self.settings_content,
            1
        )

        # ======================================================
        # DEFAULT SECTION
        # ======================================================

        self.show_camera_settings()

    # ==========================================================
    # NAVIGATION BUTTON
    # ==========================================================

    def create_nav_button(self, text):

        button = QPushButton(text)

        button.setFixedSize(
            155,
            32
        )

        button.setCursor(
            Qt.PointingHandCursor
        )

        button.setStyleSheet(
            f"""
            QPushButton {{
                text-align: left;
                padding-left: 12px;
                border-radius: 7px;
                color: {self.SECONDARY};
                font-size: 12px;
                background: transparent;
            }}

            QPushButton:hover {{
                background-color: #EDF5FC;
                color: {self.NAVY};
            }}
            """
        )

        return button

    # ==========================================================
    # ACTIVE NAVIGATION
    # ==========================================================

    def update_nav_buttons(self):

        buttons = {
            "General": self.general_btn,
            "Camera": self.camera_btn,
            "Gesture": self.gesture_btn,
            "Presentation": self.presentation_btn,
            "Storage": self.storage_btn,
            "About": self.about_btn,
        }

        for name, button in buttons.items():

            if name == self.current_section:

                button.setStyleSheet(
                    f"""
                    QPushButton {{
                        text-align: left;
                        padding-left: 12px;
                        border-radius: 7px;
                        color: {self.NAVY};
                        font-size: 12px;
                        font-weight: 600;
                        background-color: {self.SELECTED};
                    }}
                    """
                )

            else:

                button.setStyleSheet(
                    f"""
                    QPushButton {{
                        text-align: left;
                        padding-left: 12px;
                        border-radius: 7px;
                        color: {self.SECONDARY};
                        font-size: 12px;
                        background-color: transparent;
                    }}

                    QPushButton:hover {{
                        background-color: #EDF5FC;
                        color: {self.NAVY};
                    }}
                    """
                )

    # ==========================================================
    # CHANGE SECTION
    # ==========================================================

    def change_section(self, section):

        self.current_section = section

        self.update_nav_buttons()

        self.clear_content()

        if section == "General":

            self.show_general_settings()

        elif section == "Camera":

            self.show_camera_settings()

        elif section == "Gesture":

            self.show_gesture_settings()

        elif section == "Presentation":

            self.show_presentation_settings()

        elif section == "Storage":

            self.show_storage_settings()

        elif section == "About":

            self.show_about_settings()

    # ==========================================================
    # CLEAR CONTENT
    # ==========================================================

    def clear_content(self):

        while self.settings_content.count():

            item = self.settings_content.takeAt(0)

            widget = item.widget()

            if widget:

                widget.deleteLater()

    # ==========================================================
    # CARD
    # ==========================================================

    def create_card(self):

        card = QFrame()

        card.setStyleSheet(
            f"""
            QFrame {{
                background-color: {self.CARD};
                border: 1px solid {self.BORDER};
                border-radius: 12px;
            }}
            """
        )

        return card

    # ==========================================================
    # SETTING ROW
    # ==========================================================

    def create_row(self, label_text):

        row = QWidget()

        layout = QHBoxLayout(row)

        layout.setContentsMargins(
            16,
            10,
            16,
            10
        )

        layout.setSpacing(10)

        label = QLabel(label_text)

        label.setStyleSheet(
            f"""
            QLabel {{
                color: {self.TEXT};
                font-size: 12px;
                font-weight: 500;
            }}
            """
        )

        layout.addWidget(
            label
        )

        layout.addStretch()

        return row, layout

    # ==========================================================
    # CAMERA SETTINGS
    # ==========================================================

    def show_camera_settings(self):

        self.current_section = "Camera"

        self.update_nav_buttons()

        # ------------------------------------------------------
        # CAMERA CARD
        # ------------------------------------------------------

        card = self.create_card()

        card_layout = QVBoxLayout(card)

        card_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        card_layout.setSpacing(0)

        # Camera Device

        row, row_layout = self.create_row(
            "Camera Device"
        )

        self.camera_combo = QComboBox()

        self.camera_combo.setFixedWidth(
            128
        )

        self.camera_combo.addItems(
            [
                "Default Webcam",
                "Camera 1",
                "Camera 2"
            ]
        )

        row_layout.addWidget(
            self.camera_combo
        )

        card_layout.addWidget(row)

        self.add_separator(card_layout)

        # Resolution

        row, row_layout = self.create_row(
            "Resolution"
        )

        self.resolution_combo = QComboBox()

        self.resolution_combo.setFixedWidth(
            110
        )

        self.resolution_combo.addItems(
            [
                "1280 × 720",
                "1920 × 1080",
                "640 × 480"
            ]
        )

        row_layout.addWidget(
            self.resolution_combo
        )

        card_layout.addWidget(row)

        self.add_separator(card_layout)

        # FPS

        row, row_layout = self.create_row(
            "FPS"
        )

        self.fps_combo = QComboBox()

        self.fps_combo.setFixedWidth(
            80
        )

        self.fps_combo.addItems(
            [
                "30 FPS",
                "60 FPS",
                "24 FPS"
            ]
        )

        row_layout.addWidget(
            self.fps_combo
        )

        card_layout.addWidget(row)

        self.add_separator(card_layout)

        # Camera Preview

        row, row_layout = self.create_row(
            "Camera Preview"
        )

        self.camera_preview_toggle = QPushButton()

        self.camera_preview_toggle.setCheckable(
            True
        )

        self.camera_preview_toggle.setChecked(
            True
        )

        self.camera_preview_toggle.setFixedSize(
            36,
            20
        )

        self.camera_preview_toggle.clicked.connect(
            self.toggle_camera_preview
        )

        self.update_toggle_style()

        row_layout.addWidget(
            self.camera_preview_toggle
        )

        card_layout.addWidget(row)

        self.settings_content.addWidget(
            card
        )

        # ------------------------------------------------------
        # GESTURE CARD
        # ------------------------------------------------------

        gesture_card = self.create_card()

        gesture_layout = QVBoxLayout(
            gesture_card
        )

        gesture_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        gesture_layout.setSpacing(0)

        gesture_title = QLabel(
            "GESTURE"
        )

        gesture_title.setStyleSheet(
            f"""
            QLabel {{
                color: {self.LIGHT_BLUE};
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
                padding: 14px 16px 4px 16px;
            }}
            """
        )

        gesture_layout.addWidget(
            gesture_title
        )

        # Gesture Sensitivity

        row, row_layout = self.create_row(
            "Gesture Sensitivity"
        )

        slider = self.create_slider(
            70
        )

        row_layout.addWidget(
            slider
        )

        gesture_layout.addWidget(row)

        self.add_separator(gesture_layout)

        # Cursor Sensitivity

        row, row_layout = self.create_row(
            "Cursor Sensitivity"
        )

        slider = self.create_slider(
            55
        )

        row_layout.addWidget(
            slider
        )

        gesture_layout.addWidget(row)

        self.add_separator(gesture_layout)

        # Click Delay

        row, row_layout = self.create_row(
            "Click Delay"
        )

        slider = self.create_slider(
            30
        )

        row_layout.addWidget(
            slider
        )

        gesture_layout.addWidget(row)

        self.add_separator(gesture_layout)

        # Gesture Customization

        row, row_layout = self.create_row(
            "Gesture Customization"
        )

        manage_button = QComboBox()

        manage_button.setFixedWidth(
            85
        )

        manage_button.addItems(
            [
                "Manage",
                "Default"
            ]
        )

        row_layout.addWidget(
            manage_button
        )

        gesture_layout.addWidget(row)

        self.settings_content.addWidget(
            gesture_card
        )

        # ------------------------------------------------------
        # ABOUT CARD
        # ------------------------------------------------------

        about_card = self.create_card()

        about_layout = QVBoxLayout(
            about_card
        )

        about_layout.setContentsMargins(
            16,
            13,
            16,
            13
        )

        name = QLabel(
            "GestureBoard"
        )

        name.setStyleSheet(
            f"""
            QLabel {{
                color: {self.NAVY};
                font-size: 12px;
                font-weight: 700;
            }}
            """
        )

        about_layout.addWidget(
            name
        )

        version = QLabel(
            "Version 1.0 - OpenCV 4.9 · MediaPipe 0.10"
        )

        version.setStyleSheet(
            f"""
            QLabel {{
                color: {self.SECONDARY};
                font-size: 11px;
                margin-top: 2px;
            }}
            """
        )

        about_layout.addWidget(
            version
        )

        self.settings_content.addWidget(
            about_card
        )

        self.settings_content.addStretch()

    # ==========================================================
    # SLIDER
    # ==========================================================

    def create_slider(self, value):

        slider = QSlider(
            Qt.Horizontal
        )

        slider.setMinimum(
            0
        )

        slider.setMaximum(
            100
        )

        slider.setValue(
            value
        )

        slider.setFixedWidth(
            138
        )

        return slider

    # ==========================================================
    # SEPARATOR
    # ==========================================================

    def add_separator(self, layout):

        line = QFrame()

        line.setFrameShape(
            QFrame.HLine
        )

        line.setFixedHeight(
            1
        )

        line.setStyleSheet(
            f"""
            QFrame {{
                background-color: {self.BORDER};
                border: none;
            }}
            """
        )

        layout.addWidget(
            line
        )

    # ==========================================================
    # TOGGLE
    # ==========================================================

    def update_toggle_style(self):

        if self.camera_preview_toggle.isChecked():

            self.camera_preview_toggle.setStyleSheet(
                """
                QPushButton {
                    background-color: #AFC7E8;
                    border: none;
                    border-radius: 10px;
                }

                QPushButton::indicator {
                    width: 12px;
                    height: 12px;
                }
                """
            )

        else:

            self.camera_preview_toggle.setStyleSheet(
                """
                QPushButton {
                    background-color: #DCE8F3;
                    border: none;
                    border-radius: 10px;
                }
                """
            )

    def toggle_camera_preview(self):

        self.update_toggle_style()

    # ==========================================================
    # GENERAL
    # ==========================================================

    def show_general_settings(self):

        card = self.create_card()

        layout = QVBoxLayout(card)

        layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        row, row_layout = self.create_row(
            "Application Theme"
        )

        combo = QComboBox()

        combo.setFixedWidth(
            120
        )

        combo.addItems(
            [
                "Light",
                "System Default"
            ]
        )

        row_layout.addWidget(combo)

        layout.addWidget(row)

        self.settings_content.addWidget(card)

        self.settings_content.addStretch()

    # ==========================================================
    # GESTURE
    # ==========================================================

    def show_gesture_settings(self):

        card = self.create_card()

        layout = QVBoxLayout(card)

        layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        row, row_layout = self.create_row(
            "Gesture Sensitivity"
        )

        row_layout.addWidget(
            self.create_slider(70)
        )

        layout.addWidget(row)

        self.add_separator(layout)

        row, row_layout = self.create_row(
            "Cursor Sensitivity"
        )

        row_layout.addWidget(
            self.create_slider(55)
        )

        layout.addWidget(row)

        self.add_separator(layout)

        row, row_layout = self.create_row(
            "Click Delay"
        )

        row_layout.addWidget(
            self.create_slider(30)
        )

        layout.addWidget(row)

        self.settings_content.addWidget(card)

        self.settings_content.addStretch()

    # ==========================================================
    # PRESENTATION
    # ==========================================================

    def show_presentation_settings(self):

        card = self.create_card()

        layout = QVBoxLayout(card)

        layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        row, row_layout = self.create_row(
            "Presentation Mode"
        )

        combo = QComboBox()

        combo.setFixedWidth(
            120
        )

        combo.addItems(
            [
                "Auto Detect",
                "Manual"
            ]
        )

        row_layout.addWidget(
            combo
        )

        layout.addWidget(row)

        self.add_separator(layout)

        row, row_layout = self.create_row(
            "Full Screen"
        )

        combo = QComboBox()

        combo.setFixedWidth(
            100
        )

        combo.addItems(
            [
                "Enabled",
                "Disabled"
            ]
        )

        row_layout.addWidget(combo)

        layout.addWidget(row)

        self.settings_content.addWidget(card)

        self.settings_content.addStretch()

    # ==========================================================
    # STORAGE
    # ==========================================================

    def show_storage_settings(self):

        card = self.create_card()

        layout = QVBoxLayout(card)

        layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        row, row_layout = self.create_row(
            "Save Annotations"
        )

        combo = QComboBox()

        combo.setFixedWidth(
            120
        )

        combo.addItems(
            [
                "Enabled",
                "Disabled"
            ]
        )

        row_layout.addWidget(
            combo
        )

        layout.addWidget(row)

        self.add_separator(layout)

        row, row_layout = self.create_row(
            "Save Whiteboards"
        )

        combo = QComboBox()

        combo.setFixedWidth(
            120
        )

        combo.addItems(
            [
                "Enabled",
                "Disabled"
            ]
        )

        row_layout.addWidget(combo)

        layout.addWidget(row)

        self.settings_content.addWidget(card)

        self.settings_content.addStretch()

    # ==========================================================
    # ABOUT
    # ==========================================================

    def show_about_settings(self):

        card = self.create_card()

        layout = QVBoxLayout(card)

        layout.setContentsMargins(
            18,
            18,
            18,
            18
        )

        title = QLabel(
            "GestureBoard"
        )

        title.setStyleSheet(
            f"""
            QLabel {{
                color: {self.NAVY};
                font-size: 18px;
                font-weight: 700;
            }}
            """
        )

        layout.addWidget(title)

        version = QLabel(
            "Version 1.0"
        )

        version.setStyleSheet(
            f"""
            QLabel {{
                color: {self.SECONDARY};
                font-size: 12px;
            }}
            """
        )

        layout.addWidget(version)

        info = QLabel(
            "A gesture-controlled desktop application for "
            "presentation navigation and digital annotation "
            "using computer vision."
        )

        info.setWordWrap(
            True
        )

        info.setStyleSheet(
            f"""
            QLabel {{
                color: {self.SECONDARY};
                font-size: 12px;
                margin-top: 8px;
            }}
            """
        )

        layout.addWidget(info)

        self.settings_content.addWidget(card)

        self.settings_content.addStretch()

    # ==========================================================
    # CAMERA METHODS
    # ==========================================================

    def setActiveCamera(self, index, name):

        self.active_camera_index = index

        self.active_camera_name = name

        # Update camera dropdown if available

        if hasattr(self, "camera_combo"):

            found_index = self.camera_combo.findText(
                name
            )

            if found_index >= 0:

                self.camera_combo.setCurrentIndex(
                    found_index
                )

    # ==========================================================
    # OPTIONAL CAMERA NAME METHOD
    # ==========================================================

    def updateCameraName(self, name):

        if name:

            self.active_camera_name = name

        if hasattr(self, "camera_combo"):

            found_index = self.camera_combo.findText(
                self.active_camera_name
            )

            if found_index >= 0:

                self.camera_combo.setCurrentIndex(
                    found_index
                )