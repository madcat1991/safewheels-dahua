"""
FastAPI server that receives notifications from Dahua cameras via ITSAPI.
Handles ANPR notifications and heartbeat messages with Digest authentication.
"""
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import logging
import json
from datetime import datetime
import os
from dotenv import load_dotenv

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

app = FastAPI(title="Dahua ITSAPI Server")


async def verify_digest_auth(request: Request):
    """Verify Digest authentication from Dahua camera."""
    auth_header = request.headers.get('Authorization')

    if not auth_header or not auth_header.startswith('Digest '):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Digest authentication required",
            headers={"WWW-Authenticate": 'Digest realm="dahua_itsapi"'},
        )

    try:
        # Parse Digest auth parameters
        auth_params = {}
        auth_str = auth_header[7:]  # Skip 'Digest '
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
                detail="Invalid credentials",
                headers={"WWW-Authenticate": 'Digest realm="dahua_itsapi"'},
            )

        logger.info(f"Authenticated request from: {username}")
        return {"username": username}

    except Exception as e:
        logger.error(f"Error processing Digest auth: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Digest authentication",
            headers={"WWW-Authenticate": 'Digest realm="dahua_itsapi"'},
        )


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
    image_paths: Optional[List[str]] = None


@app.post("/NotificationInfo/TollgateInfo")
async def handle_anpr_notification(request: Request, auth=Depends(verify_digest_auth)):
    """Handle ANPR notifications from Dahua cameras."""
    try:
        body = await request.body()
        notification_data = json.loads(body)
        logger.info(f"Received ANPR notification from {auth['username']}: {notification_data}")

        return JSONResponse(
            content={
                "status": "success",
                "message": "ANPR notification received",
                "timestamp": datetime.now().isoformat()
            },
            status_code=200
        )

    except Exception as e:
        logger.error(f"Error processing ANPR notification: {str(e)}")
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )


@app.post("/NotificationInfo/KeepAlive")
async def handle_heartbeat(request: Request, auth=Depends(verify_digest_auth)):
    """Handle camera heartbeat messages."""
    try:
        body = await request.body()
        heartbeat_data = json.loads(body)
        logger.info(f"Received heartbeat from {auth['username']}: {heartbeat_data}")

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
    uvicorn.run(app, host=HOST, port=PORT)
