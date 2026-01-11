# Kyoto City Bus API

FastAPI server for searching Kyoto City Bus routes using GTFS (General Transit Feed Specification) data.

## Features

-   🚌 **Bus Route Search**: Find direct routes between two stops with departure times.
-   📍 **Nearby Stops**: Find bus stops near your GPS location.
-   🕒 **Timetable**: View schedules for specific stops.
-   👁️ **Bus Location**: Estimate bus current location based on schedule.
-   ⚡ **Fast Response**: GTFS data preloaded in memory.
-   📖 **Full Documentation**: [See API Documentation](docs/README_API.md).

## Quick Start

### 1. Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Setup GTFS Data

Download Kyoto City Bus data:

```bash
python update_gtfs_data.py
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env and set your API_KEY
```

### 4. Run Server

```bash
python main.py
```

Server will start at `http://localhost:8000`.

## Documentation

-   **[API Specification](docs/README_API.md)**: Detailed endpoint reference.
-   **[Deployment Guide](docs/DEPLOYMENT.md)**: Production setup instructions.
-   **Interactive Docs**: Visit `/kcb_api/docs` in your browser when running.

## Project Structure

```
kcb_api/
├── main.py                 # FastAPI application
├── bus_route_search.py     # Core logic
├── auth.py                 # Authentication
├── config.py               # Settings
├── docs/                   # Documentation
└── data/                   # GTFS data storage
```

## Technology Stack

-   **FastAPI**
-   **Uvicorn**
-   **Pydantic**
-   **GTFS**

## License

MIT License
