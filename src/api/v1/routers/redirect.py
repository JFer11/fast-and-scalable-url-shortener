from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse

from src.api.dependencies import db_session
from src.api.v1.schemas import Url
from src.core.database import Session
from src.models import Url

router = APIRouter()


@router.get("/{shortened_url}", status_code=status.HTTP_302_FOUND, include_in_schema=False)
def redirect(
    shortened_url : str,
    session: Session = Depends(db_session)
) -> Any:
    url = Url.objects(session).get(Url.shortened_url == shortened_url, Url.is_active == True)
    if not url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found.")
    url.clicks += 1
    session.commit()
    return RedirectResponse(url.original_url, status_code=status.HTTP_302_FOUND)
