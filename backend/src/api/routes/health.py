import time
import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.storage.r2_client import r2_client

logger = logging.getLogger(__name__)

router = APIRouter()

class HealthResponse(BaseModel):
    status: str
    r2_connected: bool
    latency_ms: float

@router.get("/health", response_model=HealthResponse)
async def check_health():
    """
    Ultra-fast unversioned health endpoint (<50ms).
    Asserts application is alive and R2 is reachable.
    Explicitly NO database queries.
    """
    start = time.perf_counter()
    r2_status = False

    try:
        # A lightweight check: validating the client is initialized and bucket exists
        # We try a very fast HEAD request or just assert endpoint configuration.
        # But a real network check to R2 is required.
        # r2_client.endpoint_url is available. HeadBucket is fast.
        r2_client.s3.head_bucket(Bucket=r2_client.bucket_name)
        r2_status = True
    except Exception as e:
        logger.error("Health check R2 connectivity failure", extra={"event": "health_r2_error", "error": str(e)})

    duration_ms = (time.perf_counter() - start) * 1000.0
    status_code = 200 if r2_status else 503
    status_text = "ok" if r2_status else "degraded"

    response = HealthResponse(
        status=status_text,
        r2_connected=r2_status,
        latency_ms=duration_ms
    )

    # We do not log every single healthy ping to avoid clogging standard out,
    # but we will log if it's degraded.
    if status_code == 503:
        logger.warning(
            "Health check degraded",
            extra={"event": "health_check_failed", "duration_ms": duration_ms}
        )

    return JSONResponse(status_code=status_code, content=response.model_dump())
