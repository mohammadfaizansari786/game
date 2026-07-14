from __future__ import annotations

import argparse

import matplotlib.pyplot as plt
import pandas as pd


def split_values(value) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value)
    return [part.strip() for part in text.replace("/", ";").split(";") if part.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze shutdown trends from enriched JSONL data.")
    parser.add_argument("input_file", nargs="?", default="enriched.jsonl", help="Input JSONL file")
    parser.add_argument("--chart", default="shutdowns_by_year.png", help="Output chart path")
    args = parser.parse_args()

    dataframe = pd.read_json(args.input_file, lines=True)
    if dataframe.empty:
        print("No records available for analysis.")
        return

    shutdown_dates = pd.to_datetime(dataframe.get("shutdown_date"), errors="coerce", utc=True)
    dataframe["shutdown_year"] = shutdown_dates.dt.year
    year_counts = dataframe.dropna(subset=["shutdown_year"]).groupby("shutdown_year").size().sort_index()

    if not year_counts.empty:
        plt.figure(figsize=(12, 6))
        year_counts.plot(kind="bar", color="#1f77b4")
        plt.title("Video Game Shutdowns by Year")
        plt.xlabel("Year")
        plt.ylabel("Shutdown Count")
        plt.tight_layout()
        plt.savefig(args.chart, dpi=200)
        plt.close()
        print(f"Saved chart to {args.chart}")

    publishers = dataframe["publisher"].dropna().astype(str)
    top_publishers = publishers.value_counts().head(10)
    if not top_publishers.empty:
        print("Top publishers killing games:")
        for publisher, count in top_publishers.items():
            print(f"- {publisher}: {count}")

    platform_values = []
    if "playstation_platform" in dataframe.columns:
        for value in dataframe["playstation_platform"].dropna():
            platform_values.extend(split_values(value))
    platform_counts = pd.Series(platform_values).value_counts()
    if not platform_counts.empty:
        print("PlayStation platform breakdown:")
        for platform, count in platform_counts.items():
            print(f"- {platform}: {count}")


if __name__ == "__main__":
    main()
