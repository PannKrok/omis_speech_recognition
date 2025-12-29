from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.domain.models import Device, DeviceType
from app.domain.repositories import InMemoryStore
from app.routers.api import build_router
from app.services.pipeline import Pipeline
from app.services.utils import new_id


BASE_DIR = Path(__file__).resolve().parent
UI_DIR = BASE_DIR / "ui"
TEMPLATES_DIR = UI_DIR / "templates"
STATIC_DIR = UI_DIR / "static"


def create_app() -> FastAPI:
    app = FastAPI(title="Speech Control Prototype")

    # In-memory store
    store = InMemoryStore()

    # Preload devices (as in UI mockups)
    store.devices = {
        "dev_thermo": Device(id="dev_thermo", name="Умный термостат", type=DeviceType.THERMOSTAT, is_on=False, value=22),
        "dev_vac": Device(id="dev_vac", name="Робот-пылесос", type=DeviceType.VACUUM, is_on=False),
        "dev_cam": Device(id="dev_cam", name="Камера безопасности", type=DeviceType.CAMERA, is_on=False),
        "dev_coffee": Device(id="dev_coffee", name="Кофемашина", type=DeviceType.COFFEE, is_on=False),
        "dev_light": Device(id="dev_light", name="Умный свет", type=DeviceType.LIGHT, is_on=False),
        "dev_ac": Device(id="dev_ac", name="Кондиционер", type=DeviceType.AC, is_on=False, value=24),
        "dev_tv": Device(id="dev_tv", name="Телевизор", type=DeviceType.TV, is_on=False),
    }

    pipeline = Pipeline(store)

    # API
    app.include_router(build_router(store, pipeline))

    # UI
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        # Render initial HTML; all dynamic updates happen via JS calls to /api/*
        return templates.TemplateResponse("index.html", {"request": request})

    return app


app = create_app()
