"""Ordered frame storage and session manifest persistence.

Captured frame images live as PNGs in a session directory (next to the
project file when possible, otherwise a temp directory). A JSON
manifest records each frame's path, extent and size so a session can be
saved and reloaded later, independent of QGIS/Qt.
"""

import json
import os
import shutil
import tempfile
import time


class Frame:
    __slots__ = ("image_path", "extent", "width", "height")

    def __init__(self, image_path, extent, width, height):
        self.image_path = image_path
        self.extent = tuple(extent)  # (xmin, ymin, xmax, ymax)
        self.width = width
        self.height = height

    def to_dict(self):
        return {
            "image_path": self.image_path,
            "extent": list(self.extent),
            "width": self.width,
            "height": self.height,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(d["image_path"], tuple(d["extent"]), d["width"], d["height"])


class FrameManager:
    MANIFEST_NAME = "session.json"

    def __init__(self, session_dir=None):
        self.frames = []
        self.session_dir = session_dir or self._make_temp_session_dir()
        os.makedirs(self.session_dir, exist_ok=True)

    @staticmethod
    def _make_temp_session_dir():
        return os.path.join(tempfile.gettempdir(), f"quick_map_gif_{int(time.time())}")

    def next_frame_path(self):
        return os.path.join(self.session_dir, f"frame_{len(self.frames):04d}.png")

    def add_frame(self, image_path, extent, width, height):
        frame = Frame(image_path, extent, width, height)
        self.frames.append(frame)
        return frame

    def remove_frame(self, index):
        if 0 <= index < len(self.frames):
            frame = self.frames.pop(index)
            self._delete_image(frame)

    def move_frame(self, from_index, to_index):
        if 0 <= from_index < len(self.frames) and 0 <= to_index < len(self.frames):
            frame = self.frames.pop(from_index)
            self.frames.insert(to_index, frame)

    def clear(self):
        for frame in self.frames:
            self._delete_image(frame)
        self.frames = []

    def save_manifest(self):
        manifest_path = os.path.join(self.session_dir, self.MANIFEST_NAME)
        with open(manifest_path, "w") as f:
            json.dump([fr.to_dict() for fr in self.frames], f, indent=2)
        return manifest_path

    @classmethod
    def load(cls, session_dir):
        manager = cls(session_dir=session_dir)
        manifest_path = os.path.join(session_dir, cls.MANIFEST_NAME)
        if os.path.exists(manifest_path):
            with open(manifest_path) as f:
                data = json.load(f)
            manager.frames = [Frame.from_dict(d) for d in data]
        return manager

    def cleanup(self):
        if os.path.isdir(self.session_dir):
            shutil.rmtree(self.session_dir, ignore_errors=True)

    @staticmethod
    def _delete_image(frame):
        if os.path.exists(frame.image_path):
            try:
                os.remove(frame.image_path)
            except OSError:
                pass
