# SafeWheels Dahua ANPR

A FastAPI application that receives notifications from Dahua cameras via ITSAPI and sends notifications via Telegram.

## Features

- Receives ANPR notifications from Dahua cameras
- Stores vehicle and plate data in a PostgreSQL database
- Sends notifications via Telegram with vehicle images
- Configurable plate recognition confidence threshold
- Containerized deployment with Docker
- Fully configurable through environment variables

## Prerequisites

- Docker and Docker Compose
- Telegram bot token
- Authorized Telegram user IDs

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/safewheels_dahua.git
   cd safewheels_dahua
   ```

2. Create a `.env` file based on `.env.example`:
   ```bash
   cp .env.example .env
   ```

3. Edit the `.env` file and set your configuration:
   - `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
   - `TELEGRAM_AUTHORIZED_USERS`: Comma-separated list of authorized user IDs
   - Database credentials and connection details
   - Server host and port settings
   - Other configuration options as needed

## Deployment

### Using Docker Compose (All Services)

To run all services (web, notification, and database):

```bash
docker-compose up -d
```

This will start:
- PostgreSQL database
- FastAPI web service
- Notification service

### Running Individual Services

You can also run individual services:

1. Start the database:
   ```bash
   docker-compose up -d db
   ```

2. Start the web service:
   ```bash
   docker-compose up -d web
   ```

3. Start the notification service:
   ```bash
   docker-compose up -d notify
   ```

### Environment Variables

All aspects of the application can be configured through environment variables in the `.env` file:

#### Database Configuration
- `POSTGRES_USER`: PostgreSQL username (default: safewheels)
- `POSTGRES_PASSWORD`: PostgreSQL password (default: safewheels)
- `POSTGRES_DB`: PostgreSQL database name (default: safewheels)
- `POSTGRES_HOST`: PostgreSQL host (default: db)
- `POSTGRES_PORT`: PostgreSQL port (default: 5432)

#### Server Configuration
- `HOST`: Host IP address for the web service (default: 0.0.0.0)
- `PORT`: Port for the web service (default: 7070)

#### Storage Configuration
- `IMAGES_DIR`: Directory for storing vehicle images (default: vehicle_images)

#### Telegram Configuration
- `TELEGRAM_BOT_TOKEN`: Telegram bot token (required)
- `TELEGRAM_AUTHORIZED_USERS`: Comma-separated list of authorized user IDs (required)

#### Notification Service Configuration
- `PLATE_CONFIDENCE_THRESHOLD`: Minimum confidence level for plate recognition (0.0 to 1.0, default: 0.7)
- `NOTIFICATION_CHECK_INTERVAL`: Interval in seconds between notification checks (default: 15)

## Architecture

The application consists of three main components:

1. **Database Service (PostgreSQL)**
   - Stores vehicle and plate data
   - Persists data between container restarts
   - Configurable host, port, and credentials

2. **Web Service (FastAPI)**
   - Receives ANPR notifications from cameras
   - Processes and stores vehicle data
   - Exposes API endpoints
   - Configurable host and port

3. **Notification Service**
   - Monitors the database for new records
   - Sends notifications via Telegram
   - Can be run independently from the web service
   - Configurable check interval and plate confidence threshold

## Volumes

- `postgres_data`: Persistent storage for PostgreSQL data
- `vehicle_images`: Directory for storing vehicle images

## Ports

- Web service: Configurable via `PORT` (default: 7070)
- PostgreSQL database: Configurable via `POSTGRES_PORT` (default: 5432)

## Development

To run the application in development mode:

1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your configuration.

4. Start PostgreSQL using Docker:
   ```bash
   docker-compose up -d db
   ```

5. Start the web service:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 7070
   ```

6. Start the notification service (in a separate terminal):
   ```bash
   python -m app.services.notify_service
   ```

The application will automatically detect whether it's running in Docker or locally and adjust the database connection accordingly.

## License

MIT
