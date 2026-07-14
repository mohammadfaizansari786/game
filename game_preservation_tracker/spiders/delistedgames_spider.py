from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import urljoin

import scrapy

from game_preservation_tracker.items import GameRecord


def compact_text(values: list[str]) -> str:
    return re.sub(r"\s+", " ", " ".join(values)).strip()


def first_match(patterns: list[str], text: str) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


class DelistedGamesSpider(scrapy.Spider):
    name = "delistedgames_spider"
    allowed_domains = ["delistedgames.com", "www.delistedgames.com"]
    base_url = "https://delistedgames.com"
    index_paths = [
        "/all-delisted-steam-games",
        "/all-delisted-playstation-3-games",
        "/all-delisted-playstation-4-games",
        "/all-delisted-playstation-vita-games",
        "/all-delisted-playstation-5-games",
    ]

    def start_requests(self):
        for path in self.index_paths:
            yield scrapy.Request(urljoin(self.base_url, path), callback=self.parse_index, meta={"index_path": path})

    def parse_index(self, response):
        detail_links = set()
        for href in response.css("article a::attr(href), .entry-content a::attr(href), table a::attr(href), main a::attr(href)").getall():
            absolute_url = urljoin(response.url, href)
            if "delistedgames.com" not in absolute_url:
                continue
            if any(path in absolute_url for path in self.index_paths):
                continue
            detail_links.add(absolute_url)

        for detail_url in sorted(detail_links):
            yield scrapy.Request(detail_url, callback=self.parse_detail, meta={"source_index": response.meta.get("index_path", "")})

        for next_href in response.css("a[rel='next']::attr(href), .next a::attr(href)").getall():
            yield response.follow(next_href, callback=self.parse_index, meta=response.meta)

    def parse_detail(self, response):
        title = response.css("h1::text, meta[property='og:title']::attr(content)").get()
        title = (title or response.url.rstrip("/").split("/")[-1]).strip()
        text_chunks = response.css("article *::text, .entry-content *::text, main *::text, body *::text").getall()
        text = compact_text(text_chunks)

        publisher = first_match([
            r"Publisher\s*[:\-]\s*([^|\n\r]+)",
            r"published by\s+([^\.\n\r]+)",
        ], text)
        developer = first_match([
            r"Developer\s*[:\-]\s*([^|\n\r]+)",
            r"developed by\s+([^\.\n\r]+)",
        ], text)

        delist_date = first_match([
            r"delist(?:ed|ing)?[^\d]{0,60}(\w+\s+\d{1,2},\s+\d{4})",
            r"delist(?:ed|ing)?[^\d]{0,60}(\d{4}-\d{2}-\d{2})",
            r"delist(?:ed|ing)?[^\d]{0,60}(\d{4})",
        ], text)
        shutdown_date = first_match([
            r"shutdown[^\d]{0,60}(\w+\s+\d{1,2},\s+\d{4})",
            r"shutdown[^\d]{0,60}(\d{4}-\d{2}-\d{2})",
            r"shutdown[^\d]{0,60}(\d{4})",
        ], text)

        playstation_platform = []
        for platform in ["PS5", "PS4", "PS3", "PS Vita", "PSP"]:
            if re.search(rf"\b{re.escape(platform)}\b", text, flags=re.IGNORECASE):
                playstation_platform.append(platform)

        if not playstation_platform and "playstation" in response.url.lower():
            if "playstation-3" in response.url.lower():
                playstation_platform.append("PS3")
            if "playstation-4" in response.url.lower():
                playstation_platform.append("PS4")
            if "playstation-vita" in response.url.lower():
                playstation_platform.append("PS Vita")
            if "playstation-5" in response.url.lower():
                playstation_platform.append("PS5")

        reason = first_match([
            r"reason\s*[:\-]\s*([^\.\n\r]+)",
            r"because\s+([^\.\n\r]+)",
            r"due to\s+([^\.\n\r]+)",
            r"license[^\.\n\r]+",
        ], text)

        playable_post_shutdown = bool(re.search(r"playable (?:offline|after shutdown)|single-player|offline mode", text, flags=re.IGNORECASE))

        ownership_model = None
        if re.search(r"license|licensed access|license-based", text, flags=re.IGNORECASE):
            ownership_model = "license-based digital access"
        elif re.search(r"buy to own|ownership", text, flags=re.IGNORECASE):
            ownership_model = "buy-to-own"

        source_quote = compact_text(response.css("article p::text, .entry-content p::text, main p::text").getall()[:3])
        if not source_quote:
            source_quote = text[:350]

        item = GameRecord()
        item["title"] = title
        item["developer"] = developer
        item["publisher"] = publisher
        item["release_date"] = None
        item["platforms"] = []
        item["genres"] = []
        item["delist_date"] = delist_date
        item["shutdown_date"] = shutdown_date
        item["reason"] = reason
        item["playable_post_shutdown"] = playable_post_shutdown
        item["ownership_model"] = ownership_model
        item["playstation_platform"] = playstation_platform
        item["event_type"] = "delisting" if delist_date and not shutdown_date else "server_shutdown" if shutdown_date else "catalog_record"
        item["ps_plus_tier"] = None
        item["trophy_impact"] = None
        item["shovelware_purge"] = bool(re.search(r"welding byte|thigames|shovelware|publisher purge", text, flags=re.IGNORECASE))
        item["source_urls"] = [response.url]
        item["source_quote"] = source_quote
        item["scraped_at"] = datetime.now(timezone.utc).isoformat()

        yield item
