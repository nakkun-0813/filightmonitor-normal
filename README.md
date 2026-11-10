# ✈️ Universal Flight Board

自宅や現在地の上空を通過・離着陸する航空機を、空港のフライトインフォメーションボード（反転フラップ式案内表示機風）＋リアルタイムターミナルレーダーで可視化するWebダッシュボードです。

---

## 🌟 主な機能

- **🗾 日本全国の主要・地方・離島空港を自動判定**  
  入力した座標（またはGPS）から最寄りの空港を即座に計算し、その空港の発着便と上空通過便を判別して表示します。
- **📟 反転フラップ（ソラリーボード）風UI**  
  空港の発着案内板を再現したパタパタ動くアニメーションボード。便名、航空会社コード、飛行ルート、機種、高度、対地速度、方角を一覧表示。
- **📡 ターミナルレーダー表示**  
  観測地点（中心）から半径約15海里（約27.7km）以内の空域をスキャン。自機位置を起点とした方位・距離をグラフィカルにプロット。
- **⛅ ピンポイント気象情報連携**  
  Open-Meteo APIと連携し、観測地点の現在気温・天候・湿度・風向・風速をリアルタイム表示。
- **📍 ダッシュボード上からの座標ワープ**  
  画面上部の入力欄から緯度・経度を直接書き換えるだけで、全国どこでも観測地をシームレスに切り替え可能。
- **🎯 Sticky追跡ロジック**  
  ADS-Bの一時的な信号瞬断や方角境界の跨ぎによる機体のチラつき・消失を防止し、安定したモニタリングを維持。その場合”Hold”と表示されます。

---

## 📂 ディレクトリ構成

```text
universal-flight-board/
├── constants.py       # 空港マスタ、航空会社、機種などの定義
├── engine.py          # 幾何計算、気象・ADS-B取得、機体追跡エンジン
├── main.py            # FastAPIアプリケーションエントリーポイント
├── requirements.txt   # 依存ライブラリ一覧
├── templates/
│   ├── setup.html     # 初期座標設定画面
│   └── board.html     # フライトボード＆レーダー画面
└── README.md


🚀 クイックスタート
1. 必要要件
Python 3.9 以上

2. リポジトリのクローン
Bash
git clone https://github.com/nakkun-0813/filightmonitor-normal
.git
cd universal-flight-board

3. 仮想環境の作成とライブラリのインストール
Windows (PowerShell):

PowerShell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
macOS / Linux:

Bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
4. サーバーの起動
Bash
python main.py
5. ブラウザでアクセス
ブラウザで以下のURLを開きます。

初期設定画面: http://localhost:8001/

ボード直通（例: 伊丹周辺）: http://localhost:8001/board?lat=34.7855&lon=135.4382

📡 使用データソース・API
ADS-B ライブフライトデータ: airplanes.live / adsb.lol
ルート情報: adsbdb.com
気象データ: Open-Meteo

📄 ライセンス
MIT License