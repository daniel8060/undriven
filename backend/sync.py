import sys
import os

# Ensure project root is on the path for gmaps/config imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
from backend.db import insert_trip
from gmaps import MapsError, driving_miles
from sqlalchemy.orm import Session


def parse_car(car_raw: str, cars: dict) -> str | None:
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
    session: Session,
    date: str,
    start: str,
    end: str,
    mode: str,
    car_name: str | None,
    notes: str,
    user_id: int,
    cars: dict | None = None,
    segments: list[dict] | None = None,
) -> float:
    """
    Resolve driving miles via Google Routes API, compute CO2, and persist the trip.
    Returns the resolved miles. Raises MapsError if routing fails.

    segments: list of {"start": str, "end": str, "mode": str} for multi-segment trips.
    """
    if cars is None:
        cars = {}

    if segments and len(segments) > 1:
        # Multi-segment trip: resolve each segment individually
        resolved_segments = []
        total_miles = 0.0
        for seg in segments:
            seg_miles = driving_miles(seg["start"], seg["end"])
            total_miles += seg_miles
            resolved_segments.append({
                "start_loc": seg["start"],
                "end_loc": seg["end"],
                "mode": seg["mode"],
                "miles": seg_miles,
            })

        overall_start = segments[0]["start"]
        overall_end = segments[-1]["end"]
        overall_mode = segments[0]["mode"]
        co2 = co2_for_car(car_name, total_miles, cars) if car_name and car_name in cars else 0.0

        insert_trip(
            session=session,
            date=date,
            start_loc=overall_start,
            end_loc=overall_end,
            mode=overall_mode,
            car_name=car_name,
            miles=total_miles,
            co2_kg=co2,
            notes=notes,
            user_id=user_id,
            segments=resolved_segments,
        )
        print(f"[log] {overall_start} \u2192 {overall_end} ({len(segments)} segments) \u2014 {total_miles:.2f} mi, {co2:.3f} kg CO2")
        return total_miles
    else:
        # Single-segment or no segments: existing behavior
        miles = driving_miles(start, end)
        co2 = co2_for_car(car_name, miles, cars) if car_name and car_name in cars else 0.0

        insert_trip(
            session=session,
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
        print(f"[log] {start} \u2192 {end} ({mode}) \u2014 {miles:.2f} mi, {co2:.3f} kg CO2")
        return miles
