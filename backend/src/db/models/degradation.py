import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID

from src.db.models.base import Base

class DegradationModel(Base):
    __tablename__ = "degradation_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Granularity: (Season, Track, Compound)
    season = Column(Integer, nullable=False)
    track_id = Column(String, nullable=False)
    compound = Column(String, nullable=False)

    # Stage 2: Linear Degradation Parameters
    alpha = Column(Float, nullable=False)
    base_wear_rate = Column(Float, nullable=False)

    # Stage 3: Cliff Parameters
    cliff_threshold = Column(Float, nullable=False)
    beta = Column(Float, nullable=False)
    gamma = Column(Float, nullable=False)

    # Stage 1: Fuel Fit Parameters
    fuel_per_km = Column(Float, nullable=False)
    fuel_time_penalty_per_kg = Column(Float, nullable=False)

    # Calibration Meta Metrics
    rmse_score = Column(Float, nullable=False)
    mae_score = Column(Float, nullable=False)
    r_squared = Column(Float, nullable=False)
    sample_count = Column(Integer, nullable=False)
    calibration_timestamp = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('ix_deg_models_season_track_compound', 'season', 'track_id', 'compound', unique=True),
    )
