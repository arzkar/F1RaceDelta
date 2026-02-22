import logging
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from src.db.models.race import Race
from src.db.models.stint import Stint
from src.db.models.lap import Lap
from src.db.models.driver import Driver

logger = logging.getLogger(__name__)

class ContinuousStintSegment:
    """
    Represents a perfectly clean, uninterrupted sequence of green-flag laps
    for a specific driver on a specific compound.
    """
    def __init__(self, driver_code: str, starting_wear_laps: int):
        self.driver_code = driver_code
        self.starting_wear_laps = starting_wear_laps # The tyre age at the start of THIS specific uninterrupted segment
        self.lap_numbers: List[int] = []
        self.lap_times: List[float] = []
        self.fuel_weights_kg: List[float] = []

    def add_lap(self, lap_number: int, lap_time_s: float, fuel_kg: float):
        self.lap_numbers.append(lap_number)
        self.lap_times.append(lap_time_s)
        self.fuel_weights_kg.append(fuel_kg)

    @property
    def is_valid(self) -> bool:
        # Require at least 3 consecutive laps to be considered a mathematically viable segment for fitting
        return len(self.lap_numbers) >= 3

class TruthExtractor:
    """
    Queries actual historical laps spanning an entire compound at a specific track.
    Aggressively purges In-Laps, Out-Laps, Safety Cars, and VSCs to generate clean arrays.
    """
    def __init__(self, db_session: Session):
        self.db = db_session

    def extract_clean_segments(self, season: int, circuit_id: str, compound: str) -> List[ContinuousStintSegment]:
        """
        Extracts all continuous green-flag segments for the specified compound and track.
        Aggregates across all drivers in the race.
        """
        # Step 1: Find the Race
        race = self.db.execute(
            select(Race).where(and_(Race.season == season, Race.circuit == circuit_id))
        ).scalar_one_or_none()

        if not race:
            logger.warning(f"No race found for {season} {circuit_id}")
            return []

        # Step 2: Find all stints on this compound
        stints = self.db.execute(
            select(Stint, Driver.driver_code)
            .join(Driver)
            .where(and_(Stint.race_id == race.id, Stint.compound == compound))
        ).all()

        all_segments: List[ContinuousStintSegment] = []

        for stint, driver_code in stints:
            # We ignore out-laps and in-laps aggressively
            # If stint is Lap 10 to Lap 30, out-lap = 10, in-lap = 30.
            # Real racing happens laps 11 through 29.
            valid_start = stint.start_lap + 1
            valid_end = stint.end_lap - 1

            if valid_end < valid_start:
                continue # Stint was too short

            # Fetch all laps for this driver in this stint
            laps = self.db.execute(
                select(Lap)
                .where(
                    and_(
                        Lap.stint_id == stint.id,
                        Lap.lap_number >= valid_start,
                        Lap.lap_number <= valid_end,
                        Lap.lap_time_seconds.isnot(None)
                    )
                )
                .order_by(Lap.lap_number)
            ).scalars().all()

            current_segment: Optional[ContinuousStintSegment] = None
            last_lap_num = -1

            for lap in laps:
                # 1. Strict Green Flag Check.
                # '1' is FastF1 generic green. 'is_green_flag' is our normalized boolean.
                # If they passed through a yellow sector, we must break the continuous chain.
                is_clean = lap.is_green_flag and lap.track_status == '1'

                if not is_clean:
                    # Broken chain. Save current if valid, and restart search.
                    if current_segment and current_segment.is_valid:
                        all_segments.append(current_segment)
                    current_segment = None
                    continue

                # 2. Continuous numbering check
                if current_segment is None or lap.lap_number != last_lap_num + 1:
                    # Start a new segment because of a gap (e.g., missed Lap 15)
                    if current_segment and current_segment.is_valid:
                        all_segments.append(current_segment)

                    # Calculate true tyre age. If stint started on Lap 10, and this segment starts on Lap 15
                    # The tyres are already 5 laps old!
                    tyre_age = lap.lap_number - stint.start_lap
                    current_segment = ContinuousStintSegment(driver_code, starting_wear_laps=tyre_age)

                # Add the physical data
                current_segment.add_lap(
                    lap_number=lap.lap_number,
                    lap_time_s=lap.lap_time_seconds,
                    fuel_kg=lap.fuel_estimate_kg or 0.0 # Will be populated natively later, default to 0 to prevent crashes
                )
                last_lap_num = lap.lap_number

            # Close dangling segment at end of stint
            if current_segment and current_segment.is_valid:
                all_segments.append(current_segment)

        logger.info(f"Extracted {len(all_segments)} clean continuous {compound} segments for {circuit_id} {season}")
        return all_segments
