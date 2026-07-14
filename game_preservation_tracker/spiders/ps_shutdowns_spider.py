from __future__ import annotations

import re
from datetime import datetime, timezone

import scrapy

from game_preservation_tracker.items import GameRecord


def compact_text(values: list[str]) -> str:
    return re.sub(r"\s+", " ", " ".join(values)).strip()


class PsShutdownsSpider(scrapy.Spider):
    name = "ps_shutdowns_spider"
    allowed_domains = ["ps-shutdowns.com", "www.ps-shutdowns.com"]
    start_urls = ["https://ps-shutdowns.com/all-games"]

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
                title = row_data.get("game") or row_data.get("title") or (values[0] if values else None)
                if not title:
                    continue

                row_text = compact_text(row.css("::text").getall())
                platform_text = row_data.get("platform") or row_data.get("platforms") or row_data.get("console") or ""
                playstation_platform = []
                for platform in ["PS5", "PS4", "PS3", "PS Vita", "PSP"]:
                    if re.search(rf"\b{re.escape(platform)}\b", platform_text + " " + row_text, flags=re.IGNORECASE):
                        playstation_platform.append(platform)

                item = GameRecord()
                item["title"] = title
                item["wikidata_id"] = None
                item["developer"] = row_data.get("developer")
                item["publisher"] = row_data.get("publisher")
                item["release_date"] = row_data.get("release") or row_data.get("release date")
                item["platforms"] = [part.strip() for part in re.split(r"[;,/]", platform_text) if part.strip()]
                item["genres"] = []
                item["delist_date"] = row_data.get("delisted") or row_data.get("delist date")
                item["shutdown_date"] = row_data.get("shutdown") or row_data.get("shutdown date") or row_data.get("server shutdown")
                item["reason"] = row_data.get("reason") or row_data.get("notes") or row_text
                item["playable_post_shutdown"] = bool(re.search(r"playable|offline|archived", row_text, flags=re.IGNORECASE))
                item["ownership_model"] = "service-based access" if re.search(r"service|online-only|license", row_text, flags=re.IGNORECASE) else None
                item["playstation_platform"] = playstation_platform
                item["event_type"] = "server_shutdown"
                item["ps_plus_tier"] = row_data.get("ps plus tier") or row_data.get("tier")
                item["trophy_impact"] = row_data.get("trophy impact") or row_data.get("trophies") or ("yes" if re.search(r"trophy", row_text, flags=re.IGNORECASE) else None)
                item["shovelware_purge"] = bool(re.search(r"shovelware|purge", row_text, flags=re.IGNORECASE))
                item["source_urls"] = [response.url]
                item["source_quote"] = row_text
                item["scraped_at"] = datetime.now(timezone.utc).isoformat()

                yield item
