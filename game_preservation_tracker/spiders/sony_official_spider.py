from __future__ import annotations

import re
from datetime import datetime, timezone

import scrapy

from game_preservation_tracker.items import GameRecord


def compact_text(values: list[str]) -> str:
    return re.sub(r"\s+", " ", " ".join(values)).strip()


class SonyOfficialSpider(scrapy.Spider):
    name = "sony_official_spider"
    allowed_domains = ["playstation.com", "blog.playstation.com"]
    start_urls = [
        "https://www.playstation.com/en-us/legal/gameservers/",
        "https://www.playstation.com/en-us/support/important-notice/",
        "https://blog.playstation.com/2021/04/19/update-on-playstation-store-for-ps3-and-ps-vita/",
    ]

    def parse(self, response):
        title = response.css("h1::text, meta[property='og:title']::attr(content), title::text").get()
        title = (title or response.url).strip()
        body_text = compact_text(response.css("body *::text").getall())

        date_match = re.search(r"(19\d{2}|20\d{2})[-/](\d{2})[-/](\d{2})", body_text)
        shutdown_date = date_match.group(0) if date_match else None
        if not shutdown_date:
            date_match = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+(19\d{2}|20\d{2})", body_text)
            shutdown_date = date_match.group(0) if date_match else None

        if "gameservers" in response.url.lower():
            event_type = "server_shutdown"
        elif "important-notice" in response.url.lower() or "store" in response.url.lower():
            event_type = "store_closure"
        else:
            event_type = "official_notice"

        reason = None
        for pattern in [r"because ([^.]+)", r"due to ([^.]+)", r"closing the ([^.]+)"]:
            match = re.search(pattern, body_text, flags=re.IGNORECASE)
            if match:
                reason = match.group(1).strip()
                break

        item = GameRecord()
        item["title"] = title
        item["wikidata_id"] = None
        item["developer"] = None
        item["publisher"] = "Sony Interactive Entertainment"
        item["release_date"] = None
        item["platforms"] = []
        item["genres"] = []
        item["delist_date"] = None
        item["shutdown_date"] = shutdown_date
        item["reason"] = reason or body_text[:300]
        item["playable_post_shutdown"] = bool(re.search(r"offline|single-player|archived", body_text, flags=re.IGNORECASE))
        item["ownership_model"] = "platform-controlled digital access"
        item["playstation_platform"] = [platform for platform in ["PS5", "PS4", "PS3", "PS Vita", "PSP"] if re.search(platform, body_text, flags=re.IGNORECASE)]
        item["event_type"] = event_type
        item["ps_plus_tier"] = None
        item["trophy_impact"] = None
        item["shovelware_purge"] = False
        item["source_urls"] = [response.url]
        item["source_quote"] = body_text[:500]
        item["scraped_at"] = datetime.now(timezone.utc).isoformat()

        yield item
