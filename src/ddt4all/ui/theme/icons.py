"""Theme-aware SVG icons.

``icon(name)`` returns a ``QIcon`` backed by :class:`SvgIconEngine`. The engine
does not keep rasterised pixels: every ``paint()`` / ``pixmap()`` call picks the
colour from the *current* theme tokens and renders the SVG (``resources/icons/svg``)
with that colour. A ``QIcon`` created once therefore follows light/dark switches
automatically: widgets only have to repaint.

Colour per mode/state (tokens from ``ddt4all.ui.theme.theme.tokens()``):

===============================  ==================================
Disabled                         ``text_muted``
``danger=True`` (any other mode  ``warn``  (also when checked / hovered: writing
or state)                        enabled is exactly when the warning matters)
Active (hover) or state On       ``accent``
Selected                         ``accent``  (see note below)
Normal                           ``text``
===============================  ==================================

Selected note: the application stylesheet paints selected list/tree/menu items
with ``accent_soft`` background and ``accent`` text, so an ``accent_text``
(white / near-black) glyph would be unreadable on them; ``accent`` is used.

Caveat: ``QIcon.pixmap()`` returns a *snapshot*. A widget that caches such a pixmap
itself (instead of painting the icon) keeps the old colour after a theme switch and
must re-request it, e.g. from ``theme.notifier().changed``.
"""
import logging

import PyQt5.QtCore as core
import PyQt5.QtGui as gui
from PyQt5 import QtSvg

from ddt4all.ui.theme import theme

log = logging.getLogger(__name__)

ICON_PATH = ":/icons/svg/{}.svg"

_svg_sources = {}    # name -> str (SVG text) or None when missing
_renderers = {}      # (name, "#rrggbb") -> QSvgRenderer
_warned = set()      # names already reported as unknown


def _load_source(name):
    """SVG text of ``name`` (read once from the Qt resources) or None."""
    if name in _svg_sources:
        return _svg_sources[name]
    # Imported lazily: registering the compiled resources at import time made
    # unrelated icon lookups (created before any QApplication) abort the process.
    import ddt4all.generated.resources_rc  # noqa: F401  (registers :/icons/...)
    source = None
    qfile = core.QFile(ICON_PATH.format(name))
    if qfile.open(core.QFile.ReadOnly):
        try:
            source = bytes(qfile.readAll()).decode("utf-8")
        finally:
            qfile.close()
    if source is None and name not in _warned:
        _warned.add(name)
        log.warning("Unknown icon '%s' (%s not found)", name, ICON_PATH.format(name))
    _svg_sources[name] = source
    return source


def _renderer(name, colour):
    """Cached QSvgRenderer for ``name`` drawn with ``colour`` (a QColor) or None."""
    key = (name, colour.name())
    renderer = _renderers.get(key)
    if renderer is None:
        source = _load_source(name)
        if source is None:
            return None
        data = source.replace("currentColor", colour.name())
        renderer = QtSvg.QSvgRenderer(core.QByteArray(data.encode("utf-8")))
        if not renderer.isValid():
            log.warning("Icon '%s' is not a valid SVG", name)
            return None
        _renderers[key] = renderer
    return renderer


def _colour(mode, state, danger):
    if mode == gui.QIcon.Disabled:
        return theme.color("text_muted")
    if danger:
        return theme.color("warn")
    if mode in (gui.QIcon.Active, gui.QIcon.Selected) or state == gui.QIcon.On:
        return theme.color("accent")
    return theme.color("text")


class SvgIconEngine(gui.QIconEngine):
    """QIconEngine rendering an SVG from the resources with the live theme colour."""

    def __init__(self, name, danger=False):
        super().__init__()
        self._name = name
        self._danger = danger

    def clone(self):
        return SvgIconEngine(self._name, self._danger)

    def actualSize(self, size, mode, state):
        return size

    def paint(self, painter, rect, mode, state):
        renderer = _renderer(self._name, _colour(mode, state, self._danger))
        if renderer is None or rect.isEmpty():
            return
        # Vector drawing straight into the painter: crisp on any device ratio.
        # Keep the aspect ratio: the largest centred square that fits the rect.
        side = min(rect.width(), rect.height())
        target = core.QRectF(
            rect.x() + (rect.width() - side) / 2.0,
            rect.y() + (rect.height() - side) / 2.0,
            side,
            side,
        )
        painter.save()
        painter.setRenderHint(gui.QPainter.Antialiasing, True)
        painter.setRenderHint(gui.QPainter.SmoothPixmapTransform, True)
        renderer.render(painter, target)
        painter.restore()

    def pixmap(self, size, mode, state):
        """Render exactly ``size`` device pixels at devicePixelRatio 1.0.

        Qt5 does not call a ``scaledPixmap`` override (it is not virtual in
        PyQt5), so QIcon.pixmap() on a HiDPI screen asks for ``size * ratio``
        device pixels here and then labels the result with the right ratio
        itself (QIcon::pixmap with Qt.AA_UseHighDpiPixmaps). Pre-multiplying by
        the application ratio here would double the size.
        """
        width, height = max(1, size.width()), max(1, size.height())
        pixmap = gui.QPixmap(width, height)
        pixmap.fill(core.Qt.transparent)
        painter = gui.QPainter(pixmap)
        try:
            self.paint(painter, core.QRect(0, 0, width, height), mode, state)
        finally:
            painter.end()
        return pixmap


def icon(name, danger=False):
    """Theme-aware icon for ``resources/icons/svg/<name>.svg`` (empty icon when unknown)."""
    if _load_source(name) is None:
        return gui.QIcon()
    return gui.QIcon(SvgIconEngine(name, danger))
