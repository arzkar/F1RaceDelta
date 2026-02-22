import time
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.api.logger import setup_logging
from src.api.routes import health

# 1. Initialize Strict JSON Logging BEFORE any routes fire
setup_logging()
logger = logging.getLogger(__name__)

# 2. IP-based Rate Limiter (e.g. default 30 requests per minute)
limiter = Limiter(key_func=get_remote_address, default_limits=["30/minute"])

# 3. Create FastAPI
app = FastAPI(
    title="F1RaceDelta API",
    version="1.0.0",
    description="Mathematical F1 Race Strategy Simulator API"
)

# 4. Attach Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 5. CORS Middleware for Next.js Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to designated frontend domains
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# 6. Structured Logging Middleware (Captures every request duration in JSON)
@app.middleware("http")
async def add_process_time_and_log(request: Request, call_next):
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
        process_time_ms = (time.perf_counter() - start_time) * 1000.0
        response.headers["X-Process-Time-Ms"] = str(round(process_time_ms, 2))

        # We explicitly drop /health from spamming the JSON logs to save quota
        if request.url.path != "/health":
            logger.info(
                "HTTP Request Completed",
                extra={
                    "event": "http_request",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": process_time_ms,
                    "client_ip": request.client.host
                }
            )
        return response

    except Exception as e:
        process_time_ms = (time.perf_counter() - start_time) * 1000.0
        logger.error(
            "HTTP Request Unhandled Exception",
            extra={
                "event": "http_exception",
                "method": request.method,
                "path": request.url.path,
                "duration_ms": process_time_ms,
                "error": str(e),
                "client_ip": request.client.host
            },
            exc_info=True
        )
        raise e

# 7. Mount Routers
# /health is completely unversioned
app.include_router(health.router)

# The v1 business routers will be attached explicitly under /api/v1
from src.api.routes import catalog, telemetry, simulation

app.include_router(catalog.router, prefix="/api/v1", tags=["Catalog"])
app.include_router(telemetry.router, prefix="/api/v1/telemetry", tags=["Data Lake"])
app.include_router(simulation.router, prefix="/api/v1/simulation", tags=["Physics Engine"])
