# Phase 5: API Layer

## 🎯 Objective

Provide robust HTTP routes capable of returning massive metadata and returning efficient, streamable interfaces for the big `parquet` data to the Frontend.

## 🛠 Required Work

### 1. High-Performance API Structure

- [ ] Standardize the FastAPI setup with robust Pydantic modeling.
- [ ] Implement robust background tasks/async event loops to prevent blocking when the app inevitably has to download/parse S3 parquet chunks into memory.

### 2. S3 Integration / Data Routing

- [ ] To avoid the FastAPI server blowing up its memory limit or bandwidth sending 100MB of telemetry JSON to the Frontend, the API MUST issue **Pre-Signed S3/R2 URLs**.
- [ ] Flow: Frontend requests lap telemetry -> FastAPI checks NeonDB for lap URL -> FastAPI signs a temporary short-lived URL from Cloudflare R2 -> Frontend downloads the lightweight Parquet directly from the edge CDN.
- [ ] **Data Resiliency (Missing Telemetry)**: The API must explicitly handle cases where `Lap.telemetry_file_path` is `NULL` (from driver dropouts/incomplete upstream data). It should return a clean `204 No Content` or a structured `404` indicating missing telemetry so the Frontend can gracefully disable charts for that driver without throwing unhandled exceptions.

### 3. Simulation Endpoints

- [ ] `POST /simulate/physics` - Accepts parameters for a micro-simulation race.
- [ ] Build WebSockets or Server-Sent Events (SSE) for the `/simulate/monte-carlo` endpoint so the user sees live probability curve updates as the iterations run behind the scenes!

## 🤔 Open Questions for Refinement

- Utilizing WebSockets/SSE for the live simulation streaming is amazing for UX, but requires slightly more effort to wire into FastAPI than typical REST. Are we comfortable pushing for SSEs?
