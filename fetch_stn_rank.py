import os
import sys
import requests
import json
import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# ==========================================
# 接收 8 碼單一參數 (例如: 20260614)
# ==========================================
if len(sys.argv) > 1 and len(sys.argv[1]) == 8:
    date_input = sys.argv[1] # 接收 GitHub Actions 傳來的 8 碼字串
    Y = date_input[0:4]
    M = date_input[4:6]
    D = date_input[6:8]
else:
    # 手動在本地端測試時的預設值
    Y, M, D = "2026", "06", "14"

API_TOKEN = "CWB-B1034BF8-0855-45E6-8F10-7C7D4DB194AA"
OUTPUT_DIR = f"stn_archives/{Y}{M}{D}"
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 80)
print(f"觀測站歷史觀測數據下載 ➔ 目標日期：{Y}-{M}-{D}")
print(f"輸出路徑: {OUTPUT_DIR}")
print("=" * 80)

raw_data_records = []

# ==========================================
# 逐時 10:00 - 19:00 氣象站 XML 下載與解析
# ==========================================
dt_10_18 = datetime(int(Y), int(M), int(D), 10, 0, 0)
end_10_18 = datetime(int(Y), int(M), int(D), 19, 0, 0)

NS = "{urn:cwa:gov:tw:cwacommon:0.1}"

while dt_10_18 <= end_10_18:
    hh = dt_10_18.strftime("%H")
    
    url = f"https://opendata.cwa.gov.tw/historyapi/v1/getData/O-A0001-001/{Y}/{M}/{D}/{hh}/00/00?Authorization={API_TOKEN}&format=XML"
    
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            stations = root.findall(f".//{NS}Station")
            
            for st in stations:
                lat = None; lon = None  # WGS84
                
                coordinates_list = st.findall(f"./{NS}GeoInfo/{NS}Coordinates")
                for coord in coordinates_list:
                    coord_name_node = coord.find(f"./{NS}CoordinateName")
                    if coord_name_node is not None and coord_name_node.text == "WGS84":
                        lat_node = coord.find(f"./{NS}StationLatitude")
                        lon_node = coord.find(f"./{NS}StationLongitude")
                        try:
                            lat = float(lat_node.text) if lat_node is not None else None
                            lon = float(lon_node.text) if lon_node is not None else None
                        except:
                            pass
                        break  # 找到 WGS84 後直接跳出小迴圈
                
                # 萬一找不到標記 WGS84 的節點，預設抓第一個 Coordinates 作為備援
                if (lat is None or lon is None) and len(coordinates_list) > 0:
                    try:
                        lat = float(coordinates_list[0].find(f"./{NS}StationLatitude").text)
                        lon = float(coordinates_list[0].find(f"./{NS}StationLongitude").text)
                    except:
                        continue  # 徹底無經緯度資料，跳過該站
                
                if lat is None or lon is None:
                    continue

                LAT_NORTH = 25.30; LAT_SOUTH = 24.75
                LON_WEST = 120.90; LON_EAST = 122.00

                # 經緯度範圍篩選 (LAT_SOUTH <= lat <= LAT_NORTH)
                if (LAT_SOUTH <= lat <= LAT_NORTH) and (LON_WEST <= lon <= LON_EAST):
                    st_name_node = st.find(f"./{NS}StationName")
                    st_id_node = st.find(f"./{NS}StationId")
                    
                    st_name = st_name_node.text if st_name_node is not None else "未知"
                    st_id = st_id_node.text if st_id_node is not None else ""         
                    
                    # 累積雨量
                    rain_node = st.find(f"./{NS}WeatherElement/{NS}Now/{NS}Precipitation")
                    try:
                        rain = float(rain_node.text) if rain_node is not None else 0.0
                        rain = rain if rain >= 0 else 0.0
                    except: rain = 0.0
                    
                    # 即時氣溫
                    temp_node = st.find(f"./{NS}WeatherElement/{NS}AirTemperature")
                    try:
                        temp = float(temp_node.text) if temp_node is not None else None
                        temp = temp if (temp and temp > -50) else None
                    except: temp = None
                    
                    # 風速與風向
                    speed_node = st.find(f"./{NS}WeatherElement/{NS}WindSpeed")
                    dir_node = st.find(f"./{NS}WeatherElement/{NS}WindDirection")
                    try: w_speed = float(speed_node.text) if speed_node is not None else 0.0
                    except: w_speed = 0.0
                    try: w_dir = float(dir_node.text) if dir_node is not None else 0.0
                    except: w_dir = 0.0
                    
                    raw_data_records.append({
                        "StationName": st_name,
                        "StationId": st_id,
                        "Hour": f"{hh}:00",
                        "Rain": rain,
                        "Temp": temp,
                        "WindSpeed": w_speed,
                        "WindDir": w_dir
                    })
            print(f"  [✓] Success: {hh}:00 觀測站 XML")
        else:
            print(f"  [⚪] {hh}:00 氣象署未回應 (HTTP {response.status_code})")
    except Exception as e:
        print(f"  [❌] {hh}:00 解析發生異常: {e}")
        
    dt_10_18 += timedelta(minutes=60)

# ==========================================
# Pandas 高度洗淨與 Top 排行榜統計
# ==========================================
if not raw_data_records:
    print("❌ 未儲存任何資料，待人工補齊。")
    sys.exit()

df = pd.DataFrame(raw_data_records)

# 總累積雨量 Top 10
df_rain = df.groupby(["StationName", "StationId"])["Rain"].sum().reset_index()
top10_rain = df_rain.sort_values(by="Rain", ascending=False).head(10).to_dict(orient="records")

# 當日最高氣溫 Top 10
df_temp = df.groupby(["StationName", "StationId"])["Temp"].max().reset_index()
top10_temp = df_temp.sort_values(by="Temp", ascending=False).head(10).to_dict(orient="records")

# 逐時風向風速矩陣
hourly_wind_matrix = df.to_dict(orient="records")

# 確保轉換成 dict 後，所有的 NaN/NaT 通通被安全過濾成 JSON 接受的 None (Null)
def sanitize_for_json(obj):
    if isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
        return None
    else:
        return obj

# 打包成網頁前端（cases.html 與 index.html）指定要吃的規格
final_summary_json = {
    "meta": {
        "target_date": f"{Y}-{M}-{D}",
        "calculated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    },
    "top10_precipitation": sanitize_for_json(top10_rain),
    "top10_max_temperature": sanitize_for_json(top10_temp),
    "hourly_wind_data": sanitize_for_json(hourly_wind_matrix)
}

json_output_path = os.path.join(OUTPUT_DIR, "stations_summary.json")
with open(json_output_path, "w", encoding="utf-8") as f:
    json.dump(final_summary_json, f, ensure_ascii=False, indent=2)

print("-" * 80)
print(f"SAVE ➔ {json_output_path}")
print("=" * 80)
