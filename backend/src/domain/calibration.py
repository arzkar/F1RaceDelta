import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from pydantic import BaseModel
from src.domain.physics import DegradationModel, FuelModel

class SimulatedLap(BaseModel):
    lap_number: int
    simulated_time_s: float
    tyre_wear: float
    fuel_mass_kg: float

class DeterministicSimulator:
    """
    Simulates a race stint without probabilistic variance (Safety Cars/Traffic logic)
    Useful for calibrating Base Physics params against historical Truth Data.
    """
    def __init__(self, degradation_model: DegradationModel, fuel_model: FuelModel, starting_fuel_kg: float = 110.0, starting_wear: float = 0.0):
        self.degradation = degradation_model
        self.fuel = fuel_model

        self.current_fuel_kg = starting_fuel_kg
        self.current_wear = starting_wear

    def run_stint(self, baseline_lap_time_s: float, start_lap: int, end_lap: int) -> List[SimulatedLap]:
        """
        Executes the linear piecewise degradation and fuel deduction loop across the stint laps.
        `baseline_lap_time_s` represents the theoretical 0-fuel, 0-wear lap time capability limit.
        """
        simulated_stint = []

        for lap in range(start_lap, end_lap + 1):
            # Accumulate wear iteratively
            self.current_wear += self.degradation.base_wear_rate

            # 1. Base Lap Capability
            lap_time = baseline_lap_time_s

            # 2. Add Tyres Drop-off Penalty
            lap_time += self.degradation.calculate_wear_penalty(self.current_wear)

            # 3. Add Fuel Weight Penalty
            lap_time += self.fuel.calculate_weight_penalty(self.current_fuel_kg)

            # Append simulation record
            simulated_stint.append(SimulatedLap(
                lap_number=lap,
                simulated_time_s=lap_time,
                tyre_wear=self.current_wear,
                fuel_mass_kg=self.current_fuel_kg
            ))

            # Deduct Fuel
            self.current_fuel_kg -= self.fuel.get_fuel_burn_per_lap()
            # F1 cars cannot run out of negative fuel
            self.current_fuel_kg = max(0.0, self.current_fuel_kg)

        return simulated_stint

def compute_rmse(actual_times: List[float], simulated_times: List[float]) -> float:
    """Computes the Root Mean Square Error natively bypassing heavier statistical packages."""
    if len(actual_times) != len(simulated_times) or len(actual_times) == 0:
        return float('inf')

    diff = np.array(actual_times) - np.array(simulated_times)
    mse = np.mean(diff ** 2)
    return float(np.sqrt(mse))
