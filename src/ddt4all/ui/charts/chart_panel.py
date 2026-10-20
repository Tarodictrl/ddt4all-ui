"""Charts dock content: toolbar, empty-state hint and the lane view."""
from __future__ import annotations

import datetime
import logging
import os
import time
from typing import Callable, Dict, Iterable, Optional, Set

import PyQt5.QtCore as core
import PyQt5.QtWidgets as widgets

import ddt4all.options as options
from ddt4all.file_manager import get_logs_dir
from ddt4all.ui.charts.lane_view import LaneView
from ddt4all.ui.charts.series import Series, export_csv, parse_value
from ddt4all.ui.theme import theme

_ = options.translator('ddt4all')
log = logging.getLogger(__name__)

MAX_SERIES = 8
WINDOW_CHOICES = (30, 60, 120, 300)
DEFAULT_WINDOW_S = 60
REPAINT_MS = 100


class ChartPanel(widgets.QWidget):
    series_added = core.pyqtSignal(str)
    series_removed = core.pyqtSignal(str)
    limit_reached = core.pyqtSignal()

    def __init__(self, parent=None, clock: Callable[[], float] = time.monotonic):
        super().__init__(parent)
        self.setObjectName("chartPanel")
        self.setAttribute(core.Qt.WA_StyledBackground, True)
        self._clock = clock
        self._series: Dict[str, Series] = {}
        self._polled: Optional[Set[str]] = None
        self._paused_edge: Optional[float] = None
        self._refresh_ms = 100
        self._window_s = DEFAULT_WINDOW_S

        title = widgets.QLabel(_("Charts"))
        title_font = title.font()
        title_font.setBold(True)
        title.setFont(title_font)

        self.pause_button = widgets.QPushButton(_("Pause"))
        self.pause_button.setCheckable(True)
        self.pause_button.setProperty("primary", True)
        self.pause_button.toggled.connect(self._on_pause_toggled)

        self.window_combo = widgets.QComboBox()
        for seconds in WINDOW_CHOICES:
            self.window_combo.addItem("%d %s" % (seconds, _("s")), seconds)
        self.window_combo.setCurrentIndex(WINDOW_CHOICES.index(DEFAULT_WINDOW_S))
        self.window_combo.currentIndexChanged.connect(self._on_window_changed)

        self.csv_button = widgets.QPushButton(_("Export CSV"))
        self.csv_button.clicked.connect(self.export_csv_dialog)
        self.clear_button = widgets.QPushButton(_("Clear"))
        self.clear_button.clicked.connect(self.clear_data)
        self.state_label = widgets.QLabel("")

        toolbar = widgets.QWidget()
        toolbar.setObjectName("chartToolbar")
        toolbar.setAttribute(core.Qt.WA_StyledBackground, True)
        toolbar_layout = widgets.QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 6, 8, 6)
        toolbar_layout.setSpacing(6)
        toolbar_layout.addWidget(title)
        toolbar_layout.addSpacing(8)
        toolbar_layout.addWidget(self.pause_button)
        toolbar_layout.addWidget(self.window_combo)
        toolbar_layout.addWidget(self.csv_button)
        toolbar_layout.addWidget(self.clear_button)
        toolbar_layout.addSpacing(8)
        toolbar_layout.addWidget(self.state_label)
        toolbar_layout.addStretch(1)

        self.lane_view = LaneView()
        self.lane_view.remove_requested.connect(self.remove_series)
        self.lane_view.scroll_requested.connect(self._on_scroll)
        scroll = widgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(widgets.QFrame.NoFrame)
        scroll.setWidget(self.lane_view)

        empty = widgets.QLabel(_("Right-click a value on the screen → Add to chart"))
        empty.setObjectName("chartEmptyHint")
        empty.setAlignment(core.Qt.AlignCenter)

        self.stack = widgets.QStackedWidget()
        self.stack.addWidget(empty)
        self.stack.addWidget(scroll)

        layout = widgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(toolbar)
        layout.addWidget(self.stack, 1)

        self.timer = core.QTimer(self)
        self.timer.setInterval(REPAINT_MS)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start()

        theme.notifier().changed.connect(self.lane_view.update)
        self.lane_view.window_s = float(self._window_s)
        self.lane_view.refresh_ms = self._refresh_ms
        self._sync_view()

    # ---- public API ----
    def add_series(self, key: str, name: str, unit: str) -> bool:
        if key in self._series:
            return True
        if len(self._series) >= MAX_SERIES:
            self.limit_reached.emit()
            return False
        used = {s.color_index for s in self._series.values()}
        color_index = next(i for i in range(MAX_SERIES) if i not in used)
        series = Series(key, name, unit, color_index)
        series.polled = self._polled is None or key in self._polled
        self._series[key] = series
        self._sync_view()
        self.series_added.emit(key)
        return True

    def remove_series(self, key: str) -> None:
        if self._series.pop(key, None) is None:
            return
        if not self._series and self.pause_button.isChecked():
            self.pause_button.setChecked(False)
        self._sync_view()
        self.series_removed.emit(key)

    def has_series(self, key: str) -> bool:
        return key in self._series

    def push(self, key: str, t: float, value_str: Optional[str]) -> None:
        try:
            series = self._series.get(key)
            if series is not None:
                series.append(t, parse_value(value_str))
        except Exception:
            log.exception("Chart push failed for %s", key)

    def set_polled_keys(self, keys: Iterable[str]) -> None:
        self._polled = set(keys)
        for key, series in self._series.items():
            series.polled = key in self._polled
        self.lane_view.update()

    def set_refresh_ms(self, ms: int) -> None:
        self._refresh_ms = max(1, int(ms))
        self.lane_view.refresh_ms = self._refresh_ms

    def window_s(self) -> int:
        return self._window_s

    def set_window_s(self, seconds) -> None:
        try:
            seconds = int(seconds)
        except (TypeError, ValueError):
            seconds = DEFAULT_WINDOW_S
        if seconds not in WINDOW_CHOICES:
            seconds = DEFAULT_WINDOW_S
        index = WINDOW_CHOICES.index(seconds)
        self.window_combo.setCurrentIndex(index)
        self._on_window_changed(index)

    def clear_data(self) -> None:
        for series in self._series.values():
            series.clear()
        self.lane_view.update()
        self._update_controls()

    def clear_all(self) -> None:
        keys = list(self._series)
        self._series.clear()
        self._polled = None
        self.pause_button.setChecked(False)
        self._sync_view()
        for key in keys:
            self.series_removed.emit(key)

    def export_csv_dialog(self) -> None:
        series = [s for s in self._series.values() if len(s)]
        if not series:
            return
        default = os.path.join(str(get_logs_dir()),
                               datetime.datetime.now().strftime("chart_%Y%m%d_%H%M%S.csv"))
        path, _filter = widgets.QFileDialog.getSaveFileName(self, _("Export CSV"), default, "CSV (*.csv)")
        if not path:
            return
        try:
            export_csv(series, path)
        except OSError as error:
            widgets.QMessageBox.warning(self, _("Export CSV"), _("Cannot write file: %s") % error)

    # ---- internals ----
    def _right_edge(self) -> float:
        return self._paused_edge if self._paused_edge is not None else self._clock()

    def _sync_view(self) -> None:
        self.lane_view.set_series(self._series.values())
        self.lane_view.right_edge = self._right_edge()
        self.stack.setCurrentIndex(1 if self._series else 0)
        self._update_controls()

    def _update_controls(self) -> None:
        has_points = any(len(s) for s in self._series.values())
        self.csv_button.setEnabled(has_points)
        self.clear_button.setEnabled(has_points)
        self.pause_button.setEnabled(bool(self._series))
        if self._paused_edge is not None:
            behind = max(0.0, self._clock() - self._paused_edge)
            self.state_label.setText("%s · −%d %s" % (_("Paused"), round(behind), _("s")))
        else:
            self.state_label.setText("")

    def _on_tick(self) -> None:
        try:
            if self._series and self._paused_edge is None:
                self.lane_view.right_edge = self._clock()
                self.lane_view.update()
            self._update_controls()
        except Exception:
            log.exception("Chart tick failed")

    def _on_pause_toggled(self, paused: bool) -> None:
        if paused:
            self._paused_edge = self._clock()
            self.pause_button.setText(_("Resume"))
        else:
            self._paused_edge = None
            self.pause_button.setText(_("Pause"))
        self.lane_view.wheel_scrolls_time = paused
        self.lane_view.right_edge = self._right_edge()
        self.lane_view.update()
        self._update_controls()

    def _on_window_changed(self, index: int) -> None:
        seconds = self.window_combo.itemData(index)
        if seconds:
            self._window_s = int(seconds)
            self.lane_view.window_s = float(seconds)
            self.lane_view.update()

    def _on_scroll(self, delta: int) -> None:
        if self._paused_edge is None or delta == 0:
            return
        firsts = [s.first_time() for s in self._series.values() if len(s)]
        if not firsts:
            return
        step = self._window_s * 0.1
        edge = self._paused_edge + (-step if delta > 0 else step)  # wheel up = back in time
        now = self._clock()
        earliest = min(min(firsts) + self._window_s, now)
        self._paused_edge = max(earliest, min(edge, now))
        self.lane_view.right_edge = self._paused_edge
        self.lane_view.update()
        self._update_controls()
