from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from db import database_url

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

url = database_url().replace("postgresql://", "postgresql+psycopg2://", 1)

target_metadata = None


def run_migrations_offline() -> None:
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(url)
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
