"""GIF export dialog: fps/loop/scale/ping-pong controls, encodes via a
background QgsTask so the UI stays responsive."""

import os

from qgis.core import QgsApplication, QgsMessageLog, QgsTask
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QImage
from qgis.PyQt.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from .gif_encoder import RGBFrame, write_gif


def _qimage_to_rgb_bytes(image):
    """Pack a QImage's pixels into tightly-packed RGB bytes (no row padding),
    accounting for QImage's bytesPerLine() stride."""
    image = image.convertToFormat(QImage.Format_RGB888)
    width, height = image.width(), image.height()
    bytes_per_line = image.bytesPerLine()

    ptr = image.constBits()
    ptr.setsize(image.sizeInBytes())
    raw = bytes(ptr)

    if bytes_per_line == width * 3:
        return raw
    rows = [raw[r * bytes_per_line : r * bytes_per_line + width * 3] for r in range(height)]
    return b"".join(rows)


class ExportDialog(QDialog):
    def __init__(self, frames, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Generate GIF")
        self.frames = frames
        self.task = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        form = QFormLayout()

        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 60)
        self.fps_spin.setValue(10)
        form.addRow("Frames per second:", self.fps_spin)

        self.loop_combo = QComboBox()
        self.loop_combo.addItem("Loop forever", 0)
        self.loop_combo.addItem("Play once", 1)
        form.addRow("Looping:", self.loop_combo)

        self.scale_spin = QSpinBox()
        self.scale_spin.setRange(10, 100)
        self.scale_spin.setValue(100)
        self.scale_spin.setSuffix(" %")
        form.addRow("Scale:", self.scale_spin)

        self.pingpong_check = QCheckBox("Ping-pong (forward then reverse)")
        form.addRow("", self.pingpong_check)

        path_row = QHBoxLayout()
        self.path_edit = QLineEdit(os.path.join(os.path.expanduser("~"), "map_animation.gif"))
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse)
        path_row.addWidget(self.path_edit)
        path_row.addWidget(browse_btn)
        form.addRow("Output file:", path_row)

        layout.addLayout(form)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        button_row = QHBoxLayout()
        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self._start_export)
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.reject)
        button_row.addWidget(self.export_btn)
        button_row.addWidget(self.close_btn)
        layout.addLayout(button_row)

        self.setLayout(layout)

    def _browse(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save GIF", self.path_edit.text(), "GIF images (*.gif)")
        if path:
            if not path.lower().endswith(".gif"):
                path += ".gif"
            self.path_edit.setText(path)

    def _start_export(self):
        output_path = self.path_edit.text().strip()
        if not output_path:
            QMessageBox.warning(self, "Quick Map GIF", "Please choose an output file.")
            return

        fps = self.fps_spin.value()
        delay_ms = round(1000 / fps)
        loop = self.loop_combo.currentData()
        scale_pct = self.scale_spin.value()
        pingpong = self.pingpong_check.isChecked()

        ordered_frames = list(self.frames)
        if pingpong and len(ordered_frames) > 2:
            ordered_frames = ordered_frames + list(reversed(ordered_frames[1:-1]))

        self.export_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Preparing frames...")
        QApplication.processEvents()  # let the status label repaint before the loop below

        try:
            rgb_frames = []
            for frame in ordered_frames:
                image = QImage(frame.image_path)
                if image.isNull():
                    raise ValueError(f"Could not read frame image: {frame.image_path}")
                if scale_pct != 100:
                    new_w = max(1, image.width() * scale_pct // 100)
                    new_h = max(1, image.height() * scale_pct // 100)
                    image = image.scaled(new_w, new_h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                rgb = _qimage_to_rgb_bytes(image)
                rgb_frames.append(RGBFrame(image.width(), image.height(), rgb, delay_ms=delay_ms))
        except Exception as exc:  # noqa: BLE001
            self.export_btn.setEnabled(True)
            self.status_label.setText("")
            QMessageBox.critical(self, "Quick Map GIF", f"Failed to prepare frames: {exc}")
            return

        self.task = _GifExportTask(rgb_frames, output_path, loop)
        self.task.taskCompleted.connect(lambda: self._on_finished(output_path, True))
        self.task.taskTerminated.connect(lambda: self._on_finished(output_path, False))
        self.status_label.setText("Encoding GIF...")
        self.progress_bar.setRange(0, 0)  # indeterminate; encoding isn't incrementally reported
        QgsApplication.taskManager().addTask(self.task)

    def _on_finished(self, output_path, success):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100 if success else 0)
        self.export_btn.setEnabled(True)
        if success:
            self.status_label.setText(f"Saved to {output_path}")
        else:
            error = self.task.error if self.task else "unknown error"
            self.status_label.setText("Export failed. See QGIS log for details.")
            QMessageBox.critical(self, "Quick Map GIF", f"GIF export failed: {error}")


class _GifExportTask(QgsTask):
    def __init__(self, rgb_frames, output_path, loop):
        super().__init__("Exporting GIF", QgsTask.CanCancel)
        self.rgb_frames = rgb_frames
        self.output_path = output_path
        self.loop = loop
        self.error = None

    def run(self):
        try:
            write_gif(self.rgb_frames, self.output_path, loop=self.loop)
            return True
        except Exception as exc:  # noqa: BLE001
            self.error = str(exc)
            return False

    def finished(self, result):
        if not result and self.error:
            QgsMessageLog.logMessage(f"Quick Map GIF export failed: {self.error}", "Quick Map GIF")
