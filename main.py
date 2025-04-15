"""
FastAPI server that receives notifications from Dahua cameras via ITSAPI.
Handles ANPR notifications and heartbeat messages.
"""
from typing import Any
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging
import json
from datetime import datetime
import base64

# Import configuration and database modules
from config import settings
import db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Dahua ITSAPI Server")


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


def get_or_raise_if_empty(data: dict, key: str) -> Any:
    """Get a value from a dictionary or raise an error if it's empty."""
    value = data.get(key)
    if value is None or value == '':
        raise ValueError(f"Missing required data: {key}")
    return value


async def save_vehicle_image(data: dict) -> str:
    """Save the vehicle body image to disk."""
    img_content = get_or_raise_if_empty(data['image'], 'content')
    snap_time = get_or_raise_if_empty(data['snap'], 'time')
    plate_number = get_or_raise_if_empty(data['plate'], 'number')

    # Create directory for this day
    date_dir = settings.images_dir / snap_time.strftime("%Y-%m-%d")
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


async def save_data(data: dict) -> None:
    """Save ANPR data including vehicle images and database record."""
    # Save the image first
    image_path = await save_vehicle_image(data)

    # Save the data to the database
    try:
        record_id = db.save_vehicle_record(
            plate_data=data['plate'],
            vehicle_data=data['vehicle'],
            snap_data=data['snap'],
            image_path=image_path
        )
        logger.info(f"Saved record to database with ID: {record_id}")
    except Exception as e:
        logger.error(f"Failed to save to database: {str(e)}")
        # Continue execution even if database save fails
        # to avoid losing the image and allow for recovery


@app.post("/NotificationInfo/TollgateInfo")
async def handle_anpr_notification(request: Request):
    """Handle ANPR notifications from Dahua cameras."""
    try:
        body = await request.body()
        notification_data = json.loads(body)
        logger.debug("Received ANPR notification")
        data = parse_picture_data(notification_data.get('Picture', {}))
        await save_data(data)
    except Exception as e:
        logger.error(f"Error processing ANPR notification: {str(e)}")
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )

    logger.debug("ANPR notification processed successfully")
    return JSONResponse(
        content={
            "status": "success",
            "message": "ANPR notification received",
            "result": "true",  # otherwise the camera will keep sending the same notification
        },
        status_code=200
    )


@app.post("/NotificationInfo/KeepAlive")
async def handle_heartbeat(request: Request):
    """Handle camera heartbeat messages."""
    try:
        body = await request.body()
        heartbeat_data = json.loads(body)
        logger.info(f"Received heartbeat: {heartbeat_data}")

        return JSONResponse(
            content={
                "status": "success",
                "message": "Heartbeat received",
                "timestamp": datetime.now().isoformat()
            },
            status_code=200
        )

    except Exception as e:
        logger.error(f"Error processing heartbeat: {str(e)}")
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on {settings.host}:{settings.port}")
    logger.info(f"Images will be saved to: {settings.images_dir.absolute()}")
    uvicorn.run(app, host=settings.host, port=settings.port)
