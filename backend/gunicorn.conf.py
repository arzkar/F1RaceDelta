# Gunicorn configuration file for FastAPI/Uvicorn deployments
import os

# Railway dynamically assigns $PORT
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# Uvicorn Worker Class
worker_class = "uvicorn.workers.UvicornWorker"

# Workers
# Railway Free tier is 1 vCPU, 512MB RAM.
# We keep workers low to prevent memory OOMs.
workers = 1

# Since we are essentially blocking during the 200ms Monte Carlo loops,
# you might slightly bump threads or rely on standard async connections
threads = 2

# Logging
# We already heavily configured structured python-json-logger inside FastAPI,
# so we pass standard out to avoid double formatting.
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Timeout
# Bounded to 30. Monte Carlo explicitly completes in <250ms.
timeout = 30
keepalive = 5
