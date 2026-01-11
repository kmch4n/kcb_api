"""
Test script for Kyoto City Bus API using requests library

This script tests all API endpoints and measures response times.
The API key is loaded from environment variables or .env file.

Usage:
    python tests/test_api.py
    
    Or with custom base URL:
    BASE_URL=http://example.com:8000 python tests/test_api.py
"""
import requests
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path


# Add parent directory to path for .env loading
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False


# Configuration
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY")

if not API_KEY:
    print("ERROR: API_KEY not found in environment variables or .env file")
    print("Please set API_KEY in .env file or as environment variable")
    sys.exit(1)


class APITester:
    """API test runner with timing measurements"""
    
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.api_key = api_key
        self.passed = 0
        self.failed = 0
        self.total_time = 0
    
    def print_section(self, title):
        """Print a formatted section header"""
        print(f"\n{'=' * 80}")
        print(f"  {title}")
        print('=' * 80)
    
    def print_response(self, response, elapsed_ms):
        """Print formatted response with timing"""
        print(f"Status Code: {response.status_code}")
        print(f"Response Time: {elapsed_ms:.2f}ms")
        print(f"Response:")
        try:
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        except:
            print(response.text)
    
    def make_request(self, method, url, **kwargs):
        """Make HTTP request and measure time"""
        start = time.time()
        response = method(url, **kwargs)
        elapsed = (time.time() - start) * 1000  # Convert to milliseconds
        self.total_time += elapsed
        return response, elapsed
    
    def test_health_check(self):
        """Test 1: Health check endpoint (no authentication required)"""
        self.print_section("Test 1: Health Check")
        
        url = f"{self.base_url}/kcb_api/health"
        response, elapsed = self.make_request(requests.get, url)
        
        self.print_response(response, elapsed)
        
        assert response.status_code == 200, "Health check failed"
        assert response.json()["status"] == "healthy", "Server is not healthy"
        print("✅ PASSED: Health check successful")
    
    def test_search_without_auth(self):
        """Test 2: Search without API key (should fail with 401)"""
        self.print_section("Test 2: Search Without Authentication")
        
        url = f"{self.base_url}/kcb_api/search"
        data = {
            "from_stop": "京都駅前",
            "to_stop": "四条河原町"
        }
        
        response, elapsed = self.make_request(requests.post, url, json=data)
        
        self.print_response(response, elapsed)
        
        assert response.status_code == 401, "Expected 401 Unauthorized"
        print("✅ PASSED: Correctly rejected unauthenticated request")
    
    def test_search_with_auth(self):
        """Test 3: Search with valid API key"""
        self.print_section("Test 3: Basic Search (京都駅前 → 四条河原町)")
        
        url = f"{self.base_url}/kcb_api/search"
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }
        data = {
            "from_stop": "京都駅前",
            "to_stop": "四条河原町"
        }
        
        response, elapsed = self.make_request(requests.post, url, json=data, headers=headers)
        
        self.print_response(response, elapsed)
        
        assert response.status_code == 200, "Search failed"
        result = response.json()
        assert result["success"] == True, "Search was not successful"
        print(f"✅ PASSED: Found {result['count']} routes")
    
    def test_search_with_time(self):
        """Test 4: Search with specific time"""
        self.print_section("Test 4: Search with Specific Time (堀川下長者町 → 京都駅前, 14:30)")
        
        url = f"{self.base_url}/kcb_api/search"
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }
        data = {
            "from_stop": "堀川下長者町",
            "to_stop": "京都駅前",
            "current_time": "14:30",
            "day_type": "weekday",
            "limit": 3
        }
        
        response, elapsed = self.make_request(requests.post, url, json=data, headers=headers)
        
        self.print_response(response, elapsed)
        
        assert response.status_code == 200, "Search with time failed"
        result = response.json()
        
        if result["count"] > 0:
            print(f"✅ PASSED: Found {result['count']} routes")
            # Print route details
            for i, route in enumerate(result["routes"], 1):
                print(f"\nRoute {i}:")
                print(f"  {route['route_name']} ({route['headsign']})")
                print(f"  {route['departure_time']} → {route['arrival_time']}")
                print(f"  {route['travel_time_minutes']} minutes")
        else:
            print("⚠️ WARNING: No routes found (might be expected depending on time)")
    
    def test_invalid_stop(self):
        """Test 5: Search with invalid stop name"""
        self.print_section("Test 5: Search with Invalid Stop Name")
        
        url = f"{self.base_url}/kcb_api/search"
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }
        data = {
            "from_stop": "NonExistentStop",
            "to_stop": "京都駅前"
        }
        
        response, elapsed = self.make_request(requests.post, url, json=data, headers=headers)
        
        self.print_response(response, elapsed)
        
        assert response.status_code == 400, "Expected 400 Bad Request"
        print("✅ PASSED: Correctly handled invalid stop name")
    
    def test_weekend_search(self):
        """Test 6: Search for Sunday schedule"""
        self.print_section("Test 6: Sunday Schedule (京都駅前 → 金閣寺道)")
        
        url = f"{self.base_url}/kcb_api/search"
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }
        data = {
            "from_stop": "京都駅前",
            "to_stop": "金閣寺道",
            "current_time": "09:00",
            "day_type": "sunday"
        }
        
        response, elapsed = self.make_request(requests.post, url, json=data, headers=headers)
        
        self.print_response(response, elapsed)
        
        assert response.status_code == 200, "Sunday search failed"
        result = response.json()
        print(f"✅ PASSED: Sunday schedule - found {result['count']} routes")
    
    def run_all_tests(self):
        """Run all tests and return success status"""
        tests = [
            self.test_health_check,
            self.test_search_without_auth,
            self.test_search_with_auth,
            self.test_search_with_time,
            self.test_invalid_stop,
            self.test_weekend_search
        ]
        
        for test in tests:
            try:
                test()
                self.passed += 1
            except AssertionError as e:
                print(f"❌ FAILED: {e}")
                self.failed += 1
            except requests.exceptions.ConnectionError:
                print(f"❌ FAILED: Cannot connect to {self.base_url}")
                print("Make sure the server is running!")
                break
            except Exception as e:
                print(f"❌ FAILED: Unexpected error - {e}")
                self.failed += 1
        
        return self.failed == 0


def main():
    """Main test runner"""
    print(f"\n{'*' * 80}")
    print(f"  Kyoto City Bus API - Test Suite")
    print(f"  Base URL: {BASE_URL}")
    print(f"  API Key: {API_KEY[:10]}..." if len(API_KEY) > 10 else f"  API Key: {API_KEY}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if HAS_DOTENV:
        print(f"  .env: Loaded successfully")
    else:
        print(f"  .env: python-dotenv not installed (using environment variables only)")
    print(f"{'*' * 80}")
    
    tester = APITester(BASE_URL, API_KEY)
    success = tester.run_all_tests()
    
    # Summary
    tester.print_section("Test Summary")
    print(f"Total Tests: {tester.passed + tester.failed}")
    print(f"✅ Passed: {tester.passed}")
    print(f"❌ Failed: {tester.failed}")
    print(f"⏱️  Total Response Time: {tester.total_time:.2f}ms")
    print(f"⏱️  Average Response Time: {tester.total_time / (tester.passed + tester.failed):.2f}ms" 
          if (tester.passed + tester.failed) > 0 else "N/A")
    
    if tester.failed == 0:
        print("\n🎉 All tests passed successfully!")
    else:
        print(f"\n⚠️ {tester.failed} test(s) failed")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
