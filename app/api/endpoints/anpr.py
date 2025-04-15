"""
ANPR endpoints for handling camera notifications.
"""
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.services.anpr import parse_picture_data, save_vehicle_image
from app.db.database import save_vehicle_record

logger = logging.getLogger(__name__)

router = APIRouter(tags=["anpr"])


@router.post("/NotificationInfo/TollgateInfo")
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
    # otherwise the camera will keep sending the same notification
    return JSONResponse(content={"Result": True})


@router.post("/NotificationInfo/KeepAlive")
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


async def save_data(data: dict) -> None:
    """Save ANPR data including vehicle images and database record."""
    # Save the image first
    image_path = await save_vehicle_image(data)

    # Save the data to the database
    try:
        record_id = save_vehicle_record(
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
