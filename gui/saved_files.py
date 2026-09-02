import os
import shutil
import subprocess
import sys
from pathlib import Path

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QIcon
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


class SavedFilesPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.main_window = parent
        self.current_filter = "All"

        # =========================================================
        # COLORS
        # =========================================================

        self.bg_color = "#F5FEFF"
        self.card_color = "#FFFFFF"
        self.preview_color = "#E5EFF8"
        self.primary = "#123A82"
        self.secondary = "#6384B8"
        self.light_blue = "#AFC7E8"
        self.border = "#D7E5F2"
        self.text = "#123A82"
        self.muted = "#7893BC"
        self.green = "#25C76F"
        self.red = "#FF4B4B"

        # =========================================================
        # MAIN LAYOUT
        # =========================================================

        self.setStyleSheet(
            f"""
            QWidget {{
                background-color: {self.bg_color};
                color: {self.text};
                font-family: "Segoe UI";
            }}

            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 4px;
            }}

            QScrollBar::handle:vertical {{
                background: #B8CCE5;
                border-radius: 4px;
                min-height: 40px;
            }}

            QScrollBar::handle:vertical:hover {{
                background: #8FAED3;
            }}

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            """
        )

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(
            40,
            30,
            40,
            30
        )
        self.main_layout.setSpacing(0)

        # =========================================================
        # HEADER
        # =========================================================

        self.header_layout = QVBoxLayout()
        self.header_layout.setSpacing(4)

        self.title = QLabel("Saved Files")

        title_font = QFont("Segoe UI", 22)
        title_font.setWeight(QFont.Bold)

        self.title.setFont(title_font)
        self.title.setStyleSheet(
            f"""
            color: {self.primary};
            background: transparent;
            """
        )

        self.subtitle = QLabel(
            "Manage annotations, whiteboards, and presentations you've saved."
        )

        self.subtitle.setStyleSheet(
            f"""
            color: {self.secondary};
            font-size: 13px;
            background: transparent;
            """
        )

        self.header_layout.addWidget(self.title)
        self.header_layout.addWidget(self.subtitle)

        self.main_layout.addLayout(self.header_layout)

        self.main_layout.addSpacing(25)

        # =========================================================
        # FILTER + SEARCH
        # =========================================================

        self.filter_layout = QHBoxLayout()
        self.filter_layout.setSpacing(10)

        self.all_button = self.create_filter_button(
            "All",
            active=True
        )

        self.annotation_button = self.create_filter_button(
            "Annotations"
        )

        self.whiteboard_button = self.create_filter_button(
            "Whiteboards"
        )

        self.presentation_button = self.create_filter_button(
            "Presentations"
        )

        self.filter_layout.addWidget(self.all_button)
        self.filter_layout.addWidget(self.annotation_button)
        self.filter_layout.addWidget(self.whiteboard_button)
        self.filter_layout.addWidget(self.presentation_button)

        self.filter_layout.addSpacing(20)

        # ---------------------------------------------------------
        # SEARCH
        # ---------------------------------------------------------

        self.search_box = QLineEdit()

        self.search_box.setPlaceholderText(
            "⌕  Search saved files..."
        )

        self.search_box.setFixedHeight(32)
        self.search_box.setMinimumWidth(240)
        self.search_box.setMaximumWidth(300)

        self.search_box.setStyleSheet(
            f"""
            QLineEdit {{
                background: #FFFFFF;
                border: 1px solid {self.light_blue};
                border-radius: 8px;
                padding-left: 12px;
                padding-right: 12px;
                color: {self.primary};
                font-size: 12px;
            }}

            QLineEdit:focus {{
                border: 1px solid #8BAED9;
            }}
            """
        )

        self.search_box.textChanged.connect(
            self.refresh_files
        )

        self.filter_layout.addWidget(
            self.search_box
        )

        self.filter_layout.addStretch()

        self.main_layout.addLayout(
            self.filter_layout
        )

        self.main_layout.addSpacing(25)

        # =========================================================
        # SCROLL AREA
        # =========================================================

        self.scroll_area = QScrollArea()

        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)

        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        self.scroll_area.setStyleSheet(
            """
            QScrollArea {
                background: transparent;
                border: none;
            }

            QWidget {
                background: transparent;
            }
            """
        )

        self.content_widget = QWidget()

        self.grid_layout = QGridLayout(
            self.content_widget
        )

        self.grid_layout.setContentsMargins(
            0,
            0,
            0,
            20
        )

        self.grid_layout.setHorizontalSpacing(14)
        self.grid_layout.setVerticalSpacing(14)

        self.scroll_area.setWidget(
            self.content_widget
        )

        self.main_layout.addWidget(
            self.scroll_area
        )

        # =========================================================
        # CREATE STORAGE FOLDERS
        # =========================================================

        self.base_folder = Path(
            os.path.join(
                os.getcwd(),
                "saved_files"
            )
        )

        self.annotation_folder = (
            self.base_folder / "annotations"
        )

        self.whiteboard_folder = (
            self.base_folder / "whiteboards"
        )

        self.presentation_folder = (
            self.base_folder / "presentations"
        )

        self.annotation_folder.mkdir(
            parents=True,
            exist_ok=True
        )

        self.whiteboard_folder.mkdir(
            parents=True,
            exist_ok=True
        )

        self.presentation_folder.mkdir(
            parents=True,
            exist_ok=True
        )

        # =========================================================
        # INITIAL FILES
        # =========================================================

        self.refresh_files()

    # =============================================================
    # FILTER BUTTON
    # =============================================================

    def create_filter_button(
        self,
        text,
        active=False
    ):

        button = QPushButton(text)

        button.setFixedHeight(32)

        if text == "All":
            button.setFixedWidth(42)
        else:
            button.setFixedWidth(95)

        button.setCursor(
            Qt.PointingHandCursor
        )

        button.clicked.connect(
            lambda checked=False, value=text:
            self.set_filter(value)
        )

        self.update_filter_button(
            button,
            active
        )

        return button

    # =============================================================
    # UPDATE FILTER BUTTON
    # =============================================================

    def update_filter_button(
        self,
        button,
        active
    ):

        if active:

            button.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {self.light_blue};
                    color: {self.primary};
                    border: none;
                    border-radius: 8px;
                    font-size: 12px;
                    font-weight: 600;
                }}

                QPushButton:hover {{
                    background-color: #9FBBDF;
                }}
                """
            )

        else:

            button.setStyleSheet(
                f"""
                QPushButton {{
                    background: transparent;
                    color: {self.secondary};
                    border: none;
                    border-radius: 8px;
                    font-size: 12px;
                }}

                QPushButton:hover {{
                    background-color: #E9F2FA;
                    color: {self.primary};
                }}
                """
            )

    # =============================================================
    # SET FILTER
    # =============================================================

    def set_filter(
        self,
        value
    ):

        self.current_filter = value

        self.update_filter_button(
            self.all_button,
            value == "All"
        )

        self.update_filter_button(
            self.annotation_button,
            value == "Annotations"
        )

        self.update_filter_button(
            self.whiteboard_button,
            value == "Whiteboards"
        )

        self.update_filter_button(
            self.presentation_button,
            value == "Presentations"
        )

        self.refresh_files()

    # =============================================================
    # GET ALL FILES
    # =============================================================

    def get_saved_files(self):

        files = []

        # ---------------------------------------------------------
        # ANNOTATIONS
        # ---------------------------------------------------------

        if self.annotation_folder.exists():

            for file in self.annotation_folder.iterdir():

                if file.is_file():

                    files.append(
                        {
                            "path": file,
                            "type": "Annotation"
                        }
                    )

        # ---------------------------------------------------------
        # WHITEBOARDS
        # ---------------------------------------------------------

        if self.whiteboard_folder.exists():

            for file in self.whiteboard_folder.iterdir():

                if file.is_file():

                    files.append(
                        {
                            "path": file,
                            "type": "Whiteboard"
                        }
                    )

        # ---------------------------------------------------------
        # PRESENTATIONS
        # ---------------------------------------------------------

        if self.presentation_folder.exists():

            for file in self.presentation_folder.iterdir():

                if file.is_file():

                    files.append(
                        {
                            "path": file,
                            "type": "Presentation"
                        }
                    )

        return files

    # =============================================================
    # FILTER FILES
    # =============================================================

    def filtered_files(self):

        files = self.get_saved_files()

        # ---------------------------------------------------------
        # TYPE FILTER
        # ---------------------------------------------------------

        if self.current_filter != "All":

            wanted_type = self.current_filter[:-1]

            files = [
                item
                for item in files
                if item["type"] == wanted_type
            ]

        # ---------------------------------------------------------
        # SEARCH
        # ---------------------------------------------------------

        search_text = (
            self.search_box.text()
            .strip()
            .lower()
        )

        if search_text:

            files = [
                item
                for item in files
                if search_text in
                item["path"].name.lower()
            ]

        # Newest first
        files.sort(
            key=lambda item:
            item["path"].stat().st_mtime,
            reverse=True
        )

        return files

    # =============================================================
    # REFRESH FILES
    # =============================================================

    def refresh_files(self):

        # Remove old cards
        while self.grid_layout.count():

            item = self.grid_layout.takeAt(0)

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        files = self.filtered_files()

        # ---------------------------------------------------------
        # EMPTY STATE
        # ---------------------------------------------------------

        if not files:

            empty = QLabel(
                "No saved files yet."
            )

            empty.setAlignment(
                Qt.AlignCenter
            )

            empty.setMinimumHeight(250)

            empty.setStyleSheet(
                f"""
                color: {self.muted};
                font-size: 14px;
                background: transparent;
                """
            )

            self.grid_layout.addWidget(
                empty,
                0,
                0,
                1,
                3
            )

            return

        # ---------------------------------------------------------
        # THREE COLUMNS
        # ---------------------------------------------------------

        for index, item in enumerate(files):

            row = index // 3
            column = index % 3

            card = self.create_file_card(
                item
            )

            self.grid_layout.addWidget(
                card,
                row,
                column
            )

        for column in range(3):

            self.grid_layout.setColumnStretch(
                column,
                1
            )

    # =============================================================
    # CREATE FILE CARD
    # =============================================================

    def create_file_card(
        self,
        item
    ):

        file_path = item["path"]
        file_type = item["type"]

        card = QFrame()

        card.setFixedHeight(220)

        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed
        )

        card.setStyleSheet(
            f"""
            QFrame {{
                background-color: {self.card_color};
                border: 1px solid {self.border};
                border-radius: 12px;
            }}
            """
        )

        card_layout = QVBoxLayout(card)

        card_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        card_layout.setSpacing(0)

        # =========================================================
        # PREVIEW
        # =========================================================

        preview = QFrame()

        preview.setFixedHeight(120)

        preview.setStyleSheet(
            f"""
            QFrame {{
                background-color: {self.preview_color};
                border: none;
                border-top-left-radius: 11px;
                border-top-right-radius: 11px;
            }}
            """
        )

        preview_layout = QVBoxLayout(
            preview
        )

        preview_layout.setAlignment(
            Qt.AlignCenter
        )

        # ---------------------------------------------------------
        # ICON
        # ---------------------------------------------------------

        icon_label = QLabel()

        icon_label.setFixedSize(
            44,
            44
        )

        icon_label.setAlignment(
            Qt.AlignCenter
        )

        icon = self.get_file_icon(
            file_type,
            file_path
        )

        icon_label.setText(
            icon
        )

        icon_label.setStyleSheet(
            """
            QLabel {
                background-color: #F7FCFF;
                border: none;
                border-radius: 12px;
                font-size: 23px;
            }
            """
        )

        preview_layout.addWidget(
            icon_label
        )

        card_layout.addWidget(
            preview
        )

        # =========================================================
        # INFORMATION
        # =========================================================

        info = QWidget()

        info_layout = QVBoxLayout(info)

        info_layout.setContentsMargins(
            14,
            10,
            14,
            8
        )

        info_layout.setSpacing(5)

        # ---------------------------------------------------------
        # FILE NAME
        # ---------------------------------------------------------

        name_label = QLabel(
            file_path.name
        )

        name_label.setToolTip(
            file_path.name
        )

        name_label.setStyleSheet(
            f"""
            QLabel {{
                color: {self.primary};
                font-size: 12px;
                font-weight: 600;
                background: transparent;
                border: none;
            }}
            """
        )

        # ---------------------------------------------------------
        # DETAILS
        # ---------------------------------------------------------

        details_layout = QHBoxLayout()

        details_layout.setSpacing(8)

        type_label = QLabel(
            file_type
        )

        type_label.setStyleSheet(
            f"""
            QLabel {{
                background-color: #E5EFF8;
                color: {self.secondary};
                border: none;
                border-radius: 5px;
                padding: 3px 7px;
                font-size: 9px;
            }}
            """
        )

        size_label = QLabel(
            self.get_file_size(
                file_path
            )
        )

        date_label = QLabel(
            self.get_file_date(
                file_path
            )
        )

        for label in [
            size_label,
            date_label
        ]:

            label.setStyleSheet(
                f"""
                QLabel {{
                    color: {self.muted};
                    font-size: 9px;
                    background: transparent;
                    border: none;
                }}
                """
            )

        details_layout.addWidget(
            type_label
        )

        details_layout.addWidget(
            date_label
        )

        details_layout.addWidget(
            size_label
        )

        details_layout.addStretch()

        # =========================================================
        # BUTTONS
        # =========================================================

        button_layout = QHBoxLayout()

        button_layout.setSpacing(6)

        open_button = self.create_action_button(
            "Open",
            primary=True
        )

        rename_button = self.create_action_button(
            "Rename"
        )

        delete_button = self.create_action_button(
            "Delete"
        )

        open_button.clicked.connect(
            lambda checked=False,
            path=file_path:
            self.open_file(path)
        )

        rename_button.clicked.connect(
            lambda checked=False,
            path=file_path:
            self.rename_file(path)
        )

        delete_button.clicked.connect(
            lambda checked=False,
            path=file_path:
            self.delete_file(path)
        )

        button_layout.addWidget(
            open_button
        )

        button_layout.addWidget(
            rename_button
        )

        button_layout.addWidget(
            delete_button
        )

        button_layout.addStretch()

        info_layout.addWidget(
            name_label
        )

        info_layout.addLayout(
            details_layout
        )

        info_layout.addLayout(
            button_layout
        )

        card_layout.addWidget(
            info
        )

        return card

    # =============================================================
    # ACTION BUTTON
    # =============================================================

    def create_action_button(
        self,
        text,
        primary=False
    ):

        button = QPushButton(text)

        button.setFixedHeight(26)

        if text == "Open":
            button.setFixedWidth(48)

        elif text == "Rename":
            button.setFixedWidth(58)

        else:
            button.setFixedWidth(52)

        button.setCursor(
            Qt.PointingHandCursor
        )

        if primary:

            button.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {self.light_blue};
                    color: {self.primary};
                    border: none;
                    border-radius: 6px;
                    font-size: 10px;
                    font-weight: 600;
                }}

                QPushButton:hover {{
                    background-color: #9EB9DF;
                }}
                """
            )

        else:

            button.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: #FFFFFF;
                    color: {self.primary};
                    border: 1px solid {self.light_blue};
                    border-radius: 6px;
                    font-size: 10px;
                }}

                QPushButton:hover {{
                    background-color: #EDF5FC;
                }}
                """
            )

        return button

    # =============================================================
    # FILE ICON
    # =============================================================

    def get_file_icon(
        self,
        file_type,
        file_path
    ):

        extension = file_path.suffix.lower()

        if file_type == "Presentation":

            if extension == ".pptx":
                return "▣"

            return "▤"

        if file_type == "Whiteboard":
            return "▱"

        if file_type == "Annotation":
            return "⌁"

        return "□"

    # =============================================================
    # FILE SIZE
    # =============================================================

    def get_file_size(
        self,
        path
    ):

        try:

            size = path.stat().st_size

            if size < 1024:
                return f"{size} B"

            if size < 1024 * 1024:
                return f"{size / 1024:.0f} KB"

            return f"{size / (1024 * 1024):.1f} MB"

        except Exception:

            return "Unknown size"

    # =============================================================
    # FILE DATE
    # =============================================================

    def get_file_date(
        self,
        path
    ):

        try:

            from datetime import datetime

            timestamp = path.stat().st_mtime

            date = datetime.fromtimestamp(
                timestamp
            )

            return date.strftime(
                "%b %d, %Y"
            )

        except Exception:

            return ""

    # =============================================================
    # OPEN FILE
    # =============================================================

    def open_file(
        self,
        path
    ):

        if not path.exists():

            QMessageBox.warning(
                self,
                "File Not Found",
                "This file no longer exists."
            )

            self.refresh_files()

            return

        try:

            if sys.platform.startswith("win"):

                os.startfile(
                    str(path)
                )

            elif sys.platform == "darwin":

                subprocess.Popen(
                    [
                        "open",
                        str(path)
                    ]
                )

            else:

                subprocess.Popen(
                    [
                        "xdg-open",
                        str(path)
                    ]
                )

        except Exception as e:

            QMessageBox.warning(
                self,
                "Unable to Open File",
                f"Could not open this file.\n\n{e}"
            )

    # =============================================================
    # RENAME FILE
    # =============================================================

    def rename_file(
        self,
        path
    ):

        if not path.exists():
            return

        current_name = path.stem

        new_name, ok = QInputDialog.getText(
            self,
            "Rename File",
            "Enter a new file name:",
            text=current_name
        )

        if not ok:
            return

        new_name = new_name.strip()

        if not new_name:
            return

        # Remove dangerous characters
        invalid_chars = [
            "\\",
            "/",
            ":",
            "*",
            "?",
            '"',
            "<",
            ">",
            "|"
        ]

        for char in invalid_chars:

            new_name = new_name.replace(
                char,
                ""
            )

        if not new_name:
            return

        new_path = path.parent / (
            new_name + path.suffix
        )

        if new_path.exists():

            QMessageBox.warning(
                self,
                "Rename Failed",
                "A file with that name already exists."
            )

            return

        try:

            path.rename(
                new_path
            )

            self.refresh_files()

        except Exception as e:

            QMessageBox.warning(
                self,
                "Rename Failed",
                f"Could not rename the file.\n\n{e}"
            )

    # =============================================================
    # DELETE FILE
    # =============================================================

    def delete_file(
        self,
        path
    ):

        if not path.exists():
            return

        answer = QMessageBox.question(
            self,
            "Delete File",
            f"Are you sure you want to delete:\n\n"
            f"{path.name}?",
            QMessageBox.Yes |
            QMessageBox.No,
            QMessageBox.No
        )

        if answer != QMessageBox.Yes:
            return

        try:

            path.unlink()

            self.refresh_files()

        except Exception as e:

            QMessageBox.warning(
                self,
                "Delete Failed",
                f"Could not delete the file.\n\n{e}"
            )

    # =============================================================
    # OPTIONAL: IMPORT FILE
    # =============================================================

    def import_file(self):

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Saved File",
            "",
            (
                "Supported Files "
                "(*.png *.jpg *.jpeg *.pdf *.pptx);;"
                "All Files (*.*)"
            )
        )

        if not file_path:
            return

        source = Path(
            file_path
        )

        extension = source.suffix.lower()

        # ---------------------------------------------------------
        # Determine destination
        # ---------------------------------------------------------

        if extension in [
            ".png",
            ".jpg",
            ".jpeg"
        ]:

            destination_folder = (
                self.annotation_folder
            )

        elif extension == ".pdf":

            destination_folder = (
                self.presentation_folder
            )

        elif extension == ".pptx":

            destination_folder = (
                self.presentation_folder
            )

        else:

            destination_folder = (
                self.annotation_folder
            )

        destination = (
            destination_folder /
            source.name
        )

        # Avoid overwrite
        counter = 1

        while destination.exists():

            destination = (
                destination_folder /
                f"{source.stem}_{counter}"
                f"{source.suffix}"
            )

            counter += 1

        try:

            shutil.copy2(
                source,
                destination
            )

            self.refresh_files()

        except Exception as e:

            QMessageBox.warning(
                self,
                "Import Failed",
                f"Could not import the file.\n\n{e}"
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