import math
import time
import re
import requests
from datetime import datetime
from typing import Optional, Dict, Tuple, List
from fastapi import FastAPI, Response, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

SEARCH_RADIUS_NM = 15       # 探索半径 (海里: 約27.8km)

# ==============================================================================
# 日本全国全空港マスタ (計85空港)
# ==============================================================================
AIRPORT_MASTER = [
    # --- 北海道 ---
    {"icao": "RJCC", "iata": "CTS", "name": "札幌/新千歳", "region": "北海道", "lat": 42.7752, "lon": 141.6922, "start_h": 7, "end_h": 22},
    {"icao": "RJCO", "iata": "OKD", "name": "札幌/丘珠",   "region": "北海道", "lat": 43.1161, "lon": 141.3803, "start_h": 7, "end_h": 21},
    {"icao": "RJCH", "iata": "HKD", "name": "函館",        "region": "北海道", "lat": 41.7700, "lon": 140.8222, "start_h": 7, "end_h": 20},
    {"icao": "RJEC", "iata": "AKJ", "name": "旭川",        "region": "北海道", "lat": 43.6708, "lon": 142.4475, "start_h": 7, "end_h": 20},
    {"icao": "RJCB", "iata": "OBO", "name": "とかち帯広",  "region": "北海道", "lat": 42.7333, "lon": 143.2172, "start_h": 7, "end_h": 21},
    {"icao": "RJCK", "iata": "KUH", "name": "たんちょう釧路","region": "北海道", "lat": 43.0411, "lon": 144.1931, "start_h": 7, "end_h": 21},
    {"icao": "RJEB", "iata": "MMB", "name": "女満別",      "region": "北海道", "lat": 43.8806, "lon": 144.1642, "start_h": 7, "end_h": 20},
    {"icao": "RJCM", "iata": "MMD", "name": "南紀白浜",    "region": "近畿",   "lat": 33.6622, "lon": 135.3619, "start_h": 7, "end_h": 20}, # 下部再分類
    {"icao": "RJCW", "iata": "WKJ", "name": "稚内",        "region": "北海道", "lat": 45.4042, "lon": 141.8056, "start_h": 7, "end_h": 20},
    {"icao": "RJCN", "iata": "SHB", "name": "根室中標津",  "region": "北海道", "lat": 43.5775, "lon": 144.9603, "start_h": 7, "end_h": 20},
    {"icao": "RJEO", "iata": "OIR", "name": "奥尻",        "region": "北海道", "lat": 42.0719, "lon": 139.4328, "start_h": 8, "end_h": 17},
    {"icao": "RJER", "iata": "RIS", "name": "利尻",        "region": "北海道", "lat": 45.2422, "lon": 141.1858, "start_h": 8, "end_h": 17},
    {"icao": "RJRE", "iata": "OIR", "name": "礼文",        "region": "北海道", "lat": 45.4547, "lon": 141.0406, "start_h": 8, "end_h": 17},
    {"icao": "RJOP", "iata": "MBE", "name": "オホーツク紋別","region": "北海道", "lat": 44.3039, "lon": 143.4042, "start_h": 8, "end_h": 18},

    # --- 東北 ---
    {"icao": "RJSS", "iata": "SDJ", "name": "仙台",        "region": "東北",   "lat": 38.1397, "lon": 140.9169, "start_h": 7, "end_h": 21},
    {"icao": "RJSA", "iata": "AOJ", "name": "青森",        "region": "東北",   "lat": 40.7347, "lon": 140.6906, "start_h": 7, "end_h": 21},
    {"icao": "RJSC", "iata": "HNA", "name": "いわて花巻",  "region": "東北",   "lat": 39.4286, "lon": 141.1356, "start_h": 7, "end_h": 20},
    {"icao": "RJSK", "iata": "AXT", "name": "秋田",        "region": "東北",   "lat": 39.6156, "lon": 140.2186, "start_h": 7, "end_h": 21},
    {"icao": "RJSO", "iata": "ONJ", "name": "大館能代",    "region": "東北",   "lat": 40.1919, "lon": 140.3736, "start_h": 7, "end_h": 19},
    {"icao": "RJSC", "iata": "GAJ", "name": "山形",        "region": "東北",   "lat": 38.4119, "lon": 140.3714, "start_h": 7, "end_h": 20},
    {"icao": "RJSY", "iata": "SYO", "name": "庄内",        "region": "東北",   "lat": 38.8122, "lon": 139.7872, "start_h": 7, "end_h": 20},
    {"icao": "RJSF", "iata": "FKS", "name": "福島",        "lat": 37.2275, "lon": 140.4319, "region": "東北", "start_h": 7, "end_h": 20},
    {"icao": "RJSM", "iata": "MSJ", "name": "三沢",        "region": "東北",   "lat": 40.7033, "lon": 141.3681, "start_h": 7, "end_h": 21},

    # --- 関東 ---
    {"icao": "RJTT", "iata": "HND", "name": "東京/羽田",    "region": "関東",   "lat": 35.5494, "lon": 139.7798, "start_h": 0, "end_h": 24},
    {"icao": "RJAA", "iata": "NRT", "name": "東京/成田",    "region": "関東",   "lat": 35.7647, "lon": 140.3863, "start_h": 6, "end_h": 23},
    {"icao": "RJAH", "iata": "IBR", "name": "茨城",        "region": "関東",   "lat": 36.1811, "lon": 140.4147, "start_h": 7, "end_h": 21},
    {"icao": "RJTO", "iata": "OIM", "name": "大島",        "region": "関東",   "lat": 34.7822, "lon": 139.3603, "start_h": 8, "end_h": 18},
    {"icao": "RJAN", "iata": "MYE", "name": "三宅島",      "region": "関東",   "lat": 34.0733, "lon": 139.5600, "start_h": 8, "end_h": 17},
    {"icao": "RTHH", "iata": "HAC", "name": "八丈島",      "region": "関東",   "lat": 33.1150, "lon": 139.7869, "start_h": 7, "end_h": 18},
    {"icao": "RJAZ", "iata": "NII", "name": "新島",        "region": "関東",   "lat": 34.3703, "lon": 139.2708, "start_h": 8, "end_h": 17},
    {"icao": "RJAZ", "iata": "KMZ", "name": "神津島",      "region": "関東",   "lat": 34.1883, "lon": 139.1367, "start_h": 8, "end_h": 17},
    {"icao": "RJTF", "iata": "---", "name": "調布",        "region": "関東",   "lat": 35.6719, "lon": 139.5281, "start_h": 8, "end_h": 18},

    # --- 中部・北陸 ---
    {"icao": "RJGG", "iata": "NGO", "name": "中部国際",    "region": "中部",   "lat": 34.8584, "lon": 136.8054, "start_h": 0, "end_h": 24},
    {"icao": "RJNA", "iata": "NKM", "name": "名古屋/小牧",  "region": "中部",   "lat": 35.2550, "lon": 136.9244, "start_h": 7, "end_h": 22},
    {"icao": "RJSN", "iata": "KIJ", "name": "新潟",        "region": "中部",   "lat": 37.9558, "lon": 139.1206, "start_h": 7, "end_h": 20},
    {"icao": "RJNT", "iata": "TOY", "name": "富山",        "region": "中部",   "lat": 36.6483, "lon": 137.1875, "start_h": 7, "end_h": 21},
    {"icao": "RJNK", "iata": "KMQ", "name": "小松",        "region": "中部",   "lat": 36.3947, "lon": 136.4075, "start_h": 7, "end_h": 21},
    {"icao": "RJNW", "iata": "NTQ", "name": "のと",        "region": "中部",   "lat": 37.2931, "lon": 136.9600, "start_h": 8, "end_h": 19},
    {"icao": "RJNS", "iata": "FSZ", "name": "静岡",        "region": "中部",   "lat": 34.7961, "lon": 138.1894, "start_h": 7, "end_h": 22},
    {"icao": "RJAF", "iata": "MMJ", "name": "松本",        "region": "中部",   "lat": 36.1667, "lon": 137.9228, "start_h": 8, "end_h": 18},

    # --- 近畿 ---
    {"icao": "RJOO", "iata": "ITM", "name": "大阪/伊丹",    "region": "近畿",   "lat": 34.7855, "lon": 135.4382, "start_h": 7, "end_h": 21},
    {"icao": "RJBB", "iata": "KIX", "name": "関西国際",    "region": "近畿",   "lat": 34.4347, "lon": 135.2440, "start_h": 0, "end_h": 24},
    {"icao": "RJBE", "iata": "UKB", "name": "神戸",        "region": "近畿",   "lat": 34.6328, "lon": 135.2239, "start_h": 7, "end_h": 23},
    {"icao": "RJBD", "iata": "SHM", "name": "南紀白浜",    "region": "近畿",   "lat": 33.6622, "lon": 135.3619, "start_h": 7, "end_h": 20},
    {"icao": "RJBT", "iata": "TJH", "name": "コウノトリ但馬","region": "近畿",   "lat": 35.5133, "lon": 134.7869, "start_h": 8, "end_h": 18},

    # --- 中国 ---
    {"icao": "RJOA", "iata": "HIJ", "name": "広島",        "region": "中国",   "lat": 34.4361, "lon": 132.9194, "start_h": 7, "end_h": 21},
    {"icao": "RJOB", "iata": "OKJ", "name": "岡山",        "region": "中国",   "lat": 34.7569, "lon": 133.8553, "start_h": 7, "end_h": 21},
    {"icao": "RJDC", "iata": "UBJ", "name": "山口宇部",    "region": "中国",   "lat": 33.9300, "lon": 131.2789, "start_h": 7, "end_h": 21},
    {"icao": "RJOI", "iata": "IWK", "name": "岩国",        "region": "中国",   "lat": 34.1439, "lon": 132.2356, "start_h": 7, "end_h": 21},
    {"icao": "RJOT", "iata": "TTJ", "name": "鳥取砂丘コナン","region": "中国", "lat": 35.5300, "lon": 134.1664, "start_h": 7, "end_h": 21},
    {"icao": "RJOZ", "iata": "YGJ", "name": "米子鬼太郎",  "region": "中国",   "lat": 35.4922, "lon": 133.2364, "start_h": 7, "end_h": 21},
    {"icao": "RJOC", "iata": "IZO", "name": "出雲",        "region": "中国",   "lat": 35.4136, "lon": 132.8897, "start_h": 7, "end_h": 21},
    {"icao": "RJOH", "iata": "IWJ", "name": "萩・石見",    "region": "中国",   "lat": 34.6769, "lon": 131.7900, "start_h": 8, "end_h": 19},
    {"icao": "RJNO", "iata": "OKI", "name": "隠岐",        "region": "中国",   "lat": 36.1811, "lon": 133.3247, "start_h": 8, "end_h": 18},

    # --- 四国 ---
    {"icao": "RJOT", "iata": "TAK", "name": "高松",        "region": "四国",   "lat": 34.2142, "lon": 134.0156, "start_h": 7, "end_h": 21},
    {"icao": "RJOM", "iata": "MYJ", "name": "松山",        "region": "四国",   "lat": 33.8272, "lon": 132.6997, "start_h": 7, "end_h": 21},
    {"icao": "RJOK", "iata": "KCZ", "name": "高知龍馬",    "region": "四国",   "lat": 33.5461, "lon": 133.6694, "start_h": 7, "end_h": 21},
    {"icao": "RJOS", "iata": "TKS", "name": "徳島阿波おどり","region": "四国", "lat": 34.1328, "lon": 134.6067, "start_h": 7, "end_h": 21},

    # --- 九州 ---
    {"icao": "RJFF", "iata": "FUK", "name": "福岡",        "region": "九州",   "lat": 33.5859, "lon": 130.4507, "start_h": 7, "end_h": 22},
    {"icao": "RJFR", "iata": "KKJ", "name": "北九州",      "region": "九州",   "lat": 33.8456, "lon": 131.0347, "start_h": 0, "end_h": 24},
    {"icao": "RJFS", "iata": "HSG", "name": "佐賀",        "region": "九州",   "lat": 33.1497, "lon": 130.3022, "start_h": 7, "end_h": 22},
    {"icao": "RJFU", "iata": "NGS", "name": "長崎",        "region": "九州",   "lat": 32.9169, "lon": 129.9136, "start_h": 7, "end_h": 22},
    {"icao": "RJFT", "iata": "KMJ", "name": "阿蘇くまもと","region": "九州",   "lat": 32.8372, "lon": 130.8569, "start_h": 7, "end_h": 21},
    {"icao": "RJFO", "iata": "OIT", "name": "大分",        "region": "九州",   "lat": 33.4794, "lon": 131.7372, "start_h": 7, "end_h": 21},
    {"icao": "RJFM", "iata": "KMI", "name": "宮崎ブーゲンビリア","region": "九州","lat": 31.8772, "lon": 131.4486, "start_h": 7, "end_h": 21},
    {"icao": "RJFK", "iata": "KOJ", "name": "鹿児島",      "region": "九州",   "lat": 31.8034, "lon": 130.7194, "start_h": 7, "end_h": 21},
    {"icao": "RJFE", "iata": "FUJ", "name": "五島福江",    "region": "九州",   "lat": 32.6664, "lon": 128.8331, "start_h": 8, "end_h": 19},
    {"icao": "RJDT", "iata": "TSJ", "name": "対馬",        "region": "九州",   "lat": 34.2967, "lon": 129.3308, "start_h": 8, "end_h": 19},
    {"icao": "RJDA", "iata": "IKI", "name": "壱岐",        "region": "九州",   "lat": 33.7489, "lon": 129.7850, "start_h": 8, "end_h": 18},
    {"icao": "RJDO", "iata": "---", "name": "上五島",      "region": "九州",   "lat": 32.9961, "lon": 129.1969, "start_h": 8, "end_h": 17},
    {"icao": "RJKA", "iata": "ASJ", "name": "奄美",        "region": "九州",   "lat": 28.4306, "lon": 129.7125, "start_h": 8, "end_h": 19},
    {"icao": "RJKN", "iata": "TKN", "name": "徳之島",      "region": "九州",   "lat": 27.8364, "lon": 128.8808, "start_h": 8, "end_h": 19},
    {"icao": "RJKB", "iata": "OKE", "name": "沖永良部",    "region": "九州",   "lat": 27.4361, "lon": 128.7014, "start_h": 8, "end_h": 19},
    {"icao": "RORY", "iata": "RNJ", "name": "与論",        "region": "九州",   "lat": 27.0439, "lon": 128.4017, "start_h": 8, "end_h": 19},
    {"icao": "RJFG", "iata": "TNE", "name": "種子島",      "region": "九州",   "lat": 30.6094, "lon": 130.9575, "start_h": 8, "end_h": 19},
    {"icao": "RJFC", "iata": "KUM", "name": "屋久島",      "region": "九州",   "lat": 30.3853, "lon": 130.6589, "start_h": 8, "end_h": 19},
    {"icao": "RJKI", "iata": "KKX", "name": "喜界",        "region": "九州",   "lat": 28.3194, "lon": 129.9281, "start_h": 8, "end_h": 18},

    # --- 沖縄 ---
    {"icao": "ROAH", "iata": "OKA", "name": "那覇",        "region": "沖縄",   "lat": 26.1958, "lon": 127.6458, "start_h": 0, "end_h": 24},
    {"icao": "ROIG", "iata": "ISG", "name": "新石垣",      "region": "沖縄",   "lat": 24.3964, "lon": 124.2450, "start_h": 7, "end_h": 21},
    {"icao": "ROMY", "iata": "MMY", "name": "宮古",        "region": "沖縄",   "lat": 24.7828, "lon": 125.2950, "start_h": 7, "end_h": 21},
    {"icao": "RORS", "iata": "SHI", "name": "下地島",      "region": "沖縄",   "lat": 24.8267, "lon": 125.1444, "start_h": 7, "end_h": 21},
    {"icao": "RORE", "iata": "IEJ", "name": "伊江島",      "region": "沖縄",   "lat": 26.7214, "lon": 127.7853, "start_h": 8, "end_h": 18},
    {"icao": "ROKJ", "iata": "UEO", "name": "久米島",      "region": "沖縄",   "lat": 26.3639, "lon": 126.7136, "start_h": 8, "end_h": 19},
    {"icao": "ROKR", "iata": "KJP", "name": "慶良間",      "region": "沖縄",   "lat": 26.1681, "lon": 127.2933, "start_h": 8, "end_h": 18},
    {"icao": "ROAG", "iata": "AGJ", "name": "粟国",        "region": "沖縄",   "lat": 26.5919, "lon": 127.2403, "start_h": 8, "end_h": 18},
    {"icao": "ROTD", "iata": "TRA", "name": "多良間",      "region": "沖縄",   "lat": 24.6533, "lon": 124.6750, "start_h": 8, "end_h": 18},
    {"icao": "ROYN", "iata": "OGN", "name": "与那国",      "region": "沖縄",   "lat": 24.4672, "lon": 122.9781, "start_h": 8, "end_h": 19},
    {"icao": "RKNM", "iata": "MMD", "name": "南大東",      "region": "沖縄",   "lat": 25.8467, "lon": 131.2639, "start_h": 8, "end_h": 18},
    {"icao": "RKMD", "iata": "KTD", "name": "北大東",      "region": "沖縄",   "lat": 25.9469, "lon": 131.3267, "start_h": 8, "end_h": 18},
    {"icao": "ROHT", "iata": "HTR", "name": "波照間",      "region": "沖縄",   "lat": 24.0592, "lon": 123.7997, "start_h": 8, "end_h": 18},
]

ICAO_TO_IATA = {}
for ap in AIRPORT_MASTER:
    if ap["iata"] != "---":
        ICAO_TO_IATA[ap["icao"]] = ap["iata"]
        ICAO_TO_IATA[ap["iata"]] = ap["iata"]

# 海外主要空港の3レター変換
ICAO_TO_IATA.update({
    "RKSI": "ICN", "RKSS": "GMP", "RKPK": "PUS", "RKPC": "CJU",
    "RCTP": "TPE", "RCSS": "TSA", "RCKH": "KHH", "VHHH": "HKG", "VMMC": "MFM",
    "ZSPD": "PVG", "ZSSS": "SHA", "ZBAA": "PEK", "ZBAD": "PKX", "ZGGG": "CAN", "ZGSZ": "SZX",
    "WSSS": "SIN", "VTBS": "BKK", "VTBD": "DMK", "WMKK": "KUL", "RPLL": "MNL",
    "VVNB": "HAN", "VVTS": "SGN", "WIII": "CGK", "VIDP": "DEL",
    "YSSY": "SYD", "YMML": "MEL", "YBBN": "BNE", "PHNL": "HNL", "PGUM": "GUM",
    "KSFO": "SFO", "KLAX": "LAX", "KSEA": "SEA", "KORD": "ORD", "KJFK": "JFK",
    "KEWR": "EWR", "KIAD": "IAD", "KDFW": "DFW", "KIAH": "IAH", "KATL": "ATL",
    "EGLL": "LHR", "LFPG": "CDG", "EDDF": "FRA", "EDDM": "MUC", "EHAM": "AMS",
    "EFHK": "HEL", "LIRF": "FCO", "LSZH": "ZRH", "LOWW": "VIE", "OMDB": "DXB", "OTHH": "DOH"
})

AIRLINE_DATA = {
    "ANA": {"name": "ANA (全日空)", "code": "ANA", "color": "#001e62"},
    "NH":  {"name": "ANA (全日空)", "code": "ANA", "color": "#001e62"},
    "AJX": {"name": "Air Japan", "code": "AJX", "color": "#001e62"},
    "AKX": {"name": "ANAウイングス", "code": "AKX", "color": "#001e62"},
    "JAL": {"name": "JAL (日本航空)", "code": "JAL", "color": "#cc0000"},
    "JL":  {"name": "JAL (日本航空)", "code": "JAL", "color": "#cc0000"},
    "JAC": {"name": "日本エアコミューター", "code": "JAC", "color": "#059669"},
    "JTA": {"name": "日本トランスオーシャン", "code": "JTA", "color": "#cc0000"},
    "RAC": {"name": "琉球エアーコミューター", "code": "RAC", "color": "#cc0000"},
    "SKY": {"name": "スカイマーク", "code": "SKY", "color": "#002b49"},
    "BC":  {"name": "スカイマーク", "code": "SKY", "color": "#002b49"},
    "APJ": {"name": "Peach", "code": "APJ", "color": "#ff66b2"},
    "MM":  {"name": "Peach", "code": "APJ", "color": "#ff66b2"},
    "JJP": {"name": "Jetstar", "code": "JJP", "color": "#ff6600"},
    "GK":  {"name": "Jetstar", "code": "JJP", "color": "#ff6600"},
    "SFJ": {"name": "スターフライヤー", "code": "SFJ", "color": "#111827"},
    "ADO": {"name": "AIRDO", "code": "ADO", "color": "#ffd400"},
    "SNA": {"name": "ソラシドエア", "code": "SNA", "color": "#008a45"},
    "FDA": {"name": "FDA", "code": "FDA", "color": "#b91c1c"},
    "IBX": {"name": "IBEX", "code": "IBX", "color": "#1d4ed8"},
    "AMX": {"name": "天草エアライン", "code": "AMX", "color": "#db2777"},
    "ORC": {"name": "オリエンタルエアブリッジ", "code": "ORC", "color": "#0284c7"},
    "NTH": {"name": "トキエア", "code": "BV", "color": "#dc2626"},
    "SJO": {"name": "スプリング・ジャパン", "code": "IJ", "color": "#059669"},
}

AIRCRAFT_MAP = {
    "B788": "Boeing 787-8", "B789": "Boeing 787-9", "B78X": "Boeing 787-10",
    "B772": "Boeing 777-200", "B773": "Boeing 777-300", "B77W": "Boeing 777-300ER",
    "B763": "Boeing 767-300", "B738": "Boeing 737-800", "B737": "Boeing 737-700",
    "B38M": "Boeing 737 MAX 8", "A359": "Airbus A350-900", "A35K": "Airbus A350-1000",
    "A320": "Airbus A320", "A20N": "Airbus A320neo", "A321": "Airbus A321",
    "A21N": "Airbus A321neo", "A333": "Airbus A330-300", "E190": "Embraer 190",
    "E170": "Embraer 170", "DH8D": "DHC-8-400", "AT76": "ATR 72-600", "AT46": "ATR 42-600"
}

COMPASS_MAP = {
    "N": "北", "NE": "北東", "E": "東", "SE": "南東",
    "S": "南", "SW": "南西", "W": "西", "NW": "北西"
}

GROUND_VEHICLE_PREFIXES = ("DENKI", "CAR", "TUG", "TOW", "BUS", "FIRE", "FOLLOW", "OPS", "MNT", "FUEL", "GND", "TEST", "0000")

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
    alt_m = alt_ft * 0.3048
    return distance_km, bearing_deg, alt_m

def deg_to_compass_code(deg: float) -> str:
    codes = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return codes[int((deg + 22.5) % 360 // 45)]

def find_nearest_airport(lat: float, lon: float) -> Tuple[Dict, float]:
    nearest = AIRPORT_MASTER[0]
    min_dist = float('inf')
    for ap in AIRPORT_MASTER:
        d, _, _ = calc_geo_metrics(lat, lon, ap["lat"], ap["lon"])
        if d < min_dist:
            min_dist = d
            nearest = ap
    return nearest, min_dist

def to_3letter(code: Optional[str]) -> Optional[str]:
    if not code: return None
    c = str(code).strip().upper()
    if c in ICAO_TO_IATA: return ICAO_TO_IATA[c]
    if len(c) == 3 and c.isalpha(): return c
    return None

class MultiUserRouteResolver:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})
        self.route_cache: Dict[str, Optional[Tuple[str, Optional[str], Optional[str]]]] = {}
        self.cache_timestamps: Dict[str, float] = {}

    def lookup_external_api(self, callsign: str) -> Optional[Tuple[str, Optional[str], Optional[str]]]:
        now = time.time()
        if callsign in self.route_cache and (now - self.cache_timestamps.get(callsign, 0)) < 3600:
            return self.route_cache[callsign]

        try:
            r1 = self.session.get(f"https://api.adsbdb.com/v0/callsign/{callsign}", timeout=1.2)
            if r1.status_code == 200:
                fr = r1.json().get("response", {}).get("flightroute", {})
                if fr:
                    o = fr.get("origin", {}).get("iata_code") or to_3letter(fr.get("origin", {}).get("icao_code"))
                    d = fr.get("destination", {}).get("iata_code") or to_3letter(fr.get("destination", {}).get("icao_code"))
                    if o and d:
                        res = (f"{o} > {d}", o, d)
                        self.route_cache[callsign] = res
                        self.cache_timestamps[callsign] = now
                        return res
        except Exception:
            pass

        self.route_cache[callsign] = None
        self.cache_timestamps[callsign] = now - 3000
        return None

    def resolve(self, callsign: str, raw_orig: str, raw_dest: str, lat: float, lon: float, alt_ft: int, vert_rate: int, track: Optional[float], target_ap: Dict) -> Tuple[str, bool]:
        target_iata = target_ap["iata"]
        target_icao = target_ap["icao"]

        o = to_3letter(raw_orig)
        d = to_3letter(raw_dest)
        if o and d:
            is_target = (o == target_iata or d == target_iata or raw_orig == target_icao or raw_dest == target_icao)
            return f"{o} > {d}", is_target

        api_res = self.lookup_external_api(callsign)
        if api_res:
            route_str, o_api, d_api = api_res
            is_target = (o_api == target_iata or d_api == target_iata)
            return route_str, is_target

        d_ap, b_ap, _ = calc_geo_metrics(lat, lon, target_ap["lat"], target_ap["lon"], alt_ft)
        heading = deg_to_compass_code(track) if track is not None else "---"
        towards_ap = (track is not None and abs((b_ap - track + 180) % 360 - 180) <= 50)

        if d_ap <= 25.0 and alt_ft <= 8000 and (vert_rate < -150 or towards_ap):
            return f"APPR > {target_iata}", True

        if d_ap <= 20.0 and alt_ft <= 10000 and vert_rate > 150:
            return f"{target_iata} > {heading}", True

        if track is not None:
            return f"PASS > {heading}", False
        return "OVER > FLY", False

resolver = MultiUserRouteResolver()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/manifest.json")
async def manifest():
    return JSONResponse({
        "name": "Live Flight Monitor",
        "short_name": "FlightMonitor",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#030712",
        "theme_color": "#030712",
        "icons": [{"src": "/icon.svg", "sizes": "192x192 512x512", "type": "image/svg+xml"}]
    })

@app.get("/icon.svg")
async def icon():
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
        <rect width="512" height="512" rx="100" fill="#0b0f19" stroke="#fbbf24" stroke-width="12"/>
        <path d="M256,120 L274,210 L370,250 L274,275 L280,350 L256,335 L232,350 L238,275 L142,250 L238,210 Z" fill="#fbbf24"/>
        <circle cx="256" cy="256" r="10" fill="#10b981"/>
    </svg>"""
    return Response(content=svg, media_type="image/svg+xml")

@app.get("/api/flights")
async def api_flights(
    lat: float = 34.8268,
    lon: float = 135.4292,
    bearings: Optional[str] = None
):
    target_ap, ap_dist = find_nearest_airport(lat, lon)
    now = datetime.now()
    is_open = target_ap["start_h"] <= now.hour < target_ap["end_h"] if target_ap["start_h"] != target_ap["end_h"] else True

    visible_bearings = [b.strip().upper() for b in bearings.split(",")] if bearings else []

    urls = [
        f"https://api.airplanes.live/v2/point/{lat:.4f}/{lon:.4f}/{SEARCH_RADIUS_NM}",
        f"https://api.adsb.lol/v2/point/{lat:.4f}/{lon:.4f}/{SEARCH_RADIUS_NM}",
    ]
    raw_list = None
    for u in urls:
        try:
            r = requests.get(u, timeout=3.5)
            if r.status_code == 200:
                raw_list = r.json().get("ac") or r.json().get("aircraft")
                if raw_list is not None: break
        except Exception:
            pass

    if raw_list is None:
        return {"window_flights": [], "other_flights": [], "provider": "Reconnecting", "airport": target_ap, "is_business_hours": is_open}

    window_flights = []
    other_flights = []

    for raw in raw_list:
        a_lat, a_lon = raw.get("lat"), raw.get("lon")
        if a_lat is None or a_lon is None: continue

        alt = 0 if (raw.get("alt_baro") in ("ground", None)) else int(raw.get("alt_baro"))
        gs = int(raw.get("gs") or 0)
        cs = str(raw.get("flight") or raw.get("r") or "").strip().upper()

        if not cs or any(cs.startswith(p) for p in GROUND_VEHICLE_PREFIXES) or alt <= 50 or gs < 45:
            continue

        vr = int(raw.get("vert_rate") or 0)
        tr = float(raw["track"]) if raw.get("track") is not None else None
        dist, bearing, _ = calc_geo_metrics(lat, lon, a_lat, a_lon, alt)
        compass_code = deg_to_compass_code(bearing)

        route, is_target_airport_flight = resolver.resolve(cs, str(raw.get("orig") or ""), str(raw.get("dest") or ""), a_lat, a_lon, alt, vr, tr, target_ap)

        prefix = cs[:3] if len(cs) >= 3 else cs[:2]
        airline = AIRLINE_DATA.get(prefix, {"name": "民間機", "code": prefix, "color": "#475569"})
        model = AIRCRAFT_MAP.get(raw.get("t", ""), raw.get("t") or "Aircraft")

        flight_obj = {
            "callsign": cs,
            "airline": airline["name"],
            "airline_code": airline["code"],
            "airline_color": airline["color"],
            "route": route,
            "phase": "TAKEOFF / CLIMB" if (alt <= 4000 and vr > 150) else ("APPROACH" if alt <= 5000 and vr < -150 else "CRUISE"),
            "model": model,
            "alt": alt,
            "vr": vr,
            "gs": gs,
            "distance": round(dist, 1),
            "compass": COMPASS_MAP.get(compass_code, compass_code),
            "bearing": bearing
        }

        in_bearing = (not visible_bearings) or (compass_code in visible_bearings)

        if is_target_airport_flight and in_bearing:
            window_flights.append(flight_obj)
        else:
            other_flights.append(flight_obj)

    window_flights.sort(key=lambda x: x["distance"])
    other_flights.sort(key=lambda x: x["distance"])

    limited_other_flights = other_flights[:10]

    return {
        "window_flights": window_flights,
        "other_flights": limited_other_flights,
        "provider": "Online ADS-B",
        "airport": target_ap,
        "is_business_hours": is_open
    }

@app.get("/", response_class=HTMLResponse)
async def index():
    # 地方別にグルーピングしたHTML <optgroup> を構築
    regions = ["北海道", "東北", "関東", "中部", "近畿", "中国", "四国", "九州", "沖縄"]
    opt_groups = []
    for reg in regions:
        group_aps = [ap for ap in AIRPORT_MASTER if ap["region"] == reg]
        opts = "".join([f'<option value="{ap["lat"]},{ap["lon"]}">{ap["name"]} ({ap["iata"]})</option>' for ap in group_aps])
        opt_groups.append(f'<optgroup label="--- {reg} ---">{opts}</optgroup>')
    
    ap_options = "".join(opt_groups)
    
    return f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <link rel="manifest" href="/manifest.json">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <title>LIVE FLIGHT BOARD</title>
    <style>
        body {{
            background-color: #030712; color: #f1f5f9;
            font-family: -apple-system, BlinkMacSystemFont, 'Courier New', monospace;
            margin: 0; padding: env(safe-area-inset-top, 10px) 12px env(safe-area-inset-bottom, 10px) 12px;
            height: 100vh; box-sizing: border-box; overflow: hidden; display: flex; flex-direction: column;
        }}
        header {{
            display: flex; justify-content: space-between; align-items: center;
            border-bottom: 2px solid #1f2937; padding-bottom: 8px; margin-bottom: 12px; flex-shrink: 0;
        }}
        .controls {{ display: flex; gap: 8px; align-items: center; }}
        select, button {{
            background: #111827; color: #38bdf8; border: 1px solid #374151;
            padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; cursor: pointer;
        }}
        button:hover {{ background: #1f2937; }}
        optgroup {{ background: #030712; color: #fbbf24; font-weight: bold; }}
        option {{ background: #111827; color: #f1f5f9; }}
        .main-layout {{
            display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(320px, 1fr);
            gap: 16px; flex-grow: 1; min-height: 0;
        }}
        @media (max-width: 900px) {{
            .main-layout {{ grid-template-columns: 1fr; overflow-y: auto; }}
            body {{ overflow-y: auto; height: auto; }}
        }}
        .left-col {{ display: flex; flex-direction: column; gap: 12px; min-height: 0; overflow-y: auto; }}
        .right-col {{ display: flex; flex-direction: column; gap: 12px; min-height: 0; }}
        .card {{
            background: #0b0f19; border: 2px solid #d97706; border-radius: 6px;
            padding: 12px 16px; flex-shrink: 0;
        }}
        .splitflap {{
            display: inline-flex; gap: 3px; background: #000; padding: 6px 8px;
            border-radius: 4px; border: 1px solid #262626; margin: 6px 0;
        }}
        .char {{
            width: 22px; height: 38px; background: #141414; color: #fbbf24;
            font-size: 22px; font-weight: bold; text-align: center; line-height: 38px; border-radius: 3px;
        }}
        .grid {{
            display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px;
            background: #000; padding: 6px 10px; border-radius: 4px; margin-top: 6px; font-size: 11px; text-align: center;
        }}
        .radar-box {{
            background: #0b0f19; border: 2px solid #1f2937; border-radius: 6px; padding: 12px;
            display: flex; flex-direction: column; align-items: center; flex-shrink: 0;
        }}
        .radar {{
            width: 80%; max-width: 320px; min-width: 220px; aspect-ratio: 1/1;
            background: #020617; border: 2px solid #1f2937; border-radius: 50%; position: relative;
        }}
        .r-h {{ position: absolute; top: 50%; left: 0; right: 0; height: 1px; background: #1f2937; }}
        .r-v {{ position: absolute; left: 50%; top: 0; bottom: 0; width: 1px; background: #1f2937; }}
        .r-c {{ position: absolute; top: 50%; left: 50%; width: 6px; height: 6px; background: #10b981; border-radius: 50%; transform: translate(-50%,-50%); box-shadow: 0 0 6px #10b981; }}
        .r-ring1 {{ position: absolute; top: 25%; left: 25%; right: 25%; bottom: 25%; border: 1px dashed #1f2937; border-radius: 50%; }}
        .blip {{ position: absolute; width: 10px; height: 10px; background: #fbbf24; border-radius: 50%; transform: translate(-50%,-50%); box-shadow: 0 0 6px #fbbf24; }}
        .blip.other {{ background: #94a3b8; width: 8px; height: 8px; box-shadow: none; }}
        .blip-lbl {{
            position: absolute; font-size: 10px; color: #38bdf8; background: rgba(2,6,23,0.85);
            padding: 1px 4px; border-radius: 2px; transform: translate(6px,-8px); white-space: nowrap; border: 1px solid #1f2937;
        }}

        #coord-modal {{
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background: rgba(0, 0, 0, 0.85); display: flex; align-items: center; justify-content: center;
            z-index: 9999; backdrop-filter: blur(4px);
        }}
        .modal-card {{
            background: #0b0f19; border: 2px solid #fbbf24; border-radius: 8px;
            padding: 24px; width: 90%; max-width: 440px; box-shadow: 0 0 25px rgba(251, 191, 36, 0.3);
        }}
        .form-group {{ margin-bottom: 12px; }}
        .form-group label {{ display: block; font-size: 11px; color: #9ca3af; margin-bottom: 4px; }}
        .form-group input {{
            width: 100%; background: #111827; border: 1px solid #374151; color: #fbbf24;
            padding: 8px; border-radius: 4px; font-size: 14px; box-sizing: border-box;
        }}
        .modal-actions {{ display: flex; gap: 8px; margin-top: 18px; }}
        .btn-primary {{
            flex: 1; background: #fbbf24; color: #000; font-weight: bold; padding: 10px;
            border: none; border-radius: 4px; cursor: pointer; font-size: 13px;
        }}
        .btn-secondary {{
            background: #1f2937; color: #38bdf8; border: 1px solid #374151; padding: 10px;
            border-radius: 4px; cursor: pointer; font-size: 12px;
        }}
    </style>
</head>
<body>
    <div id="coord-modal" style="display:none;">
        <div class="modal-card">
            <h2 style="margin:0 0 12px 0; font-size:16px; color:#fbbf24; letter-spacing:1px;">📍 監視拠点の座標設定</h2>
            <div style="font-size:11px; color:#9ca3af; margin-bottom:14px; line-height:1.4;">
                ご自宅等の緯度・経度を入力すると、全国85空港の中から最寄り空港の発着便を自動判定してメインモニターに追尾表示します。
            </div>
            
            <div class="form-group">
                <label>緯度 (Latitude):</label>
                <input type="number" step="any" id="modal-lat" placeholder="例: 35.6812">
            </div>
            <div class="form-group">
                <label>経度 (Longitude):</label>
                <input type="number" step="any" id="modal-lon" placeholder="例: 139.7671">
            </div>
            <div class="form-group">
                <label>窓の視界方角 (任意・カンマ区切り):</label>
                <input type="text" id="modal-bearings" placeholder="例: SE,S,SW (空欄で全方位)">
            </div>

            <div class="modal-actions">
                <button class="btn-secondary" onclick="useGpsInModal()">📍 GPS取得</button>
                <button class="btn-primary" onclick="saveCoordinates()">設定して開始</button>
            </div>
        </div>
    </div>

    <header>
        <div style="display:flex; align-items:center; gap:8px;">
            <div style="width:10px; height:10px; background:#10b981; border-radius:50%; box-shadow:0 0 8px #10b981;"></div>
            <h1 id="header-title" style="margin:0; font-size:18px; color:#fbbf24;">FLIGHT MONITOR</h1>
        </div>
        <div class="controls">
            <button onclick="openConfigModal()">⚙ 座標設定</button>
            <select id="airport-select" onchange="onSelectAirport(this.value)">
                <option value="">主要空港を選択 (全85空港)</option>
                {ap_options}
            </select>
            <div id="clock" style="font-size:16px; color:#fbbf24; font-weight:bold;">--:--:--</div>
        </div>
    </header>

    <div class="main-layout">
        <div id="board" class="left-col">
            <div style="text-align:center; padding:40px; color:#6b7280;">空域情報を取得中...</div>
        </div>
        <div class="right-col">
            <div class="radar-box">
                <div style="font-size:11px; color:#38bdf8; font-weight:bold; margin-bottom:8px;">📡 ターミナルレーダー (15NM)</div>
                <div class="radar" id="radar">
                    <div class="r-h"></div><div class="r-v"></div><div class="r-ring1"></div><div class="r-c" title="現在地"></div>
                </div>
                <div style="font-size:9px; color:#6b7280; text-align:center; margin-top:8px; letter-spacing:0.5px;">
                    緑＝現在地 / 黄＝当該空港発着機 / 灰＝周辺・他空港機
                </div>
            </div>
            <div style="background:#0b0f19; border:2px solid #1f2937; border-radius:6px; padding:10px; flex-grow:1; min-height:0; overflow-y:auto;" id="other-panel">
                <div style="font-size:11px; color:#9ca3af; font-weight:bold; margin-bottom:6px; border-bottom:1px solid #1f2937; padding-bottom:4px;">
                    ✈ 周辺機・通過機 近い順 (<span id="other-count">0</span>/10機)
                </div>
                <div id="other-list"></div>
            </div>
        </div>
    </div>

    <script>
        let currentLat = localStorage.getItem('lat');
        let currentLon = localStorage.getItem('lon');
        let currentBearings = localStorage.getItem('bearings') || '';

        setInterval(() => {{
            document.getElementById('clock').innerText = new Date().toTimeString().split(' ')[0];
        }}, 1000);

        window.addEventListener('DOMContentLoaded', () => {{
            if (!currentLat || !currentLon) {{
                openConfigModal();
            }} else {{
                currentLat = parseFloat(currentLat);
                currentLon = parseFloat(currentLon);
                update();
            }}
        }});

        function openConfigModal() {{
            document.getElementById('modal-lat').value = currentLat || '';
            document.getElementById('modal-lon').value = currentLon || '';
            document.getElementById('modal-bearings').value = currentBearings || '';
            document.getElementById('coord-modal').style.display = 'flex';
        }}

        function useGpsInModal() {{
            if (navigator.geolocation) {{
                navigator.geolocation.getCurrentPosition((pos) => {{
                    document.getElementById('modal-lat').value = pos.coords.latitude.toFixed(4);
                    document.getElementById('modal-lon').value = pos.coords.longitude.toFixed(4);
                }}, () => alert('位置情報の取得が許可されませんでした。'));
            }}
        }}

        function saveCoordinates() {{
            let latVal = parseFloat(document.getElementById('modal-lat').value);
            let lonVal = parseFloat(document.getElementById('modal-lon').value);
            let bearingsVal = document.getElementById('modal-bearings').value.trim();

            if (isNaN(latVal) || isNaN(lonVal)) {{
                alert('緯度と経度を正しく入力してください。');
                return;
            }}

            currentLat = latVal;
            currentLon = lonVal;
            currentBearings = bearingsVal;

            localStorage.setItem('lat', currentLat);
            localStorage.setItem('lon', currentLon);
            localStorage.setItem('bearings', currentBearings);

            document.getElementById('coord-modal').style.display = 'none';
            update();
        }}

        function onSelectAirport(val) {{
            if (!val) return;
            let parts = val.split(',');
            currentLat = parseFloat(parts[0]);
            currentLon = parseFloat(parts[1]);
            localStorage.setItem('lat', currentLat);
            localStorage.setItem('lon', currentLon);
            update();
        }}

        function renderFlap(txt) {{
            let p = txt.padEnd(12, ' ').slice(0, 12);
            let h = '<div class="splitflap">';
            for (let c of p) h += `<div class="char">${{c === ' ' ? '&nbsp;' : c}}</div>`;
            return h + '</div>';
        }}

        async function update() {{
            if (!currentLat || !currentLon) return;

            try {{
                let bParam = currentBearings ? `&bearings=${{encodeURIComponent(currentBearings)}}` : '';
                let res = await fetch(`/api/flights?lat=${{currentLat}}&lon=${{currentLon}}${{bParam}}&t=${{Date.now()}}`);
                let data = await res.json();

                document.getElementById('header-title').innerText = `${{data.airport.name}} (${{data.airport.iata}})`;

                let board = document.getElementById('board');
                let radar = document.getElementById('radar');
                radar.querySelectorAll('.blip, .blip-lbl').forEach(e => e.remove());

                // 周辺機描画（灰色）
                data.other_flights.forEach(f => {{
                    let r = Math.min(f.distance * 1.852 / 27.8, 0.9) * 50;
                    let rad = (f.bearing - 90) * (Math.PI / 180);
                    let x = 50 + r * Math.cos(rad);
                    let y = 50 + r * Math.sin(rad);

                    let b = document.createElement('div');
                    b.className = 'blip other';
                    b.style.left = `${{x}}%`; b.style.top = `${{y}}%`;
                    radar.appendChild(b);
                }});

                // メイン対象空港機描画（黄色 ＋ ラベル）
                data.window_flights.forEach(f => {{
                    let r = Math.min(f.distance * 1.852 / 27.8, 0.9) * 50;
                    let rad = (f.bearing - 90) * (Math.PI / 180);
                    let x = 50 + r * Math.cos(rad);
                    let y = 50 + r * Math.sin(rad);

                    let b = document.createElement('div');
                    b.className = 'blip';
                    b.style.left = `${{x}}%`; b.style.top = `${{y}}%`;
                    let l = document.createElement('div');
                    l.className = 'blip-lbl';
                    l.style.left = `${{x}}%`; l.style.top = `${{y}}%`;
                    l.innerHTML = `${{f.callsign}}<br>${{f.alt.toLocaleString()}}ft`;
                    radar.appendChild(b);
                    radar.appendChild(l);
                }});

                // メインモニターカード描画
                if (data.window_flights.length === 0) {{
                    board.innerHTML = `<div style="text-align:center; padding:40px; color:#6b7280; font-size:14px;">現在、視界内に【${{data.airport.name}} (${{data.airport.iata}})】発着の航空機はありません</div>`;
                }} else {{
                    board.innerHTML = data.window_flights.map(f => `
                        <div class="card">
                            <div style="display:flex; justify-content:space-between; font-size:11px; margin-bottom:4px;">
                                <span style="background:#111827; color:#38bdf8; padding:2px 6px; border-radius:3px;">${{f.phase}}</span>
                                <span style="color:#fbbf24; font-weight:bold;">${{f.callsign}} (${{f.airline}})</span>
                            </div>
                            ${{renderFlap(f.route)}}
                            <div class="grid">
                                <div><span style="color:#6b7280;">TYPE</span><br>${{f.model}}</div>
                                <div><span style="color:#6b7280;">ALT</span><br>${{f.alt.toLocaleString()}}ft</div>
                                <div><span style="color:#6b7280;">SPEED</span><br>${{f.gs}}kt</div>
                                <div><span style="color:#6b7280;">POS</span><br>${{f.compass}} / ${{f.distance}}km</div>
                            </div>
                        </div>
                    `).join('');
                }}

                // 周辺機リスト描画
                document.getElementById('other-count').innerText = data.other_flights.length;
                let oList = document.getElementById('other-list');
                if (data.other_flights.length === 0) {{
                    oList.innerHTML = '<div style="color:#6b7280; text-align:center; padding:10px; font-size:11px;">周辺機なし</div>';
                }} else {{
                    oList.innerHTML = data.other_flights.map(f => {{
                        let vrSign = f.vr > 0 ? "▲" : (f.vr < 0 ? "▼" : "―");
                        return `
                        <div style="background:#020617; border:1px solid #1f2937; border-radius:4px; padding:6px 8px; margin-bottom:5px; font-size:10px; display:flex; flex-direction:column; gap:2px;">
                            <div style="display:flex; justify-content:space-between;">
                                <span style="color:#f8fafc; font-weight:bold;">${{f.callsign}} (${{f.airline}})</span>
                                <span style="color:#e2e8f0; font-weight:bold;">${{f.distance}}km / ${{f.compass}}</span>
                            </div>
                            <div style="color:#38bdf8; font-size:11px; font-weight:bold;">✈ ${{f.route}}</div>
                            <div style="display:flex; justify-content:space-between; color:#9ca3af; font-size:9px;">
                                <span>TYPE: ${{f.model}}</span>
                                <span>ALT: ${{f.alt.toLocaleString()}} ft ${{vrSign}}</span>
                            </div>
                        </div>
                    `;
                    }}).join('');
                }}

            }} catch(e) {{
                console.error(e);
            }}
        }}

        setInterval(update, 4000);
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)