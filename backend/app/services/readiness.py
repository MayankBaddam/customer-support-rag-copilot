from sqlalchemy import text

from app.database.session import get_database_engine


async def check_readiness() -> dict[str, str]:
    """Verify the configured runtime database without exposing connection details."""
    engine = get_database_engine()
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"application": "ok", "database": "connected"}