from pathlib import Path
from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.pulse.clock import clock
from src.pulse.db import get_db
from src.pulse.services import ServiceCreate, create_service, list_services
from src.pulse.state.incidents import (
    acknowledge_incident,
    add_incident_note,
    get_incident_timeline,
)

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(prefix="/ops", tags=["operator"])


@router.get("", response_class=HTMLResponse)
async def operator_dashboard(request: Request):
    """Operator dashboard showing services, recent latencies, and active/resolved incidents."""
    now_utc_str = clock.now().strftime("%Y-%m-%d %H:%M:%S")

    async with get_db() as db:
        raw_services = await list_services(db)
        services = []
        recent_n = 5

        for s in raw_services:
            # Query the latest recent_n checks in chronological order
            async with db.execute(
                """
                SELECT id, latency_ms, state, checked_at
                FROM (
                    SELECT id, latency_ms, state, checked_at
                    FROM health_checks
                    WHERE service_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                )
                ORDER BY id ASC
                """,
                (s["id"], recent_n),
            ) as cursor:
                checks = [dict(r) for r in await cursor.fetchall()]

            latest_latency = checks[-1]["latency_ms"] if checks else None
            services.append(
                {
                    **s,
                    "latest_latency": latest_latency,
                    "recent_checks": checks,
                }
            )

        # Active incidents first
        async with db.execute(
            """
            SELECT i.id, i.service_id, i.opened_at, i.status, i.acknowledged_at,
                   i.acknowledged_by, i.title, s.name as service_name
            FROM incidents i
            JOIN services s ON s.id = i.service_id
            WHERE i.status = 'active'
            ORDER BY i.id DESC
            """
        ) as cursor:
            active_incidents = [dict(r) for r in await cursor.fetchall()]

        # Resolved incidents
        async with db.execute(
            """
            SELECT i.id, i.service_id, i.opened_at, i.resolved_at, i.status,
                   i.acknowledged_at, i.acknowledged_by, i.title, s.name as service_name
            FROM incidents i
            JOIN services s ON s.id = i.service_id
            WHERE i.status = 'resolved'
            ORDER BY i.id DESC
            LIMIT 20
            """
        ) as cursor:
            resolved_incidents = [dict(r) for r in await cursor.fetchall()]

    return templates.TemplateResponse(
        request=request,
        name="operator/dashboard.html",
        context={
            "services": services,
            "recent_n": recent_n,
            "active_incidents": active_incidents,
            "resolved_incidents": resolved_incidents,
            "now_utc": now_utc_str,
            "auto_refresh": True,
        },
    )


@router.get("/services/new", response_class=HTMLResponse)
async def new_service_form(request: Request):
    """Renders the service registration form."""
    now_utc_str = clock.now().strftime("%Y-%m-%d %H:%M:%S")
    return templates.TemplateResponse(
        request=request,
        name="operator/service_form.html",
        context={"now_utc": now_utc_str, "error": None},
    )


@router.post("/services/new")
async def create_service_from_form(
    request: Request,
    name: str = Form(...),
    slug: str = Form(None),
    health_url: str = Form(...),
    owner: str = Form(...),
    interval_seconds: int = Form(10),
    slo_target: float = Form(99.9),
):
    """Handles service registration form submission."""
    try:
        service_in = ServiceCreate(
            name=name,
            slug=slug if slug and slug.strip() else None,
            health_url=health_url,
            owner=owner,
            interval_seconds=interval_seconds,
            slo_target=slo_target,
        )
        async with get_db() as db:
            await create_service(db, service_in)
        return RedirectResponse(url="/ops", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as err:
        now_utc_str = clock.now().strftime("%Y-%m-%d %H:%M:%S")
        return templates.TemplateResponse(
            request=request,
            name="operator/service_form.html",
            context={"now_utc": now_utc_str, "error": str(err)},
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@router.get("/incidents/{incident_id}", response_class=HTMLResponse)
async def incident_detail(request: Request, incident_id: int):
    """Incident detail view showing status and event timeline."""
    now_utc_str = clock.now().strftime("%Y-%m-%d %H:%M:%S")
    async with get_db() as db:
        async with db.execute(
            """
            SELECT i.id, i.service_id, i.opened_at, i.resolved_at, i.status,
                   i.acknowledged_at, i.acknowledged_by, i.title, s.name as service_name
            FROM incidents i
            JOIN services s ON s.id = i.service_id
            WHERE i.id = ?
            """,
            (incident_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Incident not found")
            incident = dict(row)

        timeline = await get_incident_timeline(db, incident_id)

    return templates.TemplateResponse(
        request=request,
        name="operator/incident.html",
        context={
            "incident": incident,
            "timeline": timeline,
            "now_utc": now_utc_str,
            "auto_refresh": False,
        },
    )


@router.post("/incidents/{incident_id}/acknowledge")
async def acknowledge_incident_route(
    incident_id: int, acknowledged_by: str = Form("operator")
):
    """Acknowledge action endpoint."""
    async with get_db() as db:
        try:
            await acknowledge_incident(db, incident_id, acknowledged_by=acknowledged_by)
            return RedirectResponse(
                url=f"/ops/incidents/{incident_id}",
                status_code=status.HTTP_303_SEE_OTHER,
            )
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.post("/incidents/{incident_id}/notes")
async def add_note_route(incident_id: int, note: str = Form(...)):
    """Add-note action endpoint."""
    if not note or not note.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Note cannot be empty")

    async with get_db() as db:
        try:
            await add_incident_note(db, incident_id, note=note)
            return RedirectResponse(
                url=f"/ops/incidents/{incident_id}",
                status_code=status.HTTP_303_SEE_OTHER,
            )
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
