from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QSizeGrip,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
)

from PyQt5.QtCore import QEvent, QPoint, QRect, Qt

from widgets.sidebar import TitleBar, Sidebar

from gui.splash import SplashPage
from gui.tutorial import TutorialPage
from gui.camera_setup import CameraSetupPage
from gui.dashboard import DashboardPage

# Feature pages
from gui.presentation import PresentationPage
from gui.virtual_mouse import VirtualMousePage
from gui.whiteboard import WhiteboardPage
from gui.annotation import AnnotationPage
from gui.saved_files import SavedFilesPage
from gui.settings import SettingsPage


class MainWindow(QMainWindow):

    RESIZE_MARGIN = 8

    def __init__(self):
        super().__init__()

        # ==========================================================
        # WINDOW SETTINGS
        # ==========================================================

        self.setWindowTitle("GestureBoard")
        self.setMinimumSize(1100, 700)

        self.active_camera_index = None
        self.active_camera_name = "No camera selected"

        # Current page name
        self.current_page = "Home"

        # Resize variables
        self._resize_edges = Qt.Edges()
        self._resize_origin = QPoint()
        self._resize_geometry = QRect()

        # Frameless window
        self.setWindowFlags(Qt.FramelessWindowHint)

        # ==========================================================
        # WINDOW STYLE
        # ==========================================================

        self.setStyleSheet("""
            QMainWindow {
                background-color: #F5FEFF;
            }

            QWidget {
                background-color: #F5FEFF;
                color: #0E2F76;
            }
        """)

        # ==========================================================
        # CENTRAL WIDGET
        # ==========================================================

        self.central = QWidget()
        self.central.setObjectName("CentralWidget")

        self.central.setStyleSheet("""
            QWidget#CentralWidget {
                background-color: #F5FEFF;
                border: 1px solid #AAC0E1;
            }
        """)

        self.setCentralWidget(self.central)

        self.mainLayout = QVBoxLayout(self.central)

        self.mainLayout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        self.mainLayout.setSpacing(0)

        # ==========================================================
        # TITLE BAR
        # ==========================================================

        self.titlebar = TitleBar(self)

        self.mainLayout.addWidget(
            self.titlebar
        )

        # ==========================================================
        # MAIN BODY
        #
        # SIDEBAR | PAGE
        # ==========================================================

        self.body = QWidget()

        self.body.setStyleSheet("""
            QWidget {
                background-color: #F5FEFF;
            }
        """)

        self.bodyLayout = QHBoxLayout(
            self.body
        )

        self.bodyLayout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        self.bodyLayout.setSpacing(0)

        self.mainLayout.addWidget(
            self.body
        )

        # ==========================================================
        # SIDEBAR
        # ==========================================================

        self.sidebar = Sidebar(self)

        self.sidebar.setFixedWidth(212)

        self.bodyLayout.addWidget(
            self.sidebar
        )

        # ==========================================================
        # STACKED PAGE CONTAINER
        # ==========================================================

        self.stack = QStackedWidget()

        self.stack.setObjectName(
            "MainStack"
        )

        self.stack.setStyleSheet("""
            QStackedWidget#MainStack {
                background-color: #F5FEFF;
                border: none;
            }
        """)

        self.bodyLayout.addWidget(
            self.stack,
            1
        )

        # ==========================================================
        # RESIZE GRIP
        # ==========================================================

        self.size_grip = QSizeGrip(
            self.central
        )

        self.size_grip.setFixedSize(
            18,
            18
        )

        self.size_grip.setStyleSheet(
            "background: transparent; border: none;"
        )

        # ==========================================================
        # CREATE STARTUP PAGES
        # ==========================================================

        self.splash = SplashPage(self)

        self.tutorial = TutorialPage(self)

        self.camera_setup = CameraSetupPage(self)

        # ==========================================================
        # CREATE DASHBOARD
        # ==========================================================

        self.dashboard = DashboardPage(self)

        # ==========================================================
        # CREATE FEATURE PAGES
        # ==========================================================

        self.presentation = PresentationPage(self)

        self.virtual_mouse = VirtualMousePage(self)

        self.whiteboard = WhiteboardPage(self)

        self.annotation = AnnotationPage(self)

        self.saved_files = SavedFilesPage(self)

        self.settings = SettingsPage(self)

        # ==========================================================
        # ADD PAGES TO STACK
        # ==========================================================

        self.stack.addWidget(
            self.splash
        )

        self.stack.addWidget(
            self.tutorial
        )

        self.stack.addWidget(
            self.camera_setup
        )

        self.stack.addWidget(
            self.dashboard
        )

        self.stack.addWidget(
            self.presentation
        )

        self.stack.addWidget(
            self.virtual_mouse
        )

        self.stack.addWidget(
            self.whiteboard
        )

        self.stack.addWidget(
            self.annotation
        )

        self.stack.addWidget(
            self.saved_files
        )

        self.stack.addWidget(
            self.settings
        )

        # ==========================================================
        # INITIAL PAGE
        # ==========================================================

        self.stack.setCurrentWidget(
            self.splash
        )

        # Hide sidebar during splash/tutorial
        self.sidebar.hide()

        # ==========================================================
        # WINDOW EVENT FILTER
        # ==========================================================

        QApplication.instance().installEventFilter(
            self
        )

    # ==============================================================
    # RESIZE EVENT
    # ==============================================================

    def resizeEvent(self, event):

        super().resizeEvent(event)

        if hasattr(self, "size_grip"):

            self.size_grip.move(
                self.central.width()
                - self.size_grip.width()
                - 2,

                self.central.height()
                - self.size_grip.height()
                - 2
            )

            self.size_grip.raise_()

    # ==============================================================
    # DETECT RESIZE EDGES
    # ==============================================================

    def _edges_at(self, global_position):

        if self.isMaximized():
            return Qt.Edges()

        local = self.mapFromGlobal(
            global_position
        )

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

    # ==============================================================
    # RESIZE CURSOR
    # ==============================================================

    @staticmethod
    def _cursor_for_edges(edges):

        if edges in (
            Qt.LeftEdge | Qt.TopEdge,
            Qt.RightEdge | Qt.BottomEdge
        ):

            return Qt.SizeFDiagCursor

        if edges in (
            Qt.RightEdge | Qt.TopEdge,
            Qt.LeftEdge | Qt.BottomEdge
        ):

            return Qt.SizeBDiagCursor

        if edges & (
            Qt.LeftEdge | Qt.RightEdge
        ):

            return Qt.SizeHorCursor

        if edges & (
            Qt.TopEdge | Qt.BottomEdge
        ):

            return Qt.SizeVerCursor

        return Qt.ArrowCursor

    # ==============================================================
    # RESIZE WINDOW
    # ==============================================================

    def _resize_window(
        self,
        global_position
    ):

        delta = (
            global_position
            - self._resize_origin
        )

        geometry = QRect(
            self._resize_geometry
        )

        if self._resize_edges & Qt.LeftEdge:

            geometry.setLeft(
                geometry.left()
                + delta.x()
            )

        if self._resize_edges & Qt.RightEdge:

            geometry.setRight(
                geometry.right()
                + delta.x()
            )

        if self._resize_edges & Qt.TopEdge:

            geometry.setTop(
                geometry.top()
                + delta.y()
            )

        if self._resize_edges & Qt.BottomEdge:

            geometry.setBottom(
                geometry.bottom()
                + delta.y()
            )

        geometry.setWidth(
            max(
                self.minimumWidth(),
                geometry.width()
            )
        )

        geometry.setHeight(
            max(
                self.minimumHeight(),
                geometry.height()
            )
        )

        self.setGeometry(
            geometry
        )

    # ==============================================================
    # EVENT FILTER
    # ==============================================================

    def eventFilter(
        self,
        watched,
        event
    ):

        if (
            not isinstance(watched, QWidget)
            or watched.window() is not self
        ):

            return super().eventFilter(
                watched,
                event
            )

        # ----------------------------------------------------------
        # MOUSE PRESS
        # ----------------------------------------------------------

        if (
            event.type()
            == QEvent.MouseButtonPress
            and event.button()
            == Qt.LeftButton
        ):

            edges = self._edges_at(
                event.globalPos()
            )

            if edges:

                self._resize_edges = edges

                self._resize_origin = (
                    event.globalPos()
                )

                self._resize_geometry = (
                    self.geometry()
                )

                return True

        # ----------------------------------------------------------
        # MOUSE MOVE
        # ----------------------------------------------------------

        elif event.type() == QEvent.MouseMove:

            if self._resize_edges:

                if event.buttons() & Qt.LeftButton:

                    self._resize_window(
                        event.globalPos()
                    )

                    return True

                self._resize_edges = (
                    Qt.Edges()
                )

            watched.setCursor(
                self._cursor_for_edges(
                    self._edges_at(
                        event.globalPos()
                    )
                )
            )

        # ----------------------------------------------------------
        # MOUSE RELEASE
        # ----------------------------------------------------------

        elif (
            event.type()
            == QEvent.MouseButtonRelease
            and self._resize_edges
        ):

            self._resize_edges = (
                Qt.Edges()
            )

            watched.setCursor(
                self._cursor_for_edges(
                    self._edges_at(
                        event.globalPos()
                    )
                )
            )

            return True

        return super().eventFilter(
            watched,
            event
        )

    # ==============================================================
    # SIDEBAR
    # ==============================================================

    def showSidebar(self):

        if not self.sidebar.isVisible():

            self.sidebar.show()

    # --------------------------------------------------------------

    def hideSidebar(self):

        if self.sidebar.isVisible():

            self.sidebar.hide()

    # ==============================================================
    # ACTIVE SIDEBAR PAGE
    # ==============================================================

    def setActivePage(self, page_name):

        """
        Updates the active page indicator in the sidebar.

        Example:

            setActivePage("Home")
            setActivePage("Annotation")
            setActivePage("Settings")
        """

        self.current_page = page_name

        # ----------------------------------------------------------
        # Tell Sidebar about the active page
        # ----------------------------------------------------------

        try:

            if hasattr(
                self.sidebar,
                "setActivePage"
            ):

                self.sidebar.setActivePage(
                    page_name
                )

        except Exception as e:

            print(
                f"Sidebar active page warning: {e}"
            )

        # ----------------------------------------------------------
        # Alternative method names
        # ----------------------------------------------------------

        try:

            if hasattr(
                self.sidebar,
                "updateActivePage"
            ):

                self.sidebar.updateActivePage(
                    page_name
                )

        except Exception:
            pass

        # ----------------------------------------------------------
        # If Sidebar stores active_page directly
        # ----------------------------------------------------------

        try:

            self.sidebar.active_page = page_name

        except Exception:
            pass

        # ----------------------------------------------------------
        # If Sidebar has navigation buttons
        # ----------------------------------------------------------

        try:

            if hasattr(
                self.sidebar,
                "update_navigation"
            ):

                self.sidebar.update_navigation(
                    page_name
                )

        except Exception:
            pass

    # ==============================================================
    # STARTUP NAVIGATION
    # ==============================================================

    def showSplash(self):

        self.hideSidebar()

        self.current_page = "Splash"

        self.stack.setCurrentWidget(
            self.splash
        )

    # --------------------------------------------------------------

    def showTutorial(self):

        self.hideSidebar()

        self.current_page = "Tutorial"

        self.stack.setCurrentWidget(
            self.tutorial
        )

    # --------------------------------------------------------------

    def showCameraSetup(self):

        # Sidebar must be visible
        self.showSidebar()

        # Active sidebar item
        self.setActivePage(
            "Camera Setup"
        )

        # Refresh available cameras
        try:

            self.camera_setup.refresh_cameras()

        except Exception as e:

            print(
                f"Camera refresh warning: {e}"
            )

        self.stack.setCurrentWidget(
            self.camera_setup
        )

    # ==============================================================
    # HOME / DASHBOARD
    # ==============================================================

    def showHome(self):

        """
        HOME always opens the Dashboard.

        The sidebar stays visible.
        """

        self.showDashboard()

    # --------------------------------------------------------------

    def showDashboard(self):

        print(
            "Opening Dashboard..."
        )

        # Show sidebar
        self.showSidebar()

        # Mark HOME as active
        self.setActivePage(
            "Home"
        )

        # Update camera
        try:

            self.dashboard.updateCameraName(
                self.active_camera_name
            )

        except Exception:

            pass

        # Update dashboard active page
        try:

            self.dashboard.setActivePage(
                "Home"
            )

        except Exception:

            pass

        # Show dashboard
        self.stack.setCurrentWidget(
            self.dashboard
        )

        self.stack.raise_()

    # ==============================================================
    # PRESENTATION CONTROL
    # ==============================================================

    def showPresentation(self):

        print(
            "Opening Presentation Control..."
        )

        # Keep sidebar visible
        self.showSidebar()

        # IMPORTANT:
        # Change active sidebar item
        self.setActivePage(
            "Presentation Control"
        )

        # Update dashboard if needed
        try:

            self.dashboard.setActivePage(
                "Presentation Control"
            )

        except Exception:

            pass

        # Update camera
        try:

            if hasattr(
                self.presentation,
                "updateCameraName"
            ):

                self.presentation.updateCameraName(
                    self.active_camera_name
                )

        except Exception:
            pass

        # Update actual page
        self.stack.setCurrentWidget(
            self.presentation
        )

        self.stack.raise_()

    # ==============================================================
    # VIRTUAL MOUSE
    # ==============================================================

    def showVirtualMouse(self):

        print(
            "Opening Virtual Mouse..."
        )

        # Keep sidebar visible
        self.showSidebar()

        # Active sidebar item
        self.setActivePage(
            "Virtual Mouse"
        )

        # Update camera
        try:

            if hasattr(
                self.virtual_mouse,
                "updateCameraName"
            ):

                self.virtual_mouse.updateCameraName(
                    self.active_camera_name
                )

        except Exception:
            pass

        # Show page
        self.stack.setCurrentWidget(
            self.virtual_mouse
        )

        self.stack.raise_()

    # ==============================================================
    # WHITEBOARD
    # ==============================================================

    def showWhiteboard(self):

        print(
            "Opening Whiteboard..."
        )

        # Keep sidebar visible
        self.showSidebar()

        # Active sidebar item
        self.setActivePage(
            "Whiteboard"
        )

        # Update camera
        try:

            if hasattr(
                self.whiteboard,
                "updateCameraName"
            ):

                self.whiteboard.updateCameraName(
                    self.active_camera_name
                )

        except Exception:
            pass

        # Show page
        self.stack.setCurrentWidget(
            self.whiteboard
        )

        self.stack.raise_()

    # ==============================================================
    # ANNOTATION
    # ==============================================================

    def showAnnotation(self):

        print(
            "Opening Annotation..."
        )

        # Keep sidebar visible
        self.showSidebar()

        # IMPORTANT:
        # Annotation is now the active page
        self.setActivePage(
            "Annotation"
        )

        # Update camera if supported
        try:

            if hasattr(
                self.annotation,
                "updateCameraName"
            ):

                self.annotation.updateCameraName(
                    self.active_camera_name
                )

        except Exception:
            pass

        # Show annotation page
        self.stack.setCurrentWidget(
            self.annotation
        )

        self.stack.raise_()

    # ==============================================================
    # SAVED FILES
    # ==============================================================

    def showSavedFiles(self):

        print(
            "Opening Saved Files..."
        )

        # Keep sidebar visible
        self.showSidebar()

        # Active sidebar item
        self.setActivePage(
            "Saved Files"
        )

        # Show page
        self.stack.setCurrentWidget(
            self.saved_files
        )

        self.stack.raise_()

    # ==============================================================
    # SETTINGS
    # ==============================================================

    def showSettings(self):

        print(
            "Opening Settings..."
        )

        # Keep sidebar visible
        self.showSidebar()

        # Active sidebar item
        self.setActivePage(
            "Settings"
        )

        # Show page
        self.stack.setCurrentWidget(
            self.settings
        )

        self.stack.raise_()

    # ==============================================================
    # CAMERA
    # ==============================================================

    def setActiveCamera(
        self,
        index,
        name
    ):

        self.active_camera_index = index

        self.active_camera_name = name

        print(
            f"Active camera: {name} "
            f"(index {index})"
        )

        # ----------------------------------------------------------
        # Dashboard
        # ----------------------------------------------------------

        try:

            if hasattr(
                self.dashboard,
                "setActiveCamera"
            ):

                self.dashboard.setActiveCamera(
                    name
                )

            elif hasattr(
                self.dashboard,
                "updateCameraName"
            ):

                self.dashboard.updateCameraName(
                    name
                )

        except Exception as e:

            print(
                f"Dashboard camera warning: {e}"
            )

        # ----------------------------------------------------------
        # Presentation
        # ----------------------------------------------------------

        try:

            if hasattr(
                self.presentation,
                "setActiveCamera"
            ):

                self.presentation.setActiveCamera(
                    index,
                    name
                )

        except Exception as e:

            print(
                f"Presentation camera warning: {e}"
            )

        # ----------------------------------------------------------
        # Virtual Mouse
        # ----------------------------------------------------------

        try:

            if hasattr(
                self.virtual_mouse,
                "setActiveCamera"
            ):

                self.virtual_mouse.setActiveCamera(
                    index,
                    name
                )

        except Exception as e:

            print(
                f"Virtual mouse camera warning: {e}"
            )

        # ----------------------------------------------------------
        # Whiteboard
        # ----------------------------------------------------------

        try:

            if hasattr(
                self.whiteboard,
                "setActiveCamera"
            ):

                self.whiteboard.setActiveCamera(
                    index,
                    name
                )

        except Exception as e:

            print(
                f"Whiteboard camera warning: {e}"
            )

        # ----------------------------------------------------------
        # Annotation
        # ----------------------------------------------------------

        try:

            if hasattr(
                self.annotation,
                "setActiveCamera"
            ):

                self.annotation.setActiveCamera(
                    index,
                    name
                )

        except Exception as e:

            print(
                f"Annotation camera warning: {e}"
            )

        # ----------------------------------------------------------
        # Camera Setup
        # ----------------------------------------------------------

        try:

            if hasattr(
                self.camera_setup,
                "setActiveCamera"
            ):

                self.camera_setup.setActiveCamera(
                    index,
                    name
                )

        except Exception:
            pass

        # ----------------------------------------------------------
        # Save Camera Preference
        # ----------------------------------------------------------

        try:

            import settings.preferences as prefs

            prefs.set_camera(
                index,
                name
            )

        except Exception as e:

            print(
                "Warning: Could not save "
                f"camera preference: {e}"
            )