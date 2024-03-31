import typing
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import Select

from src.core.database import DatedTableMixin, Objects, Session, SQLBase

if typing.TYPE_CHECKING:
    from src.models import Url


class User(SQLBase, DatedTableMixin):
    email: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str]
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)
    urls: Mapped[List["Url"]] = relationship("Url", back_populates="owner")

    def __str__(self) -> str:
        return self.email

    @classmethod
    def actives(cls, session: Session) -> Objects["User"]:
        return Objects(cls, session, User.is_active == True)  # noqa: E712

    def get_urls(self, include_deleted : bool) -> Select:
        from src.models import Url
        statement = select(Url).filter(Url.owner_id == self.id)
        if include_deleted:
            return statement
        return statement.filter(Url.is_active == True)
