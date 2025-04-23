"""
Database operations for the SafeWheels Dahua application.
"""
import logging
from typing import Dict, Any

import asyncpg
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global pool variable
pool = None


async def get_pool() -> asyncpg.Pool:
    """
    Get or create a connection pool.

    Returns:
        asyncpg.Pool: Database connection pool
    """
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(
            user=settings.postgres_user,
            password=settings.postgres_password,
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_db,
            min_size=2,
            max_size=10
        )
        # Initialize database tables after pool is created
        await init_db()
    return pool


async def close_pool() -> None:
    """Close the connection pool."""
    global pool
    if pool:
        await pool.close()
        pool = None
        logger.info("Database connection pool closed")


async def get_connection() -> asyncpg.Connection:
    """
    Get a database connection from the pool.

    Returns:
        asyncpg.Connection: Database connection
    """
    pool = await get_pool()
    return await pool.acquire()


async def release_connection(conn: asyncpg.Connection) -> None:
    """
    Release a connection back to the pool.

    Args:
        conn: Connection to release
    """
    if conn:
        pool = await get_pool()
        await pool.release(conn)


async def init_db() -> None:
    """
    Initialize the PostgreSQL database and create the necessary tables if they don't exist.
    """
    conn = None
    try:
        pool = await get_pool()
        conn = await pool.acquire()

        # Create vehicles table
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS vehicles (
            id SERIAL PRIMARY KEY,

            -- Plate data
            plate_number TEXT NOT NULL,
            plate_region TEXT,
            plate_type TEXT,
            plate_color TEXT,
            plate_bbox INTEGER[],
            plate_channel INTEGER,
            plate_confidence INTEGER,
            plate_is_exist BOOLEAN,
            plate_upload_num INTEGER,

            -- Vehicle data
            vehicle_type TEXT,
            vehicle_color TEXT,
            vehicle_sign TEXT,
            vehicle_series TEXT,
            vehicle_bbox INTEGER[],

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
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_plate_number ON vehicles(plate_number)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_detection_time ON vehicles(detection_time)')

        logger.info(f"Database initialized at {settings.postgres_db}")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise
    finally:
        if conn:
            await pool.release(conn)


async def save_vehicle_record(
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
    conn = None
    try:
        conn = await get_connection()

        # Extract the plate data
        plate_number = plate_data.get('number', '')
        plate_region = plate_data.get('region', '')
        plate_type = plate_data.get('type', '')
        plate_color = plate_data.get('color', '')
        plate_bbox = plate_data.get('bbox')
        plate_channel = plate_data.get('channel')
        plate_confidence = plate_data.get('confidence')
        plate_is_exist = plate_data.get('is_exist')
        plate_upload_num = plate_data.get('upload_num')

        # Extract the vehicle data
        vehicle_type = vehicle_data.get('type', '')
        vehicle_color = vehicle_data.get('color', '')
        vehicle_sign = vehicle_data.get('sign', '')
        vehicle_series = vehicle_data.get('series', '')
        vehicle_bbox = vehicle_data.get('bbox')

        # Extract the snap data
        detection_time = snap_data.get('time')
        direction = snap_data.get('direction', '')
        allow_user = snap_data.get('allow_user')
        allow_user_end_time = snap_data.get('allow_user_end_time', '')
        block_user = snap_data.get('block_user')
        block_user_end_time = snap_data.get('block_user_end_time', '')
        timezone = snap_data.get('timezone')

        # Insert the record
        sql = '''
        INSERT INTO vehicles (
            plate_number, plate_region, plate_type, plate_color, plate_bbox, plate_channel,
            plate_confidence, plate_is_exist, plate_upload_num,
            vehicle_type, vehicle_color, vehicle_sign, vehicle_series, vehicle_bbox,
            detection_time, direction, allow_user, allow_user_end_time, block_user,
            block_user_end_time, timezone, image_path
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22)
        RETURNING id
        '''
        record_id = await conn.fetchval(
            sql,
            plate_number, plate_region, plate_type, plate_color, plate_bbox, plate_channel,
            plate_confidence, plate_is_exist, plate_upload_num,
            vehicle_type, vehicle_color, vehicle_sign, vehicle_series, vehicle_bbox,
            detection_time, direction, allow_user, allow_user_end_time, block_user,
            block_user_end_time, timezone, image_path
        )

        logger.debug(f"Saved vehicle record ID: {record_id}, plate: {plate_number}")
        return record_id

    except Exception as e:
        logger.error(f"Error saving vehicle record: {str(e)}")
        raise
    finally:
        if conn:
            await release_connection(conn)
