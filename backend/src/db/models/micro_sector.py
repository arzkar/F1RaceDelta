import uuid
from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.db.models.base import Base

class MicroSector(Base):
    __tablename__ = "micro_sectors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lap_id = Column(UUID(as_uuid=True), ForeignKey("laps.id"), nullable=False)
    corner_number = Column(Integer, nullable=False)
    entry_speed_kmh = Column(Float, nullable=True)
    apex_speed_kmh = Column(Float, nullable=True)
    exit_speed_kmh = Column(Float, nullable=True)

    # Relationships
    lap = relationship("Lap", back_populates="micro_sectors")
