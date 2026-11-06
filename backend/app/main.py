import asyncio
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging

from app.config import settings
from app.database import engine, Base
from app.migrate_db import migrate_database
from app.routers import cameras, analytics, alerts, recommendations, events, reports, websocket, venue_map, emergency, staff, auth, heatmap, settings as settings_router

# Create database tables automatically on startup and synchronize missing columns
Base.metadata.create_all(bind=engine)
migrate_database()

# Ensure uploads directories exist
UPLOAD_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
MAPS_DIR = os.path.join(UPLOAD_ROOT, "maps")
VIDEOS_DIR = os.path.join(UPLOAD_ROOT, "videos")
os.makedirs(MAPS_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Real-time Computer Vision Crowd Safety System API",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static file directory for serving uploaded floorplans and videos
app.mount("/static", StaticFiles(directory=UPLOAD_ROOT), name="static")

# Register REST Routers under /api
app.include_router(cameras.router, prefix=settings.API_PREFIX)
app.include_router(analytics.router, prefix=settings.API_PREFIX)
app.include_router(alerts.router, prefix=settings.API_PREFIX)
app.include_router(recommendations.router, prefix=settings.API_PREFIX)
app.include_router(events.router, prefix=settings.API_PREFIX)
app.include_router(venue_map.router, prefix=settings.API_PREFIX)
app.include_router(emergency.router, prefix=settings.API_PREFIX)
app.include_router(staff.router, prefix=settings.API_PREFIX)
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(settings_router.router, prefix=settings.API_PREFIX)
app.include_router(reports.router, prefix=settings.API_PREFIX)
app.include_router(heatmap.router, prefix=settings.API_PREFIX)

# Register WebSockets Router
app.include_router(websocket.router)

@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI Backend Server initialized.")
    from app.ai.ingestion_manager import ingestion_coordinator
    if ingestion_coordinator.acquire_ownership():
        logger.info(f"[INGESTION][LEADER] Acquired camera ingestion lock (PID: {os.getpid()}). Starting background AI WebSockets ingestion loop...")
        asyncio.create_task(websocket.start_ai_processing_loop())
    else:
        owner_pid = ingestion_coordinator.get_owner_pid()
        pid_str = f"PID {owner_pid}" if owner_pid is not None else "unknown PID (lock held by active owner)"
        logger.info(f"[INGESTION][FOLLOWER] Ingestion lock already held by {pid_str}. Running in API-only worker mode (PID: {os.getpid()}).")

@app.on_event("shutdown")
async def shutdown_event():
    from app.ai.ingestion_manager import ingestion_coordinator
    if ingestion_coordinator.is_owner:
        logger.info(f"[INGESTION][SHUTDOWN] Releasing camera ingestion lock (PID: {os.getpid()})...")
        ingestion_coordinator.release_ownership()

@app.get("/")
def root():
    return {
        "status": "ONLINE",
        "system": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "websocket": "/ws/live"
    }
