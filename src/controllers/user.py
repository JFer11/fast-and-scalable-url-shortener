from fastapi import HTTPException

from src.api.v1.schemas import UserCreate
from src.core.database import Session
from src.core.security import PasswordManager
from src.models import User


class UserController:
    @staticmethod
    def create(user_data: UserCreate, session: Session, is_superuser: bool = False) -> User:
        user = User.objects(session).get(User.email == user_data.email)
        if user:
            raise HTTPException(status_code=409, detail="Email address already in use")
        user_dict = user_data.dict()
        hashed_password = PasswordManager.get_password_hash(user_data.password)
        user_dict.update({"password": hashed_password, "is_superuser": is_superuser})
        user = User.objects(session).create(user_dict)
        return user

    @staticmethod
    def login(user_data: UserCreate, session: Session) -> User:
        login_exception = HTTPException(
            status_code=401, detail="Invalid email or password"
        )
        user = User.objects(session).get(User.email == user_data.email)
        if not user:
            raise login_exception
        if not PasswordManager.verify_password(user_data.password, user.password):
            raise login_exception
        return user
