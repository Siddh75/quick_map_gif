"""Standalone preview window: plays captured frames back as a simple
flip-book animation in their own window, separate from the capture dock,
so the user can sanity-check pacing and framing before running a full
GIF export."""

from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtGui import QPixmap
from qgis.PyQt.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
)

DEFAULT_FPS = 10


class PreviewWindow(QDialog):
    def __init__(self, frames, fps=DEFAULT_FPS, parent=None):
        super().__init__(parent)
        self.setWindowTitle("QuickMapGif -- Preview")
        self.setWindowFlags(self.windowFlags() | Qt.Window)
        self.frames = frames
        self._index = 0
        self._playing = True

        self._build_ui(fps)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)
        self._show_frame()
        self._timer.start(self._interval_ms())

    def _build_ui(self, fps):
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(320, 240)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setStyleSheet("background-color: #202020;")

        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)

        self.play_btn = QPushButton("Pause")
        self.play_btn.clicked.connect(self._toggle_play)

        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 60)
        self.fps_spin.setValue(fps)
        self.fps_spin.valueChanged.connect(self._on_fps_changed)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)

        controls = QHBoxLayout()
        controls.addWidget(self.play_btn)
        controls.addWidget(QLabel("FPS:"))
        controls.addWidget(self.fps_spin)
        controls.addStretch(1)
        controls.addWidget(close_btn)

        layout = QVBoxLayout()
        layout.addWidget(self.image_label, 1)
        layout.addWidget(self.status_label)
        layout.addLayout(controls)
        self.setLayout(layout)
        self.resize(640, 520)

    def _interval_ms(self):
        return max(1, round(1000 / self.fps_spin.value()))

    def _on_fps_changed(self, _value):
        self._timer.setInterval(self._interval_ms())

    def _toggle_play(self):
        self._playing = not self._playing
        self.play_btn.setText("Pause" if self._playing else "Play")

    def _advance(self):
        if not self._playing or not self.frames:
            return
        self._index = (self._index + 1) % len(self.frames)
        self._show_frame()

    def _show_frame(self):
        if not self.frames:
            self.status_label.setText("No frames captured yet.")
            return
        frame = self.frames[self._index]
        pixmap = QPixmap(frame.image_path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled)
        self.status_label.setText(f"Frame {self._index + 1} of {len(self.frames)}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._show_frame()

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
