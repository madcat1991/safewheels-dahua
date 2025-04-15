"""
FastAPI server that receives notifications from Dahua cameras via ITSAPI.
Handles ANPR notifications and heartbeat messages.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import logging
import json
from datetime import datetime
import os
import base64
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables and configure logging
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Server configuration
HOST = os.getenv("HOST")
if not HOST:
    raise ValueError("HOST must be set in .env file")

PORT = os.getenv("PORT")
if not PORT:
    raise ValueError("PORT must be set in .env file")
PORT = int(PORT)  # Convert to integer since env vars are strings

# Create directory for storing images
IMAGES_DIR_NAME = os.getenv("IMAGES_DIR")
if not IMAGES_DIR_NAME:
    raise ValueError("IMAGES_DIR must be set in .env file")
IMAGES_DIR = Path(IMAGES_DIR_NAME)
IMAGES_DIR.mkdir(exist_ok=True)

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
        "normal_pic": parse_normal_pic_data(picture_data.get('NormalPic', {})),
        "plate": parse_plate_data(picture_data.get('Plate', {})),
        "vehicle": parse_vehicle_data(picture_data.get('Vehicle', {})),
        "snap": parse_snap_data(picture_data.get('SnapInfo', {})),
    }


@app.post("/NotificationInfo/TollgateInfo")
async def handle_anpr_notification(request: Request):
    """Handle ANPR notifications from Dahua cameras."""
    try:
        body = await request.body()
        notification_data = json.loads(body)
        logger.debug("Received ANPR notification")
        data = parse_picture_data(notification_data.get('Picture', {}))
    except Exception as e:
        logger.error(f"Error parsing ANPR notification: {str(e)}")
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )

    try:
        #await save_data(data)
        print(data)
    except Exception as e:
        logger.error(f"Error saving data: {str(e)}")
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )

    # just return success
    logger.debug("ANPR notification processed successfully")
    return JSONResponse(
        content={"status": "success", "message": "ANPR notification received"},
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
    logger.info(f"Starting server on {HOST}:{PORT}")
    logger.info(f"Images will be saved to: {IMAGES_DIR.absolute()}")
    uvicorn.run(app, host=HOST, port=PORT)
