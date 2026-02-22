# F1RaceDelta Backend

This is the Python backend monolith for the **F1RaceDelta** project. It handles data ingestion from FastF1, normalizes high-frequency telemetry, persists core metadata into a NeonDB (PostgreSQL) database, and exports batch-compressed telemetry data to a Cloudflare R2 Data Lake.

## Architecture

We use a **Hybrid Data Pipeline**:

1. **Macro Data (`NeonDB`)**: Stores relational metadata (Races, Drivers, Stints, Laps). Useful for SQL queries, season aggregations, and tire degradation models.
2. **Micro Data (`Cloudflare R2`)**: Stores high-frequency (~10Hz) driver telemetry. Stored as `zstd` compressed `.parquet` files segmented per driver per race.

## Setup Python Environment

Ensure you have Python 3.12+ and [Poetry](https://python-poetry.org/docs/) installed.

```bash
# In the backend/ folder:
poetry install
```

Make sure your `.env` file is properly populated with your `NEON_DB_URL` and `R2_*` credentials (see `.env.example`).

### Migrations

Database schema is managed by `alembic`. To ensure your DB is up to date:

```bash
poetry run alembic upgrade head
```

---

## Data Ingestion Scripts

The backend provides CLI scripts to pull data from the FastF1 API directly into your database and data lake.

### What does `--session` mean?

In Formula 1, an event weekend consists of multiple sessions. The fastf1 library uses specific identifiers to choose which session's data to download.
Common identifiers include:

- `"R"` : Race
- `"Q"` : Qualifying
- `"S"` : Sprint
- `"SS"`: Sprint Shootout
- `"FP1"`, `"FP2"`, `"FP3"` : Free Practice sessions

By default, the scripts will pull Race (`R`) data.

### 1. Ingest a Single Race

You can ingest a specific race by providing the year and the Grand Prix name (or geographic location).

```bash
poetry run python -m src.scripts.ingest_race --year 2024 --gp "Bahrain" --session "R"
```

**Flags available:**

- `--skip-telemetry`: Only sync the Macro data to Postgres (Races, Drivers, Laps). **Highly recommended for local testing** to avoid downloading massive telemetry payloads and writing to Cloudflare R2.
- `--dry-run`: Evaluate what would be fetched without making any database changes or uploading files.
- `--force`: Force overwrite existing records in the database if they already exist. By default, the ingestion pipelines are fully idempotent and will safely skip duplicate rows.

### 2. Ingest a Full Season

You can pull an entire year's worth of data sequentially. The script loops through the official calendar schedule and ingests every round one by one.

```bash
poetry run python -m src.scripts.ingest_season --year 2024 --session "R"
```

_(Note: Ingesting an entire season with telemetry enabled will take a significant amount of time and download several gigabytes of cache data locally to the `backend/cache/` folder.)_

## Caching

All scripts use the fastf1 disk cache internally. Responses are saved in `backend/cache/`. This makes subsequent runs significantly faster. Do not delete this folder unless you want to force redownload data from the upstream servers.

## Physics Calibration

Once you have ingested a season of data (macro and telemetry), you must run the Deterministic Tyres & Fuel Calibrator to generate the mathematical physics constants required by the Monte Carlo Strategy Sandbox. This will optimize degradation models (alpha, beta, cliff_threshold, etc.) per track and compound for the given season.

```bash
poetry run python -m src.scripts.calibrate_season --year 2025
```

This reads the clean, green-flag laps from your local NeonDB, runs the L-BFGS-B optimization loops, and natively updates the `degradation_models` DB tables.
