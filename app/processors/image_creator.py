import logging
import os
import textwrap
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Template definitions ──────────────────────────────────────────────────────

TEMPLATES = {
    # 1. Modern gradient (lectures, general)
    "lecture_update": {
        "bg": [(26, 26, 46), (90, 40, 140)],
        "accent": (140, 82, 255),
        "icon": "🎓", "label": "LECTURE", "style": "gradient",
    },
    # 2. Fire orange (DPP, practice)
    "dpp_release": {
        "bg": [(20, 20, 20), (180, 60, 0)],
        "accent": (255, 140, 0),
        "icon": "📝", "label": "DPP", "style": "gradient",
    },
    # 3. Green schedule (timetable)
    "schedule_update": {
        "bg": [(0, 40, 20), (0, 110, 60)],
        "accent": (0, 210, 120),
        "icon": "📅", "label": "SCHEDULE", "style": "schedule",
    },
    # 4. Quote card — pink/magenta (teacher quotes, tips)
    "general_tip": {
        "bg": [(60, 0, 40), (160, 20, 90)],
        "accent": (255, 80, 160),
        "icon": "💡", "label": "PRO TIP", "style": "quote",
    },
    # 5. Breaking news — blue (announcements, news)
    "announcement": {
        "bg": [(0, 20, 60), (0, 60, 160)],
        "accent": (80, 160, 255),
        "icon": "🔔", "label": "BREAKING", "style": "breaking",
    },
}

CONTENT_TYPE_TEMPLATE_MAP = {
    "lecture":      "lecture_update",
    "dpp":          "dpp_release",
    "schedule":     "schedule_update",
    "tip":          "general_tip",
    "announcement": "announcement",
    "general":      "lecture_update",
}


class ImageCreator:
    def __init__(self, config):
        self.config = config
        self.upload_dir = Path(__file__).parent.parent / "dashboard" / "static" / "uploads"
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    # ── Public API ────────────────────────────────────────────────────────────

    def create_post_image(self, update, template: str = None, size=(1080, 1080)) -> str:
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            logger.error("Pillow not installed")
            return ""

        if not template:
            template = CONTENT_TYPE_TEMPLATE_MAP.get(update.content_type or "general", "lecture_update")
        cfg = TEMPLATES.get(template, TEMPLATES["lecture_update"])
        style = cfg.get("style", "gradient")

        img = self._gradient_bg(size, cfg["bg"]).convert("RGBA")
        draw = ImageDraw.Draw(img)

        if style == "quote":
            self._draw_quote(draw, img, update, cfg, size)
        elif style == "breaking":
            self._draw_breaking(draw, img, update, cfg, size)
        elif style == "schedule":
            self._draw_schedule(draw, img, update, cfg, size)
        else:
            self._draw_gradient(draw, img, update, cfg, size)

        filename = f"{uuid.uuid4().hex}.jpg"
        out = self.upload_dir / filename
        img.convert("RGB").save(str(out), "JPEG", quality=93, optimize=True)
        return f"uploads/{filename}"

    def create_story_image(self, update, template: str = None) -> str:
        return self.create_post_image(update, template, size=(1080, 1920))

    # ── Layout renderers ──────────────────────────────────────────────────────

    def _draw_gradient(self, draw, img, update, cfg, size):
        """Default modern gradient layout."""
        w, h = size
        title = update.title or "PW Update"
        body  = (update.body or "")[:180]
        accent = cfg["accent"]

        self._draw_circles(draw, w, h, accent)

        f28 = self._font(28); f36 = self._font(36); f56 = self._font(56)

        # Top label badge
        draw.rounded_rectangle([60, 55, 310, 112], radius=10, fill=accent)
        draw.text((80, 64), f"{cfg['icon']}  {cfg['label']}", fill="white", font=f28)
        draw.text((w - 170, 60), "PW PCB", fill=(255, 255, 255), font=f36)

        # Bottom dark overlay
        draw.rectangle([0, h - 500, w, h], fill=(0, 0, 0, 170))

        # Title
        wrapped = textwrap.fill(title, width=26)
        draw.text((60, h - 480), wrapped, fill="white", font=f56)

        # Body
        if body:
            draw.text((60, h - 240),
                      textwrap.fill(body[:160], width=52),
                      fill=(210, 210, 210), font=f28)

        # Bottom bar
        draw.rectangle([0, h - 78, w, h], fill=accent)
        draw.text((60, h - 60),
                  "Physics Wallah  •  PCB Class 12  •  NEET 2025",
                  fill="white", font=f28)

    def _draw_quote(self, draw, img, update, cfg, size):
        """Quote-card style — large quote marks, centred text."""
        w, h = size
        accent = cfg["accent"]
        title = update.title or "PW Update"
        body  = (update.body or "")[:200]

        self._draw_circles(draw, w, h, accent)

        f22 = self._font(22); f32 = self._font(32); f52 = self._font(52); f80 = self._font(80)

        # Big quotation mark
        draw.text((60, 80), "“", fill=(*accent, 120), font=f80)

        # Centred title box
        overlay = img.copy()
        from PIL import ImageDraw as _ID
        od = _ID.Draw(overlay)
        od.rectangle([80, h // 2 - 260, w - 80, h // 2 + 120], fill=(0, 0, 0, 140))
        img.alpha_composite(overlay)
        draw = _ID.Draw(img)

        wrapped = textwrap.fill(title, width=24)
        draw.text((w // 2, h // 2 - 200), wrapped,
                  fill="white", font=f52, anchor="mm", align="center")

        if body:
            draw.text((w // 2, h // 2 + 60),
                      textwrap.fill(body[:120], width=44),
                      fill=(200, 200, 200), font=f22, anchor="mm", align="center")

        # Accent bottom strip
        draw.rectangle([0, h - 78, w, h], fill=accent)
        draw.text((60, h - 60), f"{cfg['icon']}  PW PCB  •  NEET 2025", fill="white", font=f22)

        # Source label
        draw.rounded_rectangle([60, 55, 260, 106], radius=8, fill=accent)
        draw.text((78, 62), cfg["label"], fill="white", font=f32)

    def _draw_breaking(self, draw, img, update, cfg, size):
        """Breaking-news style — bold top banner."""
        w, h = size
        accent = cfg["accent"]
        title = update.title or "Breaking Update"
        body  = (update.body or "")[:200]

        # Top urgent banner
        draw.rectangle([0, 0, w, 130], fill=(*accent, 230))
        f30 = self._font(30); f48 = self._font(48); f60 = self._font(60)
        draw.text((w // 2, 65), f"⚡  {cfg['label']}  ⚡",
                  fill="white", font=f48, anchor="mm")

        self._draw_circles(draw, w, h, accent)

        # Dark panel
        draw.rectangle([0, h - 560, w, h], fill=(0, 0, 0, 180))

        # Title
        wrapped = textwrap.fill(title, width=24)
        draw.text((60, h - 540), wrapped, fill="white", font=f60)

        if body:
            draw.text((60, h - 260),
                      textwrap.fill(body[:180], width=50),
                      fill=(200, 220, 255), font=f30)

        # Bottom
        draw.rectangle([0, h - 80, w, h], fill=(*accent, 220))
        draw.text((60, h - 62),
                  "Physics Wallah  •  PCB Class 12",
                  fill="white", font=f30)

    def _draw_schedule(self, draw, img, update, cfg, size):
        """Clean schedule/timetable card."""
        w, h = size
        accent = cfg["accent"]
        title = update.title or "Schedule Update"
        body  = (update.body or "")[:300]

        self._draw_circles(draw, w, h, accent)

        f24 = self._font(24); f36 = self._font(36); f52 = self._font(52)

        # Header
        draw.rectangle([0, 0, w, 140], fill=(*accent, 200))
        draw.text((w // 2, 70), "📅  CLASS SCHEDULE", fill="white", font=f52, anchor="mm")

        # Content area
        draw.rectangle([60, 180, w - 60, h - 100], fill=(0, 0, 0, 150), )
        draw.rounded_rectangle([60, 180, w - 60, h - 100], radius=16, fill=(0, 0, 0, 150))

        # Lines of schedule text
        draw.text((100, 210), title, fill=accent, font=f36)
        if body:
            y = 290
            for line in body.split("\n")[:10]:
                if line.strip():
                    draw.text((100, y), line.strip()[:55], fill=(220, 220, 220), font=f24)
                    y += 46
                    if y > h - 150:
                        break

        draw.rectangle([0, h - 80, w, h], fill=accent)
        draw.text((60, h - 62), "PW PCB  •  NEET 2025  •  Class 12", fill="white", font=f24)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _gradient_bg(self, size, colors):
        from PIL import Image, ImageDraw
        img = Image.new("RGB", size, colors[0])
        d = ImageDraw.Draw(img)
        for i in range(size[1]):
            t = i / size[1]
            r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * t)
            g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * t)
            b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * t)
            d.line([(0, i), (size[0], i)], fill=(r, g, b))
        return img

    def _draw_circles(self, draw, w, h, accent):
        a = (*accent, 25)
        draw.ellipse([w - 320, -120, w + 120, 320], fill=a)
        draw.ellipse([-120, h - 320, 220, h + 120], fill=a)
        draw.ellipse([w // 2 - 60, h // 2 - 60, w // 2 + 60, h // 2 + 60], fill=(*accent, 12))

    def _font(self, size: int):
        from PIL import ImageFont
        font_dir = Path(__file__).parent.parent / "dashboard" / "static" / "fonts"
        font_dir.mkdir(parents=True, exist_ok=True)
        bold = font_dir / "Poppins-Bold.ttf"
        reg  = font_dir / "Poppins-Regular.ttf"
        if not bold.exists():
            self._dl_font("https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Bold.ttf", bold)
        if not reg.exists():
            self._dl_font("https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Regular.ttf", reg)
        for path in [str(bold), str(reg),
                     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                     "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"]:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()

    @staticmethod
    def _dl_font(url, dest):
        try:
            import urllib.request
            urllib.request.urlretrieve(url, str(dest))
        except Exception as e:
            logger.warning(f"Font download failed: {e}")
