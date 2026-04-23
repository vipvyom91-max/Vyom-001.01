"""Generate PWA app icons."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow not installed"); sys.exit(1)

ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "app", "dashboard", "static", "icons")
os.makedirs(ICON_DIR, exist_ok=True)

def make_icon(size):
    img = Image.new("RGB", (size, size), (13, 13, 26))
    draw = ImageDraw.Draw(img)
    # Purple gradient circle background
    margin = size // 8
    draw.ellipse([margin, margin, size - margin, size - margin], fill=(124, 58, 237))
    # Inner circle
    m2 = size // 5
    draw.ellipse([m2, m2, size - m2, size - m2], fill=(91, 33, 182))
    # "PW" text
    try:
        font = ImageFont.truetype("/system/fonts/Roboto-Bold.ttf", size // 3)
    except:
        font = ImageFont.load_default()
    text = "PW"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(((size - tw) // 2, (size - th) // 2 - size // 20), text, fill="white", font=font)
    return img

for size in [192, 512]:
    path = os.path.join(ICON_DIR, f"icon-{size}.png")
    make_icon(size).save(path)
    print(f"✅ {path}")

print("✅ Icons created!")
