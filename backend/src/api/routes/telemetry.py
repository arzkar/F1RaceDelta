import logging
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from src.db.session import get_db
from src.db.models.lap import Lap
from src.storage.r2_client import r2_client

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/telemetry/{race_id}/{driver_id}")
def get_telemetry_url(race_id: str, driver_id: str, db: Session = Depends(get_db)):
    """
    Returns a short-lived (5-minute) Presigned Cloudflare R2 URL to the driver's full
    Parquet trace for the specified race.

    If data string is missing due to ingestion failure or FastF1 corruption,
    returns an explicit HTTP 204 No Content so the Next.js frontend gracefully disables the chart.
    """
    # Simply fetch the first lap that contains a telemetry pointer for this driver/race combo.
    # Ingestion creates one single Parquet file per driver per race, but assigns the pointer to every lap row.
    lap = db.execute(
        select(Lap)
        .where(
            and_(
                Lap.race_id == race_id,
                Lap.driver_id == driver_id,
                Lap.telemetry_file_path.isnot(None)
            )
        )
        .limit(1)
    ).scalar_one_or_none()

    if not lap or not lap.telemetry_file_path:
        # Data Resiliency: No data for this driver in this race! (DNF on lap 1, or missing upstream data)
        # 204 No Content means "Request worked perfectly, but there is mathematically blank payload to give you".
        logger.warning(f"Telemetry missing for Race {race_id} Driver {driver_id}. Returning 204.")
        return Response(status_code=204)

    # We have a valid R2 path (e.g. "telemetry/2025/bahrain/VER.parquet")
    # Generate the strict 5-minute readonly presigned URL securely bypassing standard backend memory proxying
    try:
        url = r2_client.s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': r2_client.bucket_name,
                'Key': lap.telemetry_file_path
            },
            ExpiresIn=300  # 5 minutes
        )

        return {"url": url}
    except Exception as e:
        logger.error("Failed to generate presigned telemetry URL", extra={"error": str(e), "path": lap.telemetry_file_path})
        raise HTTPException(status_code=500, detail="Storage gateway error generating presigned telemetry link.")
