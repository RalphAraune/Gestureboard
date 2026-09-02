from pathlib import Path

from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRectF
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QPainterPath, QFont
from PyQt5.QtWidgets import QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget, QGraphicsOpacityEffect


class SplashPage(QWidget):
    """Light splash showing concentric rings, logo, and a progress bar.

    Once loading reaches 100%, the progress area is smoothly transformed into
    a 'Get Started' button. Clicking it starts the onboarding tutorial.
    """

    DURATION_MS = 5000

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.elapsed_ms = 0
        self.finished_loading = False
        self.setObjectName("splashPage")

        # Frost White background with concentric rings drawn in paintEvent.
        self.setStyleSheet("""
            QWidget#splashPage { background: #F5FEFF; }
            QLabel { background: transparent; color: #0E2F76; }
            QLabel#brand { font-size: 30px; font-weight: 800; color: #0E2F76; }
            QLabel#tagline { color: #5C6BC0; font-size: 13px; }
            QLabel#loading { color: #AAC0E1; font-size: 11px; }
            QProgressBar { background: #E4ECF7; border: none; border-radius: 3px; height: 4px; }
            QProgressBar::chunk { background: #0E2F76; border-radius: 3px; }
            QPushButton#getStarted {
                background: #0E2F76; color: #F5FEFF; border: none; border-radius: 10px;
                min-height: 50px; min-width: 210px; font-size: 15px; font-weight: 700;
            }
            QPushButton#getStarted:hover { background: #1B4499; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 50)
        layout.setAlignment(Qt.AlignCenter)
        layout.addStretch(1)

        # Blue rounded-square "G" logo (logo1.png if available)
        self.logo = QLabel()
        self.logo.setAlignment(Qt.AlignCenter)
        self.logo.setFixedSize(56, 56)
        logo_path = Path(__file__).resolve().parent.parent / "assets" / "logo" / "logo1.png"
        pixmap = QPixmap(str(logo_path))
        if not pixmap.isNull():
            self.logo.setPixmap(pixmap.scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.logo.setStyleSheet(
                "background: #0E2F76; color: #F5FEFF; border-radius: 12px;"
                "font-size: 30px; font-weight: 800;"
            )
            self.logo.setText("G")
        layout.addWidget(self.logo, 0, Qt.AlignCenter)

        layout.addSpacing(24)

        # Branding
        brand = QLabel("GestureBoard")
        brand.setObjectName("brand")
        brand.setAlignment(Qt.AlignCenter)
        layout.addWidget(brand)

        tagline = QLabel("Gesture-Controlled Presentation and Annotation System")
        tagline.setObjectName("tagline")
        tagline.setAlignment(Qt.AlignCenter)
        layout.addWidget(tagline)

        layout.addSpacing(36)

        # Thin progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.setFixedSize(220, 4)
        layout.addWidget(self.progress, 0, Qt.AlignCenter)

        layout.addSpacing(12)

        # Loading label
        self.loading_label = QLabel("Initializing System…")
        self.loading_label.setObjectName("loading")
        self.loading_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.loading_label)

        # Get Started button (hidden until loading completes)
        self.get_started_btn = QPushButton("Get Started")
        self.get_started_btn.setObjectName("getStarted")
        self.get_started_btn.setCursor(Qt.PointingHandCursor)
        self.get_started_btn.clicked.connect(self.navigate_to_get_started)
        self.get_started_btn.hide()

        self._fade = QGraphicsOpacityEffect(self.get_started_btn)
        self.get_started_btn.setGraphicsEffect(self._fade)

        layout.addSpacing(12)
        layout.addWidget(self.get_started_btn, 0, Qt.AlignCenter)
        layout.addStretch(1)

        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.advance_loading)
        self.timer.start()

    def paintEvent(self, event):
        """Draw the concentric decorative rings on the light background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2

        # Faint outer rings to innermost, using progressively stronger blue.
        rings = [(330, 26), (270, 38), (210, 52), (150, 70)]
        for radius, alpha in rings:
            pen = QPen(QColor(14, 47, 118, alpha))
            pen.setWidthF(2.0)
            painter.setPen(pen)
            painter.drawEllipse(QRectF(cx - radius, cy - radius, radius * 2, radius * 2))

        super().paintEvent(event)

    def advance_loading(self):
        self.elapsed_ms = min(self.DURATION_MS, self.elapsed_ms + self.timer.interval())
        percent = int(self.elapsed_ms * 100 / self.DURATION_MS)
        self.progress.setValue(percent)
        self.loading_label.setText(f"Initializing System… {percent}%")
        if self.elapsed_ms >= self.DURATION_MS:
            self.timer.stop()
            self.show_get_started()

    def show_get_started(self):
        """Transition progress bar into a Get Started button."""
        if self.finished_loading:
            return
        self.finished_loading = True

        # Hide loading UI
        self.loading_label.hide()
        self.progress.hide()

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
