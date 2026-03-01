FROM python:3.12-slim as builder

WORKDIR /app
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# We need gcc/build-essential for compiling numpy/scipy extensions on slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install poetry==2.0.1

COPY pyproject.toml poetry.lock ./
# Install cleanly without dev dependencies like pytest
RUN poetry install --without dev --no-root && rm -rf $POETRY_CACHE_DIR

# --- Runtime Stage ---
FROM python:3.12-slim as runtime

WORKDIR /app

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY . ./

# Railway explicitly enforces running on $PORT
# Gunicorn is pre-configured to handle the bind via gunicorn.conf.py
CMD ["gunicorn", "src.api.main:app", "-c", "gunicorn.conf.py"]
