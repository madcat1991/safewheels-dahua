"""
Service for processing new vehicle records and sending notifications via Telegram.
"""
import asyncio
import json
import logging
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

import cv2
import telegram
from telegram import InputFile

from app.core.config import settings

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

    def get_new_records(self) -> List[Dict]:
        """
        Get new vehicle records from the database.

        Returns:
            List of new vehicle records
        """
        try:
            conn = sqlite3.connect(settings.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, plate_number, plate_bbox, vehicle_bbox, image_path, detection_time, direction
                FROM vehicles
                WHERE id > ?
                ORDER BY id ASC
            ''', (self.last_processed_id,))

            records = []
            for row in cursor.fetchall():
                record = {
                    'id': row[0],
                    'plate_number': row[1],
                    'plate_bbox': json.loads(row[2]) if row[2] else None,
                    'vehicle_bbox': json.loads(row[3]) if row[3] else None,
                    'image_path': row[4],
                    'detection_time': row[5],
                    'direction': row[6]
                }
                records.append(record)

            return records
        except Exception as e:
            logger.error(f"Error getting new records: {str(e)}")
            return []
        finally:
            if conn:
                conn.close()

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
            detection_time = datetime.fromisoformat(record['detection_time'])
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

            # Add plate info
            if record['plate_number']:
                caption += f"📝 License plate: {record['plate_number']}\n"
            elif record['plate_bbox']:
                caption += "⚠️⚠️⚠️ No license plate recognized ⚠️⚠️⚠️\n"
            else:
                caption += "🚨🚨🚨 No license plate detected 🚨🚨🚨\n"

            caption += f"⏱️ Time: {time_str}"

            # Send the photo to each authorized user
            success_count = 0
            error_count = 0

            for user_id in settings.authorized_users:
                try:
                    photo = InputFile(image_bytes, filename=f"vehicle_{record['id']}.jpg")
                    await self.bot.send_photo(
                        chat_id=user_id,
                        photo=photo,
                        caption=caption
                    )
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to send notification to user {user_id}: {e}")
                    error_count += 1

            # Update the last processed ID if at least one notification was sent
            if success_count > 0:
                self.last_processed_id = record['id']
                self._save_last_processed_id(record['id'])
                msg = f"Sent notification for record {record['id']} to {success_count} users"
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
                records = self.get_new_records()
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
