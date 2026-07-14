from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from urllib.parse import urlencode

import scrapy

from game_preservation_tracker.items import GameRecord


def compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def build_api_url(params: dict[str, str]) -> str:
    base_url = "https://en.wikipedia.org/w/api.php"
    query = urlencode(params)
    return f"{base_url}?{query}"


class WikipediaSpider(scrapy.Spider):
    name = "wikipedia_spider"
    allowed_domains = ["en.wikipedia.org"]
    start_category = "Category:Online games by year of shutdown"

    def start_requests(self):
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": self.start_category,
            "cmtype": "subcat|page",
            "cmlimit": "max",
            "format": "json",
        }
        yield scrapy.Request(build_api_url(params), callback=self.parse_category, meta={"category": self.start_category})

    def parse_category(self, response):
        payload = json.loads(response.text)
        members = payload.get("query", {}).get("categorymembers", [])

        for member in members:
            title = member.get("title", "")
            namespace = member.get("ns")
            if namespace == 14 and title:
                params = {
                    "action": "query",
                    "list": "categorymembers",
                    "cmtitle": title,
                    "cmtype": "subcat|page",
                    "cmlimit": "max",
                    "format": "json",
                }
                yield scrapy.Request(build_api_url(params), callback=self.parse_category, meta={"category": title})
            elif namespace == 0 and title:
                params = {
                    "action": "query",
                    "titles": title,
                    "prop": "extracts|pageprops|info",
                    "explaintext": "1",
                    "exintro": "1",
                    "inprop": "url",
                    "format": "json",
                    "formatversion": "2",
                }
                yield scrapy.Request(build_api_url(params), callback=self.parse_page, meta={"category": response.meta.get("category", "")})

        continuation = payload.get("continue", {})
        if continuation:
            params = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": response.meta.get("category", self.start_category),
                "cmtype": "subcat|page",
                "cmlimit": "max",
                "format": "json",
            }
            params.update({key: str(value) for key, value in continuation.items()})
            yield scrapy.Request(build_api_url(params), callback=self.parse_category, meta=response.meta)

    def parse_page(self, response):
        payload = json.loads(response.text)
        for page in payload.get("query", {}).get("pages", []):
            title = page.get("title") or ""
            extract = compact_text(page.get("extract") or "")
            wikidata_id = page.get("pageprops", {}).get("wikibase_item")
            page_url = page.get("fullurl")

            shutdown_year = None
            for candidate in [title, extract]:
                match = re.search(r"(19\d{2}|20\d{2})", candidate)
                if match:
                    shutdown_year = match.group(1)
                    break

            ownership_model = None
            lower_extract = extract.lower()
            if "free-to-play" in lower_extract:
                ownership_model = "free-to-play"
            elif "subscription" in lower_extract:
                ownership_model = "subscription"
            elif "buy-to-play" in lower_extract or "premium" in lower_extract:
                ownership_model = "buy-to-play"
            elif "always-online" in lower_extract or "service" in lower_extract:
                ownership_model = "service-based access"

            reason = None
            for pattern in [r"shut down because ([^.]+)", r"closed because ([^.]+)", r"ended service due to ([^.]+)"]:
                match = re.search(pattern, extract, flags=re.IGNORECASE)
                if match:
                    reason = match.group(1).strip()
                    break

            item = GameRecord()
            item["title"] = title
            item["wikidata_id"] = wikidata_id
            item["developer"] = None
            item["publisher"] = None
            item["release_date"] = None
            item["platforms"] = []
            item["genres"] = []
            item["delist_date"] = None
            item["shutdown_date"] = shutdown_year
            item["reason"] = reason or extract[:250] or None
            item["playable_post_shutdown"] = bool(re.search(r"offline|single-player|archived|fan server", extract, flags=re.IGNORECASE))
            item["ownership_model"] = ownership_model
            item["playstation_platform"] = []
            item["event_type"] = "shutdown"
            item["ps_plus_tier"] = None
            item["trophy_impact"] = None
            item["shovelware_purge"] = False
            item["source_urls"] = [page_url] if page_url else [f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"]
            item["source_quote"] = extract[:500]
            item["scraped_at"] = datetime.now(timezone.utc).isoformat()

            yield item
