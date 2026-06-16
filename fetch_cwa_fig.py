import os
import sys
import requests
from PIL import Image
from io import BytesIO

# ==========================================
# 🌟 核心修正：改為接收 8 碼單一參數 (例如: 20260614)
# ==========================================
if len(sys.argv) > 1 and len(sys.argv[1]) == 8:
    date_input = sys.argv[1] # 接收 GitHub Actions 傳來的 8 碼字串
    Y = date_input[0:4]
    M = date_input[4:6]
    D = date_input[6:8]
else:
    # 手動在本地端測試時的預設值
    Y, M, D = "2026", "06", "14"

OUTPUT_DIR = f"cwaFig_archives/{Y}{M}{D}"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 🌟 自動換算：各個官方氣象網址所需要的日期代碼
YYMMDD = f"{Y[2:]}{M}{D}"   # 兩碼年份，例如 "260614"
YYYYMMDD = f"{Y}{M}{D}"     # 四碼年份，例如 "20260614"

print("=" * 80)
print(f"☁️  綜觀天氣牆與大氣熱力探空抓取工廠啟動 ➔ 目標日期：{Y}-{M}-{D} 00UTC (08:00 LST)")
print(f"📂 輸出封存路徑: {OUTPUT_DIR}")
print("=" * 80)

# ==========================================
# 雙網址自動切換下載核心引擎 (外加智慧 PNG 轉檔)
# ==========================================
def download_static_map(primary_url, fallback_url, output_name, label):
    out_path = os.path.join(OUTPUT_DIR, output_name)
    content = None
    # for 23:30 自動補圖
    if os.path.exists(out_path):
        # 額外檢查：確保檔案不是 0 KB 或小於 1 KB 的死檔、破碎檔
        if os.path.getsize(out_path) > 1024: 
            print(f"  [⏭️] {label} ➔ 圖片已存在且完整，跳過重複下載：{output_name}")
            return 
    
    # 1. 嘗試優先方案
    try:
        res = requests.get(primary_url, timeout=12)
        if res.status_code == 200:
            content = res.content
            print(f"  [✓] {label} ➔ 優先官方伺服器抓取成功！")
    except Exception:
        pass
        
    # 2. 優先方案失敗，啟動備援學術伺服器
    if content is None:
        try:
            res = requests.get(fallback_url, timeout=12)
            if res.status_code == 200:
                content = res.content
                print(f"  [✓] {label} ➔ 備援學術伺服器自愈啟動成功！")
        except Exception as e:
            print(f"  [❌] {label} ➔ 兩端伺服器均無回應或超時: {e}")
            return

    # 3. 順利取得資料，進行封存寫入
    if content:
        try:
            # 🌟 安全機制：如果網頁指定要 .png 格式，利用 Pillow 轉成貨真價實的 PNG 檔案
            if output_name.lower().endswith(".png"):
                img = Image.open(BytesIO(content))
                img.save(out_path, "PNG")
            else:
                # 其他 gif 檔案直接二進位寫入
                with open(out_path, "wb") as f:
                    f.write(content)
            print(f"      ➔ 檔案已安全寫入：{output_name}")
        except Exception as e:
            print(f"  [❌] {label} ➔ 磁碟寫入或格式轉換失敗: {e}")

# ==========================================
# 🚀 開始派發大氣環境場抓取任務
# ==========================================

# ➔ g-1. 台北 46692 探空圖
url_skewt_46692_pri = f"https://npd1.cwa.gov.tw/NPD/irisme_data/Weather/SKEWT/SKW___000_{YYMMDD}00_46692.gif"
url_skewt_46692_fal = f"http://140.137.32.27/www/skw2/{Y}/{M}/{D}/{YYYYMMDD}_0000.46692.skw.jpg"
download_static_map(url_skewt_46692_pri, url_skewt_46692_fal, "skewt_taipei.gif", "台北站探空圖 (46692)")

# ➔ g-2. 彭佳嶼 46695 探空圖
url_skewt_46695_pri = f"https://npd1.cwa.gov.tw/NPD/irisme_data/Weather/SKEWT/SKW___000_{YYMMDD}00_46695.gif"
url_skewt_46695_fal = f"http://140.137.32.27/www/skw2/{Y}/{M}/{D}/{YYYYMMDD}_0000.46695.skw.jpg"
download_static_map(url_skewt_46695_pri, url_skewt_46695_fal, "skewt_pengjia.gif", "彭佳嶼站探空圖 (46695)")

# ➔ h-1. 地面天氣圖 (🌟 會自動轉存為真正的 .png 格式以防網頁破圖)
url_sfc_pri = f"http://140.137.32.27/www/cwbmap/{Y}/{M}/{D}/{YYYYMMDD}_0000.cwbmap.sfcmap.gif"
url_sfc_fal = f"https://npd1.cwa.gov.tw/NPD/irisme_data/Weather/ANALYSIS/GRA___000_{YYMMDD}00_103.gif"
download_static_map(url_sfc_pri, url_sfc_fal, "synoptic_sfc.png", "天氣綜觀地面圖")

# ➔ h-2. 850 hPa 高空分析圖
url_850_pri = f"https://npd1.cwa.gov.tw/NPD/irisme_data/Weather/HLANALYSIS/GRA___000_{YYMMDD}00_001.gif"
url_850_fal = f"http://140.137.32.27/www/cwbmap/{Y}/{M}/{D}/{YYYYMMDD}_0000.cwbmap.asu850.gif"
download_static_map(url_850_pri, url_850_fal, "synoptic_850.gif", "850hPa高空分析流場")

# ➔ h-3. 500 hPa 高空分析圖
url_500_pri = f"https://npd1.cwa.gov.tw/NPD/irisme_data/Weather/HLANALYSIS/GRA___000_{YYMMDD}00_003.gif"
url_500_fal = f"http://140.137.32.27/www/cwbmap/{Y}/{M}/{D}/{YYYYMMDD}_0000.cwbmap.asu500.gif"
download_static_map(url_500_pri, url_500_fal, "synoptic_500.gif", "500hPa高空綜觀環境")

print("=" * 80)
print(f"🎉 綜觀大氣牆環境圖資封存完畢！")
print("=" * 80)
