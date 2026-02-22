# Phase 6: Frontend Dashboard & Data Streaming

## 🎯 Objective

Construct an incredibly visually rich Next.js frontend capable of rendering and streaming live high-frequency telemetry charts flawlessly at 60FPS.

## 🛠 Required Work

### 1. High-Performance Charting Engine

- [ ] Since standard chart libraries (like Recharts/Chart.js) choke and lag heavily when attempting to render 5,000+ points on a line, we must adopt an HTML5 Canvas or WebGL engine.
- [ ] Integrate highly optimized libraries like `uPlot` or Apache `ECharts` to stack Throttle/Brake/Speed traces smoothly along distance.

### 2. Direct Telemetry Downloading (Client-Side)

- [ ] Implement client-side `parquet.js` or `arrow` decoding to parse the downloaded telemetry files directly in the user's browser, vastly taking the load off the backend server.
- [ ] Sync chart axes across the different metrics (Speed matches RPM, matches Braking distance).

### 3. Simulation Playground

- [ ] Build the interactive lap-by-lap simulation views (comparing Physics vs. ML predictions).
- [ ] Handle Server-Sent Events (SSE) from the API so the Monte Carlo progress bars load dynamically.

### 4. Deployment Infrastructure

- [ ] Ensure proper environment variables point to the R2 Cloud buckets and NeonDB.
- [ ] Dockerize the environment utilizing a robust multi-stage Docker build to keep the image tight.
