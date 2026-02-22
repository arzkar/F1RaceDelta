# 🏎 F1RaceDelta

**Telemetry-Driven Race Simulation & Strategy Analytics for Formula 1**

F1RaceDelta is a full-stack motorsport analytics platform that ingests high-frequency Formula 1 telemetry, calibrates physics-informed degradation models against historical race data, and exposes a Monte Carlo simulation engine through a high-performance web dashboard.

It is designed to feel like a professional motorsport analytics product — not a hobby dashboard.

---

## 🚀 What It Does

F1RaceDelta turns raw telemetry into actionable race intelligence.

It allows users to:

- 📊 Visualize full-session telemetry (Speed, Throttle, RPM, Gear)
- 🧮 Analyze tyre degradation curves per track & compound
- 🏁 Simulate head-to-head strategy battles using calibrated models
- 🎲 Run Monte Carlo race simulations with probabilistic outcomes
- 📈 Inspect deterministic degradation models derived from real data

---

## 🧠 Core Concept

Instead of guessing race performance trends, F1RaceDelta:

1. Ingests historical F1 session data
2. Stores high-frequency telemetry in a compressed Parquet data lake
3. Calibrates degradation & fuel models against green-flag laps
4. Builds deterministic simulation engines from fitted parameters
5. Exposes Monte Carlo simulations via a REST API
6. Renders telemetry & strategy outcomes in-browser using WebGL charts

The result:

> A data-calibrated race simulation engine grounded in historical telemetry.

---

## 🏗 Architecture Overview

### Backend (FastAPI + Poetry + Docker)

- Deterministic physics & degradation engine
- Calibration layer using numerical optimization
- Monte Carlo simulation module
- NeonDB for metadata
- Cloudflare R2 for telemetry data lake
- Structured JSON logging
- Versioned REST API (`/api/v1`)
- Rate-limited public endpoints

### Frontend (Next.js 14 + TypeScript)

- Dark-mode premium dashboard
- Client-side Parquet decoding (WASM)
- Web Worker telemetry parsing
- Apache ECharts (Canvas/WebGL rendering)
- Zustand state management
- SaaS-ready layout structure

---

## 📂 Project Structure

```
.
├── backend/      # FastAPI backend, domain engine, calibration logic
├── frontend/     # Next.js dashboard & telemetry visualization
├── docs/         # Architecture & planning documents
├── cache/        # FastF1 local cache (ignored in git)
└── README.md
```

---

## 🧮 Simulation Philosophy

The system separates modeling into stages:

- **Phase 3** – Deterministic degradation & fuel modeling
- **Phase 4** – Historical calibration against race stints
- **Phase 5** – API exposure & Monte Carlo execution
- **Phase 6** – High-performance telemetry visualization

Calibration is deterministic and reproducible.

Monte Carlo simulations operate only on calibrated constants.

No random guesswork.
No hardcoded curves.
No artificial smoothing of safety car laps.

---

## 🎯 Design Goals

- Performance-first
- Deterministic modeling
- Clean separation of concerns
- Browser-side heavy data rendering
- SaaS-ready structure
- Motorsport-grade credibility

The UI aims to blend:

- F1 TV Pro telemetry density
- Apple-level polish & motion discipline
- Enterprise-grade structure

---

## 🛠 Running Locally

### Backend

```bash
cd backend
poetry install
poetry run uvicorn src.api.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## 🌍 Deployment

Backend is containerized via Docker and deployed to Railway.

- Gunicorn + Uvicorn workers
- Public, rate-limited API
- Presigned R2 telemetry routing
- Structured production logging

---

## 📊 Current Capabilities

- Telemetry ingestion & storage
- Parquet-based data lake
- Deterministic tyre degradation modeling
- Calibration against historical green-flag laps
- Head-to-head Monte Carlo simulation
- High-density Canvas-based chart rendering

---

## 🔮 Future Extensions

- User accounts & saved strategies
- Multi-race comparative modeling
- Temperature & track evolution modeling
- Real-time telemetry ingestion
- Premium strategy analysis features

---

## ⚖ Disclaimer

This project uses publicly available telemetry and modeling techniques for analytical purposes only.
It is not affiliated with Formula 1 or any official team.

---

## 👨‍💻 Author

Built as a full-stack engineering + quantitative modeling project focused on performance, architecture, and product quality.
