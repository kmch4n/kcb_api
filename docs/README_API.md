# Kyoto City Bus API

FastAPI server for searching Kyoto City Bus routes using GTFS data.

## Setup

### 1. Install Dependencies

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env and set your API_KEY
```

**Required Settings:**

-   `API_KEY` - Set your API key for client authentication

**Optional Settings:**

-   `HOST` - Server host (default: 0.0.0.0)
-   `PORT` - Server port (default: 8000)
-   `LOG_LEVEL` - Logging level (debug/info/warning/error)

### 3. Ensure GTFS Data

Make sure GTFS data is available in the `./data` directory. If not, run:

```bash
python update_gtfs_data.py
```

## Running the Server

### Development Mode

```bash
python main.py
```

Or with auto-reload:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

Using the startup script:

```bash
chmod +x run.sh
./run.sh
```

Or directly with uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
```

## API Usage

### Authentication

All requests (except `/kcb_api/health`) require an API key in the `X-API-Key` header:

```python
import requests

headers = {"X-API-Key": "your-api-key-here"}
response = requests.get(url, headers=headers)
```

### Endpoints

#### Health Check

```bash
GET /kcb_api/health
```

No authentication required.

**Response:**

```json
{
    "status": "healthy",
    "timestamp": "2026-01-11T12:15:00"
}
```

#### Search Bus Routes

```bash
POST /kcb_api/search
```

**Request Body:**

```json
{
    "from_stop": "堀川下長者町",
    "to_stop": "京都駅前",
    "current_time": "14:30",
    "day_type": "weekday",
    "limit": 3
}
```

**Parameters:**

-   `from_stop` (required): Departure stop name
-   `to_stop` (required): Arrival stop name
-   `current_time` (optional): Departure time in HH:MM format (default: current time)
-   `day_type` (optional): Day type (`weekday`/`saturday`/`sunday`), default: `weekday`
-   `limit` (optional): Maximum number of results (1-10), default: 3

**Response:**

```json
{
    "success": true,
    "query": {
        "from_stop": "堀川下長者町",
        "to_stop": "京都駅前",
        "current_time": "14:30",
        "day_type": "weekday",
        "limit": 3
    },
    "count": 2,
    "routes": [
        {
            "route_name": "市バス９",
            "route_id": "00900",
            "trip_id": "00900_01001_1234",
            "headsign": "京都駅前",
            "departure_time": "14:35:00",
            "departure_stop_id": "061123",
            "departure_stop_desc": "堀川下長者町(南行)",
            "arrival_time": "14:45:00",
            "arrival_stop_id": "061211",
            "arrival_stop_desc": "京都駅前(A1)",
            "travel_time_minutes": 10,
            "service_id": "01001"
        }
    ]
}
```

**Error Response:**

```json
{
    "success": false,
    "error": "Stop '存在しない停留所' not found.",
    "status_code": 400
}
```

### Example Python Code

```python
import requests

BASE_URL = "http://localhost:8000"
API_KEY = "your-api-key-here"

# Basic search (weekday, current time)
url = f"{BASE_URL}/kcb_api/search"
headers = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}
data = {
    "from_stop": "四条河原町",
    "to_stop": "京都駅前"
}

response = requests.post(url, json=data, headers=headers)
print(response.json())

# Search with specific time
data = {
    "from_stop": "堀川下長者町",
    "to_stop": "京都駅前",
    "current_time": "14:30",
    "day_type": "weekday",
    "limit": 5
}

response = requests.post(url, json=data, headers=headers)
print(response.json())

# Sunday search
data = {
    "from_stop": "京都駅前",
    "to_stop": "金閣寺道",
    "current_time": "09:00",
    "day_type": "sunday"
}

response = requests.post(url, json=data, headers=headers)
print(response.json())
```

## Running the Server

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions on running the server.

## Interactive API Documentation

Once the server is running, visit:

-   Swagger UI: http://localhost:8000/kcb_api/docs
-   ReDoc: http://localhost:8000/kcb_api/redoc

## Stopping the Server

Press `Ctrl+C` in the terminal where the server is running.
