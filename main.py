"""
FastAPI application for Kyoto City Bus route search
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
import math
from datetime import datetime
import re
import logging

from config import settings
from auth import verify_api_key
from bus_route_search import (
    search_bus,
    find_transfer_routes,
    GTFSDataLoader,
    search_similar_stop_names,
    parse_gtfs_time,
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Kyoto City Bus API",
    description="""京都市バスの経路・時刻表・停留所を検索するAPIです。

## データソースについて

本APIが利用する公共交通データは、**[公共交通オープンデータセンター](https://www.odpt.org/)** において提供されるものです（公共交通オープンデータ基本ライセンス）。

本APIを利用したアプリを公開する際は、エンドユーザーへの通知が義務付けられています。
`GET /kcb_api/info` エンドポイントで通知文を取得し、アプリ内（ヘルプ・免責事項画面等）に表示してください。
""",
    version="1.0.0",
    docs_url="/kcb_api/docs",
    redoc_url="/kcb_api/redoc",
    openapi_url="/kcb_api/openapi.json",
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
    current_time: Optional[str] = Field(
        None, description="出発時刻 (HH:MM形式)", pattern=r"^\d{1,2}:\d{2}$"
    )
    day_type: str = Field(
        "weekday",
        description="運行日タイプ (weekday/saturday/sunday)。dateが指定された場合は無視されます。",
    )
    date: Optional[str] = Field(
        None,
        description="検索日（YYYY-MM-DD形式）。祝日・特別ダイヤを考慮します。指定時はday_typeより優先されます。",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    limit: int = Field(3, description="最大結果件数", ge=1, le=10)

    @field_validator("day_type")
    @classmethod
    def validate_day_type(cls, v: str) -> str:
        allowed = {"weekday", "saturday", "sunday"}
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
    stops_count: int = Field(..., description="停車駅数（出発地・目的地を含む）")
    fare: Optional[int] = Field(None, description="運賃（円）")
    service_id: str = Field(..., description="運行サービスID")


class SearchResponse(BaseModel):
    """検索結果レスポンス"""

    success: bool = Field(True, description="検索成功フラグ")
    query: dict = Field(..., description="検索条件")
    count: int = Field(..., description="検索結果件数")
    routes: List[BusRoute] = Field(..., description="バス路線リスト")


class TransferSearchRequest(BaseModel):
    """乗り換え検索リクエスト"""

    from_stop: str = Field(..., description="出発停留所名", min_length=1)
    to_stop: str = Field(..., description="到着停留所名", min_length=1)
    current_time: Optional[str] = Field(
        None,
        description="出発時刻 (HH:MM形式)。省略時は現在時刻",
        pattern=r"^\d{1,2}:\d{2}(:\d{2})?$",
    )
    day_type: str = Field(
        "weekday",
        description="運行日タイプ (weekday/saturday/sunday)。dateが指定された場合は無視されます。",
    )
    date: Optional[str] = Field(
        None,
        description="検索日（YYYY-MM-DD形式）。祝日・特別ダイヤを考慮します。",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    min_transfer_time: int = Field(5, description="最小乗り換え時間（分）", ge=1, le=30)
    limit: int = Field(5, description="最大結果件数", ge=1, le=10)


class TransferLeg(BaseModel):
    """乗り換え経路の1区間"""

    route_name: str = Field(..., description="路線名")
    route_id: str = Field(..., description="路線ID")
    trip_id: str = Field(..., description="便ID")
    headsign: str = Field(..., description="行き先表示")
    departure_stop: str = Field(..., description="出発停留所名")
    departure_stop_id: str = Field(..., description="出発停留所ID")
    departure_stop_desc: str = Field(..., description="出発停留所詳細")
    departure_time: str = Field(..., description="出発時刻")
    arrival_stop: str = Field(..., description="到着停留所名")
    arrival_stop_id: str = Field(..., description="到着停留所ID")
    arrival_stop_desc: str = Field(..., description="到着停留所詳細")
    arrival_time: str = Field(..., description="到着時刻")


class TransferInfo(BaseModel):
    """乗り換え情報"""

    stop_name: str = Field(..., description="乗り換え停留所名")
    from_platform: str = Field(..., description="降車プラットフォーム")
    to_platform: str = Field(..., description="乗車プラットフォーム")
    wait_minutes: int = Field(..., description="乗り換え待ち時間（分）")


class TransferRoute(BaseModel):
    """乗り換え経路"""

    type: str = Field("transfer", description="経路タイプ")
    total_time_minutes: int = Field(..., description="総所要時間（分）")
    legs: List[TransferLeg] = Field(..., description="経路区間リスト")
    transfer_info: TransferInfo = Field(..., description="乗り換え情報")


class TransferSearchResponse(BaseModel):
    """乗り換え検索レスポンス"""

    success: bool = Field(True, description="検索成功フラグ")
    query: dict = Field(..., description="検索条件")
    count: int = Field(..., description="検索結果件数")
    routes: List[TransferRoute] = Field(..., description="乗り換え経路リスト")


class ErrorResponse(BaseModel):
    """エラーレスポンス"""

    success: bool = Field(False, description="常にFalse")
    error: str = Field(..., description="エラーメッセージ")
    detail: Optional[str] = Field(None, description="詳細情報")
    status_code: Optional[int] = Field(None, description="HTTPステータスコード")


class StopInfo(BaseModel):
    """停留所情報"""

    stop_name: str = Field(..., description="停留所名")
    stop_ids: List[str] = Field(
        ..., description="停留所ID一覧（同名の停留所が複数ある場合）"
    )


class StopSearchResponse(BaseModel):
    """停留所検索結果"""

    success: bool = Field(True, description="検索成功フラグ")
    query: str = Field(..., description="検索クエリ")
    count: int = Field(..., description="検索結果件数")
    stops: List[StopInfo] = Field(..., description="停留所リスト")


class TimetableEntry(BaseModel):
    """時刻表エントリ"""

    departure_time: str = Field(..., description="出発時刻")
    route_name: str = Field(..., description="路線名")
    route_id: str = Field(..., description="路線ID")
    headsign: str = Field(..., description="行き先")
    trip_id: str = Field(..., description="便ID")
    service_id: str = Field(..., description="運行サービスID")


class TimetableResponse(BaseModel):
    """時刻表レスポンス"""

    success: bool = Field(True, description="成功フラグ")
    stop_id: str = Field(..., description="停留所ID")
    stop_name: Optional[str] = Field(None, description="停留所名")
    count: int = Field(..., description="便数")
    timetable: List[TimetableEntry] = Field(..., description="時刻表エントリ")


class NearbyStopInfo(BaseModel):
    """周辺停留所情報"""

    stop_id: str = Field(..., description="代表停留所ID（最も近いプラットフォーム）")
    stop_ids: List[str] = Field(..., description="同じ停留所名に属するすべての停留所ID")
    stop_name: str = Field(..., description="停留所名")
    stop_desc: str = Field(..., description="停留所説明（最も近いプラットフォーム）")
    stop_lat: float = Field(..., description="緯度（最も近いプラットフォーム）")
    stop_lon: float = Field(..., description="経度（最も近いプラットフォーム）")
    distance_meters: float = Field(
        ..., description="距離（メートル、最も近いプラットフォームまで）"
    )


class NearbyStopsResponse(BaseModel):
    """周辺停留所検索レスポンス"""

    success: bool = Field(True, description="成功フラグ")
    query: dict = Field(..., description="検索条件")
    count: int = Field(..., description="検索結果件数")
    stops: List[NearbyStopInfo] = Field(..., description="停留所リスト")


class StopLocation(BaseModel):
    """停留所位置情報"""

    stop_id: str = Field(..., description="停留所ID")
    stop_name: str = Field(..., description="停留所名")
    time: str = Field(..., description="時刻")


class TripLocationResponse(BaseModel):
    """バス現在位置情報レスポンス"""

    success: bool = Field(True, description="成功フラグ")
    trip_id: str = Field(..., description="便ID")
    query_time: str = Field(..., description="照会時刻")
    status: str = Field(..., description="運行状況 (not_started/between_stops/arrived)")
    message: str = Field(..., description="状況メッセージ")
    from_stop: Optional[StopLocation] = Field(None, description="直前の停留所")
    to_stop: Optional[StopLocation] = Field(None, description="直後の停留所")
    estimated_arrival_minutes: Optional[int] = Field(
        None, description="次停留所までの推定時間(分)"
    )
    previous_stops: Optional[List[StopLocation]] = Field(
        None, description="乗車予定バス停の前3つの停留所（順番通り）"
    )
    boarding_stop: Optional[StopLocation] = Field(
        None, description="ユーザーの乗車予定バス停"
    )


class DataNoticeResponse(BaseModel):
    """データソース情報と利用通知"""

    data_source: str = Field(..., description="データ提供元")
    data_source_url: str = Field(..., description="データ提供元URL")
    operator: str = Field(..., description="公共交通事業者名")
    notice: List[str] = Field(..., description="利用通知文（各項目を順番に表示してください）")
    contact: str = Field(..., description="本アプリに関する問い合わせ先")


# ============================================================
# Utility Functions
# ============================================================


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two GPS coordinates using Haversine formula

    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates

    Returns:
        Distance in meters
    """
    R = 6371000  # Earth radius in meters

    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    # Haversine formula
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


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


@app.get("/kcb_api/info", response_model=DataNoticeResponse, tags=["General"])
async def get_data_notice():
    """
    データソース情報と利用通知を返します（認証不要）。

    本APIを利用したアプリを公開する際は、このエンドポイントが返す `notice` の内容を
    アプリのヘルプ・免責事項画面等でエンドユーザーに表示してください。
    """
    return DataNoticeResponse(
        data_source="公共交通オープンデータセンター",
        data_source_url="https://www.odpt.org/",
        operator="京都市交通局",
        notice=[
            "本アプリケーション等が利用する公共交通データは、公共交通オープンデータセンターにおいて提供されるものです。",
            "公共交通事業者により提供されたデータを元にしていますが、必ずしも正確・完全なものとは限りません。",
            "本アプリケーションの表示内容について、公共交通事業者への直接の問合せは行わないでください。",
        ],
        contact="kmchan@kmchan.jp",
    )


@app.get(
    "/kcb_api/stops/search",
    response_model=StopSearchResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized - Invalid API Key"},
        400: {
            "model": ErrorResponse,
            "description": "Bad Request - Invalid parameters",
        },
    },
)
async def search_stops(q: str, limit: int = 10, api_key: str = Depends(verify_api_key)):
    """
    停留所名を検索（部分一致）

    - **q**: 検索クエリ（停留所名の一部）
    - **limit**: 最大結果件数（1-50、デフォルト10）
    """
    try:
        # Validate limit
        if limit < 1 or limit > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="limit must be between 1 and 50",
            )

        logger.info(f"Stop search request: q='{q}', limit={limit}")

        # Load stops data
        loader = GTFSDataLoader.get_instance(settings.get_gtfs_dir())
        stops_data = loader.load_stops()

        # Search for similar stop names
        matching_names = search_similar_stop_names(q, stops_data, limit=limit)

        # Build response
        stops_list = []
        for stop_name in matching_names:
            stop_ids = [stop["stop_id"] for stop in stops_data[stop_name]]
            stops_list.append(StopInfo(stop_name=stop_name, stop_ids=stop_ids))

        response = StopSearchResponse(
            success=True, query=q, count=len(stops_list), stops=stops_list
        )

        logger.info(f"Found {len(stops_list)} matching stops")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in stop search: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred",
        )


@app.get(
    "/kcb_api/timetable/{stop_id}",
    response_model=TimetableResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized - Invalid API Key"},
        404: {"model": ErrorResponse, "description": "Stop not found"},
    },
)
async def get_timetable(
    stop_id: str,
    route: Optional[str] = None,
    day_type: str = "weekday",
    api_key: str = Depends(verify_api_key),
):
    """
    特定停留所の時刻表を取得

    - **stop_id**: 停留所ID（必須）
    - **route**: 路線名でフィルタ（オプション、例: "205"）
    - **day_type**: 運行日タイプ（weekday/saturday/sunday、デフォルト: weekday）
    """
    try:
        logger.info(
            f"Timetable request: stop_id={stop_id}, route={route}, day_type={day_type}"
        )

        # Load GTFS data
        loader = GTFSDataLoader.get_instance(settings.get_gtfs_dir())
        trip_to_stops, stop_to_trips = loader.load_stop_times()
        routes_data = loader.load_routes()
        trips_data = loader.load_trips()
        calendar_data = loader.load_calendar()
        stops_data = loader.load_stops()

        # Check if stop exists
        if stop_id not in stop_to_trips:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stop ID '{stop_id}' not found",
            )

        # Determine service IDs for the day type
        from bus_route_search import determine_service_ids

        service_ids = determine_service_ids(day_type)

        # Get stop name
        stop_name = None
        for name, stop_list in stops_data.items():
            if any(s["stop_id"] == stop_id for s in stop_list):
                stop_name = name
                break

        # Collect timetable entries
        timetable_entries = []
        trip_ids = stop_to_trips[stop_id]

        for trip_id in trip_ids:
            trip_info = trips_data.get(trip_id)
            if not trip_info:
                continue

            # Filter by service_id (day type)
            if trip_info["service_id"] not in service_ids:
                continue

            # Filter by route if specified
            route_id = trip_info["route_id"]
            route_name = routes_data.get(route_id, "")

            if route and route not in route_name:
                continue

            # Find departure time for this stop
            stops_in_trip = trip_to_stops.get(trip_id, [])
            for stop_info in stops_in_trip:
                if stop_info["stop_id"] == stop_id:
                    timetable_entries.append(
                        TimetableEntry(
                            departure_time=stop_info["departure_time"],
                            route_name=route_name,
                            route_id=route_id,
                            headsign=trip_info["headsign"],
                            trip_id=trip_id,
                            service_id=trip_info["service_id"],
                        )
                    )
                    break

        # Sort by departure time
        timetable_entries.sort(key=lambda x: x.departure_time)

        response = TimetableResponse(
            success=True,
            stop_id=stop_id,
            stop_name=stop_name,
            count=len(timetable_entries),
            timetable=timetable_entries,
        )

        logger.info(f"Found {len(timetable_entries)} timetable entries")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in timetable: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred",
        )


@app.get(
    "/kcb_api/stops/nearby",
    response_model=NearbyStopsResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized - Invalid API Key"},
        400: {
            "model": ErrorResponse,
            "description": "Bad Request - Invalid parameters",
        },
    },
)
async def get_nearby_stops(
    lat: float,
    lon: float,
    radius: int = 500,
    limit: int = 20,
    api_key: str = Depends(verify_api_key),
):
    """
    GPS座標から指定半径内の停留所を検索

    - **lat**: 緯度（-90 to 90）
    - **lon**: 経度（-180 to 180）
    - **radius**: 検索半径（メートル、デフォルト500、最大5000）
    - **limit**: 最大結果数（デフォルト20、最大100）
    """
    try:
        # Validate coordinates
        if not (-90 <= lat <= 90):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Latitude must be between -90 and 90",
            )
        if not (-180 <= lon <= 180):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Longitude must be between -180 and 180",
            )

        # Validate radius
        if radius < 1 or radius > 5000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Radius must be between 1 and 5000 meters",
            )

        # Validate limit
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Limit must be between 1 and 100",
            )

        logger.info(
            f"Nearby stops request: lat={lat}, lon={lon}, radius={radius}, limit={limit}"
        )

        # Load stops data
        loader = GTFSDataLoader.get_instance(settings.get_gtfs_dir())
        stops_data = loader.load_stops()

        # Calculate bounding box for optimization (rough filter)
        # 1 degree latitude ≈ 111km
        lat_delta = (radius / 111000) * 1.5  # Add margin

        # 極座標付近でのゼロ除算を防ぐ
        if abs(lat) > 89:
            # 極点付近では経度の変化が小さいため、大きめのマージンを設定
            lon_delta = 180  # 全経度を含む
        else:
            lon_delta = (radius / (111000 * math.cos(math.radians(lat)))) * 1.5

        # Collect nearby stops grouped by stop_name
        # Key: stop_name, Value: dict with best (nearest) stop info and all stop_ids
        stops_by_name: dict = {}

        for stop_name, stop_list in stops_data.items():
            for stop in stop_list:
                stop_lat = float(stop["stop_lat"])
                stop_lon = float(stop["stop_lon"])

                # Quick bounding box filter
                if not (
                    lat - lat_delta <= stop_lat <= lat + lat_delta
                    and lon - lon_delta <= stop_lon <= lon + lon_delta
                ):
                    continue

                # Calculate precise distance
                distance = haversine_distance(lat, lon, stop_lat, stop_lon)

                # Filter by radius
                if distance <= radius:
                    if stop_name not in stops_by_name:
                        # First stop with this name
                        stops_by_name[stop_name] = {
                            "stop_id": stop["stop_id"],
                            "stop_ids": [stop["stop_id"]],
                            "stop_name": stop_name,
                            "stop_desc": stop.get("stop_desc", ""),
                            "stop_lat": stop_lat,
                            "stop_lon": stop_lon,
                            "distance_meters": round(distance, 1),
                        }
                    else:
                        # Add stop_id to the list
                        if stop["stop_id"] not in stops_by_name[stop_name]["stop_ids"]:
                            stops_by_name[stop_name]["stop_ids"].append(stop["stop_id"])

                        # Update if this stop is closer
                        if distance < stops_by_name[stop_name]["distance_meters"]:
                            stops_by_name[stop_name]["stop_id"] = stop["stop_id"]
                            stops_by_name[stop_name]["stop_desc"] = stop.get(
                                "stop_desc", ""
                            )
                            stops_by_name[stop_name]["stop_lat"] = stop_lat
                            stops_by_name[stop_name]["stop_lon"] = stop_lon
                            stops_by_name[stop_name]["distance_meters"] = round(
                                distance, 1
                            )

        # Convert to list of NearbyStopInfo
        nearby_stops = [NearbyStopInfo(**data) for data in stops_by_name.values()]

        # Sort by distance (nearest first)
        nearby_stops.sort(key=lambda x: x.distance_meters)

        # Apply limit
        nearby_stops = nearby_stops[:limit]

        response = NearbyStopsResponse(
            success=True,
            query={"lat": lat, "lon": lon, "radius": radius, "limit": limit},
            count=len(nearby_stops),
            stops=nearby_stops,
        )

        logger.info(f"Found {len(nearby_stops)} nearby stops")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in nearby stops: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred",
        )


@app.get(
    "/kcb_api/trip/{trip_id}/location",
    response_model=TripLocationResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized - Invalid API Key"},
        404: {"model": ErrorResponse, "description": "Trip not found"},
    },
)
async def get_trip_location(
    trip_id: str,
    time: Optional[str] = None,
    departure_stop_id: Optional[str] = None,
    api_key: str = Depends(verify_api_key),
):
    """
    バスの推定位置を取得（時刻表ベース）

    - **trip_id**: 便ID（検索結果から取得）
    - **time**: 確認したい時刻（HH:MM形式、省略時は現在時刻）
    - **departure_stop_id**: ユーザーの乗車予定バス停ID（指定すると前3つの停留所情報も返す）

    注意: ダイヤ通りに運行している前提での推定です。実際の位置とは異なる場合があります。
    """
    try:
        # 時刻の設定とバリデーション
        if time is None:
            query_time = datetime.now().strftime("%H:%M:00")
        else:
            # 時刻フォーマットのバリデーション
            if not re.match(r"^[0-9]{1,2}:[0-5][0-9](:[0-5][0-9])?$", time):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="time must be in HH:MM or HH:MM:SS format (e.g., '9:30' or '09:30:00')",
                )

            # 時間の範囲チェック（GTFS対応で30時まで許可）
            try:
                hours = int(time.split(":")[0])
                if hours > 30:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="hour must be between 0 and 30 for GTFS compatibility",
                    )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid time format",
                )

            # 時刻を「HH:MM:SS」形式に正規化（単一桁時間対応）
            if ":" in time:
                parts = time.split(":")
                if len(parts) == 2:  # "H:MM" or "HH:MM"
                    hour = parts[0].zfill(2)
                    minute = parts[1]
                    query_time = f"{hour}:{minute}:00"
                elif len(parts) == 3:  # "H:MM:SS" or "HH:MM:SS"
                    hour = parts[0].zfill(2)
                    minute = parts[1]
                    second = parts[2]
                    query_time = f"{hour}:{minute}:{second}"
                else:
                    query_time = time
            else:
                query_time = time

        logger.info(f"Trip location request: trip_id={trip_id}, time={query_time}")

        # Load GTFS data
        loader = GTFSDataLoader.get_instance(settings.get_gtfs_dir())
        trip_to_stops, _ = loader.load_stop_times()
        trips_data = loader.load_trips()
        stops_data = loader.load_stops()
        routes_data = loader.load_routes()

        # Check if trip exists
        if trip_id not in trip_to_stops:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trip ID '{trip_id}' not found",
            )

        stops = trip_to_stops[trip_id]
        trip_info = trips_data.get(trip_id, {})

        # Helper function to get stop name
        def get_stop_name(stop_id):
            for name, stop_list in stops_data.items():
                if any(s["stop_id"] == stop_id for s in stop_list):
                    return name
            return stop_id

        # 乗車予定バス停の前3つの停留所を取得（departure_stop_id指定時）
        previous_stops_list = None
        boarding_stop_info = None

        if departure_stop_id:
            # 乗車予定バス停のインデックスを探す
            boarding_index = None
            for idx, stop in enumerate(stops):
                if stop["stop_id"] == departure_stop_id:
                    boarding_index = idx
                    boarding_stop_info = StopLocation(
                        stop_id=stop["stop_id"],
                        stop_name=get_stop_name(stop["stop_id"]),
                        time=stop["departure_time"],
                    )
                    break

            # 前3つの停留所を取得
            if boarding_index is not None and boarding_index > 0:
                previous_stops_list = []
                start_idx = max(0, boarding_index - 3)
                for idx in range(start_idx, boarding_index):
                    prev_stop = stops[idx]
                    previous_stops_list.append(
                        StopLocation(
                            stop_id=prev_stop["stop_id"],
                            stop_name=get_stop_name(prev_stop["stop_id"]),
                            time=prev_stop["departure_time"],
                        )
                    )

        # Estimate current location
        for i, stop in enumerate(stops):
            departure_time = stop["departure_time"]

            # Still before this stop
            if query_time < departure_time:
                # Not started yet (before first stop)
                if i == 0:
                    return TripLocationResponse(
                        success=True,
                        trip_id=trip_id,
                        query_time=query_time,
                        status="not_started",
                        message=f"まだ始発していません（始発: {departure_time}）",
                        to_stop=StopLocation(
                            stop_id=stop["stop_id"],
                            stop_name=get_stop_name(stop["stop_id"]),
                            time=departure_time,
                        ),
                        previous_stops=previous_stops_list,
                        boarding_stop=boarding_stop_info,
                    )

                # Between previous stop and this stop
                prev_stop = stops[i - 1]

                # Calculate estimated arrival time in minutes
                try:
                    query_minutes = parse_gtfs_time(query_time)
                    arrival_minutes = parse_gtfs_time(stop["arrival_time"])
                    diff = arrival_minutes - query_minutes
                    estimated_minutes = int(diff) if diff > 0 else 0
                except:
                    estimated_minutes = None

                return TripLocationResponse(
                    success=True,
                    trip_id=trip_id,
                    query_time=query_time,
                    status="between_stops",
                    message=f"{get_stop_name(prev_stop['stop_id'])}を出発 → {get_stop_name(stop['stop_id'])}に向かっています",
                    from_stop=StopLocation(
                        stop_id=prev_stop["stop_id"],
                        stop_name=get_stop_name(prev_stop["stop_id"]),
                        time=prev_stop["departure_time"],
                    ),
                    to_stop=StopLocation(
                        stop_id=stop["stop_id"],
                        stop_name=get_stop_name(stop["stop_id"]),
                        time=stop["arrival_time"],
                    ),
                    estimated_arrival_minutes=estimated_minutes,
                    previous_stops=previous_stops_list,
                    boarding_stop=boarding_stop_info,
                )

        # Arrived at final destination
        last_stop = stops[-1]
        return TripLocationResponse(
            success=True,
            trip_id=trip_id,
            query_time=query_time,
            status="arrived",
            message=f"終点に到着済み（{get_stop_name(last_stop['stop_id'])} {last_stop['departure_time']}）",
            from_stop=StopLocation(
                stop_id=last_stop["stop_id"],
                stop_name=get_stop_name(last_stop["stop_id"]),
                time=last_stop["departure_time"],
            ),
            previous_stops=previous_stops_list,
            boarding_stop=boarding_stop_info,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in trip location: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred",
        )


@app.post(
    "/kcb_api/search",
    response_model=SearchResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized - Invalid API Key"},
        400: {
            "model": ErrorResponse,
            "description": "Bad Request - Invalid parameters",
        },
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
async def search_routes(request: SearchRequest, api_key: str = Depends(verify_api_key)):
    """
    京都市バスの経路を検索

    - **from_stop**: 出発停留所名（例: "堀川下長者町"）
    - **to_stop**: 到着停留所名（例: "京都駅前"）
    - **current_time**: 出発時刻（HH:MM形式、省略時は現在時刻）
    - **day_type**: 運行日タイプ（weekday/saturday/sunday）。dateが指定された場合は無視されます。
    - **date**: 検索日（YYYY-MM-DD形式）。祝日・特別ダイヤを考慮します。
    - **limit**: 最大結果件数（1-10、デフォルト3）
    """
    try:
        logger.info(
            f"Search request: {request.from_stop} -> {request.to_stop}, date={request.date}"
        )

        # Call search function with date support
        results = search_bus(
            from_stop_name=request.from_stop,
            to_stop_name=request.to_stop,
            current_time=request.current_time,
            day_type=request.day_type,
            date=request.date,
        )

        # Apply limit
        limited_results = results[: request.limit]

        # Convert to response model
        routes = [BusRoute(**route) for route in limited_results]

        response = SearchResponse(
            success=True,
            query={
                "from_stop": request.from_stop,
                "to_stop": request.to_stop,
                "current_time": request.current_time or "現在時刻",
                "day_type": request.day_type,
                "date": request.date,
                "limit": request.limit,
            },
            count=len(routes),
            routes=routes,
        )

        logger.info(f"Found {len(routes)} routes")
        return response

    except ValueError as e:
        # Handle search errors (e.g., stop not found)
        logger.warning(f"Search error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred",
        )


@app.post(
    "/kcb_api/search/transfer",
    response_model=TransferSearchResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized - Invalid API Key"},
        400: {
            "model": ErrorResponse,
            "description": "Bad Request - Invalid parameters",
        },
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
async def search_transfer_routes(
    request: TransferSearchRequest, api_key: str = Depends(verify_api_key)
):
    """
    乗り換え経路を検索

    直通便がない場合に、1回乗り換えで目的地に到達できる経路を検索します。

    - **from_stop**: 出発停留所名（例: 京都駅前）
    - **to_stop**: 到着停留所名（例: 銀閣寺道）
    - **current_time**: 出発時刻（HH:MM形式）
    - **day_type**: 運行日タイプ（dateが指定された場合は無視）
    - **date**: 検索日（祝日・特別ダイヤを考慮）
    - **min_transfer_time**: 最小乗り換え時間（デフォルト5分）
    - **limit**: 最大結果件数（デフォルト5件）
    """
    try:
        logger.info(
            f"Transfer search request: {request.from_stop} -> {request.to_stop}"
        )

        results = find_transfer_routes(
            from_stop_name=request.from_stop,
            to_stop_name=request.to_stop,
            current_time=request.current_time,
            day_type=request.day_type,
            date=request.date,
            min_transfer_time=request.min_transfer_time,
            limit=request.limit,
        )

        # Convert to response model
        routes = [TransferRoute(**route) for route in results]

        response = TransferSearchResponse(
            success=True,
            query={
                "from_stop": request.from_stop,
                "to_stop": request.to_stop,
                "current_time": request.current_time or "現在時刻",
                "day_type": request.day_type,
                "date": request.date,
                "min_transfer_time": request.min_transfer_time,
                "limit": request.limit,
            },
            count=len(routes),
            routes=routes,
        )

        logger.info(f"Found {len(routes)} transfer routes")
        return response

    except ValueError as e:
        logger.warning(f"Transfer search error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except Exception as e:
        logger.error(f"Unexpected error in transfer search: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred",
        )


# ============================================================
# Exception Handlers
# ============================================================


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail, "status_code": exc.status_code},
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
            "detail": str(exc) if settings.LOG_LEVEL == "debug" else None,
        },
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
        log_level=settings.LOG_LEVEL,
    )
