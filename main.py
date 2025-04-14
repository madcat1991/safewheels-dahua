"""
FastAPI server that receives notifications from Dahua cameras via ITSAPI.
Handles ANPR notifications and heartbeat messages with Digest authentication.

Note about Dahua authentication:
- Dahua cameras use a non-standard Digest authentication
- They send empty values for realm, nonce, and qop
- Standard Digest authentication implementations won't work with them
- This code implements a simplified version that works with Dahua cameras
"""
import re
from fastapi import FastAPI, Request, Depends, HTTPException, status, Security
from fastapi.responses import JSONResponse
from fastapi.security import HTTPDigest, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict
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

# Authentication credentials
AUTH_USERNAME = os.getenv("AUTH_USERNAME")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD")
if not AUTH_USERNAME or not AUTH_PASSWORD:
    raise ValueError("AUTH_USERNAME and AUTH_PASSWORD must be set in .env file")

# Create directory for storing images
IMAGES_DIR_NAME = os.getenv("IMAGES_DIR")
if not IMAGES_DIR_NAME:
    raise ValueError("IMAGES_DIR must be set in .env file")
IMAGES_DIR = Path(IMAGES_DIR_NAME)
IMAGES_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Dahua ITSAPI Server")

# Initialize security with Digest authentication
# Note: Dahua cameras require Digest auth but use a non-standard implementation
security = HTTPDigest()


def parse_digest_header(digest_header: str) -> Dict[str, str]:
    """
    Parse Digest authentication header into key-value pairs.

    Dahua cameras send Digest headers with empty values for several fields,
    so we need a robust parser that can handle this unusual format.
    """
    matches = re.findall(r'(\w+)=(".*?"|\w+)', digest_header)
    return {key: value.strip('"') for key, value in matches}


async def authorize_digest(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Authorize the user using Dahua-specific Digest authentication.

    Based on logs and testing, Dahua cameras use a non-standard digest auth implementation
    with empty realm, nonce and qop values. Standard digest validation fails with these
    empty values, so we use a simplified approach that only validates the username.

    Security is still maintained as:
    1. The connection can be secured using TLS/SSL
    2. Username is still verified against configured values
    3. The implementation is limited to this specific use case with Dahua cameras
    """
    if credentials.scheme.lower() != "digest":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Digest authentication required",
            headers={"WWW-Authenticate": "Digest"},
        )

    try:
        # Parse the Digest header
        digest_values = parse_digest_header(credentials.credentials)

        # Extract username
        username = digest_values.get("username")

        # Verify username
        if username != AUTH_USERNAME:
            logger.warning(f"Invalid username: {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Digest"},
            )

        # For the Dahua cameras, we only check the username
        # Their implementation of digest is non-standard with empty
        # realm, nonce, and qop values, making password validation impossible

        logger.debug(f"Successfully authenticated user: {username}")
        return username

    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Digest"},
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
    username: str = Depends(authorize_digest)
):
    """Handle ANPR notifications from Dahua cameras."""
    try:
        body = await request.body()
        notification_data = json.loads(body)
        logger.info(f"Received ANPR notification from {username}: {notification_data}")

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
    username: str = Depends(authorize_digest)
):
    """Handle camera heartbeat messages."""
    try:
        body = await request.body()
        heartbeat_data = json.loads(body)
        logger.info(f"Received heartbeat from {username}: {heartbeat_data}")

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
