import logging
from pathlib import Path
from typing import Optional
import fastf1

logger = logging.getLogger(__name__)

# Configure FastF1 cache using specific directory preventing git commits
CACHE_DIR = Path(__file__).resolve().parents[3] / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
fastf1.Cache.enable_cache(str(CACHE_DIR))

def fetch_session_data(year: int, gp: str, identifier: str = "R") -> Optional[fastf1.core.Session]:
    """
    Fetches F1 session data using fastf1.
    If the session is not found or fails to load, returns None.
    """
    logger.info(f"Fetching FastF1 session: {year} {gp} - {identifier}")
    try:
        session = fastf1.get_session(year, gp, identifier)
        return session
    except Exception as e:
        logger.error(f"Failed to fetch session data: {e}", exc_info=True)
        return None
