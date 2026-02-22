import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.db.models.base import Base

class Stint(Base):
    __tablename__ = "stints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    race_id = Column(UUID(as_uuid=True), ForeignKey("races.id"), nullable=False)
    driver_id = Column(UUID(as_uuid=True), ForeignKey("drivers.id"), nullable=False)
    compound = Column(String, nullable=False)  # SOFT, MEDIUM, HARD, INTERMEDIATE, WET
    start_lap = Column(Integer, nullable=False)
    end_lap = Column(Integer, nullable=False)
    stint_length = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    race = relationship("Race", back_populates="stints")
    driver = relationship("Driver", back_populates="stints")
    laps = relationship("Lap", back_populates="stint", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_stints_race_driver_start', 'race_id', 'driver_id', 'start_lap', unique=True),
        Index('ix_stints_race_id', 'race_id'),
        Index('ix_stints_driver_id', 'driver_id'),
        Index('ix_stints_compound', 'compound'),
    )
