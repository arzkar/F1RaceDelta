import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.db.models.base import Base

class Race(Base):
    __tablename__ = "races"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    season = Column(Integer, nullable=False)
    grand_prix = Column(String, nullable=False)
    circuit = Column(String, nullable=False)
    circuit_length_km = Column(Float, nullable=False)
    total_laps = Column(Integer, nullable=False)
    race_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    stints = relationship("Stint", back_populates="race", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_races_season_grand_prix', 'season', 'grand_prix', unique=True),
    )
