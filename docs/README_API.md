# Kyoto City Bus API Documentation

This document provides detailed information about all available endpoints in the Kyoto City Bus API.

## Base URL

All URLs referenced in the documentation have the following base:

```
http://localhost:8000
```

## Authentication

All endpoints (except Health Check) require an API Key.
Include it in the request header `X-API-Key`.

```http
X-API-Key: your_api_key_here
```

---

## Endpoints

### 1. Health Check

Check operational status of the server.

-   **URL**: `/kcb_api/health`
-   **Method**: `GET`
-   **Auth**: Not Required

#### Response

```json
{
    "status": "healthy",
    "timestamp": "2026-01-11T12:00:00"
}
```

---

### 2. Search Stops

Search for bus stops by name (partial match).

-   **URL**: `/kcb_api/stops/search`
-   **Method**: `GET`
-   **Auth**: Required

#### Parameters

| Name    | Type    | Required | Description                     |
| ------- | ------- | -------- | ------------------------------- |
| `q`     | string  | Yes      | Search query (e.g., "京都")     |
| `limit` | integer | No       | Max results (1-50, default: 10) |

#### Response

```json
{
    "success": true,
    "query": "京都",
    "count": 1,
    "stops": [
        {
            "stop_name": "京都駅前",
            "stop_ids": ["061211", "061212"]
        }
    ]
}
```

---

### 3. Search Nearby Stops

Find stops within a specified radius of GPS coordinates.

-   **URL**: `/kcb_api/stops/nearby`
-   **Method**: `GET`
-   **Auth**: Required

#### Parameters

| Name     | Type    | Required | Description                               |
| -------- | ------- | -------- | ----------------------------------------- |
| `lat`    | float   | Yes      | Latitude (-90 to 90)                      |
| `lon`    | float   | Yes      | Longitude (-180 to 180)                   |
| `radius` | integer | No       | Radius in meters (max 5000, default: 500) |
| `limit`  | integer | No       | Max results (default: 20)                 |

#### Response

```json
{
    "success": true,
    "query": { "lat": 35.0, "lon": 135.7, "radius": 500, "limit": 20 },
    "count": 2,
    "stops": [
        {
            "stop_id": "012345",
            "stop_ids": ["012345", "012346", "012347"],
            "stop_name": "京都駅八条口",
            "stop_desc": "Northbound",
            "stop_lat": 35.001,
            "stop_lon": 135.701,
            "distance_meters": 150.5
        }
    ]
}
```

**Fields:**

-   `stop_id`: Representative stop ID (nearest platform)
-   `stop_ids`: All stop IDs with the same stop name (all platforms)
-   `distance_meters`: Distance to the nearest platform

---

### 4. Search Bus Routes (Direct)

Find direct bus routes between two stops.

-   **URL**: `/kcb_api/search`
-   **Method**: `POST`
-   **Auth**: Required

#### Request Body

```json
{
    "from_stop": "京都駅前",
    "to_stop": "金閣寺道",
    "current_time": "09:00",
    "day_type": "weekday",
    "date": "2026-01-12",
    "limit": 3
}
```

**Parameters:**

-   `day_type`: `weekday`, `saturday`, or `sunday`. Ignored if `date` is provided.
-   `date`: (Optional) Search date in `YYYY-MM-DD` format. When provided, holidays and special schedules are considered. Takes priority over `day_type`.

#### Response

```json
{
    "success": true,
    "count": 1,
    "routes": [
        {
            "route_name": "205",
            "trip_id": "205_weekday_123",
            "headsign": "金閣寺道 / 北大路バスターミナル",
            "departure_time": "09:05:00",
            "departure_stop_desc": "B3",
            "arrival_time": "09:45:00",
            "arrival_stop_desc": "Main",
            "travel_time_minutes": 40,
            "stops_count": 12,
            "fare": 230,
            "service_id": "weekday_01"
        }
    ]
}
```

**New Fields:**

-   `stops_count`: Number of stops from departure to arrival (including both).
-   `fare`: Bus fare in Japanese Yen (JPY). Returns `null` if fare information is unavailable.

---

### 5. Search Transfer Routes

Find routes with one transfer when no direct route is available.

-   **URL**: `/kcb_api/search/transfer`
-   **Method**: `POST`
-   **Auth**: Required

#### Request Body

```json
{
    "from_stop": "京都駅前",
    "to_stop": "銀閣寺道",
    "current_time": "09:00",
    "day_type": "weekday",
    "date": "2026-01-22",
    "min_transfer_time": 5,
    "limit": 3
}
```

**Parameters:**

-   `from_stop`: Departure stop name (required)
-   `to_stop`: Arrival stop name (required)
-   `current_time`: Departure time in HH:MM format (optional, defaults to current time)
-   `day_type`: `weekday`, `saturday`, or `sunday` (ignored if `date` is provided)
-   `date`: Search date in `YYYY-MM-DD` format (optional, considers holidays)
-   `min_transfer_time`: Minimum transfer time in minutes (default: 5, max: 30)
-   `limit`: Maximum results (default: 5, max: 10)

#### Response

```json
{
    "success": true,
    "query": { ... },
    "count": 1,
    "routes": [
        {
            "type": "transfer",
            "total_time_minutes": 41,
            "legs": [
                {
                    "route_name": "市バス７",
                    "route_id": "00700",
                    "trip_id": "00700_01001_1298",
                    "headsign": "",
                    "departure_stop": "京都駅前",
                    "departure_stop_id": "061212",
                    "departure_stop_desc": "京都駅前(A2)",
                    "departure_time": "09:30:00",
                    "arrival_stop": "河原町丸太町",
                    "arrival_stop_id": "005400",
                    "arrival_stop_desc": "河原町丸太町(C)",
                    "arrival_time": "09:51:00"
                },
                {
                    "route_name": "市バス２０４",
                    "route_id": "20400",
                    "trip_id": "20400_01001_4556",
                    "headsign": "",
                    "departure_stop": "河原町丸太町",
                    "departure_stop_id": "005100",
                    "departure_stop_desc": "河原町丸太町(D)",
                    "departure_time": "09:56:00",
                    "arrival_stop": "銀閣寺道",
                    "arrival_stop_id": "103400",
                    "arrival_stop_desc": "銀閣寺道(B)",
                    "arrival_time": "10:11:00"
                }
            ],
            "transfer_info": {
                "stop_name": "河原町丸太町",
                "from_platform": "河原町丸太町(C)",
                "to_platform": "河原町丸太町(D)",
                "wait_minutes": 5
            }
        }
    ]
}
```

---

### 6. Get Timetable

Get the schedule for a specific stop.

-   **URL**: `/kcb_api/timetable/{stop_id}`
-   **Method**: `GET`
-   **Auth**: Required

#### Parameters

| Name       | Type   | Required | Description                               |
| ---------- | ------ | -------- | ----------------------------------------- |
| `route`    | string | No       | Filter by route name                      |
| `day_type` | string | No       | `weekday` (default), `saturday`, `sunday` |

#### Response

```json
{
    "success": true,
    "stop_id": "061211",
    "stop_name": "京都駅前",
    "count": 50,
    "timetable": [
        {
            "departure_time": "09:00:00",
            "route_name": "205",
            "route_id": "00205",
            "headsign": "金閣寺道",
            "trip_id": "TRIP_123",
            "service_id": "weekday_01"
        }
    ]
}
```

---

### 7. Estimate Bus Location

Estimate the current location of a specific bus trip based on the timetable.

-   **URL**: `/kcb_api/trip/{trip_id}/location`
-   **Method**: `GET`
-   **Auth**: Required

#### Parameters

| Name                | Type   | Required | Description                                                                       |
| ------------------- | ------ | -------- | --------------------------------------------------------------------------------- |
| `time`              | string | No       | Reference time (HH:MM or HH:MM:SS). Default: current server time.                 |
| `departure_stop_id` | string | No       | Your boarding stop ID. If provided, returns the previous 3 stops before boarding. |

#### Response

```json
{
    "success": true,
    "trip_id": "TRIP_123",
    "query_time": "09:20:00",
    "status": "between_stops",
    "message": "河原町五条を出発 → 四条河原町に向かっています",
    "from_stop": {
        "stop_id": "STOP_A",
        "stop_name": "河原町五条",
        "time": "09:18:00"
    },
    "to_stop": {
        "stop_id": "STOP_B",
        "stop_name": "四条河原町",
        "time": "09:22:00"
    },
    "estimated_arrival_minutes": 2,
    "previous_stops": [
        {
            "stop_id": "STOP_X",
            "stop_name": "祇園",
            "time": "09:10:00"
        },
        {
            "stop_id": "STOP_Y",
            "stop_name": "清水道",
            "time": "09:13:00"
        },
        {
            "stop_id": "STOP_Z",
            "stop_name": "東山三条",
            "time": "09:16:00"
        }
    ],
    "boarding_stop": {
        "stop_id": "STOP_BOARD",
        "stop_name": "四条大宮",
        "time": "09:25:00"
    }
}
```

**New Fields (when `departure_stop_id` is provided):**

-   `previous_stops`: List of up to 3 stops before your boarding stop (in order).
-   `boarding_stop`: Your boarding stop information.

**Status Values:**

-   `not_started`: Bus has not left the first stop.
-   `between_stops`: Bus is in transit.
-   `arrived`: Bus has reached the final destination.

**Error Responses:**

-   **400 Bad Request** - Invalid time format:

    ```json
    {
        "detail": "time must be in HH:MM or HH:MM:SS format (e.g., '9:30' or '09:30:00')"
    }
    ```

-   **400 Bad Request** - Hour out of range:
    ```json
    {
        "detail": "hour must be between 0 and 30 for GTFS compatibility"
    }
    ```

---

## Python Client Examples

Here are complete examples using the `requests` library.

### 1. Setup

Define keys and base URL.

```python
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_KEY = "your_actual_api_key_here"  # Match .env

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

def print_resp(resp):
    print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
```

### 2. Search Stops

Find stop ID by name.

```python
# Search for stops containing "Kyoto"
params = {"q": "京都", "limit": 5}
response = requests.get(f"{BASE_URL}/kcb_api/stops/search", headers=headers, params=params)

if response.ok:
    print("Found stops:")
    print_resp(response)
```

### 3. Find Nearby Stops

Find stops near Kyoto Station (34.9858° N, 135.7588° E).

```python
params = {
    "lat": 34.9858,
    "lon": 135.7588,
    "radius": 300,  # 300 meters
    "limit": 5
}
response = requests.get(f"{BASE_URL}/kcb_api/stops/nearby", headers=headers, params=params)

print_resp(response)
```

### 4. Search Route & Get Trip Details

Search for a route and look up the timetable for one of the results.

```python
# 1. Search for route
payload = {
    "from_stop": "京都駅前",
    "to_stop": "四条河原町",
    "current_time": "10:00",
    "day_type": "weekday"
}

resp = requests.post(f"{BASE_URL}/kcb_api/search", headers=headers, json=payload)
data = resp.json()

if data.get("count", 0) > 0:
    top_route = data["routes"][0]
    print(f"Top Route: {top_route['route_name']} (Trip ID: {top_route['trip_id']})")

    # 2. Get Timetable for the departure stop of this route
    stop_id = top_route["departure_stop_id"]
    route_name = top_route["route_name"]

    timetable_url = f"{BASE_URL}/kcb_api/timetable/{stop_id}"
    params = {"route": route_name, "day_type": "weekday"}

    ts_resp = requests.get(timetable_url, headers=headers, params=params)
    print("\nTimetable for this route:")
    print_resp(ts_resp)
else:
    print("No route found.")
```

### 5. Track Bus Location (Estimation)

Using the trip ID from the search result, check where the bus is.

```python
trip_id = "target_trip_id_here"  # Get this from search results

# Check location at 10:15
params = {"time": "10:15"}
loc_resp = requests.get(f"{BASE_URL}/kcb_api/trip/{trip_id}/location", headers=headers, params=params)

print("\nBus Location Status:")
print_resp(loc_resp)
```
