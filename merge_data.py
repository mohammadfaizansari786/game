from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd


SOURCE_PRIORITY = ["sony_official", "delistedgames", "ps_shutdowns", "wikipedia", "skg_wiki"]
DOMAIN_PRIORITY = {
    "playstation.com": "sony_official",
    "blog.playstation.com": "sony_official",
    "delistedgames.com": "delistedgames",
    "ps-shutdowns.com": "ps_shutdowns",
    "wikipedia.org": "wikipedia",
    "stopkillinggames.wiki.gg": "skg_wiki",
}


def normalize_title(title: str | None) -> str:
    text = unicodedata.normalize("NFKD", title or "")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"\[[^\]]+\]", "", text)
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text).lower()
    return re.sub(r"\s+", " ", text).strip()


def infer_source(record: dict) -> str:
    for url in record.get("source_urls", []) or []:
        for domain, source in DOMAIN_PRIORITY.items():
            if domain in url:
                return source
    return "unknown"


def source_rank(record: dict) -> int:
    source = infer_source(record)
    try:
        return SOURCE_PRIORITY.index(source)
    except ValueError:
        return len(SOURCE_PRIORITY)


def read_jsonl_files(input_dir: Path) -> pd.DataFrame:
    rows: list[dict] = []
    for path in sorted(input_dir.glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def merge_group(group: pd.DataFrame) -> dict:
    ordered = group.sort_values(by="_source_rank", ascending=True)
    merged: dict = {}

    def assign(field: str, value):
        if value is None:
            return
        if isinstance(value, float) and pd.isna(value):
            return
        if isinstance(value, list) and not value:
            return
        if isinstance(value, str) and not value.strip():
            return
        if field not in merged or merged[field] in (None, "", [], {}):
            merged[field] = value

    for _, row in ordered.iterrows():
        record = row.to_dict()
        for field, value in record.items():
            if field in {"_source_rank", "_normalized_title"}:
                continue
            if field == "source_urls":
                urls = merged.get("source_urls", []) or []
                for url in value or []:
                    if url not in urls:
                        urls.append(url)
                merged["source_urls"] = urls
                continue
            if field in {"genres", "platforms", "playstation_platform"}:
                existing = merged.get(field, []) or []
                incoming = value or []
                if isinstance(incoming, str):
                    incoming = [part.strip() for part in re.split(r"[;,/]", incoming) if part.strip()]
                for item in incoming:
                    if item not in existing:
                        existing.append(item)
                merged[field] = existing
                continue
            assign(field, value)

    merged["title"] = merged.get("title") or ordered.iloc[0].get("title")
    return merged


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge JSONL crawls into a single prioritized dataset.")
    parser.add_argument("input_dir", nargs="?", default=".", help="Directory containing source JSONL files")
    parser.add_argument("--output", default="merged.jsonl", help="Output JSONL file")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    dataframe = read_jsonl_files(input_dir)
    if dataframe.empty:
        Path(args.output).write_text("", encoding="utf-8")
        return

    dataframe["_normalized_title"] = dataframe["title"].map(normalize_title)
    dataframe["_source_rank"] = dataframe.apply(source_rank, axis=1)

    merged_rows = []
    for _, group in dataframe.groupby("_normalized_title", dropna=False):
        merged_rows.append(merge_group(group))

    output_frame = pd.DataFrame(merged_rows).sort_values(by="title", kind="stable")
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_frame.to_json(output_path, orient="records", lines=True, force_ascii=False)


if __name__ == "__main__":
    main()
