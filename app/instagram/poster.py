import logging
import os
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com/v18.0"


class InstagramPoster:
    """Posts to Instagram via the official Graph API (business/creator accounts)."""

    def __init__(self, config):
        self.config = config
        self.token = config.INSTAGRAM_ACCESS_TOKEN if hasattr(config, "INSTAGRAM_ACCESS_TOKEN") else ""
        self.ig_id = config.INSTAGRAM_BUSINESS_ACCOUNT_ID if hasattr(config, "INSTAGRAM_BUSINESS_ACCOUNT_ID") else ""
        self.public_base_url = getattr(config, "PUBLIC_BASE_URL", "")

    # ── public API ────────────────────────────────────────────────────────
    def post_feed_image(self, post, app=None) -> str:
        """Upload a single image to Instagram feed. Returns IG post ID."""
        image_url = self._resolve_image_url(post.image_path, app)
        if not image_url:
            raise ValueError("Cannot resolve public image URL for Instagram posting")

        caption = post.full_caption
        container_id = self._create_media_container(image_url, caption)
        post_id = self._publish_container(container_id)
        logger.info(f"Posted to Instagram: {post_id}")
        return post_id

    def post_story(self, post, app=None) -> str:
        image_url = self._resolve_image_url(post.image_path, app)
        if not image_url:
            raise ValueError("Cannot resolve public image URL")
        container_id = self._create_media_container(image_url, "", media_type="STORIES")
        return self._publish_container(container_id)

    def post_carousel(self, posts: list, caption: str, app=None) -> str:
        child_ids = []
        for p in posts:
            img_url = self._resolve_image_url(p.image_path, app)
            if img_url:
                r = requests.post(
                    f"{GRAPH_BASE}/{self.ig_id}/media",
                    params={
                        "image_url": img_url,
                        "is_carousel_item": "true",
                        "access_token": self.token,
                    },
                    timeout=30,
                )
                r.raise_for_status()
                child_ids.append(r.json()["id"])

        if not child_ids:
            raise ValueError("No valid images for carousel")

        carousel_r = requests.post(
            f"{GRAPH_BASE}/{self.ig_id}/media",
            params={
                "media_type": "CAROUSEL",
                "children": ",".join(child_ids),
                "caption": caption,
                "access_token": self.token,
            },
            timeout=30,
        )
        carousel_r.raise_for_status()
        return self._publish_container(carousel_r.json()["id"])

    def verify_connection(self) -> dict:
        """Test credentials — returns account info dict."""
        if not self.token or not self.ig_id:
            return {"ok": False, "error": "Missing credentials"}
        try:
            r = requests.get(
                f"{GRAPH_BASE}/{self.ig_id}",
                params={"fields": "id,username,followers_count", "access_token": self.token},
                timeout=10,
            )
            r.raise_for_status()
            return {"ok": True, **r.json()}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── private helpers ───────────────────────────────────────────────────
    def _create_media_container(self, image_url: str, caption: str, media_type: str = "") -> str:
        params = {
            "image_url": image_url,
            "caption": caption,
            "access_token": self.token,
        }
        if media_type:
            params["media_type"] = media_type

        r = requests.post(
            f"{GRAPH_BASE}/{self.ig_id}/media",
            params=params,
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["id"]

    def _publish_container(self, container_id: str) -> str:
        r = requests.post(
            f"{GRAPH_BASE}/{self.ig_id}/media_publish",
            params={"creation_id": container_id, "access_token": self.token},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["id"]

    def _resolve_image_url(self, image_path: str, app=None) -> str:
        if not image_path:
            return ""
        if image_path.startswith("http"):
            return image_path
        if self.public_base_url:
            return f"{self.public_base_url.rstrip('/')}/static/{image_path}"
        # Fallback: instagrapi local upload
        if app:
            static_folder = Path(app.static_folder) if hasattr(app, "static_folder") else Path("app/dashboard/static")
            local_path = static_folder / image_path
            if local_path.exists():
                return self._upload_via_instagrapi(str(local_path))
        return ""

    def _upload_via_instagrapi(self, local_path: str) -> str:
        """Use instagrapi as fallback for environments without public URLs."""
        try:
            from instagrapi import Client
            cl = Client()
            cl.login(self.config.INSTAGRAM_USERNAME, self.config.INSTAGRAM_PASSWORD)
            media = cl.photo_upload(local_path, caption="")
            cl.media_delete(media.pk)  # placeholder upload — actual post happens through Graph API
            return ""  # instagrapi posting handled separately if Graph API unavailable
        except Exception as e:
            logger.error(f"instagrapi upload failed: {e}")
            return ""
