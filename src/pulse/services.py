import re
from urllib.parse import urlparse
from pydantic import BaseModel, Field, field_validator
from src.pulse.clock import clock


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_-]+", "-", text).strip("-")


class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str | None = Field(default=None, max_length=100)
    health_url: str = Field(..., min_length=7, max_length=500)
    owner: str = Field(..., min_length=1, max_length=100)
    interval_seconds: int = Field(default=10, ge=1, le=3600)
    slo_target: float = Field(default=99.9, ge=50.0, le=100.0)

    @field_validator("health_url")
    @classmethod
    def validate_health_url(cls, v: str) -> str:
        v = v.strip()
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("health_url must be a valid http or https URL")
        return v

    @field_validator("name", "owner")
    @classmethod
    def strip_strings(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty or whitespace only")
        return v


class ServiceResponse(BaseModel):
    id: int
    name: str
    slug: str
    health_url: str
    owner: str
    interval_seconds: int
    slo_target: float
    enabled: bool
    current_state: str
    consecutive_failures: int
    consecutive_successes: int
    first_failure_at: str | None
    next_check_at: str | None
    created_at: str


async def list_services(db) -> list[dict]:
    async with db.execute(
        """
        SELECT id, name, slug, health_url, owner, interval_seconds, slo_target,
               enabled, current_state, consecutive_failures, consecutive_successes,
               first_failure_at, next_check_at, created_at
        FROM services
        ORDER BY id ASC
        """
    ) as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_service(db, service_id: int) -> dict | None:
    async with db.execute(
        """
        SELECT id, name, slug, health_url, owner, interval_seconds, slo_target,
               enabled, current_state, consecutive_failures, consecutive_successes,
               first_failure_at, next_check_at, created_at
        FROM services
        WHERE id = ?
        """,
        (service_id,),
    ) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None


async def create_service(db, data: ServiceCreate) -> dict:
    slug = data.slug or slugify(data.name)
    now_iso = clock.now().isoformat()

    # Check for duplicate name, slug, or health_url
    async with db.execute(
        "SELECT id FROM services WHERE name = ? OR slug = ? OR health_url = ?",
        (data.name, slug, data.health_url),
    ) as cursor:
        existing = await cursor.fetchone()
        if existing:
            raise ValueError("A service with this name, slug, or health URL already exists")

    cursor = await db.execute(
        """
        INSERT INTO services (
            name, slug, health_url, owner, interval_seconds, slo_target,
            enabled, current_state, consecutive_failures, consecutive_successes,
            next_check_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, 1, 'HEALTHY', 0, 0, ?, ?)
        """,
        (
            data.name,
            slug,
            data.health_url,
            data.owner,
            data.interval_seconds,
            data.slo_target,
            now_iso,
            now_iso,
        ),
    )
    await db.commit()
    service_id = cursor.lastrowid
    return await get_service(db, service_id)
