"""
FastAPI application for Kyoto City Bus route search
"""
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
import logging

from config import settings
from auth import verify_api_key
from bus_route_search import search_bus, GTFSDataLoader

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Kyoto City Bus API",
    description="API for searching Kyoto City Bus routes",
    version="1.0.0",
    docs_url="/kcb_api/docs",
    redoc_url="/kcb_api/redoc",
    openapi_url="/kcb_api/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Request/Response Models
# ============================================================

class SearchRequest(BaseModel):
    """Bus route search request"""
    from_stop: str = Field(..., description="出発停留所名", min_length=1)
    to_stop: str = Field(..., description="到着停留所名", min_length=1)
    current_time: Optional[str] = Field(None, description="出発時刻 (HH:MM形式)", pattern=r"^\d{1,2}:\d{2}$")
    day_type: str = Field("weekday", description="運行日タイプ (weekday/saturday/sunday)")
    limit: int = Field(3, description="最大結果件数", ge=1, le=10)
    
    @field_validator('day_type')
    @classmethod
    def validate_day_type(cls, v: str) -> str:
        allowed = {'weekday', 'saturday', 'sunday'}
        if v not in allowed:
            raise ValueError(f"day_type must be one of {allowed}")
        return v


class BusRoute(BaseModel):
    """個別のバス路線情報"""
    route_name: str = Field(..., description="路線名")
    route_id: str = Field(..., description="路線ID")
    trip_id: str = Field(..., description="便ID")
    headsign: str = Field(..., description="行き先表示")
    departure_time: str = Field(..., description="出発時刻")
    departure_stop_id: str = Field(..., description="出発停留所ID")
    departure_stop_desc: str = Field(..., description="出発停留所詳細")
    arrival_time: str = Field(..., description="到着時刻")
    arrival_stop_id: str = Field(..., description="到着停留所ID")
    arrival_stop_desc: str = Field(..., description="到着停留所詳細")
    travel_time_minutes: int = Field(..., description="所要時間（分）")
    service_id: str = Field(..., description="運行サービスID")


class SearchResponse(BaseModel):
    """検索結果レスポンス"""
    success: bool = Field(True, description="検索成功フラグ")
    query: dict = Field(..., description="検索条件")
    count: int = Field(..., description="検索結果件数")
    routes: List[BusRoute] = Field(..., description="バス路線リスト")


class ErrorResponse(BaseModel):
    """エラーレスポンス"""
    success: bool = Field(False, description="常にFalse")
    error: str = Field(..., description="エラーメッセージ")
    detail: Optional[str] = Field(None, description="詳細情報")


# ============================================================
# Startup Event - Preload GTFS Data
# ============================================================

@app.on_event("startup")
async def startup_event():
    """
    Server startup event - preload GTFS data into memory
    """
    logger.info("Starting KCB API server...")
    logger.info(f"Preloading GTFS data from: {settings.get_gtfs_dir()}")
    
    try:
        # Initialize data loader (will cache data in memory)
        loader = GTFSDataLoader.get_instance(settings.get_gtfs_dir())
        
        # Preload all data
        logger.info("Loading stops...")
        loader.load_stops()
        
        logger.info("Loading routes...")
        loader.load_routes()
        
        logger.info("Loading trips...")
        loader.load_trips()
        
        logger.info("Loading stop times (this may take a moment)...")
        loader.load_stop_times()
        
        logger.info("Loading calendar...")
        loader.load_calendar()
        
        logger.info("GTFS data loaded successfully!")
        
    except Exception as e:
        logger.error(f"Failed to load GTFS data: {e}")
        raise


# ============================================================
# API Endpoints
# ============================================================

@app.get("/kcb_api/health")
async def health_check():
    """
    Health check endpoint (no authentication required)
    """
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post(
    "/kcb_api/search",
    response_model=SearchResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized - Invalid API Key"},
        400: {"model": ErrorResponse, "description": "Bad Request - Invalid parameters"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    }
)
async def search_routes(
    request: SearchRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    京都市バスの経路を検索
    
    - **from_stop**: 出発停留所名（例: "堀川下長者町"）
    - **to_stop**: 到着停留所名（例: "京都駅前"）
    - **current_time**: 出発時刻（HH:MM形式、省略時は現在時刻）
    - **day_type**: 運行日タイプ（weekday/saturday/sunday）
    - **limit**: 最大結果件数（1-10、デフォルト3）
    """
    try:
        logger.info(f"Search request: {request.from_stop} -> {request.to_stop}")
        
        # Call search function
        results = search_bus(
            from_stop_name=request.from_stop,
            to_stop_name=request.to_stop,
            current_time=request.current_time,
            day_type=request.day_type
        )
        
        # Apply limit
        limited_results = results[:request.limit]
        
        # Convert to response model
        routes = [BusRoute(**route) for route in limited_results]
        
        response = SearchResponse(
            success=True,
            query={
                "from_stop": request.from_stop,
                "to_stop": request.to_stop,
                "current_time": request.current_time or "現在時刻",
                "day_type": request.day_type,
                "limit": request.limit
            },
            count=len(routes),
            routes=routes
        )
        
        logger.info(f"Found {len(routes)} routes")
        return response
        
    except ValueError as e:
        # Handle search errors (e.g., stop not found)
        logger.warning(f"Search error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred"
        )


# ============================================================
# Exception Handlers
# ============================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if settings.LOG_LEVEL == "debug" else None
        }
    )


# ============================================================
# Main entry point
# ============================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL
    )
