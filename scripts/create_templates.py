"""
Generate base template PNG files for image creation.
Run once after setup to create the template backgrounds.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("❌ Pillow not installed. Run: pip install Pillow")
    sys.exit(1)

TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "app", "dashboard", "static", "templates"
)
os.makedirs(TEMPLATE_DIR, exist_ok=True)

TEMPLATES = {
    "lecture_update":  [(26,26,46), (90,40,140)],
    "dpp_release":     [(20,20,20), (180,80,0)],
    "schedule_update": [(0,40,25),  (0,110,70)],
    "general_tip":     [(60,0,40),  (160,20,90)],
    "announcement":    [(0,25,70),  (0,70,160)],
}

def make_gradient(size, c1, c2):
    img = Image.new("RGB", size)
    draw = ImageDraw.Draw(img)
    for i in range(size[1]):
        t = i / size[1]
        r = int(c1[0] + (c2[0]-c1[0]) * t)
        g = int(c1[1] + (c2[1]-c1[1]) * t)
        b = int(c1[2] + (c2[2]-c1[2]) * t)
        draw.line([(0,i),(size[0],i)], fill=(r,g,b))
    return img

for name, (c1, c2) in TEMPLATES.items():
    # Feed (1080×1080)
    feed_path = os.path.join(TEMPLATE_DIR, f"base_{name}_feed.png")
    make_gradient((1080, 1080), c1, c2).save(feed_path)
    print(f"  ✅ {feed_path}")
    # Story (1080×1920)
    story_path = os.path.join(TEMPLATE_DIR, f"base_{name}_story.png")
    make_gradient((1080, 1920), c1, c2).save(story_path)
    print(f"  ✅ {story_path}")

print("\n✅ All template images created successfully.")
