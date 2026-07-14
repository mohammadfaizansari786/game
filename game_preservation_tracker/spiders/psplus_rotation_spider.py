from __future__ import annotations

import re
from datetime import datetime, timezone

import scrapy

from game_preservation_tracker.items import GameRecord


def compact_text(values: list[str]) -> str:
    return re.sub(r"\s+", " ", " ".join(values)).strip()


class PsPlusRotationSpider(scrapy.Spider):
    name = "psplus_rotation_spider"
    allowed_domains = ["playstation.com"]
    start_urls = ["https://www.playstation.com/en-us/ps-plus/whats-new/"]

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse, meta={"playwright": True})

    def parse(self, response):
        page_text = compact_text(response.css("body *::text").getall())
        if "last chance to play" not in page_text.lower():
            page_text = compact_text(response.xpath("//text()[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'last chance to play')]/parent::*/following::text()").getall())

        seen_titles: set[str] = set()
        for link in response.css("a[href]"):
            link_text = compact_text(link.css("::text").getall())
            href = link.attrib.get("href", "")
            if not link_text:
                continue
            if len(link_text) < 3:
                continue
            if "last chance to play" in link_text.lower():
                continue
            if link_text.lower() in seen_titles:
                continue
            if re.search(r"\d{1,2}/\d{1,2}/\d{2,4}|\d{4}", link_text) or "last chance" in page_text.lower():
                seen_titles.add(link_text.lower())

                item = GameRecord()
                item["title"] = link_text
                item["wikidata_id"] = None
                item["developer"] = None
                item["publisher"] = None
                item["release_date"] = None
                item["platforms"] = []
                item["genres"] = []
                item["delist_date"] = None
                item["shutdown_date"] = None
                item["reason"] = "Last Chance to Play rotation"
                item["playable_post_shutdown"] = False
                item["ownership_model"] = "subscription rotation"
                item["playstation_platform"] = []
                item["event_type"] = "ps_plus_rotation"
                item["ps_plus_tier"] = None
                item["trophy_impact"] = None
                item["shovelware_purge"] = False
                item["source_urls"] = [response.url, href] if href else [response.url]
                item["source_quote"] = compact_text(link.css("::text").getall())
                item["scraped_at"] = datetime.now(timezone.utc).isoformat()

                yield item
