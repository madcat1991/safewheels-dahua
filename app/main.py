"""
FastAPI server that receives notifications from Dahua cameras via ITSAPI.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.config import settings
from app.api.endpoints import anpr
from app.db.database import get_pool, close_pool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("Initializing database connection pool")
    logger.info(f"DB host: {settings.postgres_host}, port: {settings.postgres_port}")
    await get_pool()

    yield

    # Shutdown
    logger.info("Closing database connection pool")
    await close_pool()


# Create FastAPI app
app = FastAPI(
    title="SafeWheels Dahua ANPR",
    description="API server for receiving and processing ANPR notifications from Dahua cameras",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(anpr.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "app": "SafeWheels Dahua ANPR",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on {settings.host}:{settings.port}")
    logger.info(f"Images will be saved to: {settings.images_dir_path.absolute()}")
    uvicorn.run(app, host=settings.host, port=settings.port)
