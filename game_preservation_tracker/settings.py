from __future__ import annotations

BOT_NAME = "game_preservation_tracker"

SPIDER_MODULES = ["game_preservation_tracker.spiders"]
NEWSPIDER_MODULE = "game_preservation_tracker.spiders"

ROBOTSTXT_OBEY = True
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 1.0
RANDOMIZE_DOWNLOAD_DELAY = True
DOWNLOAD_TIMEOUT = 30

COOKIES_ENABLED = False
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [429, 500, 502, 503, 504, 522, 524, 408]

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 15.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
AUTOTHROTTLE_DEBUG = False

FEED_EXPORT_ENCODING = "utf-8"
FEEDS = {
    "exports/%(name)s-%(time)s.jsonl": {
        "format": "jsonlines",
        "encoding": "utf-8",
        "store_empty": False,
        "indent": 0,
    }
}

DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.8",
}

LOG_LEVEL = "INFO"
