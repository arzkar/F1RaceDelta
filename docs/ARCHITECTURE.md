# F1RaceDelta -- System Architecture & Database Design Document

Author: Arbaaz Laskar
Project: F1RaceDelta
Version: v0.1
Status: Design Phase

---

# 1. Project Philosophy

F1RaceDelta is a backend-first, domain-driven race modeling engine.

It is designed to:

- Ingest historical Formula 1 session data
- Normalize and structure telemetry into clean domain models
- Model tyre degradation mathematically
- Simulate race strategies lap-by-lap
- Run Monte Carlo probabilistic simulations
- Compare physics-based models with ML-based predictions
- Remain modular, testable, and extensible

The system prioritizes:

- Clean architecture
- Explicit modeling assumptions
- Reproducibility
- Backend independence from UI
- SaaS optionality without architectural compromise

---

# 2. Technology Decisions

## 2.1 Database: NeonDB (Serverless Postgres) + Cloud Storage (R2/S3)

We intentionally selected NeonDB over Supabase for relational data, combined with a Cloud Object Store (like Cloudflare R2 or AWS S3) for high-frequency telemetry.

**Rationale for Hybrid Approach:**

- **Pure Postgres** without opinionated auth coupling for managing races, drivers, stints, and lap metadata.
- **Data Volume Reality:** FastF1 provides ~10-20Hz telemetry (Speed, RPM, Gear, Throttle, Brake) per car. 20 cars _ 60 laps _ 10Hz = ~2M rows per race. A full 24-race season generates ~10GB of raw telemetry.
- **Cost Efficiency:** NeonDB Free Tier is capped at 500MB, which would be exhausted in just 2 races. By storing the heavy `telemetry` traces as highly compressed `.parquet` files in a free/cheap Cloud Storage bucket (e.g., Cloudflare R2 offers 10GB free/month), the Postgres database stays extremely lean and fast.
- **Resiliency:** Built to handle inherently missing or incomplete upstream FastF1 data gracefully. If a driver drops out or the API is incomplete, their telemetry processing is aborted cleanly leaving their Cloudflare Object pointer `NULL` in the Postgres DB, without failing the ingestion loop.

Authentication and SaaS features are deferred to Phase 8.

---

# 3. System Architecture Overview

High-level architecture:

\[ FastF1 Data Ingestion \]
↓
\[ Data Normalization Layer \]
↙ ↘
\[ Highly Compressed Parquet \] \[ Structured Postgres Storage \]
\[ (Telemetry in R2/S3) ] \[ (Macro Metadata in NeonDB) \]
↘ ↙
\[ Domain Modeling Engine (Micro-Physics) \]
↓
\[ Simulation Engine \]
↓
\[ Machine Learning Layer (Behavior Cloning) \]
↓
\[ FastAPI REST Interface \]
↓
\[ Next.js Frontend (High-Perf WebGL/Canvas Charts) \]

Key principles:

- Domain logic must not depend on database
- Simulation engine must run independently of HTTP layer
- API layer must be thin
- Database is structured, not raw-blob storage

---

# 4. Data Strategy

## 4.1 Hybrid Data Storage

Raw FastF1 session data will NOT be stored as massive continuous blobs in Postgres.

Instead:

1.  Fetch high-frequency session telemetry (Car data & Positional GPS) via FastF1.
2.  Clean and normalize (smooth GPS jumps, interpolate missing dropped frames).
3.  Segment telemetry precisely by `lap_id` or `stint_id`.
4.  Export micro-telemetry traces (Speed, RPM, Gear, Throttle, Brake, DRS, X, Y, Z, Distance) as `.parquet` files.
5.  Upload `.parquet` files to Cloudflare R2 / AWS S3.
6.  Store structured summary entities (Drivers, Laps, Stints, S3 URLs) in NeonDB.

This standard "Data Lake" architecture allows the simulation engine to stream telemetry effortlessly via Pandas/Polars while keeping Postgres queries lightning fast.

---

# 5. Database Schema Design

All tables follow:

- UUID primary keys
- Explicit foreign key relationships
- Indexed fields for simulation queries
- No implicit coupling

---

## 5.1 races

Fields:

- id (UUID, PK)
- season (INT)
- grand_prix (VARCHAR)
- circuit (VARCHAR)
- circuit_length_km (FLOAT)
- total_laps (INT)
- race_date (DATE)
- created_at (TIMESTAMP)

Indexes: - (season, grand_prix)

---

## 5.2 drivers

Fields:

- id (UUID, PK)
- driver_code (VARCHAR, e.g. VER, HAM)
- full_name (VARCHAR)
- team (VARCHAR)
- season (INT)

Indexes: - (driver_code, season)

---

## 5.3 stints

Represents a tyre stint.

Fields:

- id (UUID, PK)
- race_id (FK → races)
- driver_id (FK → drivers)
- compound (VARCHAR)
- start_lap (INT)
- end_lap (INT)
- stint_length (INT)
- created_at (TIMESTAMP)

Indexes: - (race_id) - (driver_id) - (compound)

---

## 5.4 laps

Stores cleaned lap metadata and acts as the pointer to the heavy telemetry files.

Fields:

- id (UUID, PK)
- stint_id (FK → stints)
- lap_number (INT)
- lap_time_seconds (FLOAT)
- sector_1_seconds (FLOAT)
- sector_2_seconds (FLOAT)
- sector_3_seconds (FLOAT)
- track_status (VARCHAR)
- is_green_flag (BOOLEAN)
- fuel_estimate_kg (FLOAT, nullable)
- telemetry_file_path (VARCHAR, nullable) -> Pointer to S3/R2 .parquet file
- created_at (TIMESTAMP)

Indexes: - (stint_id) - (lap_number)

---

## 5.5 micro_sectors (New)

Optional structured table to mathematically model specific corner speeds instead of full laps.

Fields:

- id (UUID, PK)
- lap_id (FK → laps)
- corner_number (INT)
- entry_speed_kmh (FLOAT)
- apex_speed_kmh (FLOAT)
- exit_speed_kmh (FLOAT)

---

## 5.6 degradation_models

Stores computed degradation model parameters.

Fields:

- id (UUID, PK)
- race_id (FK → races)
- driver_id (FK → drivers)
- compound (VARCHAR)
- model_type (VARCHAR)
- coefficient_primary (FLOAT)
- coefficient_secondary (FLOAT, nullable)
- r_squared (FLOAT)
- cliff_lap_estimate (INT, nullable)
- created_at (TIMESTAMP)

Indexes: - (race_id, driver_id, compound)

---

# 6. Domain Layer Design

Domain models must be pure Python classes.

Rules:

- No DB calls
- No HTTP logic
- Pure mathematical logic
- Fully unit testable

---

# 7. Simulation Engine Design

The engine must support thousands of simulations per second-scale batch, emphasizing stability and rigorous calibration over fake precision.

## 7.1 Telemetry-Informed Preprocessing

- Do not simulate raw 10Hz loops.
- Slices laps into ~150-300 **micro-sectors**.
- Pre-computes `baseline_time`, `baseline_speed`, and `load_proxies` to generate deterministic fast-execution arrays.

## 7.2 Piecewise Degradation Model

- **Lap-Based Wear Accumulation**: `wear_n = wear_(n-1) + base_wear_rate`
- **Grip Model**: Linear degradation curve (`alpha * wear`) up to a predefined `cliff_threshold`.
- **The Cliff**: Exponential drop (`beta * exp(gamma * (wear - cliff_threshold))`) if pushed past limits.

## 7.3 Linear Fuel Physics

- **Track-length Dependent Constant Burn**: `fuel_per_lap = fuel_per_km * track_length_km`.
- **Time Penalty Formulation**: `lap_time_delta = fuel_mass * fuel_time_penalty_per_kg`.
- No dynamic throttle-based integration in v1 to preserve computational speed.

## 7.4 Two-Driver Overtaking Strategy

- Single-driver simulated baseline running deterministic undercut logic.
- Gap closure triggers "Dirty Air penalty".
- Compute overtake probability via sigmoid logic. Resolve via Monte Carlo. No full 20-car grid physics modeled in v1.

---

# 8. Calibration & Monte Carlo Engine

Monte Carlo requires structured repeated simulation with controlled randomness.

1. **Deterministic Calibration Mode (Critical)**
   - Simulator loads real stint lap times and runs deterministically.
   - Computes Root Mean Square Error (RMSE) against actual historical trace.
   - Optimizes degradation/fuel parameters saving them to `degradation_models` DB table constrainted to < 0.2-0.3 sec error margins.

2. **Probabilistic Monte Carlo Mode**
   - Takes calibrated baseline params and applies slight statistical variances (2-5% degradation slope shifts).
   - Generates finishing distribution probabilities.

---

# 9. Explicit Non-Goals (Scope Containment)

**Out of Scope for v1:**

- ERS Battery & Harvesting Simulation
- True Tyre Thermodynamics
- Brake Temperature Modeling
- Suspension Dynamics
- Full 20-Car Grid Racecraft processing

The priority of this backend is building a **Calibrated, Explainable, Telemetry-Informed Race Strategy Simulator with Probabilistic Forecasting**, not a full vehicle dynamics game engine.

---

# 10. API Design

FastAPI must expose:

- GET /races/{year}/{gp}
- POST /simulate/degradation
- POST /simulate/strategy
- POST /simulate/monte-carlo

All simulation endpoints must be stateless.

---

# 11. No Authentication (Initial Phases)

Public-first platform.

Future auth will wrap endpoints without modifying simulation logic.

---

# 12. Deployment Strategy

- Dockerized backend
- Separate ML worker (optional)
- NeonDB hosted instance
- Frontend deployed independently
- Redis optional for caching

---

# 13. Engineering Quality Requirements

- High unit test coverage in domain layer
- Explicit modeling documentation
- Type hints everywhere
- Pydantic validation for inputs
- Linting + formatting enforced

---

# 14. Long-Term Evolution

Future roadmap:

- User accounts
- Saved simulation history
- Public API access
- Paid advanced simulation tier
- CLI simulation tool
- Strategy optimization solver

---

# 15. Success Criteria

F1RaceDelta is successful if:

- A backend engineer respects the architecture
- A data scientist respects the modeling
- An F1 analyst respects the assumptions
- The system is modular and extensible
- It becomes a signature technical project

---

End of Document
