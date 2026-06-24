import sys
import os 
import requests
import xml.etree.ElementTree as ET
import numpy as np
from datetime import datetime, timedelta
# import shutil

# ==========================================
if len(sys.argv) > 1 and len(sys.argv[1]) == 8:
    date_input = sys.argv[1] 
    Y = date_input[0:4]
    M = date_input[4:6]
    D = date_input[6:8]
    print(f"接收指定日期：{Y}-{M}-{D}")
else:
    # 本地手動無參數測試時的預設值
    Y, M, D = "2026", "06", "14"  
    print(f"未指定參數，採用預設本地測試日期：{Y}-{M}-{D}")

API_TOKEN = "CWB-B1034BF8-0855-45E6-8F10-7C7D4DB194AA"

# 台北盆地雷達格點切片範圍
TAIPEI_Y_START, TAIPEI_Y_END = 540, 584
TAIPEI_X_START, TAIPEI_X_END = 480, 544

DBZ_THRESHOLD = 40.0       # 40 dBZ 門檻
GRID_COUNT_THRESHOLD = 6   # 6格達標 (6 * 1.5625 = 9.375 km², 約近 10 km²)

print("-" * 80)

# 偵測午後對流時段：台灣時間 12:00 - 18:00 (每 10 分鐘一幀)
start_dt = datetime(int(Y), int(M), int(D), 12, 0, 0)
end_dt = datetime(int(Y), int(M), int(D), 18, 0, 0)

current_dt = start_dt
time_series_results = []
nx, ny = 921, 881

print(f"{'觀測時間 (LST)':<25}{'盆地內≥40dBZ格點數':<18}{'換算面積 (km²)':<15}{'單一時段判定':<10}")
print("-" * 70)

# ==========================================
# 雷達格點數據掃描迴圈
# ==========================================
while current_dt <= end_dt:
    hh = current_dt.strftime("%H")
    mm = current_dt.strftime("%M")
    ss = current_dt.strftime("%S")
    
    url = f"https://opendata.cwa.gov.tw/historyapi/v1/getData/O-A0059-001/{Y}/{M}/{D}/{hh}/{mm}/{ss}?Authorization={API_TOKEN}&format=XML"
    
    try:
        response = requests.get(url, timeout=12)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            
            # 全自動搜索隱藏的格點大字串
            raw_text = ""
            for node in root.iter():
                if node.text and node.text.count(',') > 100:
                    raw_text = node.text.strip()
                    break
            
            if raw_text:
                flat_data = np.fromstring(raw_text, sep=',')[:(nx * ny)]
                full_matrix = flat_data.reshape((ny, nx))
                
                # 台北盆地切片與格點統計
                taipei_basin = full_matrix[TAIPEI_Y_START:TAIPEI_Y_END, TAIPEI_X_START:TAIPEI_X_END]
                valid_taipei = taipei_basin[taipei_basin >= 0]
                
                if len(valid_taipei) > 0:
                    strong_grids = valid_taipei[valid_taipei >= DBZ_THRESHOLD]
                    grid_count = len(strong_grids)
                    calculated_area = grid_count * 1.5625
                else:
                    grid_count, calculated_area = 0, 0.0
                
                is_single_met = grid_count >= GRID_COUNT_THRESHOLD
                time_series_results.append(is_single_met)
                
                time_label = current_dt.strftime('%Y-%m-%d %H:%M')
                status_text = "🔴 達標" if is_single_met else "⚪ 正常"
                print(f"{time_label:<25}{grid_count:<22}{calculated_area:<18.2f}{status_text:<10}")
                
                current_dt += timedelta(minutes=10)
                continue

        # 晴天、無回波防呆
        time_series_results.append(False)
        time_label = current_dt.strftime('%Y-%m-%d %H:%M')
        print(f"{time_label:<25}{0:<22}{0.00:<18.2f}{'🔵 無回波':<10}")
        
    except Exception as e:
        time_series_results.append(False)
        time_label = current_dt.strftime('%Y-%m-%d %H:%M')
        print(f"{time_label:<25}{0:<22}{0.00:<18.2f}{'❌ 異常跳過':<10}")
        
    current_dt += timedelta(minutes=10)

# ==========================================
# 時間持續性驗證 (連續滿 30 分鐘，即 3 幀達標)
# ==========================================
is_triggered = False
consecutive_counter = 0

for result in time_series_results:
    if result:
        consecutive_counter += 1
        if consecutive_counter >= 3:
            is_triggered = True
            break
    else:
        consecutive_counter = 0

# ==========================================
# 用環境變數指揮 GitHub Actions 進行分流
# ==========================================
print("-" * 70)
if is_triggered:
    print(f"\n🟢 [判定成功] {Y}-{M}-{D}")
    print("通知 GitHub Actions 繼續進行後續打包！")
    print("=" * 80)
    sys.exit(0)
else:
    print(f"\n🟡 [未達標準] {Y}-{M}-{D} ")
    print("SKIP。通知 GitHub Actions 跳過今日自動打包步驟。")

    '''
    # 轉換日期格式為 YYYY-MM-DD
    qpf_date_str = f"{Y}{M}{D}"
    qpf_dir = f"./qpf_images/{qpf_date_str}"
    
    if os.path.exists(qpf_dir):
        # 實體強制刪除整個 QPF 當日資料夾（連同裡面的圖片）
        shutil.rmtree(qpf_dir)
        print(f"Cleaned up: 已成功刪除未達標之當日 QPF 資料夾 -> {qpf_dir}")
    else:
        print("Info: 今日未產生 QPF 資料夾，無需清理。")
    '''
    print("=" * 80)
    
    if "GITHUB_ENV" in os.environ:
        with open(os.environ["GITHUB_ENV"], "a") as f:
            f.write("SKIP_RUN=true\n")
            
    sys.exit(0) # 不是Error!!!
