import requests
import time
import random
import os
import json
import traceback
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

# 환경 변수 로드
GENERAL_WEBHOOK = os.environ.get("GENERAL_WEBHOOK")
LOG_WEBHOOK = os.environ.get("LOG_WEBHOOK")
IS_MANUAL = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"

def send_discord(message, mode="all"):
    """
    mode="all": General 채널과 Log 채널 양쪽 모두 전송
    mode="log": Log 채널에만 전송
    """
    targets = []
    if mode == "all":
        if GENERAL_WEBHOOK: targets.append(GENERAL_WEBHOOK)
        if LOG_WEBHOOK: targets.append(LOG_WEBHOOK)
    elif mode == "log":
        if LOG_WEBHOOK: targets.append(LOG_WEBHOOK)
    print(message)

    for url in targets:
        try:
            requests.post(url, json={'content': message})
        except Exception as e:
            print(f"디스코드 전송 실패 ({url[-10:]}): {e}")

# 시작 로그
start_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
if IS_MANUAL:
    send_discord(f"▶️ [시스템] 수동 기동 시작! ({start_time_str})", mode="all")
else:
    send_discord(f"🤖 [시스템] 정기 스케줄러 기동 ({start_time_str})", mode="log")

now = datetime.now()
if now.minute < 5:
    send_discord(f"🟢 [생존신호] {now.hour}시 정각 감시 중... (엔진 정상)", mode="all")

# ==========================================
# 🤖 1. 크롬 브라우저 세팅
# ==========================================
send_discord("Chrome 드라이버 세팅 중...", mode="log")
options = Options()
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36')
options.add_argument('--window-size=1920,1080')

try:
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
except Exception as e:
    send_discord(f"❌ [드라이버 에러] 크롬 드라이버 설치 실패:\n{e}", mode="all")
    exit(1)
send_discord("Chrome 드라이버 세팅 완료!", mode="log")

TARGET_DATES = ["2026-05-23", "2026-05-24", "2026-05-25"] #예매할 날짜
API_URL = "https://museum-tickets.nintendo.com/en/api/calendar?target_year=2026&target_month=5"
MAIN_URL = "https://museum-tickets.nintendo.com/en/calendar"

# ==========================================
# 🍪 2. 보안 쿠키 발급
# ==========================================
send_discord("🍪 아카마이 보안 쿠키 굽기 시작...", mode="log")
driver.get(MAIN_URL)
time.sleep(3)

start_time = time.time()
MAX_RUNTIME = 270 
loop_count = 0

send_discord(f"## 🚀 감시 루프 시작 (최대 {MAX_RUNTIME}초)", mode="log")

while True:
    current_elapsed = time.time() - start_time
    if current_elapsed > MAX_RUNTIME:
        send_discord(f"⏰ 설정된 가동 시간({MAX_RUNTIME}초)이 경과되어 종료합니다.", mode="log")
        break

    loop_count += 1
    timestamp = datetime.now().strftime('%H:%M:%S')

    try:
        driver.get(API_URL)
        raw_text = driver.find_element(By.TAG_NAME, "body").text
        
        try:
            data = json.loads(raw_text)
            calendar_data = data.get("data", {}).get("calendar", {})
            available_dates = []

            for date in TARGET_DATES:
                day_info = calendar_data.get(date)
                if day_info and day_info.get("sale_status") == 1:
                    available_dates.append(date)

            if available_dates:
                send_discord(f"🚨🎉 [발견] {available_dates} 예매 가능!!\n👉 {MAIN_URL}", mode="all")
                break
            else:
                # 매진 상태 로그 (log 채널에만 상세히 남김)
                send_discord(f"-# [{timestamp}] {loop_count}회차 감시 중... 여전히 매진 상태입니다.", mode="log")

        except json.JSONDecodeError:
            send_discord(f"⚠️ [{timestamp}] 보안 장벽 감지! 쿠키 재생성 시도...", mode="log")
            driver.get(MAIN_URL)
            time.sleep(3)

    except Exception as e:
        err_traceback = traceback.format_exc()
        send_discord(f"⚠️ [실행 에러]\n```python\n{err_traceback[:1500]}\n```", mode="all")
        break

    time.sleep(random.uniform(5.0, 10.0)) # 차단 방지를 위해 약간 더 여유있게 조정

driver.quit()
send_discord(f"## 🏁 [시스템] 프로그램 정상 종료 (총 {loop_count}회 시도)", mode="log")
