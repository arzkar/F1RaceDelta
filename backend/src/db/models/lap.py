import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.db.models.base import Base

class Lap(Base):
    __tablename__ = "laps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    race_id = Column(UUID(as_uuid=True), ForeignKey("races.id"), nullable=False)
    driver_id = Column(UUID(as_uuid=True), ForeignKey("drivers.id"), nullable=False)
    stint_id = Column(UUID(as_uuid=True), ForeignKey("stints.id"), nullable=False)
    lap_number = Column(Integer, nullable=False)
    lap_time_seconds = Column(Float, nullable=True)  # Might be null on out-laps/DNFs
    sector_1_seconds = Column(Float, nullable=True)
    sector_2_seconds = Column(Float, nullable=True)
    sector_3_seconds = Column(Float, nullable=True)
    track_status = Column(String, nullable=True)
    is_green_flag = Column(Boolean, nullable=False, default=True)
    fuel_estimate_kg = Column(Float, nullable=True)
    telemetry_file_path = Column(String, nullable=True)  # Pointer to S3/R2 .parquet file
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    race = relationship("Race")
    driver = relationship("Driver")
    stint = relationship("Stint", back_populates="laps")
    micro_sectors = relationship("MicroSector", back_populates="lap", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_laps_race_driver_lap', 'race_id', 'driver_id', 'lap_number', unique=True),
        Index('ix_laps_stint_id', 'stint_id'),
        Index('ix_laps_lap_number', 'lap_number'),
    )
