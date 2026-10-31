"""Dialog that connects a phone as the camera.

Shows a QR code for the phone to scan (plus the address as text to
type in), lets the user pick the network when the laptop is on more
than one, and shows whether the phone is connected. The server itself
lives in core/phone_camera.py.
"""

from PyQt5.QtCore import QRectF, Qt, QTimer
from PyQt5.QtGui import QColor, QGuiApplication, QPainter
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.phone_camera import (
    PhoneCameraServer,
    local_ipv4s,
    phone_url,
)
from settings import theme as app_theme
from widgets import page_background


# ============================================================
# QR CODE
# Drawn from the qrcode library's module matrix, so it stays sharp
# at any size. Always dark on white: phones read that best.
# ============================================================

class QrCode(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._matrix = None
        self.setFixedSize(248, 248)

    def set_text(self, text):

        import qrcode

        if not text:
            self._matrix = None
        else:
            qr = qrcode.QRCode(border=3, error_correction=qrcode.constants.ERROR_CORRECT_M)
            qr.add_data(text)
            qr.make(fit=True)
            self._matrix = qr.get_matrix()

        self.update()

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawRoundedRect(QRectF(self.rect()), 14, 14)

        if not self._matrix:
            return

        count = len(self._matrix)
        cell = min(self.width(), self.height()) / count
        offset = (self.width() - cell * count) / 2

        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setBrush(QColor("#0A1D47"))

        for y, row in enumerate(self._matrix):
            for x, dark in enumerate(row):
                if dark:
                    painter.drawRect(QRectF(
                        offset + x * cell, offset + y * cell, cell + 0.5, cell + 0.5
                    ))


# ============================================================
# DIALOG
# ============================================================

STATUS_TEXT = {
    "waiting": "Waiting for your phone",
    "connected": "Phone connected",
    "paused": "Phone connected, but no video. Keep the page open and the screen on.",
    "disconnected": "Phone disconnected. It reconnects by itself when the page is open.",
    "stopped": "Not running",
}


class PhoneCameraDialog(QDialog):
    """Accepted once the phone is connected and the user confirms."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Use your phone as the camera")
        self.setModal(True)
        self.setMinimumWidth(720)

        self.server = PhoneCameraServer.get()

        self._build()
        self._apply_style()

        self.refresh_networks()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_status)
        self._timer.start(300)
        self._update_status()

    # --------------------------------------------------------
    # LAYOUT
    # --------------------------------------------------------

    def _build(self):

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 22)
        root.setSpacing(16)

        title = QLabel("Use your phone as the camera")
        title.setObjectName("title")

        subtitle = QLabel(
            "Nothing to install on the phone, and no internet needed. "
            "Your phone streams its camera to GestureBoard over your local network."
        )
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)

        root.addWidget(title)
        root.addWidget(subtitle)

        body = QHBoxLayout()
        body.setSpacing(24)

        # ---------- QR and address ----------

        left = QVBoxLayout()
        left.setSpacing(10)

        self.qr = QrCode()
        left.addWidget(self.qr, 0, Qt.AlignHCenter)

        self.url_label = QLabel()
        self.url_label.setObjectName("url")
        self.url_label.setAlignment(Qt.AlignCenter)
        self.url_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        left.addWidget(self.url_label)

        self.copy_button = QPushButton("Copy address")
        self.copy_button.setObjectName("secondary")
        self.copy_button.setCursor(Qt.PointingHandCursor)
        self.copy_button.clicked.connect(self._copy_url)
        left.addWidget(self.copy_button, 0, Qt.AlignHCenter)

        left.addStretch()
        body.addLayout(left)

        # ---------- steps, network, status ----------

        right = QVBoxLayout()
        right.setSpacing(10)

        steps = [
            "Connect the phone and this computer to the same network: "
            "Wi-Fi, the phone's hotspot, or USB tethering.",
            "Scan the QR code with the phone's camera, or type the address "
            "into its browser.",
            "First time only: the browser warns that the connection is not "
            "private. Tap Advanced, then Proceed. On iPhone, tap Show Details, "
            "then visit this website.",
            "Allow the camera when the browser asks.",
        ]

        for number, text in enumerate(steps, start=1):
            right.addLayout(self._step(number, text))

        right.addSpacing(6)

        network_row = QHBoxLayout()
        network_row.setSpacing(8)

        network_label = QLabel("Network")
        network_label.setObjectName("fieldLabel")

        self.network_combo = QComboBox()
        self.network_combo.setCursor(Qt.PointingHandCursor)
        self.network_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.network_combo.currentIndexChanged.connect(self._show_url)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setObjectName("secondary")
        self.refresh_button.setCursor(Qt.PointingHandCursor)
        self.refresh_button.setToolTip("Look for networks again (after plugging in USB tethering, for example)")
        self.refresh_button.clicked.connect(self.refresh_networks)

        network_row.addWidget(network_label)
        network_row.addWidget(self.network_combo, 1)
        network_row.addWidget(self.refresh_button)
        right.addLayout(network_row)

        self.status_frame = QFrame()
        self.status_frame.setObjectName("statusFrame")

        status_layout = QHBoxLayout(self.status_frame)
        status_layout.setContentsMargins(14, 10, 14, 10)
        status_layout.setSpacing(10)

        self.status_dot = QLabel()
        self.status_dot.setObjectName("statusDot")
        self.status_dot.setFixedSize(12, 12)

        self.status_label = QLabel()
        self.status_label.setObjectName("statusText")
        self.status_label.setWordWrap(True)

        status_layout.addWidget(self.status_dot, 0, Qt.AlignVCenter)
        status_layout.addWidget(self.status_label, 1)
        right.addWidget(self.status_frame)

        self.help_label = QLabel(
            "Phone can't open the page? Check both are on the network picked "
            "above, and allow GestureBoard when Windows Firewall asks "
            "(on public networks too: hotspots and USB tethering count as public)."
        )
        self.help_label.setObjectName("help")
        self.help_label.setWordWrap(True)
        right.addWidget(self.help_label)

        right.addStretch()
        body.addLayout(right, 1)

        root.addLayout(body, 1)

        # ---------- buttons ----------

        buttons = QHBoxLayout()
        buttons.addStretch()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("secondary")
        self.cancel_button.setCursor(Qt.PointingHandCursor)
        self.cancel_button.clicked.connect(self.reject)

        self.use_button = QPushButton("Use phone camera")
        self.use_button.setObjectName("primary")
        self.use_button.setCursor(Qt.PointingHandCursor)
        self.use_button.setEnabled(False)
        self.use_button.clicked.connect(self.accept)

        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.use_button)
        root.addLayout(buttons)

    def _step(self, number, text):

        row = QHBoxLayout()
        row.setSpacing(10)

        badge = QLabel(str(number))
        badge.setObjectName("stepNumber")
        badge.setFixedSize(24, 24)
        badge.setAlignment(Qt.AlignCenter)

        label = QLabel(text)
        label.setObjectName("stepText")
        label.setWordWrap(True)

        row.addWidget(badge, 0, Qt.AlignTop)
        row.addWidget(label, 1)

        return row

    # --------------------------------------------------------
    # NETWORKS AND ADDRESS
    # --------------------------------------------------------

    def refresh_networks(self):
        """List the laptop's addresses, and make sure the server runs
        with a certificate that covers all of them."""

        networks = local_ipv4s()

        current = self.network_combo.currentData()

        self.network_combo.blockSignals(True)
        self.network_combo.clear()

        for name, ip in networks:
            self.network_combo.addItem(f"{name} ({ip})", ip)

        found = self.network_combo.findData(current)
        self.network_combo.setCurrentIndex(found if found >= 0 else 0)
        self.network_combo.setEnabled(len(networks) > 1)
        self.network_combo.blockSignals(False)

        if not networks:
            self.server.error = (
                "This computer is not on any network. Turn on Wi-Fi, the phone's "
                "hotspot or USB tethering, then press Refresh."
            )
            self._show_url()
            return

        # A new address (USB tethering plugged in) needs a certificate
        # that includes it: restart the server with a fresh one.
        if self.server.running and not all(self.server.covers(ip) for _n, ip in networks):
            self.server.restart()
        elif not self.server.running:
            self.server.start()

        self._show_url()

    def _show_url(self, *_):

        ip = self.network_combo.currentData()
        url = phone_url(ip) if ip and self.server.running else ""

        self.qr.set_text(url)
        self.url_label.setText(url or "No address yet")
        self.copy_button.setEnabled(bool(url))

    def _copy_url(self):

        ip = self.network_combo.currentData()

        if ip:
            QGuiApplication.clipboard().setText(phone_url(ip))
            self.copy_button.setText("Copied")
            QTimer.singleShot(1500, lambda: self.copy_button.setText("Copy address"))

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    def _update_status(self):

        if not self.server.running:
            state = "error"
            text = self.server.error or STATUS_TEXT["stopped"]
        else:
            state = self.server.status
            text = STATUS_TEXT.get(state, state)

        self.status_label.setText(text)
        self.status_frame.setProperty("state", state)
        self.status_dot.setProperty("state", state)

        for widget in (self.status_frame, self.status_dot):
            widget.style().unpolish(widget)
            widget.style().polish(widget)

        connected = state == "connected"
        self.use_button.setEnabled(connected)
        self.help_label.setVisible(state in ("waiting", "error"))

    def done(self, result):
        self._timer.stop()
        super().done(result)

    # --------------------------------------------------------
    # STYLE
    # --------------------------------------------------------

    def _apply_style(self):

        c = page_background.page_colors()
        dark = app_theme.is_dark()

        sheet = "#17314F" if dark else "#FFFFFF"
        field = "#0F2038" if dark else "#F4F7FB"
        field_border = "#335B89" if dark else "#B9CCE4"
        hover = "#21416A" if dark else "#EAF1F9"
        step_bg = "#21416A" if dark else "#E3F7FB"
        step_fg = "#9FE6F2" if dark else "#0D7C92"

        ok, ok_bg = ("#5FD39A", "#173B2E") if dark else ("#23804F", "#E3F4EA")
        wait, wait_bg = ("#FFC857", "#3D3220") if dark else ("#9A6400", "#FFF3D6")
        bad, bad_bg = ("#F07A70", "#4A2328") if dark else ("#B83227", "#F8E1DF")

        self.setStyleSheet(f"""
            QDialog {{ background: {sheet}; }}
            QLabel {{ background: transparent; color: {c['text']}; }}

            QLabel#title {{ font-size: 24px; font-weight: 800; }}
            QLabel#subtitle {{ font-size: 15px; color: {c['text_secondary']}; }}

            QLabel#url {{ font-size: 15px; font-weight: 700; }}

            QLabel#stepNumber {{
                background: {step_bg}; color: {step_fg};
                border-radius: 12px; font-size: 13px; font-weight: 800;
            }}
            QLabel#stepText {{ font-size: 15px; }}
            QLabel#fieldLabel {{ font-size: 15px; font-weight: 700; }}
            QLabel#help {{ font-size: 13px; color: {c['text_secondary']}; }}

            QComboBox {{
                background: {field}; color: {c['text']};
                border: 1px solid {field_border}; border-radius: 10px;
                padding: 7px 12px; font-size: 15px; min-height: 22px;
            }}
            QComboBox QAbstractItemView {{
                background: {sheet}; color: {c['text']};
                selection-background-color: {hover}; selection-color: {c['text']};
            }}

            QPushButton {{
                border-radius: 10px; padding: 9px 18px;
                font-size: 15px; font-weight: 700; min-height: 22px;
            }}
            QPushButton#primary {{ background: {c['primary']}; color: {c['primary_text']}; border: none; }}
            QPushButton#primary:hover {{ background: {c['sidebar_hover']}; color: {c['sidebar_text']}; }}
            QPushButton#primary:disabled {{ background: {field_border}; color: {c['text_secondary']}; }}
            QPushButton#secondary {{
                background: {field}; color: {c['text']}; border: 1px solid {field_border};
            }}
            QPushButton#secondary:hover {{ background: {hover}; }}
            QPushButton:focus {{ outline: none; border: 2px solid {c['accent'] if dark else c['sidebar_hover']}; }}

            QFrame#statusFrame {{ border-radius: 12px; background: {wait_bg}; }}
            QFrame#statusFrame[state="connected"] {{ background: {ok_bg}; }}
            QFrame#statusFrame[state="disconnected"],
            QFrame#statusFrame[state="error"] {{ background: {bad_bg}; }}

            QLabel#statusText {{ font-size: 15px; font-weight: 700; }}

            QLabel#statusDot {{ border-radius: 6px; background: {wait}; }}
            QLabel#statusDot[state="connected"] {{ background: {ok}; }}
            QLabel#statusDot[state="disconnected"],
            QLabel#statusDot[state="error"] {{ background: {bad}; }}
        """)


def connect_phone(parent=None):
    """Show the dialog; True once the phone is connected and chosen."""

    dialog = PhoneCameraDialog(parent)
    return dialog.exec_() == QDialog.Accepted
