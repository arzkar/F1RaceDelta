import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

def is_valid_lap(lap: pd.Series) -> bool:
    """Check if the lap is a valid racing lap to export."""
    # Remove in-laps and out-laps
    if not pd.isna(lap['PitOutTime']) or not pd.isna(lap['PitInTime']):
        return False
    # Remove red flag laps (TrackStatus code '5' usually indicates Red Flag)
    track_status = str(lap['TrackStatus'])
    if '5' in track_status:
        return False
    return True

def normalize_lap_telemetry(lap: pd.Series) -> pd.DataFrame:
    """
    Extracts, normalizes, and resamples telemetry for a single lap.
    Returns an empty DataFrame if it fails or is invalid.
    """
    try:
        if not is_valid_lap(lap):
            return pd.DataFrame()

        # get_telemetry() downloads/parses data for this lap internally using the fastf1 cache
        tel = lap.get_telemetry()
        if tel.empty:
            return pd.DataFrame()

        # Convert SessionTime to timedelta, then to seconds relative to lap start
        # The telemetry DataFrame has a 'Time' column which is timedelta from session start.
        lap_start_time = lap['LapStartTime']
        if pd.isna(lap_start_time):
            # Fallback if LapStartTime is missing
            lap_start_time = tel['SessionTime'].iloc[0]

        # Calculate relative time in float seconds
        relative_time = (tel['SessionTime'] - lap_start_time).dt.total_seconds()

        # Build strictly the DataFrame requested by user
        # 'nGear' in fastf1 is the gear.
        df = pd.DataFrame({
            'timestamp': relative_time,
            'lap_number': int(lap['LapNumber']),
            'speed': tel['Speed'],
            'throttle': tel['Throttle'],
            'brake': tel['Brake'],
            'gear': tel['nGear'],
            'rpm': tel['RPM'],
            'x': tel['X'],
            'y': tel['Y']
        })

        # Drop rows with severe missing data if any
        df = df.dropna(subset=['timestamp'])

        # Resample to 10Hz (0.1s steps)
        # We will interpolate the numerical values over a regular time grid
        if len(df) < 2:
            return pd.DataFrame()

        max_time = df['timestamp'].max()
        # Create a new index of 0.0, 0.1, 0.2 ... max_time
        target_timestamps = np.arange(0.0, max_time, 0.1)

        # Create a temporary dataframe with both original and target timestamps to interpolate
        df_target = pd.DataFrame({'timestamp': target_timestamps})
        df_target['lap_number'] = int(lap['LapNumber'])

        # Use numpy interpolation for each column
        for col in ['speed', 'throttle', 'brake', 'gear', 'rpm', 'x', 'y']:
            # FastF1 often provides 'brake' as boolean or int (0/1 or 0-100). We treat it as float for interp.
            df_target[col] = np.interp(target_timestamps, df['timestamp'].values, df[col].astype(float).values)

        # Optional: round gear back to int
        df_target['gear'] = df_target['gear'].round().astype(int)

        return df_target

    except Exception as e:
        logger.warning(f"Could not normalize telemetry for lap {lap.get('LapNumber', 'Unknown')}: {e}")
        return pd.DataFrame()

def get_normalized_telemetry_for_driver(driver_laps: pd.DataFrame) -> pd.DataFrame:
    """
    Iterates over all laps for a driver, normalizes telemetry, and concatenates them.
    """
    lap_dfs = []

    for _, lap in driver_laps.iterlaps():
        df = normalize_lap_telemetry(lap)
        if not df.empty:
            lap_dfs.append(df)

    if not lap_dfs:
        return pd.DataFrame()

    final_df = pd.concat(lap_dfs, ignore_index=True)
    return final_df
