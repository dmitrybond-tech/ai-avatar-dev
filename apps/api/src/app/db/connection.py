"""Database connection management."""
import asyncpg
from app.core.settings import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_pool: asyncpg.Pool = None


async def init_db() -> asyncpg.Pool:
    """Initialize database connection pool and run migrations."""
    global _pool
    
    logger.info("Connecting to database...")
    _pool = await asyncpg.create_pool(
        settings.database_url,
        min_size=2,
        max_size=10,
        command_timeout=60,
    )
    
    # Run initialization SQL
    async with _pool.acquire() as conn:
        with open("/app/src/app/db/init.sql", "r") as f:
            init_sql = f.read()
        await conn.execute(init_sql)
    
    logger.info("Database initialized")
    return _pool


async def close_db() -> None:
    """Close database connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database connection closed")


def get_db_pool() -> asyncpg.Pool:
    """Get the database connection pool."""
    if _pool is None:
        raise RuntimeError("Database not initialized")
    return _pool

