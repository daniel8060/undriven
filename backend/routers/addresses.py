from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import SavedAddress, User
from backend.schemas import (
    AddressCreateRequest, AddressResponse, AddressUpdateRequest, ReorderRequest,
)

router = APIRouter(prefix="/api/addresses", tags=["addresses"])


@router.get("", response_model=list[AddressResponse])
def list_addresses(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return user.addresses


@router.post("", response_model=AddressResponse, status_code=201)
def create_address(
    body: AddressCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    label = body.label.strip()
    address = body.address.strip()
    if not label or not address:
        raise HTTPException(status_code=400, detail="label and address are required")
    if db.query(SavedAddress).filter_by(user_id=user.id, label=label).first():
        raise HTTPException(status_code=409, detail=f"label '{label}' already exists")
    next_order = db.query(SavedAddress).filter_by(user_id=user.id).count()
    addr = SavedAddress(user_id=user.id, label=label, address=address, sort_order=next_order)
    db.add(addr)
    db.commit()
    db.refresh(addr)
    return addr


@router.patch("/{addr_id}", response_model=AddressResponse)
def update_address(
    addr_id: int,
    body: AddressUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    addr = db.query(SavedAddress).filter_by(id=addr_id, user_id=user.id).first()
    if not addr:
        raise HTTPException(status_code=404, detail="Address not found")
    if body.label is not None:
        addr.label = body.label.strip()
    if body.address is not None:
        addr.address = body.address.strip()
    db.commit()
    db.refresh(addr)
    return addr


@router.delete("/{addr_id}", status_code=204)
def delete_address(
    addr_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    addr = db.query(SavedAddress).filter_by(id=addr_id, user_id=user.id).first()
    if not addr:
        raise HTTPException(status_code=404, detail="Address not found")
    db.delete(addr)
    db.commit()


@router.post("/reorder", status_code=204)
def reorder_addresses(
    body: ReorderRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    addrs_by_id = {a.id: a for a in user.addresses}
    for order, addr_id in enumerate(body.ids):
        if addr_id in addrs_by_id:
            addrs_by_id[addr_id].sort_order = order
    db.commit()
