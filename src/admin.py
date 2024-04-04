from fastapi import Request
from fastapi.responses import RedirectResponse
from sqladmin import ModelView
from sqladmin.authentication import AuthenticationBackend

from src.core.database import AsyncSessionLocal
from src.core.security import AuthManager, PasswordManager
from src.models import User, Url

import logging

logger = logging.getLogger(__name__)


class AdminAuth(AuthenticationBackend):
    cookie_name = "admin-cookie"

    async def login(self, request: Request) -> bool:
        form = await request.form()
        email, password = form["username"], form["password"]
        async with AsyncSessionLocal() as session:
            user = await User.objects(session).get(User.email == email)
        if not user or not user.is_superuser:
            return False
        if not PasswordManager.verify_password(password, user.password):  # type: ignore[arg-type]
            return False
        token, _ = AuthManager.create_access_token(user=user)
        request.session.update({AdminAuth.cookie_name: token})
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> RedirectResponse | None:
        failed_auth_response = RedirectResponse(
            request.url_for("admin:login"), status_code=302
        )
        manager = AuthManager()
        token = request.session.get(AdminAuth.cookie_name)
        if not token:
            return failed_auth_response
        try:
            async with AsyncSessionLocal() as session:
                user = await manager.get_user_from_token(token=token, session=session)
        except Exception:
            return failed_auth_response
        if not user.is_superuser:
            return failed_auth_response
        return None



class UserAdmin(ModelView, model=User):
    column_list = [
        User.email,
        User.created_at,
        User.id,
        User.password,
        User.is_superuser,
    ]
    column_searchable_list = [User.id, User.email]


class UrlAdmin(ModelView, model=Url):
    column_list = [
        Url.original_url,
        Url.shortened_url,
        Url.is_active,
        Url.clicks,
        Url.owner,
        Url.created_at,
        Url.updated_at,
        Url.id,
    ]
