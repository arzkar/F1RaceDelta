from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from typing import List
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID

from src.db.session import get_db
from src.db.models.race import Race
from src.db.models.driver import Driver
from src.db.models.stint import Stint

router = APIRouter()

# --- Response Schemas ---

class RaceBase(BaseModel):
    id: UUID
    season: int
    grand_prix: str
    circuit: str
    circuit_length_km: float
    total_laps: int
    race_date: datetime

    model_config = ConfigDict(from_attributes=True)

class DriverBase(BaseModel):
    driver_code: str
    full_name: str
    team: str
    season: int

    model_config = ConfigDict(from_attributes=True)

class StintBase(BaseModel):
    compound: str
    start_lap: int
    end_lap: int
    stint_length: int
    driver_code: str

    model_config = ConfigDict(from_attributes=True)

# --- Routes ---

@router.get("/seasons", response_model=List[int])
def get_seasons(db: Session = Depends(get_db)):
    """Returns a list of all distinct F1 seasons currently available in the database."""
    # Since season is an integer, we ask distinct over it
    seasons = db.execute(select(Race.season).distinct()).scalars().all()
    # Sort descending (newest first)
    return sorted(seasons, reverse=True)

@router.get("/seasons/{year}/races", response_model=List[RaceBase])
def get_races(year: int, db: Session = Depends(get_db)):
    """Returns all races for a specific season, ordered chronologically."""
    races = db.execute(select(Race).where(Race.season == year).order_by(Race.race_date)).scalars().all()
    if not races:
        raise HTTPException(status_code=404, detail=f"No races found for season {year}")
    return races

@router.get("/races/{race_id}/drivers", response_model=List[DriverBase])
def get_race_drivers(race_id: str, db: Session = Depends(get_db)):
    """Returns the grid of drivers that participated in a specific race by joining stints."""
    race = db.get(Race, race_id)
    if not race:
        raise HTTPException(status_code=404, detail="Race not found")

    drivers = db.execute(
        select(Driver).join(Stint).where(Stint.race_id == race_id).distinct()
    ).scalars().all()

    return drivers

@router.get("/races/{race_id}/stints", response_model=List[StintBase])
def get_race_stints(race_id: str, db: Session = Depends(get_db)):
    """
    Returns the complete pit strategy history for the race.
    Flattened to include the driver_code string directly in the Pydantic schema
    for easy frontend rendering (e.g. 'VER: SOFT (1-15) -> HARD (16-52)').
    """
    race = db.get(Race, race_id)
    if not race:
        raise HTTPException(status_code=404, detail="Race not found")

    stints = db.execute(
        select(Stint, Driver.driver_code)
        .join(Driver, Stint.driver_id == Driver.id)
        .where(Stint.race_id == race_id)
        .order_by(Driver.driver_code, Stint.start_lap)
    ).all()

    # We map the raw tuple from SQLAlchemy directly to the flattened Pydantic model
    return [
        StintBase(
            compound=st.compound,
            start_lap=st.start_lap,
            end_lap=st.end_lap,
            stint_length=st.stint_length,
            driver_code=dc
        )
        for st, dc in stints
    ]
