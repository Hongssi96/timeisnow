"""Use the same private DB configuration as the application."""
from alembic import context
from sqlalchemy import create_engine, pool
from app.common.database import connect_db

config = context.config
# No business models yet. Explicit revisions only; autogenerate is unavailable.
target_metadata = None


def run(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(dialect_name="postgresql", literal_binds=True,
                      target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
else:
    supplied = config.attributes.get("connection")
    if supplied is not None:
        run(supplied)
    else:
        engine = create_engine("postgresql+psycopg://", creator=connect_db,
                               poolclass=pool.NullPool, hide_parameters=True)
        try:
            with engine.connect() as connection:
                run(connection)
        finally:
            engine.dispose()
