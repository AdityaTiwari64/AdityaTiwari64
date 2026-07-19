#!/usr/bin/env python3
"""
Convert a portrait photo into a CLEAN, monochrome ASCII-art SVG that "types"
itself in like a terminal, then holds.

Monochrome is deliberate -- per-character rainbow color is what makes ASCII
portraits look noisy. One fill color + a good density ramp + high contrast
reads as neat and legible.

GitHub renders SVGs embedded via <img> and runs SMIL animations (JS does NOT
run). Each row is revealed with a left-to-right clip wipe plus a small block
cursor riding the wipe edge, staggered top -> bottom, so the whole portrait
prints once and freezes.

Usage:
    python scripts/make_ascii_svg.py [input.png] [output.svg]

    Defaults: profile.png -> aditya-ascii.svg
"""
from PIL import Image, ImageEnhance, ImageFilter
import html
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "profile.png")
OUT  = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "aditya-ascii.svg")

COLS      = 100
ROWS      = 53
CELL_W    = 8
CELL_H    = 15
RAMP      = " .`:-=+*cs#%@"   # bright(sparse) -> dark(dense); leading space clears bg

# Global tuning — contrast/brightness applied inline via Pillow
CONTRAST    = 1.3          # gentle boost; auto-levels already does the heavy lifting
BRIGHTNESS  = 1.05         # slight boost to push face mids toward lighter chars
GAMMA       = 1.4          # >1 lightens mids -> face maps to mid-density chars (.:-=+*)
SHARPEN     = True         # unsharp mask to recover detail
WHITE_FLOOR = 0.84         # luminance above this -> space (clear background)
BG_THRESH   = 230          # RGB channels all above this -> treat as background (white)

PAD        = 20
TITLEBAR_H = 30
STATUS_H   = 30
ART_W      = COLS * CELL_W
ART_H      = ROWS * CELL_H
CANVAS_W   = ART_W + PAD * 2
CANVAS_H   = TITLEBAR_H + ART_H + STATUS_H + PAD

BG         = "#0d1117"
BG2        = "#111722"
FRAME      = "#30363d"
TITLE_TEXT = "#7d8590"
INK        = "#c9d1d9"    # the single ascii color
CURSOR_COL = "#c9d1d9"

# Reveal timing
ROW_DUR = 0.11
STAGGER = 0.11             # == ROW_DUR -> a single cursor sweeping down

STATIC = bool(os.environ.get("STATIC"))


def _flood_fill_bg(rgb_arr, tolerance=30):
    """Flood-fill from the four corners to find the background mask.
    Works even with JPEG compression artifacts on near-white backgrounds."""
    import numpy as np
    from collections import deque

    H, W = rgb_arr.shape[:2]
    visited = np.zeros((H, W), dtype=bool)
    bg_mask = np.zeros((H, W), dtype=bool)

    # Sample seed color from the corner (average of 4 corners)
    corners = [rgb_arr[0,0], rgb_arr[0,W-1], rgb_arr[H-1,0], rgb_arr[H-1,W-1]]
    seed_color = np.mean(corners, axis=0).astype(np.float32)

    queue = deque()
    for seed in [(0,0),(0,W-1),(H-1,0),(H-1,W-1)]:
        if not visited[seed]:
            queue.append(seed)
            visited[seed] = True

    while queue:
        y, x = queue.popleft()
        pixel = rgb_arr[y, x].astype(np.float32)
        dist = np.max(np.abs(pixel - seed_color))
        if dist > tolerance:
            continue
        bg_mask[y, x] = True
        for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
            ny, nx = y+dy, x+dx
            if 0 <= ny < H and 0 <= nx < W and not visited[ny, nx]:
                visited[ny, nx] = True
                queue.append((ny, nx))

    return bg_mask


def sample_image():
    """Load image, enhance it inline, and sample into a COLS x ROWS char grid."""
    import numpy as np

    # Load as RGB so we can detect the background before going grayscale
    rgb = Image.open(SRC).convert("RGB")
    rgb_arr = np.array(rgb)

    # Use flood-fill from corners to detect background (handles JPEG compression artifacts)
    bg_mask = _flood_fill_bg(rgb_arr, tolerance=35)
    print(f"  Background pixels detected: {bg_mask.sum()} / {bg_mask.size} ({100*bg_mask.sum()/bg_mask.size:.1f}%)")

    # Convert to grayscale for processing
    im = rgb.convert("L")
    arr = np.array(im, dtype=np.float32)

    # Auto-levels on the SUBJECT only (exclude bg pixels from histogram)
    subject_vals = arr[~bg_mask]
    if subject_vals.size > 0:
        lo = float(np.percentile(subject_vals, 2))
        hi = float(np.percentile(subject_vals, 98))
        print(f"  Subject lum range: {lo:.0f} - {hi:.0f}")
        arr = np.clip((arr - lo) / max(hi - lo, 1) * 255, 0, 255)

    # Force background to pure white AFTER levels stretch
    arr[bg_mask] = 255
    im = Image.fromarray(arr.astype(np.uint8))

    if SHARPEN:
        im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=180, threshold=2))
    im = ImageEnhance.Brightness(im).enhance(BRIGHTNESS)
    im = ImageEnhance.Contrast(im).enhance(CONTRAST)
    im = im.resize((COLS, ROWS), Image.LANCZOS)
    px = im.load()

    rows_txt = []
    for y in range(ROWS):
        chars = []
        for x in range(COLS):
            lum = px[x, y] / 255.0
            lum = pow(lum, GAMMA)
            if lum >= WHITE_FLOOR:
                chars.append(" ")
                continue
            idx = int((1.0 - lum) * (len(RAMP) - 1))
            idx = max(0, min(idx, len(RAMP) - 1))
            chars.append(RAMP[idx])
        rows_txt.append("".join(chars))
    return rows_txt


def build_svg(rows_txt):
    parts = []
    mono  = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{CANVAS_W}" height="{CANVAS_H}" '
        f'role="img" aria-label="Aditya Tiwari — ASCII portrait">'
    )
    parts.append(
        f'<style>'
        f'text{{font-family:{mono};font-size:{CELL_H - 2}px;'
        f'white-space:pre;letter-spacing:0px;}}'
        f'</style>'
    )

    # Background
    parts.append(f'<rect width="{CANVAS_W}" height="{CANVAS_H}" fill="{BG}"/>')

    # Title bar
    parts.append(f'<rect width="{CANVAS_W}" height="{TITLEBAR_H}" rx="10" fill="{BG2}"/>')
    parts.append(f'<rect y="{TITLEBAR_H - 1}" width="{CANVAS_W}" height="1" fill="{FRAME}" opacity=".35"/>')
    for i, col in enumerate(["#ff5f57", "#ffbd2e", "#28c841"]):
        parts.append(f'<circle cx="{14 + i * 18}" cy="{TITLEBAR_H // 2}" r="5" fill="{col}"/>')
    parts.append(
        f'<text x="{CANVAS_W // 2}" y="{TITLEBAR_H // 2 + 5}" '
        f'text-anchor="middle" font-size="11" fill="{TITLE_TEXT}">~/portrait.sh</text>'
    )

    # ASCII rows with clip-wipe reveal
    art_x = PAD
    art_y = TITLEBAR_H

    if not STATIC:
        # One <clipPath> per row: a rect that grows from width=0 to full width
        for ri in range(ROWS):
            clip_id  = f"cr{ri}"
            delay    = ri * STAGGER
            row_y    = art_y + ri * CELL_H
            row_h    = CELL_H + 1

            parts.append(f'<defs><clipPath id="{clip_id}">')
            parts.append(
                f'<rect x="{art_x}" y="{row_y}" width="0" height="{row_h}">'
                f'<animate attributeName="width" from="0" to="{ART_W}" '
                f'begin="{delay:.3f}s" dur="{ROW_DUR:.3f}s" fill="freeze"/>'
                f'</rect>'
            )
            parts.append('</clipPath></defs>')

        # Cursor block (rides the right edge of the wipe)
        for ri in range(ROWS):
            delay  = ri * STAGGER
            row_y  = art_y + ri * CELL_H
            end_d  = (ri + 1) * STAGGER  # cursor disappears when next row starts
            parts.append(
                f'<rect x="{art_x}" y="{row_y}" width="{CELL_W}" height="{CELL_H}" '
                f'fill="{CURSOR_COL}" opacity="0">'
                f'<animate attributeName="x" from="{art_x}" to="{art_x + ART_W}" '
                f'begin="{delay:.3f}s" dur="{ROW_DUR:.3f}s" fill="freeze"/>'
                f'<animate attributeName="opacity" values="0;0.7;0" '
                f'keyTimes="0;0.01;1" begin="{delay:.3f}s" dur="{ROW_DUR:.3f}s" fill="freeze"/>'
                f'</rect>'
            )

    # Text rows
    for ri, row in enumerate(rows_txt):
        y    = art_y + ri * CELL_H + (CELL_H - 2)  # baseline
        text = html.escape(row)
        if STATIC:
            parts.append(
                f'<text x="{art_x}" y="{y}" fill="{INK}" '
                f'xml:space="preserve" textLength="{ART_W}" lengthAdjust="spacing">{text}</text>'
            )
        else:
            clip_id = f"cr{ri}"
            parts.append(
                f'<text x="{art_x}" y="{y}" fill="{INK}" clip-path="url(#{clip_id})" '
                f'xml:space="preserve" textLength="{ART_W}" lengthAdjust="spacing">{text}</text>'
            )

    # Status bar
    bar_y = CANVAS_H - STATUS_H
    parts.append(f'<rect y="{bar_y}" width="{CANVAS_W}" height="{STATUS_H}" fill="{BG2}" opacity=".9"/>')
    parts.append(f'<rect y="{bar_y}" width="{CANVAS_W}" height="1" fill="{FRAME}" opacity=".35"/>')
    parts.append(
        f'<text x="{PAD}" y="{bar_y + STATUS_H // 2 + 5}" '
        f'font-size="10" fill="{TITLE_TEXT}">portrait rendered · AdityaTiwari64</text>'
    )

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    if not os.path.exists(SRC):
        print(f"Source image not found: {SRC}")
        print("Place your portrait photo as profile.png in the repo root, then re-run.")
        sys.exit(1)

    print(f"Sampling {SRC} ...")
    rows_txt = sample_image()
    svg = build_svg(rows_txt)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Written {OUT}")


if __name__ == "__main__":
    main()
