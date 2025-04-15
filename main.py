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


async def save_vehicle_image(
        plate_number: str,
        image_data: str,
        timestamp: datetime,
        direction: str = "unknown"
        ) -> str:
    """Save the vehicle body image to disk."""
    try:
        # Create directory for this day
        date_dir = IMAGES_DIR / timestamp.strftime("%Y-%m-%d")
        date_dir.mkdir(exist_ok=True)

        # Create filename with timestamp (including microseconds), direction and plate number
        time_str = timestamp.strftime('%H-%M-%S.%f')
        filename = f"{time_str}_{direction}_{plate_number}.jpg"
        file_path = date_dir / filename

        # Decode and save the image
        image_bytes = base64.b64decode(image_data)
        with open(file_path, 'wb') as f:
            f.write(image_bytes)

        logger.debug(f"Saved vehicle image: {file_path}")
        return str(file_path)
    except Exception as e:
        logger.error(f"Error saving vehicle image: {str(e)}")
        return None


class VehicleInfo(BaseModel):
    """Model for ANPR vehicle information."""
    plate_number: Optional[str] = None
    vehicle_color: Optional[str] = None
    vehicle_logo: Optional[str] = None
    vehicle_type: Optional[str] = None
    driving_direction: Optional[str] = None
    capture_time: Optional[str] = None
    location: Optional[str] = None
    accuracy: Optional[float] = None
    in_blocklist: Optional[bool] = None
    vehicle_body_image: Optional[str] = None  # Base64 encoded image


@app.post("/NotificationInfo/TollgateInfo")
async def handle_anpr_notification(request: Request):
    """Handle ANPR notifications from Dahua cameras."""
    try:
        body = await request.body()
        notification_data = json.loads(body)
        logger.info(f"Received ANPR notification: {notification_data}")

        # Extract vehicle information
        vehicle_info = notification_data.get('vehicle_info', {})
        plate_number = vehicle_info.get('plate_number', 'unknown')
        direction = vehicle_info.get('driving_direction', 'unknown')

        # Map direction to in/out if needed
        direction_map = {
            'east': 'in',
            'west': 'out',
            # Add more mappings as needed
        }
        direction = direction_map.get(direction.lower(), direction)

        timestamp = datetime.now()

        # Handle vehicle body image if present
        image_path = None
        if 'vehicle_body_image' in notification_data:
            image_path = await save_vehicle_image(
                plate_number,
                notification_data['vehicle_body_image'],
                timestamp,
                direction
            )

        response_data = {
            "status": "success",
            "message": "ANPR notification received",
            "timestamp": timestamp.isoformat(),
            "saved_image_path": image_path,
            "direction": direction
        }

        return JSONResponse(content=response_data, status_code=200)

    except Exception as e:
        logger.error(f"Error processing ANPR notification: {str(e)}")
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
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
