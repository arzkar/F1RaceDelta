import argparse
import logging
from typing import List
from sqlalchemy import select, and_

from src.db.session import get_db
from src.db.models.race import Race
from src.db.models.degradation import DegradationModel
from src.calibration.truth_extractor import TruthExtractor
from src.calibration.optimizer import MathOptimizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

COMPOUNDS = ["SOFT", "MEDIUM", "HARD"]

def calibrate_circuit_compound(db, season: int, race: Race, compound: str) -> None:
    extractor = TruthExtractor(db)
    clean_segments = extractor.extract_clean_segments(season, race.circuit, compound)

    if not clean_segments:
        logger.warning(f"Skipping Calibration: [{race.circuit}] [{compound}] lacks sufficient green-flag data.")
        return

    optimizer = MathOptimizer(track_name=race.circuit, circuit_length_km=race.circuit_length_km, compound=compound)
    result = optimizer.optimize(clean_segments)

    if not result:
        logger.error(f"Optimizer failed to converge for [{race.circuit}] [{compound}]")
        return

    logger.info(f"Calibration Complete: [{race.circuit}] [{compound}] | RMSE: {result.rmse_score:.3f}s | Alpha: {result.alpha:.4f} | Samples: {result.sample_count}")

    # Upsert the result into the database
    existing_model = db.execute(
        select(DegradationModel).where(
            and_(
                DegradationModel.season == season,
                DegradationModel.track_id == race.circuit,
                DegradationModel.compound == compound
            )
        )
    ).scalar_one_or_none()

    if existing_model:
        existing_model.alpha = result.alpha
        existing_model.base_wear_rate = result.base_wear_rate
        existing_model.cliff_threshold = result.cliff_threshold
        existing_model.beta = result.beta
        existing_model.gamma = result.gamma
        existing_model.fuel_per_km = result.fuel_per_km
        existing_model.fuel_time_penalty_per_kg = result.fuel_time_penalty_per_kg
        existing_model.rmse_score = result.rmse_score
        existing_model.mae_score = result.mae_score
        existing_model.r_squared = result.r_squared
        existing_model.sample_count = result.sample_count
        logger.info(f"Updated existing model in DB for [{race.circuit}] [{compound}]")
    else:
        new_model = DegradationModel(
            season=season,
            track_id=race.circuit,
            compound=compound,
            alpha=result.alpha,
            base_wear_rate=result.base_wear_rate,
            cliff_threshold=result.cliff_threshold,
            beta=result.beta,
            gamma=result.gamma,
            fuel_per_km=result.fuel_per_km,
            fuel_time_penalty_per_kg=result.fuel_time_penalty_per_kg,
            rmse_score=result.rmse_score,
            mae_score=result.mae_score,
            r_squared=result.r_squared,
            sample_count=result.sample_count
        )
        db.add(new_model)
        logger.info(f"Inserted new model to DB for [{race.circuit}] [{compound}]")

    db.commit()

def calibrate_season(season: int):
    """
    Iterates over every race in the database for the given season.
    Extracts all Truth Data per compound and optimizes it deterministically.
    """
    db = next(get_db())
    try:
        races = db.execute(select(Race).where(Race.season == season)).scalars().all()
        if not races:
            logger.error(f"No races found in the database for season {season}")
            return

        logger.info(f"Starting Deterministic Calibration for {len(races)} races in {season}...")

        for race in races:
            for compound in COMPOUNDS:
                calibrate_circuit_compound(db, season, race, compound)

        logger.info("Season Calibration Pipeline Complete.")

    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deterministic Tyres & Fuel Calibrator")
    parser.add_argument("--year", type=int, required=True, help="F1 Season Year to calibrate against")

    args = parser.parse_args()
    calibrate_season(args.year)
