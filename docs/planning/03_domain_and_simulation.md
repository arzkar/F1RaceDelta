# Phase 3: Domain Layer & Micro-Simulation Engine

## 🎯 Objective

Build a mathematically rich domain layer capable of digesting high-frequency telemetry. Pivot from pure "lap-time math" to "micro-physics", modeling traction, braking, and energy curves over track distance.

## 🛠 Required Work

### 1. Data Lake Consumer

- [ ] Build an efficient `boto3` reader that intelligently fetches and caches `.parquet` files into memory during a simulation execution, extracting track boundaries and reference telemetry curves.

### 2. The Micro-Simulation Engine

- [ ] **Distance-based State**: Rather than iterating lap-by-lap, the engine increments state by distance or time steps simulating a car travelling across X/Y coordinates.
- [ ] **Traction & Braking Model**: Compute theoretical braking points and acceleration limits based on historical telemetry. Simulate what happens to lap time when we apply +5% brake efficiency.
- [ ] **Dynamic Fuel Physics**: Calculate fuel burn precisely based on total time at 100% throttle for a given lap, rather than a flat kg/lap deduction.
- [ ] **Energy Recovery System (ERS)**: Model battery charging under braking zones and deployment on straights.

### 3. Enhanced Degradation Modelling

- [ ] Model tyre temperature and slip angle. Degradation shouldn't be a flat curve; it's a consequence of the cumulative energy pushed through the tyres during heavy cornering forces over the previous laps.
- [ ] Write unit tests simulating full stint telemetry loads.

## 🤔 Open Questions for Refinement

- Running micro-physics step-by-step for a full race distance is computationally heavy. Are we comfortable with standard Python for this, or will we need to vectorize the simulation loop heavily via NumPy/C bindings?
