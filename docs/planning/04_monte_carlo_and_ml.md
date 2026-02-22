# Phase 4: Machine Learning & Behavior Cloning

## 🎯 Objective

Utilize the massive pool of granular Parquet telemetry to train machine learning models to map "Driver Behavior Profiles" and predict micro-sector times beneath the physics engine layer.

## 🛠 Required Work

### 1. Deep ML Pipeline

- [ ] **Behavior Profiling**: Train models classifying driver characteristics. E.g., identifying early apices, trail braking preferences, and throttle application aggression directly from telemetry traces.
- [ ] **Deep Tyre Degradation Networks**: Build NN pipelines predicting actual grip cliff events based on real-world telemetry wear signatures.
- [ ] **Micro-Sector Regressions**: Instead of predicting a lap time natively, predict the speed out of Corner 12 based on fuel load, and compound the micro-sectors into a lap time.

### 2. Monte Carlo Variance

- [ ] Build the variance loop. Injecting variance into the micro-physics model means randomizing brake points (+/- 5 meters) or changing throttle confidence levels on corner exits per iteration.
- [ ] Run `N` simulations to build wide probability curves of finishing times.

## 🤔 Open Questions for Refinement

- Will the ML training happen asynchronously via GitHub Actions/Modal/external workers and then purely served by our API, or are we hoping to train small incremental models locally?
