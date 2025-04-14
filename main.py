"""
FastAPI server that receives notifications from Dahua cameras via ITSAPI.
Handles ANPR notifications and heartbeat messages with Digest authentication.
"""
from fastapi import FastAPI, Request, Depends, HTTPException, status, Security
from fastapi.responses import JSONResponse
from fastapi.security import HTTPDigest, HTTPAuthorizationCredentials
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
HOST = "192.168.1.203"  # VPN interface IP
PORT = 7070

# Authentication credentials
AUTH_USERNAME = os.getenv("AUTH_USERNAME")
if not AUTH_USERNAME:
    raise ValueError("AUTH_USERNAME must be set in .env file")

# Create directory for storing images
IMAGES_DIR = Path("vehicle_images")
IMAGES_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Dahua ITSAPI Server")
security = HTTPDigest()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """Validate Digest authentication credentials."""
    try:
        # Extract username from Digest auth
        auth_str = credentials.credentials
        auth_params = {}

        # Parse the comma-separated parameters
        for param in auth_str.split(','):
            if '=' not in param:
                continue
            key, value = param.split('=', 1)
            auth_params[key.strip()] = value.strip().strip('"')

        username = auth_params.get('username')

        if username != AUTH_USERNAME:
            logger.warning(f"Invalid username: {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        logger.info(f"Authenticated request from: {username}")
        return {"username": username}

    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


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

        logger.info(f"Saved vehicle image: {file_path}")
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
async def handle_anpr_notification(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Handle ANPR notifications from Dahua cameras."""
    try:
        body = await request.body()
        notification_data = json.loads(body)
        logger.info(f"Received ANPR notification from {current_user['username']}: {notification_data}")

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
async def handle_heartbeat(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Handle camera heartbeat messages."""
    try:
        body = await request.body()
        heartbeat_data = json.loads(body)
        logger.info(f"Received heartbeat from {current_user['username']}: {heartbeat_data}")

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
    logger.info(f"Using username: {AUTH_USERNAME}")
    logger.info(f"Images will be saved to: {IMAGES_DIR.absolute()}")
    uvicorn.run(app, host=HOST, port=PORT)
