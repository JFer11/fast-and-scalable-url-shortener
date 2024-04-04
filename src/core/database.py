import uuid
from datetime import datetime
from typing import Any, Dict, Generic, Sequence, Type, TypeVar

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import func, select
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    declarative_mixin,
    declared_attr,
    mapped_column,
    sessionmaker,
)
from sqlalchemy.sql import Select

from src.core.config import settings
from src.helpers.casing import snakecase
from src.helpers.sql import random_uuid, utcnow


async_engine = create_async_engine(settings.database_url, echo=True)
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class SQLBase(DeclarativeBase):
    __abstract__ = True

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return snakecase(cls.__name__)

    @classmethod
    def objects(cls: Type["_Model"], session: AsyncSession) -> "Objects[_Model]":
        return Objects(cls, session)


_Model = TypeVar("_Model", bound=SQLBase)


class Objects(Generic[_Model]):
    cls: Type[_Model]
    session: AsyncSession
    base_statement: Select
    queryset_filters: Any = None

    def __init__(
        self,
        cls: Type[_Model],
        session: AsyncSession,
        *queryset_filters: Any,
    ) -> None:
        self.cls = cls
        self.session = session
        base_statement = select(cls)
        if queryset_filters:
            self.queryset_filters = queryset_filters
            base_statement = base_statement.where(*queryset_filters)
        self.base_statement = base_statement

    async def all(self) -> Sequence[_Model]:
        result = await self.session.execute(self.base_statement)
        return result.scalars().unique().all()

    async def get(self, *where_clause: Any) -> _Model | None:
        statement = self.base_statement.where(*where_clause)
        result = await self.session.execute(statement)
        return result.scalars().unique().one_or_none()

    async def get_or_404(self, *where_clause: Any) -> _Model:
        obj = await self.get(*where_clause)
        if obj is None:
            raise HTTPException(
                status_code=404, detail=f"{self.cls.__name__} not found"
            )
        return obj

    async def get_all(self, *where_clause: Any) -> Sequence[_Model]:
        statement = self.base_statement.where(*where_clause)
        result = await self.session.execute(statement)
        return result.scalars().unique().all()

    async def count(self, *where_clause: Any) -> int:
        statement = select(func.count()).select_from(self.cls)
        if self.queryset_filters:
            statement = statement.where(*self.queryset_filters)
        if where_clause:
            statement = statement.where(*where_clause)
        result = await self.session.execute(statement)
        return result.scalar_one()

    async def create(self, data: Dict[str, Any]) -> _Model:
        obj = self.cls(**data)
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj


@declarative_mixin
class TableIdMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=random_uuid()
    )


@declarative_mixin
class DatedTableMixin(TableIdMixin):
    created_at: Mapped[datetime] = mapped_column(server_default=utcnow())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=utcnow(), onupdate=datetime.utcnow()
    )
