# Tests

This directory contains test scripts for the Kyoto City Bus API.

## Test Files

-   `test_api.py` - Integration tests for API endpoints using requests library

## Running Tests

### Prerequisites

Install test dependencies:

```bash
pip install requests python-dotenv
```

### Basic Usage

Make sure the API server is running, then:

```bash
# Run tests
python tests/test_api.py
```

The test script will:

-   Load API_KEY from `.env` file automatically
-   Test all API endpoints
-   Measure response times
-   Display detailed results

### Custom Configuration

You can override settings using environment variables:

```bash
# Use custom base URL
BASE_URL=http://example.com:8000 python tests/test_api.py

# Use custom API key
API_KEY=your-key-here python tests/test_api.py
```

## Test Coverage

The test suite includes:

1. **Health Check** - Verify server is running
2. **Authentication** - Test API key validation (success & failure)
3. **Basic Search** - Search for bus routes between two stops
4. **Time-specific Search** - Search with specific departure time
5. **Error Handling** - Test invalid stop names
6. **Weekend Schedule** - Test Sunday/Saturday schedules

## Test Output

Each test displays:

-   Status code
-   Response time in milliseconds
-   Full JSON response
-   Pass/fail status

Summary includes:

-   Total tests run
-   Pass/fail count
-   Total response time
-   Average response time

## Expected Results

All tests should pass when:

-   Server is running on the configured base URL
-   Valid API_KEY is configured
-   GTFS data is loaded in the `data/` directory

## Troubleshooting

**Connection Error**

```
❌ FAILED: Cannot connect to http://localhost:8000
```

Solution: Start the API server with `python main.py`

**Missing API Key**

```
ERROR: API_KEY not found
```

Solution: Ensure `.env` file exists with `API_KEY=your-key-here`

**No Routes Found**

```
⚠️ WARNING: No routes found
```

This may be expected depending on the time and day. The test searches for routes after the specified time.
