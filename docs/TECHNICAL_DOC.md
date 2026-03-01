# F1RaceDelta — Comprehensive Technical Documentation

**Author:** Arbaaz Laskar
**Version:** v1.0
**Last Updated:** March 2026

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Data Ingestion Pipeline](#4-data-ingestion-pipeline)
5. [Telemetry Normalization & Export](#5-telemetry-normalization--export)
6. [Database Schema](#6-database-schema)
7. [Domain Physics Engine](#7-domain-physics-engine)
8. [Calibration System](#8-calibration-system)
9. [Monte Carlo Simulation Engine](#9-monte-carlo-simulation-engine)
10. [Micro-Sector Preprocessor](#10-micro-sector-preprocessor)
11. [REST API Layer](#11-rest-api-layer)
12. [Frontend Architecture](#12-frontend-architecture)
13. [Telemetry Visualization Pipeline](#13-telemetry-visualization-pipeline)
14. [Storage Layer (Cloudflare R2)](#14-storage-layer-cloudflare-r2)
15. [Deployment & Infrastructure](#15-deployment--infrastructure)
16. [CLI Scripts & Tooling](#16-cli-scripts--tooling)

---

## 1. Project Overview

F1RaceDelta is a full-stack motorsport analytics platform that ingests high-frequency Formula 1 telemetry data, calibrates physics-informed degradation models against historical race data, and exposes a Monte Carlo simulation engine through a high-performance web dashboard.

The system is designed around a core principle: **no random guesswork, no hardcoded curves, no artificial smoothing**. Every simulation parameter is derived from real historical data through deterministic mathematical fitting.

### What It Does

- Ingests historical F1 session data via the FastF1 library
- Stores high-frequency telemetry (~10Hz per car) in a compressed Parquet data lake on Cloudflare R2
- Stores structured race metadata (drivers, stints, laps, sectors) in NeonDB (Serverless Postgres)
- Calibrates tyre degradation and fuel models against green-flag laps using SciPy numerical optimization
- Runs deterministic lap-by-lap race strategy simulations
- Executes head-to-head Monte Carlo simulations (up to 10,000 iterations) with probabilistic overtake modeling
- Renders telemetry and strategy outcomes in-browser using ECharts (Canvas rendering) with WASM-decoded Parquet data

### Design Philosophy

- **Backend-first, domain-driven**: Domain logic is pure Python with zero database or HTTP dependencies
- **Deterministic modeling**: Calibration is reproducible; Monte Carlo operates only on calibrated constants
- **Clean separation**: The simulation engine runs independently of the API layer
- **Performance-first**: Browser-side heavy data rendering via Web Workers and zero-copy typed arrays
- **SaaS-ready**: The architecture supports future user accounts, saved strategies, and premium tiers

---

## 2. System Architecture

The system follows a layered data pipeline architecture:

```
┌──────────────────────────────────────────────────────────────────────┐
│                        FastF1 Data Source                           │
│           (Official F1 Timing Data via Python API)                 │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    Ingestion Layer                                   │
│  ┌─────────────┐  ┌──────────────────┐  ┌───────────────────────┐  │
│  │ FastF1      │→ │ Telemetry        │→ │ Parquet Exporter      │  │
│  │ Fetcher     │  │ Normalizer       │  │ (zstd, PyArrow)       │  │
│  └─────────────┘  └──────────────────┘  └───────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ DB Sync (Macro Data: Races, Drivers, Stints, Laps)          │   │
│  │ Uses Postgres ON CONFLICT DO UPDATE for idempotency          │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────┬────────────────────────────┘
                       │                  │
              ┌────────▼────────┐  ┌──────▼───────┐
              │  Cloudflare R2  │  │   NeonDB     │
              │  (Parquet Lake) │  │  (Postgres)  │
              │  ~10GB/season   │  │  ≤500MB      │
              └────────┬────────┘  └──────┬───────┘
                       │                  │
              ┌────────▼──────────────────▼────────────────────────────┐
              │              Domain Modeling Engine                     │
              │  ┌───────────────┐  ┌──────────────┐  ┌────────────┐  │
              │  │ Physics       │  │ Calibration  │  │ Monte      │  │
              │  │ (Degradation  │  │ (3-Stage     │  │ Carlo      │  │
              │  │  + Fuel)      │  │  SciPy Fit)  │  │ Simulator  │  │
              │  └───────────────┘  └──────────────┘  └────────────┘  │
              └────────────────────────┬───────────────────────────────┘
                                       │
              ┌────────────────────────▼───────────────────────────────┐
              │           FastAPI REST Interface (/api/v1)             │
              │  Rate-limited (30/min) · Structured JSON Logging       │
              │  CORS · Versioned · Stateless Simulation Endpoints     │
              └────────────────────────┬───────────────────────────────┘
                                       │
              ┌────────────────────────▼───────────────────────────────┐
              │       Next.js 14 Frontend (TypeScript + React 19)      │
              │  Zustand State · ECharts · WASM Parquet · Web Workers  │
              └────────────────────────────────────────────────────────┘
```

### Key Architectural Constraints

1. **Domain logic must not depend on database** — all physics models are pure Pydantic classes
2. **Simulation engine must run independently of HTTP layer** — the `DeterministicSimulator` and `HeadToHeadSimulator` are standalone classes
3. **API layer must be thin** — routes are orchestration only, no business logic
4. **Database is structured, not raw-blob storage** — telemetry goes to R2, metadata to Postgres

---

## 3. Technology Stack

### Backend

| Component        | Technology                          | Purpose                                    |
| ---------------- | ----------------------------------- | ------------------------------------------ |
| Framework        | FastAPI 0.129                       | Async REST API with automatic OpenAPI docs |
| Language         | Python 3.12                         | Type-hinted domain logic                   |
| ORM              | SQLAlchemy 2.0                      | Database models and queries                |
| Migrations       | Alembic                             | Schema version control                     |
| Database         | NeonDB (Serverless Postgres)        | Structured metadata storage                |
| Object Store     | Cloudflare R2 (S3-compatible)       | Telemetry data lake                        |
| Data Source      | FastF1 3.8                          | Official F1 timing data ingestion          |
| Data Processing  | Pandas 2.2, PyArrow 23, Polars 1.38 | Telemetry normalization and export         |
| Math             | NumPy, SciPy (L-BFGS-B optimizer)   | Numerical optimization and statistics      |
| Validation       | Pydantic 2.12                       | Request/response schemas and domain models |
| Rate Limiting    | SlowAPI                             | IP-based request throttling                |
| Logging          | python-json-logger                  | Structured JSON production logs            |
| WSGI             | Gunicorn + Uvicorn workers          | Production application server              |
| Storage Client   | boto3                               | S3-compatible R2 API access                |
| Containerization | Docker (multi-stage build)          | Production deployment                      |
| Package Manager  | Poetry 1.8                          | Dependency management                      |

### Frontend

| Component       | Technology                        | Purpose                               |
| --------------- | --------------------------------- | ------------------------------------- |
| Framework       | Next.js 16.1 (App Router)         | React SSR/CSR framework               |
| Language        | TypeScript 5                      | Type-safe component development       |
| React           | React 19.2                        | UI rendering                          |
| State           | Zustand 5.0                       | Lightweight global state management   |
| Charts          | ECharts 6.0 + echarts-for-react   | Canvas-rendered high-density charts   |
| Parquet Decoder | parquet-wasm 0.7                  | WebAssembly Parquet file decoding     |
| Arrow           | apache-arrow 21.1                 | Zero-copy IPC buffer handling         |
| Icons           | Lucide React                      | Icon library                          |
| Theming         | next-themes                       | Dark/light mode switching             |
| Styling         | Tailwind CSS 4                    | Utility-first CSS                     |
| Typography      | Geist + Geist Mono (Google Fonts) | Modern sans-serif and monospace fonts |

---

## 4. Data Ingestion Pipeline

The ingestion pipeline transforms raw FastF1 session data into structured database records and compressed telemetry files. It is executed via CLI scripts and is fully idempotent.

### Pipeline Flow

```
fastf1.get_session(year, gp, "R")
        │
        ▼
session.load(telemetry=True, weather=True)
        │
        ├──► sync_macro_data(db, session)
        │       │
        │       ├──► Upsert Race (season + grand_prix = unique)
        │       ├──► Upsert Drivers (driver_code + season = unique)
        │       ├──► Upsert Stints (race_id + driver_id + start_lap = unique)
        │       └──► Upsert Laps (race_id + driver_id + lap_number = unique)
        │
        └──► For each driver:
                │
                ├──► get_normalized_telemetry_for_driver(drv_laps)
                │       │
                │       └──► Per lap: normalize_lap_telemetry(lap)
                │               │
                │               ├──► Validate lap (no PitIn/PitOut, no Red Flag)
                │               ├──► Extract telemetry via lap.get_telemetry()
                │               ├──► Compute relative timestamps (seconds from lap start)
                │               ├──► Resample to exactly 10Hz (0.1s intervals)
                │               └──► Interpolate: speed, throttle, brake, gear, rpm, x, y
                │
                ├──► export_driver_telemetry_to_datalake(df, season, gp, driver)
                │       │
                │       ├──► Sort by (lap_number, timestamp)
                │       ├──► Write to temp .parquet (PyArrow engine, zstd level 3)
                │       ├──► Upload to R2: {season}/{clean_gp}/{driver}/telemetry_v1.parquet
                │       └──► Clean up temp file
                │
                └──► update_lap_telemetry_pointers(db, race_id, driver_id, object_key)
                        │
                        └──► UPDATE laps SET telemetry_file_path = ? WHERE race_id = ? AND driver_id = ?
```

### FastF1 Fetcher (`fastf1_fetcher.py`)

The fetcher is a thin wrapper around `fastf1.get_session()`. It configures a local disk cache at `{project_root}/cache/` to avoid re-downloading session data on repeated runs. The cache directory is excluded from git.

```python
CACHE_DIR = Path(__file__).resolve().parents[3] / "cache"
fastf1.Cache.enable_cache(str(CACHE_DIR))
```

### Circuit Breaker Logic

The `ingest_race.py` script includes a circuit breaker that skips `session.load()` (an expensive network operation) if the race data already exists in the database:

1. If `--skip-telemetry` and the race exists in DB → skip entirely
2. If telemetry is requested and laps already have `telemetry_file_path` pointers → skip entirely
3. Use `--force` to override and re-ingest

### Idempotent Upserts

All database writes use Postgres `ON CONFLICT DO UPDATE` (via SQLAlchemy's `insert().on_conflict_do_update()`), keyed on unique composite indexes. This means the ingestion pipeline can be run multiple times safely without creating duplicate records.

---

## 5. Telemetry Normalization & Export

### Normalization (`telemetry_normalizer.py`)

Raw FastF1 telemetry arrives at irregular sampling rates (typically 10-20Hz). The normalizer performs the following transformations per lap:

1. **Validation**: Rejects pit-in laps, pit-out laps, and red-flag laps
2. **Timestamp Computation**: Converts absolute `SessionTime` (timedelta) to relative seconds from `LapStartTime`
3. **Channel Extraction**: Pulls `Speed`, `Throttle`, `Brake`, `nGear` (gear), `RPM`, `X`, `Y` into a clean DataFrame
4. **10Hz Resampling**: Creates a uniform time grid at 0.1-second intervals from 0.0 to `max_time`
5. **Linear Interpolation**: Uses `numpy.interp()` to resample each channel onto the uniform grid
6. **Gear Rounding**: Rounds interpolated gear values back to integers

The output schema per lap row:

| Column       | Type  | Description                                 |
| ------------ | ----- | ------------------------------------------- |
| `timestamp`  | float | Seconds from lap start (0.0, 0.1, 0.2, ...) |
| `lap_number` | int   | Absolute lap number in the race             |
| `speed`      | float | Speed in km/h                               |
| `throttle`   | float | Throttle application (0-100)                |
| `brake`      | float | Brake application (0-100 or boolean)        |
| `gear`       | int   | Current gear (1-8)                          |
| `rpm`        | float | Engine RPM                                  |
| `x`          | float | GPS X coordinate                            |
| `y`          | float | GPS Y coordinate                            |

### Export (`exporter.py`)

Normalized telemetry is exported as a single Parquet file per driver per race:

- **Engine**: PyArrow
- **Compression**: Zstandard (zstd) at level 3 — chosen for the optimal balance between compression ratio and decompression speed
- **Sort Order**: `(lap_number, timestamp)` — ensures sequential reads are cache-friendly
- **Object Key Format**: `{season}/{clean-gp-name}/{driver_code}/telemetry_v1.parquet`
  - Example: `2025/australian-grand-prix/VER/telemetry_v1.parquet`

### Data Volume Reality

FastF1 provides ~10-20Hz telemetry per car. For a typical race:

- 20 cars × 60 laps × 10Hz = **~2 million rows per race**
- A full 24-race season generates **~10GB of raw telemetry**
- NeonDB free tier caps at 500MB — hence the hybrid storage strategy

---

## 6. Database Schema

All tables use **UUID primary keys**, explicit foreign key relationships, and composite unique indexes for upsert safety. Schema migrations are managed with Alembic.

### Entity-Relationship Diagram

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│    races     │       │   drivers    │       │ degradation  │
│              │       │              │       │   _models    │
│ id (PK)      │       │ id (PK)      │       │              │
│ season       │       │ driver_code  │       │ id (PK)      │
│ grand_prix   │       │ full_name    │       │ season       │
│ circuit      │       │ team         │       │ track_id     │
│ circuit_     │       │ season       │       │ compound     │
│  length_km   │       │              │       │ alpha        │
│ total_laps   │       │ UQ: (driver_ │       │ base_wear_   │
│ race_date    │       │  code,season)│       │  rate        │
│ created_at   │       └──────┬───────┘       │ cliff_thres  │
│              │              │               │ beta, gamma  │
│ UQ: (season, │              │               │ fuel_per_km  │
│  grand_prix) │              │               │ fuel_time_   │
└──────┬───────┘              │               │  penalty     │
       │                      │               │ rmse, mae    │
       │     ┌────────────────┤               │ r_squared    │
       │     │                │               │ sample_count │
       ▼     ▼                │               │              │
┌──────────────┐              │               │ UQ: (season, │
│   stints     │              │               │  track_id,   │
│              │              │               │  compound)   │
│ id (PK)      │              │               └──────────────┘
│ race_id (FK) │◄─────────────┘
│ driver_id(FK)│
│ compound     │
│ start_lap    │
│ end_lap      │
│ stint_length │
│ created_at   │
│              │
│ UQ: (race_id,│
│  driver_id,  │
│  start_lap)  │
└──────┬───────┘
       │
       ▼
┌──────────────┐       ┌──────────────┐
│    laps      │       │ micro_sectors│
│              │       │              │
│ id (PK)      │       │ id (PK)      │
│ race_id (FK) │       │ lap_id (FK)  │
│ driver_id(FK)│       │ corner_number│
│ stint_id(FK) │──────►│ entry_speed  │
│ lap_number   │       │ apex_speed   │
│ lap_time_s   │       │ exit_speed   │
│ sector_1_s   │       └──────────────┘
│ sector_2_s   │
│ sector_3_s   │
│ track_status │
│ is_green_flag│
│ fuel_est_kg  │
│ telemetry_   │
│  file_path   │
│ created_at   │
│              │
│ UQ: (race_id,│
│  driver_id,  │
│  lap_number) │
└──────────────┘
```

### Table Details

#### `races`

Stores one row per Grand Prix event. The `circuit` field stores the FastF1 `event.Location` string (e.g., "Melbourne", "Sakhir"). `circuit_length_km` and `total_laps` are either extracted from FastF1's `circuit_info` or backfilled via the `backfill_race_metadata.py` script using official FIA data.

#### `drivers`

One row per driver per season. `driver_code` is the 3-letter FIA abbreviation (VER, HAM, NOR). The composite unique index `(driver_code, season)` allows the same driver code to exist across different seasons with potentially different team affiliations.

#### `stints`

Represents a continuous tyre stint for a specific driver in a specific race. A stint is bounded by `start_lap` and `end_lap` and has a single `compound` (SOFT, MEDIUM, HARD, INTERMEDIATE, WET). Stints are derived from FastF1's `Stint` grouping column in the laps DataFrame.

#### `laps`

One row per lap per driver. The `track_status` field contains the FastF1 track status code:

- `'1'` = Green flag (normal racing)
- `'2'` = Yellow flag
- `'4'` = Safety Car
- `'5'` = Red Flag
- `'6'` = VSC (Virtual Safety Car)

The `is_green_flag` boolean is computed during ingestion as `track_status == '1'`. The `telemetry_file_path` column is a pointer to the R2 object key containing this driver's full-race Parquet file. All laps for a given driver in a given race share the same pointer.

#### `degradation_models`

Stores the output of the calibration pipeline. One row per `(season, track_id, compound)` combination. Contains all fitted physics parameters (alpha, base_wear_rate, cliff_threshold, beta, gamma, fuel_per_km, fuel_time_penalty_per_kg) and quality metrics (RMSE, MAE, R²).

#### `micro_sectors`

Optional structured table for modeling specific corner speeds. Contains entry/apex/exit speeds per corner per lap. This table is defined but not yet actively populated — it is reserved for future fine-grained track modeling.

---

## 7. Domain Physics Engine

The physics engine is implemented as pure Pydantic models with zero database or HTTP dependencies. It consists of two core models: `DegradationModel` and `FuelModel`.

### 7.1 Tyre Degradation Model (`DegradationModel`)

The degradation model implements a **piecewise lap-based wear accumulation** system. It separates tyre behavior into two distinct phases:

#### Phase 1: Linear Degradation (Normal Racing)

During normal racing conditions, tyre performance degrades linearly as wear accumulates:

```
wear_n = wear_(n-1) + base_wear_rate
penalty = alpha × current_wear
```

Where:

- `base_wear_rate` (float): The fundamental flat wear increment added every lap. Represents the physical rubber loss per lap. Typical range: 0.02–0.2
- `alpha` (float): The linear slope of degradation — seconds of lap time lost per unit of accumulated wear. Typical range: 0.0–0.15
- `current_wear` (float): The cumulative wear accumulated across all laps in the current stint

**Example**: If `base_wear_rate = 0.05` and `alpha = 0.08`, then after 10 laps:

- `current_wear = 10 × 0.05 = 0.5`
- `penalty = 0.08 × 0.5 = 0.04 seconds` added to the baseline lap time

#### Phase 2: Exponential Cliff (Tyre Failure)

When cumulative wear exceeds the `cliff_threshold`, the tyre enters an exponential decline phase:

```
if current_wear < cliff_threshold:
    penalty = alpha × current_wear                              # Linear
else:
    linear_max = alpha × cliff_threshold
    exponential_penalty = beta × exp(gamma × (current_wear - cliff_threshold))
    penalty = linear_max + exponential_penalty                  # Cliff
```

Where:

- `cliff_threshold` (float): The accumulated wear point at which the tyre falls off the cliff. Typical range: 5.0–40.0
- `beta` (float): The exponential severity multiplier after the cliff. Controls the initial magnitude of the exponential drop. Typical range: 0.0–5.0
- `gamma` (float): The exponential growth rate after the cliff. Controls how rapidly the penalty accelerates. Typical range: 0.0–5.0

**The cliff mechanism models the real-world phenomenon** where F1 tyres maintain relatively consistent performance until their rubber compound is depleted beyond a critical threshold, at which point lap times increase dramatically and unpredictably.

### 7.2 Fuel Model (`FuelModel`)

The fuel model implements a **deterministic track-length-dependent constant burn** formula. No throttle-based integration is used — this is a deliberate design choice to preserve computational speed for Monte Carlo execution.

#### Fuel Burn Per Lap

```
fuel_burn_per_lap = fuel_per_km_kg × track_length_km
```

Where:

- `fuel_per_km_kg` (float): Theoretical kg of fuel burned per kilometer. Typical range: 0.5–3.0 kg/km
- `track_length_km` (float): Circuit length in kilometers (sourced from the `races` table)

#### Fuel Weight Penalty

```
lap_time_delta = current_fuel_mass_kg × fuel_time_penalty_per_kg
```

Where:

- `current_fuel_mass_kg` (float): Remaining fuel in the car (starts at ~110 kg, decreases each lap)
- `fuel_time_penalty_per_kg` (float): Lap time penalty per kg of fuel weight. The FIA-accepted approximation is **~0.035 seconds per kg**. Typical range: 0.02–0.06

**Physical interpretation**: A fully fueled F1 car (~110 kg of fuel) is approximately **3.85 seconds slower** per lap than an empty car. As the race progresses and fuel burns off, the car naturally gets faster — this is the "fuel effect" visible in real race telemetry as a gradual lap time improvement independent of tyre degradation.

### 7.3 Combined Lap Time Formula

The `DeterministicSimulator` combines both models to produce a per-lap simulated time:

```
simulated_lap_time = baseline_lap_time
                   + degradation_penalty(current_wear)
                   + fuel_weight_penalty(current_fuel_mass)
```

Where `baseline_lap_time` represents the **theoretical 0-fuel, 0-wear lap time capability limit** — the absolute fastest a driver could lap the circuit under perfect conditions. This baseline is determined per-driver during calibration.

Each lap iteration:

1. Accumulates wear: `current_wear += base_wear_rate`
2. Computes degradation penalty from accumulated wear
3. Computes fuel weight penalty from remaining fuel
4. Deducts fuel: `current_fuel -= fuel_burn_per_lap` (clamped to ≥ 0)

---

## 8. Calibration System

The calibration system is responsible for fitting the physics model parameters to actual historical race data. It uses a **strict 3-stage deterministic mathematical fitting solver** implemented with SciPy's L-BFGS-B optimizer.

### 8.1 Truth Extraction (`truth_extractor.py`)

Before calibration can occur, the system must extract mathematically clean training data from the database. The `TruthExtractor` performs aggressive purging of contaminated laps.

#### Filtering Rules

1. **Out-lap removal**: The first lap of every stint is discarded (cold tyres, crossing pit lane)
2. **In-lap removal**: The last lap of every stint is discarded (driver lifts off, entering pit lane)
3. **Green flag enforcement**: Only laps with `is_green_flag == True` AND `track_status == '1'` are kept
4. **Continuity enforcement**: If a lap number gap is detected (e.g., missing data for lap 15), the current segment is closed and a new segment begins
5. **Minimum segment length**: Segments with fewer than 3 consecutive clean laps are rejected as statistically insufficient

#### ContinuousStintSegment

The output is a list of `ContinuousStintSegment` objects, each representing an uninterrupted sequence of green-flag laps for a specific driver on a specific compound:

```python
class ContinuousStintSegment:
    driver_code: str                    # e.g., "VER"
    starting_wear_laps: int             # Tyre age at the start of this segment
    lap_numbers: List[int]              # e.g., [12, 13, 14, 15, 16]
    lap_times: List[float]              # e.g., [86.5, 86.7, 86.9, 87.1, 87.4]
    fuel_weights_kg: List[float]        # Estimated fuel weights
```

The `starting_wear_laps` is computed as `lap.lap_number - stint.start_lap`, representing how many laps the tyres have already completed before this particular clean segment begins.

### 8.2 Three-Stage Optimizer (`optimizer.py`)

The optimizer isolates different physical effects by fitting them in sequence. Each stage uses SciPy's `minimize()` with the L-BFGS-B (Limited-memory Broyden–Fletcher–Goldfarb–Shanno with Bound constraints) algorithm.

#### Driver Baseline Determination

Before optimization begins, the optimizer computes a per-driver baseline lap time:

```python
baseline = fastest_actual_lap - 1.0  # seconds
```

For each driver, their fastest recorded lap is taken, and 1 second is subtracted as an aggressive theoretical baseline. The optimizer then uses fuel and wear models to build lap times back UP to the actual driven pace.

#### Stage 1: Fuel Parameter Fitting

**Objective**: Isolate the fuel effect by fitting only on early-stint laps (where tyre degradation is minimal).

**Parameters being fitted**:

- `fuel_per_km_kg` — bounded to [0.5, 3.0]
- `fuel_time_penalty_per_kg` — bounded to [0.02, 0.06]

**Data filter**: Only segments where `starting_wear_laps < 10` (early in a stint, fresh tyres)

```python
minimize(objective_stage_1, x0=[1.5, 0.035], method='L-BFGS-B',
         bounds=[(0.5, 3.0), (0.02, 0.06)])
```

**Rationale**: Early in a tyre stint, degradation is negligible. The lap time differences are dominated by fuel burn. By fitting fuel first, we remove its effect before attempting to measure degradation.

#### Stage 2: Linear Degradation Fitting

**Objective**: With fuel parameters now locked, fit the linear degradation slope.

**Parameters being fitted**:

- `alpha` — bounded to [0.0, 0.15]
- `base_wear_rate` — bounded to [0.0, 0.2]

**Data filter**: Only segments where `starting_wear_laps < 25` (avoids cliff region)

```python
minimize(objective_stage_2, x0=[0.05, 1.0], method='L-BFGS-B',
         bounds=[(0.0, 0.15), (0.0, 0.2)])
```

**Rationale**: By excluding deep-stint laps, we prevent the cliff behavior from polluting the linear fit.

#### Stage 3: Cliff Parameter Fitting (Conditional)

**Objective**: Fit the exponential cliff parameters using all available data.

**Precondition**: Only runs if the maximum theoretical wear across all segments exceeds 10.0. If no stint was long enough to potentially reach a cliff, the parameters are set to disabled values:

- `cliff_threshold = 999.0` (effectively unreachable)
- `beta = 0.0`, `gamma = 0.0`

**Parameters being fitted**:

- `cliff_threshold` — bounded to [5.0, 40.0]
- `beta` — bounded to [0.0, 5.0]
- `gamma` — bounded to [0.0, 5.0]

```python
minimize(objective_stage_3, x0=[15.0, 0.2, 0.5], method='L-BFGS-B',
         bounds=[(5.0, 40.0), (0.0, 5.0), (0.0, 5.0)])
```

### 8.3 Quality Metrics

After all three stages complete, the optimizer computes final quality scores against the full dataset:

- **RMSE** (Root Mean Square Error): `sqrt(mean((actual - predicted)²))`
- **MAE** (Mean Absolute Error): `mean(|actual - predicted|)`
- **R²** (Coefficient of Determination): `1 - (SS_res / SS_tot)` where `SS_res = Σ(y - ŷ)²` and `SS_tot = Σ(y - ȳ)²`

The target is RMSE < 0.2–0.3 seconds — meaning the model predicts lap times within a quarter-second of reality on average.

### 8.4 Segment Simulation for Fitting

During each optimizer evaluation, the system creates a fresh `DeterministicSimulator` for the segment being tested:

1. Computes starting wear: `starting_wear = segment.starting_wear_laps × base_wear_rate`
2. Computes fuel consumption to this point: `fuel_burnt = fuel_burn_per_lap × (first_lap_number - 1)`
3. Runs the simulator across the segment's lap range
4. Compares predicted lap times against actual historical lap times
5. Returns RMSE as the loss function value

---

## 9. Monte Carlo Simulation Engine

The Monte Carlo engine (`monte_carlo.py`) executes thousands of probabilistic head-to-head race simulations between two drivers to determine statistical win probabilities.

### 9.1 Configuration (`MonteCarloConfig`)

| Parameter                          | Default | Description                                                 |
| ---------------------------------- | ------- | ----------------------------------------------------------- |
| `iterations`                       | 1,000   | Number of Monte Carlo iterations (capped at 10,000 by API)  |
| `degradation_variance_percent`     | 5%      | Gaussian noise amplitude applied to degradation parameters  |
| `dirty_air_penalty_seconds`        | 0.8s    | Time penalty for the trailing car when within gap threshold |
| `overtake_delta_threshold_seconds` | 0.5s    | Pace advantage needed for >50% overtake probability         |
| `gap_threshold_seconds`            | 1.0s    | Gap distance at which dirty air effect activates            |

### 9.2 Per-Iteration Execution

Each Monte Carlo iteration runs a complete lap-by-lap race between Driver A and Driver B:

#### Step 1: Parameter Perturbation

At the start of each iteration, the `alpha` (degradation slope) parameter for each driver is randomly perturbed using a Gaussian distribution:

```python
perturbed_alpha = max(0.0001, random.gauss(base_alpha, base_alpha * variance_percent))
```

This models the inherent uncertainty in tyre behavior — even with identical compounds on the same track, degradation rates vary slightly due to driving style, track temperature, and setup variations.

#### Step 2: Lap-by-Lap Simulation

For each lap from 1 to `total_laps`:

1. **Compute raw lap times** via the `DeterministicSimulator` for both drivers
2. **Apply dirty air penalty**: If the gap between cars is less than `gap_threshold_seconds` (default 1.0s), the trailing car receives a `dirty_air_penalty_seconds` (default 0.8s) addition to their lap time
3. **Recompute gap**: `gap_change = time_b - time_a` (positive means A was faster)
4. **Check for position swap**: If the gap changes sign (cars "cross" on track), an overtake evaluation is triggered

#### Step 3: Overtake Mechanics (Sigmoid Probability)

When the gap changes sign (indicating the trailing car has caught and theoretically passed the leader), the system computes an overtake probability using a **logistic sigmoid function**:

```python
probability = 1 / (1 + exp(-k × (pace_advantage - offset)))
```

Where:

- `k = 5.0` — steepness parameter creating a sharp activation edge
- `offset = overtake_delta_threshold_seconds` (default 0.5s) — centers the 50% probability point
- `pace_advantage` — the raw pace difference between the overtaking and defending driver (accounting for dirty air)

**Sigmoid behavior**:

- At `pace_advantage = 0.0s`: probability ≈ 7.6% (very low — no real advantage)
- At `pace_advantage = 0.5s`: probability = 50.0% (coin flip at the threshold)
- At `pace_advantage = 1.0s`: probability ≈ 92.4% (strong advantage, almost certain pass)
- At `pace_advantage = 1.5s`: probability ≈ 99.3% (dominant advantage)

**Overtake resolution**:

- A random number `r ∈ [0, 1)` is drawn
- If `r < probability`: overtake succeeds — gap inverts, positions swap
- If `r ≥ probability`: overtake fails — gap is reset to 0.2s (trailing car stuck behind), trailing car's lap time is penalized to `leader_time + 0.1s`

### 9.3 Aggregation

After all iterations complete:

```python
win_probability_a = (a_wins / iterations) × 100.0
win_probability_b = (b_wins / iterations) × 100.0
```

Before each iteration, the perturbed parameters are restored to their calibrated baseline values to ensure clean statistical independence between iterations.

---

## 10. Micro-Sector Preprocessor

The `MicroSectorPreprocessor` (`preprocessor.py`) is responsible for converting raw 10Hz telemetry into aggregated micro-sector summaries. This avoids simulating at 10Hz resolution, which would be computationally prohibitive for Monte Carlo runs.

### Processing Steps

1. **Fetch**: Streams the Parquet file directly from R2 into memory via `r2_client.read_file_stream()`
2. **Distance Computation**: For each lap, calculates cumulative track distance from speed and time:
   ```
   dt = diff(timestamps)
   speed_ms = speed_kmh / 3.6
   dx = speed_ms × dt
   track_distance = cumsum(dx)
   ```
3. **Sector Binning**: Divides the lap into `target_sectors` (default 200) equal-distance bins:
   ```
   sector_size = total_distance / 200
   micro_sector_id = floor(track_distance / sector_size)
   ```
4. **Aggregation**: For each micro-sector, computes:
   - `baseline_time_s`: Sum of dt within the sector (how long the car spent in this sector)
   - `baseline_speed_kmh`: Mean speed within the sector
   - `mean_throttle`: Average throttle application (0-100)
   - `mean_brake`: Average brake application (0-100)
   - `distance_start` / `distance_end`: Track distance bounds of the sector

### Load Proxy Computation

Since true lateral G-force data requires steering angle and corner radius (not available in FastF1), the preprocessor uses speed variance and throttle/brake patterns as load proxies:

- High speed + high brake = high longitudinal load
- Speed variance within a sector = cornering indicator

---

## 11. REST API Layer

The API is built on FastAPI and mounted under versioned prefixes. All simulation endpoints are stateless.

### Application Configuration (`main.py`)

- **Rate Limiting**: 30 requests/minute per IP (via SlowAPI)
- **CORS**: Allows all origins (production should restrict to frontend domain)
- **Structured Logging Middleware**: Every HTTP request is logged as JSON with method, path, status code, duration, and client IP. `/health` endpoint is excluded from logging to avoid noise.
- **Response Header**: `X-Process-Time-Ms` is injected into every response

### Router Mounting

| Prefix               | Router              | Tag            |
| -------------------- | ------------------- | -------------- |
| `/health`            | `health.router`     | (unversioned)  |
| `/api/v1`            | `catalog.router`    | Catalog        |
| `/api/v1/telemetry`  | `telemetry.router`  | Data Lake      |
| `/api/v1/simulation` | `simulation.router` | Physics Engine |

### Endpoint Reference

#### Health

| Method | Path      | Description                                                                                                     |
| ------ | --------- | --------------------------------------------------------------------------------------------------------------- |
| `GET`  | `/health` | Returns R2 connectivity status and API latency. No DB queries. Target: <50ms. Returns 503 if R2 is unreachable. |

#### Catalog

| Method | Path                                   | Description                                                            |
| ------ | -------------------------------------- | ---------------------------------------------------------------------- |
| `GET`  | `/api/v1/seasons`                      | Returns all distinct F1 seasons in the database (descending)           |
| `GET`  | `/api/v1/seasons/{year}/races`         | Returns all races for a season, ordered chronologically                |
| `GET`  | `/api/v1/races/{race_id}/drivers`      | Returns the driver grid for a specific race (joined through stints)    |
| `GET`  | `/api/v1/races/{race_id}/stints`       | Returns the complete pit strategy history, flattened with driver codes |
| `GET`  | `/api/v1/race-pace/{season}/{race_id}` | Computes per-driver rolling baseline pace from 1–5 preceding races     |

#### Race Pace Algorithm

The race pace endpoint computes each driver's representative pace using a rolling lookback window:

1. **Calendar ordering**: All races in the season are ordered chronologically
2. **Lookback window**: Up to 5 races preceding the selected race
3. **Outlier filtering**: Laps exceeding 130% of the race's fastest lap are rejected
4. **Per-race median**: For each driver in each lookback race, the median lap time is computed (minimum 3 clean laps required)
5. **Cross-race average**: The medians across all lookback races are averaged to produce the final pace figure

If the selected race is the first of the season, the endpoint returns an empty list and the frontend defaults to 85.0s.

#### Telemetry

| Method | Path                                        | Description                                                                                                                      |
| ------ | ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `GET`  | `/api/v1/telemetry/{race_id}/{driver_code}` | Returns a 5-minute presigned R2 URL for the driver's Parquet file. Returns HTTP 204 if data is missing (DNF, ingestion failure). |

#### Simulation

| Method | Path                                            | Description                                                            |
| ------ | ----------------------------------------------- | ---------------------------------------------------------------------- |
| `GET`  | `/api/v1/simulation/models/{season}/{track_id}` | Returns calibrated degradation parameters for all compounds at a track |
| `POST` | `/api/v1/simulation/monte-carlo`                | Executes Monte Carlo head-to-head simulation (max 10,000 iterations)   |
| `POST` | `/api/v1/simulation/strategy`                   | Runs deterministic multi-stint strategy simulation                     |

#### Monte Carlo Request Schema

```json
{
  "race_id": "uuid",
  "driver_a_id": "VER",
  "driver_b_id": "HAM",
  "compound_a": "SOFT",
  "compound_b": "HARD",
  "iterations": 10000,
  "total_laps": 50,
  "starting_wear_laps_a": 0,
  "starting_wear_laps_b": 0,
  "starting_gap_s": 0.0
}
```

#### Strategy Request Schema

```json
{
  "race_id": "uuid",
  "baseline_lap_time_s": 85.0,
  "starting_fuel_kg": 110.0,
  "stints": [
    { "compound": "MEDIUM", "laps": 25 },
    { "compound": "HARD", "laps": 30 }
  ]
}
```

The strategy simulator runs each stint sequentially, preserving fuel state across pit stops but resetting tyre wear to 0.0 (fresh tyres). It uses calibrated degradation models from the database, falling back to hardcoded defaults per compound if no calibrated model exists:

| Compound | Default α | Default base_wear_rate | Default cliff_threshold |
| -------- | --------- | ---------------------- | ----------------------- |
| SOFT     | 0.08      | 0.04                   | 0.7                     |
| MEDIUM   | 0.05      | 0.03                   | 0.85                    |
| HARD     | 0.03      | 0.02                   | 1.0                     |

---

## 12. Frontend Architecture

The frontend is a Next.js 16 application using the App Router with TypeScript and React 19. It follows a SaaS-style dashboard layout.

### Layout Structure

```
┌──────────────────────────────────────────────────────────────┐
│ Sidebar (w-64, fixed)                                        │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ F1RaceDelta (logo + pulse indicator)                     │ │
│ ├──────────────────────────────────────────────────────────┤ │
│ │ Dashboard     (/                )                        │ │
│ │ Telemetry     (/telemetry       )                        │ │
│ │ Strategy      (/strategy        )                        │ │
│ │ Monte Carlo   (/monte-carlo     )                        │ │
│ │ Models        (/models          )                        │ │
│ ├──────────────────────────────────────────────────────────┤ │
│ │ Theme Toggle (Dark/Light)                                │ │
│ │ Engine Status (Online indicator)                         │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ Topbar (h-16, sticky, backdrop-blur)                     │ │
│ │ Season ▼ │ Race ▼ │     Driver A ▼  VS  Driver B ▼      │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ Main Content (flex-1, overflow-y-auto, p-6)              │ │
│ │ [Page-specific content rendered here]                    │ │
│ └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### State Management (Zustand)

All global UI state is managed through a single Zustand store (`uiStore.ts`):

```typescript
interface UiStore {
  selectedSeason: number; // Default: 2025
  selectedRaceId: string | null;
  selectedDriverA: string | null;
  selectedDriverB: string | null;
  setSeason(season: number): void;
  setRace(raceId: string): void;
  setDrivers(a: string | null, b: string | null): void;
}
```

**Cascade behavior**: Setting a new season resets race and driver selections. Setting a new race resets driver selections. This prevents stale cross-context state.

### Pages

#### Dashboard (`/`)

Landing page with navigation cards to Telemetry Analyzer and Monte Carlo Strategy (placeholder). Links are styled with glassmorphic hover effects.

#### Telemetry (`/telemetry`)

Displays side-by-side high-frequency telemetry traces for one or two selected drivers. The data flows through a presigned URL → Web Worker → WASM Parquet decode → Arrow IPC → ECharts pipeline (detailed in Section 13).

#### Strategy (`/strategy`)

Interactive race strategy simulator. Users configure:

- **Stint plan**: 1–5 stints with compound selection (SOFT/MEDIUM/HARD) and lap counts
- **Baseline lap time**: Theoretical fastest lap (60–120s)
- **Starting fuel**: Initial fuel load (10–150 kg)

A visual stint bar shows the proportional length of each stint using compound colors (Red=SOFT, Yellow=MEDIUM, White=HARD). The "Run Strategy" button POSTs to `/api/v1/simulation/strategy` and renders two synchronized ECharts:

- **Top chart**: Lap time vs. lap number (color-coded per compound)
- **Bottom chart**: Tyre wear and fuel mass vs. lap number (dual Y-axis)

Pit stop locations are rendered as dashed vertical mark lines.

#### Monte Carlo (`/monte-carlo`)

Head-to-head Monte Carlo sandbox. Users configure iterations (1k–10k slider), starting gap, and tyre age offset. POSTs to `/api/v1/simulation/monte-carlo`. Results are displayed as:

- **Stacked horizontal bar chart**: Win probability distribution (blue gradient = Driver A, red gradient = Driver B)
- **Mean Delta at Finish**: Signed time gap at the end
- **Mathematical Confidence**: Displayed as 99.7% (3-sigma reference)

### Theming

The application supports dark and light modes via `next-themes`. CSS custom properties define the palette:

| Variable    | Dark Mode | Light Mode |
| ----------- | --------- | ---------- |
| `--bg`      | `#09090b` | `#ffffff`  |
| `--fg`      | `#fafafa` | `#18181b`  |
| `--panel`   | `#18181b` | `#f4f4f5`  |
| `--border`  | `#27272a` | `#e4e4e7`  |
| `--muted`   | `#a1a1aa` | `#71717a`  |
| `--surface` | `#18181b` | `#fafafa`  |

F1 compound colors are defined as theme constants: Soft=`#ef4444`, Medium=`#eab308`, Hard=`#f3f4f6`, Intermediate=`#22c55e`, Wet=`#3b82f6`.

---

## 13. Telemetry Visualization Pipeline

The telemetry page implements a high-performance zero-copy data pipeline from Cloudflare R2 to Canvas-rendered ECharts.

### Data Flow

```
1. Topbar → user selects Season, Race, Driver A/B
2. useUiStore provides selectedRaceId + selectedDriverA/B
3. useTelemetryUrl(raceId, driverCode) fetches presigned URL
       │
       └──► GET /api/v1/telemetry/{race_id}/{driver_code}
            Returns { url: "https://r2.cloudflare.com/...?signature=..." }
                    (5-minute expiry)

4. useTelemetry(presignedUrl) hook initializes a Web Worker
       │
       └──► Web Worker (parquetWorker.ts):
            a. fetch(presignedUrl) → ArrayBuffer from R2
            b. new Uint8Array(arrayBuffer)
            c. parquet.default(wasmUrl)    // Initialize WASM module
            d. parquet.readParquet(uint8)  // Decode Parquet → Arrow Table
            e. table.intoIPCStream()       // Serialize to Arrow IPC
            f. postMessage({ ipcBuffer }, [ipcBuffer.buffer])  // Zero-copy transfer

5. Main Thread receives IPC buffer:
       a. arrow.tableFromIPC(ipcBuffer)    // Zero-copy Arrow Table
       b. extractBestLap(table)            // Select most complete lap
       c. Returns DecodedTelemetry (Float32Array × 6 channels)

6. TelemetryChart renders via ECharts (Canvas renderer)
```

### Best Lap Selection (`extractBestLap`)

Since the Parquet file contains all laps for the entire race, the frontend must select a single representative lap for display:

1. Groups rows by `lap_number` into contiguous ranges
2. Filters to laps with >200 data points (~20+ seconds of data at 10Hz)
3. Among qualifying laps, selects the one with the **longest time span** (most complete clean lap)
4. Falls back to the lap with the most data points if no lap meets the 200-point threshold
5. Returns sub-arrays (zero-copy via `Float32Array.subarray()`) for distance, speed, throttle, brake, rpm, and gear

### ECharts Configuration

The telemetry chart renders three synchronized sub-charts in a single ECharts instance:

| Grid                | Y-Axis       | Series                                                                                             |
| ------------------- | ------------ | -------------------------------------------------------------------------------------------------- |
| Top (28% height)    | Speed (km/h) | Driver A Speed (blue), Driver B Speed (orange)                                                     |
| Middle (18% height) | 0–100        | Driver A Throttle (green), Driver A Brake (red), Driver B Throttle (lime), Driver B Brake (orange) |
| Bottom (18% height) | RPM          | Driver A RPM (purple), Driver B RPM (pink)                                                         |

All series use:

- **LTTB sampling**: Largest-Triangle-Three-Buckets downsampling for rendering performance
- **`large: true`**: Enables ECharts large data mode (GPU-accelerated rendering for >5k points)
- **Linked axis pointers**: Hovering on one sub-chart syncs the crosshair across all three
- **Data zoom**: Inside (drag) + slider zoom that controls all three x-axes simultaneously

---

## 14. Storage Layer (Cloudflare R2)

The R2 storage client (`r2_client.py`) is a singleton wrapper around `boto3` configured for Cloudflare R2's S3-compatible API.

### Configuration

```python
boto3.client(
    service_name="s3",
    endpoint_url=settings.R2_ENDPOINT_URL,
    aws_access_key_id=settings.R2_ACCESS_KEY_ID,
    aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
    region_name="auto"  # R2 uses 'auto' region
)
```

### Operations

| Method                                                 | Purpose                                              |
| ------------------------------------------------------ | ---------------------------------------------------- |
| `upload_file(file_path, object_name)`                  | Uploads a local file to R2                           |
| `generate_presigned_url(object_name, expiration=3600)` | Generates a time-limited download URL                |
| `read_file_stream(object_name)`                        | Returns a streaming body for in-memory Parquet reads |

### Why R2?

- **10GB free storage/month** — sufficient for multiple seasons of compressed Parquet telemetry
- **S3-compatible API** — drop-in replacement using boto3
- **No egress fees** — critical for a public-facing API serving telemetry downloads
- **Presigned URLs** — allows the frontend to download directly from R2 without proxying through the backend

---

## 15. Deployment & Infrastructure

### Backend Deployment

The backend is containerized via a **multi-stage Docker build**:

**Stage 1 (Builder)**:

- Base: `python:3.12-slim`
- Installs `build-essential` for compiling numpy/scipy C extensions
- Installs Poetry 1.8.3
- Runs `poetry install --without dev --no-root` (production-only dependencies)

**Stage 2 (Runtime)**:

- Base: `python:3.12-slim` (clean, no compiler toolchain)
- Copies only the `.venv` from the builder stage
- Copies application source
- Entrypoint: `gunicorn src.api.main:app -c gunicorn.conf.py`

### Gunicorn Configuration

```python
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
worker_class = "uvicorn.workers.UvicornWorker"
workers = 1          # Railway free tier: 1 vCPU, 512MB RAM
threads = 2          # Handles blocking Monte Carlo loops
timeout = 30         # Monte Carlo completes in <250ms
keepalive = 5
```

### Environment Variables

| Variable                   | Component | Purpose                                 |
| -------------------------- | --------- | --------------------------------------- |
| `NEON_DB_URL`              | Backend   | PostgreSQL connection string            |
| `R2_ACCOUNT_ID`            | Backend   | Cloudflare account identifier           |
| `R2_ACCESS_KEY_ID`         | Backend   | R2 API access key                       |
| `R2_SECRET_ACCESS_KEY`     | Backend   | R2 API secret key                       |
| `R2_TOKEN`                 | Backend   | R2 API token                            |
| `R2_BUCKET_NAME`           | Backend   | R2 bucket name                          |
| `R2_ENDPOINT_URL`          | Backend   | R2 S3-compatible endpoint               |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend  | Backend API URL for client-side fetches |

---

## 16. CLI Scripts & Tooling

### `ingest_race.py`

Ingests a single race's data (macro metadata + optional telemetry).

```bash
cd backend && poetry run python -m src.scripts.ingest_race \
  --year 2025 --gp "Australian Grand Prix" \
  --session R \
  --skip-telemetry  # Optional: skip heavy R2 upload
  --force           # Optional: overwrite existing data
  --dry-run         # Optional: preview without writing
```

### `ingest_season.py`

Ingests all races for an entire season by iterating over FastF1's event schedule. Automatically skips pre-season testing events (RoundNumber = 0). Continues to the next race if one fails.

```bash
cd backend && poetry run python -m src.scripts.ingest_season \
  --year 2025 --session R
```

### `calibrate_season.py`

Runs the 3-stage deterministic calibration pipeline for every race and compound in a season. For each `(circuit, compound)` combination:

1. Extracts clean segments via `TruthExtractor`
2. Runs `MathOptimizer.optimize()`
3. Upserts the fitted parameters into the `degradation_models` table

```bash
cd backend && poetry run python -m src.scripts.calibrate_season --year 2025
```

### `backfill_race_metadata.py`

One-time script to populate `circuit_length_km` and `total_laps` from hardcoded FIA data for all 24 circuits in the 2025 season. Used when FastF1's `circuit_info` doesn't provide length data.

```bash
cd backend && poetry run python -m src.scripts.backfill_race_metadata
```

### `set_r2_cors.py`

Configures CORS headers on the R2 bucket to allow browser-direct Parquet downloads from presigned URLs.

---

_End of Technical Document_
