import os

from PyQt5.QtCore import Qt, QPointF, QRectF, QSize
from PyQt5.QtGui import (
    QPainter,
    QPainterPath,
    QPen,
    QColor,
    QImage,
    QFontMetrics,
    QKeySequence
)
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QButtonGroup,
    QSlider,
    QShortcut,
    QFileDialog,
    QMessageBox,
    QFrame,
    QSizePolicy
)

from settings import theme as app_theme
from widgets import page_background
from gui.whiteboard import BrushPreview, WhiteboardPage, tool_pixmap

try:
    import fitz
except ImportError:
    fitz = None


# ============================================================
# ANNOTATION CANVAS
#
# The page being marked up sits on a "desk" like a sheet of paper.
# Two layers: the page (a PDF page, or a blank slide) and the ink
# drawn over it. Ink is stored in page pixels, so it stays on the
# words it was drawn over when the window is resized, and the
# eraser only ever removes ink, never the slide underneath.
# ============================================================

# Blank sheet shown before a PDF is opened: a 16:9 slide.
BLANK_SIZE = QSize(1600, 900)

# Space between the desk edge and the sheet.
DESK_MARGIN = 22

# Marker and eraser widths relative to the pen size.
MARKER_FACTOR = 5
ERASER_FACTOR = 6

MARKER_ALPHA = 100

UNDO_LIMIT = 30


class AnnotationCanvas(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMinimumSize(320, 220)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCursor(Qt.CrossCursor)

        self.page = self._blank_page()
        self.ink = self._blank_ink(self.page.size())

        self.tool = "pen"
        self.pen_color = QColor("#172033")
        self.pen_width = 4

        self.undo_stack = []
        self.redo_stack = []

        self.drawing = False
        self.stroke_base = None
        self.stroke_path = None
        self.last_point = QPointF()

        # Theme colours, set by AnnotationPage.apply_theme().
        self.desk = QColor("#E4EEF7")
        self.sheet_border = QColor("#BED2E9")
        self.shadow = QColor(14, 47, 118)
        self.hint_color = QColor("#5A6B93")

        # Shown on the blank sheet until something is drawn.
        self.placeholder = (
            "Open a PDF to mark up its pages,\n"
            "or draw right here on this blank sheet."
        )
        self.show_placeholder = True

    # ========================================================
    # LAYERS
    # ========================================================

    @staticmethod
    def _blank_page():
        image = QImage(BLANK_SIZE, QImage.Format_ARGB32)
        image.fill(QColor("#FFFFFF"))
        return image

    @staticmethod
    def _blank_ink(size):
        image = QImage(size, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.transparent)
        return image

    def set_page(self, image, ink=None, undo=None, redo=None):
        """Show `image` as the sheet, with that page's saved ink."""

        if image is None or image.isNull():
            image = self._blank_page()

        self.page = image.convertToFormat(QImage.Format_ARGB32)
        self.ink = ink if ink is not None else self._blank_ink(self.page.size())
        self.undo_stack = undo if undo is not None else []
        self.redo_stack = redo if redo is not None else []
        self.drawing = False
        self.update()

    def state(self):
        """The current page's ink and history, to restore later."""
        return self.ink, self.undo_stack, self.redo_stack

    # ========================================================
    # GEOMETRY
    # ========================================================

    def sheet_rect(self):
        """Where the sheet is drawn: fitted and centred on the desk."""

        area = QRectF(self.rect()).adjusted(
            DESK_MARGIN, DESK_MARGIN, -DESK_MARGIN, -DESK_MARGIN
        )

        pw, ph = self.page.width(), self.page.height()
        scale = min(area.width() / pw, area.height() / ph)
        w, h = pw * scale, ph * scale

        return QRectF(
            area.center().x() - w / 2,
            area.center().y() - h / 2,
            w,
            h
        )

    def _page_scale(self):
        """Page pixels per screen pixel."""
        rect = self.sheet_rect()
        return self.page.width() / max(1.0, rect.width())

    def _to_page(self, pos):
        rect = self.sheet_rect()
        scale = self._page_scale()
        return QPointF(
            (pos.x() - rect.x()) * scale,
            (pos.y() - rect.y()) * scale
        )

    def tool_width(self):
        """Width of the current tool on screen, in pixels."""

        if self.tool == "highlighter":
            return self.pen_width * MARKER_FACTOR
        if self.tool == "eraser":
            return self.pen_width * ERASER_FACTOR
        return self.pen_width

    # ========================================================
    # PAINT
    # ========================================================

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        painter.fillRect(self.rect(), self.desk)

        sheet = self.sheet_rect()

        # Soft shadow: a few widening, fading outlines under the sheet.
        painter.setPen(Qt.NoPen)
        for spread, alpha in ((12, 6), (7, 10), (3, 16)):
            shadow = QColor(self.shadow)
            shadow.setAlpha(alpha)
            painter.setBrush(shadow)
            painter.drawRoundedRect(
                sheet.adjusted(-spread, -spread + 3, spread, spread + 3),
                spread + 2,
                spread + 2
            )

        painter.drawImage(sheet, self.page)
        painter.drawImage(sheet, self.ink)

        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(self.sheet_border, 1))
        painter.drawRect(sheet.adjusted(-0.5, -0.5, 0.5, 0.5))

        if self.show_placeholder:
            font = painter.font()
            font.setFamily("Segoe UI")
            font.setPixelSize(max(15, min(22, int(sheet.height() / 20))))
            painter.setFont(font)
            painter.setPen(self.hint_color)
            painter.drawText(sheet, Qt.AlignCenter, self.placeholder)

        painter.end()

    # ========================================================
    # DRAWING
    # ========================================================

    def mousePressEvent(self, event):

        if event.button() != Qt.LeftButton:
            return

        self.drawing = True
        self.show_placeholder = False
        self.stroke_base = self.ink.copy()

        point = self._to_page(event.pos())
        self.last_point = point

        # A tiny first segment so a single click still leaves a dot.
        self.stroke_path = QPainterPath(point)
        self.stroke_path.lineTo(point + QPointF(0.01, 0.01))

        self._draw_stroke(point)

    def mouseMoveEvent(self, event):

        if not self.drawing:
            return

        point = self._to_page(event.pos())
        self.stroke_path.lineTo(point)
        self._draw_stroke(point)

    def mouseReleaseEvent(self, event):

        if event.button() != Qt.LeftButton or not self.drawing:
            return

        self.drawing = False

        # History holds the ink from before each stroke.
        self.undo_stack.append(self.stroke_base)
        if len(self.undo_stack) > UNDO_LIMIT:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

        self.stroke_base = None
        self.stroke_path = None

    def _draw_stroke(self, point):

        width = self.tool_width() * self._page_scale()

        if self.tool == "eraser":
            # Erase as the cursor moves; only the ink layer is touched.
            painter = QPainter(self.ink)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.setPen(QPen(Qt.black, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawLine(self.last_point, point)
            painter.end()

        else:
            # Redraw the whole stroke over the ink from before it, so a
            # see-through marker stays even instead of blotchy where
            # its segments overlap.
            color = QColor(self.pen_color)
            if self.tool == "highlighter":
                color.setAlpha(MARKER_ALPHA)

            self.ink = self.stroke_base.copy()

            painter = QPainter(self.ink)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(self.stroke_path)
            painter.end()

        self.last_point = point
        self.update()

    # ========================================================
    # SETTINGS
    # ========================================================

    def set_tool(self, tool):
        self.tool = tool

    def set_color(self, color):
        self.pen_color = QColor(color)

    def set_pen_width(self, width):
        self.pen_width = width

    # ========================================================
    # HISTORY
    # ========================================================

    def clear_canvas(self):

        self.undo_stack.append(self.ink.copy())
        if len(self.undo_stack) > UNDO_LIMIT:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

        self.ink = self._blank_ink(self.page.size())
        self.update()

    def undo(self):

        if not self.undo_stack:
            return

        self.redo_stack.append(self.ink)
        self.ink = self.undo_stack.pop()
        self.update()

    def redo(self):

        if not self.redo_stack:
            return

        self.undo_stack.append(self.ink)
        self.ink = self.redo_stack.pop()
        self.update()


# ============================================================
# ANNOTATION PAGE
# ============================================================

class AnnotationPage(QWidget):

    # Same ink colours as the Whiteboard.
    SWATCHES = WhiteboardPage.SWATCHES

    def __init__(self, main_window=None):

        super().__init__(main_window)

        self.main_window = main_window

        # ----------------------------------------------------
        # Camera information (kept for MainWindow; this page
        # is drawn on with the mouse or the Virtual Mouse)
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

        # Ink and history of each page, so flipping pages keeps them.
        self.page_states = {}

        self.current_color = self.SWATCHES[0][0]

        self.colors = page_background.page_colors()

        self._tool_buttons = []
        self.swatch_buttons = {}

        self.setup_ui()

    # ========================================================
    # UI
    # ========================================================

    def setup_ui(self):

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 24, 32, 18)
        main_layout.setSpacing(12)

        # ====================================================
        # HEADER
        # ====================================================

        title = QLabel("Annotation")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "Mark up PDF pages with a regular mouse or the Virtual Mouse."
        )
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(title)
        title_col.addWidget(subtitle)

        header_row = QHBoxLayout()
        header_row.setSpacing(12)
        header_row.addLayout(title_col, 1)

        # Which file is open.
        self.file_pill = QLabel()
        self.file_pill.setObjectName("filePill")
        header_row.addWidget(self.file_pill, alignment=Qt.AlignTop)

        main_layout.addLayout(header_row)

        # ====================================================
        # TOOL DOCK
        # ====================================================

        dock = QFrame()
        dock.setObjectName("dock")

        dock_layout = QVBoxLayout(dock)
        dock_layout.setContentsMargins(12, 10, 14, 10)
        dock_layout.setSpacing(10)

        # ---------- row 1: tools, history, open ----------

        tools_row = QHBoxLayout()
        tools_row.setSpacing(6)

        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)

        self.tool_buttons = {}

        for name, label, tip in (
            ("pen", "Pen", "Pen (P)"),
            ("highlighter", "Marker", "Highlighter (H)"),
            ("eraser", "Eraser", "Erase ink, not the slide (E)"),
        ):
            button = self.create_tool_button(name, label, tip)
            button.setCheckable(True)
            button.clicked.connect(
                lambda checked=False, tool=name: self.select_tool(tool)
            )
            self.tool_group.addButton(button)
            self.tool_buttons[name] = button
            tools_row.addWidget(button)

        tools_row.addWidget(self.create_separator())

        undo_button = self.create_tool_button("undo", "Undo", "Undo (Ctrl+Z)")
        undo_button.clicked.connect(self.canvas_undo)
        tools_row.addWidget(undo_button)

        redo_button = self.create_tool_button("redo", "Redo", "Redo (Ctrl+Y)")
        redo_button.clicked.connect(self.canvas_redo)
        tools_row.addWidget(redo_button)

        clear_button = self.create_tool_button(
            "clear", "Clear", "Clear the ink on this page", danger=True
        )
        clear_button.clicked.connect(self.clear_canvas)
        tools_row.addWidget(clear_button)

        tools_row.addStretch()

        self.open_button = QPushButton("Open PDF")
        self.open_button.setObjectName("openButton")
        self.open_button.setCursor(Qt.PointingHandCursor)
        self.open_button.setToolTip("Open a PDF to mark up (Ctrl+O)")
        self.open_button.setMinimumHeight(56)
        self.open_button.clicked.connect(self.upload_pdf)
        tools_row.addWidget(self.open_button)

        dock_layout.addLayout(tools_row)

        rule = QFrame()
        rule.setObjectName("dockRule")
        rule.setFixedHeight(1)
        dock_layout.addWidget(rule)

        # ---------- row 2: colours, size ----------

        brush_row = QHBoxLayout()
        brush_row.setContentsMargins(4, 0, 0, 0)
        brush_row.setSpacing(6)

        colour_label = QLabel("Colour")
        colour_label.setObjectName("controlLabel")
        brush_row.addWidget(colour_label)

        self.swatch_group = QButtonGroup(self)
        self.swatch_group.setExclusive(True)

        for color, name in self.SWATCHES:

            swatch = QPushButton()
            swatch.setCheckable(True)
            swatch.setFixedSize(40, 40)
            swatch.setCursor(Qt.PointingHandCursor)
            swatch.setToolTip(name)
            swatch.clicked.connect(
                lambda checked=False, c=color: self.select_color(c)
            )

            self.swatch_group.addButton(swatch)
            self.swatch_buttons[color] = swatch
            brush_row.addWidget(swatch)

        brush_row.addWidget(self.create_separator())

        self.brush_preview = BrushPreview()
        brush_row.addWidget(self.brush_preview)

        size_label = QLabel("Size")
        size_label.setObjectName("controlLabel")
        brush_row.addWidget(size_label)

        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(1, 20)
        self.size_slider.setValue(4)
        self.size_slider.setMinimumWidth(70)
        self.size_slider.setMaximumWidth(200)
        self.size_slider.setCursor(Qt.PointingHandCursor)
        self.size_slider.valueChanged.connect(self.change_size)
        brush_row.addWidget(self.size_slider, 1)

        self.size_value = QLabel("4 px")
        self.size_value.setObjectName("controlValue")
        self.size_value.setFixedWidth(50)
        brush_row.addSpacing(6)
        brush_row.addWidget(self.size_value)

        brush_row.addStretch()

        dock_layout.addLayout(brush_row)

        main_layout.addWidget(dock)

        # ====================================================
        # DESK + SHEET
        # ====================================================

        self.desk_frame = QFrame()
        self.desk_frame.setObjectName("deskFrame")

        desk_layout = QVBoxLayout(self.desk_frame)
        desk_layout.setContentsMargins(1, 1, 1, 1)
        desk_layout.setSpacing(0)

        self.canvas = AnnotationCanvas()
        desk_layout.addWidget(self.canvas)

        main_layout.addWidget(self.desk_frame, 1)

        # ====================================================
        # PAGE BAR
        # ====================================================

        pager = QHBoxLayout()
        pager.setSpacing(10)
        pager.addStretch()

        self.prev_button = QPushButton("Previous")
        self.prev_button.setObjectName("pagerButton")
        self.prev_button.setCursor(Qt.PointingHandCursor)
        self.prev_button.setToolTip("Previous page (Left arrow)")
        self.prev_button.clicked.connect(self.previous_page)
        pager.addWidget(self.prev_button)

        self.page_label = QLabel()
        self.page_label.setObjectName("pageLabel")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setMinimumWidth(130)
        pager.addWidget(self.page_label)

        self.next_button = QPushButton("Next")
        self.next_button.setObjectName("pagerButton")
        self.next_button.setCursor(Qt.PointingHandCursor)
        self.next_button.setToolTip("Next page (Right arrow)")
        self.next_button.clicked.connect(self.next_page)
        pager.addWidget(self.next_button)

        pager.addStretch()

        main_layout.addLayout(pager)

        # Keyboard shortcuts named in the tooltips.
        for keys, action in (
            ("P", lambda: self.select_tool("pen")),
            ("H", lambda: self.select_tool("highlighter")),
            ("E", lambda: self.select_tool("eraser")),
            ("Ctrl+Z", self.canvas_undo),
            ("Ctrl+Y", self.canvas_redo),
            ("Ctrl+O", self.upload_pdf),
            ("Left", self.previous_page),
            ("PgUp", self.previous_page),
            ("Right", self.next_page),
            ("PgDown", self.next_page),
        ):
            QShortcut(QKeySequence(keys), self, action)

        page_background.clear_layers(self)

        # ====================================================
        # DEFAULTS
        # ====================================================

        self.swatch_buttons[self.current_color].setChecked(True)
        self.canvas.set_color(self.current_color)

        self.select_tool("pen")

        self.update_page_label()

        self.apply_theme()

    # ========================================================
    # THEME
    #
    # The chrome follows the app theme with the Whiteboard's
    # palette. The sheet stays paper white in both themes; in dark
    # mode it sits on a dark desk.
    # ========================================================

    @property
    def _palette(self):
        if app_theme.is_dark():
            return WhiteboardPage.DARK_PALETTE
        return WhiteboardPage.LIGHT_PALETTE

    def apply_theme(self):

        self.colors = page_background.page_colors()

        dark = app_theme.is_dark()
        p = self._palette

        desk = "#0F2038" if dark else "#E4EEF7"

        self.setStyleSheet(page_background.LAYER_RULE + f"""
            QWidget {{
                color: {p['text']};
                font-family: "Segoe UI";
            }}

            QLabel {{
                background: transparent;
            }}

            QLabel#pageTitle {{
                font-size: 28px;
                font-weight: 800;
            }}

            QLabel#pageSubtitle {{
                font-size: 16px;
                color: {p['muted']};
            }}

            QLabel#filePill {{
                background: {p['pill']};
                color: {p['muted']};
                border-radius: 18px;
                padding: 8px 18px;
                font-size: 15px;
                font-weight: 700;
            }}

            QLabel#filePill[open="true"] {{
                color: {p['text']};
            }}

            /* ---------- tool dock ---------- */

            QFrame#dock {{
                background-color: {p['dock']};
                border: 1px solid {p['border']};
                border-radius: 14px;
            }}

            QFrame#dockRule, QFrame#divider {{
                background-color: {p['border']};
                border: none;
            }}

            QToolButton#tool, QToolButton#dangerTool {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 12px;
                color: {p['text']};
                font-size: 13px;
                font-weight: 600;
                padding: 4px 2px 3px 2px;
            }}

            QToolButton#tool:hover {{
                background: {p['hover']};
            }}

            QToolButton#tool:pressed {{
                background: {p['pressed']};
            }}

            QToolButton#tool:checked {{
                background: {p['primary']};
                color: #F5FEFF;
            }}

            QToolButton#tool:focus, QToolButton#dangerTool:focus {{
                outline: none;
            }}

            QToolButton#dangerTool {{
                color: {p['danger_icon']};
            }}

            QToolButton#dangerTool:hover {{
                background: {p['danger_hover']};
            }}

            QPushButton#openButton {{
                background: {p['primary']};
                color: #F5FEFF;
                border: none;
                border-radius: 12px;
                padding: 10px 24px;
                font-size: 17px;
                font-weight: 700;
            }}

            QPushButton#openButton:hover {{
                background: {p['primary_hover']};
            }}

            QLabel#controlLabel {{
                font-size: 15px;
                font-weight: 600;
                color: {p['muted']};
            }}

            QLabel#controlValue {{
                font-size: 15px;
                font-weight: 700;
            }}

            QSlider {{
                background: transparent;
                min-height: 30px;
            }}

            QSlider::groove:horizontal {{
                height: 8px;
                background: {p['groove']};
                border-radius: 4px;
            }}

            QSlider::sub-page:horizontal {{
                background: {p['primary']};
                border-radius: 4px;
            }}

            QSlider::handle:horizontal {{
                width: 20px;
                height: 20px;
                margin: -8px 0;
                background: {p['handle']};
                border: 3px solid {p['primary']};
                border-radius: 12px;
            }}

            /* ---------- desk and page bar ---------- */

            QFrame#deskFrame {{
                background-color: {desk};
                border: 1px solid {p['border']};
                border-radius: 8px;
            }}

            QPushButton#pagerButton {{
                background: {p['dock']};
                color: {p['text']};
                border: 1px solid {p['border']};
                border-radius: 12px;
                padding: 8px 20px;
                font-size: 15px;
                font-weight: 600;
            }}

            QPushButton#pagerButton:hover {{
                background: {p['hover']};
            }}

            QPushButton#pagerButton:disabled {{
                color: {p['border']};
                background: transparent;
            }}

            QLabel#pageLabel {{
                font-size: 15px;
                font-weight: 700;
                color: {p['muted']};
            }}
        """)

        for button, icon, danger in self._tool_buttons:
            self._paint_tool_icon(button, icon, danger)

        for color, swatch in self.swatch_buttons.items():
            swatch.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {color};
                    border: 3px solid {p['swatch_ring']};
                    border-radius: 20px;
                }}

                QPushButton:hover {{
                    border: 3px solid {p['hover']};
                }}

                QPushButton:checked {{
                    border: 5px solid #22C3DE;
                }}

                QPushButton:focus {{
                    outline: none;
                }}
                """
            )

        self.brush_preview.set_ring(p["border"])

        self.canvas.desk = QColor(desk)
        self.canvas.sheet_border = QColor(p["border"])
        self.canvas.shadow = QColor("#000000" if dark else "#0E2F76")
        self.canvas.hint_color = QColor("#5A6B93")
        self.canvas.update()

        self.update()

    def paintEvent(self, event):

        page_background.paint_page_background(self, self.colors)

    # ========================================================
    # TOOL BUTTONS
    # ========================================================

    def create_tool_button(self, icon, label, tooltip, danger=False):

        # Icon with its name underneath, as on the Whiteboard.
        button = QToolButton()
        button.setObjectName("dangerTool" if danger else "tool")
        button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        button.setText(label)
        button.setFixedSize(64, 60)
        button.setCursor(Qt.PointingHandCursor)
        button.setToolTip(tooltip)
        button.setIconSize(QSize(26, 26))

        self._tool_buttons.append((button, icon, danger))
        self._paint_tool_icon(button, icon, danger)

        return button

    def _paint_tool_icon(self, button, icon, danger):

        from PyQt5.QtGui import QIcon

        p = self._palette
        idle = p["danger_icon"] if danger else p["tool_icon"]

        qicon = QIcon()
        qicon.addPixmap(tool_pixmap(icon, idle, 26), QIcon.Normal, QIcon.Off)
        qicon.addPixmap(tool_pixmap(icon, "#F5FEFF", 26), QIcon.Normal, QIcon.On)

        button.setIcon(qicon)

    def create_separator(self):

        separator = QFrame()
        separator.setObjectName("divider")
        separator.setFixedSize(1, 26)

        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.addWidget(separator, 0, Qt.AlignVCenter)

        return wrapper

    # ========================================================
    # TOOLS AND BRUSH
    # ========================================================

    def select_tool(self, tool):

        self.canvas.set_tool(tool)
        self.tool_buttons[tool].setChecked(True)
        self._update_preview()

    def select_color(self, color):

        self.current_color = color
        self.canvas.set_color(color)

        # Picking a colour while erasing means "draw with this".
        if self.canvas.tool == "eraser":
            self.select_tool("pen")
        else:
            self._update_preview()

    def change_size(self, value):

        self.canvas.set_pen_width(value)
        self.size_value.setText(f"{value} px")
        self._update_preview()

    def _update_preview(self):

        tool = self.canvas.tool

        if tool == "eraser":
            color, opacity = "#FFFFFF", 100
        elif tool == "highlighter":
            color, opacity = self.current_color, round(MARKER_ALPHA / 2.55)
        else:
            color, opacity = self.current_color, 100

        self.brush_preview.set_brush(color, self.canvas.tool_width(), opacity)

    # ========================================================
    # HISTORY
    # ========================================================

    def clear_canvas(self):

        reply = QMessageBox.question(
            self,
            "Clear ink",
            "Clear everything drawn on this page? The PDF itself stays.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.canvas.clear_canvas()

    def canvas_undo(self):
        self.canvas.undo()

    def canvas_redo(self):
        self.canvas.redo()

    # ========================================================
    # OPEN PDF
    # ========================================================

    def upload_pdf(self):

        if fitz is None:
            QMessageBox.warning(
                self,
                "PyMuPDF needed",
                "Opening PDFs needs PyMuPDF.\n\n"
                "Install it with:\n"
                "pip install pymupdf"
            )
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open PDF",
            "",
            "PDF Files (*.pdf)"
        )

        if not path:
            return

        try:
            document = fitz.open(path)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Couldn't open PDF",
                f"This file couldn't be opened as a PDF.\n\n{e}"
            )
            return

        if document.page_count == 0:
            document.close()
            QMessageBox.warning(
                self,
                "Empty PDF",
                "This PDF has no pages. Choose another file."
            )
            return

        if self.pdf_document is not None:
            try:
                self.pdf_document.close()
            except Exception:
                pass

        self.pdf_document = document
        self.pdf_path = path
        self.total_pages = document.page_count
        self.current_page = 0
        self.page_states = {}

        self.canvas.show_placeholder = False
        self.show_page(0, keep_current=False)

    # ========================================================
    # PAGES
    # ========================================================

    def render_page_image(self, page_number):

        page = self.pdf_document.load_page(page_number)

        # Twice the PDF's size, so text stays sharp on large screens.
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)

        return QImage(
            pixmap.samples,
            pixmap.width,
            pixmap.height,
            pixmap.stride,
            QImage.Format_RGB888
        ).copy()

    def show_page(self, page_number, keep_current=True):

        if self.pdf_document is None:
            return

        try:
            image = self.render_page_image(page_number)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Couldn't show page",
                f"Page {page_number + 1} couldn't be displayed.\n\n{e}"
            )
            return

        if keep_current:
            self.page_states[self.current_page] = self.canvas.state()

        self.current_page = page_number
        self.canvas.set_page(image, *self.page_states.get(page_number, ()))

        self.update_page_label()

    def next_page(self):

        if self.pdf_document is not None and self.current_page < self.total_pages - 1:
            self.show_page(self.current_page + 1)

    def previous_page(self):

        if self.pdf_document is not None and self.current_page > 0:
            self.show_page(self.current_page - 1)

    def update_page_label(self):

        has_pdf = self.pdf_document is not None

        if has_pdf:
            self.page_label.setText(
                f"Page {self.current_page + 1} of {self.total_pages}"
            )
            name = os.path.basename(self.pdf_path)
        else:
            self.page_label.setText("Blank sheet")
            name = "No PDF open"

        self.prev_button.setVisible(has_pdf)
        self.next_button.setVisible(has_pdf)
        self.prev_button.setEnabled(has_pdf and self.current_page > 0)
        self.next_button.setEnabled(
            has_pdf and self.current_page < self.total_pages - 1
        )

        # Long file names are shortened so the header keeps its shape.
        metrics = QFontMetrics(self.file_pill.font())
        self.file_pill.setText(metrics.elidedText(name, Qt.ElideMiddle, 300))
        self.file_pill.setToolTip(self.pdf_path or "")
        self.file_pill.setProperty("open", has_pdf)
        self.file_pill.style().unpolish(self.file_pill)
        self.file_pill.style().polish(self.file_pill)

    # ========================================================
    # CAMERA FUNCTIONS
    # ========================================================
    # These are kept because MainWindow calls them.
    # Annotation itself DOES NOT use hand gestures.
    # ========================================================

    def setActiveCamera(self, index, name):

        self.active_camera_index = index
        self.active_camera_name = name

    def updateCameraName(self, name):

        self.active_camera_name = name
