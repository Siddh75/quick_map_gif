# QuickMapGif

A QGIS plugin for manually capturing a sequence of map canvas frames and
exporting them as an animated GIF — no Pillow, no ffmpeg, no external
dependencies.

New to the plugin? [**TUTORIAL.md**](TUTORIAL.md) walks through a full
worked example, fixed-view and moving-camera animations included.

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
   to the "Installed" tab, and enable **QuickMapGif**.
4. A toolbar icon and a **Plugins > QuickMapGif** menu entry appear —
   click either to open the capture dock.

Symlinking during development means edits to these files take effect the
next time you use **Plugin Reloader** (a separate QGIS plugin) or restart
QGIS, without re-copying.

```bash
ln -s "/Users/siddharthgupta/Projects/quick_map_gif" ~/Library/Application\ Support/QGIS/QGIS3/profiles/default/python/plugins/quick_map_gif
```

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

## Publishing to plugins.qgis.org

This repo is prepared to meet the [official repository's requirements](https://docs.qgis.org/3.44/en/docs/pyqgis_developer_cookbook/plugins/releasing.html): `metadata.txt`, `__init__.py`, and `LICENSE` (GPLv2-or-later, matching QGIS's own license) are all in place, the icon is a real design rather than the default, `repository`/`tracker`/`homepage` point at this live repo, and the code passes a `pyflakes`/`pycodestyle` check with no findings.

To actually submit:

1. Get an OSGeo ID at the [OSGeo web portal](https://www.osgeo.org/community/getting-started-osgeo/osgeo_userid/) if you don't already have one — required to upload to the official repository.
2. Push the current state of this repo (including `LICENSE` and `icon.png`) to `main` on GitHub so the linked repository/tracker/homepage URLs resolve to the real thing.
3. Zip the plugin folder itself (a folder named `quick_map_gif/` at the top level of the archive — not its contents at the zip root), excluding `.git`, `.gitignore`, `.DS_Store`, and `__pycache__`.
4. Upload the zip at [plugins.qgis.org/plugins/add](https://plugins.qgis.org/plugins/add/). A staff member reviews and approves new uploads — approvals run daily on weekdays.
5. Bump `version` in `metadata.txt` for every subsequent upload; the repository requires each uploaded version to be unique.

## Known limitations (v0.1)

- Palette is quantized to 256 colors per export; very colorful basemaps
  may show mild banding/dithering artifacts compared to the source PNGs.
- "Lock extent" only locks pan/zoom; layer visibility, styling, and other
  canvas state are not tracked or restored automatically.
- No MP4/WebP export yet — GIF only, by design for this first version.
