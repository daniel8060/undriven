from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import SavedCar, User
from backend.schemas import CarCreateRequest, CarResponse, CarUpdateRequest, ReorderRequest

router = APIRouter(prefix="/api/cars", tags=["cars"])


@router.get("", response_model=list[CarResponse])
def list_cars(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return user.cars


@router.post("", response_model=CarResponse, status_code=201)
def create_car(
    body: CarCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    if db.query(SavedCar).filter_by(user_id=user.id, name=name).first():
        raise HTTPException(status_code=409, detail=f"car '{name}' already exists")

    no_default = not db.query(SavedCar).filter_by(user_id=user.id, is_default=True).first()
    next_order = db.query(SavedCar).filter_by(user_id=user.id).count()
    car = SavedCar(
        user_id=user.id, name=name, mpg=body.mpg,
        fuel_type=body.fuel_type.strip(), is_default=no_default, sort_order=next_order,
    )
    db.add(car)
    db.commit()
    db.refresh(car)
    return car


@router.patch("/{car_id}", response_model=CarResponse)
def update_car(
    car_id: int,
    body: CarUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    car = db.query(SavedCar).filter_by(id=car_id, user_id=user.id).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")
    if body.name is not None:
        car.name = body.name.strip()
    if body.mpg is not None:
        car.mpg = body.mpg
    if body.fuel_type is not None:
        car.fuel_type = body.fuel_type.strip()
    db.commit()
    db.refresh(car)
    return car


@router.delete("/{car_id}", status_code=204)
def delete_car(
    car_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    car = db.query(SavedCar).filter_by(id=car_id, user_id=user.id).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")
    was_default = car.is_default
    db.delete(car)
    db.flush()
    if was_default:
        next_car = db.query(SavedCar).filter_by(user_id=user.id).first()
        if next_car:
            next_car.is_default = True
    db.commit()


@router.post("/reorder", status_code=204)
def reorder_cars(
    body: ReorderRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cars_by_id = {c.id: c for c in user.cars}
    for order, car_id in enumerate(body.ids):
        if car_id in cars_by_id:
            cars_by_id[car_id].sort_order = order
    db.commit()


@router.post("/{car_id}/set-default", response_model=CarResponse)
def set_default_car(
    car_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    car = db.query(SavedCar).filter_by(id=car_id, user_id=user.id).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")
    db.query(SavedCar).filter_by(user_id=user.id, is_default=True).update({"is_default": False})
    car.is_default = True
    db.commit()
    db.refresh(car)
    return car
