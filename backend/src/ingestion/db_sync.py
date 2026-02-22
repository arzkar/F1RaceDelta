import logging
import math
import uuid
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
import pandas as pd
import fastf1

from src.db.models.race import Race
from src.db.models.driver import Driver
from src.db.models.stint import Stint
from src.db.models.lap import Lap

logger = logging.getLogger(__name__)

def clean_float(val: Any) -> float | None:
    """Helper to convert Pandas/Numpy floats/NaT to python floats/None for SQLAlchemy."""
    if pd.isna(val):
        return None
    return float(val)

def sync_macro_data(db: Session, session: fastf1.core.Session, force: bool = False):
    """
    Syncs Core Macro Data for Phase 2A: Race, Drivers, Stints, Laps.
    Uses Postgres ON CONFLICT DO UPDATE for idempotency.
    """
    event = session.event

    # 1. Upsert Race
    race_stmt = insert(Race).values(
        season=event.year,
        grand_prix=event.EventName,
        circuit=event.Location,
        circuit_length_km=0.0,
        total_laps=0,
        race_date=event.EventDate.to_pydatetime() if pd.notnull(event.EventDate) else None
    )

    race_update_dict = {
        c.name: c for c in race_stmt.excluded if not c.primary_key
    }

    race_stmt = race_stmt.on_conflict_do_update(
        index_elements=['season', 'grand_prix'],
        set_=race_update_dict
    ).returning(Race.id)

    race_id = db.execute(race_stmt).scalar_one()
    db.commit()

    # 2. Upsert Drivers
    laps_df = session.laps
    if laps_df.empty:
        logger.warning("No laps found in session.")
        return

    drivers = session.drivers
    driver_ids = {}

    for drv_num in drivers:
        drv_info = session.get_driver(drv_num)
        drv_stmt = insert(Driver).values(
            driver_code=drv_info['Abbreviation'],
            full_name=drv_info['FullName'],
            team=drv_info['TeamName'],
            season=event.year
        )
        drv_stmt = drv_stmt.on_conflict_do_update(
            index_elements=['driver_code', 'season'],
            set_={'full_name': drv_stmt.excluded.full_name, 'team': drv_stmt.excluded.team}
        ).returning(Driver.id)

        drv_id = db.execute(drv_stmt).scalar_one()
        driver_ids[drv_info['Abbreviation']] = drv_id

    db.commit()

    # 3. Upsert Stints & 4. Laps
    for driver_code, driver_id in driver_ids.items():
        drv_laps = laps_df.pick_driver(driver_code)
        if drv_laps.empty:
            continue

        stints = drv_laps.groupby('Stint')

        for stint_num, stint_laps in stints:
            if pd.isna(stint_num) or stint_num == 0:
                continue

            compound_series = stint_laps['Compound']
            compound = compound_series.iloc[0] if 'Compound' in stint_laps.columns and not pd.isna(compound_series.iloc[0]) else 'UNKNOWN'

            start_lap = int(stint_laps['LapNumber'].min())
            end_lap = int(stint_laps['LapNumber'].max())
            stint_length = end_lap - start_lap + 1

            stint_stmt = insert(Stint).values(
                race_id=race_id,
                driver_id=driver_id,
                compound=str(compound),
                start_lap=start_lap,
                end_lap=end_lap,
                stint_length=stint_length
            )

            stint_stmt = stint_stmt.on_conflict_do_update(
                index_elements=['race_id', 'driver_id', 'start_lap'],
                set_={
                    'end_lap': stint_stmt.excluded.end_lap,
                    'stint_length': stint_stmt.excluded.stint_length,
                    'compound': stint_stmt.excluded.compound
                }
            ).returning(Stint.id)

            stint_id = db.execute(stint_stmt).scalar_one()

            lap_values = []
            for _, lap in stint_laps.iterrows():
                lap_time = clean_float(lap['LapTime'].total_seconds()) if pd.notnull(lap['LapTime']) else None
                sector_1 = clean_float(lap['Sector1Time'].total_seconds()) if pd.notnull(lap['Sector1Time']) else None
                sector_2 = clean_float(lap['Sector2Time'].total_seconds()) if pd.notnull(lap['Sector2Time']) else None
                sector_3 = clean_float(lap['Sector3Time'].total_seconds()) if pd.notnull(lap['Sector3Time']) else None

                track_status = str(lap['TrackStatus']) if pd.notnull(lap['TrackStatus']) else None

                lap_values.append({
                    "race_id": race_id,
                    "driver_id": driver_id,
                    "stint_id": stint_id,
                    "lap_number": int(lap['LapNumber']),
                    "lap_time_seconds": lap_time,
                    "sector_1_seconds": sector_1,
                    "sector_2_seconds": sector_2,
                    "sector_3_seconds": sector_3,
                    "track_status": track_status,
                    "is_green_flag": track_status == '1' if track_status else True,
                })

            if lap_values:
                lap_stmt = insert(Lap).values(lap_values)
                if force:
                    lap_stmt = lap_stmt.on_conflict_do_update(
                        index_elements=['race_id', 'driver_id', 'lap_number'],
                        set_={
                            'stint_id': lap_stmt.excluded.stint_id,
                            'lap_time_seconds': lap_stmt.excluded.lap_time_seconds,
                            'sector_1_seconds': lap_stmt.excluded.sector_1_seconds,
                            'sector_2_seconds': lap_stmt.excluded.sector_2_seconds,
                            'sector_3_seconds': lap_stmt.excluded.sector_3_seconds,
                            'track_status': lap_stmt.excluded.track_status,
                            'is_green_flag': lap_stmt.excluded.is_green_flag,
                        }
                    )
                else:
                    lap_stmt = lap_stmt.on_conflict_do_nothing(
                        index_elements=['race_id', 'driver_id', 'lap_number']
                    )
                db.execute(lap_stmt)

    db.commit()
    logger.info("Successfully synced Macro Data to DB")

def update_lap_telemetry_pointers(db: Session, race_id: uuid.UUID, driver_id: uuid.UUID, telemetry_file_path: str):
    """
    Updates all laps for a specific driver and race to point to their shared Telemetry Data Lake parquet file.
    """
    stmt = (
        update(Lap)
        .where(Lap.race_id == race_id)
        .where(Lap.driver_id == driver_id)
        .values(telemetry_file_path=telemetry_file_path)
    )
    db.execute(stmt)
    db.commit()
