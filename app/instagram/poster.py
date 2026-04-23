import logging
import os
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com/v18.0"
_INSTA_SESSION_FILE = Path("ig_session.json")


class InstagramPoster:
    """
    Posts to Instagram.
    - If INSTAGRAM_ACCESS_TOKEN + INSTAGRAM_BUSINESS_ACCOUNT_ID + PUBLIC_BASE_URL are set,
      uses the official Graph API.
    - Otherwise falls back to instagrapi (username + password, works on Termux).
    """

    def __init__(self, config):
        self.config = config
        self.token = getattr(config, "INSTAGRAM_ACCESS_TOKEN", "")
        self.ig_id = getattr(config, "INSTAGRAM_BUSINESS_ACCOUNT_ID", "")
        self.public_base_url = getattr(config, "PUBLIC_BASE_URL", "")
        self.username = getattr(config, "INSTAGRAM_USERNAME", "")
        self.password = getattr(config, "INSTAGRAM_PASSWORD", "")
        self._cl = None  # instagrapi Client (lazy)

    # ── Public API ────────────────────────────────────────────────────────────

    def post_feed_image(self, post) -> str:
        """Upload a single image to Instagram feed. Returns IG post ID."""
        caption = post.full_caption
        local_path = self._local_image_path(post.image_path)

        if self._use_graph_api():
            image_url = self._public_image_url(post.image_path)
            if not image_url:
                raise ValueError("PUBLIC_BASE_URL not set — cannot use Graph API without public image URL")
            container_id = self._graph_create_container(image_url, caption)
            return self._graph_publish(container_id)

        # instagrapi path (works on local Termux, no public URL needed)
        if not local_path or not local_path.exists():
            raise ValueError(f"Image file not found: {local_path}")
        cl = self._insta_client()
        media = cl.photo_upload(str(local_path), caption=caption)
        logger.info(f"Posted via instagrapi: {media.pk}")
        return str(media.pk)

    def post_story(self, post) -> str:
        caption = post.full_caption
        local_path = self._local_image_path(post.image_path)

        if self._use_graph_api():
            image_url = self._public_image_url(post.image_path)
            if not image_url:
                raise ValueError("PUBLIC_BASE_URL not set")
            container_id = self._graph_create_container(image_url, "", media_type="STORIES")
            return self._graph_publish(container_id)

        if not local_path or not local_path.exists():
            raise ValueError(f"Image file not found: {local_path}")
        cl = self._insta_client()
        media = cl.photo_upload_to_story(str(local_path))
        return str(media.pk)

    def post_carousel(self, posts: list, caption: str) -> str:
        if self._use_graph_api():
            child_ids = []
            for p in posts:
                img_url = self._public_image_url(p.image_path)
                if img_url:
                    r = requests.post(
                        f"{GRAPH_BASE}/{self.ig_id}/media",
                        params={"image_url": img_url, "is_carousel_item": "true",
                                "access_token": self.token},
                        timeout=30,
                    )
                    r.raise_for_status()
                    child_ids.append(r.json()["id"])
            if not child_ids:
                raise ValueError("No valid images for carousel")
            r = requests.post(
                f"{GRAPH_BASE}/{self.ig_id}/media",
                params={"media_type": "CAROUSEL", "children": ",".join(child_ids),
                        "caption": caption, "access_token": self.token},
                timeout=30,
            )
            r.raise_for_status()
            return self._graph_publish(r.json()["id"])

        paths = []
        for p in posts:
            lp = self._local_image_path(p.image_path)
            if lp and lp.exists():
                paths.append(str(lp))
        if not paths:
            raise ValueError("No valid local images for carousel")
        cl = self._insta_client()
        media = cl.album_upload(paths, caption=caption)
        return str(media.pk)

    def verify_connection(self) -> dict:
        """Test credentials — returns account info dict."""
        if self._use_graph_api():
            if not self.token or not self.ig_id:
                return {"ok": False, "error": "Missing Graph API credentials"}
            try:
                r = requests.get(
                    f"{GRAPH_BASE}/{self.ig_id}",
                    params={"fields": "id,username,followers_count",
                            "access_token": self.token},
                    timeout=10,
                )
                r.raise_for_status()
                return {"ok": True, "method": "graph_api", **r.json()}
            except Exception as e:
                return {"ok": False, "error": str(e)}

        if not self.username or not self.password:
            return {"ok": False, "error": "INSTAGRAM_USERNAME/PASSWORD not set"}
        try:
            cl = self._insta_client()
            info = cl.account_info()
            return {"ok": True, "method": "instagrapi",
                    "username": info.username, "followers": info.follower_count}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _use_graph_api(self) -> bool:
        return bool(self.token and self.ig_id)

    def _public_image_url(self, image_path: str) -> str:
        if not image_path:
            return ""
        if image_path.startswith("http"):
            return image_path
        if self.public_base_url:
            return f"{self.public_base_url.rstrip('/')}/static/{image_path}"
        return ""

    def _local_image_path(self, image_path: str) -> Path | None:
        if not image_path:
            return None
        base = Path(__file__).parent.parent / "dashboard" / "static"
        return base / image_path

    def _insta_client(self):
        if self._cl is not None:
            return self._cl
        try:
            from instagrapi import Client
        except ImportError:
            raise RuntimeError("instagrapi not installed — run: pip install instagrapi")
        cl = Client()
        cl.delay_range = [1, 3]
        if _INSTA_SESSION_FILE.exists():
            try:
                cl.load_settings(str(_INSTA_SESSION_FILE))
                cl.login(self.username, self.password)
                logger.info("instagrapi: logged in with saved session")
            except Exception:
                cl = Client()
                cl.delay_range = [1, 3]
                cl.login(self.username, self.password)
                cl.dump_settings(str(_INSTA_SESSION_FILE))
                logger.info("instagrapi: new login, session saved")
        else:
            cl.login(self.username, self.password)
            cl.dump_settings(str(_INSTA_SESSION_FILE))
            logger.info("instagrapi: logged in, session saved to ig_session.json")
        self._cl = cl
        return cl

    def _graph_create_container(self, image_url: str, caption: str,
                                 media_type: str = "") -> str:
        params = {"image_url": image_url, "caption": caption,
                  "access_token": self.token}
        if media_type:
            params["media_type"] = media_type
        r = requests.post(f"{GRAPH_BASE}/{self.ig_id}/media",
                          params=params, timeout=30)
        r.raise_for_status()
        return r.json()["id"]

    def _graph_publish(self, container_id: str) -> str:
        r = requests.post(
            f"{GRAPH_BASE}/{self.ig_id}/media_publish",
            params={"creation_id": container_id, "access_token": self.token},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["id"]
