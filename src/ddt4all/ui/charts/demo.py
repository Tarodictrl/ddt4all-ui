"""Manual check for the charts panel without an adapter.

Run: python -m ddt4all.ui.charts.demo [--dark]
"""
import math
import random
import sys
import time

import PyQt5.QtCore as core
import PyQt5.QtWidgets as widgets

import ddt4all.version as version
from ddt4all.ui.charts.chart_panel import ChartPanel
from ddt4all.ui.theme import theme

DEMO_SERIES = [
    ("demo/rpm", "Engine speed", "rpm"),
    ("demo/coolant", "Coolant temp", "°C"),
    ("demo/battery", "Battery", "V"),
    ("demo/gaps", "With gaps", ""),
    ("demo/const", "Constant", "%"),
    ("demo/text", "Text value", ""),
]


def main():
    widgets.QApplication.setAttribute(core.Qt.AA_UseHighDpiPixmaps, True)
    app = widgets.QApplication(sys.argv)
    theme.apply_theme(app, "--dark" in sys.argv)

    window = widgets.QMainWindow()
    window.setWindowTitle(version.__appname__ + " charts demo")
    panel = ChartPanel()
    panel.set_refresh_ms(100)
    dock = widgets.QDockWidget("Charts", window)
    dock.setWidget(panel)
    window.setCentralWidget(widgets.QLabel("ECU screen placeholder", alignment=core.Qt.AlignCenter))
    window.addDockWidget(core.Qt.BottomDockWidgetArea, dock)
    window.resizeDocks([dock], [360], core.Qt.Vertical)

    for key, name, unit in DEMO_SERIES:
        panel.add_series(key, name, unit)

    started = time.monotonic()
    state = {"extra": 0, "battery_polled": True}

    def tick():
        now = time.monotonic()
        elapsed = now - started
        rpm = 800 + 400 * math.sin(elapsed / 3.0) + random.uniform(-20, 20)
        panel.push("demo/rpm", now, "%.0f" % rpm)
        panel.push("demo/coolant", now, ("%.1f" % (20 + 5 * int(elapsed / 5))).replace(".", ","))
        panel.push("demo/battery", now, "%.2f" % (13.9 + 0.1 * math.sin(elapsed)))
        gaps = None if int(elapsed) % 7 < 2 else "%.2f" % (50 * math.sin(elapsed))
        panel.push("demo/gaps", now, gaps)
        panel.push("demo/const", now, "42")
        panel.push("demo/text", now, "ON")
        for i in range(state["extra"]):
            panel.push("demo/extra%d" % i, now, "%.1f" % (i * 10 + random.random()))

    feed = core.QTimer()
    feed.setInterval(100)
    feed.timeout.connect(tick)
    feed.start()

    toolbar = window.addToolBar("Demo")

    def toggle_theme():
        theme.apply_theme(app, not theme.is_dark())

    def add_extra():
        key = "demo/extra%d" % state["extra"]
        if panel.add_series(key, "Extra %d" % state["extra"], "u"):
            state["extra"] += 1

    def toggle_battery_polled():
        state["battery_polled"] = not state["battery_polled"]
        keys = {key for key, _name, _unit in DEMO_SERIES}
        if not state["battery_polled"]:
            keys.discard("demo/battery")
        panel.set_polled_keys(keys)

    def pause_feed():
        feed.stop()
        core.QTimer.singleShot(5000, feed.start)

    toolbar.addAction("Toggle theme", toggle_theme)
    toolbar.addAction("Add series", add_extra)
    toolbar.addAction("Toggle battery polled", toggle_battery_polled)
    toolbar.addAction("Pause feed 5 s", pause_feed)
    panel.limit_reached.connect(lambda: window.statusBar().showMessage("Limit: 8 series", 4000))

    window.resize(1100, 650)
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
