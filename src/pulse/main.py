import asyncio
from contextlib import asynccontextmanager

import aiosqlite
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from src.pulse.api.routes import router as api_router
from src.pulse.checker.scheduler import Scheduler
from src.pulse.config import settings
from src.pulse.db import init_db
from src.pulse.seed import seed_services
from src.pulse.web.operator import router as operator_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schema and seed initial services
    await init_db()
    await seed_services()

    # U2: background check loop (D-12/D-14); skipped runs counted (D-13)
    scheduler = Scheduler()
    app.state.scheduler = scheduler

    async def loop():
        while True:
            try:
                async with aiosqlite.connect(str(settings.db_path)) as db:
                    await scheduler.run_once(db)
            except Exception:
                pass
            await asyncio.sleep(1.0)

    task = asyncio.create_task(loop())
    yield
    task.cancel()


app = FastAPI(
    title="Pulse - Service Status & Incident Hub",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(api_router)
app.include_router(operator_router)


@app.get("/", include_in_schema=False)
async def root_redirect():
    """Redirect root / to operator dashboard per D-20."""
    return RedirectResponse(url="/ops", status_code=307)


@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok"}
