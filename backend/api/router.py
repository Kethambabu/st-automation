"""
AI Test Platform — Root API Router

Aggregates all versioned API routers into a single router for the application.
"""

from fastapi import APIRouter

from api.v1 import upload, projects, tests, results, analysis, review, generation

# ── Create the root API router ─────────────────────────
api_router = APIRouter(prefix="/api/v1")

# ── Include all v1 routers ─────────────────────────────
api_router.include_router(upload.router)
api_router.include_router(projects.router)
api_router.include_router(tests.router)
api_router.include_router(results.router)
api_router.include_router(analysis.router)
api_router.include_router(review.router)
api_router.include_router(generation.router)

