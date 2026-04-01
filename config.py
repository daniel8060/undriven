ORS_API_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjI4MjY4MDI0MGUzNTQ5ZDM4OGM5MzQwZjE1MDVmYjdlIiwiaCI6Im11cm11cjY0In0="

SHEET_ID = "your-google-sheet-id-here"
SHEET_TAB = "Sheet1"

GOOGLE_CREDENTIALS_FILE = "credentials.json"

CARS = {
    "4Runner": {"mpg": 18.0, "fuel_type": "gasoline"},
    "Corolla": {"mpg": 29.0, "fuel_type": "gasoline"},
}

# Bias geocoding results toward your area. Set to your approximate location.
# Find your lon/lat at: https://www.latlong.net
# Leave as None to use ORS defaults (may return distant results for ambiguous names).
GEOCODE_FOCUS = None  # e.g. {"lon": -122.41, "lat": 37.77}

CO2_KG_PER_GALLON = {
    "gasoline": 8.887,
    "diesel": 10.180,
    "electric": 0.0,
    "hybrid": 8.887,
}
