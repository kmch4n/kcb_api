import requests
import sys
import time
from datetime import datetime

BASE_URL = "http://localhost:8000/kcb_api"
API_KEY = "***REMOVED***"


def verify_feature_5():
    print("Verifying Feature 5: Bus Location Estimation")

    # 1. Health Check
    try:
        resp = requests.get(f"{BASE_URL}/health")
        if resp.status_code != 200:
            print(f"Server not healthy: {resp.status_code}")
            return False
        print("Server is healthy.")
    except Exception as e:
        print(f"Failed to connect to server: {e}")
        return False

    # 2. Search for a route to get a trip_id
    # We need a trip ID to query location.
    # Let's search for a common route.
    search_payload = {
        "from_stop": "京都駅前",
        "to_stop": "四条河原町",
        "current_time": "12:00",
        "day_type": "weekday",
    }
    headers = {"X-API-Key": API_KEY}

    print(f"Searching for route: {search_payload}")
    resp = requests.post(f"{BASE_URL}/search", json=search_payload, headers=headers)

    if resp.status_code != 200:
        print(f"Search failed: {resp.status_code} {resp.text}")
        # Try to get API KEY from environment if failed?
        # Assuming dev environment has some key or check if auth is enabled.
        # But let's proceed assuming the key works or we find out why.
        return False

    data = resp.json()
    if not data.get("routes"):
        print("No routes found. Cannot proceed with verification.")
        return False

    route = data["routes"][0]
    trip_id = route["trip_id"]
    print(f"Found trip: {trip_id} (Route: {route['route_name']})")

    # 3. Test Location Endpoint with different times

    # Text Case A: Before Start
    # Departure is around 12:00 (based on search). Let's check 10:00.
    print("\n--- Test Case A: Before Start (10:00) ---")
    check_location(trip_id, "10:00", headers)

    # Test Case B: During Trip
    # We need to pick a time between departure and arrival.
    dep_time = route["departure_time"]
    arr_time = route["arrival_time"]

    # Calculate a middle time
    def parse_time(t):
        h, m, s = map(int, t.split(":"))
        return h * 60 + m

    def format_time(m):
        h = m // 60
        mn = m % 60
        return f"{h:02d}:{mn:02d}"

    mid_minutes = (parse_time(dep_time) + parse_time(arr_time)) // 2
    mid_time = format_time(mid_minutes)

    print(f"\n--- Test Case B: During Trip ({mid_time}) ---")
    check_location(trip_id, mid_time, headers)

    # Test Case C: After Arrival
    # Check 1 hour after arrival
    after_minutes = parse_time(arr_time) + 60
    after_time = format_time(after_minutes)

    print(f"\n--- Test Case C: After Arrival ({after_time}) ---")
    check_location(trip_id, after_time, headers)


def check_location(trip_id, time_str, headers):
    url = f"{BASE_URL}/trip/{trip_id}/location?time={time_str}"
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        loc = resp.json()
        print(f"Status: {loc['status']}")
        print(f"Message: {loc['message']}")
        if loc.get("from_stop"):
            print(f"From: {loc['from_stop']['stop_name']} ({loc['from_stop']['time']})")
        if loc.get("to_stop"):
            print(f"To:   {loc['to_stop']['stop_name']} ({loc['to_stop']['time']})")
    else:
        print(f"Failed: {resp.status_code} {resp.text}")


if __name__ == "__main__":
    # Give server a moment to start if run immediately
    time.sleep(2)
    verify_feature_5()
