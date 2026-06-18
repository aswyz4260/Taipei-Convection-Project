import os
import sys
import requests
from PIL import Image
from io import BytesIO
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

DATE_STR = f"{Y}{M}{D}"
RADAR_DIR = f"radar_archives/{DATE_STR}"
SFC_DIR = f"sfc_archives/{DATE_STR}"

# 一口氣把雷達跟地面場的雲端防線資料夾全部開好
os.makedirs(RADAR_DIR, exist_ok=True)
os.makedirs(SFC_DIR, exist_ok=True)

print("=" * 80)
print(f"⛈️  北台灣午後對流圖片工廠啟動 ➔ 目標日期：{Y}-{M}-{D}")
print(f"📡 雷達輸出路徑: {RADAR_DIR}")
print(f"🌡️  地面輸出路徑: {SFC_DIR}")
print("=" * 80)

# ==========================================
# 影像下載與裁切核心引擎
# ==========================================
def download_and_crop(url, crop_box, output_path, label, save_format="JPEG"):
    if os.path.exists(output_path):
        # 確保檔案不是 0 KB 或破碎檔
        if os.path.getsize(output_path) > 1024: 
            print(f"[{label}] ⏭️ 圖片已存在且完整，跳過重複下載與裁切")
            return True
    try:
        response = requests.get(url, timeout=12) # 稍微放寬連線超時，防止氣象署伺服器塞車
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            cropped_img = img.crop(crop_box)
            
            # 如果存成 PNG，必須保留模式；存成 JPEG 則強制轉 RGB
            if save_format.upper() == "JPEG":
                if cropped_img.mode in ('RGBA', 'P'):
                    cropped_img = cropped_img.convert('RGB')
                cropped_img.save(output_path, "JPEG", quality=90)
            else:
                # 🌟 為了對齊網頁前端的 Fetch 機制，任務 C 儲存為 PNG
                cropped_img.save(output_path, "PNG")
            return True
        else:
            print(f"[{label}] ⚠️ 狀態碼異常 ({response.status_code}) ➔ {url}")
            return False
    except Exception as e:
        print(f"[{label}] ❌ 連線或裁切異常: {e}")
        return False

# ==========================================
# 任務 A & B 迴圈：台灣時間 10:00 - 18:00 (每 10 分鐘，維持原檔名 .jpg)
# ==========================================
print("\n📡 正在處理：[a.雷達回波] 與 [b.逐時閃電] (10分鐘步進)...")
dt_10_18 = datetime(int(Y), int(M), int(D), 10, 0, 0)
end_10_18 = datetime(int(Y), int(M), int(D), 18, 0, 0)

while dt_10_18 <= end_10_18:
    hhmm = dt_10_18.strftime("%H%M")
    hh_mm_display = dt_10_18.strftime("%H:%M") 
    
    # ➔ a. 雷達回波無地形 (.jpg)
    url_a = f"http://140.137.32.27/www/cwbrad/{Y}/{M}/{D}/{DATE_STR}_{hhmm}.cwbrad.TV1.jpg"
    path_a = os.path.join(RADAR_DIR, f"radar_north_{DATE_STR}_{hhmm}.jpg")
    box_a = (333, 83, 833, 417)
    
    if download_and_crop(url_a, box_a, path_a, "雷達", "JPEG"):
        print(f"  [✓] 雷達圖 {hh_mm_display} ➔ {os.path.basename(path_a)}")
        
    # ➔ b. 逐時閃電資料 (.jpg)
    url_b = f"http://140.137.32.27/www/cwblgt/{Y}/{M}/{D}/{DATE_STR}_{hhmm}.cwblgt.lgtx.gif"
    path_b = os.path.join(RADAR_DIR, f"radar_lgt_north_{DATE_STR}_{hhmm}.jpg")
    box_b = (368, 0, 1110, 492) 
    
    if download_and_crop(url_b, box_b, path_b, "閃電", "JPEG"):
        print(f"  [✓] 閃電圖 {hh_mm_display} ➔ {os.path.basename(path_b)}")
        
    dt_10_18 += timedelta(minutes=10)

print("-" * 80)

# ==========================================
# 任務 C 迴圈：台灣時間 08:00 - 18:00
# ==========================================
print("\n🌡️ 正在處理：[c-1.時雨量風場] 與 [c-2.溫度分布風場] (30分鐘步進)...")
dt_09_15 = datetime(int(Y), int(M), int(D), 8, 0, 0)
end_09_15 = datetime(int(Y), int(M), int(D), 18, 0, 0)

while dt_09_15 <= end_09_15:
    hhmm = dt_09_15.strftime("%H%M")
    hh_mm_log = dt_09_15.strftime("%H:%M") 
    
    # ➔ c-1. 時雨量+風
    url_c1 = f"http://140.137.32.27/www/rainhr/{Y}/{M}/{D}/{DATE_STR}_{hhmm}.cwbrain.rainhrw.jpg"
    path_c1 = os.path.join(SFC_DIR, f"rain_wind_north_{DATE_STR}_{hhmm}.jpg")
    box_c1 = (150, 0, 880, 340)
    
    if download_and_crop(url_c1, box_c1, path_c1, "時雨量+風", "PNG"):
        print(f"  [✓] 雨量風場 {hh_mm_log} ➔ {os.path.basename(path_c1)}")
    
    # 溫度只有整點
    if hhmm.endswith("00"):
        # ➔ c-2. 溫度分布+風
        url_c2 = f"http://140.137.32.27/www/cwbgtp/{Y}/{M}/{D}/{DATE_STR}_{hhmm}.cwbtemp.GTPw.jpg"
        path_c2 = os.path.join(SFC_DIR, f"temp_wind_north_{DATE_STR}_{hhmm}.jpg")
        box_c2 = (420, 0, 1500, 600)
        
        if download_and_crop(url_c2, box_c2, path_c2, "溫度+風", "PNG"):
            print(f"  [✓] 溫度風場 {hh_mm_log} ➔ {os.path.basename(path_c2)}")
    else: 
        print(f"  [⏭️] 溫度風場 {hh_mm_log} ➔ 非整點跳過")
            
    dt_09_15 += timedelta(minutes=30)

print("=" * 80)
print(f"🎉 圖片工廠任務全數執行完畢！目標日期：{Y}-{M}-{D} 封存完成。")
print("=" * 80)
