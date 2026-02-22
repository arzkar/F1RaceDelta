# Phase 2: Data Ingestion & Normalization Layer

## 🎯 Objective

Fetch high-frequency historical Formula 1 session telemetry (10-20Hz) via FastF1. Clean the GPS and trace anomalies, segment data precisely down to the lap distance, and export the heavy arrays to `.parquet` in Cloud Storage while saving relationship mappings in NeonDB.

## 🛠 Required Work

### 1. FastF1 Ingestion Pipeline

- [ ] Build a reliable fetcher utilizing the `fastf1` library.
- [ ] Pull core session metadata, lap times, and the massive `session.telemetry` DataFrames (Speed, RPM, Gear, Throttle, Brake, DRS, X/Y/Z).

### 2. High-Frequency Normalization

- [ ] **GPS/Telemetry Smoothing**: FastF1 data can feature GPS jumps or missing rows. Write pandas/polars logic to interpolate and smooth these anomalies.
- [ ] **Data Alignment**: Ensure Distance metrics (`DistanceToDriverAhead` and absolute track distance) perfectly align with the lap milestones.
- [ ] **Segmentation**: Slice the giant continuous telemetry array strictly by driver and lap, mapping it into `stints`.

### 3. Hybrid Persistence Pipeline

- [ ] **Heavy Lifting**: Convert the normalized Pandas telemetry DataFrames for each lap into highly compressed `.parquet` files to reduce disk footprint massively vs CSV/JSON.
- [ ] **Cloud Upload**: Stream the `.parquet` files directly to Cloudflare R2 / S3.
- [ ] **Metadata Logging**: Once uploaded, insert the `Lap` row in NeonDB, saving the generated `s3://f1racedelta/.../lap_id.parquet` URL in the database.
- [ ] **Data Resiliency (Handling Incomplete API Data)**: If FastF1 returns incomplete position or car data for a specific driver (e.g. `Position data is incomplete!`), skip exactly that driver without failing the ingestion run. The `telemetry_file_path` in NeonDB will cleanly remain `NULL` for those laps.

## 🤔 Open Questions for Refinement

- We will be processing heavily using DataFrames. Should we opt for `polars` instead of `pandas` to speed up the ingestion and normalization since it's orders of magnitude faster in Python?
