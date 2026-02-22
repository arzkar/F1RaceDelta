import random
import numpy as np
import math
from typing import List, Dict, Optional
from pydantic import BaseModel

from src.domain.physics import DegradationModel, FuelModel
from src.domain.calibration import DeterministicSimulator

class OvertakeEvent(BaseModel):
    lap: int
    overtaking_driver: str
    overtaken_driver: str
    probability_computed: float
    successful: bool

class MonteCarloConfig(BaseModel):
    iterations: int = 1000
    degradation_variance_percent: float = 0.05
    dirty_air_penalty_seconds: float = 0.8
    overtake_delta_threshold_seconds: float = 0.5
    gap_threshold_seconds: float = 1.0

class HeadToHeadSimulator:
    """
    Executes a probabilistic simulation between two drivers racing a stint.
    Injects "Dirty Air" penalties and computes Overtake Sigmoids probabilistically.
    """
    def __init__(
        self,
        driver_a_code: str,
        driver_a_deg: DegradationModel,
        driver_a_fuel: FuelModel,
        driver_b_code: str,
        driver_b_deg: DegradationModel,
        driver_b_fuel: FuelModel,
        config: MonteCarloConfig
    ):
        self.driver_a = driver_a_code
        self.driver_b = driver_b_code

        self.sim_a = DeterministicSimulator(driver_a_deg, driver_a_fuel)
        self.sim_b = DeterministicSimulator(driver_b_deg, driver_b_fuel)

        self.config = config

    def _apply_variance(self, base_val: float, variance_percent: float) -> float:
        """Injects a Gaussian randomized variance bounded by a percentage margin."""
        std_dev = base_val * variance_percent
        return max(0.0001, random.gauss(base_val, std_dev))

    def _compute_overtake_probability(self, pace_advantage: float) -> float:
        """
        Computes overtaking likelihood using a Logistic function (Sigmoid).
        The larger the pacing advantage (`pace_advantage`), the higher the probability.
        Requires advantage to exceed threshold to yield >5% chance.
        """
        if pace_advantage <= 0:
            return 0.0

        # Steeper curve based on threshold limit (k=5 creates sharp activation edge)
        # Offset centers the 50% probability closer to the delta_threshold.
        k = 5.0
        offset = self.config.overtake_delta_threshold_seconds

        probability = 1.0 / (1.0 + math.exp(-k * (pace_advantage - offset)))
        return probability

    def run_probabilistic_iteration(
        self,
        base_lap_a: float,
        base_lap_b: float,
        total_laps: int,
        start_gap_ab: float = 2.0
    ) -> Dict:
        """
        Executes a single probabilistic race between A and B, maintaining running state.
        `start_gap_ab` > 0 implies A is ahead. < 0 implies B is ahead.
        """
        # Perturb the parameters slightly for THIS specific race iteration
        self.sim_a.degradation.alpha = self._apply_variance(self.sim_a.degradation.alpha, self.config.degradation_variance_percent)
        self.sim_b.degradation.alpha = self._apply_variance(self.sim_b.degradation.alpha, self.config.degradation_variance_percent)

        current_gap = start_gap_ab
        events = []

        # Reset Physical State
        self.sim_a.current_wear = 0.0
        self.sim_b.current_wear = 0.0

        history_a, history_b = [], []

        for lap in range(1, total_laps + 1):
            # Compute raw theoretical lap time mathematically
            lap_a = self.sim_a.run_stint(base_lap_a, lap, lap)[0]
            lap_b = self.sim_b.run_stint(base_lap_b, lap, lap)[0]

            time_a, time_b = lap_a.simulated_time_s, lap_b.simulated_time_s

            # Interactive Gap Logic
            driver_a_ahead = current_gap > 0
            abs_gap = abs(current_gap)

            if abs_gap < self.config.gap_threshold_seconds:
                # Driver trailing receives dirty air penalty slowing them down
                if driver_a_ahead:
                    time_b += self.config.dirty_air_penalty_seconds
                else:
                    time_a += self.config.dirty_air_penalty_seconds

            # Recompute gap after penalties
            gap_change = time_b - time_a # Positive means A was faster
            new_gap = current_gap + gap_change

            # Evaluate Overtake Mechanics if they swapped positions physically on the road
            if current_gap > 0 and new_gap <= 0:
                # B caught A. Did B truly overtake A safely?
                pace_advantage = time_a - (time_b - self.config.dirty_air_penalty_seconds)
                prob = self._compute_overtake_probability(pace_advantage)

                success = random.random() < prob
                events.append(OvertakeEvent(
                    lap=lap,
                    overtaking_driver=self.driver_b,
                    overtaken_driver=self.driver_a,
                    probability_computed=prob,
                    successful=success
                ))

                if success:
                    # Overtake sticks. Gap is now inverted.
                    current_gap = new_gap
                else:
                    # Cannot pass. Blocked tightly. Reset gap exactly behind defending car.
                    current_gap = 0.2
                    time_b = time_a + 0.1 # Forced slowdown behind

            elif current_gap < 0 and new_gap >= 0:
                # A caught B.
                pace_advantage = time_b - (time_a - self.config.dirty_air_penalty_seconds)
                prob = self._compute_overtake_probability(pace_advantage)

                success = random.random() < prob
                events.append(OvertakeEvent(
                    lap=lap,
                    overtaking_driver=self.driver_a,
                    overtaken_driver=self.driver_b,
                    probability_computed=prob,
                    successful=success
                ))

                if success:
                    current_gap = new_gap
                else:
                    current_gap = -0.2
                    time_a = time_b + 0.1
            else:
                current_gap = new_gap

            history_a.append(time_a)
            history_b.append(time_b)

        return {
            "driver_a_times": history_a,
            "driver_b_times": history_b,
            "final_gap": current_gap,
            "winner": self.driver_a if current_gap > 0 else self.driver_b,
            "events": events
        }

    def run_monte_carlo(self, base_lap_a: float, base_lap_b: float, total_laps: int, start_gap_ab: float = 2.0):
        """Executes Thousands of iterations and aggregates the winning percentages."""
        a_wins = 0
        b_wins = 0

        # Save absolute baseline parameters before we randomly mutate them locally
        def snapshot(mdl: DegradationModel):
            return { 'alpha': mdl.alpha, 'beta': mdl.beta }

        snap_a = snapshot(self.sim_a.degradation)
        snap_b = snapshot(self.sim_b.degradation)

        for i in range(self.config.iterations):
            # Restore baseline for clean iteration randomness
            self.sim_a.degradation.alpha = snap_a['alpha']
            self.sim_b.degradation.alpha = snap_b['alpha']

            result = self.run_probabilistic_iteration(base_lap_a, base_lap_b, total_laps, start_gap_ab)

            if result["winner"] == self.driver_a:
                a_wins += 1
            else:
                b_wins += 1

        return {
            "iterations_run": self.config.iterations,
            "win_probability_a": (a_wins / self.config.iterations) * 100.0,
            "win_probability_b": (b_wins / self.config.iterations) * 100.0
        }
