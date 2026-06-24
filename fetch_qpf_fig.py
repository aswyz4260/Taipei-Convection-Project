import os
import time
import requests
import re
from datetime import datetime

IMG_DIR = f"./qpf_images/{datetime.now().strftime('%Y%m%d')}"  
os.makedirs(IMG_DIR, exist_ok=True)

API_TOKEN = "CWB-B1034BF8-0855-45E6-8F10-7C7D4DB194AA"

def wait_until_1130():
    while True:
        now = datetime.now()
        # 判斷目前時間是否已經到達或超過 11:30
        if now.hour > 11 or (now.hour == 11 and now.minute >= 30):
            print(f"NOW: {now.strftime('%H:%M')}")
            break
        else:
            print(f"TOO EARLY: {now.strftime('%H:%M')}, SLEEP 30s...")
            time.sleep(30)

def main():
    today_tw = datetime.now().strftime("%Y%m%d")
    today_dash = datetime.now().strftime("%Y-%m-%d")
    
    url_xml = f"https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/F-C0035-015?Authorization={API_TOKEN}&format=XML"
    url_12h = f"https://cwaopendata.s3.ap-northeast-1.amazonaws.com/Forecast/F-C0035-015.png"
    url_6h_base = f"https://www.cwa.gov.tw/Data/fcst_img/QPF_ChFcstPrecip_6_06.png"

    # 阻擋 11:30 之前的偷跑 (Github Actions 設定提早觸發)
    wait_until_1130()

    # 檢查 XML Sent 是否更新，最多等 20 次 (共 1 小時)
    max_tries = 20
    wait_seconds = 180

    for i in range(1, max_tries + 1):
        print(f"\n[TRY: {i}/{max_tries}] UPDATED or not...")
        
        try:
            ts_now = datetime.now().strftime("%Y%m%d%H%M%S")
            res_xml = requests.get(f"{url_xml}&cache={ts_now}", timeout=10)
            
            if res_xml.status_code == 200:
                sent_match = re.search(r'<Sent>([^<]+)</Sent>', res_xml.text)
                
                if sent_match:
                    sent_time_str = sent_match.group(1)
                    print(f"Sent = {sent_time_str}")
                    
                    sent_date = sent_time_str.split('T')[0]
                    sent_hour = int(sent_time_str.split('T')[1].split(':')[0])
                    
                    if sent_date == today_dash and sent_hour in [10, 11]:
                        print("START DOWNLOADING...")
                        
                        res_12h = requests.get(url_12h, timeout=15)
                        if res_12h.status_code == 200:
                            with open(f"{IMG_DIR}/QPF_12h_{today_tw}_1130.png", "wb") as f:
                                f.write(res_12h.content)
                            print("SUCCESS: 已儲存 12h 預報圖")

                        # 下載 6h 官網圖 (帶上最新執行的時間戳破除快取)
                        res_6h = requests.get(f"{url_6h_base}?T={ts_now}", timeout=15)
                        if res_6h.status_code == 200:
                            with open(f"{IMG_DIR}/QPF_6h_{today_tw}_1130.png", "wb") as f:
                                f.write(res_6h.content)
                            print("SUCCESS: 已儲存 6h 預報圖")

                        return
                    else:
                        print("氣象署後端資料尚未更新，畫面上還是舊預報")
                else:
                    print("無法解析 XML 中的 <Sent> 標籤。")
            else:
                print(f"XML API 連線異常 (狀態碼: {res_xml.status_code})")
                
        except Exception as e:
            print(f"執行發生異常: {e}")

        if i < max_tries:
            print(f"等待 {wait_seconds // 60} 分鐘後進行下一次 XML 檢查...")
            time.sleep(wait_seconds)

    print("❌ 超時，今天未抓取到 11:30 最新預報")
    exit(1)

if __name__ == "__main__":
    main()
