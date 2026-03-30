"""
AI Test Platform — Shared API Dependencies
"""

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from models.base import get_db


async def get_database_session(
    db: AsyncSession = Depends(get_db),
) -> AsyncSession:
    """Inject a database session into route handlers."""
    return db
