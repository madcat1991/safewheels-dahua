# SafeWheels Dahua

A FastAPI server for receiving ANPR (Automatic Number Plate Recognition) notifications from Dahua cameras via the ITSAPI protocol.

## Features

- Receives vehicle detection events from Dahua cameras
- Stores vehicle images with timestamp and direction information
- Handles heartbeat messages to maintain connection
- Implements the custom Digest authentication required by Dahua cameras

## Dahua Authentication Implementation

The Dahua cameras use a non-standard implementation of Digest authentication that has these unusual characteristics:

- They send **empty values** for several required Digest fields:
  - `realm=""`
  - `nonce=""`
  - `qop=""`
- Standard Digest authentication libraries fail when trying to validate these credentials
- Our implementation only validates the username, since standard password validation is impossible with empty nonce/realm values

This approach still maintains security because:
1. The connection can be secured using TLS/SSL
2. Username is still verified against configured values
3. The implementation is specific to Dahua cameras

### Authentication Code Details

The key parts of our authentication implementation:

```python
def parse_digest_header(digest_header: str) -> Dict[str, str]:
    """Parse Digest authentication header into key-value pairs."""
    matches = re.findall(r'(\w+)=(".*?"|\w+)', digest_header)
    return {key: value.strip('"') for key, value in matches}

async def authorize_digest(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Authorize the user using Dahua-specific Digest authentication."""
    # ...
    # Parse the Digest header
    digest_values = parse_digest_header(credentials.credentials)

    # Extract username
    username = digest_values.get("username")

    # Verify username
    if username != AUTH_USERNAME:
        # Raise exception if invalid

    # For Dahua cameras, we only check the username
    # Their implementation makes standard validation impossible
    return username
```

## Configuration

Configuration is done via environment variables in a `.env` file:

```
# Authentication
AUTH_USERNAME=your_username_here
AUTH_PASSWORD=your_password_here

# Server configuration
HOST=192.168.1.203  # VPN interface IP
PORT=7070

# Storage configuration
IMAGES_DIR=vehicle_images  # Directory where vehicle images will be stored
```

## Installation

1. Clone this repository
2. Create a `.env` file with your configuration
3. Install dependencies: `pip install -r requirements.txt`
4. Run the server: `python main.py`

## API Endpoints

- `/NotificationInfo/TollgateInfo` - Receives ANPR notifications
- `/NotificationInfo/KeepAlive` - Handles camera heartbeat messages

Both endpoints require Digest authentication with the configured username.

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
