"""Render the integration icon (brand/icon.png, 256x256, and icon@2x 512x512)."""
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "custom_components/ring_plus/brand"
BLUE, DARK, WHITE, ACCENT = (3, 169, 244), (1, 87, 155), (255, 255, 255), (255, 193, 7)


def render(size: int) -> Image.Image:
    s = 4  # supersample
    n = size * s
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    u = n / 256

    def p(x, y):
        return (x * u, y * u)

    d.rounded_rectangle([0, 0, n - 1, n - 1], radius=56 * u, fill=BLUE)
    # shield
    shield = [p(128, 28), p(206, 56), p(206, 130), p(196, 166), p(128, 228), p(60, 166), p(50, 130), p(50, 56)]
    d.polygon(shield, fill=WHITE)
    inner = [p(128, 44), p(192, 67), p(192, 129), p(184, 158), p(128, 210), p(72, 158), p(64, 129), p(64, 67)]
    d.polygon(inner, fill=DARK)
    # ring
    d.ellipse([p(128 - 44, 122 - 44), p(128 + 44, 122 + 44)], outline=WHITE, width=int(14 * u))
    d.ellipse([p(128 - 14, 122 - 14), p(128 + 14, 122 + 14)], fill=ACCENT)
    return img.resize((size, size), Image.LANCZOS)


OUT.mkdir(parents=True, exist_ok=True)
render(256).save(OUT / "icon.png")
render(512).save(OUT / "icon@2x.png")
print("wrote", OUT)
