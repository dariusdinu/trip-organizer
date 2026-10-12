"""Import grouped place CSV files into the local database."""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.session import SessionLocal
from backend.app.models import Category, Destination, Place


@dataclass
class ImportSummary:
    files_processed: int = 0
    rows_processed: int = 0
    places_created: int = 0
    duplicates_skipped: int = 0
    rows_failed: int = 0


def _text(row: dict[str, str | None], field: str) -> str | None:
    value = row.get(field)
    cleaned = value.strip() if value else ""
    return cleaned or None


def _number(row: dict[str, str | None], field: str) -> float | None:
    value = _text(row, field)
    if value is None:
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be a number, got {value!r}") from exc


def _find_destination(session: Session, name: str | None) -> Destination | None:
    if name is None or name.casefold() == "unknown":
        return None
    destination = session.scalar(select(Destination).where(Destination.name == name))
    if destination is None:
        destination = Destination(name=name)
        session.add(destination)
        session.flush()
    return destination


def _find_category(session: Session, name: str | None) -> Category | None:
    if name is None or name.casefold() == "uncategorized":
        return None
    category = session.scalar(select(Category).where(Category.name == name))
    if category is None:
        category = Category(name=name)
        session.add(category)
        session.flush()
    return category


def _is_duplicate(
    session: Session,
    *,
    name: str,
    destination_id: int | None,
    category_id: int | None,
) -> bool:
    statement = select(Place.name).where(
        Place.destination_id == destination_id if destination_id is not None else Place.destination_id.is_(None),
        Place.category_id == category_id if category_id is not None else Place.category_id.is_(None),
    )
    normalized_name = " ".join(name.split()).casefold()
    return any(" ".join(existing_name.split()).casefold() == normalized_name for existing_name in session.scalars(statement))


def _import_row(session: Session, row: dict[str, str | None]) -> bool:
    name = _text(row, "name")
    if name is None:
        raise ValueError("name is required")

    url = _text(row, "url")
    if url and session.scalar(select(Place.id).where(Place.url == url).limit(1)) is not None:
        return False

    destination = _find_destination(session, _text(row, "city"))
    category = _find_category(session, _text(row, "category"))
    url = _text(row, "url")

    if _is_duplicate(
        session,
        name=name,
        destination_id=destination.id if destination else None,
        category_id=category.id if category else None,
    ):
        return False

    place = Place(
        name=name,
        destination=destination,
        category=category,
        url=url,
        address=_text(row, "address"),
        latitude=_number(row, "latitude"),
        longitude=_number(row, "longitude"),
        note=_text(row, "note"),
        source_file=_text(row, "source_file"),
    )
    session.add(place)
    session.flush()
    return True


def import_csv_path(input_path: Path) -> ImportSummary:
    if input_path.is_file():
        files = [input_path] if input_path.suffix.lower() == ".csv" else []
    elif input_path.is_dir():
        files = sorted(input_path.glob("*.csv"))
    else:
        raise FileNotFoundError(f"CSV file or directory not found: {input_path}")
    if not files:
        raise FileNotFoundError(f"No CSV files found at: {input_path}")

    summary = ImportSummary()
    with SessionLocal() as session:
        for csv_path in files:
            summary.files_processed += 1
            try:
                with csv_path.open(encoding="utf-8-sig", newline="") as source:
                    reader = csv.DictReader(source)
                    required_columns = {"name", "city", "category"}
                    missing = required_columns - set(reader.fieldnames or [])
                    if missing:
                        raise ValueError(f"missing required columns: {', '.join(sorted(missing))}")
                    for line_number, row in enumerate(reader, start=2):
                        summary.rows_processed += 1
                        try:
                            with session.begin_nested():
                                created = _import_row(session, row)
                            if created:
                                summary.places_created += 1
                            else:
                                summary.duplicates_skipped += 1
                        except Exception as exc:
                            summary.rows_failed += 1
                            print(f"{csv_path}:{line_number}: {exc}", file=sys.stderr)
            except (OSError, UnicodeError, csv.Error, ValueError) as exc:
                summary.rows_failed += 1
                print(f"Could not import {csv_path}: {exc}", file=sys.stderr)
        session.commit()
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Import grouped city CSV files into SQLite.")
    parser.add_argument("input_path", help="A grouped CSV file or a directory containing grouped CSV files")
    args = parser.parse_args()
    try:
        summary = import_csv_path(Path(args.input_path))
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Files processed: {summary.files_processed}")
    print(f"Rows processed: {summary.rows_processed}")
    print(f"Places created: {summary.places_created}")
    print(f"Duplicates skipped: {summary.duplicates_skipped}")
    print(f"Rows failed: {summary.rows_failed}")
    return 1 if summary.rows_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
