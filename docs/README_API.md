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
            "stop_name": "京都駅八条口",
            "stop_desc": "Northbound",
            "stop_lat": 35.001,
            "stop_lon": 135.701,
            "distance_meters": 150.5
        }
    ]
}
```

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
    "limit": 3
}
```

_Note: `day_type` can be `weekday`, `saturday`, or `sunday`._

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
            "service_id": "weekday_01"
        }
    ]
}
```

---

### 5. Get Timetable

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

### 6. Estimate Bus Location

Estimate the current location of a specific bus trip based on the timetable.

-   **URL**: `/kcb_api/trip/{trip_id}/location`
-   **Method**: `GET`
-   **Auth**: Required

#### Parameters

| Name   | Type   | Required | Description                                                       |
| ------ | ------ | -------- | ----------------------------------------------------------------- |
| `time` | string | No       | Reference time (HH:MM or HH:MM:SS). Default: current server time. |

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
    "estimated_arrival_minutes": 2
}
```

**Status Values:**

-   `not_started`: Bus has not left the first stop.
-   `between_stops`: Bus is in transit.
-   `arrived`: Bus has reached the final destination.

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
