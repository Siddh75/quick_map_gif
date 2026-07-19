"""Main plugin class: wires a toolbar/menu action to the capture dock widget."""

import os

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction


class QuickMapGifPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.dock_widget = None
        self.action = None

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, "icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
        self.action = QAction(icon, "QuickMapGif", self.iface.mainWindow())
        self.action.setCheckable(True)
        self.action.triggered.connect(self.toggle_dock)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&QuickMapGif", self.action)

    def toggle_dock(self, checked):
        if self.dock_widget is None:
            # Imported lazily so a missing/broken dependency doesn't break initGui().
            from .dock_widget import QuickMapGifDockWidget

            self.dock_widget = QuickMapGifDockWidget(self.iface)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock_widget)
            self.dock_widget.closingPlugin.connect(self._on_dock_closed)
        self.dock_widget.setVisible(checked)

    def _on_dock_closed(self):
        if self.action is not None:
            self.action.setChecked(False)

    def unload(self):
        if self.dock_widget is not None:
            # removeDockWidget() doesn't fire closeEvent, so clean up the
            # canvas rubber band overlay explicitly to avoid leaving a
            # stray outline behind when the plugin is disabled/reloaded.
            self.dock_widget.watcher.cleanup()
            self.iface.removeDockWidget(self.dock_widget)
            self.dock_widget.deleteLater()
            self.dock_widget = None
        if self.action is not None:
            self.iface.removeToolBarIcon(self.action)
            self.iface.removePluginMenu("&QuickMapGif", self.action)
            self.action = None
