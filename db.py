"""
Database operations for the SafeWheels Dahua application.
"""
import sqlite3
import logging
from datetime import datetime
from typing import Dict, Any

from config import settings

logger = logging.getLogger(__name__)


def init_db() -> None:
    """
    Initialize the SQLite database and create the necessary tables if they don't exist.
    """
    try:
        conn = sqlite3.connect(settings.db_path)
        cursor = conn.cursor()

        # Create vehicles table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate_number TEXT NOT NULL,
            plate_region TEXT,
            plate_type TEXT,
            plate_color TEXT,
            vehicle_type TEXT,
            vehicle_color TEXT,
            vehicle_sign TEXT,
            vehicle_series TEXT,
            detection_time TIMESTAMP NOT NULL,
            direction TEXT,
            image_path TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Create indexes for common searches
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_plate_number ON vehicles(plate_number)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_detection_time ON vehicles(detection_time)')

        conn.commit()
        logger.info(f"Database initialized at {settings.db_path}")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()


def save_vehicle_record(
    plate_data: Dict[str, Any],
    vehicle_data: Dict[str, Any],
    snap_data: Dict[str, Any],
    image_path: str
) -> int:
    """
    Save vehicle detection record to the database.

    Args:
        plate_data: Dictionary containing plate information
        vehicle_data: Dictionary containing vehicle information
        snap_data: Dictionary containing snapshot information
        image_path: Path to the saved vehicle image

    Returns:
        The ID of the inserted record
    """
    try:
        conn = sqlite3.connect(settings.db_path)
        cursor = conn.cursor()

        # Extract the needed data
        plate_number = plate_data.get('number', '')
        plate_region = plate_data.get('region', '')
        plate_type = plate_data.get('type', '')
        plate_color = plate_data.get('color', '')

        vehicle_type = vehicle_data.get('type', '')
        vehicle_color = vehicle_data.get('color', '')
        vehicle_sign = vehicle_data.get('sign', '')
        vehicle_series = vehicle_data.get('series', '')

        detection_time = snap_data.get('time')
        if isinstance(detection_time, datetime):
            detection_time = detection_time.isoformat()
        direction = snap_data.get('direction', '')

        # Insert the record
        cursor.execute('''
        INSERT INTO vehicles (
            plate_number, plate_region, plate_type, plate_color,
            vehicle_type, vehicle_color, vehicle_sign, vehicle_series,
            detection_time, direction, image_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            plate_number, plate_region, plate_type, plate_color,
            vehicle_type, vehicle_color, vehicle_sign, vehicle_series,
            detection_time, direction, image_path
        ))

        record_id = cursor.lastrowid
        conn.commit()
        logger.debug(f"Saved vehicle record ID: {record_id}, plate: {plate_number}")
        return record_id

    except Exception as e:
        logger.error(f"Error saving vehicle record: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


# Initialize the database when this module is imported
init_db()
