# Trip Organizer

A small Python utility for importing saved Google Maps places from Google
Takeout, then grouping them by city and category.

## Project layout

```text
src/trip_organizer/       Python package and command-line tools
data/private/             Local list links (ignored by Git)
data/exports/             Local Takeout exports (ignored by Git)
data/processed/           Generated CSV files (ignored by Git)
```

Personal exports, list URLs, browser profiles, and generated CSVs stay local
and are excluded from Git.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Import Google Takeout saved lists

In Google Takeout, select **Saved**, download the ZIP, then parse it:

```powershell
python -m trip_organizer.google_takeout_parser "C:\Downloads\takeout.zip" --output csv > data/exports/places.csv
```

The parser handles Takeout JSON, CSV, and KML files and recognizes localized
CSV headers. It includes place name, URL, address, coordinates, note, and the
source list file when present.

## Group by city and category

```powershell
python -m trip_organizer.group_places data/exports/places.csv --output-dir data/processed/grouped_places
```

City is inferred from the saved-list filename. Category is normalized from
that same filename (for example, `Athens Coffee` becomes `Coffee Shops`).
Generic lists are marked `Uncategorized`; unrecognized categories are marked
`Other`.

## Optional public-list browser parser

`google_maps_list_parser` is retained for public/shared list URLs. Add one URL
per line to `data/private/links.txt`, then run:

```powershell
python -m pip install playwright
python -m playwright install chromium
python -m trip_organizer.google_maps_list_parser data/private/links.txt --output csv > data/exports/browser_places.csv
```

The browser parser may not access lists that require Google sign-in.
