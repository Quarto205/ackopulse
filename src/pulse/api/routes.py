from fastapi import APIRouter, HTTPException, status
from src.pulse.db import get_db
from src.pulse.services import (
    ServiceCreate,
    ServiceResponse,
    create_service,
    get_service,
    list_services,
)

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/services", response_model=list[ServiceResponse])
async def api_list_services():
    async with get_db() as db:
        return await list_services(db)


@router.post("/services", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
async def api_create_service(service_in: ServiceCreate):
    async with get_db() as db:
        try:
            new_service = await create_service(db, service_in)
            return new_service
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(err),
            )


@router.get("/services/{service_id}", response_model=ServiceResponse)
async def api_get_service(service_id: int):
    async with get_db() as db:
        service = await get_service(db, service_id)
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Service with id {service_id} not found",
            )
        return service


@router.get("/metrics/summary")
async def api_metrics_summary():
    """Per-service availability, budget, MTTD, MTTR (D-25/26/27)."""
    from src.pulse.metrics.calc import service_metrics
    async with get_db() as db:
        async with db.execute(
            "SELECT id, name, current_state, slo_target FROM services ORDER BY id"
        ) as cur:
            rows = [dict(zip(("id", "name", "current_state", "slo_target"), r))
                    for r in await cur.fetchall()]
        metrics = [await service_metrics(db, row) for row in rows]
    return {"services": metrics}
