import os
import logging
import pandas as pd
from typing import Optional
from pathlib import Path

from src.storage.r2_client import r2_client

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parents[3] / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def export_driver_telemetry_to_datalake(
    df: pd.DataFrame,
    season: int,
    grand_prix: str,
    driver_code: str
) -> Optional[str]:
    """
    Exports a driver's normalized telemetry DataFrame to Cloudflare R2
    as a zstd-compressed Parquet file.
    Returns the object key if successful.
    """
    if df.empty:
        logger.warning(f"No telemetry data to export for driver {driver_code}")
        return None

    clean_gp = grand_prix.lower().replace(" ", "-").replace("/", "")
    object_key = f"{season}/{clean_gp}/{driver_code}/telemetry_v1.parquet"

    temp_file: Path = CACHE_DIR / f"temp_{driver_code}_telemetry.parquet"

    try:
        # Sort values to ensure partitioned by lap_number within the single file implicitly
        df = df.sort_values(by=['lap_number', 'timestamp'])

        # User explicitly requested PyArrow engine with zstd level 3
        df.to_parquet(
            temp_file,
            engine="pyarrow",
            compression="zstd",
            compression_level=3
        )

        success = r2_client.upload_file(str(temp_file), object_key)
        if success:
            logger.info(f"Successfully exported {driver_code} telemetry to Data Lake: {object_key}")
            return object_key
        return None
    except Exception as e:
        logger.error(f"Failed to export telemetry for {driver_code}: {e}", exc_info=True)
        return None
    finally:
        if temp_file.exists():
            try:
                os.remove(temp_file)
            except OSError:
                pass
