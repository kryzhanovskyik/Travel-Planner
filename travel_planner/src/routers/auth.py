import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src import models, schemas
from src.auth import (
    SECRET_KEY, ALGORITHM,
    create_access_token, hash_password, verify_password, get_current_user,
)
from src.database import get_db


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.UserResponse, status_code=201)
async def register(
    body: schemas.UserCreate,
    db: AsyncSession = Depends(get_db),
) -> models.User:
    result = await db.execute(select(models.User).where(models.User.username == body.username))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="Username already taken")

    user = models.User(username=body.username, hashed_password=hash_password(body.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=schemas.TokenResponse)
async def login(
    body: schemas.LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(select(models.User).where(models.User.username == body.username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {"access_token": create_access_token(user.id), "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserResponse)
async def me(current_user: models.User = Depends(get_current_user)) -> models.User:
    return current_user


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    token = request.headers["authorization"].split(" ", 1)[1]
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    jti: str = payload["jti"]

    db.add(models.RevokedToken(jti=jti))
    await db.commit()
