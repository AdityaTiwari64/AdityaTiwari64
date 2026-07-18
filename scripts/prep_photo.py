#!/usr/bin/env python3
"""
Prepare a portrait photo for clean ASCII conversion:
  1. Remove the background (rembg) so the subject is isolated.
  2. Boost LOCAL contrast (CLAHE via OpenCV) so a flatly-lit face gains
     highlights and shadows -- this turns a dark blob into a readable face.
  3. Composite the subject onto pure white so the background maps to blank
     (white -> spaces in the ASCII density ramp).

Output: source-prepped.png (grayscale), consumed by make_ascii_svg.py.
Run once whenever the source photo changes; the ASCII SVG itself is static.

    python scripts/prep_photo.py <input.jpg> [output.png]

Requirements (local only -- not needed by CI):
    pip install pillow numpy opencv-python rembg
"""
import os
import sys

# These imports will only work if portrait deps are installed locally
try:
    import cv2
    import numpy as np
    from PIL import Image
    from rembg import remove
except ImportError:
    print("Missing portrait dependencies. Install them locally:")
    print("  pip install pillow numpy opencv-python rembg")
    sys.exit(1)

HERE = os.path.dirname(os.path.abspath(__file__))
INP  = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "source-photo.jpg")
OUT  = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "source-prepped.png")


def main():
    print(f"Input:  {INP}")

    # 1. Remove background
    print("Removing background (rembg) ...")
    with open(INP, "rb") as f:
        raw = f.read()
    cut_bytes = remove(raw)                         # returns PNG bytes with alpha
    cut = Image.open(__import__("io").BytesIO(cut_bytes)).convert("RGBA")

    # 2. Boost local contrast with CLAHE (on the luminance channel)
    print("Applying CLAHE local contrast ...")
    bgr    = cv2.cvtColor(np.array(cut.convert("RGB")), cv2.COLOR_RGB2BGR)
    lab    = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe  = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    l_eq   = clahe.apply(l)
    lab_eq = cv2.merge([l_eq, a, b])
    bgr_eq = cv2.cvtColor(lab_eq, cv2.COLOR_LAB2BGR)
    rgb_eq = cv2.cvtColor(bgr_eq, cv2.COLOR_BGR2RGB)

    # Re-attach the original alpha mask
    enhanced = Image.fromarray(rgb_eq).convert("RGBA")
    enhanced.putalpha(cut.split()[3])   # restore alpha from rembg

    # 3. Composite onto pure white
    print("Compositing onto white ...")
    white = Image.new("RGBA", enhanced.size, (255, 255, 255, 255))
    white.paste(enhanced, mask=enhanced.split()[3])
    result = white.convert("L")   # grayscale

    result.save(OUT)
    print(f"Written {OUT}  ({result.size[0]}x{result.size[1]})")
    print("Now run:  python scripts/make_ascii_svg.py")


if __name__ == "__main__":
    main()
