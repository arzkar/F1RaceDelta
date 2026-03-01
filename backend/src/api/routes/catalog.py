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


# --- Race Pace ---

class DriverPace(BaseModel):
    driver_code: str
    computed_pace_s: float
    races_used: int

class RacePaceResponse(BaseModel):
    race_id: str
    race_round: int
    lookback_races: int
    driver_paces: List[DriverPace]


@router.get("/race-pace/{season}/{race_id}", response_model=RacePaceResponse)
def get_race_pace(season: int, race_id: str, db: Session = Depends(get_db)):
    """
    Computes each driver's rolling baseline pace from the preceding 1–5 races.
    Uses per-race median lap time (filtering outliers > 130% of best) then averages
    across the lookback window.
    """
    from sqlalchemy import func, text as sa_text
    from src.db.models.lap import Lap

    # 1. Build race calendar order
    all_races = db.execute(
        select(Race).where(Race.season == season).order_by(Race.race_date)
    ).scalars().all()

    race_index = {str(r.id): i for i, r in enumerate(all_races)}
    if race_id not in race_index:
        raise HTTPException(status_code=404, detail="Race not found in this season")

    current_round = race_index[race_id]  # 0-indexed

    # 2. Determine lookback window (up to 5 preceding races)
    lookback_start = max(0, current_round - 5)
    lookback_races = all_races[lookback_start:current_round]

    if not lookback_races:
        # First race — no prior data, return empty (frontend uses 85.0 default)
        return RacePaceResponse(
            race_id=race_id, race_round=current_round + 1,
            lookback_races=0, driver_paces=[]
        )

    lookback_ids = [r.id for r in lookback_races]

    # 3. Query all valid laps from the lookback races
    rows = db.execute(
        select(
            Lap.race_id,
            Driver.driver_code,
            Lap.lap_time_seconds,
        )
        .join(Driver, Lap.driver_id == Driver.id)
        .where(
            Lap.race_id.in_(lookback_ids),
            Lap.lap_time_seconds.isnot(None),
        )
        .order_by(Driver.driver_code, Lap.race_id, Lap.lap_time_seconds)
    ).all()

    # 4. Find the fastest lap per lookback race (for outlier filtering)
    fastest_per_race: dict[str, float] = {}
    for race_id_val, _dc, lap_time in rows:
        rid = str(race_id_val)
        if rid not in fastest_per_race or lap_time < fastest_per_race[rid]:
            fastest_per_race[rid] = lap_time

    # 5. Group clean laps by (driver, race) → compute per-race median
    import statistics
    driver_race_laps: dict[str, dict[str, list[float]]] = {}

    for race_id_val, dc, lap_time in rows:
        rid = str(race_id_val)
        # Filter outlier laps: > 130% of the race's fastest lap
        threshold = fastest_per_race.get(rid, 999) * 1.3
        if lap_time > threshold:
            continue

        driver_race_laps.setdefault(dc, {}).setdefault(rid, []).append(lap_time)

    # 6. Per driver: median of each race → average of medians
    driver_paces: List[DriverPace] = []

    for dc, race_laps in sorted(driver_race_laps.items()):
        medians = []
        for rid, laps in race_laps.items():
            if len(laps) >= 3:  # need at least 3 clean laps for a meaningful median
                medians.append(statistics.median(laps))

        if medians:
            avg_pace = round(sum(medians) / len(medians), 3)
            driver_paces.append(DriverPace(
                driver_code=dc, computed_pace_s=avg_pace, races_used=len(medians)
            ))

    # Sort by pace (fastest first)
    driver_paces.sort(key=lambda d: d.computed_pace_s)

    return RacePaceResponse(
        race_id=race_id,
        race_round=current_round + 1,
        lookback_races=len(lookback_races),
        driver_paces=driver_paces,
    )
