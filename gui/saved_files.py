import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt5.QtGui import QColor, QFontMetrics, QPainter, QPainterPath, QPen, QPixmap
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QScrollArea,
    QFrame,
    QMessageBox,
    QInputDialog,
    QSizePolicy,
    QFileDialog,
)

from settings import theme as app_theme
from widgets import page_background
from widgets.sidebar import nav_icon


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}

# Filter tab label -> file type stored on each item (None = everything)
FILTERS = [
    ("All files", None),
    ("Whiteboards", "Whiteboard"),
    ("Annotations", "Annotation"),
    ("Presentations", "Presentation"),
]

CARD_MIN_WIDTH = 250


def page_colors():
    """Shared page surfaces plus the few extra tones this page needs."""

    c = page_background.page_colors()

    if app_theme.is_dark():
        c.update(
            preview="#0F2038",
            danger="#F07167",
            danger_hover="#3A2230",
            tab_active_bg="#3E7CF7",
            tab_active_text="#0B1A30",
        )
    else:
        c.update(
            preview="#CFDFF0",
            danger="#B83227",
            danger_hover="#F3DCDA",
            tab_active_bg="#0E2F76",
            tab_active_text="#F5FEFF",
        )

    return c


# =================================================================
# ELIDED LABEL
# Long file names end in "..." instead of stretching the card.
# =================================================================

class ElidedLabel(QLabel):

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._full_text = text
        self.setToolTip(text)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)

    def paintEvent(self, event):
        painter = QPainter(self)
        metrics = QFontMetrics(self.font())
        text = metrics.elidedText(
            self._full_text, Qt.ElideRight, self.width()
        )
        painter.setPen(self.palette().color(self.foregroundRole()))
        painter.drawText(self.rect(), Qt.AlignLeft | Qt.AlignVCenter, text)


# =================================================================
# THUMBNAIL
# Shows the saved picture itself; other files get a line icon.
# =================================================================

class FileThumbnail(QWidget):

    clicked = pyqtSignal()

    def __init__(self, pixmap, icon_name, extension, colors, parent=None):
        super().__init__(parent)

        self._pixmap = pixmap
        self._icon_name = icon_name
        self._extension = extension
        self._colors = colors
        self._hover = False

        self.setFixedHeight(150)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Open file")

    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.pos()):
            self.clicked.emit()

    def paintEvent(self, event):
        c = self._colors
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        clip = QPainterPath()
        clip.addRoundedRect(rect, 8, 8)
        painter.setClipPath(clip)
        painter.fillRect(self.rect(), QColor(c["preview"]))

        if self._pixmap is not None and not self._pixmap.isNull():
            # Fill the frame, cropping the overflow evenly.
            scaled = self._pixmap.scaled(
                self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        else:
            icon = nav_icon(self._icon_name, c["text_secondary"], size=40).pixmap(40, 40)
            top = (self.height() - 40) // 2 - 10
            painter.drawPixmap((self.width() - 40) // 2, top, icon)

            painter.setPen(QColor(c["text_secondary"]))
            font = painter.font()
            font.setPointSize(9)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(
                QRectF(0, top + 48, self.width(), 20),
                Qt.AlignHCenter | Qt.AlignTop,
                f"{self._extension} file",
            )

        painter.setClipping(False)
        pen = QPen(QColor(c["primary"] if self._hover else c["card_border"]))
        pen.setWidthF(2 if self._hover else 1)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)


# =================================================================
# SAVED FILES PAGE
# =================================================================

class SavedFilesPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.main_window = parent
        self.current_filter = None
        self.columns = 3
        self.cards = []
        self.thumbnail_cache = {}
        self.colors = page_colors()

        self.setObjectName("savedFilesPage")
        self.setAttribute(Qt.WA_StyledBackground, True)

        # =========================================================
        # STORAGE FOLDERS
        # =========================================================

        self.base_folder = Path(os.getcwd()) / "saved_files"
        self.annotation_folder = self.base_folder / "annotations"
        self.whiteboard_folder = self.base_folder / "whiteboards"
        self.presentation_folder = self.base_folder / "presentations"

        for folder in (
            self.annotation_folder,
            self.whiteboard_folder,
            self.presentation_folder,
        ):
            folder.mkdir(parents=True, exist_ok=True)

        self.setup_ui()
        self.apply_theme()

    # =============================================================
    # UI
    # =============================================================

    def setup_ui(self):

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 30, 40, 24)
        main_layout.setSpacing(0)

        # ---------------------------------------------------------
        # HEADER: title on the left, folder actions on the right
        # ---------------------------------------------------------

        header = QHBoxLayout()
        header.setSpacing(10)

        titles = QVBoxLayout()
        titles.setSpacing(4)

        title = QLabel("Saved files")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "Drawings and slides you've saved in GestureBoard. "
            "Click a preview to open it."
        )
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)

        titles.addWidget(title)
        titles.addWidget(subtitle)

        header.addLayout(titles, 1)

        self.folder_button = QPushButton("Open folder")
        self.folder_button.setObjectName("secondaryButton")
        self.folder_button.setToolTip(str(self.base_folder))
        self.folder_button.clicked.connect(self.open_folder)

        self.add_button = QPushButton("Add a file")
        self.add_button.setObjectName("primaryButton")
        self.add_button.setToolTip("Copy an image, PDF or PowerPoint into Saved files")
        self.add_button.clicked.connect(self.import_file)

        for button in (self.folder_button, self.add_button):
            button.setCursor(Qt.PointingHandCursor)
            button.setFixedHeight(36)
            header.addWidget(button, 0, Qt.AlignTop)

        main_layout.addLayout(header)
        main_layout.addSpacing(22)

        # ---------------------------------------------------------
        # FILTER TABS + SEARCH
        # ---------------------------------------------------------

        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        self.filter_buttons = {}

        for label, file_type in FILTERS:
            button = QPushButton(label)
            button.setObjectName("filterTab")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setFixedHeight(34)
            button.clicked.connect(
                lambda checked=False, value=file_type: self.set_filter(value)
            )
            self.filter_buttons[file_type] = (button, label)
            toolbar.addWidget(button)

        toolbar.addStretch()

        self.search_box = QLineEdit()
        self.search_box.setObjectName("searchBox")
        self.search_box.setPlaceholderText("Search by file name")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.setFixedHeight(36)
        self.search_box.setMinimumWidth(220)
        self.search_box.setMaximumWidth(300)
        self.search_box.textChanged.connect(self.refresh_files)

        toolbar.addWidget(self.search_box)

        main_layout.addLayout(toolbar)
        main_layout.addSpacing(14)

        self.summary_label = QLabel()
        self.summary_label.setObjectName("summary")
        main_layout.addWidget(self.summary_label)
        main_layout.addSpacing(10)

        # ---------------------------------------------------------
        # CARD GRID
        # ---------------------------------------------------------

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("filesScroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.content_widget = QWidget()
        self.content_widget.setObjectName("filesContent")

        self.grid_layout = QGridLayout(self.content_widget)
        self.grid_layout.setContentsMargins(0, 0, 6, 20)
        self.grid_layout.setHorizontalSpacing(16)
        self.grid_layout.setVerticalSpacing(16)
        self.grid_layout.setAlignment(Qt.AlignTop)

        self.scroll_area.setWidget(self.content_widget)
        self.scroll_area.viewport().setAutoFillBackground(False)
        self.scroll_area.viewport().setObjectName("filesViewport")

        main_layout.addWidget(self.scroll_area, 1)

    # =============================================================
    # THEME
    # =============================================================

    def apply_theme(self):

        self.colors = c = page_colors()

        self.setStyleSheet(
            f"""
            QWidget#filesContent,
            QWidget#filesViewport,
            QScrollArea#filesScroll {{
                background: transparent;
                border: none;
            }}

            QLabel {{
                background: transparent;
                color: {c['text']};
                border: none;
            }}

            QLabel#pageTitle {{
                font-size: 25px;
                font-weight: 700;
            }}

            QLabel#pageSubtitle {{
                color: {c['text_secondary']};
                font-size: 13px;
            }}

            QLabel#summary {{
                color: {c['text_secondary']};
                font-size: 12px;
            }}

            QPushButton {{
                font-size: 13px;
                border-radius: 8px;
                padding: 0 16px;
            }}

            QPushButton:focus {{
                outline: none;
                border: 2px solid {c['accent']};
            }}

            QPushButton#primaryButton {{
                background-color: {c['primary']};
                color: {c['primary_text']};
                border: none;
                font-weight: 600;
            }}

            QPushButton#primaryButton:hover {{
                background-color: {c['sidebar_hover']};
            }}

            QPushButton#secondaryButton {{
                background-color: transparent;
                color: {c['text']};
                border: 1px solid {c['border']};
            }}

            QPushButton#secondaryButton:hover {{
                background-color: {c['button_hover']};
            }}

            QPushButton#filterTab {{
                background-color: transparent;
                color: {c['text_secondary']};
                border: 1px solid transparent;
                padding: 0 14px;
            }}

            QPushButton#filterTab:hover {{
                background-color: {c['button_hover']};
                color: {c['text']};
            }}

            QPushButton#filterTab:checked {{
                background-color: {c['tab_active_bg']};
                color: {c['tab_active_text']};
            }}

            QLineEdit#searchBox {{
                background-color: {c['input_bg']};
                color: {c['text']};
                border: 1px solid {c['input_border']};
                border-radius: 8px;
                padding: 0 12px;
                font-size: 13px;
            }}

            QLineEdit#searchBox:focus {{
                border: 2px solid {c['primary']};
            }}

            QFrame#fileCard {{
                background-color: {c['card']};
                border: 1px solid {c['card_border']};
                border-radius: 12px;
            }}

            QLabel#fileName {{
                font-size: 14px;
                font-weight: 600;
            }}

            QLabel#fileType {{
                background-color: {c['preview']};
                color: {c['text']};
                border-radius: 5px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 600;
            }}

            QLabel#fileMeta {{
                color: {c['text_secondary']};
                font-size: 11px;
            }}

            QPushButton#openButton {{
                background-color: {c['primary']};
                color: {c['primary_text']};
                border: none;
                font-weight: 600;
                font-size: 12px;
                padding: 0 18px;
            }}

            QPushButton#openButton:hover {{
                background-color: {c['sidebar_hover']};
            }}

            QPushButton#cardButton {{
                background-color: transparent;
                color: {c['text']};
                border: 1px solid {c['card_border']};
                font-size: 12px;
                padding: 0 12px;
            }}

            QPushButton#cardButton:hover {{
                background-color: {c['button_hover']};
            }}

            QPushButton#deleteButton {{
                background-color: transparent;
                color: {c['danger']};
                border: 1px solid transparent;
                font-size: 12px;
                padding: 0 10px;
            }}

            QPushButton#deleteButton:hover {{
                background-color: {c['danger_hover']};
            }}

            QFrame#emptyState {{
                background-color: {c['card']};
                border: 1px dashed {c['border']};
                border-radius: 14px;
            }}

            QLabel#emptyTitle {{
                font-size: 17px;
                font-weight: 700;
            }}

            QLabel#emptyBody {{
                color: {c['text_secondary']};
                font-size: 13px;
            }}

            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 4px 0;
            }}

            QScrollBar::handle:vertical {{
                background: {c['border']};
                border-radius: 4px;
                min-height: 40px;
            }}

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            """
        )

        self.refresh_files()
        self.update()

    # =============================================================
    # BACKGROUND
    # Whiteboard-style dot grid plus a large hand outline in the
    # bottom-right corner, so the empty space below the cards isn't bare.
    # =============================================================

    def paintEvent(self, event):

        page_background.paint_page_background(self, self.colors)

    # =============================================================
    # FILTER
    # =============================================================

    def set_filter(self, value):

        self.current_filter = value
        self.refresh_files()

    def update_filter_tabs(self, files):

        counts = {None: len(files)}

        for item in files:
            counts[item["type"]] = counts.get(item["type"], 0) + 1

        for file_type, (button, label) in self.filter_buttons.items():
            button.setText(f"{label}  {counts.get(file_type, 0)}")
            button.setChecked(file_type == self.current_filter)

    # =============================================================
    # GET ALL FILES
    # =============================================================

    def get_saved_files(self):

        files = []

        for folder, file_type in (
            (self.annotation_folder, "Annotation"),
            (self.whiteboard_folder, "Whiteboard"),
            (self.presentation_folder, "Presentation"),
        ):

            if not folder.exists():
                continue

            for file in folder.iterdir():

                if file.is_file():
                    files.append({"path": file, "type": file_type})

        return files

    # =============================================================
    # FILTER FILES
    # =============================================================

    def filtered_files(self, files):

        if self.current_filter is not None:
            files = [
                item for item in files
                if item["type"] == self.current_filter
            ]

        search_text = self.search_box.text().strip().lower()

        if search_text:
            files = [
                item for item in files
                if search_text in item["path"].name.lower()
            ]

        # Newest first
        files.sort(
            key=lambda item: self.safe_mtime(item["path"]),
            reverse=True
        )

        return files

    # =============================================================
    # REFRESH FILES
    # =============================================================

    def refresh_files(self, *_):

        self.clear_grid()

        all_files = self.get_saved_files()
        files = self.filtered_files(list(all_files))

        self.update_filter_tabs(all_files)
        self.update_summary(len(files), all_files)

        if not files:
            self.show_empty_state(all_files)
            return

        self.columns = self.column_count()
        self.cards = [self.create_file_card(item) for item in files]
        self.layout_cards()

    def clear_grid(self):

        while self.grid_layout.count():

            item = self.grid_layout.takeAt(0)
            widget = item.widget()

            if widget is not None:
                widget.hide()
                widget.deleteLater()

        for column in range(self.grid_layout.columnCount()):
            self.grid_layout.setColumnStretch(column, 0)

        self.cards = []

    def layout_cards(self):

        for column in range(self.grid_layout.columnCount()):
            self.grid_layout.setColumnStretch(column, 0)

        for index, card in enumerate(self.cards):
            self.grid_layout.addWidget(
                card,
                index // self.columns,
                index % self.columns
            )

        for column in range(self.columns):
            self.grid_layout.setColumnStretch(column, 1)

    def update_summary(self, shown, all_files):

        if self.current_filter is None:
            pool = len(all_files)
        else:
            pool = sum(1 for f in all_files if f["type"] == self.current_filter)

        search_text = self.search_box.text().strip()

        if search_text and pool:
            text = f"{shown} of {pool} {self.plural(pool)} match “{search_text}”"
        elif shown:
            text = f"{shown} {self.plural(shown)}, newest first"
        else:
            text = ""

        self.summary_label.setText(text)
        self.summary_label.setVisible(bool(text))

    @staticmethod
    def plural(count):
        return "file" if count == 1 else "files"

    # =============================================================
    # RESPONSIVE COLUMNS
    # =============================================================

    def column_count(self):

        # The viewport isn't sized until the page is shown; fall back to
        # the page width minus its side margins.
        width = self.scroll_area.viewport().width()

        if not self.isVisible() or width < 50:
            width = self.width() - 80

        return max(1, min(4, width // CARD_MIN_WIDTH))

    def resizeEvent(self, event):

        super().resizeEvent(event)

        columns = self.column_count()

        if columns != self.columns:
            self.columns = columns

            if self.cards:
                for card in self.cards:
                    self.grid_layout.removeWidget(card)
                self.layout_cards()

    def showEvent(self, event):

        # Pick up files saved while another page was open.
        super().showEvent(event)
        self.refresh_files()

    # =============================================================
    # EMPTY STATE
    # Says why the list is empty and what to do next.
    # =============================================================

    def show_empty_state(self, all_files):

        search_text = self.search_box.text().strip()

        if search_text:
            title = f"No files match “{search_text}”"
            body = "Check the spelling, or clear the search to see every file."
            action_text, action = "Clear search", self.search_box.clear
        elif all_files:
            label = self.filter_buttons[self.current_filter][1].lower()
            title = f"No {label} yet"
            body = "Files of this kind will appear here after you save one."
            action_text, action = "Show all files", lambda: self.set_filter(None)
        else:
            title = "Nothing saved yet"
            body = (
                "When you save a drawing on the Whiteboard, it shows up here.\n"
                "You can also add an image, PDF or PowerPoint from your computer."
            )
            if self.main_window is not None and hasattr(self.main_window, "showWhiteboard"):
                action_text, action = "Open Whiteboard", self.main_window.showWhiteboard
            else:
                action_text, action = "Add a file", self.import_file

        box = QFrame()
        box.setObjectName("emptyState")
        box.setMinimumHeight(260)

        layout = QVBoxLayout(box)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)

        icon = QLabel()
        icon.setAlignment(Qt.AlignCenter)
        icon.setPixmap(
            nav_icon("folder", self.colors["text_secondary"], size=44).pixmap(44, 44)
        )

        title_label = QLabel(title)
        title_label.setObjectName("emptyTitle")
        title_label.setAlignment(Qt.AlignCenter)

        body_label = QLabel(body)
        body_label.setObjectName("emptyBody")
        body_label.setAlignment(Qt.AlignCenter)
        body_label.setWordWrap(True)
        body_label.setMinimumWidth(420)

        button = QPushButton(action_text)
        button.setObjectName("primaryButton")
        button.setCursor(Qt.PointingHandCursor)
        button.setFixedHeight(36)
        button.clicked.connect(lambda checked=False: action())

        layout.addWidget(icon)
        layout.addSpacing(4)
        layout.addWidget(title_label)
        layout.addWidget(body_label)
        layout.addSpacing(10)
        layout.addWidget(button, 0, Qt.AlignCenter)

        self.grid_layout.addWidget(box, 0, 0, 1, max(1, self.columns))

        for column in range(max(1, self.columns)):
            self.grid_layout.setColumnStretch(column, 1)

    # =============================================================
    # CREATE FILE CARD
    # =============================================================

    def create_file_card(self, item):

        file_path = item["path"]
        file_type = item["type"]

        card = QFrame()
        card.setObjectName("fileCard")
        card.setMinimumWidth(CARD_MIN_WIDTH - 30)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 12)
        layout.setSpacing(0)

        # ---------------------------------------------------------
        # PREVIEW
        # ---------------------------------------------------------

        thumbnail = FileThumbnail(
            self.get_thumbnail(file_path),
            self.get_icon_name(file_type),
            file_path.suffix.lstrip(".").upper() or "Unknown",
            self.colors,
        )
        thumbnail.clicked.connect(
            lambda path=file_path: self.open_file(path)
        )

        layout.addWidget(thumbnail)
        layout.addSpacing(12)

        # ---------------------------------------------------------
        # NAME + DETAILS
        # ---------------------------------------------------------

        info = QVBoxLayout()
        info.setContentsMargins(4, 0, 4, 0)
        info.setSpacing(6)

        name_label = ElidedLabel(file_path.stem or file_path.name)
        name_label.setObjectName("fileName")
        name_label.setToolTip(file_path.name)

        details = QHBoxLayout()
        details.setSpacing(8)

        type_label = QLabel(file_type)
        type_label.setObjectName("fileType")

        meta_label = QLabel(
            f"{self.get_file_date(file_path)}, {self.get_file_size(file_path)}"
        )
        meta_label.setObjectName("fileMeta")

        details.addWidget(type_label)
        details.addWidget(meta_label)
        details.addStretch()

        info.addWidget(name_label)
        info.addLayout(details)

        layout.addLayout(info)
        layout.addSpacing(12)

        # ---------------------------------------------------------
        # ACTIONS: Open first, Delete set apart on the right
        # ---------------------------------------------------------

        actions = QHBoxLayout()
        actions.setContentsMargins(4, 0, 4, 0)
        actions.setSpacing(6)

        open_button = self.create_action_button("Open", "openButton")
        rename_button = self.create_action_button("Rename", "cardButton")
        delete_button = self.create_action_button("Delete", "deleteButton")

        open_button.clicked.connect(
            lambda checked=False, path=file_path: self.open_file(path)
        )
        rename_button.clicked.connect(
            lambda checked=False, path=file_path: self.rename_file(path)
        )
        delete_button.clicked.connect(
            lambda checked=False, path=file_path: self.delete_file(path)
        )

        actions.addWidget(open_button)
        actions.addWidget(rename_button)
        actions.addStretch()
        actions.addWidget(delete_button)

        layout.addLayout(actions)

        return card

    # =============================================================
    # ACTION BUTTON
    # =============================================================

    def create_action_button(self, text, object_name):

        button = QPushButton(text)
        button.setObjectName(object_name)
        button.setFixedHeight(32)
        button.setCursor(Qt.PointingHandCursor)

        return button

    # =============================================================
    # THUMBNAIL / ICON
    # =============================================================

    def get_thumbnail(self, path):

        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            return None

        key = (str(path), self.safe_mtime(path))

        if key not in self.thumbnail_cache:

            pixmap = QPixmap(str(path))

            # Keep memory low: a card never needs more than ~600px.
            if not pixmap.isNull() and pixmap.width() > 600:
                pixmap = pixmap.scaledToWidth(600, Qt.SmoothTransformation)

            self.thumbnail_cache[key] = pixmap

        return self.thumbnail_cache[key]

    def get_icon_name(self, file_type):

        return {
            "Whiteboard": "whiteboard",
            "Presentation": "presentation",
            "Annotation": "presentation",
        }.get(file_type, "folder")

    # =============================================================
    # FILE SIZE
    # =============================================================

    def get_file_size(self, path):

        try:
            size = path.stat().st_size

            if size < 1024:
                return f"{size} B"

            if size < 1024 * 1024:
                return f"{size / 1024:.0f} KB"

            return f"{size / (1024 * 1024):.1f} MB"

        except Exception:
            return "size unknown"

    # =============================================================
    # FILE DATE
    # "Today, 3:14 PM" reads faster than a full date.
    # =============================================================

    def get_file_date(self, path):

        try:
            date = datetime.fromtimestamp(path.stat().st_mtime)
        except Exception:
            return "Date unknown"

        today = datetime.now().date()
        time_text = date.strftime("%I:%M %p").lstrip("0")

        if date.date() == today:
            return f"Today, {time_text}"

        if date.date() == today - timedelta(days=1):
            return f"Yesterday, {time_text}"

        if date.year == today.year:
            return date.strftime("%b %d").replace(" 0", " ")

        return date.strftime("%b %d, %Y").replace(" 0", " ")

    @staticmethod
    def safe_mtime(path):

        try:
            return path.stat().st_mtime
        except Exception:
            return 0

    # =============================================================
    # OPEN FILE / FOLDER
    # =============================================================

    def open_path(self, path):

        if sys.platform.startswith("win"):
            os.startfile(str(path))

        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])

        else:
            subprocess.Popen(["xdg-open", str(path)])

    def open_file(self, path):

        if not path.exists():

            QMessageBox.warning(
                self,
                "File not found",
                f"{path.name} was moved or deleted outside GestureBoard. "
                "The list has been updated."
            )

            self.refresh_files()
            return

        try:
            self.open_path(path)

        except Exception as e:

            QMessageBox.warning(
                self,
                "Couldn't open file",
                f"No app on this computer could open {path.name}.\n\n{e}"
            )

    def open_folder(self):

        try:
            self.base_folder.mkdir(parents=True, exist_ok=True)
            self.open_path(self.base_folder)

        except Exception as e:

            QMessageBox.warning(
                self,
                "Couldn't open folder",
                f"The Saved files folder couldn't be opened.\n\n{e}"
            )

    # =============================================================
    # RENAME FILE
    # =============================================================

    def rename_file(self, path):

        if not path.exists():
            self.refresh_files()
            return

        new_name, ok = QInputDialog.getText(
            self,
            "Rename file",
            f"New name (the {path.suffix or 'file'} ending stays the same):",
            text=path.stem
        )

        if not ok:
            return

        # Characters Windows doesn't allow in file names
        for char in '\\/:*?"<>|':
            new_name = new_name.replace(char, "")

        new_name = new_name.strip()

        if not new_name or new_name == path.stem:
            return

        new_path = path.parent / (new_name + path.suffix)

        if new_path.exists():

            QMessageBox.warning(
                self,
                "Name already used",
                f"There's already a file called {new_path.name}. "
                "Pick a different name."
            )
            return

        try:
            path.rename(new_path)
            self.refresh_files()

        except Exception as e:

            QMessageBox.warning(
                self,
                "Couldn't rename file",
                f"{path.name} couldn't be renamed. "
                f"Close it in any other app and try again.\n\n{e}"
            )

    # =============================================================
    # DELETE FILE
    # =============================================================

    def delete_file(self, path):

        if not path.exists():
            self.refresh_files()
            return

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("Delete file")
        box.setText(f"Delete {path.name}?")
        box.setInformativeText(
            "It will be removed from your computer. This can't be undone."
        )

        delete_button = box.addButton("Delete file", QMessageBox.DestructiveRole)
        cancel_button = box.addButton("Cancel", QMessageBox.RejectRole)
        box.setDefaultButton(cancel_button)
        box.exec_()

        if box.clickedButton() is not delete_button:
            return

        try:
            path.unlink()
            self.refresh_files()

        except Exception as e:

            QMessageBox.warning(
                self,
                "Couldn't delete file",
                f"{path.name} couldn't be deleted. "
                f"Close it in any other app and try again.\n\n{e}"
            )

    # =============================================================
    # ADD (IMPORT) FILE
    # =============================================================

    def import_file(self):

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Add a file to Saved files",
            "",
            (
                "Images, PDFs and PowerPoints "
                "(*.png *.jpg *.jpeg *.pdf *.pptx);;"
                "All files (*.*)"
            )
        )

        if not file_path:
            return

        source = Path(file_path)
        extension = source.suffix.lower()

        if extension in (".pdf", ".pptx", ".ppt"):
            destination_folder = self.presentation_folder
        else:
            destination_folder = self.annotation_folder

        destination = destination_folder / source.name

        # Avoid overwrite
        counter = 1

        while destination.exists():
            destination = (
                destination_folder /
                f"{source.stem}_{counter}{source.suffix}"
            )
            counter += 1

        try:
            shutil.copy2(source, destination)
            self.refresh_files()

        except Exception as e:

            QMessageBox.warning(
                self,
                "Couldn't add file",
                f"{source.name} couldn't be copied into Saved files.\n\n{e}"
            )

    # =============================================================
    # CAMERA COMPATIBILITY
    # =============================================================

    def updateCameraName(
        self,
        name
    ):
        """
        Kept for compatibility with MainWindow.
        Saved Files does not need the camera name.
        """
        pass

    # =============================================================
    # ACTIVE CAMERA COMPATIBILITY
    # =============================================================

    def setActiveCamera(
        self,
        index,
        name
    ):
        """
        Kept for compatibility with MainWindow.
        """
        pass
