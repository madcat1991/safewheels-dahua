"""
Configuration settings for the SafeWheels Dahua application.
"""
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings using Pydantic BaseSettings."""
    # Server configuration
    host: str = Field("192.168.1.203", description="Host IP address to bind to")
    port: int = Field(7070, description="Port to listen on")

    # Storage configuration
    images_dir: str = Field("vehicle_images", description="Directory where vehicle images will be stored")

    # Database configuration
    db_filename: str = Field("safewheels.db", description="SQLite database filename")

    # Telegram configuration
    telegram_bot_token: str = Field("", description="Telegram bot token for notifications")
    telegram_authorized_users: str = Field("", description="Comma-separated list of authorized Telegram user IDs")

    # Notification service configuration
    notification_check_interval: int = Field(15, description="Interval in seconds between checks for new records")

    @property
    def images_dir_path(self) -> Path:
        """Return the Path object for the images directory."""
        path = Path(self.images_dir)
        path.mkdir(exist_ok=True)
        return path

    @property
    def db_path(self) -> Path:
        """Return the Path object for the database file."""
        return Path(self.db_filename)

    @property
    def authorized_users(self) -> list[int]:
        """Return list of authorized Telegram user IDs."""
        return [int(uid.strip()) for uid in self.telegram_authorized_users.split(",") if uid.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Create a global settings instance
settings = Settings()
