from fastapi import HTTPException

from src.api.v1.schemas import UserCreate
from src.core.database import AsyncSession
from src.core.security import PasswordManager
from src.models import User


class UserController:
    @staticmethod
    async def create(user_data: UserCreate, session: AsyncSession, is_superuser: bool = False) -> User:
        user = await User.objects(session).get(User.email == user_data.email)
        if user:
            raise HTTPException(status_code=409, detail="Email address already in use")
        user_dict = user_data.dict()
        hashed_password = PasswordManager.get_password_hash(user_data.password)
        user_dict.update({"password": hashed_password, "is_superuser": is_superuser})
        user = await User.objects(session).create(user_dict)
        return user

    @staticmethod
    async def login(user_data: UserCreate, session: AsyncSession) -> User:
        login_exception = HTTPException(
            status_code=401, detail="Invalid email or password"
        )
        user = await User.objects(session).get(User.email == user_data.email)
        if not user:
            raise login_exception
        if not PasswordManager.verify_password(user_data.password, user.password):
            raise login_exception
        return user
