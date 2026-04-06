import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_MAPS_API_KEY = os.environ["GOOGLE_MAPS_API_KEY"]  # required — set in .env

SHEET_ID = os.environ.get("SHEET_ID", "")
SHEET_TAB = os.environ.get("SHEET_TAB", "Sheet1")
GOOGLE_CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS_FILE", "credentials.json")

CARS = {
    "4Runner": {"mpg": 18.0, "fuel_type": "gasoline"},
    "Corolla": {"mpg": 29.0, "fuel_type": "gasoline"},
}

# Bias geocoding results toward your area. Set to your approximate location.
# Find your lon/lat at: https://www.latlong.net
# Leave as None to use ORS defaults (may return distant results for ambiguous names).
GEOCODE_FOCUS = {"lon": -122.04, "lat": 37.37}  # Sunnyvale, CA


CO2_KG_PER_GALLON = {
    "gasoline": 8.887,
    "diesel": 10.180,
    "electric": 0.0,
    "hybrid": 8.887,
}
