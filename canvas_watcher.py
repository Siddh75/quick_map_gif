"""Reference-extent lock and drift detection for the map canvas.

While "Lock extent" is checked, every frame is captured using a single
stored reference extent, and the canvas is watched for accidental
pan/zoom drift away from it (e.g. from scrolling while inspecting data
between captures). While unlocked, each capture simply uses whatever
extent is currently showing, so the user can intentionally move the
camera between frames.
"""

from qgis.core import QgsGeometry, QgsRectangle, QgsWkbTypes
from qgis.gui import QgsRubberBand
from qgis.PyQt.QtCore import QObject, Qt, pyqtSignal
from qgis.PyQt.QtGui import QColor


class CanvasWatcher(QObject):
    # Emitted whenever the drifted state changes (not on every canvas move).
    driftChanged = pyqtSignal(bool)

    def __init__(self, canvas, tolerance=0.005, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.tolerance = tolerance
        self.reference_extent = None
        self.locked = True
        self._drifted = False
        self.canvas.extentsChanged.connect(self._check_drift)

        self.rubber_band = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.rubber_band.setStrokeColor(QColor(220, 20, 60))
        self.rubber_band.setFillColor(QColor(220, 20, 60, 25))
        self.rubber_band.setWidth(2)
        self.rubber_band.setLineStyle(Qt.DashLine)

    def set_reference(self, extent=None):
        """(Re)baseline the reference extent to the given extent, or the
        canvas's current extent if none is given."""
        self.reference_extent = QgsRectangle(extent if extent is not None else self.canvas.extent())
        self._set_drifted(False)
        self._update_rubber_band()

    def set_locked(self, locked):
        """Enable/disable the lock. Enabling always adopts whatever the
        canvas is currently showing as the new reference -- otherwise
        re-locking after an intentional pan would immediately (and
        incorrectly) report drift against a stale, pre-pan reference."""
        self.locked = locked
        if locked:
            self.set_reference()  # also updates the rubber band
        else:
            self._set_drifted(False)
            self._update_rubber_band()

    def snap_back(self):
        """Reset the live canvas view to match the reference extent."""
        if self.reference_extent is not None:
            self.canvas.setExtent(self.reference_extent)
            self.canvas.refresh()
            self._set_drifted(False)

    def current_extent(self):
        """The extent that should be used for the next capture."""
        if self.locked and self.reference_extent is not None:
            return QgsRectangle(self.reference_extent)
        return QgsRectangle(self.canvas.extent())

    def is_drifted(self):
        return self._drifted

    def cleanup(self):
        """Remove the rubber band overlay from the canvas. Call this when
        the dock is closed/the plugin is unloaded so no stray outline is
        left behind on the map."""
        self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
        self.rubber_band.hide()

    def _update_rubber_band(self):
        if self.locked and self.reference_extent is not None:
            self.rubber_band.setToGeometry(QgsGeometry.fromRect(self.reference_extent), None)
            self.rubber_band.show()
        else:
            self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)

    def _check_drift(self):
        if not self.locked or self.reference_extent is None:
            return
        current = self.canvas.extent()
        ref = self.reference_extent
        if ref.width() <= 0 or ref.height() <= 0:
            return
        dx = abs(current.center().x() - ref.center().x()) / ref.width()
        dy = abs(current.center().y() - ref.center().y()) / ref.height()
        dw = abs(current.width() - ref.width()) / ref.width()
        dh = abs(current.height() - ref.height()) / ref.height()
        self._set_drifted(max(dx, dy, dw, dh) > self.tolerance)

    def _set_drifted(self, drifted):
        if drifted != self._drifted:
            self._drifted = drifted
            self.driftChanged.emit(drifted)
