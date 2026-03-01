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
from src.domain.monte_carlo import HeadToHeadSimulator, MonteCarloConfig

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
    iterations: int = Field(..., gt=0, le=10000, description="Cannot exceed 10,000 to protect Railway CPU quota.")
    total_laps: int = Field(..., gt=0, le=100, description="A standard F1 race does not exceed ~78 laps.")
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

# --- Strategy Simulation Schemas ---

class StrategyStint(BaseModel):
    compound: str = Field(..., description="SOFT, MEDIUM, or HARD")
    laps: int = Field(..., gt=0, le=100)

class StrategyRequest(BaseModel):
    race_id: str
    baseline_lap_time_s: float = Field(85.0, gt=60.0, le=120.0)
    starting_fuel_kg: float = Field(110.0, gt=0.0, le=150.0)
    stints: List[StrategyStint] = Field(..., min_length=1, max_length=5)

class StrategyLapResult(BaseModel):
    lap_number: int
    simulated_time_s: float
    tyre_wear: float
    fuel_mass_kg: float
    compound: str

class StrategyResponse(BaseModel):
    total_laps_simulated: int
    race_total_laps: int
    circuit: str
    circuit_length_km: float
    laps: List[StrategyLapResult]
    pit_laps: List[int]

# Default degradation parameters when no calibrated model exists
_DEFAULT_DEG = {
    "SOFT":   {"alpha": 0.08, "base_wear_rate": 0.04, "cliff_threshold": 0.7,  "beta": 0.3,  "gamma": 1.5},
    "MEDIUM": {"alpha": 0.05, "base_wear_rate": 0.03, "cliff_threshold": 0.85, "beta": 0.25, "gamma": 1.3},
    "HARD":   {"alpha": 0.03, "base_wear_rate": 0.02, "cliff_threshold": 1.0,  "beta": 0.2,  "gamma": 1.1},
}

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
    mc_config = MonteCarloConfig(
        iterations=req.iterations,
        degradation_variance_percent=0.05,
        dirty_air_penalty_seconds=0.8,
        overtake_delta_threshold_seconds=0.5,
        gap_threshold_seconds=1.0
    )

    simulator = HeadToHeadSimulator(
        driver_a_code=req.driver_a_id,
        driver_a_deg=phys_deg_a,
        driver_a_fuel=phys_fuel,
        driver_b_code=req.driver_b_id,
        driver_b_deg=phys_deg_b,
        driver_b_fuel=phys_fuel,
        config=mc_config
    )

    # 4. Trigger Execution
    # We assign Driver A and Driver B theoretical baseline lap times.
    # We deduct tyre age offset if present.
    base_lap = 85.0

    # Starting offset physics (simulated tyre age wear pre-applied to the baseline pace)
    base_lap_a = base_lap + (req.starting_wear_laps_a * phys_deg_a.base_wear_rate)
    base_lap_b = base_lap + (req.starting_wear_laps_b * phys_deg_b.base_wear_rate)

    results = simulator.run_monte_carlo(
        base_lap_a=base_lap_a,
        base_lap_b=base_lap_b,
        total_laps=req.total_laps,
        start_gap_ab=req.starting_gap_s
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
        driver_a_win_pct=results.get("win_probability_a", 0.0),
        driver_b_win_pct=results.get("win_probability_b", 0.0),
        mean_gap_at_flag_s=0.0
    )


@router.post("/strategy", response_model=StrategyResponse)
def simulate_strategy(req: StrategyRequest, db: Session = Depends(get_db)):
    """
    Deterministic race strategy simulator.
    Runs the calibrated DeterministicSimulator for each stint sequentially,
    preserving fuel state across pit stops.
    """
    from src.domain.physics import DegradationModel as PhysicsDeg, FuelModel as PhysicsFuel
    from src.domain.calibration import DeterministicSimulator

    # 1. Fetch race metadata
    race = db.get(Race, req.race_id)
    if not race:
        raise HTTPException(status_code=404, detail="Race not found")

    circuit_length_km = race.circuit_length_km or 5.0  # safe fallback

    # 2. Resolve degradation models per compound
    def get_deg_params(compound: str) -> dict:
        """Fetch calibrated params from DB, fall back to defaults."""
        db_model = db.execute(
            select(DegradationModel).where(
                and_(
                    DegradationModel.season == race.season,
                    DegradationModel.track_id == race.circuit,
                    DegradationModel.compound == compound
                )
            )
        ).scalar_one_or_none()

        if db_model:
            return {
                "alpha": db_model.alpha,
                "base_wear_rate": db_model.base_wear_rate,
                "cliff_threshold": db_model.cliff_threshold,
                "beta": db_model.beta,
                "gamma": db_model.gamma,
                "fuel_per_km": db_model.fuel_per_km,
                "fuel_time_penalty_per_kg": db_model.fuel_time_penalty_per_kg,
            }

        defaults = _DEFAULT_DEG.get(compound, _DEFAULT_DEG["MEDIUM"])
        return {
            **defaults,
            "fuel_per_km": 0.06,
            "fuel_time_penalty_per_kg": 0.035,
        }

    # 3. Run simulation stint-by-stint
    all_laps: List[StrategyLapResult] = []
    pit_laps: List[int] = []
    current_fuel_kg = req.starting_fuel_kg
    current_lap = 1

    for i, stint in enumerate(req.stints):
        params = get_deg_params(stint.compound)

        deg_model = PhysicsDeg(
            track_name=race.circuit,
            compound=stint.compound,
            base_wear_rate=params["base_wear_rate"],
            alpha=params["alpha"],
            cliff_threshold=params["cliff_threshold"],
            beta=params["beta"],
            gamma=params["gamma"],
        )
        fuel_model = PhysicsFuel(
            track_length_km=circuit_length_km,
            fuel_per_km_kg=params["fuel_per_km"],
            fuel_time_penalty_per_kg=params["fuel_time_penalty_per_kg"],
        )

        simulator = DeterministicSimulator(
            degradation_model=deg_model,
            fuel_model=fuel_model,
            starting_fuel_kg=current_fuel_kg,
            starting_wear=0.0,  # Fresh tyres after each pit stop
        )

        end_lap = current_lap + stint.laps - 1
        stint_laps = simulator.run_stint(
            baseline_lap_time_s=req.baseline_lap_time_s,
            start_lap=current_lap,
            end_lap=end_lap,
        )

        for sl in stint_laps:
            all_laps.append(StrategyLapResult(
                lap_number=sl.lap_number,
                simulated_time_s=round(sl.simulated_time_s, 3),
                tyre_wear=round(sl.tyre_wear, 4),
                fuel_mass_kg=round(sl.fuel_mass_kg, 2),
                compound=stint.compound,
            ))

        # Carry fuel state across pit stops
        current_fuel_kg = simulator.current_fuel_kg
        current_lap = end_lap + 1

        # Record the lap this stint starts on (pit stop happened just before, except first stint)
        if i > 0:
            pit_laps.append(stint_laps[0].lap_number)

    return StrategyResponse(
        total_laps_simulated=len(all_laps),
        race_total_laps=race.total_laps or 0,
        circuit=race.circuit,
        circuit_length_km=circuit_length_km,
        laps=all_laps,
        pit_laps=pit_laps,
    )
