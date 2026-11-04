import time
import math
import re
import requests
from datetime import datetime
from typing import List, Optional, Dict, Tuple
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
import uvicorn

# ==============================================================================
# 設定パラメータ（ベース）
# ==============================================================================
SEARCH_RADIUS_NM = 12       # 探索半径 (海里: 約22.2km)
FLIGHT_HOLD_SEC = 120.0     # ADS-B通信途絶後、機体情報を保持し続ける秒数 (45秒→120秒へ延長)

# ==============================================================================
# 日本全国の空港マスタ (最寄り空港自動判定用)
# ==============================================================================
MAJOR_AIRPORTS = {
    # 北海道
    "CTS": (42.7752, 141.6923, "新千歳"), "OKD": (43.1167, 141.3833, "丘珠"),
    "HKD": (41.7772, 140.8222, "函館"), "AKJ": (43.6708, 142.4475, "旭川"),
    "OBO": (42.7333, 143.2172, "帯広"), "KUH": (43.0408, 144.1931, "釧路"),
    "MMB": (43.8808, 144.1642, "女満別"), "WKJ": (45.4042, 141.8011, "稚内"),
    "RIS": (45.2422, 141.1128, "利尻"), "MBE": (44.3042, 143.4044, "紋別"),
    "SHB": (43.5775, 144.9606, "中標津"),
    # 東北
    "AOJ": (40.7333, 140.6900, "青森"), "MSJ": (40.7039, 141.3689, "三沢"),
    "ONJ": (40.1914, 140.3711, "大館能代"), "AXT": (39.6156, 140.2186, "秋田"),
    "HNA": (39.4289, 141.1350, "花巻"), "SYO": (38.8122, 139.7872, "庄内"),
    "SDJ": (38.1397, 140.9169, "仙台"), "GAJ": (38.4119, 140.3711, "山形"),
    "FKS": (37.2272, 140.4286, "福島"),
    # 関東・甲信越
    "HND": (35.5494, 139.7798, "羽田"), "NRT": (35.7647, 140.3863, "成田"),
    "IBR": (36.1822, 140.4150, "茨城"), "KIJ": (37.9558, 139.1133, "新潟"),
    "MMJ": (36.1667, 137.9222, "松本"),
    # 北陸・東海
    "TOY": (36.6486, 137.1875, "富山"), "KMQ": (36.3944, 136.4075, "小松"),
    "NTQ": (37.2933, 136.9619, "能登"), "FSZ": (34.7961, 138.1894, "静岡"),
    "NGO": (34.8583, 136.8054, "中部"), "NKM": (35.2550, 136.9242, "小牧"),
    # 近畿
    "ITM": (34.7855, 135.4382, "伊丹"), "KIX": (34.4320, 135.2304, "関西"),
    "UKB": (34.6328, 135.2239, "神戸"), "SHM": (33.6622, 135.3619, "南紀白浜"),
    "TJH": (35.5122, 134.7858, "但馬"),
    # 中国
    "OKJ": (34.7578, 133.8553, "岡山"), "HIJ": (34.4361, 132.9194, "広島"),
    "IWK": (34.1436, 132.2356, "岩国"), "TTJ": (35.5300, 134.1658, "鳥取"),
    "YGJ": (35.4939, 133.2367, "米子"), "IZO": (35.4136, 132.8897, "出雲"),
    "IWJ": (34.6761, 131.9344, "石見"), "UBJ": (33.9300, 131.2789, "山口宇部"),
    # 四国
    "TAK": (34.2142, 134.0156, "高松"), "TKS": (34.1328, 134.6064, "徳島"),
    "MYJ": (33.8272, 132.6997, "松山"), "KCZ": (33.5461, 133.6694, "高知"),
    # 九州
    "FUK": (33.5859, 130.4507, "福岡"), "KKJ": (33.8394, 130.9664, "北九州"),
    "HSG": (33.1497, 130.3025, "佐賀"), "NGS": (32.9169, 129.9136, "長崎"),
    "OIT": (33.4794, 131.7375, "大分"), "KMJ": (32.8378, 130.8550, "熊本"),
    "KMI": (31.8772, 131.4486, "宮崎"), "KOJ": (31.8034, 130.7194, "鹿児島"),
    # 離島
    "TSJ": (34.2883, 129.3303, "対馬"), "FUJ": (32.6669, 128.8328, "福江"),
    "ASJ": (28.4306, 129.7125, "奄美"), "TKN": (27.8358, 128.8814, "徳之島"),
    "OKE": (27.4253, 128.7019, "沖永良部"), "RNJ": (27.0433, 128.4014, "与論"),
    "OKA": (26.1958, 127.6459, "那覇"), "UEO": (26.3639, 126.7136, "久米島"),
    "MMY": (24.7828, 125.2844, "宮古"), "SHI": (24.8267, 125.1444, "下地島"),
    "ISG": (24.3964, 124.2450, "新石垣"), "TRA": (24.6533, 124.6931, "多良間"),
    "OGN": (24.4667, 122.9772, "与那国")
}

# ==============================================================================
# 辞書マスタ (ICAO, エアライン, 機種, 方角, 天気)
# ==============================================================================
ICAO_TO_IATA = {
    "RJOO": "ITM", "RJTT": "HND", "RJBB": "KIX", "RJBE": "UKB", "RJAA": "NRT",
    "RJCC": "CTS", "RJFF": "FUK", "ROAH": "OKA", "RJGG": "NGO", "RJSS": "SDJ",
    "RJFK": "KOJ", "RJFT": "KMJ", "RJFO": "OIT", "RJFM": "KMI", "RJOT": "TAK",
    "RJOK": "KCZ", "RJOM": "MYJ", "RJOA": "HIJ", "RJOB": "OKJ", "RJSN": "KIJ",
    "RJNT": "TOY", "RJNK": "KMQ", "RJCH": "HKD", "RJEC": "AKJ", "ROIG": "ISG",
    "RJSA": "AOJ", "RJSK": "AXT", "RJSC": "GAJ", "RJSF": "FKS", "RJSI": "HNA",
    "RJSM": "MSJ", "RJSR": "ONJ", "RJSY": "SYO", "RJFU": "NGS", "RJFR": "KKJ",
    "RJFS": "HSG", "RJFE": "FUJ", "RJFG": "TNE", "RJFC": "KUM", "RJKA": "ASJ",
    "RJKI": "Kikai", "RJKN": "TKN", "RJKX": "OKE", "RJOH": "YGJ", "RJOI": "IWK",
    "RJOC": "IZO", "RJOW": "IWJ", "RJBT": "TJH", "RJBD": "SHM", "RJCO": "OKD",
    "RJER": "RIS", "RJEO": "MBE", "RJCM": "MMB", "RJAW": "IBR", "RJAF": "MMJ",
    "RJNW": "NTQ", "RJNS": "FSZ", "RJNA": "NKM", "RJOR": "TTJ", "RJDC": "UBJ",
    "RJOS": "TKS", "RJDT": "TSJ", "RJKA": "ASJ", "ROAH": "OKA", "ROKJ": "UEO",
    "ROMY": "MMY", "ROIG": "ISG", "RORS": "SHI", "ROYN": "OGN",
}

AIRLINE_DATA = {
    "ANA": {"name": "ANA", "code": "ANA", "color": "#001e62"},
    "NH":  {"name": "ANA", "code": "ANA", "color": "#001e62"},
    "AKX": {"name": "ANA WINGS", "code": "AKX", "color": "#001e62"},
    "AJX": {"name": "Air Japan", "code": "AJX", "color": "#001e62"},
    "JAL": {"name": "JAL", "code": "JAL", "color": "#cc0000"},
    "JL":  {"name": "JAL", "code": "JAL", "color": "#cc0000"},
    "Jair":{"name": "J-AIR", "code": "JLJ", "color": "#cc0000"},
    "JLJ": {"name": "J-AIR", "code": "JLJ", "color": "#cc0000"},
    "JTA": {"name": "JTA", "code": "JTA", "color": "#cc0000"},
    "RAC": {"name": "RAC", "code": "RAC", "color": "#cc0000"},
    "JAC": {"name": "JAC", "code": "JAC", "color": "#059669"},
    "SKY": {"name": "SKYMARK", "code": "SKY", "color": "#002b49"},
    "APJ": {"name": "Peach", "code": "APJ", "color": "#ff66b2"},
    "JJP": {"name": "Jetstar", "code": "JJP", "color": "#ff6600"},
    "SFJ": {"name": "StarFlyer", "code": "SFJ", "color": "#111827"},
    "ADO": {"name": "AIRDO", "code": "ADO", "color": "#ffd400"},
    "SNA": {"name": "Solaseed", "code": "SNA", "color": "#008a45"},
    "FDA": {"name": "FDA", "code": "FDA", "color": "#b91c1c"},
    "IBX": {"name": "IBEX", "code": "IBX", "color": "#1d4ed8"},
    "AMX": {"name": "AMX", "code": "AMX", "color": "#db2777"},
    "HAC": {"name": "HAC", "code": "HAC", "color": "#cc0000"},
}

AIRCRAFT_MAP = {
    "B788": "B787-8", "B789": "B787-9", "B772": "B777-200", "B773": "B777-300",
    "B738": "B737-800", "A359": "A350-900", "A320": "A320", "A20N": "A320neo",
    "A321": "A321", "E190": "E190", "E170": "E170", "DH8D": "DHC-8-400", "AT76": "ATR72", "AT46": "ATR42"
}

COMPASS_MAP = {"N": "北", "NE": "北東", "E": "東", "SE": "南東", "S": "南", "SW": "南西", "W": "西", "NW": "北西"}
WMO_CODES = {0: "快晴", 1: "晴れ", 2: "一部曇り", 3: "曇り", 45: "霧", 51: "霧雨", 61: "雨", 63: "雨", 65: "大雨", 71: "雪", 95: "雷雨"}
GROUND_VEHICLE_PREFIXES = ("DENKI", "CAR", "TUG", "TOW", "BUS", "FIRE", "FOLLOW", "OPS", "MNT", "FUEL", "GND", "TEST", "0000")

# ==============================================================================
# ヘルパー関数
# ==============================================================================
def calc_geo_metrics(lat1: float, lon1: float, lat2: float, lon2: float, alt_ft: int = 0) -> Tuple[float, float, float]:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    distance_km = 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    y = math.sin(dlambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlambda)
    bearing_deg = (math.degrees(math.atan2(y, x)) + 360) % 360
    return distance_km, bearing_deg, alt_ft * 0.3048

def deg_to_compass_code(deg: float) -> str:
    codes = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return codes[int((deg + 22.5) % 360 // 45)]

def deg_to_compass_16(deg: float) -> str:
    val = int((deg / 22.5) + .5)
    arr = ["北","北北東","北東","東北東","東","東南東","南東","南南東","南","南南西","南西","西南西","西","西北西","北西","北北西"]
    return arr[(val % 16)]

def get_nearest_airport(lat: float, lon: float) -> Tuple[str, str, float, float]:
    nearest_code = ""
    nearest_name = ""
    nearest_lat, nearest_lon = 0.0, 0.0
    min_dist = float('inf')
    
    for code, (a_lat, a_lon, name) in MAJOR_AIRPORTS.items():
        dist, _, _ = calc_geo_metrics(lat, lon, a_lat, a_lon)
        if dist < min_dist:
            min_dist = dist
            nearest_code = code
            nearest_name = name
            nearest_lat = a_lat
            nearest_lon = a_lon
            
    return nearest_code, nearest_name, nearest_lat, nearest_lon

# ==============================================================================
# 汎用フライトエンジン
# ==============================================================================
class SmartRouteResolver:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})
        self.route_cache = {}

    def lookup_api(self, callsign: str) -> Optional[str]:
        if callsign in self.route_cache: return self.route_cache[callsign]
        try:
            r = self.session.get(f"https://api.adsbdb.com/v0/callsign/{callsign}", timeout=1.0)
            if r.status_code == 200:
                fr = r.json().get("response", {}).get("flightroute", {})
                o = fr.get("origin", {}).get("iata_code")
                d = fr.get("destination", {}).get("iata_code")
                if o and d:
                    res = f"{o} > {d}"
                    self.route_cache[callsign] = res
                    return res
        except: pass
        self.route_cache[callsign] = None
        return None

class UniversalFlightEngine:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})
        self.resolver = SmartRouteResolver()
        self.tracked_flights = {}
        self.current_home = (0.0, 0.0)
        self.cached_weather = {"temp": "--", "humidity": "--", "condition": "--", "wind_speed": "--", "wind_dir": "--"}
        self.last_weather_fetch = 0.0

    def get_weather(self, lat: float, lon: float) -> Dict[str, str]:
        now = time.time()
        dist_moved, _, _ = calc_geo_metrics(self.current_home[0], self.current_home[1], lat, lon)
        if (now - self.last_weather_fetch) < 600 and dist_moved < 1.0: 
            return self.cached_weather
            
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m&wind_speed_unit=ms&timezone=Asia%2FTokyo"
            r = self.session.get(url, timeout=2.0)
            if r.status_code == 200:
                c = r.json().get("current", {})
                self.cached_weather = {
                    "temp": str(c.get("temperature_2m", "--")), 
                    "humidity": str(c.get("relative_humidity_2m", "--")),
                    "condition": WMO_CODES.get(c.get("weather_code", 0), "不明"),
                    "wind_speed": str(round(c.get("wind_speed_10m", 0), 1)), 
                    "wind_dir": deg_to_compass_16(c.get("wind_direction_10m", 0))
                }
                self.last_weather_fetch = now
        except: pass
        return self.cached_weather

    def get_flights(self, home_lat: float, home_lon: float, visible_bearings: List[str]):
        dist_moved, _, _ = calc_geo_metrics(self.current_home[0], self.current_home[1], home_lat, home_lon)
        if dist_moved > 1.0:
            self.tracked_flights = {}
            self.current_home = (home_lat, home_lon)

        apt_code, apt_name, apt_lat, apt_lon = get_nearest_airport(home_lat, home_lon)
        weather_data = self.get_weather(home_lat, home_lon)
        current_time = time.time()
        
        raw_list = None
        for url in [f"https://api.airplanes.live/v2/point/{home_lat:.4f}/{home_lon:.4f}/{SEARCH_RADIUS_NM}", f"https://api.adsb.lol/v2/point/{home_lat:.4f}/{home_lon:.4f}/{SEARCH_RADIUS_NM}"]:
            try:
                r = self.session.get(url, timeout=3.0)
                if r.status_code == 200:
                    raw_list = r.json().get("ac", r.json().get("aircraft"))
                    break
            except: pass

        if raw_list is not None:
            for raw in raw_list:
                lat, lon, alt = raw.get("lat"), raw.get("lon"), raw.get("alt_baro")
                if lat is None or lon is None: continue
                gs = int(raw.get("gs") or 0)
                alt_baro = 0 if alt in ("ground", None) else int(alt)
                cs = str(raw.get("flight") or "").strip().upper()
                
                if not cs or gs < 45 or any(cs.startswith(p) for p in GROUND_VEHICLE_PREFIXES): continue

                vr = int(raw.get("vert_rate") or 0)
                track = raw.get("track")
                dist_home, bearing_home, _ = calc_geo_metrics(home_lat, home_lon, lat, lon, alt_baro)
                compass_home = deg_to_compass_code(bearing_home)
                
                dist_apt, _, _ = calc_geo_metrics(lat, lon, apt_lat, apt_lon, alt_baro)
                
                api_route = self.resolver.lookup_api(cs)
                is_target_apt = False
                
                if api_route and apt_code in api_route:
                    is_target_apt = True
                elif dist_apt <= 15.0 and alt_baro <= 5500:
                    is_target_apt = True

                in_window = (compass_home in visible_bearings) if visible_bearings else True

                # ==============================================================
                # 🎯 STICKY（張り付き）ロジック: 一度捕捉した機体は条件から外れても維持する
                # ==============================================================
                prev_f = self.tracked_flights.get(cs)
                if prev_f:
                    is_target_apt = is_target_apt or prev_f.get("is_target", False)
                    in_window = in_window or prev_f.get("in_window", False)

                phase = "通過・周辺便"
                if is_target_apt:
                    if alt_baro <= 3500 and vr > 150: phase = f"{apt_name} 離陸・上昇"
                    elif alt_baro <= 4500 and vr < -150: phase = f"{apt_name} 進入・降下"
                    elif vr > 250: phase = "離陸・上昇中"
                    elif vr < -250: phase = "進入・降下中"
                    else: phase = f"{apt_name}空域 飛行中"

                al_info = AIRLINE_DATA.get(cs[:3], AIRLINE_DATA.get(cs[:2], {"name": "民間機", "code": cs[:3], "color": "#475569"}))
                
                route_str = api_route
                if not route_str:
                    h_compass = deg_to_compass_code(track) if track else "---"
                    if is_target_apt:
                        route_str = f"{apt_code} > {h_compass}" if (vr > 100 or alt_baro < 3500) else f"APPR > {apt_code}"
                    else:
                        route_str = f"PASS > {h_compass}"

                self.tracked_flights[cs] = {
                    "callsign": cs, "airline": al_info["name"], "airline_code": al_info["code"], "color": al_info["color"],
                    "route": route_str, "phase": phase, "model": AIRCRAFT_MAP.get(raw.get("t", ""), raw.get("t", "Aircraft")),
                    "alt": alt_baro, "vr": vr, "gs": gs, "distance": round(dist_home, 1), "compass": COMPASS_MAP.get(compass_home, compass_home),
                    "bearing": bearing_home, "is_target": is_target_apt,
                    "in_window": in_window,
                    "last_seen": current_time
                }

        window_f, other_f = [], []
        for cs, f in list(self.tracked_flights.items()):
            age = current_time - f["last_seen"]
            if age > FLIGHT_HOLD_SEC:
                del self.tracked_flights[cs]
                continue
            f_copy = dict(f)
            f_copy["is_holding"] = age > 5.0
            f_copy["age_sec"] = int(age)

            if f_copy["is_target"] and f_copy["in_window"]: window_f.append(f_copy)
            else: other_f.append(f_copy)

        window_f.sort(key=lambda x: x["distance"])
        other_f.sort(key=lambda x: x["distance"])
        
        return window_f, other_f[:10], weather_data, apt_code, apt_name

app = FastAPI()
engine = UniversalFlightEngine()

# ==============================================================================
# HTML テンプレート
# ==============================================================================
SETUP_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Universal Flight Board Setup</title>
    <style>
        body { background: #030712; color: #f1f5f9; font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: #0b0f19; border: 2px solid #1f2937; padding: 30px; border-radius: 8px; width: 100%; max-width: 400px; box-shadow: 0 10px 25px rgba(0,0,0,0.8); }
        h2 { color: #38bdf8; text-align: center; margin-top: 0; font-family: monospace;}
        .input-group { margin-bottom: 15px; }
        label { display: block; font-size: 13px; color: #9ca3af; margin-bottom: 5px; }
        input[type="text"] { width: 100%; padding: 10px; background: #020617; border: 1px solid #374151; color: white; border-radius: 4px; box-sizing: border-box; }
        .btn { width: 100%; padding: 12px; background: #0284c7; color: white; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; margin-top: 10px; }
        .btn:hover { background: #0369a1; }
        .btn-gps { background: #059669; margin-bottom: 20px; }
        .btn-gps:hover { background: #047857; }
        .checkbox-group { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 5px; }
        .checkbox-group label { display: inline-flex; align-items: center; background: #111827; padding: 5px 10px; border-radius: 4px; border: 1px solid #374151; cursor: pointer; font-size: 13px;}
    </style>
</head>
<body>
    <div class="card">
        <h2>✈️ Flight Board Setup</h2>
        <button type="button" class="btn btn-gps" onclick="getLocation()">📍 現在地をGPSで自動取得</button>
        
        <form action="/board" method="GET">
            <div class="input-group">
                <label>緯度 (Latitude) - 例: 34.7855</label>
                <input type="text" id="lat" name="lat" required>
            </div>
            <div class="input-group">
                <label>経度 (Longitude) - 例: 135.4382</label>
                <input type="text" id="lon" name="lon" required>
            </div>
            <div class="input-group">
                <label>窓から見える方角 (チェックなしで全方位モニタ)</label>
                <div class="checkbox-group">
                    <label><input type="checkbox" name="b" value="N"> 北</label>
                    <label><input type="checkbox" name="b" value="NE"> 北東</label>
                    <label><input type="checkbox" name="b" value="E"> 東</label>
                    <label><input type="checkbox" name="b" value="SE"> 南東</label>
                    <label><input type="checkbox" name="b" value="S"> 南</label>
                    <label><input type="checkbox" name="b" value="SW"> 南西</label>
                    <label><input type="checkbox" name="b" value="W"> 西</label>
                    <label><input type="checkbox" name="b" value="NW"> 北西</label>
                </div>
            </div>
            <button type="submit" class="btn">モニターを起動する 🚀</button>
        </form>
    </div>
    <script>
        function getLocation() {
            let btn = document.querySelector('.btn-gps');
            btn.innerText = "取得中...";
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition((pos) => {
                    document.getElementById('lat').value = pos.coords.latitude;
                    document.getElementById('lon').value = pos.coords.longitude;
                    btn.innerText = "📍 現在地を取得完了";
                }, () => {
                    alert("位置情報の取得に失敗しました。ブラウザの権限設定を確認してください。");
                    btn.innerText = "📍 現在地をGPSで自動取得";
                });
            }
        }
    </script>
</body>
</html>
"""

BOARD_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>UNIVERSAL FLIGHT BOARD</title>
    <style>
        body { background-color: #030712; color: #f1f5f9; font-family: 'Courier New', Courier, monospace, sans-serif; margin: 0; padding: 12px; height: 100vh; box-sizing: border-box; overflow: hidden; display: flex; flex-direction: column; }
        header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #1f2937; padding-bottom: 8px; margin-bottom: 12px; flex-shrink: 0; gap: 10px; flex-wrap: wrap;}
        .header-left { display: flex; align-items: center; gap: 12px; }
        .live-dot { width: 10px; height: 10px; background-color: #10b981; border-radius: 50%; box-shadow: 0 0 10px #10b981; animation: pulse 1.6s infinite; flex-shrink: 0;}
        @keyframes pulse { 0% { opacity: 1; transform: scale(1); } 50% { opacity: 0.3; transform: scale(0.85); } 100% { opacity: 1; transform: scale(1); } }
        h1 { margin: 0; font-size: 19px; color: #fbbf24; letter-spacing: 2px; text-shadow: 0 0 12px rgba(251, 191, 36, 0.4); white-space: nowrap;}
        
        .location-controls { display: flex; gap: 4px; align-items: center; background: #0b0f19; padding: 4px 10px; border-radius: 6px; border: 1px solid #1f2937; }
        .location-controls input { width: 70px; background: #020617; border: 1px solid #374151; color: #fff; font-size: 12px; padding: 4px; border-radius: 3px; text-align: center; }
        .location-controls .btn-update { background: #0284c7; color: white; border: none; padding: 4px 8px; font-size: 11px; border-radius: 3px; cursor: pointer; font-weight: bold; }
        .location-controls .btn-update:hover { background: #0369a1; }
        .location-controls .btn-gps { background: #059669; color: white; border: none; padding: 4px 6px; font-size: 11px; border-radius: 3px; cursor: pointer; }
        
        .header-right { display: flex; align-items: center; gap: 15px; }
        .weather-panel { display: flex; gap: 14px; background: rgba(17, 24, 39, 0.6); padding: 6px 12px; border-radius: 6px; border: 1px solid #1f2937; font-size: 13px; color: #93c5fd; font-weight: bold; }
        .weather-item span { color: #e2e8f0; margin-left: 4px; }
        .status { font-size: 12px; color: #6b7280; }
        
        .main-layout { display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(340px, 1fr); gap: 16px; flex-grow: 1; min-height: 0; }
        .left-column { display: flex; flex-direction: column; gap: 12px; min-height: 0; height: 100%; overflow-y: auto; }
        .right-sidebar { display: flex; flex-direction: column; gap: 12px; min-height: 0; height: 100%; }
        
        .flap-card { background: #0b0f19; border: 2px solid #1f2937; border-radius: 6px; box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 10px 25px rgba(0,0,0,0.8); padding: 14px 18px; flex-shrink: 0; }
        .flap-card.primary { border-color: #d97706; }
        .top-info { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; border-bottom: 1px dashed #1f2937; padding-bottom: 6px; }
        .flight-phase-badge { background: #111827; color: #38bdf8; border: 1px solid #374151; padding: 3px 10px; border-radius: 4px; font-size: 11px; font-weight: bold; letter-spacing: 1px; }
        .airline-logo { display: inline-block; padding: 2px 7px; border-radius: 3px; font-size: 11px; font-weight: bold; color: #ffffff; margin-right: 6px; }
        
        .splitflap-display { display: inline-flex; gap: 3px; background: #000000; padding: 6px 8px; border-radius: 4px; border: 1px solid #262626; box-shadow: inset 0 0 10px rgba(0,0,0,0.9); perspective: 400px; }
        .flap-char { position: relative; width: 24px; height: 40px; background: #141414; color: #fbbf24; font-size: 24px; font-weight: bold; text-align: center; line-height: 40px; border-radius: 3px; box-shadow: 0 2px 4px rgba(0,0,0,0.8); overflow: hidden; }
        .flap-char::after { content: ''; position: absolute; left: 0; right: 0; top: 50%; height: 1px; background: rgba(0, 0, 0, 0.9); border-bottom: 1px solid rgba(255, 255, 255, 0.12); z-index: 5; }
        .flap-char.flip { animation: flipAnim 0.35s cubic-bezier(0.4, 0.0, 0.2, 1); }
        @keyframes flipAnim { 0% { transform: rotateX(0deg); filter: brightness(1); } 50% { transform: rotateX(-90deg); filter: brightness(0.5); } 100% { transform: rotateX(0deg); filter: brightness(1); } }
        
        .details-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-top: 12px; background: #000000; padding: 8px 10px; border-radius: 4px; border: 1px solid #1f2937; }
        .detail-label { font-size: 9px; color: #6b7280; text-align: center; margin-bottom: 2px; }
        .detail-value { font-size: 13px; color: #f3f4f6; font-weight: bold; text-align: center; }
        
        /* レーダーデザイン */
        .radar-panel { background: #0b0f19; border: 2px solid #1f2937; border-radius: 6px; padding: 14px; display: flex; flex-direction: column; align-items: center; box-shadow: 0 8px 20px rgba(0,0,0,0.7); flex-shrink: 0; }
        .radar-title { font-size: 12px; color: #38bdf8; font-weight: bold; margin-bottom: 10px; border-bottom: 1px solid #1f2937; padding-bottom: 4px; width: 100%; text-align: center; }
        
        .radar-screen { width: 85%; max-width: 360px; min-width: 250px; aspect-ratio: 1 / 1; background: radial-gradient(circle at center, #002b4d 0%, #000a14 70%); border: 3px solid #0f172a; border-radius: 50%; position: relative; overflow: hidden; box-shadow: inset 0 0 30px rgba(0, 0, 0, 0.9), 0 0 10px rgba(56, 189, 248, 0.2); }
        .radar-grid-rings { position: absolute; top: 0; left: 0; width: 100%; height: 100%; border-radius: 50%; background-image: repeating-radial-gradient(transparent, transparent 15%, rgba(56, 189, 248, 0.15) 15.5%, transparent 16%); }
        .radar-line-h { position: absolute; top: 50%; left: 0; right: 0; height: 1px; background: rgba(56, 189, 248, 0.25); }
        .radar-line-v { position: absolute; left: 50%; top: 0; bottom: 0; width: 1px; background: rgba(56, 189, 248, 0.25); }
        .radar-center { position: absolute; top: 50%; left: 50%; width: 5px; height: 5px; background: #38bdf8; border-radius: 50%; transform: translate(-50%, -50%); box-shadow: 0 0 10px #38bdf8; z-index: 20; }
        .radar-sweep { position: absolute; top: 0; left: 0; width: 100%; height: 100%; border-radius: 50%; background: conic-gradient(from 0deg, rgba(56,189,248,0.7) 0deg, rgba(56,189,248,0.1) 60deg, transparent 90deg, transparent 360deg); animation: scan 4s linear infinite; pointer-events: none; z-index: 10;}
        @keyframes scan { to { transform: rotate(360deg); } }
        
        .radar-blip { position: absolute; width: 8px; height: 8px; background: #94a3b8; border-radius: 50%; transform: translate(-50%, -50%); z-index: 15; transition: all 1.5s ease-out; }
        .radar-blip.tgt { background: #facc15; width: 10px; height: 10px; box-shadow: 0 0 8px #facc15; }
        .radar-blip.tgt.primary { background: #f59e0b; width: 14px; height: 14px; box-shadow: 0 0 15px #f59e0b; }
        .radar-label { position: absolute; font-size: 10px; color: #7dd3fc; background: rgba(2, 6, 23, 0.85); padding: 2px 4px; border: 1px solid rgba(56, 189, 248, 0.3); z-index: 16; transform: translate(8px, -10px); transition: all 1.5s ease-out; border-radius: 2px; }
        
        .other-flights-panel { background: #0b0f19; border: 2px solid #1f2937; border-radius: 6px; padding: 10px; flex-grow: 1; display: flex; flex-direction: column; overflow: hidden;}
        .other-flight-item { background: #020617; border: 1px solid #1f2937; border-radius: 4px; padding: 8px; margin-bottom: 6px; display: flex; flex-direction: column; font-size: 11px;}
        .standby-board { text-align: center; background: #0b0f19; border: 2px solid #1f2937; border-radius: 6px; padding: 20px; flex-grow: 1; display: flex; flex-direction: column; justify-content: center; }
    </style>
</head>
<body>
    <header>
        <div class="header-left">
            <div class="live-dot"></div>
            <div>
                <h1 id="board-title">UNIVERSAL FLIGHT BOARD</h1>
                <div class="status" id="provider-status">スキャンを準備中...</div>
            </div>
        </div>
        
        <!-- グローバル座標コントロール -->
        <div class="location-controls">
            <span style="font-size: 11px; color:#9ca3af; font-weight:bold;">観測地:</span>
            <input type="text" id="board-lat" placeholder="緯度">
            <input type="text" id="board-lon" placeholder="経度">
            <button class="btn-update" onclick="updateLocation()">更新</button>
            <button class="btn-gps" onclick="getBoardLocation()" title="現在地を取得">📍</button>
        </div>

        <div class="header-right">
            <div class="weather-panel" id="weather-panel"><div class="weather-item">🌧️ 取得中...</div></div>
            <div class="status" id="clock" style="font-size: 18px; color: #fbbf24; font-weight: bold;">--:--:--</div>
        </div>
    </header>

    <div class="main-layout">
        <div id="board-container" class="left-column">
            <div class="standby-board">
                <div style="font-size: 18px; color: #38bdf8; font-weight: bold; margin-bottom: 6px;">🪟 空間を初期スキャン中...</div>
                <div style="font-size: 12px; color: #9ca3af;">最寄り空港のトラフィックを受信すると表示されます</div>
            </div>
        </div>

        <div class="right-sidebar">
            <div class="radar-panel">
                <div class="radar-title">📡 ターミナルレーダー</div>
                
                <div class="radar-screen" id="radar-screen">
                    <div class="radar-grid-rings"></div>
                    <div class="radar-line-h"></div>
                    <div class="radar-line-v"></div>
                    <div class="radar-sweep"></div>
                    <div class="radar-center" title="現在地"></div>
                </div>
                <div style="font-size: 9px; color: #6b7280; text-align: center; margin-top: 10px;">水色＝現在地 / 黄＝最寄り空港便 / 灰＝通過機</div>
            </div>

            <div class="other-flights-panel">
                <div style="font-size: 11px; color: #9ca3af; font-weight: bold; border-bottom: 1px solid #1f2937; padding-bottom: 4px; margin-bottom: 6px;">
                    ✈ 周辺通過機 近い順 (<span id="other-count">0</span>機)
                </div>
                <div id="other-flights-list" style="overflow-y: auto;"></div>
            </div>
        </div>
    </div>

    <script>
        const urlParams = new URLSearchParams(window.location.search);
        let lat = urlParams.get('lat') || "34.7855";
        let lon = urlParams.get('lon') || "135.4382";
        const bearings = urlParams.getAll('b').join(',');
        
        document.getElementById('board-lat').value = lat;
        document.getElementById('board-lon').value = lon;

        setInterval(() => { document.getElementById('clock').innerText = new Date().toTimeString().split(' ')[0]; }, 1000);
        let lastRoutes = {};

        function updateLocation() {
            lat = document.getElementById('board-lat').value;
            lon = document.getElementById('board-lon').value;
            
            let newUrl = new URL(window.location);
            newUrl.searchParams.set('lat', lat);
            newUrl.searchParams.set('lon', lon);
            window.history.pushState({}, '', newUrl);
            
            document.getElementById('board-title').innerText = `🔄 RELOADING...`;
            document.getElementById('provider-status').innerHTML = `新しい観測地のデータを取得中...`;
            update();
        }

        function getBoardLocation() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition((pos) => {
                    document.getElementById('board-lat').value = pos.coords.latitude.toFixed(4);
                    document.getElementById('board-lon').value = pos.coords.longitude.toFixed(4);
                    updateLocation();
                }, () => alert("GPSの取得に失敗しました。"));
            }
        }

        function renderFlap(text, id) {
            let padded = text.padEnd(12, ' ').slice(0, 12);
            let prev = lastRoutes[id] || "";
            let html = '<div class="splitflap-display">';
            for (let i = 0; i < padded.length; i++) {
                let char = padded[i];
                let cls = (prev[i] !== char) ? 'flip' : '';
                html += `<div class="flap-char ${cls}">${char === ' ' ? '&nbsp;' : char}</div>`;
            }
            html += '</div>';
            lastRoutes[id] = padded;
            return html;
        }

        async function update() {
            try {
                let res = await fetch(`/api/flights?lat=${lat}&lon=${lon}&bearings=${bearings}`);
                let data = await res.json();
                
                document.getElementById('board-title').innerText = `${data.apt_code} FLIGHT BOARD`;
                document.getElementById('provider-status').innerHTML = `BASE: ${data.apt_name}周辺 (対象: ${data.window_flights.length}機)`;
                
                if(data.weather) {
                    document.getElementById('weather-panel').innerHTML = `
                        <div class="weather-item">☁️ <span>${data.weather.condition}</span></div>
                        <div class="weather-item">🌡️ <span>${data.weather.temp}℃</span></div>
                        <div class="weather-item">💧 <span>${data.weather.humidity}%</span></div>
                        <div class="weather-item">🌬️ <span>${data.weather.wind_dir} ${data.weather.wind_speed}m/s</span></div>
                    `;
                }

                let container = document.getElementById('board-container');
                let radar = document.getElementById('radar-screen');
                let otherList = document.getElementById('other-flights-list');
                document.getElementById('other-count').innerText = data.other_flights.length;
                
                radar.querySelectorAll('.radar-blip, .radar-label').forEach(b => b.remove());

                const drawBlip = (f, isTarget, isPrimary) => {
                    let r = Math.min(f.distance * 1.852 / 22.2, 0.90) * 50;
                    let rad = (f.bearing - 90) * (Math.PI / 180);
                    let x = 50 + r * Math.cos(rad), y = 50 + r * Math.sin(rad);
                    
                    let b = document.createElement('div');
                    b.className = `radar-blip ${isTarget ? 'tgt' : ''} ${isPrimary ? 'primary' : ''}`;
                    b.style.left = `${x}%`; b.style.top = `${y}%`;
                    radar.appendChild(b);
                    
                    if(isTarget) {
                        let l = document.createElement('div');
                        l.className = 'radar-label'; l.style.left = `${x}%`; l.style.top = `${y}%`;
                        l.innerHTML = `${f.callsign}<br><span style="color:#fbbf24">${f.alt}ft</span>`;
                        radar.appendChild(l);
                    }
                };

                data.other_flights.forEach(f => drawBlip(f, false, false));
                data.window_flights.forEach((f, i) => drawBlip(f, true, i === 0));

                if (data.window_flights.length === 0) {
                    container.innerHTML = `<div class="standby-board"><div style="color:#38bdf8;font-size:18px;font-weight:bold;">🪟 視界内はクリアです</div><div style="color:#9ca3af;font-size:12px;margin-top:6px;">現在、指定方角に${data.apt_name}発着便は見当たりません</div></div>`;
                } else {
                    container.innerHTML = data.window_flights.map((f, i) => `
                        <div class="flap-card ${i === 0 ? 'primary' : ''}">
                            <div class="top-info">
                                <div class="flight-phase-badge">${i === 0 ? '★ VISIBLE' : '◆ IN VIEW'} : ${f.phase}${f.is_holding ? ` <span style="color:#f59e0b">[HOLD]</span>` : ''}</div>
                                <div style="font-size: 13px; font-weight: bold; color: #9ca3af;">
                                    <span class="airline-logo" style="background-color: ${f.color};">${f.airline_code}</span>
                                    <span style="color: #f8fafc;">${f.callsign}</span>
                                </div>
                            </div>
                            <div style="font-size: 9px; color: #6b7280; margin-bottom:4px;">FLIGHT ROUTE</div>
                            <div>${renderFlap(f.route, `slot_${i}`)}</div>
                            <div class="details-grid">
                                <div><div class="detail-label">AIRCRAFT</div><div class="detail-value" style="color:#38bdf8;">${f.model}</div></div>
                                <div><div class="detail-label">ALTITUDE</div><div class="detail-value">${f.alt} ft</div></div>
                                <div><div class="detail-label">SPEED/VR</div><div class="detail-value">${f.gs}kt (${f.vr>0?'+':''}${f.vr})</div></div>
                                <div><div class="detail-label">DIRECTION</div><div class="detail-value" style="color:#fbbf24;">${f.compass} / ${f.distance}km</div></div>
                            </div>
                        </div>
                    `).join('');
                }

                otherList.innerHTML = data.other_flights.map(f => {
                    let vrSign = f.vr > 0 ? "▲" : (f.vr < 0 ? "▼" : "―");
                    let holdBadge = f.is_holding ? ` <span style="color:#f59e0b; font-size:9px;">[HOLD]</span>` : '';
                    return `
                    <div class="other-flight-item">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <span class="other-badge" style="background:${f.color};">${f.airline_code}</span> 
                                <span style="color:#f8fafc;font-weight:bold;">${f.callsign}</span>
                                <span style="color:#9ca3af;font-size:10px;margin-left:4px;">${f.airline}</span>
                                ${holdBadge}
                            </div>
                            <div style="color:#e2e8f0;font-weight:bold;font-size:10px;">${f.distance}km / ${f.compass}</div>
                        </div>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:4px;">
                            <div style="color:#38bdf8;font-weight:bold;font-family:monospace;font-size:12px;">✈ ${f.route}</div>
                            <div style="color:#cbd5e1;font-size:10px;text-align:right;">
                                ALT: <span style="color:#fbbf24;font-weight:bold;">${f.alt}ft</span> ${vrSign} <br>
                                SPD: <span style="color:#fbbf24;font-weight:bold;">${f.gs}kt</span>
                            </div>
                        </div>
                    </div>
                    `;
                }).join('');

            } catch (e) { console.error(e); }
        }
        setInterval(update, 3000);
        update();
    </script>
</body>
</html>
"""

# ==============================================================================
# API エンドポイント
# ==============================================================================
@app.get("/", response_class=HTMLResponse)
async def setup():
    return SETUP_HTML

@app.get("/board", response_class=HTMLResponse)
async def board():
    return BOARD_HTML

@app.get("/api/flights")
async def api_flights(lat: float = Query(...), lon: float = Query(...), bearings: str = Query("")):
    b_list = [b.strip() for b in bearings.split(",")] if bearings else []
    window_flights, other_flights, weather, apt_code, apt_name = engine.get_flights(lat, lon, b_list)
    return {
        "window_flights": window_flights,
        "other_flights": other_flights,
        "weather": weather,
        "apt_code": apt_code,
        "apt_name": apt_name
    }

if __name__ == "__main__":
    print("=" * 65)
    print(" ✈️  ユニバーサル フライトボード サーバー起動！ (ポート: 8001)")
    print(" 🌐 ブラウザでアクセス: http://localhost:8001")
    print("=" * 65)
    uvicorn.run(app, host="0.0.0.0", port=8001)