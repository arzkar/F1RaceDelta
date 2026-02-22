import argparse
import logging
import sys

from src.db.session import SessionLocal
from src.ingestion.fastf1_fetcher import fetch_session_data
from src.ingestion.db_sync import sync_macro_data

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_ingestion(year: int, gp: str, session_identifier: str, skip_telemetry: bool, force: bool, dry_run: bool):
    session = fetch_session_data(year, gp, session_identifier)
    if not session:
        logger.error(f"Could not fetch session data for {year} {gp}. Skipping.")
        return

    # circuit breaker: Check if we can completely skip `session.load()`
    db = SessionLocal()
    try:
        from src.db.models.race import Race
        from src.db.models.lap import Lap

        race = db.query(Race).filter_by(season=session.event.year, grand_prix=session.event.EventName).first()
        if race and not force and not dry_run:
            if skip_telemetry:
                logger.info(f"Race {session.event.year} {session.event.EventName} Macro Data already exists in DB. Skipping load. Use --force to overwrite.")
                return
            else:
                laps_with_telemetry = db.query(Lap).filter(Lap.race_id == race.id, Lap.telemetry_file_path.isnot(None)).first()
                if laps_with_telemetry:
                    logger.info(f"Race {session.event.year} {session.event.EventName} Macro & Telemetry Data already exists. Skipping load. Use --force to overwrite.")
                    return
    finally:
        db.close()

    logger.info("Loading session metadata...")
    session.load(telemetry=not skip_telemetry, weather=True, messages=False)

    if dry_run:
        logger.info("[DRY RUN] Would ingest the following:")
        logger.info(f"Event: {session.event.EventName} {session.event.year}")
        logger.info(f"Laps: {len(session.laps)}")
        logger.info(f"Drivers: {len(session.drivers)}")
        if not skip_telemetry:
            logger.info("[DRY RUN] Would process telemetry for exporting to R2.")
        return

    logger.info("Syncing Core Macro Data to DB...")
    db = SessionLocal()
    try:
        sync_macro_data(db, session, force=force)
    except Exception as e:
        logger.error(f"Failed to sync macro data: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()

    if not skip_telemetry:
        logger.info("Processing telemetry for Phase 2B...")
        from src.ingestion.telemetry_normalizer import get_normalized_telemetry_for_driver
        from src.ingestion.exporter import export_driver_telemetry_to_datalake
        from src.db.models.race import Race
        from src.db.models.driver import Driver
        from src.ingestion.db_sync import update_lap_telemetry_pointers

        db = SessionLocal()
        try:
            race = db.query(Race).filter_by(season=session.event.year, grand_prix=session.event.EventName).first()
            if not race:
                logger.error("Race not found in DB! Cannot sync telemetry.")
                return

            for drv_num in session.drivers:
                drv_info = session.get_driver(drv_num)
                driver_code = drv_info['Abbreviation']

                logger.info(f"Extracting telemetry for driver {driver_code}...")
                drv_laps = session.laps.pick_driver(driver_code)

                if drv_laps.empty:
                    continue

                tel_df = get_normalized_telemetry_for_driver(drv_laps)
                if tel_df.empty:
                    logger.warning(f"No valid telemetry produced for {driver_code}.")
                    continue

                object_key = export_driver_telemetry_to_datalake(
                    tel_df,
                    season=session.event.year,
                    grand_prix=session.event.EventName,
                    driver_code=driver_code
                )

                if object_key:
                    driver = db.query(Driver).filter_by(driver_code=driver_code, season=session.event.year).first()
                    if driver:
                        logger.info(f"Updating NeonDB lap pointers for {driver_code} -> {object_key}")
                        update_lap_telemetry_pointers(db, race.id, driver.id, object_key)

        except Exception as e:
            logger.error(f"Failed to process telemetry: {e}", exc_info=True)
            db.rollback()
        finally:
            db.close()

def main():
    parser = argparse.ArgumentParser(description="Ingest F1 Race Data")
    parser.add_argument("--year", type=int, required=True, help="F1 Season Year")
    parser.add_argument("--gp", type=str, required=True, help="Grand Prix Name or Round Number")
    parser.add_argument("--session", type=str, default="R", help="Session Identifier (e.g., R, Q, FP1)")
    parser.add_argument("--skip-telemetry", action="store_true", help="Skip inserting telemetry data to R2")
    parser.add_argument("--force", action="store_true", help="Force overwrite existing records in DB/Lake")
    parser.add_argument("--dry-run", action="store_true", help="Preview what would be ingested without saving to DB/Lake")

    args = parser.parse_args()

    run_ingestion(
        year=args.year,
        gp=args.gp,
        session_identifier=args.session,
        skip_telemetry=args.skip_telemetry,
        force=args.force,
        dry_run=args.dry_run
    )

if __name__ == "__main__":
    main()
