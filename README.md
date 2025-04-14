# Dahua ITSAPI Server

A FastAPI server that receives notifications from Dahua cameras via ITSAPI. Handles both ANPR (Automatic Number Plate Recognition) data and camera heartbeats with Digest authentication.

## Features

- Receives ANPR notifications from Dahua cameras
- Handles camera heartbeat messages
- Uses Digest authentication (compatible with Dahua cameras)
- Detailed logging of all events

## Setup

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with authentication credentials:
```bash
AUTH_USERNAME=your_username
AUTH_PASSWORD=your_password
```

## Running the Server

Start the server:
```bash
python main.py
```

The server will start on `http://<your-server-ip>:7070`

## API Endpoints

- `POST /NotificationInfo/TollgateInfo`: Receives ANPR notifications
- `POST /NotificationInfo/KeepAlive`: Handles camera heartbeat messages

## Image Storage

Vehicle images are automatically saved with the following structure:

```
vehicle_images/
├── 2024-02-20/
│   ├── 14-30-45.123456_in_ABC123.jpg
│   └── 14-35-22.654321_out_XYZ789.jpg
└── 2024-02-21/
    └── 09-15-33.987654_in_DEF456.jpg
```

Filename format: `HH-MM-SS.μμμμμμ_direction_plate.jpg`
- `HH-MM-SS`: Hours, minutes, seconds
- `μμμμμμ`: Microseconds for unique identification
- `direction`: Vehicle direction (in/out)
- `plate`: License plate number

## Dahua Camera Configuration

Configure your Dahua camera with these settings:

1. Enable ITSAPI notifications
2. Set Protocol Version to V1.19
3. Configure Platform Server: `http://<your-server-ip>:7070`
4. Set Heartbeat Interface to: `/NotificationInfo/KeepAlive`
5. Set ANPR Info Interface to: `/NotificationInfo/TollgateInfo`
6. Set Authentication Username and Password to match your `.env` file
7. Enable the following data types:
   - ANPR Info with:
     - Plate Number
     - Vehicle Color
     - Logo
     - Vehicle Type
     - Driving Direction
     - Time
     - Location
     - Accuracy
     - Vehicle in Blocklist
8. Under Picture settings:
   - Enable "Vehicle Body Cutout"
   - Set Encoding Format to UTF8

## Authentication

The server uses Digest authentication, which is the standard authentication method used by Dahua cameras. The camera will automatically handle the Digest authentication process. You only need to:

1. Set the username and password in your `.env` file
2. Configure the same username and password in the camera's web interface
3. The camera will handle the Digest authentication headers automatically

## Testing

You can test the endpoints using curl with Digest authentication:

1. Test ANPR notification endpoint:
```bash
curl -v --digest -u "your_username:your_password" \
  -X POST http://<your-server-ip>:7070/NotificationInfo/TollgateInfo \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_info": {
      "plate_number": "ABC123",
      "vehicle_color": "white",
      "vehicle_type": "car",
      "driving_direction": "east"
    },
    "vehicle_body_image": "<base64-encoded-image-data>"
  }'
```

2. Test heartbeat endpoint:
```bash
curl -v --digest -u "your_username:your_password" \
  -X POST http://<your-server-ip>:7070/NotificationInfo/KeepAlive \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "your_device_id",
    "timestamp": "2024-01-01T00:00:00Z",
    "status": {"status": "active"}
  }'
```

The `-v` flag will show you the complete authentication process, including:
- Initial request
- Server's authentication challenge
- Final authenticated request

Expected responses:
- Success: HTTP 200 with JSON response containing "status": "success"
- Auth failure: HTTP 401 Unauthorized
- Error: HTTP 500 with error details

## Logging

Logs are written to stdout with the following format:
```
timestamp - logger_name - level - message
```

The server logs:
- All authentication attempts
- Received ANPR notifications with vehicle data
- Image save operations with paths
- Camera heartbeat messages
- Any errors or issues
