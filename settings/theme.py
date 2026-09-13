"""Application light / dark theme handling.

The chosen theme is persisted in settings/config.json under the "theme" key.
`apply_theme()` applies it to the running QApplication and to the main shell.
"""

import settings.preferences as prefs


# ============================================================
# PALETTES
# ============================================================

LIGHT = {
    "name": "Light",
    "bg": "#F5FEFF",
    "card": "#FFFFFF",
    "border": "#AAC0E1",
    "text": "#0E2F76",
    "text_secondary": "#5A6B93",
    "muted": "#AAC0E1",
    "sidebar": "#0E2F76",
    "sidebar_text": "#F5FEFF",
    "sidebar_hover": "#1B4499",
    "accent": "#AAC0E1",
    "accent_text": "#0E2F76",
    "input_bg": "#FFFFFF",
    "input_border": "#AAC0E1",
    "button_bg": "#FFFFFF",
    "button_text": "#5A6B93",
    "button_hover": "#EFF4FC",
    "primary": "#0E2F76",
    "primary_text": "#F5FEFF",
}

DARK = {
    "name": "Dark",
    "bg": "#0B1A30",
    "card": "#132742",
    "border": "#27496E",
    "text": "#E6EEF8",
    "text_secondary": "#9DB2CC",
    "muted": "#5A7396",
    "sidebar": "#081324",
    "sidebar_text": "#E6EEF8",
    "sidebar_hover": "#1B3A63",
    "accent": "#3E7CF7",
    "accent_text": "#0B1A30",
    "input_bg": "#0F2038",
    "input_border": "#27496E",
    "button_bg": "#132742",
    "button_text": "#C7D5EA",
    "button_hover": "#1B3A63",
    "primary": "#3E7CF7",
    "primary_text": "#0B1A30",
}

THEMES = {
    "Light": LIGHT,
    "Dark": DARK,
    "System Default": LIGHT,
}


# ============================================================
# CURRENT THEME
# ============================================================

def current_name():
    try:
        name = prefs.load().get("theme", "Light")
    except Exception:
        name = "Light"
    if name not in THEMES:
        name = "Light"
    return name


def colors():
    return THEMES.get(current_name(), LIGHT)


def set_theme(name):
    if name not in THEMES:
        name = "Light"
    prefs.save({"theme": name})


def is_dark():
    return current_name() == "Dark"


# ============================================================
# GLOBAL STYLESHEET (dialogs, tooltips, scrollbars)
# ============================================================

def global_stylesheet():
    """Stylesheet applied to the QApplication.

    Light mode keeps the existing per-page styling, so it returns an empty
    string. Dark mode also darkens generic dialogs/popups so they match.
    """

    if not is_dark():
        return ""

    c = DARK

    return f"""
        QMessageBox {{
            background-color: {c['card']};
        }}
        QMessageBox QLabel {{
            color: {c['text']};
        }}
        QMessageBox QPushButton {{
            background-color: {c['button_bg']};
            color: {c['text']};
            border: 1px solid {c['border']};
            border-radius: 6px;
            padding: 6px 14px;
            min-width: 70px;
        }}
        QMessageBox QPushButton:hover {{
            background-color: {c['button_hover']};
        }}
        QToolTip {{
            background-color: {c['card']};
            color: {c['text']};
            border: 1px solid {c['border']};
        }}
        QScrollBar:vertical {{
            background: {c['bg']};
            width: 12px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {c['border']};
            border-radius: 6px;
            min-height: 30px;
        }}
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QScrollBar:horizontal {{
            background: {c['bg']};
            height: 12px;
            margin: 0;
        }}
        QScrollBar::handle:horizontal {{
            background: {c['border']};
            border-radius: 6px;
            min-width: 30px;
        }}
        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {{
            width: 0;
        }}
    """
