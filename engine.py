"""
engine.py: 幾何計算およびデータフェッチエンジン
"""

import math
import time
import httpx
from typing import List, Optional, Dict, Tuple
from constants import (
    SEARCH_RADIUS_NM, FLIGHT_HOLD_SEC, MAJOR_AIRPORTS,
    AIRLINE_DATA, AIRCRAFT_MAP, COMPASS_MAP, WMO_CODES, GROUND_VEHICLE_PREFIXES
)

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
    nearest_code, nearest_name = "", ""
    nearest_lat, nearest_lon = 0.0, 0.0
    min_dist = float('inf')
    for code, (a_lat, a_lon, name) in MAJOR_AIRPORTS.items():
        dist, _, _ = calc_geo_metrics(lat, lon, a_lat, a_lon)
        if dist < min_dist:
            min_dist = dist
            nearest_code, nearest_name, nearest_lat, nearest_lon = code, name, a_lat, a_lon
    return nearest_code, nearest_name, nearest_lat, nearest_lon

class UniversalFlightEngine:
    def __init__(self):
        self.route_cache = {}
        self.tracked_flights: Dict[str, Dict] = {}
        self.cached_weather = {"temp": "--", "humidity": "--", "condition": "--", "wind_speed": "--", "wind_dir": "--"}
        self.last_weather_fetch = 0.0
        self.last_api_fetch = 0.0
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

    async def lookup_route(self, client: httpx.AsyncClient, callsign: str) -> Optional[str]:
        if callsign in self.route_cache:
            return self.route_cache[callsign]
        try:
            r = await client.get(f"https://api.adsbdb.com/v0/callsign/{callsign}", timeout=1.5)
            if r.status_code == 200:
                fr = r.json().get("response", {}).get("flightroute", {})
                o, d = fr.get("origin", {}).get("iata_code"), fr.get("destination", {}).get("iata_code")
                if o and d:
                    route = f"{o} > {d}"
                    self.route_cache[callsign] = route
                    return route
        except:
            pass
        self.route_cache[callsign] = None
        return None

    async def get_weather(self, client: httpx.AsyncClient, lat: float, lon: float) -> Dict[str, str]:
        now = time.time()
        if (now - self.last_weather_fetch) < 300:
            return self.cached_weather
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m&wind_speed_unit=ms&timezone=Asia%2FTokyo"
            r = await client.get(url, timeout=2.5)
            if r.status_code == 200:
                c = r.json().get("current", {})
                self.cached_weather = {
                    "temp": str(c.get("temperature_2m", "--")),
                    "humidity": str(c.get("relative_humidity_2m", "--")),
                    "condition": WMO_CODES.get(c.get("weather_code", 0), "晴れ"),
                    "wind_speed": str(round(c.get("wind_speed_10m", 0), 1)),
                    "wind_dir": deg_to_compass_16(c.get("wind_direction_10m", 0))
                }
                self.last_weather_fetch = now
        except:
            pass
        return self.cached_weather

    async def update_flights(self, home_lat: float, home_lon: float, visible_bearings: List[str]):
        current_time = time.time()
        apt_code, apt_name, apt_lat, apt_lon = get_nearest_airport(home_lat, home_lon)

        if (current_time - self.last_api_fetch) >= 3.0:
            raw_list = None
            async with httpx.AsyncClient(headers=self.headers, verify=False) as client:
                for url in [
                    f"https://api.airplanes.live/v2/point/{home_lat:.4f}/{home_lon:.4f}/{SEARCH_RADIUS_NM}",
                    f"https://api.adsb.lol/v2/point/{home_lat:.4f}/{home_lon:.4f}/{SEARCH_RADIUS_NM}"
                ]:
                    try:
                        r = await client.get(url, timeout=3.0)
                        if r.status_code == 200:
                            data = r.json()
                            raw_list = data.get("ac") or data.get("aircraft")
                            if raw_list is not None:
                                self.last_api_fetch = current_time
                                break
                    except:
                        continue

                if raw_list is not None:
                    for raw in raw_list:
                        lat, lon = raw.get("lat"), raw.get("lon")
                        if lat is None or lon is None:
                            continue
                        alt = raw.get("alt_baro")
                        gs = int(raw.get("gs") or 0)
                        alt_baro = 0 if alt in ("ground", None) else int(alt)
                        cs = str(raw.get("flight") or "").strip().upper()

                        if not cs or gs < 40 or any(cs.startswith(p) for p in GROUND_VEHICLE_PREFIXES):
                            continue

                        vr = int(raw.get("vert_rate") or 0)
                        track = raw.get("track")
                        dist_home, bearing_home, _ = calc_geo_metrics(home_lat, home_lon, lat, lon, alt_baro)
                        compass_home = deg_to_compass_code(bearing_home)
                        dist_apt, _, _ = calc_geo_metrics(lat, lon, apt_lat, apt_lon, alt_baro)

                        api_route = await self.lookup_route(client, cs)
                        is_target_apt = False
                        if api_route and apt_code in api_route:
                            is_target_apt = True
                        elif dist_apt <= 20.0 and alt_baro <= 6500:
                            is_target_apt = True

                        prev_f = self.tracked_flights.get(cs)
                        if prev_f:
                            is_target_apt = is_target_apt or prev_f.get("is_target", False)

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
                            route_str = f"{apt_code} > {h_compass}" if is_target_apt else f"PASS > {h_compass}"

                        self.tracked_flights[cs] = {
                            "callsign": cs, "airline": al_info["name"], "airline_code": al_info["code"], "color": al_info["color"],
                            "route": route_str, "phase": phase, "model": AIRCRAFT_MAP.get(raw.get("t", ""), raw.get("t", "Aircraft")),
                            "alt": alt_baro, "vr": vr, "gs": gs, "distance": round(dist_home, 1),
                            "compass": COMPASS_MAP.get(compass_home, compass_home),
                            "compass_code": compass_home,
                            "bearing": bearing_home, "is_target": is_target_apt,
                            "last_seen": current_time
                        }

        async with httpx.AsyncClient(verify=False) as client:
            weather_data = await self.get_weather(client, home_lat, home_lon)

        window_f, other_f = [], []
        for cs, f in list(self.tracked_flights.items()):
            age = current_time - f["last_seen"]
            if age > FLIGHT_HOLD_SEC:
                del self.tracked_flights[cs]
                continue

            f_copy = dict(f)
            f_copy["is_holding"] = age > 5.0
            f_copy["age_sec"] = int(age)

            in_win = (f["compass_code"] in visible_bearings) if visible_bearings else True
            if f["is_target"] and in_win:
                window_f.append(f_copy)
            else:
                other_f.append(f_copy)

        window_f.sort(key=lambda x: x["distance"])
        other_f.sort(key=lambda x: x["distance"])
        return window_f, other_f[:10], weather_data, apt_code, apt_name