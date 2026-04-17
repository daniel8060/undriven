from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import User

router = APIRouter(prefix="/api", tags=["maps"])


@router.get("/autocomplete")
def api_autocomplete(
    q: str = Query(""),
    lon: float | None = Query(None),
    lat: float | None = Query(None),
    user: User = Depends(get_current_user),
):
    if len(q.strip()) < 2:
        return []
    try:
        from gmaps import autocomplete
        focus = {"lon": lon, "lat": lat} if lon is not None and lat is not None else None
        return autocomplete(q.strip(), focus=focus)
    except Exception:
        return []


@router.get("/reverse-geocode")
def api_reverse_geocode(
    lon: float = Query(...),
    lat: float = Query(...),
    user: User = Depends(get_current_user),
):
    try:
        from gmaps import reverse_geocode
        return {"label": reverse_geocode(lon, lat)}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/geocode")
def api_geocode(
    q: str = Query(...),
    user: User = Depends(get_current_user),
):
    if not q.strip():
        raise HTTPException(status_code=400, detail="q param required")
    try:
        from gmaps import geocode
        lon, lat = geocode(q.strip())
        return {"query": q.strip(), "lon": lon, "lat": lat}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
