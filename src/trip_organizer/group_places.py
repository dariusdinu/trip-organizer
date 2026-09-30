"""Group the Takeout CSV export into city-based files.

Takeout's saved-list CSVs contain names and URLs but usually no address or
coordinates. This script therefore uses the originating list filename as the
location signal and keeps mixed/default lists in ``unknown.csv``.
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path


CITY_ALIASES = {
    "athens": "Athens",
    "barcelona": "Barcelona",
    "bari": "Bari",
    "bratislava": "Bratislava",
    "krakow": "Krakow",
    "milan": "Milan",
    "milano": "Milan",
    "paris": "Paris",
    "rome": "Rome",
    "stockholm": "Stockholm",
    "venice": "Venice",
}

CATEGORY_ALIASES = {
    "accommodation": "Accommodation",
    "attraction": "Attractions",
    "attractions": "Attractions",
    "bakery": "Bakeries",
    "bakeries": "Bakeries",
    "bar": "Bars",
    "bars": "Bars",
    "beach": "Beaches",
    "beaches": "Beaches",
    "bridge": "Bridges",
    "bridges": "Bridges",
    "brunch": "Brunch",
    "cafe": "Coffee Shops",
    "cafes": "Coffee Shops",
    "coffee": "Coffee Shops",
    "coffee bakery": "Coffee Shops",
    "coffee breakfast": "Coffee Shops",
    "coffee shop": "Coffee Shops",
    "dessert": "Desserts",
    "desserts": "Desserts",
    "dessert shop": "Desserts",
    "drinks": "Drinks",
    "fragrance": "Perfume & Fragrance",
    "fragrance store": "Perfume & Fragrance",
    "fragrance stores": "Perfume & Fragrance",
    "gelateria": "Ice Cream",
    "gelaterias": "Ice Cream",
    "images": "Images",
    "perfume shop": "Perfume & Fragrance",
    "perfume shops": "Perfume & Fragrance",
    "perfume store": "Perfume & Fragrance",
    "perfume stores": "Perfume & Fragrance",
    "photogenic": "Photo Spots",
    "photography": "Photo Spots",
    "restaurant": "Restaurants",
    "restaurants": "Restaurants",
    "shopping": "Shopping",
    "souvenir": "Souvenirs",
    "souvenirs": "Souvenirs",
    "street food": "Street Food",
}


def detect_encoding(path: Path) -> str:
    with path.open("rb") as file:
        prefix = file.read(4)
    return "utf-16" if prefix.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"


def city_from_source(source_file: str) -> str:
    """Infer a city from a Takeout source filename, or return Unknown."""
    filename = Path(source_file).stem.lower()
    for alias, city in CITY_ALIASES.items():
        if re.search(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", filename):
            return city
    return "Unknown"


def category_from_source(source_file: str) -> str:
    """Infer a normalized category from the saved-list filename."""
    stem = Path(source_file).stem.lower()
    for alias in CITY_ALIASES:
        stem = re.sub(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", " ", stem)
    category_words = re.sub(r"[_-]+", " ", stem)
    category_words = " ".join(category_words.split())
    if category_words in {"images", "imagini"}:
        return "Images"
    if category_words in {"default list", "listă prestabilită", "vreau să merg aici"}:
        return "Uncategorized"
    return CATEGORY_ALIASES.get(category_words, "Other")


def read_places(path: Path) -> list[dict[str, str]]:
    with path.open(encoding=detect_encoding(path), newline="") as file:
        return list(csv.DictReader(file))


def safe_filename(city: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", city.lower()).strip("_") or "unknown"


def write_group(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Group Takeout places by city inferred from their saved-list names.")
    parser.add_argument("input_csv", help="CSV produced by google_takeout_parser.py")
    parser.add_argument("-o", "--output-dir", default="grouped_places")
    args = parser.parse_args()

    input_path = Path(args.input_csv)
    output_dir = Path(args.output_dir)
    rows = read_places(input_path)
    if not rows:
        parser.error("input CSV contains no places")

    fields = list(rows[0])
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        source_file = row.get("source_file", "")
        city = city_from_source(source_file)
        category = category_from_source(source_file)
        row["city"] = city
        row["category"] = category
        groups[city].append(row)
    for field in ("city", "category"):
        if field not in fields:
            fields.append(field)

    output_dir.mkdir(parents=True, exist_ok=True)
    for city, city_rows in sorted(groups.items()):
        write_group(output_dir / f"{safe_filename(city)}.csv", city_rows, fields)
        print(f"{city}: {len(city_rows)} places")
    print(f"Wrote {len(groups)} city files to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
