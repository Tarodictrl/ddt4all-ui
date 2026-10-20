"""QPainter widget drawing one lane per parameter with a shared time axis."""
from __future__ import annotations

import array
import logging
import operator
from bisect import bisect_left, bisect_right
from typing import Iterable, List, Optional, Sequence, Tuple

import PyQt5.QtCore as core
import PyQt5.QtGui as gui
import PyQt5.QtWidgets as widgets

import ddt4all.options as options
from ddt4all.ui.charts.series import Point, Series
from ddt4all.ui.theme import theme

_ = options.translator('ddt4all')
log = logging.getLogger(__name__)

LEFT_W = 110        # name / value column
Y_LABEL_W = 44      # min / max labels
AXIS_H = 22         # time axis
PAD = 8
LANE_MIN_H = 48
CLOSE_SIZE = 14
TICK_STEPS = (1, 2, 5, 10, 15, 30, 60, 120)
MAX_TICKS = 6


def format_value(v: Optional[float]) -> str:
    if v is None:
        return "—"
    if float(v).is_integer():
        return str(int(v))
    text = "{:.3f}".format(v).rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def _gap_from_times(times: Sequence[float], refresh_ms: int) -> float:
    diffs = sorted(b - a for a, b in zip(times, times[1:]) if b > a)
    median = diffs[len(diffs) // 2] if diffs else 0.0
    return max(3.0 * median, 3.0 * refresh_ms / 1000.0, 0.5)


def gap_threshold(points: Sequence[Point], refresh_ms: int) -> float:
    """Break the line when samples are further apart than ~3 real polling periods."""
    return _gap_from_times([t for t, _v in points[-51:]], refresh_ms)


def split_runs(points: Sequence[Point], gap: float) -> List[List[Tuple[float, float]]]:
    """Split samples into continuous runs at None values and time gaps."""
    runs: List[List[Tuple[float, float]]] = []
    current: List[Tuple[float, float]] = []
    prev_t: Optional[float] = None
    for t, v in points:
        if v is None or (prev_t is not None and t - prev_t > gap):
            if current:
                runs.append(current)
            current = []
        if v is not None:
            current.append((t, v))
        prev_t = t
    if current:
        runs.append(current)
    return runs


def decimate(xy: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Keep min and max y per pixel column so peaks survive downsampling."""
    out: List[Tuple[float, float]] = []
    column: Optional[int] = None
    low = high = 0.0
    for x, y in xy:
        c = int(x)
        if c != column:
            if column is not None:
                out.append((float(column), low))
                if high != low:
                    out.append((float(column), high))
            column, low, high = c, y, y
        else:
            low = min(low, y)
            high = max(high, y)
    if column is not None:
        out.append((float(column), low))
        if high != low:
            out.append((float(column), high))
    return out


def decimate_run(ts: Sequence[float], vs: Sequence[float], t0: float, t1: float,
                 columns: int) -> Tuple[Sequence[float], Sequence[float]]:
    """Reduce one continuous run to min/max per pixel column, working on times.

    ``columns`` is the plot width in pixels. Runs that already have no more points
    than that are returned unchanged. Points outside [t0, t1] (the neighbours that
    let the line reach the edges) are kept as they are. Reduced points carry the
    time of their column centre, so they map back to pixels like any other sample.
    Returns the new (times, values) pair.
    """
    low_i = bisect_left(ts, t0)
    high_i = bisect_right(ts, t1)
    columns = max(1, int(columns))
    if high_i - low_i <= columns or t1 <= t0:
        return ts, vs
    out_t = list(ts[:low_i])
    out_v = list(vs[:low_i])
    add_t, add_v = out_t.append, out_v.append
    step = (t1 - t0) / columns
    start = low_i
    last = columns - 1
    for c in range(columns):
        stop = high_i if c == last else bisect_left(ts, t0 + (c + 1) * step, start, high_i)
        if stop <= start:
            continue
        tc = t0 + (c + 0.5) * step
        if stop - start == 1:
            add_t(tc)
            add_v(vs[start])
        else:
            chunk = vs[start:stop]
            low = min(chunk)
            high = max(chunk)
            add_t(tc)
            if low == high:
                add_v(low)
            else:
                add_t(tc)
                if chunk[0] > chunk[-1]:  # falling inside the column: keep the stroke direction
                    add_v(high)
                    add_v(low)
                else:
                    add_v(low)
                    add_v(high)
        start = stop
    out_t.extend(ts[high_i:])
    out_v.extend(vs[high_i:])
    return out_t, out_v


def _runs(ts: Sequence[float], vs: Sequence[Optional[float]],
          refresh_ms: int) -> List[Tuple[Sequence[float], Sequence[float]]]:
    """Continuous runs as (times, values) pairs; the common gap-free case avoids per-point Python."""
    if not ts:
        return []
    gap = _gap_from_times(ts[-51:], refresh_ms)
    if None not in vs and (len(ts) < 2 or max(map(operator.sub, ts[1:], ts)) <= gap):
        return [(ts, vs)]
    runs = []
    for run in split_runs(list(zip(ts, vs)), gap):
        rt, rv = zip(*run)
        runs.append((rt, rv))
    return runs


def _polygon(xs: Sequence[float], ys: Sequence[float]) -> gui.QPolygonF:
    """Build a QPolygonF from coordinate lists; fills the buffer directly when PyQt allows it."""
    n = len(xs)
    try:
        poly = gui.QPolygonF(n)
        raw = poly.data()
        raw.setsize(n * 16)  # QPointF is two doubles
        coords = array.array("d", bytes(n * 16))
        coords[0::2] = array.array("d", xs)
        coords[1::2] = array.array("d", ys)
        memoryview(raw).cast("B").cast("d")[:] = coords
        return poly
    except (AttributeError, TypeError, ValueError, BufferError):
        return gui.QPolygonF(list(map(core.QPointF, xs, ys)))


class LaneView(widgets.QWidget):
    remove_requested = core.pyqtSignal(str)
    scroll_requested = core.pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.series: List[Series] = []
        self.window_s = 60.0
        self.right_edge = 0.0
        self.refresh_ms = 100
        self.wheel_scrolls_time = False
        self._hover: Optional[core.QPoint] = None
        self._paint_failed = False
        self.setMouseTracking(True)
        self.setMinimumHeight(LANE_MIN_H + AXIS_H)

    # ---- state ----
    def set_series(self, series: Iterable[Series]) -> None:
        self.series = list(series)
        self.setMinimumHeight(max(1, len(self.series)) * LANE_MIN_H + AXIS_H)
        self.update()

    # ---- geometry ----
    def _plot_rect(self) -> core.QRectF:
        left = float(LEFT_W + Y_LABEL_W)
        width = max(1.0, self.width() - left - PAD)
        height = max(1.0, float(self.height() - AXIS_H))
        return core.QRectF(left, 0.0, width, height)

    def _lane_height(self) -> float:
        return (self.height() - AXIS_H) / max(1, len(self.series))

    def _lane_index_at(self, y: int) -> Optional[int]:
        if not self.series or y < 0 or y >= self.height() - AXIS_H:
            return None
        return min(int(y // self._lane_height()), len(self.series) - 1)

    def _close_rect(self, lane_top: float) -> core.QRectF:
        return core.QRectF(LEFT_W - CLOSE_SIZE - 4, lane_top + 3, CLOSE_SIZE, CLOSE_SIZE)

    def _cursor_time(self) -> Optional[float]:
        if self._hover is None:
            return None
        plot = self._plot_rect()
        x = float(self._hover.x())
        if x < plot.left() or x > plot.right() or self._hover.y() > plot.bottom():
            return None
        return self.right_edge - self.window_s + (x - plot.left()) / plot.width() * self.window_s

    # ---- painting ----
    def paintEvent(self, event):
        painter = gui.QPainter(self)
        try:
            self._paint(painter)
        except Exception:
            if not self._paint_failed:
                self._paint_failed = True
                log.exception("Chart paint failed")
        finally:
            painter.end()

    def _fonts(self):
        small = gui.QFont(self.font())
        small.setPointSizeF(max(7.0, small.pointSizeF() * 0.85))
        big = gui.QFont(self.font())
        big.setPointSizeF(13.0)
        big.setBold(True)
        return small, big

    def _paint(self, p: gui.QPainter) -> None:
        p.fillRect(self.rect(), theme.color("surface"))
        if not self.series:
            return
        p.setRenderHint(gui.QPainter.Antialiasing, True)
        plot = self._plot_rect()
        lane_h = self._lane_height()
        t1 = self.right_edge
        t0 = t1 - self.window_s
        cursor_t = self._cursor_time()
        hover_index = self._lane_index_at(self._hover.y()) if self._hover is not None else None
        colors = theme.series_colors()
        small, big = self._fonts()
        for index, series in enumerate(self.series):
            lane = core.QRectF(0.0, index * lane_h, float(self.width()), lane_h)
            color = colors[series.color_index % len(colors)] if series.polled else theme.color("text_muted")
            self._paint_lane(p, series, lane, plot, t0, t1, cursor_t, color, hover_index == index, small, big)
        self._paint_axis(p, plot, small)
        if cursor_t is not None:
            p.setPen(gui.QPen(theme.color("text_muted"), 1, core.Qt.DashLine))
            x = float(self._hover.x())
            p.drawLine(core.QPointF(x, 0.0), core.QPointF(x, plot.bottom()))

    def _paint_lane(self, p, series, lane, plot, t0, t1, cursor_t, color, hovered, small, big):
        small_fm = gui.QFontMetrics(small)
        p.setPen(gui.QPen(theme.color("border"), 1))
        p.drawLine(core.QPointF(0.0, lane.bottom()), core.QPointF(lane.right(), lane.bottom()))
        p.fillRect(core.QRectF(0.0, lane.top() + 4, 3.0, max(1.0, lane.height() - 8)), color)

        # Name and unit
        title = "%s, %s" % (series.name, series.unit) if series.unit else series.name
        title_w = LEFT_W - CLOSE_SIZE - 14
        p.setFont(small)
        p.setPen(theme.color("text_muted"))
        p.drawText(core.QRectF(8.0, lane.top() + 4, title_w, small_fm.height()),
                   core.Qt.AlignLeft | core.Qt.AlignVCenter,
                   small_fm.elidedText(title, core.Qt.ElideRight, title_w))

        # Value at cursor, or the latest one
        point = series.value_at(cursor_t) if cursor_t is not None else series.last()
        value = point[1] if point is not None else None
        p.setFont(big)
        p.setPen(theme.color("text") if (value is not None and series.polled) else theme.color("text_muted"))
        value_top = lane.top() + 4 + small_fm.height()
        p.drawText(core.QRectF(8.0, value_top, LEFT_W - 12, max(1.0, lane.bottom() - value_top - 4)),
                   core.Qt.AlignLeft | core.Qt.AlignVCenter, format_value(value))

        if hovered:
            p.setFont(small)
            p.setPen(theme.color("text_muted"))
            p.drawText(self._close_rect(lane.top()), core.Qt.AlignCenter, "×")

        area = core.QRectF(plot.left(), lane.top() + 6, plot.width(), max(4.0, lane.height() - 12))
        p.setFont(small)
        if not series.polled:
            p.setPen(theme.color("text_muted"))
            p.drawText(area, core.Qt.AlignRight | core.Qt.AlignTop, _("not polled"))
        if not series.has_numeric():
            p.setPen(theme.color("text_muted"))
            p.drawText(area, core.Qt.AlignCenter, _("no numeric data"))
            return

        runs = _runs(*series.visible_columns(t0, t1), self.refresh_ms)
        if not runs:
            return
        data_min = min(min(vs) for _ts, vs in runs)
        data_max = max(max(vs) for _ts, vs in runs)
        vmin, vmax = data_min, data_max
        if vmax == vmin:
            vmin, vmax = vmin - 1.0, vmax + 1.0
        else:
            margin = (vmax - vmin) * 0.1
            vmin, vmax = vmin - margin, vmax + margin

        # Min / max labels (real data extremes) and a middle grid line
        p.setPen(theme.color("text_muted"))
        label_w = Y_LABEL_W - 6
        p.drawText(core.QRectF(LEFT_W, area.top() - 2, label_w, small_fm.height()),
                   core.Qt.AlignRight | core.Qt.AlignTop, format_value(data_max))
        p.drawText(core.QRectF(LEFT_W, area.bottom() - small_fm.height() + 2, label_w, small_fm.height()),
                   core.Qt.AlignRight | core.Qt.AlignBottom, format_value(data_min))
        p.setPen(gui.QPen(theme.color("border"), 1))
        mid = area.center().y()
        p.drawLine(core.QPointF(area.left(), mid), core.QPointF(area.right(), mid))

        span_t = max(t1 - t0, 1e-6)
        span_v = vmax - vmin

        left, width, bottom, height = area.left(), area.width(), area.bottom(), area.height()
        kx = width / span_t
        ky = height / span_v
        p.save()
        p.setClipRect(area.adjusted(0, -2, 0, 2))
        pen = gui.QPen(color, 1.0)
        pen.setCosmetic(True)
        p.setPen(pen)
        columns = int(width)
        for ts, vs in runs:
            ts, vs = decimate_run(ts, vs, t0, t1, columns)
            xs = [left + (t - t0) * kx for t in ts]
            ys = [bottom - (v - vmin) * ky for v in vs]
            if len(xs) == 1:
                p.drawEllipse(core.QPointF(xs[0], ys[0]), 1.5, 1.5)
                continue
            p.drawPolyline(_polygon(xs, ys))
        p.restore()

    def _paint_axis(self, p, plot, small):
        top = plot.bottom()
        p.setPen(gui.QPen(theme.color("border"), 1))
        p.drawLine(core.QPointF(plot.left(), top), core.QPointF(plot.right(), top))
        step = next((s for s in TICK_STEPS if self.window_s / s <= MAX_TICKS), TICK_STEPS[-1])
        p.setFont(small)
        p.setPen(theme.color("text_muted"))
        k = 0
        while k * step <= self.window_s + 1e-9:
            x = plot.right() - k * step / self.window_s * plot.width()
            p.drawLine(core.QPointF(x, top), core.QPointF(x, top + 4))
            label = "0 %s" % _("s") if k == 0 else "−%d %s" % (k * step, _("s"))
            p.drawText(core.QRectF(x - 30, top + 4, 60, AXIS_H - 4),
                       core.Qt.AlignHCenter | core.Qt.AlignTop, label)
            k += 1

    # ---- mouse ----
    def mouseMoveEvent(self, event):
        self._hover = event.pos()
        self.update()

    def leaveEvent(self, event):
        self._hover = None
        self.update()

    def mousePressEvent(self, event):
        if event.button() == core.Qt.LeftButton:
            index = self._lane_index_at(event.pos().y())
            if index is not None:
                close = self._close_rect(index * self._lane_height())
                if close.contains(core.QPointF(event.pos())):
                    self.remove_requested.emit(self.series[index].key)
                    event.accept()
                    return
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        if not self.wheel_scrolls_time:
            event.ignore()  # let the surrounding scroll area scroll the lanes
            return
        self.scroll_requested.emit(event.angleDelta().y())
        event.accept()
