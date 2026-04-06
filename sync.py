import config
from db import insert_trip
from ors import driving_miles, ORSError


def parse_car(car_raw: str) -> str | None:
    """Return a valid car name from a raw string, or None if blank/unknown."""
    name = car_raw.strip()
    if not name:
        return None
    if name not in config.CARS:
        print(f"  [warn] unknown car name: {name!r}")
        return None
    return name


def co2_for_car(car_name: str, miles: float) -> float:
    car = config.CARS[car_name]
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
    start_coord: tuple | None = None,
    end_coord:   tuple | None = None,
) -> float:
    """
    Resolve driving miles via ORS, compute CO2, and persist the trip.
    Returns the resolved miles. Raises ORSError if geocoding/routing fails.
    Pre-computed coordinates can be passed to skip geocoding entirely.
    """
    miles = driving_miles(start, end, start_coord=start_coord, end_coord=end_coord)
    co2 = co2_for_car(car_name, miles) if car_name else 0.0

    insert_trip(
        date=date,
        start_loc=start,
        end_loc=end,
        mode=mode,
        car_name=car_name,
        miles=miles,
        co2_kg=co2,
        notes=notes,
    )
    print(f"[log] {start} → {end} ({mode}) — {miles:.2f} mi, {co2:.3f} kg CO2")
    return miles
