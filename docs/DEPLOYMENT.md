# Running the Server

This guide shows how to run the Kyoto City Bus API server for personal use.

## Quick Start

### 1. Start the Server

```bash
cd /path/to/kcb_api
source .venv/bin/activate
python main.py
```

The server will start on `http://localhost:8000`

### 2. Test the API

```python
import requests

# Health check
response = requests.get("http://localhost:8000/kcb_api/health")
print(response.json())
```

## Running Options

### Option 1: Direct Execution

```bash
python main.py
```

### Option 2: Using run.sh

```bash
chmod +x run.sh
./run.sh
```

### Option 3: With Uvicorn

For development with auto-reload:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

For production:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Configuration

Edit `.env` file to configure:

-   `API_KEY` - Your authentication key
-   `HOST` - Server host (default: 0.0.0.0)
-   `PORT` - Server port (default: 8000)
-   `LOG_LEVEL` - Logging level (default: info)

## Accessing the API

Once running, you can access:

-   **Health Check**: http://localhost:8000/kcb_api/health
-   **API Documentation**: http://localhost:8000/kcb_api/docs
-   **ReDoc**: http://localhost:8000/kcb_api/redoc

## Stopping the Server

Press `Ctrl+C` in the terminal where the server is running.

## Updating GTFS Data

To update bus route data:

```bash
python update_gtfs_data.py
```

Then restart the server to load new data.

## Troubleshooting

### Port Already in Use

If port 8000 is already in use:

```bash
# Find the process
lsof -i :8000

# Kill it (replace PID with actual process ID)
kill <PID>
```

Or change the port in `.env`:

```
PORT=8001
```

### Module Not Found

Make sure you're in the virtual environment:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### GTFS Data Missing

If you see errors about missing data files:

```bash
python update_gtfs_data.py
```

This will download the latest GTFS data to the `./data` directory.
