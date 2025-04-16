"""
ANPR core functions for parsing and processing camera data.
"""
import base64
import logging
from datetime import datetime
from typing import Any, Dict

from app.core.config import settings

logger = logging.getLogger(__name__)


def parse_plate_data(plate_data: dict) -> dict:
    """Parse plate data from Dahua ANPR notification."""
    return {
        "bbox": plate_data.get('BoundingBox'),
        "channel": plate_data.get('Channel'),
        "confidence": plate_data.get('Confidence'),
        "is_exist": plate_data.get('IsExist'),
        "color": plate_data.get('PlateColor'),
        "number": plate_data.get('PlateNumber'),
        "type": plate_data.get('PlateType'),
        "region": plate_data.get('Region'),
        "upload_num": plate_data.get('UploadNum'),
    }


def parse_vehicle_data(vehicle_data: dict) -> dict:
    """Parse vehicle data from Dahua ANPR notification."""
    return {
        "bbox": vehicle_data.get('VehicleBoundingBox'),
        "color": vehicle_data.get('VehicleColor'),
        "series": vehicle_data.get('VehicleSeries'),
        "sign": vehicle_data.get('VehicleSign'),
        "type": vehicle_data.get('VehicleType'),
    }


def parse_snap_data(snap_data: dict) -> dict:
    """Parse snap data from Dahua ANPR notification."""
    dt = snap_data.get('AccurateTime')
    if dt is not None:
        dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S.%f')

    return {
        "time": dt,
        "allow_user": snap_data.get('AllowUser'),
        "allow_user_end_time": snap_data.get('AllowUserEndTime'),
        "block_user": snap_data.get('BlockUser'),
        "block_user_end_time": snap_data.get('BlockUserEndTime'),
        "direction": snap_data.get('Direction'),
        "timezone": snap_data.get('TimeZone'),
    }


def parse_normal_pic_data(normal_pic_data: dict) -> dict:
    """Parse normal pic data from Dahua ANPR notification."""
    return {
        "content": normal_pic_data.get('Content'),
        "name": normal_pic_data.get('PicName'),
    }


def parse_picture_data(picture_data: dict) -> dict:
    """Parse picture data from Dahua ANPR notification."""
    return {
        "image": parse_normal_pic_data(picture_data.get('NormalPic', {})),
        "plate": parse_plate_data(picture_data.get('Plate', {})),
        "vehicle": parse_vehicle_data(picture_data.get('Vehicle', {})),
        "snap": parse_snap_data(picture_data.get('SnapInfo', {})),
    }


async def save_vehicle_image(data: Dict[str, Any]) -> str:
    """Save the vehicle body image to disk."""
    img_content = data['image']['content']
    snap_time = data['snap']['time']
    plate_number = data['plate']['number']

    # Create directory for this day
    date_dir = settings.images_dir_path / snap_time.strftime("%Y-%m-%d")
    date_dir.mkdir(exist_ok=True)

    # Create filename with timestamp (including microseconds) and plate number
    time_str = snap_time.strftime('%Y%m%d_%H%M%S.%f')
    filename = f"{time_str}_{plate_number}.jpg"
    file_path = date_dir / filename

    # Decode and save the image
    image_bytes = base64.b64decode(img_content)
    with open(file_path, 'wb') as f:
        f.write(image_bytes)

    logger.debug(f"Saved vehicle image: {file_path}")
    return str(file_path)
