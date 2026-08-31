from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QSizeGrip,
    QWidget,
    QVBoxLayout,
    QStackedWidget
)
from PyQt5.QtCore import QEvent, QPoint, QRect, Qt

from widgets.sidebar import TitleBar

from gui.splash import SplashPage
from gui.tutorial import TutorialPage
from gui.camera_setup import CameraSetupPage
from gui.dashboard import DashboardPage


class MainWindow(QMainWindow):

    RESIZE_MARGIN = 8

    def __init__(self):
        super().__init__()

        # ======================================================
        # Window Settings
        # ======================================================

        self.setWindowTitle("GestureBoard")
        self.setMinimumSize(820, 600)
        self.active_camera_index = None
        self.active_camera_name = "No camera selected"
        self._resize_edges = Qt.Edges()
        self._resize_origin = QPoint()
        self._resize_geometry = QRect()

        # Remove the default Windows title bar
        self.setWindowFlags(Qt.FramelessWindowHint)

        # Light background
        self.setStyleSheet("""
            QMainWindow{
                background-color:#F4F6FB;
            }

            QWidget{
                background-color:#F4F6FB;
                color:#1F2430;
            }
        """)

        # ======================================================
        # Main Container
        # ======================================================

        self.central = QWidget()

        self.setCentralWidget(self.central)

        # Thin purple accent border around the frameless window (matches theme)
        self.central.setStyleSheet("""
            QWidget{
                background-color:#F4F6FB;
                color:#1F2430;
            }
            border: 1px solid #7C3AED;
        """)

        self.mainLayout = QVBoxLayout()

        self.mainLayout.setContentsMargins(0, 0, 0, 0)

        self.mainLayout.setSpacing(0)

        self.central.setLayout(self.mainLayout)

        # Visible bottom-right adjuster for users who restore the window from
        # full screen and prefer a clear resize handle.
        self.size_grip = QSizeGrip(self.central)
        self.size_grip.setFixedSize(18, 18)
        self.size_grip.setStyleSheet("background: transparent;")

        # ======================================================
        # Custom Title Bar
        # ======================================================

        self.titlebar = TitleBar(self)

        self.mainLayout.addWidget(self.titlebar)

        # ======================================================
        # Page Container
        # ======================================================

        self.stack = QStackedWidget()

        self.stack.setObjectName("MainStack")

        self.mainLayout.addWidget(self.stack)
        self.mainLayout.setStretch(1, 1)

        # ======================================================
        # Pages
        # ======================================================

        self.splash = SplashPage(self)

        self.tutorial = TutorialPage(self)

        self.camera_setup = CameraSetupPage(self)
        self.dashboard = DashboardPage(self)

        # ======================================================
        # Add Pages
        # ======================================================

        self.stack.addWidget(self.splash)

        self.stack.addWidget(self.tutorial)

        self.stack.addWidget(self.camera_setup)
        self.stack.addWidget(self.dashboard)

        # ======================================================
        # First Page
        # ======================================================

        self.stack.setCurrentWidget(self.splash)

        # A frameless window has no native Windows resize border. Monitor mouse
        # events from every child widget so its edges and corners can resize.
        QApplication.instance().installEventFilter(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "size_grip"):
            self.size_grip.move(
                self.central.width() - self.size_grip.width() - 2,
                self.central.height() - self.size_grip.height() - 2,
            )
            self.size_grip.raise_()

    def _edges_at(self, global_position):
        if self.isMaximized():
            return Qt.Edges()
        local = self.mapFromGlobal(global_position)
        rect = self.rect()
        margin = self.RESIZE_MARGIN
        edges = Qt.Edges()
        if local.x() <= margin:
            edges |= Qt.LeftEdge
        elif local.x() >= rect.width() - margin:
            edges |= Qt.RightEdge
        if local.y() <= margin:
            edges |= Qt.TopEdge
        elif local.y() >= rect.height() - margin:
            edges |= Qt.BottomEdge
        return edges

    @staticmethod
    def _cursor_for_edges(edges):
        if edges in (Qt.LeftEdge | Qt.TopEdge, Qt.RightEdge | Qt.BottomEdge):
            return Qt.SizeFDiagCursor
        if edges in (Qt.RightEdge | Qt.TopEdge, Qt.LeftEdge | Qt.BottomEdge):
            return Qt.SizeBDiagCursor
        if edges & (Qt.LeftEdge | Qt.RightEdge):
            return Qt.SizeHorCursor
        if edges & (Qt.TopEdge | Qt.BottomEdge):
            return Qt.SizeVerCursor
        return Qt.ArrowCursor

    def _resize_window(self, global_position):
        delta = global_position - self._resize_origin
        geometry = QRect(self._resize_geometry)
        if self._resize_edges & Qt.LeftEdge:
            geometry.setLeft(geometry.left() + delta.x())
        if self._resize_edges & Qt.RightEdge:
            geometry.setRight(geometry.right() + delta.x())
        if self._resize_edges & Qt.TopEdge:
            geometry.setTop(geometry.top() + delta.y())
        if self._resize_edges & Qt.BottomEdge:
            geometry.setBottom(geometry.bottom() + delta.y())
        geometry.setWidth(max(self.minimumWidth(), geometry.width()))
        geometry.setHeight(max(self.minimumHeight(), geometry.height()))
        self.setGeometry(geometry)

    def eventFilter(self, watched, event):
        if not isinstance(watched, QWidget) or watched.window() is not self:
            return super().eventFilter(watched, event)
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            edges = self._edges_at(event.globalPos())
            if edges:
                self._resize_edges = edges
                self._resize_origin = event.globalPos()
                self._resize_geometry = self.geometry()
                return True
        elif event.type() == QEvent.MouseMove:
            if self._resize_edges:
                if event.buttons() & Qt.LeftButton:
                    self._resize_window(event.globalPos())
                    return True
                self._resize_edges = Qt.Edges()
            watched.setCursor(self._cursor_for_edges(self._edges_at(event.globalPos())))
        elif event.type() == QEvent.MouseButtonRelease and self._resize_edges:
            self._resize_edges = Qt.Edges()
            watched.setCursor(self._cursor_for_edges(self._edges_at(event.globalPos())))
            return True
        return super().eventFilter(watched, event)

# ======================================================
    # Navigation
    # ======================================================

    def showSplash(self):
        self.stack.setCurrentWidget(self.splash)

    def showTutorial(self):
        self.stack.setCurrentWidget(self.tutorial)

    def showHome(self):
        self.showDashboard()

    def showCameraSetup(self):
        self.camera_setup.refresh_cameras()
        self.stack.setCurrentWidget(self.camera_setup)

    def showDashboard(self):
        self.dashboard.updateCameraName(self.active_camera_name)
        self.dashboard.setActivePage("Home")
        self.stack.setCurrentWidget(self.dashboard)

    def showPresentation(self):
        self.dashboard.setActivePage("Presentation Control")
        self.stack.setCurrentWidget(self.dashboard)

    def showVirtualMouse(self):
        self.dashboard.setActivePage("Virtual Mouse")
        self.stack.setCurrentWidget(self.dashboard)

    def showWhiteboard(self):
        self.dashboard.setActivePage("Whiteboard")
        self.stack.setCurrentWidget(self.dashboard)

    def showAnnotation(self):
        self.dashboard.setActivePage("Annotation")
        self.stack.setCurrentWidget(self.dashboard)

    def showSavedFiles(self):
        self.dashboard.setActivePage("Saved Files")
        self.stack.setCurrentWidget(self.dashboard)

    def showSettings(self):
        self.dashboard.setActivePage("Settings")
        self.stack.setCurrentWidget(self.dashboard)

    def setActiveCamera(self, index, name):
        self.active_camera_index = index
        self.active_camera_name = name
        self.dashboard.setActiveCamera(name)
        import settings.preferences as prefs
        prefs.set_camera(index, name)
