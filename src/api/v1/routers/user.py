from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate

from src import models
from src.api.dependencies import db_session, get_user
from src.api.v1 import schemas
from src.api.v1.schemas import Token, UserCreate
from src.controllers import UserController
from src.core.database import Session
from src.core.security import AuthManager

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
def signup(
    response: Response,
    user_data: UserCreate,
    session: Session = Depends(db_session),
) -> Token | None:
    user = UserController.create(user_data=user_data, session=session)
    return AuthManager.process_login(user=user, response=response)


@router.post("/login")
def login(
    response: Response,
    user_data: UserCreate,
    session: Session = Depends(db_session),
) -> Token | None:
    user = UserController.login(user_data=user_data, session=session)
    return AuthManager.process_login(user=user, response=response)


@router.get("/me", response_model=schemas.User)
def me(user: models.User = Depends(get_user)) -> Any:
    return user
