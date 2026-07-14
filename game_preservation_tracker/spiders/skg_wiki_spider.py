from __future__ import annotations

import re
from datetime import datetime, timezone

import scrapy

from game_preservation_tracker.items import GameRecord


def compact_text(values: list[str]) -> str:
    return re.sub(r"\s+", " ", " ".join(values)).strip()


class SkgWikiSpider(scrapy.Spider):
    name = "skg_wiki_spider"
    allowed_domains = ["stopkillinggames.wiki.gg", "www.stopkillinggames.wiki.gg"]
    start_urls = ["https://stopkillinggames.wiki.gg/wiki/Dead_game_list"]

    def parse(self, response):
        for table in response.css("table"):
            headers = [compact_text(header.css("::text").getall()) for header in table.css("tr:first-child th")]
            if not headers:
                continue

            for row in table.css("tr")[1:]:
                cells = row.css("th, td")
                if not cells:
                    continue

                values = [compact_text(cell.css("::text").getall()) for cell in cells]
                row_data = {headers[index].lower(): values[index] for index in range(min(len(headers), len(values)))}
                title = row_data.get("title") or row_data.get("game") or (values[0] if values else None)
                if not title:
                    continue

                row_text = compact_text(row.css("::text").getall())
                item = GameRecord()
                item["title"] = title
                item["wikidata_id"] = None
                item["developer"] = row_data.get("developer")
                item["publisher"] = row_data.get("publisher")
                item["release_date"] = row_data.get("release date")
                item["platforms"] = [part.strip() for part in re.split(r"[;,/]", row_data.get("platform") or row_data.get("platforms") or "") if part.strip()]
                item["genres"] = [part.strip() for part in re.split(r"[;,/]", row_data.get("genre") or row_data.get("genres") or "") if part.strip()]
                item["delist_date"] = row_data.get("delisted") or row_data.get("delist date")
                item["shutdown_date"] = row_data.get("shutdown") or row_data.get("service ended") or row_data.get("status")
                item["reason"] = row_data.get("reason") or row_data.get("notes") or row_text
                item["playable_post_shutdown"] = bool(re.search(r"playable|offline|preserved", row_text, flags=re.IGNORECASE))
                item["ownership_model"] = "community preservation list"
                item["playstation_platform"] = [platform for platform in ["PS5", "PS4", "PS3", "PS Vita", "PSP"] if re.search(platform, row_text, flags=re.IGNORECASE)]
                item["event_type"] = "catalog_record"
                item["ps_plus_tier"] = None
                item["trophy_impact"] = None
                item["shovelware_purge"] = bool(re.search(r"purge|shovelware", row_text, flags=re.IGNORECASE))
                item["source_urls"] = [response.url]
                item["source_quote"] = row_text
                item["scraped_at"] = datetime.now(timezone.utc).isoformat()

                yield item
