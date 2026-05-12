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

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
IS_MANUAL = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"

def send_discord(message):
    print(f"send_discord: {message}")
    if not WEBHOOK_URL:
        return
    try:
        clean_url = WEBHOOK_URL
        requests.post(clean_url, json={'content': message})
    except Exception as e:
        print(f"디스코드 전송 실패: {e}")

if IS_MANUAL:
    send_discord("▶️ [시스템] 셀레니움 엔진 닌텐도 감시 기동 시작!")

now = datetime.now()
if now.minute < 5:
    send_discord(f"🟢 [생존신호] {now.hour}시 정각 감시 중... (크롬 브라우저 정상 작동)")

# ==========================================
# 🤖 1. 크롬 브라우저 (투명 모드) 세팅
# ==========================================
print("Chrome 드라이버 세팅 중...")
options = Options()
options.add_argument('--headless=new') # 화면 없이 백그라운드 실행
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
# 사람인 척 위장하는 유저 에이전트
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36')
options.add_argument('--window-size=1920,1080')

# 깃허브 서버 안에 크롬 설치 및 실행
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

TARGET_DATES = ["2026-05-23", "2026-05-24", "2026-05-25"]
API_URL = "https://museum-tickets.nintendo.com/en/api/calendar?target_year=2026&target_month=5"
MAIN_URL = "https://museum-tickets.nintendo.com/en/calendar"

# ==========================================
# 🍪 2. 메인 페이지 들러서 보안 쿠키 '자동' 발급받기
# ==========================================
print("메인 페이지 접속하여 아카마이 보안 쿠키 굽는 중...")
driver.get(MAIN_URL)
time.sleep(5)  # 자바스크립트가 실행되고 쿠키가 구워질 때까지 대기

start_time = time.time()
MAX_RUNTIME = 280  # 셀레니움 종료 시간 감안하여 4분 40초로 세팅

print("🚀 4분 40초 셀레니움 감시 루프 시작...")

while True:
    if time.time() - start_time > MAX_RUNTIME:
        print("⏰ 가동 시간 종료.")
        break

    try:
        # 브라우저가 직접 API 주소로 이동 (화면에 JSON 텍스트가 뜸)
        driver.get(API_URL)
        
        # 화면에 뿌려진 텍스트(JSON) 긁어오기
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
                send_discord(f"🚨🎉 [발견] {available_dates} 예매 가능!!\n👉 {MAIN_URL}")
                break
            else:
                print("현재 매진 중...")

        except json.JSONDecodeError:
            # 방패에 막혔다면 다시 메인 페이지로 가서 쿠키를 새로 굽습니다.
            print("🚨 JSON이 아님. 보안 방패에 막힘! 쿠키 재발급 시도 중...")
            driver.get(MAIN_URL)
            time.sleep(2)

    except Exception as e:
        err_traceback = traceback.format_exc()
        send_discord(f"⚠️ [셀레니움 에러] 오류 발생\n\n```python\n{err_traceback[:1500]}\n```")
        break

    # 3~7초 랜덤 대기
    time.sleep(random.uniform(3.0, 7.0))

# 완전히 끝나면 브라우저 닫기
driver.quit()
print("프로그램 정상 종료")
