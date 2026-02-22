import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, List
import io

from src.storage.r2_client import r2_client

logger = logging.getLogger(__name__)

class MicroSectorPreprocessor:
    """
    Responsible for fetching 10Hz physical telemetry from the R2 Data Lake
    and aggregating it into fast, deterministic micro-sectors to avoid simulating at 10Hz.
    """
    def __init__(self, target_sectors: int = 200):
        self.target_sectors = target_sectors

    def fetch_driver_telemetry(self, object_key: str) -> pd.DataFrame:
        """
        Streams the exact Parquet object from Cloudflare R2 into memory.
        """
        stream = r2_client.read_file_stream(object_key)
        if not stream:
            logger.error(f"Failed to fetch telemetry from Data Lake: {object_key}")
            return pd.DataFrame()

        # Read the raw byte stream directly into a PyArrow-backed DataFrame
        df = pd.read_parquet(io.BytesIO(stream.read()), engine="pyarrow")
        return df

    def compute_lap_distance(self, df_lap: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates cumulative track distance (meters) for a single lap based on timestamp and speed.
        Speed is provided in km/h. Need to convert to m/s.
        """
        # Ensure it's sorted by time
        df_lap = df_lap.sort_values(by="timestamp").copy()

        # Calculate time delta (dt) in seconds
        df_lap['dt'] = df_lap['timestamp'].diff().fillna(0.0)

        # Convert speed km/h to m/s
        df_lap['speed_ms'] = df_lap['speed'] / 3.6

        # Distance delta = speed * dt
        df_lap['dx'] = df_lap['speed_ms'] * df_lap['dt']

        # Cumulative distance
        df_lap['track_distance'] = df_lap['dx'].cumsum()

        return df_lap

    def aggregate_into_micro_sectors(self, df_lap: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Slices a single continuous lap into `self.target_sectors` chunks.
        Computes the baseline averages for speed and proxies for lateral/longitudinal loads.
        """
        if df_lap.empty or 'track_distance' not in df_lap.columns:
            return []

        total_distance = df_lap['track_distance'].max()
        if total_distance <= 0:
            return []

        # Create the sector bins based on total lap distance
        sector_size = total_distance / self.target_sectors

        # Assign each row to a micro-sector bucket (0 to target_sectors - 1)
        df_lap['micro_sector_id'] = (df_lap['track_distance'] // sector_size).astype(int)

        # Cap the max ID to handle edge cases precisely at the finish line
        df_lap['micro_sector_id'] = df_lap['micro_sector_id'].clip(upper=self.target_sectors - 1)

        sectors = []
        # Group by the micro-sector completely vectorised
        grouped = df_lap.groupby('micro_sector_id')

        for sector_id, group in grouped:
            # We use absolute throttle & brake to generate simple proxies for "load" on the tyre
            # Brake is usually 0-100. Throttle is 0-100.
            # Speed is km/h. High speed + High brake = Massive longitudinal load proxy

            baseline_speed = group['speed'].mean()
            mean_throttle = group['throttle'].mean()
            mean_brake = float(np.mean(pd.to_numeric(group['brake'], errors='coerce').fillna(0)))

            # Simple Proxy: Cornering happens when speed drops but throttle isn't fully 100
            # A true lateral G proxy would require steering angle and corner radius,
            # but Speed variance serves as a strong substitute for acceleration loads.

            dt_sector = group['dt'].sum()

            sectors.append({
                "sector_id": int(sector_id),
                "baseline_time_s": float(dt_sector),
                "baseline_speed_kmh": float(baseline_speed),
                "mean_throttle": float(mean_throttle),
                "mean_brake": float(mean_brake),
                "distance_start": float(group['track_distance'].min()),
                "distance_end": float(group['track_distance'].max()),
            })

        return sectors

    def process_stint(self, object_key: str, lap_numbers: List[int]) -> Dict[int, List[Dict[str, Any]]]:
        """
        Fetches the driver's telemetry object, extracts the specific laps for the stint,
        and runs the micro-sector aggregator on each.
        Returns a dictionary mapping { lap_number: [ List of MicroSectors ] }
        """
        df = self.fetch_driver_telemetry(object_key)
        if df.empty:
            return {}

        stint_data = {}
        # Filter down to just the laps requested in this stint
        df_stint = df[df['lap_number'].isin(lap_numbers)]

        for lap_num, group in df_stint.groupby('lap_number'):
            df_lap = self.compute_lap_distance(group)
            sectors = self.aggregate_into_micro_sectors(df_lap)
            stint_data[int(lap_num)] = sectors

        logger.info(f"Successfully processed {len(stint_data)} laps into {self.target_sectors} micro-sectors from {object_key}")
        return stint_data
