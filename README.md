# Trip Organizer

A local travel-planning application for importing saved Google Maps places
from Google Takeout, grouping them by city and category, and browsing them in
a small React interface.

## Project layout

```text
src/trip_organizer/       Python package and command-line tools
backend/                  FastAPI API, SQLAlchemy models, and CSV importer
frontend/                 React + Vite application
data/exports/             Local Takeout exports (ignored by Git)
data/processed/           Generated CSV files (ignored by Git)
```

Personal exports and generated CSVs stay local and are excluded from Git.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Import places and start the API

```powershell
python -m backend.app.database.init_db
python -m backend.app.importers.csv_import data/processed/grouped_places
python -m uvicorn backend.app.main:app --reload
```

The importer accepts either the directory containing grouped CSVs or one CSV
file. It creates destinations and categories from the `city` and `category`
columns; `Unknown` destinations and `Uncategorized` categories are stored as
unassigned. Existing places are skipped when their non-empty URL matches, or
when normalized name, destination, and category match exactly. Import summaries
and row-level errors are printed to the console.

The API is available at `http://127.0.0.1:8000`. Useful endpoints are
`/health`, `/destinations`, `/categories`, `/places`, and `/docs`. Places can
be filtered with `destination_id` and `category_id` query parameters.

The default SQLite database is `data/trip_organizer.db`. Override its URL with
`TRIP_ORGANIZER_DATABASE_URL`. By default, CORS permits Vite on ports 5173 at
localhost and 127.0.0.1; override this comma-separated list with
`TRIP_ORGANIZER_CORS_ORIGINS` if needed. Schema initialization is explicit;
starting the API does not create or reset the database.

## Start the frontend

In a second PowerShell terminal:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Open the Vite URL shown in the terminal (normally `http://localhost:5173`).
The frontend uses `http://localhost:8000` as its API by default. To change it,
copy `.env.example` to `.env` and set `VITE_API_BASE_URL` before starting Vite.

## Takeout workflow

In Google Takeout, select **Saved**, download the ZIP, then parse and group it:

```powershell
python -m trip_organizer.google_takeout_parser "C:\Downloads\takeout.zip" --output csv > data/exports/places.csv
python -m trip_organizer.group_places data/exports/places.csv --output-dir data/processed/grouped_places
```

The parser handles Takeout JSON, CSV, and KML files and recognizes localized
CSV headers. It includes place name, URL, address, coordinates, note, and the
source list file when present. City and category are inferred from saved-list
filenames during grouping.
