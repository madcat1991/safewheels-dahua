"""
Database operations for the SafeWheels Dahua application.
"""
import sqlite3
import logging
import json
from datetime import datetime
from typing import Dict, Any

from app.core.config import settings

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

            -- Plate data
            plate_number TEXT NOT NULL,
            plate_region TEXT,
            plate_type TEXT,
            plate_color TEXT,
            plate_bbox TEXT,
            plate_channel INTEGER,
            plate_confidence INTEGER,
            plate_is_exist BOOLEAN,
            plate_upload_num INTEGER,

            -- Vehicle data
            vehicle_type TEXT,
            vehicle_color TEXT,
            vehicle_sign TEXT,
            vehicle_series TEXT,
            vehicle_bbox TEXT,

            -- Snap data
            detection_time TIMESTAMP NOT NULL,
            direction TEXT,
            allow_user BOOLEAN,
            allow_user_end_time TEXT,
            block_user BOOLEAN,
            block_user_end_time TEXT,
            timezone INTEGER,

            -- Image data
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

        # Extract the plate data
        plate_number = plate_data.get('number', '')
        plate_region = plate_data.get('region', '')
        plate_type = plate_data.get('type', '')
        plate_color = plate_data.get('color', '')
        plate_bbox = json.dumps(plate_data.get('bbox')) if plate_data.get('bbox') else None
        plate_channel = plate_data.get('channel')
        plate_confidence = plate_data.get('confidence')
        plate_is_exist = plate_data.get('is_exist')
        plate_upload_num = plate_data.get('upload_num')

        # Extract the vehicle data
        vehicle_type = vehicle_data.get('type', '')
        vehicle_color = vehicle_data.get('color', '')
        vehicle_sign = vehicle_data.get('sign', '')
        vehicle_series = vehicle_data.get('series', '')
        vehicle_bbox = json.dumps(vehicle_data.get('bbox')) if vehicle_data.get('bbox') else None

        # Extract the snap data
        detection_time = snap_data.get('time')
        if isinstance(detection_time, datetime):
            detection_time = detection_time.isoformat()
        direction = snap_data.get('direction', '')
        allow_user = snap_data.get('allow_user')
        allow_user_end_time = snap_data.get('allow_user_end_time', '')
        block_user = snap_data.get('block_user')
        block_user_end_time = snap_data.get('block_user_end_time', '')
        timezone = snap_data.get('timezone')

        # Insert the record
        cursor.execute('''
        INSERT INTO vehicles (
            plate_number, plate_region, plate_type, plate_color, plate_bbox, plate_channel,
            plate_confidence, plate_is_exist, plate_upload_num,
            vehicle_type, vehicle_color, vehicle_sign, vehicle_series, vehicle_bbox,
            detection_time, direction, allow_user, allow_user_end_time, block_user,
            block_user_end_time, timezone, image_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            plate_number, plate_region, plate_type, plate_color, plate_bbox, plate_channel,
            plate_confidence, plate_is_exist, plate_upload_num,
            vehicle_type, vehicle_color, vehicle_sign, vehicle_series, vehicle_bbox,
            detection_time, direction, allow_user, allow_user_end_time, block_user,
            block_user_end_time, timezone, image_path
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
