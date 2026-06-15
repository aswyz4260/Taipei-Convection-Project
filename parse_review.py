import os
import json
import re

def parse_github_issue():
    # 從 GitHub Actions 讀取研究員送出的 Issue 內容
    issue_body = os.environ.get("ISSUE_BODY", "")
    issue_title = os.environ.get("ISSUE_TITLE", "")
    
    # 1. 從標題或內容抓取個案日期 (格式: YYYY-MM-DD)
    date_match = re.search(r"\d{4}-\d{2}-\d{2}", issue_title)
    if not date_match:
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", issue_body)
    
    if not date_match:
        print("❌ 錯誤：無法從 Issue 標題或內文中識別個案日期！")
        return
    
    case_date = date_match.group(0)
    date_str = case_date.replace("-", "")
    print(f"📅 開始解析個案日期: {case_date}")

    # 初始化最終要倒灌回網頁的 JSON 結構
    result = {
        "date": case_date,
        "synoptic_fields": {},
        "thermodynamics": {},
        "rain_wind_evolution": {"times": [], "summary": ""},
        "temp_wind_evolution": {"times": [], "summary": ""},
        "radar_lgt_evolution": {"times": [], "summary": ""}
    }

    # 🧠 用簡單的區塊切分法解析 YAML Form 的輸出
    # GitHub Form 會把各區塊用 ### 標題與內文隔開
    sections = issue_body.split("### ")
    
    for section in sections:
        lines = section.strip().split("\n")
        if not lines:
            continue
        
        header = lines[0].strip()
        content_lines = [l.strip() for l in lines[1:] if l.strip() and not l.startswith("_No response_")]
        content = "\n".join(content_lines).strip()
        
        # 1. 解析綜觀天氣場 (未填寫或勾選就不納入)
        if "地面天氣圖描述" in header and content:
            result["synoptic_fields"]["sfc_chart"] = content
        elif "850hPa圖描述" in header and content:
            result["synoptic_fields"]["h850_chart"] = content
        elif "500hPa圖描述" in header and content:
            result["synoptic_fields"]["h500_chart"] = content
            
        # 2. 解析熱動力環境
        elif "台北探空描述" in header and content:
            result["thermodynamics"]["taipei"] = content
        elif "彭佳嶼探空描述" in header and content:
            result["thermodynamics"]["pengjia"] = content
            
        # 3. 降雨與風場逐時分布變化
        elif "選擇欲記錄/留存的雨量風向圖時間點" in header:
            # Dropdown 多選會輸出成像 "09:00, 09:30, 10:00" 這樣的字串
            times = [t.strip() for l in content_lines for t in l.split(",") if t.strip()]
            result["rain_wind_evolution"]["times"] = times
        elif "降雨與風場逐時變化總結描述" in header and content:
            result["rain_wind_evolution"]["summary"] = content
            
        # 4. 溫度逐時分布變化
        elif "選擇欲記錄/留存的溫度風向圖時間點" in header:
            times = [t.strip() for l in content_lines for t in l.split(",") if t.strip()]
            result["temp_wind_evolution"]["times"] = times
        elif "溫度逐時變化總結描述" in header and content:
            result["temp_wind_evolution"]["summary"] = content
            
        # 5. 雷達與降雨發展史
        elif "選擇欲記錄/留存的雷達與落雷關鍵時間點" in header:
            times = [t.strip() for l in content_lines for t in l.split(",") if t.strip()]
            result["radar_lgt_evolution"]["times"] = times

    # 🌟 寫入對應日期的 sfc_archives 資料夾中 (例如: ./sfc_archives/20260615/review_summary.json)
    target_dir = f"./sfc_archives/{date_str}"
    os.makedirs(target_dir, exist_ok=True)
    
    with open(f"{target_dir}/review_summary.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
        
    print(f"🎉 成功！科學審查報告已安全封存至 {target_dir}/review_summary.json")

if __name__ == "__main__":
    parse_github_issue()