"""
AI Test Platform — Test Case Model
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class TestCase(Base):
    """Represents an AI-generated test case."""

    __tablename__ = "test_cases"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    target_file: Mapped[str] = mapped_column(String(500), nullable=False)
    target_function: Mapped[str] = mapped_column(String(255), nullable=False)
    test_type: Mapped[str] = mapped_column(
        String(30), default="unit", comment="unit | integration | edge_case"
    )
    test_code: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="GENERATED", comment="GENERATED | REVIEWED | APPROVED | FAILED"
    )
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    project = relationship("Project", back_populates="test_cases")
    results = relationship("TestResult", back_populates="test_case", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<TestCase(id={self.id}, target={self.target_function}, status={self.status})>"
