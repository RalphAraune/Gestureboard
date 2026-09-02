import os

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import (
    QPainter,
    QPen,
    QColor,
    QPixmap,
    QImage
)
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QFrame,
    QSizePolicy
)

try:
    import fitz
except ImportError:
    fitz = None


# ============================================================
# DRAWING CANVAS
# ============================================================

class AnnotationCanvas(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMinimumSize(600, 400)
        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )

        self.setMouseTracking(True)

        # ----------------------------------------------------
        # Canvas
        # ----------------------------------------------------

        self.background = QColor("#E4EEF7")

        self.image = QImage(
            1200,
            700,
            QImage.Format_ARGB32
        )

        self.image.fill(self.background)

        # ----------------------------------------------------
        # Drawing settings
        # ----------------------------------------------------

        self.tool = "pen"

        self.pen_color = QColor("#132B5C")

        self.pen_width = 4

        self.highlighter_width = 20

        self.eraser_width = 25

        self.opacity = 255

        # ----------------------------------------------------
        # Mouse state
        # ----------------------------------------------------

        self.drawing = False

        self.last_point = QPoint()

        # ----------------------------------------------------
        # Undo / redo
        # ----------------------------------------------------

        self.undo_stack = []

        self.redo_stack = []

        self.save_state()


    # ========================================================
    # PAINT
    # ========================================================

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.Antialiasing
        )

        target_rect = self.rect()

        source_rect = self.image.rect()

        painter.drawImage(
            target_rect,
            self.image,
            source_rect
        )

        painter.end()


    # ========================================================
    # RESIZE
    # ========================================================

    def resizeEvent(self, event):

        if self.image.size() != self.size():

            old_image = self.image

            new_image = QImage(
                max(1, self.width()),
                max(1, self.height()),
                QImage.Format_ARGB32
            )

            new_image.fill(self.background)

            painter = QPainter(new_image)

            painter.drawImage(
                0,
                0,
                old_image
            )

            painter.end()

            self.image = new_image

        super().resizeEvent(event)


    # ========================================================
    # SAVE STATE
    # ========================================================

    def save_state(self):

        self.undo_stack.append(
            self.image.copy()
        )

        if len(self.undo_stack) > 30:
            self.undo_stack.pop(0)

        self.redo_stack.clear()


    # ========================================================
    # MOUSE PRESS
    # ========================================================

    def mousePressEvent(self, event):

        if event.button() != Qt.LeftButton:
            return

        self.drawing = True

        self.last_point = event.pos()

        # Save state before drawing
        self.save_state()


    # ========================================================
    # MOUSE MOVE
    # ========================================================

    def mouseMoveEvent(self, event):

        if not self.drawing:
            return

        current_point = event.pos()

        painter = QPainter(self.image)

        painter.setRenderHint(
            QPainter.Antialiasing
        )

        # ----------------------------------------------------
        # PEN
        # ----------------------------------------------------

        if self.tool == "pen":

            pen = QPen(
                self.pen_color,
                self.pen_width,
                Qt.SolidLine,
                Qt.RoundCap,
                Qt.RoundJoin
            )

            pen.setColor(
                QColor(
                    self.pen_color.red(),
                    self.pen_color.green(),
                    self.pen_color.blue(),
                    self.opacity
                )
            )

            painter.setPen(pen)

            painter.drawLine(
                self.last_point,
                current_point
            )

        # ----------------------------------------------------
        # HIGHLIGHTER
        # ----------------------------------------------------

        elif self.tool == "highlighter":

            color = QColor(
                self.pen_color.red(),
                self.pen_color.green(),
                self.pen_color.blue(),
                90
            )

            pen = QPen(
                color,
                self.highlighter_width,
                Qt.SolidLine,
                Qt.RoundCap,
                Qt.RoundJoin
            )

            painter.setPen(pen)

            painter.drawLine(
                self.last_point,
                current_point
            )

        # ----------------------------------------------------
        # ERASER
        # ----------------------------------------------------

        elif self.tool == "eraser":

            painter.setCompositionMode(
                QPainter.CompositionMode_Source
            )

            # Restore the background color
            pen = QPen(
                self.background,
                self.eraser_width,
                Qt.SolidLine,
                Qt.RoundCap,
                Qt.RoundJoin
            )

            painter.setPen(pen)

            painter.drawLine(
                self.last_point,
                current_point
            )

            painter.setCompositionMode(
                QPainter.CompositionMode_SourceOver
            )

        painter.end()

        self.last_point = current_point

        self.update()


    # ========================================================
    # MOUSE RELEASE
    # ========================================================

    def mouseReleaseEvent(self, event):

        if event.button() == Qt.LeftButton:

            self.drawing = False

            self.update()


    # ========================================================
    # SET TOOL
    # ========================================================

    def set_tool(self, tool):

        self.tool = tool


    # ========================================================
    # SET COLOR
    # ========================================================

    def set_color(self, color):

        self.pen_color = QColor(color)

        self.tool = "pen"


    # ========================================================
    # SET PEN SIZE
    # ========================================================

    def set_pen_width(self, width):

        self.pen_width = width


    # ========================================================
    # SET OPACITY
    # ========================================================

    def set_opacity(self, opacity):

        self.opacity = opacity


    # ========================================================
    # CLEAR CANVAS
    # ========================================================

    def clear_canvas(self):

        self.save_state()

        self.image.fill(
            self.background
        )

        self.update()


    # ========================================================
    # UNDO
    # ========================================================

    def undo(self):

        if len(self.undo_stack) <= 1:
            return

        current = self.undo_stack.pop()

        self.redo_stack.append(
            current
        )

        self.image = self.undo_stack[-1].copy()

        self.update()


    # ========================================================
    # REDO
    # ========================================================

    def redo(self):

        if not self.redo_stack:
            return

        state = self.redo_stack.pop()

        self.undo_stack.append(
            state.copy()
        )

        self.image = state.copy()

        self.update()


    # ========================================================
    # LOAD IMAGE
    # ========================================================

    def load_image(self, image):

        if image.isNull():
            return

        self.image = image.convertToFormat(
            QImage.Format_ARGB32
        )

        self.undo_stack.clear()

        self.redo_stack.clear()

        self.undo_stack.append(
            self.image.copy()
        )

        self.update()


    # ========================================================
    # SAVE IMAGE
    # ========================================================

    def save_image(self, path):

        if not path:
            return False

        return self.image.save(
            path,
            "PNG"
        )


# ============================================================
# ANNOTATION PAGE
# ============================================================

class AnnotationPage(QWidget):

    def __init__(self, main_window=None):

        super().__init__(main_window)

        self.main_window = main_window

        # ----------------------------------------------------
        # Camera information
        # ----------------------------------------------------

        self.active_camera_index = None

        self.active_camera_name = "No camera selected"

        # ----------------------------------------------------
        # PDF
        # ----------------------------------------------------

        self.pdf_document = None

        self.pdf_path = None

        self.current_page = 0

        self.total_pages = 0

        # ----------------------------------------------------
        # Main background
        # ----------------------------------------------------

        self.setStyleSheet("""
            QWidget {
                background-color: #F5FEFF;
                color: #163A7A;
                font-family: "Segoe UI";
            }

            QLabel {
                background: transparent;
            }

            QPushButton {
                background-color: #F5FEFF;
                border: 1px solid #C7D8EC;
                border-radius: 7px;
                padding: 7px 12px;
                color: #163A7A;
                font-size: 13px;
            }

            QPushButton:hover {
                background-color: #E8F1FB;
            }

            QPushButton:pressed {
                background-color: #D5E4F6;
            }
        """)

        # ====================================================
        # MAIN LAYOUT
        # ====================================================

        self.main_layout = QVBoxLayout(self)

        self.main_layout.setContentsMargins(
            40,
            28,
            40,
            28
        )

        self.main_layout.setSpacing(10)

        # ====================================================
        # HEADER
        # ====================================================

        header_layout = QHBoxLayout()

        # Title section
        title_layout = QVBoxLayout()

        self.title_label = QLabel(
            "Annotation"
        )

        self.title_label.setStyleSheet("""
            QLabel {
                color: #123777;
                font-size: 25px;
                font-weight: 700;
            }
        """)

        self.subtitle_label = QLabel(
            "Annotate presentation materials using your mouse."
        )

        self.subtitle_label.setStyleSheet("""
            QLabel {
                color: #6684B5;
                font-size: 13px;
            }
        """)

        title_layout.addWidget(
            self.title_label
        )

        title_layout.addWidget(
            self.subtitle_label
        )

        header_layout.addLayout(
            title_layout
        )

        header_layout.addStretch()

        # Status
        self.mode_status = QLabel(
            "● Annotation Mode: Active"
        )

        self.mode_status.setStyleSheet("""
            QLabel {
                background-color: #E2EDF8;
                color: #5577AA;
                border-radius: 14px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: 600;
            }
        """)

        header_layout.addWidget(
            self.mode_status
        )

        self.main_layout.addLayout(
            header_layout
        )

        # ====================================================
        # TOOLBAR
        # ====================================================

        toolbar_frame = QFrame()

        toolbar_frame.setStyleSheet("""
            QFrame {
                background-color: #F8FCFF;
                border: 1px solid #D8E5F2;
                border-radius: 9px;
            }
        """)

        toolbar_layout = QHBoxLayout(
            toolbar_frame
        )

        toolbar_layout.setContentsMargins(
            8,
            7,
            8,
            7
        )

        toolbar_layout.setSpacing(5)

        # ----------------------------------------------------
        # Upload
        # ----------------------------------------------------

        self.upload_button = QPushButton(
            "Upload PDF"
        )

        self.upload_button.clicked.connect(
            self.upload_pdf
        )

        toolbar_layout.addWidget(
            self.upload_button
        )

        self.prev_button = QPushButton(
            "‹"
        )

        self.prev_button.setFixedWidth(35)

        self.prev_button.clicked.connect(
            self.previous_page
        )

        toolbar_layout.addWidget(
            self.prev_button
        )

        self.next_button = QPushButton(
            "›"
        )

        self.next_button.setFixedWidth(35)

        self.next_button.clicked.connect(
            self.next_page
        )

        toolbar_layout.addWidget(
            self.next_button
        )

        # Separator
        separator1 = QFrame()

        separator1.setFrameShape(
            QFrame.VLine
        )

        separator1.setStyleSheet(
            "color: #D7E4F1;"
        )

        toolbar_layout.addWidget(
            separator1
        )

        # ----------------------------------------------------
        # Pen
        # ----------------------------------------------------

        self.pen_button = QPushButton(
            "✎"
        )

        self.pen_button.setFixedWidth(40)

        self.pen_button.clicked.connect(
            lambda: self.select_tool("pen")
        )

        toolbar_layout.addWidget(
            self.pen_button
        )

        # ----------------------------------------------------
        # Highlighter
        # ----------------------------------------------------

        self.highlighter_button = QPushButton(
            "▰"
        )

        self.highlighter_button.setFixedWidth(40)

        self.highlighter_button.clicked.connect(
            lambda: self.select_tool("highlighter")
        )

        toolbar_layout.addWidget(
            self.highlighter_button
        )

        # ----------------------------------------------------
        # Eraser
        # ----------------------------------------------------

        self.eraser_button = QPushButton(
            "⌫"
        )

        self.eraser_button.setFixedWidth(40)

        self.eraser_button.clicked.connect(
            lambda: self.select_tool("eraser")
        )

        toolbar_layout.addWidget(
            self.eraser_button
        )

        # Separator
        separator2 = QFrame()

        separator2.setFrameShape(
            QFrame.VLine
        )

        separator2.setStyleSheet(
            "color: #D7E4F1;"
        )

        toolbar_layout.addWidget(
            separator2
        )

        # ----------------------------------------------------
        # Undo
        # ----------------------------------------------------

        self.undo_button = QPushButton(
            "↶"
        )

        self.undo_button.setFixedWidth(40)

        self.undo_button.clicked.connect(
            self.canvas_undo
        )

        toolbar_layout.addWidget(
            self.undo_button
        )

        # ----------------------------------------------------
        # Redo
        # ----------------------------------------------------

        self.redo_button = QPushButton(
            "↷"
        )

        self.redo_button.setFixedWidth(40)

        self.redo_button.clicked.connect(
            self.canvas_redo
        )

        toolbar_layout.addWidget(
            self.redo_button
        )

        # ----------------------------------------------------
        # Clear
        # ----------------------------------------------------

        self.clear_button = QPushButton(
            "♲"
        )

        self.clear_button.setFixedWidth(40)

        self.clear_button.clicked.connect(
            self.clear_canvas
        )

        toolbar_layout.addWidget(
            self.clear_button
        )

        # Separator
        separator3 = QFrame()

        separator3.setFrameShape(
            QFrame.VLine
        )

        separator3.setStyleSheet(
            "color: #D7E4F1;"
        )

        toolbar_layout.addWidget(
            separator3
        )

        # ====================================================
        # COLORS
        # ====================================================

        colors = [
            ("#132B5C", "Dark Blue"),
            ("#EF4444", "Red"),
            ("#3478F6", "Blue"),
            ("#20B86A", "Green"),
            ("#F59E0B", "Orange")
        ]

        for color, tooltip in colors:

            button = QPushButton()

            button.setFixedSize(
                22,
                22
            )

            button.setToolTip(
                tooltip
            )

            button.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {color};
                    border: 2px solid white;
                    border-radius: 11px;
                }}

                QPushButton:hover {{
                    border: 2px solid #9CB8D9;
                }}
                """
            )

            button.clicked.connect(
                lambda checked=False,
                c=color: self.select_color(c)
            )

            toolbar_layout.addWidget(
                button
            )

        # ----------------------------------------------------
        # Save
        # ----------------------------------------------------

        separator4 = QFrame()

        separator4.setFrameShape(
            QFrame.VLine
        )

        separator4.setStyleSheet(
            "color: #D7E4F1;"
        )

        toolbar_layout.addWidget(
            separator4
        )

        self.save_button = QPushButton(
            "▣"
        )

        self.save_button.setFixedWidth(40)

        self.save_button.setToolTip(
            "Save Annotation"
        )

        self.save_button.clicked.connect(
            self.save_annotation
        )

        toolbar_layout.addWidget(
            self.save_button
        )

        toolbar_layout.addStretch()

        self.main_layout.addWidget(
            toolbar_frame
        )

        # ====================================================
        # CANVAS CONTAINER
        # ====================================================

        canvas_frame = QFrame()

        canvas_frame.setStyleSheet("""
            QFrame {
                background-color: #F9FDFF;
                border: 1px solid #D6E4F1;
                border-radius: 13px;
            }
        """)

        canvas_layout = QVBoxLayout(
            canvas_frame
        )

        canvas_layout.setContentsMargins(
            10,
            10,
            10,
            10
        )

        # ----------------------------------------------------
        # Canvas
        # ----------------------------------------------------

        self.canvas = AnnotationCanvas()

        canvas_layout.addWidget(
            self.canvas
        )

        self.main_layout.addWidget(
            canvas_frame,
            1
        )

        # ====================================================
        # PAGE STATUS
        # ====================================================

        bottom_layout = QHBoxLayout()

        self.file_label = QLabel(
            "No presentation loaded"
        )

        self.file_label.setStyleSheet("""
            QLabel {
                color: #6A86AE;
                font-size: 12px;
            }
        """)

        bottom_layout.addWidget(
            self.file_label
        )

        bottom_layout.addStretch()

        self.page_label = QLabel(
            "Page 0 / 0"
        )

        self.page_label.setStyleSheet("""
            QLabel {
                background-color: #E2EDF8;
                color: #5577AA;
                border-radius: 12px;
                padding: 6px 12px;
                font-size: 12px;
            }
        """)

        bottom_layout.addWidget(
            self.page_label
        )

        self.main_layout.addLayout(
            bottom_layout
        )

        # ====================================================
        # INITIAL TOOL
        # ====================================================

        self.select_tool(
            "pen"
        )


    # ========================================================
    # SELECT TOOL
    # ========================================================

    def select_tool(self, tool):

        self.canvas.set_tool(
            tool
        )

        # Reset all buttons
        buttons = [
            self.pen_button,
            self.highlighter_button,
            self.eraser_button
        ]

        for button in buttons:

            button.setStyleSheet("""
                QPushButton {
                    background-color: #F5FEFF;
                    border: 1px solid #C7D8EC;
                    border-radius: 7px;
                    padding: 7px 12px;
                    color: #163A7A;
                    font-size: 13px;
                }
            """)

        # Highlight active button
        if tool == "pen":

            button = self.pen_button

        elif tool == "highlighter":

            button = self.highlighter_button

        else:

            button = self.eraser_button

        button.setStyleSheet("""
            QPushButton {
                background-color: #AFC6E5;
                border: 1px solid #9CB7D9;
                border-radius: 7px;
                padding: 7px 12px;
                color: #163A7A;
                font-size: 13px;
                font-weight: 600;
            }
        """)

        # Update status
        if tool == "pen":

            self.mode_status.setText(
                "● Pen Mode: Active"
            )

        elif tool == "highlighter":

            self.mode_status.setText(
                "● Highlighter Mode: Active"
            )

        elif tool == "eraser":

            self.mode_status.setText(
                "● Eraser Mode: Active"
            )


    # ========================================================
    # SELECT COLOR
    # ========================================================

    def select_color(self, color):

        self.canvas.set_color(
            color
        )

        self.select_tool(
            "pen"
        )


    # ========================================================
    # CLEAR
    # ========================================================

    def clear_canvas(self):

        reply = QMessageBox.question(
            self,
            "Clear Annotation",
            "Are you sure you want to clear the annotation?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:

            self.canvas.clear_canvas()


    # ========================================================
    # UNDO
    # ========================================================

    def canvas_undo(self):

        self.canvas.undo()


    # ========================================================
    # REDO
    # ========================================================

    def canvas_redo(self):

        self.canvas.redo()


    # ========================================================
    # UPLOAD PDF
    # ========================================================

    def upload_pdf(self):

        if fitz is None:

            QMessageBox.warning(
                self,
                "PyMuPDF Required",
                "PyMuPDF is not installed.\n\n"
                "Install it using:\n"
                "pip install pymupdf"
            )

            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Presentation",
            "",
            "PDF Files (*.pdf)"
        )

        if not path:
            return

        try:

            document = fitz.open(
                path
            )

            if document.page_count == 0:

                document.close()

                QMessageBox.warning(
                    self,
                    "Invalid PDF",
                    "The selected PDF does not contain any pages."
                )

                return

            # Close previous document
            if self.pdf_document is not None:

                try:
                    self.pdf_document.close()

                except Exception:
                    pass

            self.pdf_document = document

            self.pdf_path = path

            self.current_page = 0

            self.total_pages = document.page_count

            self.file_label.setText(
                os.path.basename(path)
            )

            self.render_pdf_page(
                self.current_page
            )

            self.update_page_label()

        except Exception as e:

            QMessageBox.critical(
                self,
                "PDF Error",
                f"Could not open the PDF.\n\n{e}"
            )


    # ========================================================
    # RENDER PDF PAGE
    # ========================================================

    def render_pdf_page(self, page_number):

        if self.pdf_document is None:
            return

        try:

            page = self.pdf_document.load_page(
                page_number
            )

            # Render at higher resolution
            matrix = fitz.Matrix(
                1.5,
                1.5
            )

            pixmap = page.get_pixmap(
                matrix=matrix,
                alpha=False
            )

            image = QImage(
                pixmap.samples,
                pixmap.width,
                pixmap.height,
                pixmap.stride,
                QImage.Format_RGB888
            ).copy()

            # Resize to fit annotation canvas
            canvas_width = max(
                1,
                self.canvas.width()
            )

            canvas_height = max(
                1,
                self.canvas.height()
            )

            image = image.scaled(
                canvas_width,
                canvas_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            # Put PDF onto centered canvas
            canvas_image = QImage(
                canvas_width,
                canvas_height,
                QImage.Format_ARGB32
            )

            canvas_image.fill(
                QColor("#E4EEF7")
            )

            painter = QPainter(
                canvas_image
            )

            x = (
                canvas_width - image.width()
            ) // 2

            y = (
                canvas_height - image.height()
            ) // 2

            painter.drawImage(
                x,
                y,
                image
            )

            painter.end()

            self.canvas.load_image(
                canvas_image
            )

        except Exception as e:

            QMessageBox.warning(
                self,
                "Page Error",
                f"Could not display the page.\n\n{e}"
            )


    # ========================================================
    # NEXT PAGE
    # ========================================================

    def next_page(self):

        if self.pdf_document is None:
            return

        if (
            self.current_page
            < self.total_pages - 1
        ):

            self.current_page += 1

            self.render_pdf_page(
                self.current_page
            )

            self.update_page_label()


    # ========================================================
    # PREVIOUS PAGE
    # ========================================================

    def previous_page(self):

        if self.pdf_document is None:
            return

        if self.current_page > 0:

            self.current_page -= 1

            self.render_pdf_page(
                self.current_page
            )

            self.update_page_label()


    # ========================================================
    # PAGE LABEL
    # ========================================================

    def update_page_label(self):

        if self.total_pages > 0:

            self.page_label.setText(
                f"Page {self.current_page + 1} / "
                f"{self.total_pages}"
            )

        else:

            self.page_label.setText(
                "Page 0 / 0"
            )


    # ========================================================
    # SAVE ANNOTATION
    # ========================================================

    def save_annotation(self):

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Annotation",
            "annotation.png",
            "PNG Image (*.png)"
        )

        if not path:
            return

        try:

            success = self.canvas.save_image(
                path
            )

            if success:

                QMessageBox.information(
                    self,
                    "Saved",
                    "Annotation saved successfully."
                )

            else:

                QMessageBox.warning(
                    self,
                    "Save Failed",
                    "Could not save the annotation."
                )

        except Exception as e:

            QMessageBox.critical(
                self,
                "Save Error",
                f"Could not save annotation.\n\n{e}"
            )


    # ========================================================
    # CAMERA FUNCTIONS
    # ========================================================
    # These are kept because MainWindow calls them.
    # Annotation itself DOES NOT use hand gestures.
    # ========================================================

    def setActiveCamera(
        self,
        index,
        name
    ):

        self.active_camera_index = index

        self.active_camera_name = name


    def updateCameraName(
        self,
        name
    ):

        self.active_camera_name = name