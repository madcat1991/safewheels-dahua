# Dahua ITSAPI Server

A FastAPI server that receives notifications from Dahua cameras via ITSAPI. The server handles ANPR (Automatic Number Plate Recognition) notifications and heartbeat messages.

## Features

- Receives and processes ANPR notifications from Dahua cameras
- Saves vehicle images with timestamps and plate numbers
- Handles camera heartbeat messages
- Stores images in organized daily directories

## Prerequisites

- Python 3.8 or higher
- FastAPI
- Uvicorn
- python-dotenv

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-directory>
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with the following variables:
```env
HOST=0.0.0.0
PORT=8000
IMAGES_DIR=./images
```

## Usage

1. Start the server:
```bash
python main.py
```

2. Configure your Dahua camera to send notifications to:
```
http://<your-server-ip>:8000/NotificationInfo/TollgateInfo
```

3. Configure the camera to send heartbeat messages to:
```
http://<your-server-ip>:8000/NotificationInfo/KeepAlive
```

## API Endpoints

### ANPR Notification
- **Endpoint**: `/NotificationInfo/TollgateInfo`
- **Method**: POST
- **Description**: Receives ANPR notifications from cameras
- **Response**: JSON with status and saved image path

### Heartbeat
- **Endpoint**: `/NotificationInfo/KeepAlive`
- **Method**: POST
- **Description**: Receives heartbeat messages from cameras
- **Response**: JSON with status and timestamp

## Image Storage

Images are saved in the following structure:
```
images/
  YYYY-MM-DD/
    HH-MM-SS.microseconds_direction_plate_number.jpg
```

## License

MIT
