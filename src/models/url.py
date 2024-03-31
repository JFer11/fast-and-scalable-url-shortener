import typing
from uuid import UUID

from sqlalchemy import ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import DatedTableMixin, SQLBase

if typing.TYPE_CHECKING:
    from src.models import User


class Url(SQLBase, DatedTableMixin):
    original_url: Mapped[str]
    shortened_url: Mapped[str] = mapped_column(unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    clicks: Mapped[int] = mapped_column(default=0)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("user.id"))
    owner: Mapped["User"] = relationship("User", back_populates="urls")

    __table_args__ = (CheckConstraint('clicks >= 0', name='clicks_positive'),)

    def __str__(self) -> str:
        return f"URL {self.shortened_url}"
