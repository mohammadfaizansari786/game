from __future__ import annotations

import scrapy


class GameRecord(scrapy.Item):
    title = scrapy.Field()
    wikidata_id = scrapy.Field()

    developer = scrapy.Field()
    publisher = scrapy.Field()
    release_date = scrapy.Field()
    platforms = scrapy.Field()
    genres = scrapy.Field()

    delist_date = scrapy.Field()
    shutdown_date = scrapy.Field()
    reason = scrapy.Field()
    playable_post_shutdown = scrapy.Field()
    ownership_model = scrapy.Field()

    playstation_platform = scrapy.Field()
    event_type = scrapy.Field()
    ps_plus_tier = scrapy.Field()
    trophy_impact = scrapy.Field()
    shovelware_purge = scrapy.Field()

    source_urls = scrapy.Field()
    source_quote = scrapy.Field()
    scraped_at = scrapy.Field()
