import uuid
from sqlalchemy import Column, Integer, String, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.db.models.base import Base

class Driver(Base):
    __tablename__ = "drivers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    driver_code = Column(String(3), nullable=False)  # e.g. VER, HAM
    full_name = Column(String, nullable=False)
    team = Column(String, nullable=False)
    season = Column(Integer, nullable=False)

    # Relationships
    stints = relationship("Stint", back_populates="driver", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_drivers_code_season', 'driver_code', 'season', unique=True),
    )
