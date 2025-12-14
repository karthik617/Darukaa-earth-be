# backend/app/auth.py
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

import models
from database import get_db
from schemas import Token, UserCreate, UserOut

# env
JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_THIS_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
REFRESH_COOKIE_NAME = os.getenv("REFRESH_COOKIE_NAME", "refresh_token")


pwd_context = CryptContext(
    schemes=["argon2"], deprecated="auto"
)  # switched from bcrypt
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------- helpers ----------------
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_jwt(payload: dict, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = payload.copy()
    to_encode.update({"exp": int(expire.timestamp())})
    token = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def create_access_token_for_user(user_id: int) -> tuple[str, int]:
    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id)}
    token = create_jwt(payload, expires_delta=expires_delta)
    expires_in = int(expires_delta.total_seconds())
    return token, expires_in


def create_refresh_token_for_user(db: Session, user_id: int) -> tuple[str, datetime]:
    jti = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "jti": jti}
    token = create_jwt(payload, expires_delta=expires_at - datetime.utcnow())
    # persist jti
    rt = models.RefreshToken(
        jti=jti, user_id=user_id, revoked=False, expires_at=expires_at
    )
    db.add(rt)
    db.commit()
    return token, expires_at


def revoke_refresh_token(db: Session, jti: str):
    stmt = select(models.RefreshToken).where(models.RefreshToken.jti == jti)
    row = db.execute(stmt).scalar_one_or_none()
    if row:
        row.revoked = True
        db.add(row)
        db.commit()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()


def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


# ---------------- endpoints ----------------
@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = get_password_hash(user_in.password)
    user = models.User(email=user_in.email, password_hash=hashed)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = get_user_by_email(db, form_data.username)
    if not user or not pwd_context.verify(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    access_token, expires_in = create_access_token_for_user(user.id)
    refresh_token, expires_at = create_refresh_token_for_user(db, user.id)

    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        samesite="lax",
        # secure=True,
        secure=not os.getenv("PYTEST_RUNNING"),
        expires=int((expires_at - datetime.utcnow()).total_seconds()),
        path="/",
    )
    return {"access_token": access_token, "expires_in": expires_in}


@router.post("/refresh", response_model=Token)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="no refresh token")
    try:
        payload = jwt.decode(refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = int(payload.get("sub"))
        jti = payload.get("jti")
        if not jti:
            raise HTTPException(status_code=401, detail="invalid refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="invalid refresh token")
    rt = (
        db.query(models.RefreshToken)
        .filter(models.RefreshToken.jti == jti, models.RefreshToken.user_id == user_id)
        .one_or_none()
    )
    if not rt or rt.revoked:
        raise HTTPException(
            status_code=401, detail="refresh token revoked or not found"
        )
    # rotate: revoke old
    rt.revoked = True
    db.add(rt)
    db.commit()
    # create new
    new_refresh_token, new_expires_at = create_refresh_token_for_user(db, user_id)
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=new_refresh_token,
        httponly=True,
        samesite="lax",
        # secure=True,
        secure=not os.getenv("PYTEST_RUNNING"),
        expires=int((new_expires_at - datetime.utcnow()).total_seconds()),
        path="/",
    )
    access_token, expires_in = create_access_token_for_user(user_id)
    return {"access_token": access_token, "expires_in": expires_in}


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if refresh_token:
        try:
            payload = jwt.decode(refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            jti = payload.get("jti")
            if jti:
                revoke_refresh_token(db, jti)
        except JWTError:
            pass
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/")
    return Response(status_code=204)
