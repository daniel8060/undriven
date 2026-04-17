from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.auth import COOKIE_NAME, create_access_token, get_current_user
from backend.database import get_db
from backend.models import User
from backend.schemas import LoginRequest, SignupRequest, UserResponse

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/login")
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=body.username).first()
    if not user or not user.check_password(body.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    token = create_access_token(user.id)
    response.set_cookie(
        COOKIE_NAME, token,
        httponly=True, samesite="lax", path="/",
        max_age=30 * 24 * 3600,
    )
    return {"ok": True}


@router.post("/signup", status_code=201)
def signup(body: SignupRequest, response: Response, db: Session = Depends(get_db)):
    if not body.username.strip() or not body.password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    if body.password != body.password2:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    if db.query(User).filter_by(username=body.username.strip()).first():
        raise HTTPException(status_code=409, detail="Username already taken")
    u = User(username=body.username.strip())
    u.set_password(body.password)
    db.add(u)
    db.commit()
    db.refresh(u)
    token = create_access_token(u.id)
    response.set_cookie(
        COOKIE_NAME, token,
        httponly=True, samesite="lax", path="/",
        max_age=30 * 24 * 3600,
    )
    return {"ok": True}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user
