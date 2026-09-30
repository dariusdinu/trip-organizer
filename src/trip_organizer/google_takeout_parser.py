"""Parse Google Takeout saved-place exports into JSON or CSV.

The input can be a Google Takeout ZIP file or an extracted Takeout directory.
The parser intentionally accepts several field names because Takeout exports
have used JSON, CSV, and KML formats over time.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree


@dataclass
class Place:
    name: str
    url: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    note: str | None = None
    source_file: str | None = None


def clean(value: Any) -> str | None:
    if value is None:
        return None
    value = " ".join(str(value).split())
    return value or None


def number(value: Any) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def first(record: dict[str, Any], *names: str) -> Any:
    lowered = {str(key).lower().replace(" ", "_"): value for key, value in record.items()}
    for name in names:
        value = lowered.get(name.lower().replace(" ", "_"))
        if value not in (None, ""):
            return value
    return None


def from_record(record: dict[str, Any], source_file: str) -> Place | None:
    properties = record.get("properties") if isinstance(record.get("properties"), dict) else {}
    location = properties.get("location") if isinstance(properties.get("location"), dict) else {}
    # Takeout saved places are GeoJSON features: the useful fields live under
    # properties.location while coordinates live under geometry.
    flattened = {**record, **properties, **location}
    geometry = record.get("geometry") or flattened.get("location") or {}
    coordinates = geometry.get("coordinates") if isinstance(geometry, dict) else None
    latitude = first(flattened, "latitude", "lat")
    longitude = first(flattened, "longitude", "lng", "lon")
    if isinstance(coordinates, (list, tuple)) and len(coordinates) >= 2:
        longitude = longitude if longitude is not None else coordinates[0]
        latitude = latitude if latitude is not None else coordinates[1]
    name = first(flattened, "title", "titlu", "name", "place_name", "label")
    url = first(
        flattened,
        "url",
        "adresa_url",
        "google_maps_url",
        "googlemapsurl",
        "maps_url",
        "link",
    )
    address = first(flattened, "address", "formatted_address")
    note = first(flattened, "note", "notă", "comment", "comentează", "description")
    if not name and not url and latitude is None and longitude is None:
        return None
    return Place(
        name=clean(name) or "Unnamed place",
        url=clean(url),
        address=clean(address),
        latitude=number(latitude),
        longitude=number(longitude),
        note=clean(note),
        source_file=source_file,
    )


def records_from_json(value: Any, source_file: str) -> Iterable[Place]:
    if isinstance(value, dict):
        place = from_record(value, source_file)
        if place:
            yield place
        else:
            for child in value.values():
                yield from records_from_json(child, source_file)
    elif isinstance(value, list):
        for child in value:
            yield from records_from_json(child, source_file)


def parse_csv(content: bytes, source_file: str) -> Iterable[Place]:
    text = content.decode("utf-8-sig", errors="replace")
    for row in csv.DictReader(io.StringIO(text)):
        place = from_record(row, source_file)
        if place:
            yield place


def parse_kml(content: bytes, source_file: str) -> Iterable[Place]:
    root = ElementTree.fromstring(content)
    for placemark in root.iter():
        if placemark.tag.rsplit("}", 1)[-1] != "Placemark":
            continue
        values: dict[str, Any] = {}
        for child in placemark.iter():
            tag = child.tag.rsplit("}", 1)[-1].lower()
            if tag in {"name", "description"} and child.text:
                values["name" if tag == "name" else "note"] = child.text
            if tag == "coordinates" and child.text:
                parts = child.text.strip().split(",")
                if len(parts) >= 2:
                    values["longitude"], values["latitude"] = parts[0], parts[1]
        place = from_record(values, source_file)
        if place:
            yield place


def parse_file(name: str, content: bytes) -> list[Place]:
    lower = name.lower()
    if lower.endswith(".json"):
        return list(records_from_json(json.loads(content.decode("utf-8-sig")), name))
    if lower.endswith(".csv"):
        return list(parse_csv(content, name))
    if lower.endswith(".kml"):
        return list(parse_kml(content, name))
    return []


def input_files(input_path: str) -> Iterable[tuple[str, bytes]]:
    path = Path(input_path)
    if path.is_file() and zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                if not info.is_dir():
                    yield info.filename, archive.read(info)
        return
    if path.is_dir():
        for file in path.rglob("*"):
            if file.is_file():
                yield str(file.relative_to(path)), file.read_bytes()
        return
    raise FileNotFoundError(f"Takeout ZIP or directory not found: {input_path}")


def extract(input_path: str, all_files: bool = False) -> list[Place]:
    places: list[Place] = []
    seen: set[tuple[str, str | None, float | None, float | None]] = set()
    for name, content in input_files(input_path):
        normalized_name = name.lower()
        is_saved_file = any(token in normalized_name for token in ("saved", "salvat", "starred", "stea"))
        is_review_file = any(token in normalized_name for token in ("review", "recenzi"))
        if not all_files and (not is_saved_file or is_review_file):
            continue
        try:
            candidates = parse_file(name, content)
        except (UnicodeDecodeError, ValueError, ElementTree.ParseError) as exc:
            print(f"warning: could not parse {name}: {exc}", file=sys.stderr)
            continue
        for place in candidates:
            key = (place.name.lower(), place.url, place.latitude, place.longitude)
            if key not in seen:
                seen.add(key)
                places.append(place)
    if not places:
        raise RuntimeError("No places found. Point the script at the Takeout ZIP or extracted folder containing Saved Places data.")
    return places


def write_output(places: Iterable[Place], output_format: str) -> None:
    # Windows consoles commonly default to cp1252; Takeout data can contain
    # Romanian and other Unicode characters that must survive CSV export.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    rows = [asdict(place) for place in places]
    if output_format == "json":
        json.dump(rows, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return
    writer = csv.DictWriter(sys.stdout, fieldnames=list(rows[0]) if rows else list(asdict(Place(""))))
    writer.writeheader()
    writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse saved places from a Google Takeout ZIP or directory.")
    parser.add_argument("takeout", help="Google Takeout ZIP file or extracted directory")
    parser.add_argument("-o", "--output", choices=("json", "csv"), default="json")
    parser.add_argument("--all-files", action="store_true", help="Scan every supported Takeout file instead of saved-location files only")
    args = parser.parse_args()
    try:
        write_output(extract(args.takeout, all_files=args.all_files), args.output)
        return 0
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
