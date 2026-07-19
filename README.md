# QuickMapGif

A QGIS plugin for manually capturing a sequence of map canvas frames and
exporting them as an animated GIF — no Pillow, no ffmpeg, no external
dependencies.

New to the plugin? [**TUTORIAL.md**](TUTORIAL.md) walks through a full
worked example, fixed-view and moving-camera animations included.


## Workflow

1. Open the **QuickMapGif** dock and navigate the map to your first frame.
2. Leave **Lock extent** checked (default) if every frame should share the
   same view — the dock stores that view as the reference. Uncheck it if
   you want to intentionally move/zoom the camera between frames.
3. Click **Capture Frame**. Repeat for each frame, changing whatever
   should animate (time slider position, layer visibility, symbology,
   filtered features, etc.) between captures.
4. If Lock extent is checked and you accidentally pan or zoom the canvas
   while adjusting things, a banner appears: **Snap back to reference**
   restores the original view, or **Use this view instead** re-baselines
   the reference to wherever you are now.
5. Reorder or delete frames in the list as needed, and use **Preview** to
   flip through them before exporting.
6. Click **Generate GIF...** and set frames per second, looping, output
   scale, and optional ping-pong (forward-then-reverse) playback, then
   **Export**. Encoding runs in the background with a progress indicator.

## Notes on captures

Frames are rendered off-screen at a fixed resolution (set via the
**Output size** fields in the dock) using `QgsMapSettings` +
`QgsMapRendererParallelJob`, rather than grabbed from the visible canvas
widget. This means every frame is pixel-identical in size no matter how
the QGIS window is resized or what display DPI you're on.

## Module layout

- `quick_map_gif.py` — plugin entrypoint, toolbar/menu wiring
- `canvas_watcher.py` — reference-extent lock and drift detection
- `frame_manager.py` — ordered frame list, on-disk session + manifest
- `capture.py` — fixed-resolution off-screen frame rendering
- `dock_widget.py` — capture panel UI
- `preview_dialog.py` — standalone preview window (play/pause, fps) for
  flipping through captured frames before exporting
- `export_dialog.py` — GIF export controls + background export task
- `gif_encoder.py` — standalone GIF89a encoder (palette quantization +
  LZW), has no QGIS/Qt dependency and can be tested independently
