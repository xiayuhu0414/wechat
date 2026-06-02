from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.db import init_db
from app.routers import autoreply, contacts, customers, files, messages, moments, settings as settings_router, tasks, wechat
from app.services.uia_enhancer import uia_enhancer
from app.tasks.manager import task_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_dirs()
    init_db()
    uia_enhancer.configure_from_settings()
    await task_manager.start()
    yield
    await task_manager.stop()
    uia_enhancer.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(wechat.router)
app.include_router(messages.router)
app.include_router(files.router)
app.include_router(customers.router)
app.include_router(contacts.router)
app.include_router(autoreply.router)
app.include_router(moments.router)
app.include_router(settings_router.router)
app.include_router(tasks.router)
app.include_router(tasks.ws_router)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "name": settings.app_name}


if settings.frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=settings.frontend_dist / "assets"), name="assets")


@app.get("/{path:path}")
def serve_frontend(path: str):
    index = settings.frontend_dist / "index.html"
    if index.exists():
        return FileResponse(index)
    return {
        "message": "autoWechat API is running. Build the frontend with `npm run build` in frontend/.",
        "docs": "/docs",
    }
