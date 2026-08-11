"""Compact camera picker and optional Camera Setup page."""

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from cv2_enumerate_cameras import enumerate_cameras
except ImportError:
    enumerate_cameras = None

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QComboBox, QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from widgets.sidebar import Sidebar


def find_named_cameras():
    """List Windows webcam names (Iriun/JoyCam included) and their OpenCV indexes."""
    if cv2 is None:
        return []
    backend = cv2.CAP_DSHOW if hasattr(cv2, "CAP_DSHOW") else cv2.CAP_ANY
    if enumerate_cameras is not None:
        try:
            devices = [(item.index, item.name) for item in enumerate_cameras(backend)]
            if devices:
                return devices
        except Exception:
            pass
    devices = []
    for index in range(6):
        probe = cv2.VideoCapture(index, backend)
        if probe.isOpened():
            devices.append((index, f"Camera {index} (device name unavailable)"))
        probe.release()
    return devices


class CameraPickerDialog(QDialog):
    """Small live-preview dialog opened from the Home screen."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.capture = None
        self.selected_index = None
        self.selected_name = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_preview)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setFixedSize(420, 455)
        self.setStyleSheet("""
            QDialog { background: #0F1E35; border: 1px solid #294263; border-radius: 14px; }
            QLabel { background: transparent; color: #EEF4FF; }
            QLabel#title { font-size: 20px; font-weight: 700; }
            QLabel#muted { color: #91A0BB; font-size: 12px; }
            QFrame#preview { background: #050B16; border: 1px solid #294263; border-radius: 10px; }
            QComboBox { background: #152842; border: 1px solid #355474; border-radius: 8px; color: white; padding: 10px; }
            QComboBox QAbstractItemView { background: #0F1E35; color: white; selection-background-color: #1B4E99; }
            QPushButton { background: #152842; border: 1px solid #355474; border-radius: 8px; color: #C9D6EA; padding: 9px 14px; }
            QPushButton#use { background: #3E7CF7; color: white; border: none; font-weight: 700; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        header = QHBoxLayout()
        title = QLabel("Camera")
        title.setObjectName("title")
        close = QPushButton("×")
        close.setFixedWidth(36)
        close.clicked.connect(self.reject)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(close)
        layout.addLayout(header)
        hint = QLabel("Choose the camera GestureBoard should use.")
        hint.setObjectName("muted")
        layout.addWidget(hint)
        preview = QFrame()
        preview.setObjectName("preview")
        preview.setFixedHeight(210)
        preview_layout = QVBoxLayout(preview)
        self.preview_label = QLabel("Detecting cameras…")
        self.preview_label.setObjectName("muted")
        self.preview_label.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(self.preview_label)
        layout.addWidget(preview)
        self.combo = QComboBox()
        self.combo.currentIndexChanged.connect(self.start_preview)
        layout.addWidget(self.combo)
        actions = QHBoxLayout()
        rescan = QPushButton("Rescan")
        use = QPushButton("Use this camera")
        use.setObjectName("use")
        rescan.clicked.connect(self.scan_cameras)
        use.clicked.connect(self.use_camera)
        actions.addWidget(rescan)
        actions.addStretch()
        actions.addWidget(use)
        layout.addLayout(actions)
        self.scan_cameras()

    def scan_cameras(self):
        self.stop_preview()
        self.combo.blockSignals(True)
        self.combo.clear()
        cameras = find_named_cameras()
        for index, name in cameras:
            self.combo.addItem(name, index)
        self.combo.blockSignals(False)
        if cameras:
            self.start_preview()
        else:
            self.preview_label.setText("No camera detected.\n\nConnect a webcam or start Iriun Webcam, then choose Rescan.")

    def start_preview(self):
        index = self.combo.currentData()
        if index is None or cv2 is None:
            return
        self.stop_preview()
        backend = cv2.CAP_DSHOW if hasattr(cv2, "CAP_DSHOW") else cv2.CAP_ANY
        self.capture = cv2.VideoCapture(index, backend)
        if self.capture.isOpened():
            self.timer.start(30)
        else:
            self.preview_label.setText("Unable to open this camera.")
            self.stop_preview()

    def update_preview(self):
        if self.capture is None:
            return
        ok, frame = self.capture.read()
        if not ok:
            return
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channels = frame.shape
        image = QImage(frame.data, width, height, channels * width, QImage.Format_RGB888)
        self.preview_label.setPixmap(QPixmap.fromImage(image).scaled(
            self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def use_camera(self):
        if self.capture is not None and self.combo.currentData() is not None:
            self.selected_index = self.combo.currentData()
            self.selected_name = self.combo.currentText()
            self.stop_preview()
            self.accept()

    def stop_preview(self):
        self.timer.stop()
        if self.capture is not None:
            self.capture.release()
            self.capture = None

    def done(self, result):
        self.stop_preview()
        super().done(result)


class CameraSetupPage(QWidget):
    """A restrained sidebar page that opens the same compact camera picker."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setObjectName("cameraSetup")
        self.setStyleSheet("""
            QWidget#cameraSetup { background: #071426; }
            QLabel { background: transparent; color: #EEF4FF; }
            QLabel#heading { font-size: 25px; font-weight: 700; }
            QLabel#muted { color: #91A0BB; font-size: 13px; }
            QFrame#panel { background: #0F1E35; border: 1px solid #294263; border-radius: 14px; }
            QPushButton { background: #3E7CF7; color: white; border: none; border-radius: 8px; padding: 11px 18px; font-weight: 700; }
        """)
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(Sidebar(parent, "Camera Setup"))
        content = QWidget()
        body = QVBoxLayout(content)
        body.setContentsMargins(42, 36, 42, 36)
        body.addWidget(self._label("Camera Setup", "heading"))
        body.addWidget(self._label("Select or change your webcam without leaving GestureBoard.", "muted"))
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setFixedSize(520, 190)
        panel_layout = QVBoxLayout(panel)
        self.selected = self._label("No camera selected", "heading")
        self.selected.setStyleSheet("font-size: 18px; font-weight: 700;")
        choose = QPushButton("Choose a camera")
        choose.clicked.connect(self.open_picker)
        panel_layout.addStretch()
        panel_layout.addWidget(self.selected, 0, Qt.AlignCenter)
        panel_layout.addWidget(self._label("Use Iriun Webcam, a USB webcam, or your integrated webcam.", "muted"), 0, Qt.AlignCenter)
        panel_layout.addSpacing(8)
        panel_layout.addWidget(choose, 0, Qt.AlignCenter)
        panel_layout.addStretch()
        body.addSpacing(16)
        body.addWidget(panel)
        body.addStretch()
        root.addWidget(content, 1)

    @staticmethod
    def _label(text, name):
        label = QLabel(text)
        label.setObjectName(name)
        return label

    def open_picker(self):
        picker = CameraPickerDialog(self)
        picker.move(self.mapToGlobal(self.rect().topLeft()))
        if picker.exec_() and self.parent_window:
            self.parent_window.setActiveCamera(picker.selected_index, picker.selected_name)
            self.selected.setText(picker.selected_name)
