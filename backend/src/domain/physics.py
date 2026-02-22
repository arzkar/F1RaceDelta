from pydantic import BaseModel, Field
import math
from typing import Dict, Any

class DegradationModel(BaseModel):
    """
    Implements a piecewise Lap-Based Wear Accumulation model.
    It executes a linear grip loss up to a predefined `cliff_threshold`,
    and then drops off exponentially.
    """
    track_name: str
    compound: str

    # Linear parameters
    base_wear_rate: float = Field(..., description="The fundamental flat wear added every single lap")
    alpha: float = Field(..., description="The linear slope of degradation (seconds lost per wear point)")

    # Cliff parameters
    cliff_threshold: float = Field(..., description="The accumulated wear point at which the tyre falls off the cliff")
    beta: float = Field(..., description="The exponential severity multiplier after the cliff")
    gamma: float = Field(..., description="The exponential growth rate after the cliff")

    def calculate_wear_penalty(self, current_wear: float) -> float:
        """
        Given the current cumulative wear of a tyre, calculates the
        expected lap time penalty (in seconds) due to degradation.
        """
        if current_wear < self.cliff_threshold:
            # Linear Phase
            return self.alpha * current_wear
        else:
            # Exponential Cliff Phase
            linear_max = self.alpha * self.cliff_threshold
            exponential_penalty = self.beta * math.exp(self.gamma * (current_wear - self.cliff_threshold))
            return linear_max + exponential_penalty

class FuelModel(BaseModel):
    """
    Implements a deterministic Track-Length Dependent Constant Burn.
    No throttle-based integration is used to ensure pure stability.
    """
    track_length_km: float
    fuel_per_km_kg: float = Field(..., description="The theoretical kg of fuel burned per kilometer")
    fuel_time_penalty_per_kg: float = Field(..., description="The lap time penalty (seconds) per kg of fuel. Usually ~0.035s")

    def get_fuel_burn_per_lap(self) -> float:
        """Returns how many kg of fuel is burned exactly per complete lap."""
        return self.fuel_per_km_kg * self.track_length_km

    def calculate_weight_penalty(self, current_fuel_mass_kg: float) -> float:
        """
        Returns the lap time penalty (in seconds) incurred by the current weight of the car.
        As fuel burns, this penalty decreases naturally making the car faster.
        """
        return current_fuel_mass_kg * self.fuel_time_penalty_per_kg
