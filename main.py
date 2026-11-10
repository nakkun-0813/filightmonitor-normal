"""
main.py: アプリケーション起動エントリーポイント
"""

from pathlib import Path
from typing import List
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import uvicorn
from engine import UniversalFlightEngine

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="Universal Flight Board")
engine = UniversalFlightEngine()

@app.get("/", response_class=HTMLResponse)
async def setup(request: Request):
    return templates.TemplateResponse("setup.html", {"request": request})

@app.get("/board", response_class=HTMLResponse)
async def board(request: Request):
    return templates.TemplateResponse("board.html", {"request": request})

@app.get("/api/flights")
async def api_flights(lat: float = Query(...), lon: float = Query(...), bearings: str = Query("")):
    b_list = [b.strip() for b in bearings.split(",")] if bearings else []
    window_flights, other_flights, weather, apt_code, apt_name = await engine.update_flights(lat, lon, b_list)
    return {
        "window_flights": window_flights,
        "other_flights": other_flights,
        "weather": weather,
        "apt_code": apt_code,
        "apt_name": apt_name
    }

if __name__ == "__main__":
    print("=" * 65)
    print(" ✈️ Universal Flight Board (Localhost: 8001)")
    print(" 🌐 URL: http://localhost:8001")
    print("=" * 65)
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)