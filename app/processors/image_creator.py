import logging
import os
import textwrap
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

TEMPLATE_COLORS = {
    "lecture_update": {
        "bg": [(26, 26, 46), (90, 40, 140)],   # dark navy → purple gradient
        "accent": (140, 82, 255),
        "icon": "🎓",
        "label": "LECTURE",
    },
    "dpp_release": {
        "bg": [(20, 20, 20), (200, 100, 0)],    # dark → orange
        "accent": (255, 165, 0),
        "icon": "📝",
        "label": "DPP",
    },
    "schedule_update": {
        "bg": [(0, 50, 30), (0, 120, 80)],      # dark green
        "accent": (0, 200, 130),
        "icon": "📅",
        "label": "SCHEDULE",
    },
    "general_tip": {
        "bg": [(80, 0, 50), (180, 30, 100)],    # dark pink
        "accent": (255, 80, 150),
        "icon": "💡",
        "label": "TIP",
    },
    "announcement": {
        "bg": [(0, 30, 80), (0, 80, 180)],      # dark blue
        "accent": (80, 160, 255),
        "icon": "🔔",
        "label": "NEWS",
    },
}

CONTENT_TYPE_TEMPLATE_MAP = {
    "lecture": "lecture_update",
    "dpp": "dpp_release",
    "schedule": "schedule_update",
    "tip": "general_tip",
    "announcement": "announcement",
    "general": "lecture_update",
}


class ImageCreator:
    def __init__(self, config):
        self.config = config
        self.upload_dir = Path(__file__).parent.parent / "dashboard" / "static" / "uploads"
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def create_post_image(self, update, template: str = None, size: tuple = (1080, 1080)) -> str:
        try:
            from PIL import Image, ImageDraw, ImageFont, ImageFilter
        except ImportError:
            logger.error("Pillow not installed")
            return ""

        if template is None:
            template = CONTENT_TYPE_TEMPLATE_MAP.get(update.content_type or "general", "lecture_update")

        cfg = TEMPLATE_COLORS.get(template, TEMPLATE_COLORS["lecture_update"])
        title = update.title or "PW Update"
        body_text = (update.body or "")[:200]

        img = self._create_gradient_bg(size, cfg["bg"]).convert("RGBA")
        draw = ImageDraw.Draw(img)

        # Geometric accent shapes
        self._draw_accents(draw, img.size, cfg["accent"])

        # Label badge
        font_small = self._load_font(28)
        font_medium = self._load_font(38)
        font_large = self._load_font(58)

        label = f"{cfg['icon']}  {cfg['label']}"
        draw.rounded_rectangle([60, 60, 60 + 220, 115], radius=10, fill=cfg["accent"])
        draw.text((80, 68), label, fill="white", font=font_small)

        # PW watermark top-right
        draw.text((size[0] - 160, 65), "PW PCB", fill=(255, 255, 255), font=font_medium)

        # Title block
        wrapped_title = textwrap.fill(title, width=28)
        draw.rectangle([0, size[1] - 480, size[0], size[1]], fill=(0, 0, 0, 160))
        draw.text((60, size[1] - 460), wrapped_title, fill="white", font=font_large)

        # Body snippet
        if body_text:
            wrapped_body = textwrap.fill(body_text[:140], width=50)
            draw.text((60, size[1] - 220), wrapped_body, fill=(220, 220, 220), font=font_small)

        # Bottom bar
        draw.rectangle([0, size[1] - 80, size[0], size[1]], fill=cfg["accent"])
        draw.text((60, size[1] - 60), "Physics Wallah  •  PCB Class 12  •  NEET 2025", fill="white", font=font_small)

        filename = f"{uuid.uuid4().hex}.jpg"
        output_path = self.upload_dir / filename
        img.convert("RGB").save(str(output_path), "JPEG", quality=92, optimize=True)
        return f"uploads/{filename}"

    def create_story_image(self, update, template: str = None) -> str:
        return self.create_post_image(update, template, size=(1080, 1920))

    def _create_gradient_bg(self, size, colors):
        from PIL import Image
        img = Image.new("RGB", size, colors[0])
        draw_layer = Image.new("RGBA", size, (0, 0, 0, 0))
        from PIL import ImageDraw
        draw = ImageDraw.Draw(draw_layer)
        for i in range(size[1]):
            t = i / size[1]
            r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * t)
            g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * t)
            b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * t)
            draw.line([(0, i), (size[0], i)], fill=(r, g, b))
        return draw_layer.convert("RGB")

    def _draw_accents(self, draw, size, accent_color):
        # Decorative circles
        a = (*accent_color, 30)
        draw.ellipse([size[0] - 300, -100, size[0] + 100, 300], fill=a)
        draw.ellipse([-100, size[1] - 300, 200, size[1] + 100], fill=a)
        draw.ellipse([size[0] // 2 - 50, size[1] // 2 - 50,
                      size[0] // 2 + 50, size[1] // 2 + 50], fill=(*accent_color, 15))

    def _load_font(self, size: int):
        from PIL import ImageFont
        font_paths = [
            str(Path(__file__).parent.parent / "dashboard" / "static" / "fonts" / "Poppins-Bold.ttf"),
            str(Path(__file__).parent.parent / "dashboard" / "static" / "fonts" / "Poppins-Regular.ttf"),
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
        for path in font_paths:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
        return ImageFont.load_default()
