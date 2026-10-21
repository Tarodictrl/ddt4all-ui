"""Applies the Fluent theme (QSS template + QPalette) and exposes theme colours."""
import logging
import sys

import PyQt5.QtCore as core
import PyQt5.QtGui as gui
import PyQt5.QtWidgets as widgets

from ddt4all.ui.theme.palette import (
    DARK,
    LIGHT,
    SERIES_COLORS_DARK,
    SERIES_COLORS_LIGHT,
)

log = logging.getLogger(__name__)

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
        log.warning("Cannot open theme template %s; no stylesheet applied", TEMPLATE_PATH)
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


def _arrow_tokens(dark, hidpi=False):
    """QSS-only tokens: the chevron PNGs for combo boxes and spin boxes.

    Kept out of palette.py on purpose: those dicts feed QPalette and tokens(),
    and a resource path is not a colour. The `-light`/`-dark` suffix names the
    theme the arrow is drawn for; a matching `@2x` file sits next to each.
    """
    # Qt does not pick @2x variants for QSS url(), so choose them explicitly
    # on high-DPI screens; the QSS width/height keeps the logical size.
    suffix = ("dark" if dark else "light") + ("@2x" if hidpi else "")
    return {
        "arrow_down": ":/icons/chevron-down-%s.png" % suffix,
        "arrow_up": ":/icons/chevron-up-%s.png" % suffix,
    }


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


# ---- Native Windows title bar -------------------------------------------
# The caption bar is drawn by Windows (DWM), not by Qt, so the stylesheet cannot
# reach it. DWM attributes switch it to dark mode (Windows 10 1809+) and, on
# Windows 11, set the exact caption and title text colours.
_DWMWA_USE_IMMERSIVE_DARK_MODE = 20
_DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19
_DWMWA_CAPTION_COLOR = 35
_DWMWA_TEXT_COLOR = 36
_DWMWA_COLOR_DEFAULT = 0xFFFFFFFF
_SWP_FRAMECHANGED_FLAGS = 0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020  # NOSIZE|NOMOVE|NOZORDER|NOACTIVATE|FRAMECHANGED

_title_bar_filter = None


def _colorref(hex_color):
    qcolor = gui.QColor(hex_color)
    return qcolor.red() | (qcolor.green() << 8) | (qcolor.blue() << 16)


def apply_title_bar(widget):
    """Match a top-level window's native Windows title bar to the current theme."""
    if sys.platform != "win32" or not widget.isWindow():
        return
    try:
        import ctypes
        from ctypes import wintypes

        hwnd = wintypes.HWND(int(widget.winId()))
        dwm = ctypes.windll.dwmapi
        dark = ctypes.c_int(1 if _state["dark"] else 0)
        for attribute in (_DWMWA_USE_IMMERSIVE_DARK_MODE, _DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1):
            if dwm.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(dark), ctypes.sizeof(dark)) == 0:
                break
        toks = tokens()
        if _state["dark"]:
            caption, text = _colorref(toks["surface"]), _colorref(toks["text"])
        else:
            caption = text = _DWMWA_COLOR_DEFAULT
        for attribute, value in ((_DWMWA_CAPTION_COLOR, caption), (_DWMWA_TEXT_COLOR, text)):
            colour = ctypes.c_uint(value)
            dwm.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(colour), ctypes.sizeof(colour))
        # Windows 10 repaints the caption only after a frame change.
        ctypes.windll.user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, _SWP_FRAMECHANGED_FLAGS)
    except Exception:
        log.debug("Cannot theme the native title bar", exc_info=True)


class _TitleBarFilter(core.QObject):
    """Themes the title bar of every window and dialog when it is first shown."""

    def eventFilter(self, obj, event):
        if event.type() == core.QEvent.Show and isinstance(obj, widgets.QWidget) and obj.isWindow():
            apply_title_bar(obj)
        return False


def _install_title_bar_support(app):
    global _title_bar_filter
    if sys.platform != "win32":
        return
    if _title_bar_filter is None:
        _title_bar_filter = _TitleBarFilter(app)
        app.installEventFilter(_title_bar_filter)
    for window in app.topLevelWidgets():
        if window.isVisible():
            apply_title_bar(window)


def apply_theme(app, dark):
    """Switch the whole application to the light or dark Fluent theme."""
    _state["dark"] = bool(dark)
    toks = tokens()
    app.setStyle("Fusion")
    app.setPalette(_build_palette(toks))
    font_family, font_size = _font_tokens()
    qss_tokens = dict(toks)
    qss_tokens.update(_arrow_tokens(_state["dark"], app.devicePixelRatio() >= 1.5))
    app.setStyleSheet(build_stylesheet(_load_template(), qss_tokens, font_family, font_size))
    _install_title_bar_support(app)
    notifier().changed.emit()
