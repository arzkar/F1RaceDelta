import pytest
import math
from src.domain.physics import DegradationModel, FuelModel
from src.domain.calibration import DeterministicSimulator, compute_rmse
from src.domain.monte_carlo import HeadToHeadSimulator, MonteCarloConfig

def test_fuel_model_linear_deduction():
    # Bahrain is approx 5.412 km
    fuel = FuelModel(
        track_length_km=5.412,
        fuel_per_km_kg=1.7, # Heavy 1.7kg burn per km
        fuel_time_penalty_per_kg=0.035
    )

    # Check exact lap burn amount
    assert math.isclose(fuel.get_fuel_burn_per_lap(), 5.412 * 1.7, rel_tol=1e-5)

    # Check time penalty for a starting 110kg car
    penalty = fuel.calculate_weight_penalty(110.0)
    assert math.isclose(penalty, 110.0 * 0.035, rel_tol=1e-5)


def test_degradation_piecewise_cliff():
    deg = DegradationModel(
        track_name="Bahrain",
        compound="SOFT",
        base_wear_rate=1.0, # 1 point per lap
        alpha=0.05,         # 0.05s lost per wear point linearly
        cliff_threshold=15.0, # Falls off a cliff after 15 laps
        beta=0.2,
        gamma=0.5
    )

    # Linear Dropoff check (Lap 10)
    # Expected: 10 * 0.05 = 0.5s drop
    assert math.isclose(deg.calculate_wear_penalty(10.0), 0.5, rel_tol=1e-5)

    # Cliff Edge Check (Lap 15)
    assert math.isclose(deg.calculate_wear_penalty(15.0), 15.0 * 0.05 + 0.2, rel_tol=1e-5)

    # Post-Cliff Check (Lap 17 -> wear=17, +2 over cliff)
    # 0.75 (linear max) + 0.2 * exp(0.5 * 2) = 0.75 + 0.2 * e^1 = 0.75 + 0.5436 = 1.2936
    expected_cliff_drop = 0.75 + 0.2 * math.exp(0.5 * 2.0)
    assert math.isclose(deg.calculate_wear_penalty(17.0), expected_cliff_drop, rel_tol=1e-5)


def test_deterministic_simulator():
    deg = DegradationModel(
        track_name="Test", compound="SOFT",
        base_wear_rate=1.0, alpha=0.05, cliff_threshold=15.0, beta=0.2, gamma=0.5
    )
    fuel = FuelModel(track_length_km=5.0, fuel_per_km_kg=1.5, fuel_time_penalty_per_kg=0.03)

    sim = DeterministicSimulator(deg, fuel, starting_fuel_kg=100.0, starting_wear=0.0)

    # Simulate a 5 lap stint with a theoretical perfect 90.0s baseline
    history = sim.run_stint(baseline_lap_time_s=90.0, start_lap=1, end_lap=5)

    assert len(history) == 5
    assert history[0].lap_number == 1

    # Verify fuel was deducted correctly over 5 laps
    # In the loop, the `fuel_mass_kg` saved to history is the weight *at the start of the lap*.
    # Lap 1 start: 100.0, Lap 2: 92.5, Lap 3: 85.0, Lap 4: 77.5, Lap 5: 70.0kg
    assert math.isclose(history[4].fuel_mass_kg, 70.0, rel_tol=1e-5)


def test_rmse_calculator():
    actual = [91.0, 91.5, 92.0]
    simulated = [91.0, 91.5, 92.5]

    # MSE should be mean( [0, 0, -0.5]^2 ) => mean( [0, 0, 0.25] ) => 0.08333
    # RMSE = sqrt(0.08333) = 0.28867
    rmse = compute_rmse(actual, simulated)
    assert math.isclose(rmse, 0.28867, rel_tol=1e-4)


def test_monte_carlo_sigmoid_overtake():
    deg = DegradationModel(
        track_name="Test", compound="SOFT", base_wear_rate=1.0, alpha=0.05, cliff_threshold=15.0, beta=0.2, gamma=0.5
    )
    fuel = FuelModel(track_length_km=5.0, fuel_per_km_kg=1.5, fuel_time_penalty_per_kg=0.03)

    config = MonteCarloConfig(overtake_delta_threshold_seconds=0.5)

    mc = HeadToHeadSimulator("VER", deg, fuel, "HAM", deg, fuel, config)

    # Test strict Sigmoid probability limits
    prob_no_advantage = mc._compute_overtake_probability(0.0)
    assert prob_no_advantage == 0.0

    prob_small_advantage = mc._compute_overtake_probability(0.1) # 0.4s under threshold
    assert prob_small_advantage < 0.20 # Should be very low chance < 20%

    # Massive overspeed => practically guaranteed overtake
    prob_huge = mc._compute_overtake_probability(2.5)
    assert prob_huge > 0.95
