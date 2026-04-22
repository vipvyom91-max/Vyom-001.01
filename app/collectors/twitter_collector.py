import logging
from datetime import datetime, timezone

from app.collectors.base import BaseCollector, retry

logger = logging.getLogger(__name__)

PCB_QUERY_TERMS = "NEET OR PCB OR Class12 OR physics OR chemistry OR biology OR DPP OR lecture"


class TwitterCollector(BaseCollector):
    source_type = "twitter"

    def collect(self) -> list[dict]:
        if not self.config.TWITTER_BEARER_TOKEN:
            logger.warning("Twitter Bearer Token not configured — skipping")
            return []
        try:
            import tweepy
        except ImportError:
            logger.error("tweepy not installed")
            return []

        client = tweepy.Client(bearer_token=self.config.TWITTER_BEARER_TOKEN, wait_on_rate_limit=True)
        return self._fetch_tweets(client)

    @retry(max_attempts=3, base_delay=10)
    def _fetch_tweets(self, client) -> list[dict]:
        handle = self.source.identifier.lstrip("@")
        query = f"from:{handle} ({PCB_QUERY_TERMS}) -is:retweet lang:en"

        since = self.source.last_checked_at
        if since and since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)

        kwargs = {
            "query": query,
            "max_results": 10,
            "tweet_fields": ["created_at", "author_id", "entities", "attachments"],
            "expansions": ["attachments.media_keys"],
            "media_fields": ["url", "preview_image_url", "type"],
        }
        if since:
            kwargs["start_time"] = since

        try:
            response = client.search_recent_tweets(**kwargs)
        except Exception as e:
            # Broader query fallback if refined query returns nothing
            logger.warning(f"Refined query failed ({e}), trying broad query")
            kwargs["query"] = f"from:{handle} -is:retweet"
            response = client.search_recent_tweets(**kwargs)

        if not response or not response.data:
            return []

        # Build media URL map
        media_map = {}
        if response.includes and response.includes.get("media"):
            for m in response.includes["media"]:
                media_map[m.media_key] = m.url or m.preview_image_url or ""

        results = []
        for tweet in response.data:
            media_url = ""
            if tweet.attachments and tweet.attachments.get("media_keys"):
                key = tweet.attachments["media_keys"][0]
                media_url = media_map.get(key, "")
            results.append(self.normalize({
                "external_id": str(tweet.id),
                "title": tweet.text[:120],
                "body": tweet.text,
                "url": f"https://twitter.com/{handle}/status/{tweet.id}",
                "media_url": media_url,
                "published_at": tweet.created_at,
            }))

        return results

    def normalize(self, raw: dict) -> dict:
        title = raw.get("title", "")
        body = raw.get("body", "")
        return {
            "external_id": raw.get("external_id"),
            "title": title[:500],
            "body": body,
            "url": raw.get("url", ""),
            "media_url": raw.get("media_url", ""),
            "published_at": raw.get("published_at"),
            "content_type": self.classify_content_type(title, body),
            "category": self.classify_category(title, body),
        }
