# Making Your First Map Animation with QuickMapGif

QuickMapGif is a QGIS plugin for building animated GIFs out of your map canvas by hand: you navigate to a view, capture a frame, change something, capture again, and repeat — then export the whole sequence as a GIF with your own timing. No Pillow, no ffmpeg, nothing to install beyond the plugin itself.

This tutorial walks through both ways people typically use it:

- **A fixed-view animation** — the camera never moves; only the data changes between frames (a time-lapse of a layer's symbology, a build-out sequence, before/after comparisons).
- **A moving-camera animation** — a zoom-in or pan "flyover" where the view itself changes frame to frame.

> This tutorial doesn't include screenshots — QGIS's own interface is your best reference. Wherever a screenshot would help, we've described exactly what you should be looking at, so you can follow along in your own project.

## What you'll need

- QGIS 3.16 or later.
- The QuickMapGif plugin installed and enabled (**Plugins → Manage and Install Plugins**, search "QuickMapGif", or install manually — see the project [README](README.md)).
- Any project with at least one or two visible layers. A basemap plus a vector layer works well; the exact data doesn't matter for this tutorial.

## 1. Meet the dock

Open the plugin from the toolbar icon or **Plugins → QuickMapGif**. A dock panel appears with, top to bottom:

- **Lock extent** — a checkbox, checked by default.
- A yellow drift banner area (hidden until it's needed).
- **Output size** — width × height in pixels for captured frames.
- **Capture Frame** — the main capture button.
- A frame list with thumbnails, plus **Delete** / **Move Up** / **Move Down**.
- **Preview...** — opens frames in their own playback window.
- **Clear Session** — wipes all captured frames for a fresh start.
- **Generate GIF...** — opens the export dialog once you have frames.

## 2. Part one: a fixed-view animation

This is the more common case — you want the exact same framing in every frame, and only the data changes (a layer toggled on, a different symbology applied, a time slider moved forward).

1. Pan and zoom to the view you want every frame to share, then leave it there.
2. Make sure **Lock extent** is checked. The moment you check it (or open the dock, since it's checked by default), QuickMapGif stores your current view as the **reference extent** and draws a dashed crimson rectangle on the canvas outlining it. That rectangle is your frame boundary — as long as it's showing, every capture uses that exact extent, regardless of what the canvas is currently showing.
3. Click **Capture Frame**. The dock's frame list gains a thumbnail for "Frame 1".
4. Now change whatever should animate — toggle a layer's visibility, switch a style, move a time slider, filter to a different subset of features. Don't touch pan or zoom.
5. Click **Capture Frame** again for "Frame 2". Repeat for as many frames as you want in the sequence.

### If you accidentally bump the view

Scroll-wheel zoom and click-drag panning are easy to trigger by accident while you're focused on toggling layers. If the canvas drifts away from the locked reference extent, a banner appears: *"View has shifted from the reference frame."* You get two ways to resolve it:

- **Snap back to reference** — restores the exact original view, so your next capture still matches the earlier frames.
- **Use this view instead** — accepts wherever you've ended up as the *new* reference going forward (useful if the drift was actually intentional).

The dashed rectangle on the canvas always shows you the current reference extent at a glance, so you don't have to guess whether you've drifted.

## 3. Part two: a moving-camera animation

For a zoom-in/flyover style animation, you want the extent to change on purpose between frames.

1. Uncheck **Lock extent**. The dashed rectangle disappears and the drift banner goes quiet — you're free to pan and zoom without any warnings.
2. Zoom/pan to your starting view and click **Capture Frame**.
3. Zoom in a bit (or pan toward your destination) and capture again. Repeat for as many steps as you like — the more frames and the smaller the steps between them, the smoother the resulting motion will look.
4. If you want to lock the view again partway through (say, the last few frames should hold steady once you've zoomed in), just re-check **Lock extent** — it adopts whatever the canvas is showing *at that moment* as the new reference, so there's no jump.

You can mix both approaches freely within one session: lock for a run of steady frames, unlock to reposition, lock again for the next steady run.

## 4. Reviewing before you export

Frame order matters, and it's easy to want to drop a bad capture or nudge two frames into a different order.

- Click a thumbnail and use **Move Up** / **Move Down** to reorder it.
- Select a thumbnail and click **Delete** to drop it.
- Click **Preview...** to open a separate playback window. It plays your captured frames on a loop with **Pause/Play** and an **FPS** control so you can judge pacing before committing to an export — handy for catching a stray frame or an awkward jump between two captures. This window is a snapshot of your frames at the moment you opened it; reopen it if you've since added, removed, or reordered frames.

## 5. Exporting the GIF

Once the sequence looks right, click **Generate GIF...**. The export dialog offers:

- **Frames per second** — how fast the animation plays back (higher fps = faster, smaller per-frame delay).
- **Looping** — loop forever, or play once and stop.
- **Scale** — shrink the output below your captured resolution (useful for keeping file size down).
- **Ping-pong** — plays forward through all frames, then backward, before looping, for a back-and-forth effect instead of a hard cut from last frame to first.
- **Output file** — where to save the `.gif`.

Click **Export**. Encoding runs in the background with a progress indicator, so QGIS stays responsive even for larger sequences. When it finishes, the dialog shows the saved path.

## Tips

- **Frame resolution vs. window size:** captures are rendered off-screen at whatever **Output size** you set, not a screenshot of the visible canvas — so resizing the QGIS window mid-session won't produce mismatched frame sizes.
- **Color banding:** GIF supports 256 colors per frame. Busy, photographic basemaps (satellite imagery, hillshade) may show slight banding compared to the source map; simpler basemaps and thematic styling reproduce cleanly.
- **File size:** more frames, higher resolution, and higher fps all increase the output size. If a GIF comes out larger than you'd like, try reducing **Scale** in the export dialog or capturing at a smaller **Output size** to begin with.
- **Starting over:** **Clear Session** removes all captured frames so you can start a new sequence without closing and reopening the dock.

## Getting help

Run into something unexpected, or have an idea for a feature? Open an issue on the [tracker](https://github.com/Siddh75/quick_map_gif/issues) — bug reports that include your QGIS version and the steps you took are the fastest to fix.
