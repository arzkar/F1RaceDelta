import time
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from pydantic import BaseModel, Field, ConfigDict

from src.db.session import get_db
from src.db.models.degradation import DegradationModel
from src.db.models.race import Race
from src.domain.monte_carlo import HeadToHeadSimulator, SimulatorConfig

logger = logging.getLogger(__name__)

router = APIRouter()

# --- Schemas ---

class DegradationModelBase(BaseModel):
    compound: str
    alpha: float
    base_wear_rate: float
    cliff_threshold: float
    beta: float
    gamma: float
    fuel_per_km: float
    fuel_time_penalty_per_kg: float
    rmse_score: float
    sample_count: int

    model_config = ConfigDict(from_attributes=True)

class MonteCarloRequest(BaseModel):
    race_id: str
    driver_a_id: str
    driver_b_id: str
    compound_a: str
    compound_b: str
    # Rate Limiting bounds inside the REST Payload directly
    iterations: int = Field(..., gt=0, le=10000, description="Cannot exceed 10,000 to protect Railway CPU quota.")
    total_laps: int = Field(..., gt=0, le=100, description="A standard F1 race does not exceed ~78 laps.")

    # Optional offsets for interactive strategy (e.g., Driver A's tyres are 10 laps older than Driver B)
    starting_wear_laps_a: int = 0
    starting_wear_laps_b: int = 0
    starting_gap_s: float = 0.0

class MonteCarloResponse(BaseModel):
    driver_a_code: str
    driver_b_code: str
    iterations_run: int
    duration_ms: float
    driver_a_win_pct: float
    driver_b_win_pct: float
    mean_gap_at_flag_s: float

# --- Routes ---

@router.get("/models/{season}/{track_id}", response_model=List[DegradationModelBase])
def get_calibrated_models(season: int, track_id: str, db: Session = Depends(get_db)):
    """
    Returns the explicitly calibrated deterministic physics constants (alpha, beta, cliff)
    for all available compounds (SOFT, MEDIUM, HARD) at this specific track in this given season.
    The frontend uses these to natively plot the curved degradation line.
    """
    models = db.execute(
        select(DegradationModel)
        .where(
            and_(
                DegradationModel.season == season,
                DegradationModel.track_id == track_id
            )
        )
    ).scalars().all()

    if not models:
        raise HTTPException(status_code=404, detail=f"No calibrated physics models exist for {season} {track_id}")

    return models

@router.post("/monte-carlo", response_model=MonteCarloResponse)
def execute_monte_carlo(req: MonteCarloRequest, db: Session = Depends(get_db)):
    """
    Blocking REST POST endpoint to run up to 10,000 Monte Carlo micro-simulations.
    Safeguards: Hard execution bounds, purely mathematical (no web sockets or streaming delay).
    """
    start = time.perf_counter()

    # 1. Fetch the Race metadata
    race = db.get(Race, req.race_id)
    if not race:
        raise HTTPException(status_code=404, detail="Race not found")

    # 2. Extract strictly calibrated Physics Constants from NeonDB
    deg_a = db.execute(select(DegradationModel).where(
        and_(DegradationModel.season == race.season, DegradationModel.track_id == race.circuit, DegradationModel.compound == req.compound_a)
    )).scalar_one_or_none()

    deg_b = db.execute(select(DegradationModel).where(
        and_(DegradationModel.season == race.season, DegradationModel.track_id == race.circuit, DegradationModel.compound == req.compound_b)
    )).scalar_one_or_none()

    if not deg_a or not deg_b:
        raise HTTPException(status_code=404, detail="Compound missing calibrated mathematics. Try running `calibrate_season.py` first.")

    # Convert NeonDB schemas back into our Mathematical Domain objects natively
    from src.domain.physics import DegradationModel as PhysicsDeg, FuelModel as PhysicsFuel

    phys_deg_a = PhysicsDeg(race.circuit, req.compound_a, deg_a.base_wear_rate, deg_a.alpha, deg_a.cliff_threshold, deg_a.beta, deg_a.gamma)
    phys_deg_b = PhysicsDeg(race.circuit, req.compound_b, deg_b.base_wear_rate, deg_b.alpha, deg_b.cliff_threshold, deg_b.beta, deg_b.gamma)

    phys_fuel = PhysicsFuel(race.circuit_length_km, deg_a.fuel_per_km, deg_a.fuel_time_penalty_per_kg)

    # 3. Instantiate the Mathematical Head to Head Engine
    config_a = SimulatorConfig(deg_model=phys_deg_a, starting_wear_laps=req.starting_wear_laps_a)
    config_b = SimulatorConfig(deg_model=phys_deg_b, starting_wear_laps=req.starting_wear_laps_b)

    simulator = HeadToHeadSimulator(
        driver_a_code=req.driver_a_id,
        driver_b_code=req.driver_b_id,
        fuel_model=phys_fuel,
        config_a=config_a,
        config_b=config_b,
        base_lap_time_s=85.0 # We approximate a baseline lap time, although it's delta that matters
    )

    # 4. Trigger Execution
    results = simulator.run_monte_carlo(
        iterations=req.iterations,
        laps=req.total_laps,
        starting_gap_s=req.starting_gap_s,
        base_variance_s=0.2 # Tightly bounded variance
    )

    duration_ms = (time.perf_counter() - start) * 1000.0

    # 5. Strict Structured JSON Logging for Monte Carlo
    logger.info(
        "Monte Carlo Simulator Completed",
        extra={
            "event": "monte_carlo_completed",
            "race_id": req.race_id,
            "driver_a_id": req.driver_a_id,
            "driver_b_id": req.driver_b_id,
            "iterations": req.iterations,
            "duration_ms": duration_ms
        }
    )

    return MonteCarloResponse(
        driver_a_code=req.driver_a_id,
        driver_b_code=req.driver_b_id,
        iterations_run=req.iterations,
        duration_ms=duration_ms,
        driver_a_win_pct=results["driver_a_win_pct"],
        driver_b_win_pct=results["driver_b_win_pct"],
        mean_gap_at_flag_s=results["final_gap_mean_s"]
    )
