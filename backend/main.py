"""
AI Test Platform — FastAPI Application Entrypoint

This is the main application file that wires everything together.
Run with: uvicorn main:app --reload
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from models.base import init_db
from api.router import api_router
from utils.logger import setup_logging, get_logger


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager."""
    # ── Startup ────────────────────────────────────────
    setup_logging()
    logger = get_logger("main")
    logger.info("Starting AI Test Platform", env=settings.APP_ENV)

    # Create storage directories
    settings.ensure_directories()

    # Initialize database tables
    await init_db()
    logger.info("Database initialized")

    yield

    # ── Shutdown ───────────────────────────────────────
    logger.info("Shutting down AI Test Platform")


# ── Create FastAPI Application ─────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "AI-powered platform for autonomous test generation and execution. "
        "Upload your project, and let AI agents analyze your code, "
        "generate comprehensive test suites, and execute them."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS Middleware ────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount API Router ──────────────────────────────────
app.include_router(api_router)


# ── Health Check ──────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    """Liveness / readiness probe."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.APP_ENV,
    }


@app.get("/", tags=["System"])
async def root():
    """Root endpoint — API information."""
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
