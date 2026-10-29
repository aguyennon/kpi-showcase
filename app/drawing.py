"""app/drawing.py

Works on the PNG that dalmenit:8816 returns. That one picture holds three
things stacked vertically:

    382-01309 · Assembly 54              <- title (ignored)
    ┌──────────┬──────┐  ┬
    │   239    │ 240  │  │               <- the drawing   -> crop_drawing()
    └──────────┴──────┘  ┴
    |<---- 1501.8 mm ---->|
    Item 239 F1 825 × 1384               <- the item list -> read_items()
    Item 240 B1 676 × 1384

HOW WE FIND THE PARTS
The drawing is the only part with long STRAIGHT LINES: frame edges and
dimension lines. Text never has them, because even a long title is letters
with gaps. So:
    first row with a long line = top of the drawing
    last row with a long line  = bottom of the drawing (the width dimension)
    everything below that      = the item list
"""

import os
import re
from io import BytesIO

import pytesseract
from PIL import Image

# A row counts as "part of the drawing" if it holds an unbroken dark run at
# least this fraction of the image width. Far longer than any run in text,
# far shorter than a frame edge or dimension line.
MIN_LINE_FRACTION = 0.25

# How much darker than the background a pixel must be to count as "ink"
# (0 = black, 255 = white). The light-blue glass doesn't count; the frame,
# the lines, the orange highlight and the grey text do.
DARKER_BY = 40

# Tesseract is a separate Windows program; pytesseract only runs it. If it
# isn't on PATH, tell pytesseract where the .exe is via .env.
# os.environ.get(name) returns None when the line is missing, so on a
# machine where tesseract IS on PATH, nothing needs setting.
if os.environ.get("KPI_TESSERACT_CMD"):
    pytesseract.pytesseract.tesseract_cmd = os.environ["KPI_TESSERACT_CMD"]


def _analyse(png: bytes):
    """Shared first step for both functions: open the image and find the
    rows that contain long lines. Returns everything the callers need, so
    neither has to repeat the work."""

    # BytesIO wraps the bytes so Pillow can read them like a file.
    image = Image.open(BytesIO(png)).convert("RGB")
    gray = image.convert("L")          # greyscale: one number per pixel
    width, height = gray.size

    # Background sampled from the top-left corner, which is always empty
    # margin. Measured, not hard-coded, so a shade change won't break it.
    cutoff = gray.getpixel((2, 2)) - DARKER_BY

    # Dark pixels become "#" (byte 35), light ones "." (byte 46), so each row
    # turns into a byte string like b"...#####...##...". Searching it for a
    # long "#####" run with `in` runs in C: fast, with no NumPy needed.
    data = gray.point(lambda v: 35 if v < cutoff else 46).tobytes()
    line = b"#" * int(width * MIN_LINE_FRACTION)

    # data[y*width:(y+1)*width] slices out row y on its own.
    rows = [y for y in range(height) if line in data[y * width:(y + 1) * width]]

    # Breathing room around crops, proportional to the image size.
    pad = max(8, height // 60)

    return image, gray, cutoff, rows, pad


def _ink_box(gray, cutoff, area, pad):
    """Tightest box around the ink inside `area` (left, top, right, bottom),
    padded a little. getbbox() returns the box around all non-zero pixels,
    so ink is marked 255 and background 0. Returns None if the area is blank."""
    ink = gray.point(lambda v: 255 if v < cutoff else 0)
    box = ink.crop(area).getbbox()
    if box is None:
        return None

    # box is relative to the cropped area, so add the area's offset back
    # to get positions in the full image.
    left, top = area[0], area[1]
    width, height = gray.size
    return (
        max(left + box[0] - pad, 0),
        max(top + box[1] - pad, 0),
        min(left + box[2] + pad, width),
        min(top + box[3] + pad, height),
    )


def crop_drawing(png: bytes) -> bytes:
    """Just the drawing, as a PNG. Returns the original if no drawing is
    found: better to show too much than nothing."""
    image, gray, cutoff, rows, pad = _analyse(png)
    if not rows:
        return png

    width, height = gray.size
    top = max(rows[0] - pad, 0)
    bottom = min(rows[-1] + pad, height)

    # Trim the empty side margins (the "2111.4 mm" label is ink, so it stays).
    box = _ink_box(gray, cutoff, (0, top, width, bottom), pad) or (0, top, width, bottom)

    out = BytesIO()
    # optimize=True: slower to save but smaller. The TV caches it, so it's
    # paid once per product.
    image.crop((box[0], top, box[2], bottom)).save(out, "PNG", optimize=True)
    return out.getvalue()


# One item line, as OCR returns it. Written to tolerate OCR's usual slips:
#   [Il1]tem   "Item" sometimes comes back as "ltem" or "1tem"
#   [^\d\s]?   the × sign comes back as x, X, *, = ... (it read "=" in
#              testing), so accept ANY one character that isn't a digit
#              or a space, or none at all
#   \s*        spacing around × varies
# The groups () capture the four values we keep.
_ITEM_LINE = re.compile(r"[Il1]tem\s+(\d+)\s+(\w{1,3})\s+(\d+)\s*[^\d\s]?\s*(\d+)")

# Codes are a letter followed by a digit (F1, B1). OCR sometimes reads the
# letter as a look-alike digit, so if a code STARTS with a digit, swap it
# for the letter it most likely was.
_LETTER_FIXES = {"8": "B", "0": "O", "5": "S", "6": "G"}


def read_items(png: bytes) -> list[dict]:
    """The item list under the drawing, read with OCR.
    Returns e.g. [{"item": 239, "code": "F1", "width": 825, "height": 1384}].
    Returns [] if there's no list or nothing could be read."""
    image, gray, cutoff, rows, pad = _analyse(png)
    if not rows:
        return []

    width, height = gray.size
    start = min(rows[-1] + pad, height)     # just below the width dimension line
    if start >= height:
        return []

    box = _ink_box(gray, cutoff, (0, start, width, height), pad)
    if box is None:
        return []

    region = gray.crop(box)

    # Enlarge 3x before reading. The text is ~12px tall, and Tesseract is
    # tuned for text around 30px: small text is where most misreads happen.
    # LANCZOS is a high-quality resize that keeps letter edges smooth.
    region = region.resize((region.width * 3, region.height * 3), Image.LANCZOS)

    # --psm 6 = "page segmentation mode 6": treat the image as one uniform
    # block of text lines. The default mode tries to detect columns and
    # layout, which can split "825 × 1384" into separate pieces.
    text = pytesseract.image_to_string(region, config="--psm 6")

    items = []
    for line in text.splitlines():
        match = _ITEM_LINE.search(line)
        if match is None:
            continue          # not a valid item line: skip it, never guess

        code = match.group(2).upper()
        if code[0].isdigit() and code[0] in _LETTER_FIXES:
            code = _LETTER_FIXES[code[0]] + code[1:]

        items.append({
            "item": int(match.group(1)),
            "code": code,
            "width": int(match.group(3)),
            "height": int(match.group(4)),
        })

    return items