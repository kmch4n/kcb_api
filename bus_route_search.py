import csv
from collections import defaultdict
import os
from datetime import datetime
from typing import Optional


class GTFSDataLoader:
    """GTFSデータの効率的なロードとキャッシュ管理"""

    _instance = None

    def __init__(self, gtfs_dir: str):
        self.gtfs_dir = gtfs_dir
        self._stops_cache = None
        self._routes_cache = None
        self._trips_cache = None
        self._stop_times_cache = None
        self._calendar_cache = None
        self._calendar_dates_cache = None
        self._fare_attributes_cache = None
        self._fare_rules_cache = None

    @classmethod
    def get_instance(cls, gtfs_dir: str = None):
        """シングルトンパターンでインスタンスを取得"""
        if cls._instance is None:
            if gtfs_dir is None:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                gtfs_dir = os.path.join(script_dir, "data")
            cls._instance = cls(gtfs_dir)
        return cls._instance

    def load_stops(self) -> dict:
        """
        stops.txtを読み込み、stop_name → stop情報のマッピングを返す

        Returns:
            {
                "京都駅前": [
                    {"stop_id": "061211", "stop_desc": "京都駅前(A1)", ...},
                    ...
                ]
            }
        """
        if self._stops_cache is not None:
            return self._stops_cache

        stops_file = os.path.join(self.gtfs_dir, "stops.txt")
        stop_name_to_stops = defaultdict(list)

        with open(stops_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                stop_name_to_stops[row["stop_name"]].append(
                    {
                        "stop_id": row["stop_id"],
                        "stop_name": row["stop_name"],
                        "stop_desc": row["stop_desc"],
                        "stop_lat": row["stop_lat"],
                        "stop_lon": row["stop_lon"],
                    }
                )

        self._stops_cache = dict(stop_name_to_stops)
        return self._stops_cache

    def load_routes(self) -> dict:
        """
        routes.txtを読み込み、route_id → route_nameのマッピングを返す

        Returns:
            {"00100": "市バス１", ...}
        """
        if self._routes_cache is not None:
            return self._routes_cache

        routes_file = os.path.join(self.gtfs_dir, "routes.txt")
        routes = {}

        with open(routes_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                routes[row["route_id"]] = row["route_short_name"]

        self._routes_cache = routes
        return self._routes_cache

    def load_trips(self) -> dict:
        """
        trips.txtを読み込み、trip_id → trip情報のマッピングを返す

        Returns:
            {
                "00100_01001_3650": {
                    "route_id": "00100",
                    "service_id": "01001",
                    "headsign": "..."
                }
            }
        """
        if self._trips_cache is not None:
            return self._trips_cache

        trips_file = os.path.join(self.gtfs_dir, "trips.txt")
        trips = {}

        with open(trips_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                trips[row["trip_id"]] = {
                    "route_id": row["route_id"],
                    "service_id": row["service_id"],
                    "headsign": row["trip_headsign"],
                }

        self._trips_cache = trips
        return self._trips_cache

    def load_stop_times(self) -> tuple[dict, dict]:
        """
        stop_times.txtを読み込み、インデックスを構築

        Returns:
            (trip_to_stops, stop_to_trips)
            - trip_to_stops: trip_id → 停車駅リスト（順序付き）
            - stop_to_trips: stop_id → trip_idセット
        """
        if self._stop_times_cache is not None:
            return self._stop_times_cache

        stop_times_file = os.path.join(self.gtfs_dir, "stop_times.txt")

        trip_to_stops = defaultdict(list)
        stop_to_trips = defaultdict(set)

        print("stop_times.txtを読み込み中...")
        count = 0

        with open(stop_times_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                count += 1
                if count % 100000 == 0:
                    print(f"  処理中: {count}行...")

                trip_id = row["trip_id"]
                stop_id = row["stop_id"]

                trip_to_stops[trip_id].append(
                    {
                        "stop_id": stop_id,
                        "stop_sequence": int(row["stop_sequence"]),
                        "arrival_time": row["arrival_time"],
                        "departure_time": row["departure_time"],
                    }
                )

                stop_to_trips[stop_id].add(trip_id)

        # 各tripの停車駅をstop_sequenceでソート
        for trip_id in trip_to_stops:
            trip_to_stops[trip_id].sort(key=lambda x: x["stop_sequence"])

        print(f"  完了: {count}行を読み込みました")

        self._stop_times_cache = (dict(trip_to_stops), dict(stop_to_trips))
        return self._stop_times_cache

    def load_calendar(self) -> dict:
        """
        calendar.txtを読み込み

        Returns:
            {
                "01001": {"monday": "1", "tuesday": "1", ...},
                ...
            }
        """
        if self._calendar_cache is not None:
            return self._calendar_cache

        calendar_file = os.path.join(self.gtfs_dir, "calendar.txt")
        calendar = {}

        with open(calendar_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                calendar[row["service_id"]] = row

        self._calendar_cache = calendar
        return self._calendar_cache

    def load_fares(self) -> dict:
        """
        fare_attributes.txtとfare_rules.txtを読み込み、route_id → fare情報のマッピングを返す

        Returns:
            {
                "00100": {"fare_id": "F_230", "price": 230, "currency": "JPY"},
                ...
            }
        """
        if (
            self._fare_attributes_cache is not None
            and self._fare_rules_cache is not None
        ):
            return self._fare_rules_cache

        # 1. fare_attributes.txtを読み込み（fare_id → price）
        fare_attributes_file = os.path.join(self.gtfs_dir, "fare_attributes.txt")
        fare_attributes = {}

        with open(fare_attributes_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                fare_attributes[row["fare_id"]] = {
                    "fare_id": row["fare_id"],
                    "price": int(row["price"]),
                    "currency": row["currency_type"],
                }

        self._fare_attributes_cache = fare_attributes

        # 2. fare_rules.txtを読み込み（route_id → fare_id）
        fare_rules_file = os.path.join(self.gtfs_dir, "fare_rules.txt")
        route_to_fare = {}

        with open(fare_rules_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                route_id = row["route_id"]
                fare_id = row["fare_id"]
                if route_id not in route_to_fare and fare_id in fare_attributes:
                    route_to_fare[route_id] = fare_attributes[fare_id]

        self._fare_rules_cache = route_to_fare
        return self._fare_rules_cache

    def load_calendar_dates(self) -> dict:
        """
        calendar_dates.txtを読み込み、(service_id, date) → exception_type のマッピングを返す

        exception_type:
            1 = サービス追加（通常運休日だが運行）
            2 = サービス削除（通常運行日だが運休）

        Returns:
            {
                ("01001", "20260112"): 2,  # 成人の日は運休
                ("02001", "20260112"): 1,  # 成人の日は運行
                ...
            }
        """
        if self._calendar_dates_cache is not None:
            return self._calendar_dates_cache

        calendar_dates_file = os.path.join(self.gtfs_dir, "calendar_dates.txt")
        calendar_dates = {}

        if os.path.exists(calendar_dates_file):
            with open(calendar_dates_file, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    service_id = row["service_id"]
                    date = row["date"]
                    exception_type = int(row["exception_type"])
                    calendar_dates[(service_id, date)] = exception_type

        self._calendar_dates_cache = calendar_dates
        return self._calendar_dates_cache


def parse_gtfs_time(time_str: str) -> int:
    """
    GTFS時刻文字列（HH:MM:SS）を分単位に変換

    Args:
        time_str: GTFS時刻文字列（例: "14:30:00" or "25:30:00"）

    Returns:
        深夜0時からの経過分数
    """
    h, m, s = map(int, time_str.split(":"))
    return h * 60 + m


def calculate_travel_time(departure_time: str, arrival_time: str) -> int:
    """
    所要時間を分単位で計算

    Args:
        departure_time: "HH:MM:SS"形式（24時以降も可、例: "25:30:00"）
        arrival_time: "HH:MM:SS"形式

    Returns:
        所要時間（分）
    """
    dep_minutes = parse_gtfs_time(departure_time)
    arr_minutes = parse_gtfs_time(arrival_time)
    return arr_minutes - dep_minutes


def determine_service_ids(
    day_type: str = None, 
    date: str = None,
    loader: GTFSDataLoader = None
) -> set[str]:
    """
    運行日タイプまたは日付から有効なservice_idセットを返す
    
    dateが指定された場合は、calendar.txtとcalendar_dates.txtを組み合わせて
    祝日・特別ダイヤを考慮した正確なサービスIDを返す。

    Args:
        day_type: 'weekday', 'saturday', 'sunday' (dateが未指定の場合に使用)
        date: 検索日（YYYYMMDD形式、例: '20260112'）指定時は祝日等を考慮
        loader: GTFSDataLoaderインスタンス（Noneの場合は新規取得）

    Returns:
        有効なservice_idのセット
    """
    if loader is None:
        loader = GTFSDataLoader.get_instance()

    calendar_data = loader.load_calendar()
    calendar_dates = loader.load_calendar_dates()
    
    # dateが指定された場合：日付ベースでサービスIDを決定
    if date is not None:
        # 日付から曜日を取得
        try:
            date_obj = datetime.strptime(date, "%Y%m%d")
        except ValueError:
            # YYYY-MM-DD形式もサポート
            date_obj = datetime.strptime(date.replace("-", ""), "%Y%m%d")
            date = date.replace("-", "")  # YYYYMMDD形式に正規化
        
        weekday_index = date_obj.weekday()  # 0=月曜, 6=日曜
        weekday_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        weekday_name = weekday_names[weekday_index]
        
        service_ids = set()
        
        # 1. まず通常のカレンダーで該当曜日に運行するサービスを取得
        for service_id, calendar_entry in calendar_data.items():
            # 日付が有効期間内かチェック
            start_date = calendar_entry.get("start_date", "")
            end_date = calendar_entry.get("end_date", "")
            if start_date and end_date:
                if not (start_date <= date <= end_date):
                    continue
            
            # 該当曜日に運行しているか
            if calendar_entry.get(weekday_name, "0") == "1":
                service_ids.add(service_id)
        
        # 2. calendar_datesで例外を適用
        for (svc_id, exc_date), exc_type in calendar_dates.items():
            if exc_date == date:
                if exc_type == 2:  # サービス削除（運休）
                    service_ids.discard(svc_id)
                elif exc_type == 1:  # サービス追加（臨時運行）
                    service_ids.add(svc_id)
        
        return service_ids
    
    # dateが未指定の場合：従来のday_typeベースの処理
    service_ids = set()

    # day_typeに応じた曜日フィールドを決定
    if day_type == "weekday":
        # 平日: 月-金のいずれかで運行するサービスをすべて含める
        weekday_fields = ["monday", "tuesday", "wednesday", "thursday", "friday"]
        for service_id, calendar_entry in calendar_data.items():
            if any(calendar_entry.get(day, "0") == "1" for day in weekday_fields):
                service_ids.add(service_id)
    elif day_type == "saturday":
        # 土曜日運行のサービス
        for service_id, calendar_entry in calendar_data.items():
            if calendar_entry.get("saturday", "0") == "1":
                service_ids.add(service_id)
    elif day_type == "sunday":
        # 日曜日運行のサービス
        for service_id, calendar_entry in calendar_data.items():
            if calendar_entry.get("sunday", "0") == "1":
                service_ids.add(service_id)

    return service_ids if service_ids else set()


def find_direct_routes(
    from_stop_ids: list[str],
    to_stop_ids: list[str],
    service_ids: set[str],
    current_time: str,
    loader: GTFSDataLoader,
) -> list[dict]:
    """
    直通便を検索するコアロジック

    Args:
        from_stop_ids: 出発停留所IDリスト
        to_stop_ids: 到着停留所IDリスト
        service_ids: 有効なservice_idセット
        current_time: 現在時刻（"HH:MM:SS"形式）
        loader: GTFSDataLoaderインスタンス

    Returns:
        候補便のリスト
    """
    trip_to_stops, stop_to_trips = loader.load_stop_times()
    trips_data = loader.load_trips()

    # 出発停留所を通過する便
    from_trips = set()
    for stop_id in from_stop_ids:
        from_trips.update(stop_to_trips.get(stop_id, set()))

    # 到着停留所を通過する便
    to_trips = set()
    for stop_id in to_stop_ids:
        to_trips.update(stop_to_trips.get(stop_id, set()))

    # 両方を通過する便
    candidate_trips = from_trips & to_trips

    results = []

    for trip_id in candidate_trips:
        # service_idチェック
        trip_info = trips_data.get(trip_id)
        if not trip_info or trip_info["service_id"] not in service_ids:
            continue

        stops = trip_to_stops[trip_id]

        # 出発停留所と到着停留所を見つける
        from_stop = None
        to_stop = None

        for stop in stops:
            if stop["stop_id"] in from_stop_ids and from_stop is None:
                from_stop = stop
            if stop["stop_id"] in to_stop_ids and to_stop is None:
                to_stop = stop

        # 両方見つかり、順序が正しいかチェック
        if (
            from_stop
            and to_stop
            and from_stop["stop_sequence"] < to_stop["stop_sequence"]
        ):
            # 現在時刻以降の便のみ
            if from_stop["departure_time"] >= current_time:
                results.append(
                    {
                        "trip_id": trip_id,
                        "from_stop_id": from_stop["stop_id"],
                        "from_departure": from_stop["departure_time"],
                        "from_stop_sequence": from_stop["stop_sequence"],
                        "to_stop_id": to_stop["stop_id"],
                        "to_arrival": to_stop["arrival_time"],
                        "to_stop_sequence": to_stop["stop_sequence"],
                    }
                )

    return results


def search_similar_stop_names(
    query: str, stops_data: dict, limit: int = 5
) -> list[str]:
    """
    類似の停留所名を検索

    Args:
        query: 検索クエリ
        stops_data: 停留所データ
        limit: 返す最大数

    Returns:
        類似停留所名のリスト
    """
    # 部分一致検索
    matches = [name for name in stops_data.keys() if query in name]
    return matches[:limit]


def search_bus(
    from_stop_name: str,
    to_stop_name: str,
    current_time: Optional[str] = None,
    day_type: str = "weekday",
    date: Optional[str] = None,
) -> list[dict]:
    """
    京都市バスの経路を検索する（直通のみ）

    Args:
        from_stop_name: 出発停留所名（例: "堀川下長者町"）
        to_stop_name: 到着停留所名（例: "京都駅前"）
        current_time: 出発時刻（HH:MM形式、例: "14:30"）省略時は現在時刻
        day_type: 'weekday', 'saturday', 'sunday' (dateが未指定の場合に使用)
        date: 検索日（YYYY-MM-DD形式、例: "2026-01-12"）祝日・特別ダイヤを考慮

    Returns:
        最大3件の検索結果（到着時刻が早い順）
        各要素の構造:
        {
            'route_name': str,              # 路線名（例: "市バス９"）
            'route_id': str,                # 路線ID
            'trip_id': str,                 # 便ID
            'headsign': str,                # 行き先表示
            'departure_time': str,          # 出発時刻
            'departure_stop_desc': str,     # 出発停留所詳細（プラットフォーム）
            'arrival_time': str,            # 到着時刻
            'arrival_stop_desc': str,       # 到着停留所詳細
            'travel_time_minutes': int      # 所要時間（分）
        }

    Raises:
        ValueError: 停留所名が見つからない場合
    """
    # 1. データローダー初期化
    loader = GTFSDataLoader.get_instance()

    # 2. 停留所IDの解決
    stops_data = loader.load_stops()
    from_stops = stops_data.get(from_stop_name, [])
    to_stops = stops_data.get(to_stop_name, [])

    if not from_stops:
        suggestions = search_similar_stop_names(from_stop_name, stops_data)
        raise ValueError(
            f"停留所 '{from_stop_name}' が見つかりません。\n"
            f"類似の停留所: {', '.join(suggestions) if suggestions else 'なし'}"
        )

    if not to_stops:
        suggestions = search_similar_stop_names(to_stop_name, stops_data)
        raise ValueError(
            f"停留所 '{to_stop_name}' が見つかりません。\n"
            f"類似の停留所: {', '.join(suggestions) if suggestions else 'なし'}"
        )

    # 3. 現在時刻の設定
    if current_time is None:
        now = datetime.now()
        current_time = now.strftime("%H:%M")

    # current_timeを"HH:MM:SS"形式に変換（単一桁時間対応）
    if ":" in current_time:
        parts = current_time.split(":")
        if len(parts) == 2:  # "H:MM" or "HH:MM"
            hour = parts[0].zfill(2)  # 左側を0埋め
            minute = parts[1]
            current_time = f"{hour}:{minute}:00"
        elif len(parts) == 3:  # "H:MM:SS" or "HH:MM:SS"
            hour = parts[0].zfill(2)
            minute = parts[1]
            second = parts[2]
            current_time = f"{hour}:{minute}:{second}"

    # 4. 運行日パターンの決定（date優先、なければday_type使用）
    service_ids = determine_service_ids(day_type=day_type, date=date)

    # 5. 直通便の検索
    routes_data = loader.load_routes()
    trips_data = loader.load_trips()
    fares_data = loader.load_fares()

    from_stop_ids = [s["stop_id"] for s in from_stops]
    to_stop_ids = [s["stop_id"] for s in to_stops]

    results = find_direct_routes(
        from_stop_ids=from_stop_ids,
        to_stop_ids=to_stop_ids,
        service_ids=service_ids,
        current_time=current_time,
        loader=loader,
    )

    # 6. 結果の整形
    formatted_results = []

    for result in results:
        trip_info = trips_data[result["trip_id"]]
        route_name = routes_data.get(trip_info["route_id"], trip_info["route_id"])

        # stop_descの取得
        from_stop_desc = next(
            s["stop_desc"] for s in from_stops if s["stop_id"] == result["from_stop_id"]
        )
        to_stop_desc = next(
            s["stop_desc"] for s in to_stops if s["stop_id"] == result["to_stop_id"]
        )

        # 停車駅数を計算（出発地と目的地を含む）
        stops_count = result["to_stop_sequence"] - result["from_stop_sequence"] + 1

        # 運賃情報を取得
        fare_info = fares_data.get(trip_info["route_id"])
        fare = fare_info["price"] if fare_info else None

        formatted_results.append(
            {
                "route_name": route_name,
                "route_id": trip_info["route_id"],
                "trip_id": result["trip_id"],
                "headsign": trip_info["headsign"],
                "departure_time": result["from_departure"],
                "departure_stop_id": result["from_stop_id"],
                "departure_stop_desc": from_stop_desc,
                "arrival_time": result["to_arrival"],
                "arrival_stop_id": result["to_stop_id"],
                "arrival_stop_desc": to_stop_desc,
                "travel_time_minutes": calculate_travel_time(
                    result["from_departure"], result["to_arrival"]
                ),
                "stops_count": stops_count,
                "fare": fare,
                "service_id": trip_info["service_id"],
            }
        )

    # 7. 出発時刻でソート（limitは呼び出し側で適用）
    formatted_results.sort(key=lambda x: x["departure_time"])
    return formatted_results


if __name__ == "__main__":
    # 使用例
    print("京都市バス経路検索")
    print("=" * 80)

    try:
        results = search_bus(
            from_stop_name="堀川下長者町",
            to_stop_name="京都駅前",
            current_time="11:49",
            day_type="weekday",
        )

        if results:
            for i, route in enumerate(results, 1):
                print(f"\n{i}. {route['route_name']} ({route['headsign']})")
                print(
                    f"   出発: {route['departure_time']} - {route['departure_stop_desc']}"
                )
                print(
                    f"   到着: {route['arrival_time']} - {route['arrival_stop_desc']}"
                )
                print(f"   所要時間: {route['travel_time_minutes']}分")
        else:
            print("\n該当する便が見つかりませんでした。")

    except ValueError as e:
        print(f"\nエラー: {e}")
