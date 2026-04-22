import json
import logging
import re

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a social media manager for Physics Wallah (PW), India's top ed-tech platform.
You create engaging, motivational Instagram content for the PCB Class 12 NEET batch.
Your audience: Class 12 students (ages 16-18) preparing for NEET 2025/2026.
Tone: energetic, peer-like, motivational — not corporate. Use emojis naturally."""

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
5. Return ONLY a valid JSON object with these keys:
   - "caption": the full Instagram caption (no hashtags, they go separately)
   - "hashtags": list of 15-20 relevant hashtag strings (include the #)
   - "story_text": ultra-short version for story overlay (max 50 chars)
   - "category": one of Physics|Chemistry|Biology|General

Return ONLY the JSON — no markdown, no extra text."""


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

    def generate_caption(self, update, post_type: str = "feed") -> dict:
        try:
            client = self._get_client()
        except ValueError as e:
            logger.warning(str(e))
            return self._fallback_caption(update)

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
            return self._parse_response(raw, update)
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return self._fallback_caption(update)

    def _parse_response(self, raw: str, update) -> dict:
        # Strip markdown code fences if present
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("```").strip()
        try:
            data = json.loads(raw)
            return {
                "caption": data.get("caption", "").strip(),
                "hashtags": data.get("hashtags", [])[:20],
                "story_text": data.get("story_text", update.title or "")[:50],
                "category": data.get("category", update.category or "General"),
            }
        except json.JSONDecodeError:
            logger.warning("Claude response was not valid JSON — using fallback")
            return self._fallback_caption(update)

    def _fallback_caption(self, update) -> dict:
        from config import Config
        title = update.title or "New PW Update"
        category = update.category or "General"
        content_type = update.content_type or "general"

        caption_lines = {
            "lecture": f"🎯 New {category} lecture just dropped on PW!\n\n📚 {title}\n\nWatch now and stay ahead in your NEET prep! Link in bio 🔗",
            "dpp": f"📝 Fresh DPP alert for {category}!\n\n{title}\n\nPractice makes perfect — solve today's DPP now! 💪",
            "schedule": f"📅 Schedule Update!\n\n{title}\n\nSave this post so you never miss a class! ✅",
            "tip": f"💡 Pro tip for NEET aspirants!\n\n{title}\n\nShare this with your study group! 🤝",
            "announcement": f"🔔 Important Announcement from PW!\n\n{title}\n\nStay tuned for more updates! 🚀",
        }
        caption = caption_lines.get(content_type, f"🚀 {title}\n\nFollow for daily PW PCB updates! 📲")
        hashtags = Config.HASHTAG_BANK["general"] + Config.HASHTAG_BANK.get(category, [])
        return {
            "caption": caption,
            "hashtags": hashtags[:18],
            "story_text": title[:50],
            "category": category,
        }
