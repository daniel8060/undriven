import config
from db import insert_trip
from gmaps import driving_miles, MapsError


def parse_car(car_raw: str, cars: dict) -> str | None:
    """Return a valid car name from a raw string, or None if blank/unknown.

    cars: mapping of {name: {mpg, fuel_type}} — typically built from the
    current user's SavedCar rows.
    """
    name = car_raw.strip()
    if not name:
        return None
    if name not in cars:
        print(f"  [warn] unknown car name: {name!r}")
        return None
    return name


def co2_for_car(car_name: str, miles: float, cars: dict) -> float:
    car = cars[car_name]
    mpg = car["mpg"]
    fuel_type = car["fuel_type"]
    co2_per_gallon = config.CO2_KG_PER_GALLON.get(fuel_type, 0.0)
    if mpg == 0:
        return 0.0
    gallons = miles / mpg
    return gallons * co2_per_gallon


def log_trip(
    date: str,
    start: str,
    end: str,
    mode: str,
    car_name: str | None,
    notes: str,
    cars: dict | None = None,
    user_id: int | None = None,
) -> float:
    """
    Resolve driving miles via Google Routes API, compute CO2, and persist the trip.
    Returns the resolved miles. Raises MapsError if routing fails.

    cars: mapping of {name: {mpg, fuel_type}} used for CO2 calculation.
    """
    if cars is None:
        cars = {}
    miles = driving_miles(start, end)
    co2 = co2_for_car(car_name, miles, cars) if car_name and car_name in cars else 0.0

    insert_trip(
        date=date,
        start_loc=start,
        end_loc=end,
        mode=mode,
        car_name=car_name,
        miles=miles,
        co2_kg=co2,
        notes=notes,
        user_id=user_id,
    )
    print(f"[log] {start} → {end} ({mode}) — {miles:.2f} mi, {co2:.3f} kg CO2")
    return miles
