import config
from db import get_known_sheet_rows, insert_trip
from ors import driving_miles, ORSError
from sheets import get_pending_rows, write_miles


def parse_cars(cars_raw: str) -> list[dict]:
    if not cars_raw.strip():
        return []

    result = []
    for token in cars_raw.split(","):
        token = token.strip()
        if not token:
            continue

        if ":" not in token:
            print(f"  [warn] malformed car token (no colon): {token!r}")
            continue

        parts = token.split(":", 1)
        car_name = parts[0].strip()
        occupants_str = parts[1].strip()

        if car_name not in config.CARS:
            print(f"  [warn] unknown car name, skipping: {car_name!r}")
            continue

        try:
            occupants = int(occupants_str)
        except ValueError:
            print(f"  [warn] non-integer occupants for {car_name!r}: {occupants_str!r}")
            continue

        result.append({"car_name": car_name, "occupants": occupants})

    return result


def co2_for_car(car_name: str, miles: float) -> float:
    car = config.CARS[car_name]
    mpg = car["mpg"]
    fuel_type = car["fuel_type"]
    co2_per_gallon = config.CO2_KG_PER_GALLON.get(fuel_type, 0.0)
    if mpg == 0:
        return 0.0
    gallons = miles / mpg
    return gallons * co2_per_gallon


def run_sync() -> dict:
    known_rows = get_known_sheet_rows()
    print(f"[sync] {len(known_rows)} rows already in DB")

    pending = get_pending_rows(known_rows)
    print(f"[sync] {len(pending)} pending rows from sheet")

    processed = 0
    errors = 0
    skipped = 0

    for row in pending:
        sheet_row = row["sheet_row"]
        start = row["start"]
        end = row["end"]
        print(f"  [row {sheet_row}] {start} → {end} ({row['mode']})")

        try:
            miles = driving_miles(start, end)
        except ORSError as exc:
            print(f"  [row {sheet_row}] ORS error: {exc}")
            errors += 1
            continue

        print(f"  [row {sheet_row}] resolved {miles:.2f} miles")

        parsed_cars = parse_cars(row["cars"])
        car_entries = []
        for car in parsed_cars:
            co2 = co2_for_car(car["car_name"], miles)
            car_entries.append({
                "car_name": car["car_name"],
                "occupants": car["occupants"],
                "co2_kg": co2,
            })

        insert_trip(
            sheet_row=sheet_row,
            date=row["date"],
            start_loc=start,
            end_loc=end,
            mode=row["mode"],
            cars_raw=row["cars"],
            miles=miles,
            notes=row["notes"],
            cars=car_entries,
        )

        write_miles(sheet_row, miles)
        print(f"  [row {sheet_row}] done")
        processed += 1

    print(f"[sync] complete — processed={processed}, errors={errors}, skipped={skipped}")
    return {"processed": processed, "errors": errors, "skipped": skipped}
