"""Generate RadioDesk.ico from scratch using Pillow."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SIZES = [16, 32,48, 64, 128, 256]
OUT = Path(__file__).parent / "RadioDesk.ico"

BRAND = (107, 46, 166)       # #6B2EA6
ACCENT = (175, 111, 86)      # #AF6F56
BG = (26, 13, 46)            # #1a0d2e


def make_frame(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background circle
    m = int(size * 0.06)
    draw.ellipse([m, m, size - m - 1, size - m - 1], fill=BG)

    # Gradient arc (fake with two arcs)
    bw = max(2, size // 10)
    draw.arc([m + bw, m + bw, size - m - bw - 1, size - m - bw - 1],
             start=200, end=400, fill=BRAND, width=bw)
    draw.arc([m + bw, m + bw, size - m - bw - 1, size - m - bw - 1],
             start=40, end=200, fill=ACCENT, width=bw)

    # Radio waves (3 arcs in white)
    cx, cy = size // 2, size // 2
    for r_ratio in (0.18, 0.28, 0.38):
        r = int(size * r_ratio)
        w = max(1, size // 28)
        draw.arc([cx - r, cy - r, cx + r, cy + r],
                 start=225, end=315, fill=(255, 255, 255, 220), width=w)

    # Center dot
    dot = max(2, size // 14)
    draw.ellipse([cx - dot, cy - dot, cx + dot, cy + dot],
                 fill=(255, 255, 255))

    return img


frames = [make_frame(s) for s in SIZES]
frames[0].save(OUT, format="ICO", sizes=[(s, s) for s in SIZES],
               append_images=frames[1:])
print(f"Icon saved -> {OUT}")
