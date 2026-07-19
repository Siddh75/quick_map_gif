"""Capture dock: lock/drift controls, frame capture, frame list, preview,
and the entry point into the GIF export dialog."""

from qgis.PyQt.QtCore import Qt, QSize, QTimer, pyqtSignal
from qgis.PyQt.QtGui import QIcon, QPixmap
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .canvas_watcher import CanvasWatcher
from .frame_manager import FrameManager
from .capture import save_frame

_THUMB_SIZE = QSize(96, 72)


class QuickMapGifDockWidget(QDockWidget):
    closingPlugin = pyqtSignal()

    DEFAULT_WIDTH = 800
    DEFAULT_HEIGHT = 600

    def __init__(self, iface, parent=None):
        super().__init__("QuickMapGif", parent)
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.frame_manager = FrameManager()
        self.watcher = CanvasWatcher(self.canvas)
        self.watcher.driftChanged.connect(self._on_drift_changed)

        self._build_ui()
        # Deferred rather than called immediately: inserting this dock into
        # the QGIS layout resizes the map canvas, which fires its own
        # extentsChanged. Grabbing the reference before that settles would
        # make the very first drift check compare against a since-changed
        # extent and falsely report drift the moment the dock appears.
        QTimer.singleShot(0, self.watcher.set_reference)

    # ------------------------------------------------------------------
    def _build_ui(self):
        container = QWidget()
        layout = QVBoxLayout()

        self.lock_checkbox = QCheckBox("Lock extent")
        self.lock_checkbox.setChecked(True)
        self.lock_checkbox.setToolTip(
            "While checked, every capture uses one fixed reference view and\n"
            "you'll be warned if the canvas drifts from it. Uncheck to move\n"
            "the camera freely between captures."
        )
        self.lock_checkbox.toggled.connect(self._on_lock_toggled)
        layout.addWidget(self.lock_checkbox)

        self.drift_banner = QLabel("")
        self.drift_banner.setStyleSheet(
            "background-color: #fff3cd; color: #664d03; padding: 4px; border-radius: 3px;"
        )
        self.drift_banner.setWordWrap(True)
        self.drift_banner.hide()
        layout.addWidget(self.drift_banner)

        banner_buttons = QHBoxLayout()
        self.snap_back_btn = QPushButton("Snap back to reference")
        self.snap_back_btn.clicked.connect(self.watcher.snap_back)
        self.update_ref_btn = QPushButton("Use this view instead")
        self.update_ref_btn.clicked.connect(self._update_reference)
        banner_buttons.addWidget(self.snap_back_btn)
        banner_buttons.addWidget(self.update_ref_btn)
        self.banner_button_row = QWidget()
        self.banner_button_row.setLayout(banner_buttons)
        self.banner_button_row.hide()
        layout.addWidget(self.banner_button_row)

        res_row = QHBoxLayout()
        res_row.addWidget(QLabel("Output size:"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(64, 8000)
        self.width_spin.setValue(self.DEFAULT_WIDTH)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(64, 8000)
        self.height_spin.setValue(self.DEFAULT_HEIGHT)
        res_row.addWidget(self.width_spin)
        res_row.addWidget(QLabel("x"))
        res_row.addWidget(self.height_spin)
        layout.addLayout(res_row)

        self.capture_btn = QPushButton("Capture Frame")
        self.capture_btn.clicked.connect(self._capture_frame)
        layout.addWidget(self.capture_btn)

        self.frame_list = QListWidget()
        self.frame_list.setIconSize(_THUMB_SIZE)
        layout.addWidget(self.frame_list)

        list_buttons = QHBoxLayout()
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._delete_selected)
        self.move_up_btn = QPushButton("Move Up")
        self.move_up_btn.clicked.connect(lambda: self._move_selected(-1))
        self.move_down_btn = QPushButton("Move Down")
        self.move_down_btn.clicked.connect(lambda: self._move_selected(1))
        list_buttons.addWidget(self.delete_btn)
        list_buttons.addWidget(self.move_up_btn)
        list_buttons.addWidget(self.move_down_btn)
        layout.addLayout(list_buttons)

        self.preview_btn = QPushButton("Preview...")
        self.preview_btn.clicked.connect(self._open_preview_window)
        layout.addWidget(self.preview_btn)

        self.clear_btn = QPushButton("Clear Session")
        self.clear_btn.clicked.connect(self._clear_session)
        layout.addWidget(self.clear_btn)

        self.export_btn = QPushButton("Generate GIF...")
        self.export_btn.clicked.connect(self._open_export_dialog)
        layout.addWidget(self.export_btn)

        container.setLayout(layout)
        self.setWidget(container)

    # ------------------------------------------------------------------
    # Lock / drift handling
    # ------------------------------------------------------------------
    def _on_lock_toggled(self, checked):
        self.watcher.set_locked(checked)

    def _on_drift_changed(self, drifted):
        self.drift_banner.setText("View has shifted from the reference frame." if drifted else "")
        self.drift_banner.setVisible(drifted)
        self.banner_button_row.setVisible(drifted)

    def _update_reference(self):
        self.watcher.set_reference()
        self._on_drift_changed(False)

    # ------------------------------------------------------------------
    # Capture / frame list management
    # ------------------------------------------------------------------
    def _capture_frame(self):
        extent = self.watcher.current_extent()
        width = self.width_spin.value()
        height = self.height_spin.value()
        output_path = self.frame_manager.next_frame_path()
        save_frame(self.canvas, extent, width, height, output_path)
        self.frame_manager.add_frame(
            output_path,
            (extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum()),
            width,
            height,
        )
        self.frame_manager.save_manifest()
        self._refresh_frame_list()

    def _refresh_frame_list(self):
        self.frame_list.clear()
        for i, frame in enumerate(self.frame_manager.frames):
            item = QListWidgetItem(f"Frame {i + 1}")
            pixmap = QPixmap(frame.image_path)
            if not pixmap.isNull():
                item.setIcon(QIcon(pixmap.scaled(_THUMB_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
            self.frame_list.addItem(item)

    def _delete_selected(self):
        row = self.frame_list.currentRow()
        if row >= 0:
            self.frame_manager.remove_frame(row)
            self.frame_manager.save_manifest()
            self._refresh_frame_list()

    def _move_selected(self, direction):
        row = self.frame_list.currentRow()
        if row < 0:
            return
        target = row + direction
        if 0 <= target < len(self.frame_manager.frames):
            self.frame_manager.move_frame(row, target)
            self.frame_manager.save_manifest()
            self._refresh_frame_list()
            self.frame_list.setCurrentRow(target)

    def _clear_session(self):
        if not self.frame_manager.frames:
            return
        confirm = QMessageBox.question(
            self, "Clear Session", "Delete all captured frames for this session?"
        )
        if confirm == QMessageBox.Yes:
            self.frame_manager.clear()
            self._refresh_frame_list()

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------
    def _open_preview_window(self):
        if not self.frame_manager.frames:
            QMessageBox.information(self, "QuickMapGif", "Capture at least one frame first.")
            return
        from .preview_dialog import PreviewWindow

        # Snapshot the current frame list; the preview window doesn't track
        # later reorders/deletes/captures made in the dock while it's open.
        self._preview_window = PreviewWindow(list(self.frame_manager.frames), parent=self)
        self._preview_window.setAttribute(Qt.WA_DeleteOnClose)
        self._preview_window.show()
        self._preview_window.raise_()
        self._preview_window.activateWindow()

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    def _open_export_dialog(self):
        if not self.frame_manager.frames:
            QMessageBox.information(self, "QuickMapGif", "Capture at least one frame first.")
            return
        from .export_dialog import ExportDialog

        dialog = ExportDialog(self.frame_manager.frames, parent=self)
        dialog.exec_()

    # ------------------------------------------------------------------
    def closeEvent(self, event):
        self.watcher.cleanup()
        self.closingPlugin.emit()
        event.accept()
