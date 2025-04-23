"""
Configuration settings for the SafeWheels Dahua application.
"""
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings using Pydantic BaseSettings."""
    # Server configuration
    host: str = Field(description="Host IP address to bind to")
    port: int = Field(description="Port to listen on")

    # Storage configuration
    images_dir: str = Field(description="Directory where vehicle images will be stored")

    # Database configuration
    postgres_user: str = Field(description="PostgreSQL username")
    postgres_password: str = Field(description="PostgreSQL password")
    postgres_db: str = Field(description="PostgreSQL database name")
    postgres_host: str = Field(description="PostgreSQL host")
    postgres_port: int = Field(description="PostgreSQL port")

    # Telegram configuration
    telegram_bot_token: str = Field(description="Telegram bot token for notifications")
    telegram_authorized_users: str = Field(description="Comma-separated list of authorized Telegram user IDs")

    # Notification service configuration
    notification_check_interval: int = Field(description="Interval in seconds between checks for new records")
    plate_confidence_threshold: float = Field(
        description="Minimum confidence level required for plate recognition (0.0 to 1.0)"
    )

    @property
    def images_dir_path(self) -> Path:
        """Return the Path object for the images directory."""
        path = Path(self.images_dir)
        path.mkdir(exist_ok=True)
        return path

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
