"""
One-time backfill script to populate circuit_length_km and total_laps
for all 2025 F1 races in the database.

Usage:
    cd backend && poetry run python -m src.scripts.backfill_race_metadata
"""
import logging
from sqlalchemy import update
from src.db.session import SessionLocal
from src.db.models.race import Race

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 2025 F1 Season — official FIA circuit data
# Key = circuit name as stored in the `races.circuit` column (matches FastF1 event.Location)
CIRCUIT_METADATA_2025 = {
    "Melbourne":          {"length_km": 5.278, "laps": 58},
    "Shanghai":           {"length_km": 5.451, "laps": 56},
    "Suzuka":             {"length_km": 5.807, "laps": 53},
    "Sakhir":             {"length_km": 5.412, "laps": 57},
    "Jeddah":             {"length_km": 6.174, "laps": 50},
    "Miami Gardens":      {"length_km": 5.412, "laps": 57},
    "Imola":              {"length_km": 4.909, "laps": 63},
    "Monaco":             {"length_km": 3.337, "laps": 78},
    "Barcelona":          {"length_km": 4.657, "laps": 66},
    "Montréal":           {"length_km": 4.361, "laps": 70},
    "Spielberg":          {"length_km": 4.318, "laps": 71},
    "Silverstone":        {"length_km": 5.891, "laps": 52},
    "Budapest":           {"length_km": 4.381, "laps": 70},
    "Spa-Francorchamps":  {"length_km": 7.004, "laps": 44},
    "Zandvoort":          {"length_km": 4.259, "laps": 72},
    "Monza":              {"length_km": 5.793, "laps": 53},
    "Baku":               {"length_km": 6.003, "laps": 51},
    "Marina Bay":         {"length_km": 4.940, "laps": 62},
    "Austin":             {"length_km": 5.513, "laps": 56},
    "Mexico City":        {"length_km": 4.304, "laps": 71},
    "São Paulo":          {"length_km": 4.309, "laps": 71},
    "Las Vegas":          {"length_km": 6.201, "laps": 50},
    "Lusail":             {"length_km": 5.419, "laps": 57},
    "Yas Island":         {"length_km": 5.281, "laps": 58},
}


def backfill():
    db = SessionLocal()
    try:
        updated = 0
        skipped = 0

        for circuit, meta in CIRCUIT_METADATA_2025.items():
            result = db.execute(
                update(Race)
                .where(Race.circuit == circuit)
                .values(
                    circuit_length_km=meta["length_km"],
                    total_laps=meta["laps"],
                )
            )
            if result.rowcount > 0:
                logger.info(f"  ✓ {circuit:25s} → {meta['length_km']} km, {meta['laps']} laps")
                updated += result.rowcount
            else:
                logger.warning(f"  ✗ {circuit:25s} → not found in DB")
                skipped += 1

        db.commit()
        logger.info(f"\nBackfill complete: {updated} races updated, {skipped} not found.")

    except Exception as e:
        logger.error(f"Backfill failed: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    backfill()
