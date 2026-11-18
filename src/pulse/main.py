from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.pulse.api.routes import router as api_router
from src.pulse.config import settings
from src.pulse.db import init_db
from src.pulse.seed import seed_services


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schema and seed initial services
    await init_db()
    await seed_services()
    yield


app = FastAPI(
    title="Pulse - Service Status & Incident Hub",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(api_router)


@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok"}
