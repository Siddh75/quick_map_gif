# Quick Map GIF

A QGIS plugin for manually capturing a sequence of map canvas frames and
exporting them as an animated GIF — no Pillow, no ffmpeg, no external
dependencies.

## Install (development)

QGIS loads plugins from your user profile's `python/plugins` folder.

This project folder *is* the plugin folder (metadata.txt, `__init__.py`,
and the rest sit right at its root), so QGIS needs a link or copy of it
placed inside your profile's plugins directory, named `quick_map_gif`.

1. Find your profile's plugin folder:
   - macOS: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
   - Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - Windows: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
2. Copy (or symlink) this entire project folder into that directory as
   `quick_map_gif`.
3. Restart QGIS, then open **Plugins > Manage and Install Plugins**, switch
   to the "Installed" tab, and enable **Quick Map GIF**.
4. A toolbar icon and a **Plugins > Quick Map GIF** menu entry appear —
   click either to open the capture dock.

Symlinking during development means edits to these files take effect the
next time you use **Plugin Reloader** (a separate QGIS plugin) or restart
QGIS, without re-copying.

```bash
ln -s "/Users/siddharthgupta/Projects/quick_map_gif" ~/Library/Application\ Support/QGIS/QGIS3/profiles/default/python/plugins/quick_map_gif
```

## Workflow

1. Open the **Quick Map GIF** dock and navigate the map to your first frame.
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

## Known limitations (v0.1)

- Palette is quantized to 256 colors per export; very colorful basemaps
  may show mild banding/dithering artifacts compared to the source PNGs.
- "Lock extent" only locks pan/zoom; layer visibility, styling, and other
  canvas state are not tracked or restored automatically.
- No MP4/WebP export yet — GIF only, by design for this first version.
