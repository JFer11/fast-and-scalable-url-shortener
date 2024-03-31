from fastapi import APIRouter

from src.api.v1.routers import user, url, redirect

v1_router = APIRouter()
v1_router.include_router(user.router, prefix="/users")
v1_router.include_router(url.router, prefix="/urls")
v1_router.include_router(redirect.router, prefix="/redirect")
