"""Applies the Fluent theme (QSS template + QPalette) and exposes theme colours."""
import sys

import PyQt5.QtCore as core
import PyQt5.QtGui as gui

from ddt4all.ui.theme.palette import (
    DARK,
    LIGHT,
    SERIES_COLORS_DARK,
    SERIES_COLORS_LIGHT,
)

TEMPLATE_PATH = ":/styles/fluent.qss"

_state = {"dark": False}
_notifier = None


class _ThemeNotifier(core.QObject):
    changed = core.pyqtSignal()


def notifier():
    """Lazily created QObject whose `changed` signal fires after apply_theme()."""
    global _notifier
    if _notifier is None:
        _notifier = _ThemeNotifier()
    return _notifier


def is_dark():
    return _state["dark"]


def tokens():
    return DARK if _state["dark"] else LIGHT


def color(name):
    return gui.QColor(tokens()[name])


def series_colors():
    raw = SERIES_COLORS_DARK if _state["dark"] else SERIES_COLORS_LIGHT
    return [gui.QColor(value) for value in raw]


def _font_tokens():
    if sys.platform == "darwin":
        # macOS keeps 14pt with the system font (previous behaviour).
        return '".AppleSystemUIFont", "Helvetica Neue", "Arial", sans-serif', "14pt"
    return '"Segoe UI", "Noto Sans", "Arial", sans-serif', "10pt"


def _load_template():
    # Imported lazily: registering the compiled resources at import time made
    # unrelated icon lookups (created before any QApplication) abort the process.
    import ddt4all.generated.resources_rc  # noqa: F401  (registers :/styles/fluent.qss)
    qfile = core.QFile(TEMPLATE_PATH)
    if not qfile.open(core.QFile.ReadOnly):
        return ""
    try:
        return bytes(qfile.readAll()).decode("utf-8")
    finally:
        qfile.close()


def build_stylesheet(template, toks, font_family, font_size):
    qss = template.replace("{font_family}", font_family).replace("{font_size}", font_size)
    for key, value in toks.items():
        qss = qss.replace("{" + key + "}", value)
    return qss


def _build_palette(toks):
    pal = gui.QPalette()
    roles = {
        gui.QPalette.Window: toks["bg"],
        gui.QPalette.WindowText: toks["text"],
        gui.QPalette.Base: toks["surface"],
        gui.QPalette.AlternateBase: toks["surface_alt"],
        gui.QPalette.Text: toks["text"],
        gui.QPalette.Button: toks["surface"],
        gui.QPalette.ButtonText: toks["text"],
        gui.QPalette.ToolTipBase: toks["surface"],
        gui.QPalette.ToolTipText: toks["text"],
        gui.QPalette.Highlight: toks["accent"],
        gui.QPalette.HighlightedText: toks["accent_text"],
        gui.QPalette.Link: toks["accent"],
        gui.QPalette.PlaceholderText: toks["text_muted"],
        gui.QPalette.Light: toks["surface"],
        gui.QPalette.Midlight: toks["surface_alt"],
        gui.QPalette.Mid: toks["border_strong"],
        gui.QPalette.Dark: toks["border_strong"],
        gui.QPalette.Shadow: toks["border_strong"],
        gui.QPalette.BrightText: toks["error"],
    }
    for role, value in roles.items():
        pal.setColor(role, gui.QColor(value))
    for role in (gui.QPalette.WindowText, gui.QPalette.Text, gui.QPalette.ButtonText):
        pal.setColor(gui.QPalette.Disabled, role, gui.QColor(toks["text_muted"]))
    return pal


def apply_theme(app, dark):
    """Switch the whole application to the light or dark Fluent theme."""
    _state["dark"] = bool(dark)
    toks = tokens()
    app.setStyle("Fusion")
    app.setPalette(_build_palette(toks))
    font_family, font_size = _font_tokens()
    app.setStyleSheet(build_stylesheet(_load_template(), toks, font_family, font_size))
    notifier().changed.emit()
