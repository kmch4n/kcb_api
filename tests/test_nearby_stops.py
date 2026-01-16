"""
Test script for Nearby Stops API

Tests the nearby stops search functionality with various locations in Kyoto.
The API key is loaded from environment variables or .env file.

Usage:
    python tests/test_nearby_stops.py
"""

import requests
import json
import os
import sys
from pathlib import Path

# Add parent directory to path for .env loading
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Configuration
BASE_URL = os.getenv("BASE_URL", "http://localhost:8081")
API_KEY = os.getenv("API_KEY")

if not API_KEY:
    print("ERROR: API_KEY not found in environment variables or .env file")
    sys.exit(1)


def test_nearby_stops(
    lat: float, lon: float, radius: int = 500, limit: int = 10, description: str = ""
):
    """Test nearby stops search"""
    print(f"\n{'=' * 80}")
    print(f"  {description}")
    print(f"  Location: ({lat}, {lon}), Radius: {radius}m, Limit: {limit}")
    print("=" * 80)

    url = f"{BASE_URL}/kcb_api/stops/nearby"
    headers = {"X-API-Key": API_KEY}
    params = {"lat": lat, "lon": lon, "radius": radius, "limit": limit}

    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Found: {data['count']} stops")
            print()

            for i, stop in enumerate(data["stops"], 1):
                print(f"{i}. {stop['stop_name']}")
                print(f"   距離: {stop['distance_meters']}m")
                print(f"   代表ID: {stop['stop_id']}")
                if 'stop_ids' in stop:
                    print(f"   全ID: {stop['stop_ids']}")
                else:
                    print(f"   (stop_ids未対応 - サーバー再起動が必要)")
                print(f"   説明: {stop['stop_desc']}")
                print()

            return data
        else:
            print(f"Error: {response.text}")
            return None

    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to {BASE_URL}")
        print("   Make sure the server is running!")
        return None


def main():
    print("=" * 80)
    print("  Nearby Stops API Test")
    print(f"  Base URL: {BASE_URL}")
    print("=" * 80)

    # Test 1: 京都駅周辺（多くのバス停がある場所）
    test_nearby_stops(
        lat=34.985849,
        lon=135.758767,
        radius=300,
        limit=10,
        description="Test 1: 京都駅周辺 (300m)",
    )

    # Test 2: 四条河原町周辺
    test_nearby_stops(
        lat=35.003713,
        lon=135.768681,
        radius=200,
        limit=5,
        description="Test 2: 四条河原町周辺 (200m)",
    )

    # Test 3: 金閣寺周辺
    test_nearby_stops(
        lat=35.039469,
        lon=135.729247,
        radius=500,
        limit=5,
        description="Test 3: 金閣寺周辺 (500m)",
    )

    # Test 4: 重複確認 - 同じ場所で広い半径
    print("\n" + "=" * 80)
    print("  Test 4: 重複排除確認 - 京都駅周辺 (1000m)")
    print("  → 同じ停留所名が複数回出ないことを確認")
    print("=" * 80)

    result = test_nearby_stops(
        lat=34.985849,
        lon=135.758767,
        radius=1000,
        limit=20,
        description="Test 4: 京都駅周辺 (1000m) - 重複確認",
    )

    if result:
        # Check for duplicates
        stop_names = [stop["stop_name"] for stop in result["stops"]]
        unique_names = set(stop_names)

        if len(stop_names) == len(unique_names):
            print("✅ 重複なし！各停留所名は1回のみ表示されています")
        else:
            duplicates = [name for name in unique_names if stop_names.count(name) > 1]
            print(f"⚠️ 重複あり: {duplicates}")


if __name__ == "__main__":
    main()
