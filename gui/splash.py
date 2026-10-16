from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtWidgets import QPushButton, QSizePolicy, QVBoxLayout, QWidget, QGraphicsOpacityEffect

from gui.splash_logo import AnimatedLogo


class SplashPage(QWidget):
    """Light splash that plays the animated GestureBoard logo.

    When the animation has finished, a 'Get Started' button fades in.
    Clicking it starts the onboarding tutorial.
    """

    # Matches the logo + tagline animation (about 5 s), plus a short pause.
    DURATION_MS = 5200

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.finished_loading = False
        self.setObjectName("splashPage")

        self.setStyleSheet("""
            QWidget#splashPage { background: #EEF2F7; }
            QLabel { background: transparent; color: #0E2F76; }
            QPushButton#getStarted {
                background: #0E2F76; color: #EEF2F7; border: none; border-radius: 10px;
                min-height: 50px; min-width: 210px; font-size: 15px; font-weight: 700;
            }
            QPushButton#getStarted:hover { background: #1B4499; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 40)
        layout.setAlignment(Qt.AlignCenter)
        layout.addStretch(1)

        # Animated logo, "GestureBoard" name and tagline
        # (plays once, then stays on screen).
        self.logo = AnimatedLogo(
            self,
            background="#EEF2F7",
            tagline="Gesture-Controlled Presentation and Annotation System",
        )
        layout.addWidget(self.logo, 0, Qt.AlignCenter)

        layout.addSpacing(28)

        # Get Started button (hidden until the animation completes). It keeps
        # its space while hidden so the logo does not jump when it appears.
        self.get_started_btn = QPushButton("Get Started")
        self.get_started_btn.setObjectName("getStarted")
        self.get_started_btn.setCursor(Qt.PointingHandCursor)
        self.get_started_btn.clicked.connect(self.navigate_to_get_started)

        policy = self.get_started_btn.sizePolicy()
        policy.setRetainSizeWhenHidden(True)
        self.get_started_btn.setSizePolicy(policy)

        self.get_started_btn.hide()

        self._fade = QGraphicsOpacityEffect(self.get_started_btn)
        self.get_started_btn.setGraphicsEffect(self._fade)

        layout.addWidget(self.get_started_btn, 0, Qt.AlignCenter)
        layout.addStretch(1)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(self.DURATION_MS)
        self.timer.timeout.connect(self.show_get_started)

    def showEvent(self, event):
        super().showEvent(event)
        # Play the logo animation the first time the splash appears,
        # and reveal the button once it has finished.
        if not self.logo.started:
            self.logo.start()
            self.timer.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Large logo that still leaves room for the name, tagline and
        # button: about half of the window's smaller side, up to 480 px.
        vmin = min(self.width(), self.height())
        # Logo + name + tagline take about 1.45x the logo width in height;
        # the button, spacing and margins need roughly 210 px more.
        fits_height = (self.height() - 210) / 1.45
        self.logo.set_logo_width(min(480, vmin * 0.5, fits_height))

    def show_get_started(self):
        """Fade in the Get Started button."""
        if self.finished_loading:
            return
        self.finished_loading = True

        # Always show the Get Started button (first-run onboarding).
        self.get_started_btn.show()
        anim = QPropertyAnimation(self._fade, b"opacity", self)
        anim.setDuration(450)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        self._anim = anim
        anim.start()

    def navigate_to_get_started(self):
        if self.parent_window:
            self.parent_window.showTutorial()
