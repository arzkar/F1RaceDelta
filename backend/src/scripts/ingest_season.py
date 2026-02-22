import argparse
import logging
import fastf1

from src.scripts.ingest_race import run_ingestion

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Ingest an Entire F1 Season")
    parser.add_argument("--year", type=int, required=True, help="F1 Season Year (e.g., 2024)")
    parser.add_argument("--session", type=str, default="R", help="Session Identifier (e.g., R, Q, Sprint)")
    parser.add_argument("--skip-telemetry", action="store_true", help="Skip inserting telemetry data to R2")
    parser.add_argument("--force", action="store_true", help="Force overwrite existing records in DB/Lake")
    parser.add_argument("--dry-run", action="store_true", help="Preview what would be ingested without saving")

    args = parser.parse_args()

    logger.info(f"Fetching event schedule for season {args.year}...")
    try:
        schedule = fastf1.get_event_schedule(args.year)
    except Exception as e:
        logger.error(f"Failed to fetch schedule for {args.year}: {e}")
        return

    # Filter out testing events, we only typically care about actual rounds (RoundNumber > 0)
    rounds = schedule[schedule['RoundNumber'] > 0]

    total_rounds = len(rounds)
    logger.info(f"Found {total_rounds} race rounds in {args.year}.")

    for _, event in rounds.iterrows():
        round_name = event['EventName']
        logger.info(f"--- Starting ingestion for {round_name} ---")
        try:
            run_ingestion(
                year=args.year,
                gp=round_name,
                session_identifier=args.session,
                skip_telemetry=args.skip_telemetry,
                force=args.force,
                dry_run=args.dry_run
            )
        except Exception as e:
            logger.error(f"Failed to ingest {round_name}: {e}", exc_info=True)
            logger.info("Continuing to next race...")

    logger.info(f"Finished season ingestion for {args.year}.")

if __name__ == "__main__":
    main()
