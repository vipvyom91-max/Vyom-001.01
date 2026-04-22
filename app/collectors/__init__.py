from app.collectors.pw_website import PWWebsiteCollector
from app.collectors.youtube import YouTubeCollector
from app.collectors.telegram_collector import TelegramCollector
from app.collectors.twitter_collector import TwitterCollector
from app.collectors.rss import RSSCollector

COLLECTOR_MAP = {
    "youtube": YouTubeCollector,
    "telegram": TelegramCollector,
    "twitter": TwitterCollector,
    "website": PWWebsiteCollector,
    "rss": RSSCollector,
}


def get_collector_for_source(source, config):
    cls = COLLECTOR_MAP.get(source.source_type)
    if not cls:
        raise ValueError(f"Unknown source type: {source.source_type}")
    return cls(source, config)
