import typing
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import DatedTableMixin, Objects, AsyncSession, SQLBase

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
    async def actives(cls, session: AsyncSession) -> Objects["User"]:
        return Objects(cls, session, User.is_active == True)  # noqa: E712

    async def get_urls(self, session: AsyncSession, include_deleted: bool = False) -> List["Url"]:
        from src.models import Url

        statement = select(Url).where(Url.owner_id == self.id)
        if not include_deleted:
            statement = statement.where(Url.is_active == True)
        result = await session.execute(statement)
        urls = result.scalars().all()
        return urls
