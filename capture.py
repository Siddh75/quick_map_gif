"""Fixed-resolution, off-screen frame capture.

Frames are rendered via QgsMapSettings + QgsMapRendererParallelJob rather
than grabbed from the on-screen canvas widget, so every frame is
pixel-identical in size regardless of the QGIS window's current size or
the display's DPI.
"""

from qgis.core import QgsMapRendererParallelJob, QgsMapSettings
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QColor


def render_frame(canvas, extent, width, height, background_color=None):
    """Render the canvas's current layers/style over `extent` at a fixed
    (width, height) resolution. Returns a QImage."""
    settings = QgsMapSettings(canvas.mapSettings())
    settings.setExtent(extent)
    settings.setOutputSize(QSize(int(width), int(height)))
    settings.setBackgroundColor(background_color or QColor(255, 255, 255))

    job = QgsMapRendererParallelJob(settings)
    job.start()
    job.waitForFinished()
    return job.renderedImage()


def save_frame(canvas, extent, width, height, output_path, background_color=None):
    image = render_frame(canvas, extent, width, height, background_color)
    image.save(output_path, "PNG")
    return output_path
