import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_MAPS_API_KEY = os.environ["GOOGLE_MAPS_API_KEY"]  # required — set in .env

CARS = {
    "4Runner": {"mpg": 18.0, "fuel_type": "gasoline"},
    "Corolla": {"mpg": 29.0, "fuel_type": "gasoline"},
}

# Bias geocoding results toward your area. Set to your approximate location.
# Find your lon/lat at: https://www.latlong.net
GEOCODE_FOCUS = {"lon": -122.04, "lat": 37.37}  # Sunnyvale, CA


CO2_KG_PER_GALLON = {
    "gasoline": 8.887,
    "diesel": 10.180,
    "electric": 0.0,
    "hybrid": 8.887,
}
