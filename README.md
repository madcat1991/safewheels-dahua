# SafeWheels Dahua ANPR

A FastAPI server that receives and processes ANPR (Automatic Number Plate Recognition) notifications from Dahua cameras.

## Features

- Receives and processes ANPR notifications from Dahua cameras
- Stores vehicle information in SQLite database
- Saves vehicle images with timestamps and plate numbers
- Handles camera heartbeat messages
- Stores images in organized daily directories
- JSON serialization for bounding box coordinates
- Complete data storage for all ANPR fields

## Project Structure

```
.
├── app
│   ├── __init__.py
│   ├── api
│   │   ├── __init__.py
│   │   └── endpoints
│   │       ├── __init__.py
│   │       └── anpr.py
│   ├── core
│   │   ├── __init__.py
│   │   ├── anpr.py
│   │   └── config.py
│   ├── db
│   │   ├── __init__.py
│   │   └── database.py
│   ├── services
│   │   ├── __init__.py
│   │   └── notify_service.py
│   └── main.py
├── requirements.txt
└── README.md
```

## Prerequisites

- Python 3.8 or higher
- FastAPI
- Uvicorn
- Pydantic Settings

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-directory>
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root with your configuration:
```env
HOST=<your-server-ip>
PORT=7070
IMAGES_DIR=vehicle_images
DB_FILENAME=safewheels.db
TELEGRAM_BOT_TOKEN=<your-bot-token>
TELEGRAM_CHAT_ID=<your-chat-id>
NOTIFICATION_CHECK_INTERVAL=15
```

## Usage

1. Start the server:
```bash
python -m app.main
```

2. Configure your Dahua camera to send notifications to:
```
http://<your-server-ip>:7070/NotificationInfo/TollgateInfo
```

3. Configure the camera to send heartbeat messages to:
```
http://<your-server-ip>:7070/NotificationInfo/KeepAlive
```

## API Endpoints

### ANPR Notification
- **Endpoint**: `/NotificationInfo/TollgateInfo`
- **Method**: POST
- **Description**: Receives ANPR notifications from cameras
- **Response**: JSON with status and message

### Heartbeat
- **Endpoint**: `/NotificationInfo/KeepAlive`
- **Method**: POST
- **Description**: Receives heartbeat messages from cameras
- **Response**: JSON with status, message, and timestamp

### Root
- **Endpoint**: `/`
- **Method**: GET
- **Description**: Returns application status
- **Response**: JSON with app name and status

## Data Storage

### Images
Images are saved in the following structure:
```
vehicle_images/
  YYYY-MM-DD/
    YYYYMMDD_HHMMSS.microseconds_plate_number.jpg
```

### Database
Vehicle records are stored in SQLite with the following information:
- Plate data (number, region, type, color, bbox, etc.)
- Vehicle data (type, color, sign, series, bbox)
- Snap data (time, direction, user permissions, timezone)
- Image path

## Development

The project follows FastAPI's recommended structure for larger applications:
- `app/api/endpoints/`: API route handlers
- `app/core/`: Core functionality and configuration
- `app/db/`: Database models and operations
- `app/services/`: Business logic and services

## License

MIT
