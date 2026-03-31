import gspread
from google.oauth2.service_account import Credentials
import config

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

# Column indices (1-based)
COL_DATE  = 1  # A
COL_START = 2  # B
COL_END   = 3  # C
COL_MODE  = 4  # D
COL_CARS  = 5  # E
COL_MILES = 6  # F
COL_NOTES = 7  # G


def _open_sheet():
    creds = Credentials.from_service_account_file(
        config.GOOGLE_CREDENTIALS_FILE, scopes=SCOPES
    )
    client = gspread.authorize(creds)
    return client.open_by_key(config.SHEET_ID).worksheet(config.SHEET_TAB)


def get_pending_rows(known_rows: set) -> list[dict]:
    sheet = _open_sheet()
    all_rows = sheet.get_all_values()  # list of lists, row 0 = header

    pending = []
    for i, row in enumerate(all_rows[1:], start=2):  # 1-based, skip header
        if i in known_rows:
            continue

        # Pad short rows
        while len(row) < COL_NOTES:
            row.append("")

        date  = row[COL_DATE  - 1].strip()
        start = row[COL_START - 1].strip()
        end   = row[COL_END   - 1].strip()
        mode  = row[COL_MODE  - 1].strip()
        cars  = row[COL_CARS  - 1].strip()
        miles = row[COL_MILES - 1].strip()
        notes = row[COL_NOTES - 1].strip()

        # Skip rows missing required fields
        if not (date and start and end and mode):
            continue

        # Only process rows where miles is blank
        if miles:
            continue

        pending.append({
            "sheet_row": i,
            "date": date,
            "start": start,
            "end": end,
            "mode": mode,
            "cars": cars,
            "notes": notes,
        })

    return pending


def write_miles(sheet_row: int, miles: float):
    sheet = _open_sheet()
    sheet.update_cell(sheet_row, COL_MILES, round(miles, 2))
