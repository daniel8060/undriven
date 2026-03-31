# Undriven

Track car miles replaced by non-car trips — bike, walk, train, bus, etc.

Every time you open the dashboard, Undriven checks your Google Sheet for new rows,
calculates the equivalent driving distance via OpenRouteService, writes the miles back
to the sheet, and stores everything locally in SQLite.

---

## Setup

### 1. Install dependencies

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync
```

### 2. Get an ORS API key

1. Sign up at [openrouteservice.org](https://openrouteservice.org)
2. Generate a free API key from your dashboard
3. Paste it into `config.py` as `ORS_API_KEY`

### 3. Set up your Google Sheet

Create a sheet with this column layout (row 1 is the header, data starts at row 2):

| A: date    | B: start          | C: end            | D: mode | E: cars            | F: miles | G: notes        |
|------------|-------------------|-------------------|---------|--------------------|----------|-----------------|
| 2024-03-15 | Portland, OR      | Seattle, WA       | train   | 4Runner:1          |          | weekend trip    |
| 2024-03-16 | Capitol Hill, Seattle | Pike Place Market | walk | Corolla:2        |          |                 |

- **date** — any parseable date string, e.g. `2024-03-15`
- **start / end** — place names or addresses that ORS can geocode
- **mode** — free text: `bike`, `walk`, `train`, `bus`, `scooter`, etc.
- **cars** — comma-separated `CarName:occupants` pairs, e.g. `4Runner:1, Corolla:2`. Must match names in `config.py`. Leave blank if tracking the trip without a specific car.
- **miles** — leave blank; Undriven fills this in automatically
- **notes** — anything you want

### 4. Create a Google service account

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or use an existing one)
3. Enable the **Google Sheets API** and **Google Drive API**
4. Go to **IAM & Admin → Service Accounts** and create a service account
5. Create a JSON key for the service account and download it
6. Rename the file to `credentials.json` and place it in this directory
7. Share your Google Sheet with the service account's email address (Editor access)

### 5. Edit config.py

```python
ORS_API_KEY = "your-key-here"
SHEET_ID    = "the-long-id-from-your-sheet-url"
SHEET_TAB   = "Sheet1"  # name of the tab
```

The sheet ID is the part of the URL between `/d/` and `/edit`:
`https://docs.google.com/spreadsheets/d/THIS_PART_HERE/edit`

### 6. Run

```bash
uv run python app.py
```

Then open [http://localhost:5000](http://localhost:5000).

---

## How the sync works

On every page load (`GET /`), Undriven:

1. Reads all rows from the sheet where column F (miles) is blank
2. Skips rows already in the local SQLite database (`trips.db`)
3. For each new row: geocodes start + end via ORS, fetches the driving distance
4. Writes the miles back to column F of the sheet
5. Stores the trip and per-car CO₂ data in SQLite
6. Renders the dashboard from SQLite (no further API calls)

You can also trigger a sync manually without a page reload:
```bash
curl -X POST http://localhost:5000/api/sync
```

Sync progress is printed to stdout — useful for debugging.

---

## Adding a new car

Edit `CARS` in `config.py`:

```python
CARS = {
    "4Runner": {"mpg": 18.0, "fuel_type": "gasoline"},
    "Corolla": {"mpg": 32.0, "fuel_type": "gasoline"},
    "Prius":   {"mpg": 52.0, "fuel_type": "hybrid"},   # ← add here
}
```

Supported `fuel_type` values: `gasoline`, `diesel`, `electric`, `hybrid`.

---

## Troubleshooting

**Miles stop filling in**
- Check the ORS API key in `config.py` — free tier has rate limits
- Make sure start/end place names are specific enough to geocode (city + state works well)
- Run with `uv run python app.py` and watch stdout for per-row error messages

**Sheet not found**
- Confirm the sheet ID in `config.py` matches your URL
- Confirm the service account email has Editor access to the sheet
- Confirm `credentials.json` is in the project root

**"Unknown car name" warning in stdout**
- The car name in column E must exactly match a key in `CARS` (case-sensitive)
