"""
Service for processing new vehicle records and sending notifications via Telegram.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import cv2
import telegram
from telegram import InputFile

from app.core.config import settings
from app.db.database import get_pool, release_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("notify_service")


class NotifyService:
    """Service for processing new vehicle records and sending notifications."""

    def __init__(self, bot_token: str):
        """
        Initialize the notification service.

        Args:
            bot_token: Telegram bot token
        """
        self.bot_token = bot_token
        self.bot = telegram.Bot(token=bot_token)
        self.last_processed_id = self._load_last_processed_id()
        self.pool = None

    def _load_last_processed_id(self) -> int:
        """Load the last processed record ID from a file."""
        try:
            with open("last_processed_id.txt", "r") as f:
                return int(f.read().strip())
        except (FileNotFoundError, ValueError):
            return 0

    def _save_last_processed_id(self, record_id: int) -> None:
        """Save the last processed record ID to a file."""
        with open("last_processed_id.txt", "w") as f:
            f.write(str(record_id))

    async def get_new_records(self) -> List[Dict]:
        """
        Get new vehicle records from the database.

        Returns:
            List of new vehicle records
        """
        conn = None
        try:
            pool = await get_pool()
            conn = await pool.acquire()

            rows = await conn.fetch('''
                SELECT
                    id,
                    plate_number,
                    plate_bbox,
                    plate_confidence,
                    vehicle_bbox,
                    image_path,
                    detection_time,
                    direction
                FROM vehicles
                WHERE vehicle_type NOT IN ('Motorcycle') AND id > $1
                ORDER BY id ASC
            ''', self.last_processed_id)

            records = []
            for row in rows:
                # Handle datetime serialization
                detection_time = row['detection_time']
                if isinstance(detection_time, datetime):
                    detection_time = detection_time.isoformat()

                record = {
                    'id': row['id'],
                    'plate_number': row['plate_number'],
                    'plate_bbox': row['plate_bbox'],
                    'plate_confidence': row['plate_confidence'],
                    'vehicle_bbox': row['vehicle_bbox'],
                    'image_path': row['image_path'],
                    'detection_time': detection_time,
                    'direction': row['direction']
                }
                records.append(record)

            return records
        except Exception as e:
            logger.error(f"Error getting new records: {str(e)}")
            return []
        finally:
            if conn:
                await release_connection(conn)

    def process_image(self, image_path: str, vehicle_bbox: List[int], plate_bbox: Optional[List[int]] = None) -> bytes:
        """
        Process the vehicle image by drawing plate bbox and cropping to vehicle bbox.

        Args:
            image_path: Path to the image file
            vehicle_bbox: Bounding box of the vehicle as [x1, y1, x2, y2] where
                (x1,y1) is top-left and (x2,y2) is bottom-right
            plate_bbox: Optional bounding box of the license plate as [x1, y1, x2, y2] where
                (x1,y1) is top-left and (x2,y2) is bottom-right

        Returns:
            Processed image as bytes
        """
        try:
            # Read the image
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Failed to read image: {image_path}")

            # Draw plate bbox if available
            if plate_bbox:
                x1, y1, x2, y2 = map(int, plate_bbox)
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Get vehicle bbox coordinates
            x1, y1, x2, y2 = map(int, vehicle_bbox)

            # Crop the image to vehicle bbox
            cropped = img[y1:y2, x1:x2]

            # Encode the image to bytes
            _, img_encoded = cv2.imencode('.jpg', cropped)
            return img_encoded.tobytes()
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            raise

    async def send_notification(self, record: Dict) -> bool:
        """
        Send a notification with the processed image.

        Args:
            record: Vehicle record data

        Returns:
            True if notification was sent successfully, False otherwise
        """
        try:
            # Process the image
            image_bytes = self.process_image(
                record['image_path'],
                record['vehicle_bbox'],
                record['plate_bbox']
            )

            # Format the detection time
            if isinstance(record['detection_time'], str):
                detection_time = datetime.fromisoformat(record['detection_time'])
            else:
                detection_time = record['detection_time']
            time_str = detection_time.strftime("%Y-%m-%d %H:%M:%S")

            # Prepare the caption
            caption = "🚗 Vehicle detected\n"

            # Add direction if available
            direction = record.get('direction', '')
            if direction == 'Obverse':
                direction_emoji = "⬇️"
            elif direction == 'Reverse':
                direction_emoji = "⬆️"
            else:
                direction_emoji = "❓"
            caption += f"📏 Direction: {direction_emoji}\n"

            plate_confidence = record.get('plate_confidence', 0)
            plate_number = record.get('plate_number')
            plate_bbox = record.get('plate_bbox')

            if plate_confidence >= settings.plate_confidence_threshold and plate_number:
                caption += f"📝 License plate: {record['plate_number']}\n"
            elif plate_bbox:
                caption += "⚠️⚠️⚠️ No license plate recognized ⚠️⚠️⚠️\n"
            else:
                caption += "🚨🚨🚨 No license plate detected 🚨🚨🚨\n"

            caption += f"⏱️ Time: {time_str}"

            error_count = 0
            for user_id in settings.authorized_users:
                try:
                    photo = InputFile(image_bytes, filename=f"vehicle_{record['id']}.jpg")
                    await self.bot.send_photo(
                        chat_id=user_id,
                        photo=photo,
                        caption=caption,
                        write_timeout=30
                    )
                except telegram.error.TimedOut:
                    # This is quite an often error, which is mainly due to the
                    # Telegram not being able to handle image uploads in a timely manner.
                    # However, it doesn't mean that the notification was not sent.
                    logger.warning(f"Timeout sending notification to user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to send notification to user {user_id}: {e}")
                    error_count += 1

            # Update the last processed ID
            # Even then we
            if error_count < len(settings.authorized_users):
                self.last_processed_id = record['id']
                self._save_last_processed_id(record['id'])
                msg = f"Sent notification for record {record['id']}"
                if error_count > 0:
                    msg += f" ({error_count} errors)"
                logger.info(msg)
                return True
            else:
                logger.error(f"Failed to send notification to any users for record {record['id']}")
                return False

        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
            return False

    async def run(self):
        """
        Run the notification service loop.
        """
        logger.info("Starting notification service")
        try:
            while True:
                # Get new records
                records = await self.get_new_records()
                if records:
                    logger.info(f"Found {len(records)} new records")
                    for record in records:
                        await self.send_notification(record)

                # Wait for the next check
                logger.info(f"Waiting {settings.notification_check_interval} seconds before next check")
                await asyncio.sleep(settings.notification_check_interval)

        except KeyboardInterrupt:
            logger.info("Notification service stopped by user")
        except Exception as e:
            logger.error(f"Error in notification service: {str(e)}")
            raise


async def main():
    """Main function to run the notification service."""
    # Get Telegram credentials from environment
    bot_token = settings.telegram_bot_token

    if not bot_token:
        logger.error("Telegram bot token not found in environment variables")
        return

    if not settings.authorized_users:
        logger.error("No authorized users configured")
        return

    # Create and run the notification service
    service = NotifyService(bot_token)
    await service.run()


if __name__ == "__main__":
    asyncio.run(main())
