import logging
import numpy as np
from typing import List, Tuple, Dict, Any, Optional
from scipy.optimize import minimize
from pydantic import BaseModel

from src.calibration.truth_extractor import ContinuousStintSegment
from src.domain.physics import DegradationModel, FuelModel
from src.domain.calibration import DeterministicSimulator

logger = logging.getLogger(__name__)

class CalibrationResult(BaseModel):
    alpha: float
    base_wear_rate: float
    cliff_threshold: float
    beta: float
    gamma: float
    fuel_per_km: float
    fuel_time_penalty_per_kg: float
    rmse_score: float
    mae_score: float
    r_squared: float
    sample_count: int

class MathOptimizer:
    """
    Executes a strict 3-Stage Deterministic mathematical fitting solver to isolate
    the actual track/compound degradation variables.
    """
    def __init__(self, track_name: str, circuit_length_km: float, compound: str):
        self.track_name = track_name
        self.circuit_length_km = circuit_length_km
        self.compound = compound

        # Initial Physics Shells
        self.deg = DegradationModel(
            track_name=self.track_name, compound=self.compound,
            base_wear_rate=0.0, alpha=0.0, cliff_threshold=999.0, beta=0.0, gamma=0.0
        )
        self.fuel = FuelModel(
            track_length_km=self.circuit_length_km,
            fuel_per_km_kg=1.5,
            fuel_time_penalty_per_kg=0.035
        )

    def _score_rmse(self, actual: List[float], predicted: List[float]) -> float:
        return float(np.sqrt(np.mean((np.array(actual) - np.array(predicted))**2)))

    def _score_mae(self, actual: List[float], predicted: List[float]) -> float:
        return float(np.mean(np.abs(np.array(actual) - np.array(predicted))))

    def _score_r2(self, actual: List[float], predicted: List[float]) -> float:
        y = np.array(actual)
        y_pred = np.array(predicted)
        ss_res = np.sum((y - y_pred)**2)
        ss_tot = np.sum((y - np.mean(y))**2)
        if ss_tot == 0.0:
            return 0.0
        return float(1 - (ss_res / ss_tot))

    def _simulate_scipy_segment(self, segment: ContinuousStintSegment, active_baseline: float) -> List[float]:
        """
        Runs the Deterministic Simulator on a single mathematically clean segment.
        Returns the raw float array of predicted lap times.
        """
        # Starting configuration for the simulation based on where THIS segment occurred in the stint
        starting_wear = float(segment.starting_wear_laps) * self.deg.base_wear_rate
        sim = DeterministicSimulator(self.deg, self.fuel, starting_fuel_kg=110.0, starting_wear=starting_wear)

        # Force the fuel tank to roughly exactly where it would be natively in the entire race
        # Fuel burn is tied to the absolute lap number, not the tyre's stint age.
        absolute_laps_completed = segment.lap_numbers[0] - 1
        sim.current_fuel_kg -= self.fuel.get_fuel_burn_per_lap() * absolute_laps_completed

        laps = sim.run_stint(
            baseline_lap_time_s=active_baseline,
            start_lap=segment.lap_numbers[0],
            end_lap=segment.lap_numbers[-1]
        )

        return [l.simulated_time_s for l in laps]

    def _objective_stage_1(self, params: np.ndarray, segments: List[ContinuousStintSegment], baselines: Dict[str, float]) -> float:
        """Stage 1: Fit only Fuel params on the early laps."""
        self.fuel.fuel_per_km_kg, self.fuel.fuel_time_penalty_per_kg = params

        predictions, actuals = [], []
        for seg in segments:
            # Stage 1 only looks at early stints!
            if seg.starting_wear_laps < 10:
                p_laps = self._simulate_scipy_segment(seg, baselines[seg.driver_code])
                predictions.extend(p_laps)
                actuals.extend(seg.lap_times)

        if not predictions:
            return 999.0
        return self._score_rmse(actuals, predictions)

    def _objective_stage_2(self, params: np.ndarray, segments: List[ContinuousStintSegment], baselines: Dict[str, float]) -> float:
        """Stage 2: Fit Linear Degradation on mid-stint laps."""
        self.deg.alpha, self.deg.base_wear_rate = params

        predictions, actuals = [], []
        for seg in segments:
            # Avoid the deep cliff
            if seg.starting_wear_laps < 25:
                p_laps = self._simulate_scipy_segment(seg, baselines[seg.driver_code])
                predictions.extend(p_laps)
                actuals.extend(seg.lap_times)

        if not predictions:
            return 999.0
        return self._score_rmse(actuals, predictions)

    def _objective_stage_3(self, params: np.ndarray, segments: List[ContinuousStintSegment], baselines: Dict[str, float]) -> float:
        """Stage 3: Fit Cliff parameters on all laps."""
        self.deg.cliff_threshold, self.deg.beta, self.deg.gamma = params

        predictions, actuals = [], []
        for seg in segments:
            p_laps = self._simulate_scipy_segment(seg, baselines[seg.driver_code])
            predictions.extend(p_laps)
            actuals.extend(seg.lap_times)

        if not predictions:
            return 999.0
        return self._score_rmse(actuals, predictions)

    def optimize(self, clean_segments: List[ContinuousStintSegment]) -> Optional[CalibrationResult]:
        """Runs the deterministic bounded SciPy 3-stage optimization."""
        if not clean_segments:
            return None

        # Determine individual driver baselines (their fastest theoretical raw limit lap)
        # To avoid skewing, we select the absolute fastest lap this driver ever set on this compound in the entire dataset
        # and subtract the fuel/deg weight bounds manually roughly, or just use their 5th percentile best lap.
        baselines = {}
        for seg in clean_segments:
            code = seg.driver_code
            fastest = min(seg.lap_times)
            if code not in baselines or fastest < baselines[code]:
                # We deduct 1 second off their fastest actual lap as an aggressive theoretical baseline
                # The optimizer will use fuel and wear to build back UP to their actual driven pace.
                baselines[code] = fastest - 1.0

        total_samples = sum(len(s.lap_times) for s in clean_segments)
        logger.info(f"Starting 3-Stage Mathematical Fit across {len(clean_segments)} segments ({total_samples} laps).")

        # --- STAGE 1 (Fuel) ---
        res1 = minimize(
            self._objective_stage_1,
            x0=[1.5, 0.035], # Initial Guesses
            args=(clean_segments, baselines),
            method='L-BFGS-B',
            bounds=[(0.5, 3.0), (0.02, 0.06)] # fuel_per_km, penalty_per_kg
        )
        self.fuel.fuel_per_km_kg, self.fuel.fuel_time_penalty_per_kg = res1.x

        # --- STAGE 2 (Linear Deg) ---
        res2 = minimize(
            self._objective_stage_2,
            x0=[0.05, 1.0],
            args=(clean_segments, baselines),
            method='L-BFGS-B',
            bounds=[(0.0, 0.15), (0.0, 0.2)] # alpha, base_wear_rate
        )
        self.deg.alpha, self.deg.base_wear_rate = res2.x

        # --- STAGE 3 (Cliff Parameters) ---
        # Did anyone even run long enough to hit a cliff? Check max wear.
        max_theoretical_wear = max(s.starting_wear_laps + len(s.lap_times) for s in clean_segments) * self.deg.base_wear_rate
        if max_theoretical_wear > 10.0:
            res3 = minimize(
                self._objective_stage_3,
                x0=[15.0, 0.2, 0.5],
                args=(clean_segments, baselines),
                method='L-BFGS-B',
                bounds=[(5.0, 40.0), (0.0, 5.0), (0.0, 5.0)] # cliff, beta, gamma
            )
            self.deg.cliff_threshold, self.deg.beta, self.deg.gamma = res3.x
        else:
            # No cliff reached mathematically. Disable it.
            self.deg.cliff_threshold = 999.0
            self.deg.beta = 0.0
            self.deg.gamma = 0.0

        # --- FINAL SCORING ---
        predictions, actuals = [], []
        for seg in clean_segments:
            p_laps = self._simulate_scipy_segment(seg, baselines[seg.driver_code])
            predictions.extend(p_laps)
            actuals.extend(seg.lap_times)

        rmse = self._score_rmse(actuals, predictions)
        mae = self._score_mae(actuals, predictions)
        r2 = self._score_r2(actuals, predictions)

        return CalibrationResult(
            alpha=self.deg.alpha,
            base_wear_rate=self.deg.base_wear_rate,
            cliff_threshold=self.deg.cliff_threshold,
            beta=self.deg.beta,
            gamma=self.deg.gamma,
            fuel_per_km=self.fuel.fuel_per_km_kg,
            fuel_time_penalty_per_kg=self.fuel.fuel_time_penalty_per_kg,
            rmse_score=rmse,
            mae_score=mae,
            r_squared=r2,
            sample_count=total_samples
        )
