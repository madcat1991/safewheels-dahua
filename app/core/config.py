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
    images_dir_name: str = Field("vehicle_images", description="Directory where vehicle images will be stored")

    # Database configuration
    db_filename: str = Field("safewheels.db", description="SQLite database filename")

    @property
    def images_dir(self) -> Path:
        """Return the Path object for the images directory."""
        path = Path(self.images_dir_name)
        path.mkdir(exist_ok=True)
        return path

    @property
    def db_path(self) -> Path:
        """Return the Path object for the database file."""
        return Path(self.db_filename)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Create a global settings instance
settings = Settings()
