#!/usr/bin/env python3
"""G213 keyboard lighting control — KDE system tray."""
import sys
import json
import os
import usb.core
import usb.util
from PyQt5.QtWidgets import (QApplication, QSystemTrayIcon, QMenu,
                              QColorDialog, QAction)
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtCore import Qt

VENDOR  = 0x046d
PRODUCT = 0xc336
CONFIG  = os.path.expanduser("~/.config/g213tray.json")

PRESETS = [
    ("Weiß",   0xff, 0xff, 0xff),
    ("Rot",    0xff, 0x00, 0x00),
    ("Grün",   0x00, 0xff, 0x00),
    ("Blau",   0x00, 0x00, 0xff),
    ("Lila",   0x80, 0x00, 0xff),
    ("Orange", 0xff, 0x60, 0x00),
    ("Cyan",   0x00, 0xff, 0xff),
]


def _send(r, g, b):
    dev = usb.core.find(idVendor=VENDOR, idProduct=PRODUCT)
    if dev is None:
        print("G213 nicht gefunden", file=sys.stderr)
        return
    iface = 1
    detached = False
    if dev.is_kernel_driver_active(iface):
        dev.detach_kernel_driver(iface)
        detached = True
    try:
        pkt = [0x11, 0xff, 0x0c, 0x3a, 0x00, 0x01, r, g, b,
               0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        dev.ctrl_transfer(0x21, 0x09, 0x0211, iface, pkt)
    finally:
        usb.util.release_interface(dev, iface)
        if detached:
            try:
                dev.attach_kernel_driver(iface)
            except Exception:
                pass


def load_state():
    try:
        with open(CONFIG) as f:
            return json.load(f)
    except Exception:
        return {"on": True, "color": [255, 255, 255]}


def save_state(state):
    with open(CONFIG, "w") as f:
        json.dump(state, f)


class G213Tray:
    def __init__(self, app):
        self.app   = app
        self.state = load_state()
        self.tray  = QSystemTrayIcon(QIcon.fromTheme("input-keyboard"), app)
        self.tray.setToolTip("G213 Beleuchtung")

        # left click = toggle
        self.tray.activated.connect(self._on_activate)

        menu = QMenu()

        toggle = QAction("Licht ein/aus", menu)
        toggle.triggered.connect(self._toggle)
        menu.addAction(toggle)
        menu.addSeparator()

        for name, r, g, b in PRESETS:
            def make_cb(r=r, g=g, b=b):
                def cb():
                    self.state["color"] = [r, g, b]
                    self.state["on"]    = True
                    _send(r, g, b)
                    save_state(self.state)
                return cb
            action = QAction(name, menu)
            action.triggered.connect(make_cb())
            menu.addAction(action)

        menu.addSeparator()
        custom = QAction("Eigene Farbe …", menu)
        custom.triggered.connect(self._pick_color)
        menu.addAction(custom)

        menu.addSeparator()
        quit_a = QAction("Beenden", menu)
        quit_a.triggered.connect(app.quit)
        menu.addAction(quit_a)

        self.tray.setContextMenu(menu)
        self.tray.show()

        # apply last saved state on startup
        if self.state["on"]:
            r, g, b = self.state["color"]
            _send(r, g, b)
        else:
            _send(0, 0, 0)

    def _toggle(self):
        self.state["on"] = not self.state["on"]
        if self.state["on"]:
            r, g, b = self.state["color"]
        else:
            r, g, b = 0, 0, 0
        _send(r, g, b)
        save_state(self.state)

    def _on_activate(self, reason):
        if reason == QSystemTrayIcon.Trigger:   # left click
            self._toggle()

    def _pick_color(self):
        r, g, b = self.state["color"]
        initial = QColor(r, g, b)
        color = QColorDialog.getColor(initial)
        if color.isValid():
            r, g, b = color.red(), color.green(), color.blue()
            self.state["color"] = [r, g, b]
            self.state["on"]    = True
            _send(r, g, b)
            save_state(self.state)


if __name__ == "__main__":
    app = App = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    tray = G213Tray(app)
    sys.exit(app.exec_())
