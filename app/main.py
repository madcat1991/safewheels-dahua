"""
FastAPI server that receives notifications from Dahua cameras via ITSAPI.
"""
import logging
from fastapi import FastAPI

from app.core.config import settings
from app.api.endpoints import anpr

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="SafeWheels Dahua ANPR",
    description="API server for receiving and processing ANPR notifications from Dahua cameras",
    version="1.0.0"
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
