"""Public read-only status page under /status (U5).

Separate prefix from /ops; separate data model (public_model) so private
fields can never leak (D-10). GET-only.
"""
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.pulse.db import get_db
from src.pulse.web.public_model import public_snapshot

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(prefix="/status", tags=["public"])


@router.get("", response_class=HTMLResponse)
async def public_status(request: Request):
    async with get_db() as db:
        snapshot = await public_snapshot(db)
    return templates.TemplateResponse(
        request,
        "public/status.html",
        {
            "services": snapshot["services"],
            "incidents": snapshot["incidents"],
        },
    )
