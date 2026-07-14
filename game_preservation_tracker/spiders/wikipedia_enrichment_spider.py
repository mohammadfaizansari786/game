from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import scrapy

from game_preservation_tracker.items import GameRecord


def build_api_url(params: dict[str, str]) -> str:
    return f"https://en.wikipedia.org/w/api.php?{urlencode(params)}"


def compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


class WikipediaEnrichmentSpider(scrapy.Spider):
    name = "wikipedia_enrichment_spider"
    allowed_domains = ["en.wikipedia.org"]

    def __init__(self, input_file: str = "merged.jsonl", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.input_file = Path(input_file)
        self.seed_records: list[dict] = []
        if self.input_file.exists():
            with self.input_file.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    self.seed_records.append(json.loads(line))

    def start_requests(self):
        for seed in self.seed_records:
            title = seed.get("title")
            if not title:
                continue
            params = {
                "action": "query",
                "list": "search",
                "srsearch": title,
                "srlimit": "1",
                "format": "json",
            }
            yield scrapy.Request(build_api_url(params), callback=self.parse_search, meta={"seed": seed})

    def parse_search(self, response):
        payload = json.loads(response.text)
        hits = payload.get("query", {}).get("search", [])
        seed = response.meta["seed"]

        if not hits:
            yield from self._emit_enriched(seed, None, None)
            return

        hit = hits[0]
        pageid = hit.get("pageid")
        title = hit.get("title") or seed.get("title")
        params = {
            "action": "query",
            "pageids": str(pageid),
            "prop": "extracts|pageprops|info",
            "explaintext": "1",
            "exintro": "1",
            "inprop": "url",
            "format": "json",
            "formatversion": "2",
        }
        yield scrapy.Request(build_api_url(params), callback=self.parse_extract, meta={"seed": seed, "title": title})

    def parse_extract(self, response):
        payload = json.loads(response.text)
        seed = response.meta["seed"]
        pages = payload.get("query", {}).get("pages", [])
        if not pages:
            yield from self._emit_enriched(seed, None, None)
            return

        page = pages[0]
        extract = compact_text(page.get("extract") or "")
        title = page.get("title") or response.meta.get("title") or seed.get("title")

        developer = self._extract_pattern([
            r"developer(?:s)?\s*[:\-]\s*([^\.\n\r]+)",
            r"developed by\s+([^\.\n\r]+)",
        ], extract)
        publisher = self._extract_pattern([
            r"publisher(?:s)?\s*[:\-]\s*([^\.\n\r]+)",
            r"published by\s+([^\.\n\r]+)",
        ], extract)
        release_date = self._extract_pattern([
            r"released\s+in\s+(19\d{2}|20\d{2})",
            r"released on\s+([^\.\n\r]+)",
            r"launched\s+in\s+(19\d{2}|20\d{2})",
        ], extract)
        genres = self._extract_pattern([
            r"genre(?:s)?\s*[:\-]\s*([^\.\n\r]+)",
            r"is a\s+([^\.\n\r]+?)\s+video game",
        ], extract)

        yield from self._emit_enriched(
            seed,
            title,
            {
                "developer": developer,
                "publisher": publisher,
                "release_date": release_date,
                "genres": [part.strip() for part in re.split(r"[;,/]| and ", genres) if part.strip()] if genres else [],
                "source_urls": [page.get("fullurl") or f"https://en.wikipedia.org/wiki/{str(title).replace(' ', '_')}"],
                "source_quote": extract[:500],
            },
        )

    def _extract_pattern(self, patterns: list[str], text: str) -> str | None:
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _emit_enriched(self, seed: dict, title: str | None, extracted: dict | None):
        merged = dict(seed)
        if title:
            merged["title"] = title

        extracted = extracted or {}
        for field in ["developer", "publisher", "release_date", "source_quote"]:
            value = extracted.get(field)
            if value and not merged.get(field):
                merged[field] = value

        if extracted.get("genres") and not merged.get("genres"):
            merged["genres"] = extracted["genres"]

        source_urls = []
        for url in merged.get("source_urls", []) or []:
            if url not in source_urls:
                source_urls.append(url)
        for url in extracted.get("source_urls", []) or []:
            if url not in source_urls:
                source_urls.append(url)
        if source_urls:
            merged["source_urls"] = source_urls

        merged["scraped_at"] = datetime.now(timezone.utc).isoformat()
        merged.setdefault("wikidata_id", None)
        merged.setdefault("platforms", [])
        merged.setdefault("genres", [])
        merged.setdefault("delist_date", None)
        merged.setdefault("shutdown_date", None)
        merged.setdefault("reason", None)
        merged.setdefault("playable_post_shutdown", None)
        merged.setdefault("ownership_model", None)
        merged.setdefault("playstation_platform", [])
        merged.setdefault("event_type", "wikipedia_enrichment")
        merged.setdefault("ps_plus_tier", None)
        merged.setdefault("trophy_impact", None)
        merged.setdefault("shovelware_purge", None)
        merged.setdefault("source_quote", extracted.get("source_quote") or merged.get("source_quote") or "")

        item = GameRecord()
        for key, value in merged.items():
            item[key] = value
        yield item
