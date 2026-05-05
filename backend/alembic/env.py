from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

from app.config import get_settings
from app.database import Base
from app.models import *  # noqa: F401,F403

config = context.config
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Our migration revision IDs use descriptive names that exceed Alembic's default
# alembic_version.version_num width of VARCHAR(32). Newer SQLAlchemy / psycopg2 on
# Python 3.14 (e.g. Render production) enforce the limit strictly and reject the
# INSERT. Older Python 3.12 stacks silently accepted the overflow. To be safe in
# every environment we pre-create the version table with a wider column. Alembic
# will then re-use it (its CREATE TABLE is IF NOT EXISTS-style behaviour).
_VERSION_TABLE_SQL = (
    "CREATE TABLE IF NOT EXISTS alembic_version ("
    "version_num VARCHAR(255) NOT NULL, "
    "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)"
    ")"
)

# If a prior environment already created the table with the default VARCHAR(32),
# widen it in place. This is a no-op when the column is already wide enough or
# the table has not yet been created.
_VERSION_TABLE_WIDEN_SQL = (
    "ALTER TABLE alembic_version "
    "ALTER COLUMN version_num TYPE VARCHAR(255)"
)


def _ensure_version_table_width(connection) -> None:
    connection.execute(text(_VERSION_TABLE_SQL))
    connection.commit()
    try:
        connection.execute(text(_VERSION_TABLE_WIDEN_SQL))
        connection.commit()
    except Exception:
        connection.rollback()
        # Some Postgres flavours / permissions may reject the ALTER even when the
        # column is already the right width. Ignore — the CREATE above already
        # guarantees a wide enough column for fresh databases.
        pass


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        _ensure_version_table_width(connection)
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
