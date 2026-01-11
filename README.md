# Kyoto City Bus API

FastAPI server for searching Kyoto City Bus routes using GTFS (General Transit Feed Specification) data.

## Features

-   🚌 **Bus Route Search**: Find direct routes between two stops with departure times
-   🔑 **API Key Authentication**: Secure access with X-API-Key header
-   ⚡ **Fast Response**: GTFS data preloaded in memory (~3 seconds startup, <100ms queries)
-   📅 **Day Type Support**: Different schedules for weekdays, Saturdays, and Sundays
-   📖 **Interactive API Docs**: Built-in Swagger UI and ReDoc

## Quick Start

### 1. Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Setup GTFS Data

Download and extract Kyoto City Bus GTFS data:

```bash
python update_gtfs_data.py
```

This will download the latest GTFS data to the `./data` directory.

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env and set your API_KEY
```

### 4. Run Server

```bash
python main.py
```

The server will start on `http://localhost:8000`

## API Usage

### Health Check

```python
import requests

response = requests.get("http://localhost:8000/kcb_api/health")
print(response.json())
# {"status": "healthy", "timestamp": "2026-01-11T12:15:00"}
```

### Search Bus Routes

```python
import requests

url = "http://localhost:8000/kcb_api/search"
headers = {
    "Content-Type": "application/json",
    "X-API-Key": "your-api-key-here"
}
data = {
    "from_stop": "京都駅前",
    "to_stop": "四条河原町",
    "current_time": "14:00",
    "day_type": "weekday"
}

response = requests.post(url, json=data, headers=headers)
print(response.json())
```

**Parameters:**

-   `from_stop` (required): Departure stop name
-   `to_stop` (required): Arrival stop name
-   `current_time` (optional): Departure time in HH:MM format (default: current time)
-   `day_type` (optional): "weekday", "saturday", or "sunday" (default: "weekday")
-   `limit` (optional): Max number of results, 1-10 (default: 3)

## Documentation

-   **[docs/README_API.md](docs/README_API.md)**: Detailed API documentation with examples
-   **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**: Production deployment guide (systemd, nginx)
-   **Interactive Docs**: http://localhost:8000/kcb_api/docs (when server is running)

## Project Structure

```
kcb_api/
├── main.py                 # FastAPI application entry point
├── config.py               # Configuration management
├── auth.py                 # API key authentication
├── bus_route_search.py     # Core search logic and GTFS data loader
├── update_gtfs_data.py     # GTFS data download/update script
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
└── data/                   # GTFS data files (auto-downloaded)
```

## Technology Stack

-   **FastAPI**: Modern, high-performance web framework
-   **Uvicorn**: ASGI server with async support
-   **Pydantic**: Data validation and settings management
-   **GTFS**: Standard transit feed format for public transportation

## License

MIT License - see [LICENSE](LICENSE) file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

-   GTFS data provided by [Open Data Challenge for Public Transportation in Tokyo](https://developer-tokyochallenge.odpt.org/)
-   Kyoto Municipal Transportation Bureau for public transportation data
