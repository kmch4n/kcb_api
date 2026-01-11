#!/usr/bin/env python3
"""
京都市バス GTFS データ自動更新ツール

このスクリプトは以下の処理を自動化します：
1. 最新のGTFSデータをダウンロード
2. data/直下に解凍
3. 時刻表を再生成（JSON形式のみ）
4. 統計情報をdetail.txtに記録
"""

import csv
import json
import os
import re
import shutil
import sys
import zipfile
import urllib.request
import urllib.parse
import urllib.error
import argparse
from collections import defaultdict
from datetime import datetime


def load_env_file(env_path: str) -> dict:
    """
    .envファイルを標準ライブラリでパース

    Args:
        env_path: .envファイルのパス

    Returns:
        環境変数の辞書

    Raises:
        FileNotFoundError: .envファイルが存在しない
    """
    env_vars = {}

    if not os.path.exists(env_path):
        raise FileNotFoundError(f".envファイルが見つかりません: {env_path}")

    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            # コメント行と空行をスキップ
            if not line or line.startswith('#'):
                continue

            # KEY = VALUE 形式をパース
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()

                # クォート除去（"value" or 'value'）
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                env_vars[key] = value

    return env_vars


def fetch_latest_date_from_web() -> str:
    """
    公共交通オープンデータのページから最新のGTFS公開日を自動取得

    Returns:
        YYYYMMDD形式の日付文字列

    Raises:
        Exception: ページ取得または日付抽出に失敗
    """
    ckan_url = "https://ckan.odpt.org/dataset/kyoto_municipal_transportation_kyoto_city_bus_gtfs/resource/d9ce405a-139d-48f1-89bd-58129f6ff93c"

    print(f"  公共交通オープンデータから最新日付を取得中...")
    print(f"  URL: {ckan_url}")

    try:
        with urllib.request.urlopen(ckan_url, timeout=30) as response:
            html = response.read().decode('utf-8')

        # date=YYYYMMDD パターンを検索
        pattern = r'date=(\d{8})'
        matches = re.findall(pattern, html)

        if not matches:
            raise ValueError("ページから日付を抽出できませんでした")

        # 最新の日付を取得（複数ある場合は最大値）
        latest_date = max(matches)

        print(f"  ✓ 最新の公開日: {latest_date}")
        return latest_date

    except urllib.error.URLError as e:
        raise Exception(f"ページの取得に失敗しました: {e}")
    except Exception as e:
        raise Exception(f"最新日付の取得に失敗しました: {e}")


def get_update_date(use_latest: bool = False) -> str:
    """
    ユーザーからdate引数を取得（対話式）

    Args:
        use_latest: Trueの場合、Webから最新日付を自動取得

    Returns:
        YYYYMMDD形式の日付文字列
    """
    if use_latest:
        try:
            return fetch_latest_date_from_web()
        except Exception as e:
            print(f"  警告: {e}")
            print(f"  手動入力に切り替えます...")
            print()

    today = datetime.now().strftime("%Y%m%d")
    print(f"GTFSデータの取得日を指定してください")
    print(f"デフォルト: {today} (今日)")
    print(f"形式: YYYYMMDD (例: 20260111)")
    print()

    user_input = input("日付 [Enter=今日]: ").strip()

    if not user_input:
        return today

    # 簡易バリデーション
    if len(user_input) != 8 or not user_input.isdigit():
        print(f"警告: 無効な日付形式です。{today}を使用します。")
        return today

    return user_input


def download_gtfs_zip(url: str, api_key: str, date_param: str, output_path: str) -> None:
    """
    GTFSデータをダウンロード

    Args:
        url: ベースURL
        api_key: APIキー
        date_param: 日付パラメータ (YYYYMMDD)
        output_path: 保存先zipファイルパス

    Raises:
        urllib.error.URLError: ダウンロード失敗
    """
    # URLにクエリパラメータを追加
    params = {
        'acl:consumerKey': api_key,
        'date': date_param
    }

    query_string = urllib.parse.urlencode(params)
    full_url = f"{url}?{query_string}"

    print(f"  GTFSデータをダウンロード中...")
    print(f"  URL: {url}")
    print(f"  日付: {date_param}")

    try:
        with urllib.request.urlopen(full_url, timeout=300) as response:
            # レスポンスコードチェック
            if response.status != 200:
                raise ValueError(f"HTTPエラー: {response.status}")

            # ファイルサイズ取得（進捗表示用）
            total_size = int(response.headers.get('Content-Length', 0))

            # チャンクでダウンロード
            chunk_size = 8192
            downloaded = 0

            with open(output_path, 'wb') as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break

                    f.write(chunk)
                    downloaded += len(chunk)

                    # 進捗表示
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\r  進捗: {percent:.1f}% ({downloaded:,}/{total_size:,} bytes)", end='')

            print(f"\n  ✓ ダウンロード完了: {output_path}")

    except urllib.error.URLError as e:
        raise urllib.error.URLError(f"ダウンロード失敗: {e}")


def extract_zip_to_data(zip_path: str, data_dir: str) -> None:
    """
    zipファイルを直接data/直下に解凍

    Args:
        zip_path: zipファイルのパス
        data_dir: 解凍先ディレクトリ (data/)

    Raises:
        zipfile.BadZipFile: zipファイルが破損
    """
    print(f"  zipファイルを解凍中: {zip_path}")

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # zip内のファイル一覧を取得
            file_list = zip_ref.namelist()

            print(f"  ファイル数: {len(file_list)}")

            # 全ファイルをdata/直下に解凍
            for file_name in file_list:
                # ディレクトリ構造を無視してファイル名のみ取得（パストラバーサル対策）
                base_name = os.path.basename(file_name)

                # 空のディレクトリエントリをスキップ
                if not base_name:
                    continue

                # ファイルを読み込み
                file_data = zip_ref.read(file_name)

                # data/直下に書き込み
                output_path = os.path.join(data_dir, base_name)
                with open(output_path, 'wb') as f:
                    f.write(file_data)

                print(f"    ✓ {base_name}")

            print(f"  ✓ 解凍完了: {data_dir}")

    except zipfile.BadZipFile:
        raise zipfile.BadZipFile(f"zipファイルが破損しています: {zip_path}")


def backup_existing_data(data_dir: str, backup_dir: str) -> None:
    """
    既存のGTFSファイルをバックアップ

    Args:
        data_dir: dataディレクトリ
        backup_dir: バックアップ先ディレクトリ
    """
    # 既存のバックアップを削除
    if os.path.exists(backup_dir):
        shutil.rmtree(backup_dir)

    # バックアップディレクトリ作成
    os.makedirs(backup_dir, exist_ok=True)

    # GTFSファイル一覧（拡張子で判定）
    gtfs_extensions = ['.txt', '.zip']

    backed_up_count = 0
    for file_name in os.listdir(data_dir):
        file_path = os.path.join(data_dir, file_name)

        # ファイルのみ対象
        if not os.path.isfile(file_path):
            continue

        # GTFS関連ファイルのみバックアップ
        if any(file_name.endswith(ext) for ext in gtfs_extensions):
            backup_path = os.path.join(backup_dir, file_name)
            shutil.copy2(file_path, backup_path)
            backed_up_count += 1

    print(f"  ✓ バックアップ完了: {backed_up_count}ファイル → {backup_dir}")


def cleanup_old_gtfs_files(data_dir: str) -> None:
    """
    data/内の古いGTFSファイルを削除

    Args:
        data_dir: dataディレクトリ
    """
    gtfs_files = [
        'agency.txt', 'calendar_dates.txt', 'calendar.txt',
        'fare_attributes.txt', 'fare_rules.txt', 'feed_info.txt',
        'frequencies.txt', 'routes.txt', 'shapes.txt', 'stops.txt',
        'stop_times.txt', 'transfers.txt', 'translations.txt', 'trips.txt'
    ]

    deleted_count = 0
    for file_name in gtfs_files:
        file_path = os.path.join(data_dir, file_name)
        if os.path.exists(file_path):
            os.remove(file_path)
            deleted_count += 1

    print(f"  ✓ 古いGTFSファイル削除: {deleted_count}ファイル")


def restore_from_backup(backup_dir: str, data_dir: str) -> None:
    """
    バックアップから復元（エラー時のロールバック）

    Args:
        backup_dir: バックアップディレクトリ
        data_dir: dataディレクトリ
    """
    print("  エラーが発生しました。バックアップから復元中...")

    for file_name in os.listdir(backup_dir):
        backup_path = os.path.join(backup_dir, file_name)
        restore_path = os.path.join(data_dir, file_name)

        shutil.copy2(backup_path, restore_path)

    print("  ✓ バックアップから復元完了")


def collect_gtfs_statistics(data_dir: str) -> dict:
    """
    GTFSファイルの統計情報を収集

    Args:
        data_dir: dataディレクトリ

    Returns:
        統計情報の辞書
    """
    stats = {}

    # 各ファイルの行数をカウント
    gtfs_files = {
        'stops.txt': '停留所数',
        'routes.txt': '路線数',
        'trips.txt': '運行便数',
        'stop_times.txt': '時刻表レコード数',
        'calendar.txt': '運行カレンダー数',
        'calendar_dates.txt': 'カレンダー例外日数',
        'fare_attributes.txt': '運賃属性数',
        'fare_rules.txt': '運賃ルール数',
        'transfers.txt': '乗換情報数',
        'shapes.txt': '路線形状数',
        'translations.txt': '翻訳情報数'
    }

    for file_name, label in gtfs_files.items():
        file_path = os.path.join(data_dir, file_name)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                # ヘッダーを除いた行数
                count = sum(1 for _ in f) - 1
                stats[label] = count
        else:
            stats[label] = 0

    # feed_info.txtからメタ情報を取得
    feed_info_path = os.path.join(data_dir, 'feed_info.txt')
    if os.path.exists(feed_info_path):
        with open(feed_info_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stats['feed_publisher'] = row.get('feed_publisher_name', '')
                stats['feed_lang'] = row.get('feed_lang', '')
                stats['feed_start_date'] = row.get('feed_start_date', '')
                stats['feed_end_date'] = row.get('feed_end_date', '')
                stats['feed_version'] = row.get('feed_version', '')
                break

    return stats


def write_detail_file(detail_path: str, stats: dict, date_param: str, timestamp: str) -> None:
    """
    detail.txtに情報を記録

    Args:
        detail_path: detail.txtのパス
        stats: 統計情報
        date_param: dateパラメータ
        timestamp: 取得日時
    """
    with open(detail_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("京都市バス GTFS データ更新情報\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"取得日時: {timestamp}\n")
        f.write(f"dateパラメータ: {date_param}\n\n")

        f.write("-" * 80 + "\n")
        f.write("データ統計\n")
        f.write("-" * 80 + "\n\n")

        # 統計情報を整形して出力
        for key in ['停留所数', '路線数', '運行便数', '時刻表レコード数',
                    '運行カレンダー数', 'カレンダー例外日数', '運賃属性数',
                    '運賃ルール数', '乗換情報数', '路線形状数', '翻訳情報数']:
            value = stats.get(key, 0)
            f.write(f"{key} : {value:,}\n")

        f.write("\n" + "-" * 80 + "\n")
        f.write("フィードメタ情報 (feed_info.txt)\n")
        f.write("-" * 80 + "\n\n")

        f.write(f"発行者: {stats.get('feed_publisher', 'N/A')}\n")
        f.write(f"言語: {stats.get('feed_lang', 'N/A')}\n")

        start = stats.get('feed_start_date', '')
        end = stats.get('feed_end_date', '')
        if start and end:
            # YYYYMMDD → YYYY-MM-DD
            start_formatted = f"{start[:4]}-{start[4:6]}-{start[6:]}"
            end_formatted = f"{end[:4]}-{end[4:6]}-{end[6:]}"
            f.write(f"有効期間: {start_formatted} ～ {end_formatted}\n")

        f.write(f"バージョン: {stats.get('feed_version', 'N/A')}\n")

        f.write("\n" + "=" * 80 + "\n")

    print(f"  ✓ detail.txt作成: {detail_path}")


def clear_timetable_directory(timetable_dir: str) -> None:
    """
    timetableフォルダ内の全ファイルを削除

    Args:
        timetable_dir: timetableディレクトリ
    """
    if not os.path.exists(timetable_dir):
        os.makedirs(timetable_dir, exist_ok=True)
        print(f"  ✓ timetableディレクトリ作成: {timetable_dir}")
        return

    deleted_count = 0
    for file_name in os.listdir(timetable_dir):
        file_path = os.path.join(timetable_dir, file_name)
        if os.path.isfile(file_path):
            os.remove(file_path)
            deleted_count += 1

    print(f"  ✓ 既存時刻表削除: {deleted_count}ファイル")


def regenerate_timetables_json_only(data_dir: str, timetable_dir: str) -> None:
    """
    時刻表をJSON形式のみで再生成

    generate_all_timetables.pyの機能を統合

    Args:
        data_dir: GTFSデータディレクトリ
        timetable_dir: 時刻表出力ディレクトリ
    """
    # GTFSファイルパス
    stop_times_file = os.path.join(data_dir, "stop_times.txt")
    trips_file = os.path.join(data_dir, "trips.txt")
    routes_file = os.path.join(data_dir, "routes.txt")
    stops_file = os.path.join(data_dir, "stops.txt")

    print("  データファイルを読み込み中...")

    # 路線情報を読み込み
    routes = {}
    with open(routes_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            routes[row['route_id']] = row['route_short_name']

    # 運行便情報を読み込み
    trips = {}
    with open(trips_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            trips[row['trip_id']] = {
                'route_id': row['route_id'],
                'headsign': row['trip_headsign']
            }

    # バス停情報を読み込み
    stops = {}
    with open(stops_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            stops[row['stop_id']] = {
                'name': row['stop_name'],
                'desc': row['stop_desc']
            }

    # 各バス停の時刻表データを格納
    timetables = defaultdict(list)

    # stop_times.txtから時刻を抽出
    print("  stop_times.txtを読み込み中...")
    count = 0
    with open(stop_times_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            count += 1
            if count % 100000 == 0:
                print(f"    処理中: {count:,}行...")

            stop_id = row['stop_id']
            trip_id = row['trip_id']

            if trip_id in trips and stop_id in stops:
                trip_info = trips[trip_id]
                route_id = trip_info['route_id']
                route_name = routes.get(route_id, route_id)

                timetables[stop_id].append({
                    'time': row['arrival_time'],
                    'route': route_name,
                    'headsign': trip_info['headsign']
                })

    print(f"  ✓ 総行数: {count:,}")
    print(f"  ✓ 時刻表データがあるバス停数: {len(timetables):,}")

    # 各バス停の時刻表をJSON形式で保存
    print("  時刻表ファイルを生成中...")

    generated_count = 0
    for stop_id, timetable_data in timetables.items():
        # 時刻でソート
        timetable_data = sorted(timetable_data, key=lambda x: x['time'])

        stop_info = stops.get(stop_id, {'name': '不明', 'desc': ''})
        stop_name = stop_info['name']
        stop_desc = stop_info['desc']

        # JSON形式で出力
        output_file = os.path.join(timetable_dir, f"{stop_id}.json")

        json_data = {
            'stop_id': stop_id,
            'stop_name': stop_name,
            'stop_desc': stop_desc,
            'total_trips': len(timetable_data),
            'timetable': timetable_data
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        generated_count += 1

        # 進捗表示（100件ごと）
        if generated_count % 100 == 0:
            print(f"    生成中: {generated_count:,}/{len(timetables):,}ファイル")

    print(f"  ✓ 完了: {generated_count:,}個の時刻表ファイルを生成")


def main() -> int:
    """メイン処理"""
    # コマンドライン引数のパース
    parser = argparse.ArgumentParser(description='京都市バス GTFS データ更新ツール')
    parser.add_argument('--date', type=str, help='取得日を手動指定 (YYYYMMDD形式)')
    parser.add_argument('--manual', action='store_true', help='対話式で日付を入力')
    args = parser.parse_args()

    # パス設定
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(script_dir, '.env')
    data_dir = os.path.join(script_dir, 'data')
    backup_dir = os.path.join(script_dir, '.data_backup')
    timetable_dir = os.path.join(script_dir, 'timetable')
    temp_zip = os.path.join(script_dir, 'gtfs_temp.zip')
    detail_path = os.path.join(data_dir, 'detail.txt')

    try:
        print("=" * 80)
        print("京都市バス GTFS データ更新ツール")
        print("=" * 80)
        print()

        # 1. .envファイル読み込み
        print("[1/9] .envファイルを読み込み中...")
        env_vars = load_env_file(env_path)
        gtfs_url = env_vars.get('DEFAULT_GTFS_URL')
        api_key = env_vars.get('ODPT_CONSUMER_KEY')

        if not gtfs_url or not api_key:
            raise ValueError(".envに必要な変数が定義されていません")
        print("  ✓ 環境変数読み込み完了")
        print()

        # 2. date引数取得
        print("[2/9] 取得日を指定...")
        if args.date:
            # 手動で日付を指定
            date_param = args.date
            print(f"  コマンドライン引数で指定: {date_param}")
        elif args.manual:
            # 対話式で入力
            date_param = get_update_date(use_latest=False)
        else:
            # デフォルト: Webから最新日付を自動取得
            date_param = get_update_date(use_latest=True)
        print(f"  ✓ 取得日: {date_param}")
        print()

        # 3. 既存データのバックアップ
        print("[3/9] 既存データをバックアップ中...")
        backup_existing_data(data_dir, backup_dir)
        print()

        # 4. GTFSデータダウンロード
        print("[4/9] GTFSデータをダウンロード中...")
        download_gtfs_zip(gtfs_url, api_key, date_param, temp_zip)
        print()

        # --- ここからはロールバックが必要な領域 ---

        # 5. 古いGTFSファイル削除
        print("[5/9] 古いGTFSファイルを削除中...")
        cleanup_old_gtfs_files(data_dir)
        print()

        # 6. zip解凍
        print("[6/9] zipファイルを解凍中...")
        extract_zip_to_data(temp_zip, data_dir)
        print()

        # 7. 統計情報収集
        print("[7/9] データ統計を収集中...")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stats = collect_gtfs_statistics(data_dir)
        print(f"  ✓ 停留所数: {stats.get('停留所数', 0):,}")
        print(f"  ✓ 路線数: {stats.get('路線数', 0):,}")
        print(f"  ✓ 運行便数: {stats.get('運行便数', 0):,}")
        print()

        # 8. detail.txt作成
        print("[8/9] detail.txtを作成中...")
        write_detail_file(detail_path, stats, date_param, timestamp)
        print()

        # 9. timetableクリア→時刻表再生成
        print("[9/9] 時刻表を再生成中...")
        clear_timetable_directory(timetable_dir)
        regenerate_timetables_json_only(data_dir, timetable_dir)
        print()

        # 成功時: バックアップ削除、一時ファイル削除
        if os.path.exists(backup_dir):
            shutil.rmtree(backup_dir)
        if os.path.exists(temp_zip):
            os.remove(temp_zip)

        print("=" * 80)
        print("✓ 更新完了!")
        print("=" * 80)
        print()
        print(f"データディレクトリ: {data_dir}")
        print(f"時刻表ディレクトリ: {timetable_dir}")
        print(f"詳細情報: {detail_path}")

    except FileNotFoundError as e:
        print(f"\n❌ エラー: {e}")
        print("処理を中断しました。")
        return 1

    except ValueError as e:
        print(f"\n❌ エラー: {e}")
        print("処理を中断しました。")
        return 1

    except Exception as e:
        print(f"\n❌ 予期しないエラー: {e}")
        print()

        # フェーズ5以降でエラーが発生した場合はロールバック
        if os.path.exists(backup_dir):
            try:
                restore_from_backup(backup_dir, data_dir)
            except Exception as restore_error:
                print(f"❌ 復元エラー: {restore_error}")
                print("手動でバックアップから復元してください:")
                print(f"  バックアップ: {backup_dir}")

        # 一時ファイル削除
        if os.path.exists(temp_zip):
            os.remove(temp_zip)

        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
