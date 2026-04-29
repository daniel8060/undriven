from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.db import delete_trip, get_all_trips, get_summary
from backend.models import User
from backend.schemas import SummaryResponse, TripLogRequest, TripResponse
from backend.sync import log_trip, parse_car

MODES = ["bike", "walk", "train", "bus", "scooter", "car", "other"]

router = APIRouter(prefix="/api", tags=["trips"])


def _user_cars_dict(user: User) -> dict:
    return {c.name: {"mpg": c.mpg, "fuel_type": c.fuel_type} for c in user.cars}


@router.get("/trips", response_model=list[TripResponse])
def list_trips(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return get_all_trips(db, user.id)


@router.post("/trips", response_model=TripResponse, status_code=201)
def create_trip(
    body: TripLogRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cars = _user_cars_dict(user)
    car_name = parse_car(body.car, cars) if body.car else None
    if body.car and car_name is None:
        raise HTTPException(status_code=400, detail=f"Unknown car: {body.car!r}")

    segments = None
    if body.segments and len(body.segments) > 1:
        segments = [{"start": s.start.strip(), "end": s.end.strip(), "mode": s.mode.strip()} for s in body.segments]
        start = segments[0]["start"]
        end = segments[-1]["end"]
        mode = segments[0]["mode"]
    else:
        start = body.start.strip()
        end = body.end.strip()
        mode = body.mode.strip()

    if not (body.date and start and end and mode):
        raise HTTPException(status_code=400, detail="Date, start, end, and mode are required")
    if mode not in MODES:
        raise HTTPException(status_code=400, detail=f"Unknown mode: {mode!r}")
    if segments:
        for s in segments:
            if s["mode"] not in MODES:
                raise HTTPException(status_code=400, detail=f"Unknown segment mode: {s['mode']!r}")

    from backend.gmaps import MapsError
    try:
        log_trip(
            session=db, date=body.date, start=start, end=end, mode=mode,
            car_name=car_name, notes=body.notes, user_id=user.id,
            cars=cars, segments=segments,
        )
        if body.round_trip and not segments:
            log_trip(
                session=db, date=body.date, start=end, end=start, mode=mode,
                car_name=car_name, notes=body.notes, user_id=user.id,
                cars=cars,
            )
    except MapsError as exc:
        raise HTTPException(status_code=502, detail=f"Could not resolve route: {exc}")

    # Return the most recently created trip
    trips = get_all_trips(db, user.id)
    return trips[0]


@router.delete("/trips/{trip_id}", status_code=204)
def remove_trip(
    trip_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not delete_trip(db, trip_id, user.id):
        raise HTTPException(status_code=404, detail="Trip not found")


@router.get("/summary", response_model=SummaryResponse)
def summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return get_summary(db, user.id)
