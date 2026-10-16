from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtWidgets import QPushButton, QVBoxLayout, QWidget, QGraphicsOpacityEffect

from gui.splash_logo import AnimatedLogo
from settings import theme as app_theme
from widgets import page_background


class SplashPage(QWidget):
    """Splash that plays the animated GestureBoard logo.

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

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 40)
        layout.setAlignment(Qt.AlignCenter)
        layout.addStretch(1)

        # Animated logo, "GestureBoard" name and tagline
        # (plays once, then stays on screen).
        self.logo = AnimatedLogo(
            self,
            tagline="Gesture-Controlled Presentation and Annotation System",
        )
        layout.addWidget(self.logo, 0, Qt.AlignCenter)

        layout.addSpacing(30)

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

        self.apply_theme()

    # ----------------------------------------------------------
    # THEME
    # ----------------------------------------------------------

    def apply_theme(self):
        """Shared Saved Files background, with theme-aware colours."""

        c = self._page_colors = page_background.page_colors()

        self.setStyleSheet(f"""
            QWidget#splashPage {{ background: transparent; }}
            QLabel {{ background: transparent; color: {c['text']}; }}
            QPushButton#getStarted {{
                background: {c['primary']};
                color: {c['primary_text']};
                border: none;
                border-radius: 10px;
                min-height: 46px;
                min-width: 200px;
                font-size: 15px;
                font-weight: 700;
            }}
            QPushButton#getStarted:hover {{
                background: {c['sidebar_hover']};
                color: {c['sidebar_text']};
            }}
        """)

        self.logo.set_dark(app_theme.is_dark())
        self.update()

    def paintEvent(self, event):
        page_background.paint_page_background(self, self._page_colors)

    # ----------------------------------------------------------
    # ANIMATION
    # ----------------------------------------------------------

    def showEvent(self, event):
        super().showEvent(event)
        # Play the logo animation the first time the splash appears,
        # and reveal the button once it has finished.
        if not self.logo.started:
            self.logo.start()
            self.timer.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Logo that still leaves room for the name, tagline and button:
        # about 38% of the window's smaller side, up to 360 px.
        vmin = min(self.width(), self.height())
        # Logo + ring + name + tagline take about 1.5x the logo width in
        # height; the button, spacing and margins need roughly 200 px more.
        fits_height = (self.height() - 200) / 1.5
        self.logo.set_logo_width(min(360, vmin * 0.38, fits_height))

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
