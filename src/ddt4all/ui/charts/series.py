"""Time-series buffer for the live charts panel. No Qt dependency."""
from __future__ import annotations

import bisect
import math
from typing import List, Optional, Sequence, Tuple

BUFFER_SECONDS = 600.0

Point = Tuple[float, Optional[float]]


def parse_value(raw) -> Optional[float]:
    """Turn a displayed ECU value ("13,9", "812", "ON", None) into a float or None."""
    if raw is None:
        return None
    try:
        value = float(str(raw).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


class Series:
    """Samples of one ECU parameter, kept for the last BUFFER_SECONDS."""

    def __init__(self, key: str, name: str, unit: str, color_index: int):
        self.key = key
        self.name = name
        self.unit = unit
        self.color_index = color_index
        self.polled = True
        self._t: List[float] = []
        self._v: List[Optional[float]] = []
        self._numeric_seen = False

    def __len__(self) -> int:
        return len(self._t)

    def append(self, t: float, v: Optional[float]) -> None:
        if self._t and t < self._t[-1]:
            t = self._t[-1]  # keep times monotonic for bisect
        self._t.append(t)
        self._v.append(v)
        if v is not None:
            self._numeric_seen = True
        cutoff = t - BUFFER_SECONDS
        if self._t[0] < cutoff:
            index = bisect.bisect_left(self._t, cutoff)
            del self._t[:index]
            del self._v[:index]

    def clear(self) -> None:
        self._t.clear()
        self._v.clear()
        self._numeric_seen = False

    def first_time(self) -> Optional[float]:
        return self._t[0] if self._t else None

    def last(self) -> Optional[Point]:
        return (self._t[-1], self._v[-1]) if self._t else None

    def has_numeric(self) -> bool:
        return self._numeric_seen

    def points(self) -> List[Point]:
        return list(zip(self._t, self._v))

    def visible(self, t0: float, t1: float) -> List[Point]:
        """Points inside [t0, t1] plus one neighbour on each side, so lines reach the edges."""
        if not self._t:
            return []
        start = max(bisect.bisect_left(self._t, t0) - 1, 0)
        stop = min(bisect.bisect_right(self._t, t1) + 1, len(self._t))
        return list(zip(self._t[start:stop], self._v[start:stop]))

    def visible_columns(self, t0: float, t1: float) -> Tuple[List[float], List[Optional[float]]]:
        """Same samples as visible(), but as parallel (times, values) lists without per-point work."""
        if not self._t:
            return [], []
        start = max(bisect.bisect_left(self._t, t0) - 1, 0)
        stop = min(bisect.bisect_right(self._t, t1) + 1, len(self._t))
        return self._t[start:stop], self._v[start:stop]

    def value_at(self, t: float) -> Optional[Point]:
        """Nearest sample to time t."""
        if not self._t:
            return None
        index = bisect.bisect_left(self._t, t)
        if index <= 0:
            best = 0
        elif index >= len(self._t):
            best = len(self._t) - 1
        else:
            best = index if self._t[index] - t < t - self._t[index - 1] else index - 1
        return self._t[best], self._v[best]


def _csv_number(value: Optional[float]) -> str:
    if value is None:
        return ""
    text = ("%.10f" % value).rstrip("0").rstrip(".")
    if text in ("", "-0"):
        text = "0"
    return text.replace(".", ",")


def _csv_header(text: str) -> str:
    """A header cell must not contain the separator or a line break, or columns shift."""
    return text.replace(";", " ").replace("\r", " ").replace("\n", " ")


def export_csv(series_list: Sequence[Series], path: str, t_origin: Optional[float] = None) -> None:
    """Write all buffered samples in the recorder format: ';' separator, ',' decimals."""
    if t_origin is None:
        firsts = [s.first_time() for s in series_list if len(s)]
        t_origin = min(firsts) if firsts else 0.0
    columns = [dict(s.points()) for s in series_list]
    times = sorted({t for column in columns for t in column})
    header = ["Time (ms)"] + [
        _csv_header("%s(%s)" % (s.name, s.unit) if s.unit else s.name) for s in series_list
    ]
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        handle.write(";".join(header) + "\n")
        for t in times:
            row = ["{:.3f}".format((t - t_origin) * 1000.0).replace(".", ",")]
            row.extend(_csv_number(column.get(t)) for column in columns)
            handle.write(";".join(row) + "\n")
