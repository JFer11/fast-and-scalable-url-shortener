from typing import Any

from fastapi import APIRouter, Depends, Response, status

from src import models
from src.api.dependencies import db_session, get_user
from src.api.v1 import schemas
from src.api.v1.schemas import Token, UserCreate
from src.controllers import UserController
from src.core.database import AsyncSession
from src.core.security import AuthManager

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
async def signup(
    response: Response,
    user_data: UserCreate,
    superuser: bool = False,
    session: AsyncSession = Depends(db_session),
) -> Token | None:
    user = await UserController.create(user_data=user_data, session=session, is_superuser=superuser)
    return AuthManager.process_login(user=user, response=response)


@router.post("/login")
async def login(
    response: Response,
    user_data: UserCreate,
    session: AsyncSession = Depends(db_session),
) -> Token | None:
    user = await UserController.login(user_data=user_data, session=session)
    return AuthManager.process_login(user=user, response=response)


@router.get("/me", response_model=schemas.User)
async def me(user: models.User = Depends(get_user)) -> Any:
    return user
