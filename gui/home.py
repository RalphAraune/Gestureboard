from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QSizePolicy,
)


class HomePage(QWidget):
    """
    GestureBoard Dashboard / Home Page.

    IMPORTANT:
    This page DOES NOT create a sidebar.
    The sidebar is created and controlled by MainWindow.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.parent_window = parent

        self.setObjectName("homePage")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setup_ui()

    # ==========================================================
    # MAIN UI
    # ==========================================================

    def setup_ui(self):

        self.setStyleSheet("""
            QWidget#homePage {
                background-color: #F4FBFD;
            }

            QLabel {
                background-color: transparent;
                color: #173A82;
            }

            QLabel#pageTitle {
                color: #173A82;
                font-size: 25px;
                font-weight: 700;
            }

            QLabel#pageSubtitle {
                color: #6380B2;
                font-size: 12px;
            }

            /* =========================
               STATUS CARDS
               ========================= */

            QFrame#statusCard {
                background-color: #FFFFFF;
                border: 1px solid #B6CDEA;
                border-radius: 9px;
            }

            QLabel#statusCaption {
                color: #91A8CB;
                font-size: 9px;
                font-weight: 700;
            }

            QLabel#statusValue {
                color: #173A82;
                font-size: 13px;
                font-weight: 600;
            }

            QLabel#statusGreen {
                color: #20A463;
                font-size: 13px;
                font-weight: 600;
            }

            QLabel#statusOrange {
                color: #E49A24;
                font-size: 13px;
                font-weight: 600;
            }

            /* =========================
               FEATURE CARDS
               ========================= */

            QFrame#featureCard {
                background-color: #FFFFFF;
                border: 1px solid #B6CDEA;
                border-radius: 10px;
            }

            QLabel#featureIcon {
                color: #173A82;
                font-size: 20px;
                font-weight: 600;
            }

            QLabel#featureTitle {
                color: #173A82;
                font-size: 14px;
                font-weight: 700;
            }

            QLabel#featureDescription {
                color: #6380B2;
                font-size: 11px;
            }

            QPushButton#featureButton {
                background-color: #173A82;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                min-height: 32px;
                font-size: 11px;
                font-weight: 700;
            }

            QPushButton#featureButton:hover {
                background-color: #31589B;
            }

            QPushButton#featureButton:pressed {
                background-color: #102E68;
            }
        """)

        # ======================================================
        # ROOT LAYOUT
        # ======================================================

        root = QVBoxLayout(self)

        root.setContentsMargins(
            28,
            24,
            28,
            24
        )

        root.setSpacing(18)

        # ======================================================
        # HEADER
        # ======================================================

        title = QLabel("Dashboard")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "Control your presentations and computer using gesture interaction."
        )

        subtitle.setObjectName("pageSubtitle")

        root.addWidget(title)
        root.addWidget(subtitle)

        # ======================================================
        # STATUS CARDS
        # ======================================================

        status_row = QHBoxLayout()
        status_row.setSpacing(14)

        # Camera
        self.camera_card = self.create_status_card(
            "CAMERA",
            "•  No camera selected",
            "green"
        )

        # Hand Tracking
        self.hand_tracking_card = self.create_status_card(
            "HAND TRACKING",
            "•  Active",
            "green"
        )

        # Gesture Recognition
        self.gesture_card = self.create_status_card(
            "GESTURE RECOGNITION",
            "•  Ready",
            "green"
        )

        # Current Mode
        self.mode_card = self.create_status_card(
            "CURRENT MODE",
            "•  Idle",
            "orange"
        )

        status_row.addWidget(self.camera_card)
        status_row.addWidget(self.hand_tracking_card)
        status_row.addWidget(self.gesture_card)
        status_row.addWidget(self.mode_card)

        root.addLayout(status_row)

        # ======================================================
        # FIRST FEATURE ROW
        # ======================================================

        feature_row_1 = QHBoxLayout()
        feature_row_1.setSpacing(14)

        presentation_card = self.create_feature_card(
            "▣",
            "Presentation Control",
            "Navigate presentation slides using gestures",
            "Open Presentation",
            "presentation"
        )

        virtual_mouse_card = self.create_feature_card(
            "◉",
            "Virtual Mouse",
            "Control your computer cursor using hand gestures",
            "Open Virtual Mouse",
            "virtual_mouse"
        )

        feature_row_1.addWidget(presentation_card)
        feature_row_1.addWidget(virtual_mouse_card)

        root.addLayout(feature_row_1)

        # ======================================================
        # SECOND FEATURE ROW
        # ======================================================

        feature_row_2 = QHBoxLayout()
        feature_row_2.setSpacing(14)

        whiteboard_card = self.create_feature_card(
            "▱",
            "Whiteboard",
            "Draw and write using your mouse",
            "Open Whiteboard",
            "whiteboard"
        )

        annotation_card = self.create_feature_card(
            "✎",
            "Annotation",
            "Annotate presentation materials using mouse controls",
            "Open Annotation",
            "annotation"
        )

        feature_row_2.addWidget(whiteboard_card)
        feature_row_2.addWidget(annotation_card)

        root.addLayout(feature_row_2)

        # Empty space underneath
        root.addStretch()

    # ==========================================================
    # STATUS CARD
    # ==========================================================

    def create_status_card(
        self,
        caption,
        value,
        status_type="normal"
    ):

        card = QFrame()
        card.setObjectName("statusCard")

        card.setMinimumHeight(68)

        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed
        )

        layout = QVBoxLayout(card)

        layout.setContentsMargins(
            14,
            10,
            14,
            10
        )

        layout.setSpacing(5)

        # Caption
        caption_label = QLabel(caption)
        caption_label.setObjectName("statusCaption")

        # Value
        value_label = QLabel(value)

        if status_type == "green":
            value_label.setObjectName("statusGreen")

        elif status_type == "orange":
            value_label.setObjectName("statusOrange")

        else:
            value_label.setObjectName("statusValue")

        layout.addWidget(caption_label)
        layout.addWidget(value_label)

        # Save references so values can be changed later
        card.value_label = value_label

        return card

    # ==========================================================
    # FEATURE CARD
    # ==========================================================

    def create_feature_card(
        self,
        icon,
        title,
        description,
        button_text,
        page_name
    ):

        card = QFrame()
        card.setObjectName("featureCard")

        card.setMinimumHeight(138)

        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed
        )

        layout = QVBoxLayout(card)

        layout.setContentsMargins(
            18,
            14,
            18,
            14
        )

        layout.setSpacing(5)

        # ------------------------------------------------------
        # Icon
        # ------------------------------------------------------

        icon_label = QLabel(icon)
        icon_label.setObjectName("featureIcon")

        icon_label.setFixedHeight(24)

        # ------------------------------------------------------
        # Title
        # ------------------------------------------------------

        title_label = QLabel(title)
        title_label.setObjectName("featureTitle")

        # ------------------------------------------------------
        # Description
        # ------------------------------------------------------

        description_label = QLabel(description)
        description_label.setObjectName("featureDescription")

        description_label.setWordWrap(True)

        # ------------------------------------------------------
        # Button
        # ------------------------------------------------------

        button = QPushButton(button_text)
        button.setObjectName("featureButton")

        button.setCursor(Qt.PointingHandCursor)

        button.setMinimumHeight(32)

        # Connect to MainWindow navigation
        button.clicked.connect(
            lambda checked=False, page=page_name:
            self.open_page(page)
        )

        # ------------------------------------------------------
        # Add widgets
        # ------------------------------------------------------

        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(description_label)

        layout.addStretch()

        layout.addWidget(button)

        return card

    # ==========================================================
    # PAGE NAVIGATION
    # ==========================================================

    def open_page(self, page_name):

        if not self.parent_window:
            return

        # Preferred method for your new MainWindow
        if hasattr(self.parent_window, "show_page"):
            self.parent_window.show_page(page_name)
            return

        # Compatibility with older MainWindow code
        if page_name == "home":
            if hasattr(self.parent_window, "showDashboard"):
                self.parent_window.showDashboard()

        elif page_name == "presentation":
            if hasattr(self.parent_window, "showPresentation"):
                self.parent_window.showPresentation()

        elif page_name == "virtual_mouse":
            if hasattr(self.parent_window, "showVirtualMouse"):
                self.parent_window.showVirtualMouse()

        elif page_name == "whiteboard":
            if hasattr(self.parent_window, "showWhiteboard"):
                self.parent_window.showWhiteboard()

        elif page_name == "annotation":
            if hasattr(self.parent_window, "showAnnotation"):
                self.parent_window.showAnnotation()

    # ==========================================================
    # CAMERA STATUS
    # ==========================================================

    def updateCameraName(self, name):

        if hasattr(self, "camera_card"):
            self.camera_card.value_label.setText(
                f"•  {name}"
            )

    # ==========================================================
    # UPDATE MODE
    # ==========================================================

    def updateMode(self, mode):

        if hasattr(self, "mode_card"):
            self.mode_card.value_label.setText(
                f"•  {mode}"
            )

    # ==========================================================
    # UPDATE CAMERA STATUS
    # ==========================================================

    def updateCameraStatus(self, connected):

        if not hasattr(self, "camera_card"):
            return

        if connected:

            self.camera_card.value_label.setText(
                "•  Connected"
            )

            self.camera_card.value_label.setObjectName(
                "statusGreen"
            )

        else:

            self.camera_card.value_label.setText(
                "•  No camera selected"
            )

            self.camera_card.value_label.setObjectName(
                "statusValue"
            )

        # Refresh stylesheet
        self.camera_card.value_label.style().unpolish(
            self.camera_card.value_label
        )

        self.camera_card.value_label.style().polish(
            self.camera_card.value_label
        )

    # ==========================================================
    # UPDATE GESTURE STATUS
    # ==========================================================

    def updateGestureStatus(self, active):

        if not hasattr(self, "gesture_card"):
            return

        if active:

            self.gesture_card.value_label.setText(
                "•  Active"
            )

        else:

            self.gesture_card.value_label.setText(
                "•  Ready"
            )

    # ==========================================================
    # UPDATE HAND TRACKING
    # ==========================================================

    def updateHandTracking(self, active):

        if not hasattr(self, "hand_tracking_card"):
            return

        if active:

            self.hand_tracking_card.value_label.setText(
                "•  Active"
            )

        else:

            self.hand_tracking_card.value_label.setText(
                "•  Ready"
            )