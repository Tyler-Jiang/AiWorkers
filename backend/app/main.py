"""AI Game Studio — FastAPI 入口（SQLite + Stage D/E）。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import SessionLocal, init_db
from app.routes import router as studio_router
from app.seed import ensure_studio_meta, seed_if_empty


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        seed_if_empty(db)
        ensure_studio_meta(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="AI Game Studio API",
    version="0.4.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
    ],
    allow_origin_regex=r"^https?://(127\.0\.0\.1|localhost)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(studio_router, prefix="/api", tags=["studio"])


@app.get("/")
def root() -> dict[str, str | dict[str, str]]:
    """根路径仅作说明；控制台请用前端 dev server（默认 5174）。"""
    return {
        "service": "AI Game Studio API",
        "hint": "浏览器里请打开前端 http://127.0.0.1:5174 ；本地址是 JSON API。",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "scene": "/api/scene",
            "requirements": "/api/requirements",
            "producer_plan": "/api/producer/generate-plan",
            "agent_invoke": "/api/agents/{agent_id}/invoke",
            "computer_request": "/api/computer/request",
            "computer_release": "/api/computer/release",
            "webhook": "/api/webhooks/cursor",
        },
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
