import os
from contextlib import asynccontextmanager
from pathlib import Path
import aiosqlite
from src.pulse.config import settings

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_db_path() -> Path:
    db_path = Path(settings.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


@asynccontextmanager
async def get_db():
    """Async context manager yielding an aiosqlite database connection."""
    db_path = get_db_path()
    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA foreign_keys=ON;")
        yield db


async def init_db(db_file: str | Path | None = None):
    """Initialize database tables and indexes from schema.sql."""
    target_path = Path(db_file) if db_file else get_db_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = f.read()
        
    async with aiosqlite.connect(str(target_path)) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA foreign_keys=ON;")
        await db.executescript(schema)
        await db.commit()
