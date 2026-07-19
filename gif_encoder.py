"""Standalone GIF89a encoder.

No QGIS/Qt dependency, so this module can be developed and unit tested
in complete isolation from QGIS. It accepts raw RGB frame buffers
(width, height, packed RGB bytes with no row padding) and writes an
animated GIF using:

  * a single shared color palette (median-cut quantization) across all
    frames, so colors stay consistent and don't flicker frame to frame
  * a NETSCAPE2.0 application extension for loop count
  * a per-frame graphic control extension for delay time
  * a standard variable-code-width LZW encoder for the pixel data

numpy is used to vectorize palette quantization when available (QGIS's
bundled Python almost always has it via GDAL/processing), with a slower
pure-Python fallback so the encoder still works without it.
"""

import struct

try:
    import numpy as np

    _HAVE_NUMPY = True
except ImportError:  # pragma: no cover - exercised only without numpy installed
    _HAVE_NUMPY = False


class RGBFrame:
    """One frame: width/height plus row-major RGB bytes (len == width*height*3)."""

    __slots__ = ("width", "height", "rgb", "delay_ms")

    def __init__(self, width, height, rgb, delay_ms=100):
        expected = width * height * 3
        if len(rgb) != expected:
            raise ValueError(f"rgb buffer length {len(rgb)} != expected {expected}")
        self.width = width
        self.height = height
        self.rgb = rgb
        self.delay_ms = delay_ms


def write_gif(frames, output_path, loop=0, max_colors=256):
    """Encode `frames` (list of RGBFrame, all the same width/height) as an
    animated GIF at `output_path`. loop=0 means loop forever; any other
    value is treated as "play once" (GIF only natively supports infinite
    loop or a fixed repeat count via the same extension, so we keep the
    UI-facing choice simple: forever vs. once)."""
    if not frames:
        raise ValueError("No frames to encode")

    width, height = frames[0].width, frames[0].height
    for frame in frames:
        if frame.width != width or frame.height != height:
            raise ValueError("All frames must share the same dimensions")

    palette = _build_palette(frames, max_colors=max_colors)
    min_code_size = max(2, (len(palette) - 1).bit_length())
    table_size = 1 << min_code_size
    padded_palette = list(palette) + [(0, 0, 0)] * (table_size - len(palette))

    with open(output_path, "wb") as f:
        f.write(b"GIF89a")
        f.write(struct.pack("<HH", width, height))
        packed_fields = 0xF0 | (min_code_size - 1)
        f.write(struct.pack("<BBB", packed_fields, 0, 0))
        for color in padded_palette:
            f.write(struct.pack("BBB", *color))

        # NETSCAPE2.0 application extension controls looping. A GIF loops
        # forever if this extension is present with count 0; per spec,
        # simply omitting it makes viewers play the animation once.
        if loop == 0:
            f.write(b"\x21\xFF\x0BNETSCAPE2.0\x03\x01\x00\x00\x00")

        for frame in frames:
            _write_frame(f, frame, palette, min_code_size)

        f.write(b"\x3B")  # trailer

    return output_path


def _write_frame(f, frame, palette, min_code_size):
    indices = _quantize_frame(frame, palette)

    delay_cs = max(1, round(frame.delay_ms / 10))
    f.write(b"\x21\xF9")
    f.write(bytes([4]))
    disposal_packed = 1 << 2  # "do not dispose" -- each frame fully repaints the canvas
    f.write(bytes([disposal_packed]))
    f.write(struct.pack("<H", delay_cs))
    f.write(bytes([0, 0]))  # transparent color index (unused), block terminator

    f.write(b"\x2C")
    f.write(struct.pack("<HHHH", 0, 0, frame.width, frame.height))
    f.write(bytes([0]))  # no local color table

    f.write(bytes([min_code_size]))
    lzw_data = _lzw_encode(indices, min_code_size)
    for start in range(0, len(lzw_data), 255):
        chunk = lzw_data[start : start + 255]
        f.write(bytes([len(chunk)]))
        f.write(chunk)
    f.write(bytes([0]))  # block terminator


# ---------------------------------------------------------------------------
# Palette quantization (median cut)
# ---------------------------------------------------------------------------


def _build_palette(frames, max_colors=256, sample_stride=4):
    if _HAVE_NUMPY:
        return _build_palette_np(frames, max_colors, sample_stride)
    return _build_palette_py(frames, max_colors, sample_stride)


def _build_palette_np(frames, max_colors, sample_stride):
    samples = [
        np.frombuffer(frame.rgb, dtype=np.uint8).reshape(-1, 3)[::sample_stride] for frame in frames
    ]
    pixels = np.concatenate(samples, axis=0).astype(np.float64)
    pixels = np.unique(pixels, axis=0)

    boxes = [pixels]
    while len(boxes) < max_colors:
        ranges = [(b.max(axis=0) - b.min(axis=0)).max() if len(b) > 1 else -1 for b in boxes]
        idx = int(np.argmax(ranges))
        if ranges[idx] <= 0:
            break
        box = boxes[idx]
        channel = int(np.argmax(box.max(axis=0) - box.min(axis=0)))
        order = np.argsort(box[:, channel])
        box = box[order]
        mid = len(box) // 2
        boxes[idx] = box[:mid]
        boxes.append(box[mid:])

    palette = []
    for box in boxes:
        if len(box):
            color = tuple(int(round(c)) for c in box.mean(axis=0))
            if color not in palette:
                palette.append(color)
    return palette[:max_colors] or [(0, 0, 0)]


def _build_palette_py(frames, max_colors, sample_stride):
    samples = []
    for frame in frames:
        rgb = frame.rgb
        for i in range(0, len(rgb) - 2, 3 * sample_stride):
            samples.append((rgb[i], rgb[i + 1], rgb[i + 2]))
    samples = list(set(samples)) or [(0, 0, 0)]

    boxes = [samples]
    while len(boxes) < max_colors:
        idx, box = max(enumerate(boxes), key=lambda kv: _box_range(kv[1]))
        if _box_range(box) <= 0 or len(box) < 2:
            break
        channel = _box_widest_channel(box)
        box_sorted = sorted(box, key=lambda p: p[channel])
        mid = len(box_sorted) // 2
        boxes[idx] = box_sorted[:mid]
        boxes.append(box_sorted[mid:])

    palette = []
    for box in boxes:
        if not box:
            continue
        n = len(box)
        avg = tuple(round(sum(p[c] for p in box) / n) for c in range(3))
        if avg not in palette:
            palette.append(avg)
    return palette[:max_colors] or [(0, 0, 0)]


def _box_range(box):
    if len(box) < 2:
        return -1
    mins = [min(p[c] for p in box) for c in range(3)]
    maxs = [max(p[c] for p in box) for c in range(3)]
    return max(maxs[c] - mins[c] for c in range(3))


def _box_widest_channel(box):
    mins = [min(p[c] for p in box) for c in range(3)]
    maxs = [max(p[c] for p in box) for c in range(3)]
    ranges = [maxs[c] - mins[c] for c in range(3)]
    return ranges.index(max(ranges))


# ---------------------------------------------------------------------------
# Quantize a frame to palette indices
# ---------------------------------------------------------------------------


def _quantize_frame(frame, palette):
    if _HAVE_NUMPY:
        pal = np.array(palette, dtype=np.float64)
        arr = np.frombuffer(frame.rgb, dtype=np.uint8).reshape(-1, 3).astype(np.float64)
        indices = np.empty(arr.shape[0], dtype=np.uint8)
        chunk = 20000
        for start in range(0, arr.shape[0], chunk):
            block = arr[start : start + chunk]
            dists = ((block[:, None, :] - pal[None, :, :]) ** 2).sum(axis=2)
            indices[start : start + chunk] = np.argmin(dists, axis=1).astype(np.uint8)
        return indices.tobytes()

    rgb = frame.rgb
    out = bytearray(len(rgb) // 3)
    cache = {}
    for i in range(0, len(rgb), 3):
        key = (rgb[i], rgb[i + 1], rgb[i + 2])
        idx = cache.get(key)
        if idx is None:
            best, best_dist = 0, None
            for pi, pc in enumerate(palette):
                d = (key[0] - pc[0]) ** 2 + (key[1] - pc[1]) ** 2 + (key[2] - pc[2]) ** 2
                if best_dist is None or d < best_dist:
                    best, best_dist = pi, d
            idx = best
            cache[key] = idx
        out[i // 3] = idx
    return bytes(out)


# ---------------------------------------------------------------------------
# LZW encoding (GIF variant, variable code width up to 12 bits)
# ---------------------------------------------------------------------------


class _BitWriter:
    def __init__(self):
        self._buffer = bytearray()
        self._bit_buffer = 0
        self._bit_count = 0

    def write(self, code, size):
        self._bit_buffer |= code << self._bit_count
        self._bit_count += size
        while self._bit_count >= 8:
            self._buffer.append(self._bit_buffer & 0xFF)
            self._bit_buffer >>= 8
            self._bit_count -= 8

    def getvalue(self):
        if self._bit_count:
            self._buffer.append(self._bit_buffer & 0xFF)
        return bytes(self._buffer)


def _lzw_encode(indices, min_code_size):
    clear_code = 1 << min_code_size
    end_code = clear_code + 1

    def reset_table():
        return {(i,): i for i in range(clear_code)}, end_code + 1, min_code_size + 1

    table, next_code, code_size = reset_table()
    bw = _BitWriter()
    bw.write(clear_code, code_size)

    prefix = (indices[0],)
    for pixel in indices[1:]:
        entry = prefix + (pixel,)
        if entry in table:
            prefix = entry
            continue

        bw.write(table[prefix], code_size)
        if next_code < 4096:
            table[entry] = next_code
            next_code += 1
            # NOTE: the bump is intentionally checked one step later than the
            # naive "next_code == (1 << code_size)" rule. A GIF decoder's
            # dictionary is always one entry behind the encoder's (it can
            # only add entry N once it has decoded the code *after* the one
            # that first needed entry N), so bumping immediately here would
            # have the decoder read the following code at the wrong width.
            if next_code > (1 << code_size) and code_size < 12:
                code_size += 1
        else:
            bw.write(clear_code, code_size)
            table, next_code, code_size = reset_table()
        prefix = (pixel,)

    bw.write(table[prefix], code_size)
    bw.write(end_code, code_size)
    return bw.getvalue()
