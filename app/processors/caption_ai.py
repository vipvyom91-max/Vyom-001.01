import json
import logging
import random
import re

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a social media manager for Physics Wallah (PW), India's top ed-tech platform.
You create engaging, motivational Instagram content for the PCB Class 12 NEET batch.
Audience: Class 12 students (16-18) preparing for NEET 2025/2026.
Tone: energetic, peer-like, motivational. Use emojis naturally."""

CAPTION_PROMPT_TEMPLATE = """Create an Instagram {post_type} caption for this PW update.

UPDATE:
Title: {title}
Source: {source}
Content Type: {content_type}
Category: {category}
Details: {body}

RULES:
1. Hook line first (bold question or powerful statement)
2. 3-5 lines of main content with relevant emojis
3. Strong call-to-action at the end
4. Under 2200 characters total
5. Return ONLY valid JSON with keys:
   - "caption": full Instagram caption (no hashtags)
   - "hashtags": list of 15-20 hashtag strings (include the #)
   - "story_text": ultra-short story overlay text (max 50 chars)
   - "category": one of Physics|Chemistry|Biology|General

Return ONLY the JSON — no markdown, no extra text."""

# ── 3 caption styles: Hype · Educational · Funny (Hindi-English mix) ─────────

_HYPE = {
    "lecture": [
        "🔥 LECTURE JUST DROPPED AND IT'S 🤯\n\n{title}\n\nYaar dekha kya? Comment mein batao agar ye topic exam mein aaya! 👇\n\nFollow karo daily PW updates ke liye 📲",
        "⚡ NEW LECTURE ALERT!\n\n{title}\n\nNotes chahiye? DM karo 'NOTES' 📝\nLink bio mein hai! 🔗",
    ],
    "dpp": [
        "📝 DPP ALERT 🚨\n\n{title}\n\nKitne questions sahi kiye? Score comment karo! 👇💪",
        "🧠 TEST YOURSELF!\n\n{title}\n\n60 minutes. No shortcuts. Let's go! 🔥\nScore share karo! ✅",
    ],
    "schedule": [
        "📅 SCHEDULE UPDATE — SAVE THIS POST NOW! 🔖\n\n{title}\n\nYe class mat chhodna! Reminder set karo ⏰",
        "⏰ CLASS ALERT!\n\n{title}\n\nCalendar mark karo bhai! 🗓️ Share karo study group mein! 🤝",
    ],
    "announcement": [
        "🚨 IMPORTANT ANNOUNCEMENT FROM PW!\n\n{title}\n\nShare karo — sab ko pata hona chahiye! 📢",
        "⚡ BIG NEWS!\n\n{title}\n\nComment mein reaction do! 👇",
    ],
    "tip": [
        "💡 PRO TIP that toppers use!\n\n{title}\n\nSave this post — exam mein kaam aayega! 🎯",
        "🧠 Ye trick 90% students ko pata hi nahi!\n\n{title}\n\nBookmark karo ye post! 📌",
    ],
}

_EDUCATIONAL = {
    "lecture": [
        "📚 New lecture on Physics Wallah\n\n{title}\n\nImportant for NEET — watch and take notes! ✏️\nLink in bio 🔗",
        "🎓 {title}\n\nClear your concepts with this detailed lecture. Consistent revision is the key to NEET success! 📖",
    ],
    "dpp": [
        "📝 Daily Practice Problems\n\n{title}\n\nRegular practice separates toppers from the rest. Attempt today's DPP! 💪",
        "🧪 {title}\n\nSolve these problems to strengthen your understanding. Track your score and improve daily! 📊",
    ],
    "schedule": [
        "📅 Class Schedule Update\n\n{title}\n\nPlan your study sessions accordingly. Consistency is everything! ✅",
        "🗓️ {title}\n\nNever miss a class. Your NEET rank depends on your consistency! 🎯",
    ],
    "announcement": [
        "📢 Important Update from Physics Wallah\n\n{title}\n\nStay updated for your NEET preparation! 🔔",
        "🔔 {title}\n\nShare this with your classmates! 📲",
    ],
    "tip": [
        "💡 Study Tip for NEET Aspirants\n\n{title}\n\nIncorporate this in your prep. Small improvements compound over time! 📈",
        "🎯 {title}\n\nApply this technique in your next study session! 💪",
    ],
}

_FUNNY = {
    "lecture": [
        "POV: Sir ne phir se kuch aisa padhaya jo boards mein nahi tha 😭\n\n{title}\n\nBut NEET mein definitely aayega 😤 Watch karo! 🔥",
        "Maa ne pucha — phone pe kya dekh raha hai?\nMaine bola — '{title}' 😇\n\n(Sir ka lecture tha — legit study!) 📚",
    ],
    "dpp": [
        "Teacher: 'Ye easy hai'\nThe DPP: {title} 😭\n\nFir bhi attempt karo — practice makes perfect! 🔥",
        "Jab DPP release hoti hai aur phone charge pe hota hai 😤📱\n\n{title}\n\nKoi reason nahi skip karne ka! 😂 Let's go! 💪",
    ],
    "schedule": [
        "Me at 3 AM making study schedule 😤📅\n\n{title}\n\nMe at 6 AM: 😴💤\n\nSave karo aur actually attend karo! 😂🙏",
        "Schedule dekh ke: 'Sab cover ho jaayega!' 💪\nSchedule follow karte waqt: 😵\n\n{title}\n\nBut seriously — mark karo! ✅",
    ],
    "announcement": [
        "PW ne announce kiya aur mera phone notification se gir gaya 😭\n\n{title}\n\nBig news! 🚨 Share karo!",
        "Sir: 'Ek important announcement hai'\nHum sab: 👀👀👀\n\n{title}\n\nComment mein reaction do! 👇",
    ],
    "tip": [
        "Ye tip 11th mein pata hoti toh life different hoti 😭\n\n{title}\n\nSave karo — kaam aayega! 🙏📌",
        "Topper bhai ne share kiya ye secret tip 🤫\n\n{title}\n\nFollow karo — baad mein thank karna! 😂🔥",
    ],
}

_STYLES = [_HYPE, _EDUCATIONAL, _FUNNY]
_STYLE_MAP = {"hype": _HYPE, "educational": _EDUCATIONAL, "funny": _FUNNY}


class CaptionAI:
    def __init__(self, config):
        self.config = config
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.config.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY not set")
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.config.ANTHROPIC_API_KEY)
        return self._client

    def generate_caption(self, update, post_type: str = "feed",
                         style: str = "random") -> dict:
        """
        style: "random" | "hype" | "educational" | "funny"
        If Anthropic API key is set, uses Claude AI (style param is ignored for AI).
        Otherwise uses template fallback with the requested style.
        """
        try:
            client = self._get_client()
        except ValueError as e:
            logger.debug(str(e))
            return self._fallback(update, style)

        prompt = CAPTION_PROMPT_TEMPLATE.format(
            post_type=post_type,
            title=update.title or "",
            source=update.source.source_type if update.source else "unknown",
            content_type=update.content_type or "general",
            category=update.category or "General",
            body=(update.body or "")[:600],
        )
        try:
            message = client.messages.create(
                model="claude-opus-4-5",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            result = self._parse(raw, update)
            result["style"] = "ai"
            return result
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return self._fallback(update, style)

    def _parse(self, raw: str, update) -> dict:
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
        try:
            data = json.loads(raw)
            return {
                "caption":    data.get("caption", "").strip(),
                "hashtags":   data.get("hashtags", [])[:20],
                "story_text": data.get("story_text", update.title or "")[:50],
                "category":   data.get("category", update.category or "General"),
                "style":      "ai",
            }
        except json.JSONDecodeError:
            return self._fallback(update, "random")

    def _fallback(self, update, style: str = "random") -> dict:
        from config import Config
        title    = (update.title or "PW Update")[:120]
        ctype    = update.content_type or "general"
        category = update.category or "General"

        if style == "random" or style not in _STYLE_MAP:
            chosen_style = random.choice(_STYLES)
            style_name = random.choice(["hype", "educational", "funny"])
        else:
            chosen_style = _STYLE_MAP[style]
            style_name = style

        templates = chosen_style.get(ctype) or chosen_style.get("lecture", ["🚀 {title}\n\nFollow for daily PW updates! 📲"])
        caption   = random.choice(templates).format(title=title)

        hashtags = list(dict.fromkeys(
            Config.HASHTAG_BANK["general"]
            + Config.HASHTAG_BANK.get(category, [])
            + Config.HASHTAG_BANK.get(
                "DPP" if ctype == "dpp" else "Schedule" if ctype == "schedule" else "general", []
            )
        ))
        return {
            "caption":    caption,
            "hashtags":   hashtags[:20],
            "story_text": title[:50],
            "category":   category,
            "style":      style_name,
        }
