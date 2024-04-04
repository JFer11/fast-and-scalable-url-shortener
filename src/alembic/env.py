from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
from src import models  # noqa: F401
from src.core.config import settings
from src.core.database import SQLBase

# Alembic Config object
config = context.config

# Python logging setup
fileConfig(config.config_file_name)

target_metadata = SQLBase.metadata

DATABASE_URL = settings.database_url.replace("postgresql://", "async+postgresql://")

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = create_async_engine(DATABASE_URL)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

def do_run_migrations(connection):
    """Configure context and run migrations."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        # Enable the option below if the migration script needs to access the Alembic context
        # user_module_prefix='sa.',
    )

    with context.begin_transaction():
        context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    # Using asyncio to run the async function
    import asyncio
    asyncio.run(run_migrations_online())
