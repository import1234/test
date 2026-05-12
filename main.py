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
# 🛡️ 봇 탐지 우회를 위한 스텔스 라이브러리
from selenium_stealth import stealth

# 환경 변수 로드
GENERAL_WEBHOOK = os.environ.get("GENERAL_WEBHOOK")
LOG_WEBHOOK = os.environ.get("LOG_WEBHOOK")
IS_MANUAL = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"

def send_discord(message, mode="all"):
    """
    mode="all": General 채널과 Log 채널 양쪽 모두 전송
    mode="log": Log 채널에만 전송
    """
    print(message)
    targets = []
    if mode == "all":
        if GENERAL_WEBHOOK: targets.append(GENERAL_WEBHOOK)
        if LOG_WEBHOOK: targets.append(LOG_WEBHOOK)
    elif mode == "log":
        if LOG_WEBHOOK: targets.append(LOG_WEBHOOK)

    for url in targets:
        try:
            requests.post(url, json={'content': message})
        except Exception as e:
            print(f"디스코드 전송 실패: {e}")

# 시작 로그
start_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
if IS_MANUAL:
    send_discord(f"▶️ [시스템] 수동 기동 시작! ({start_time_str})", mode="all")
else:
    send_discord(f"🤖 [시스템] 정기 스케줄러 기동 ({start_time_str})", mode="log")

# ==========================================
# 🤖 1. 크롬 브라우저 세팅 (Stealth 강화)
# ==========================================
send_discord("Chrome 드라이버 세팅 중 (Stealth Mode)...", mode="log")
options = Options()
options.add_argument('--headless=new') # 최신 헤드리스 모드 사용
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument("--window-size=1920,1080")

# 핵심: 자동화 제어 플래그 제거 (아카마이 우회 필수)
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

# 실제 크롬 브라우저와 유사한 User-Agent 설정
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')

try:
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    # 🛡️ Selenium-Stealth 적용: 하드웨어 지문 및 JS 환경 위장
    stealth(driver,
        languages=["ko-KR", "ko", "en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )
except Exception as e:
    send_discord(f"❌ [드라이버 에러] 설치 실패:\n{e}", mode="all")
    exit(1)

send_discord("Chrome 드라이버 세팅 완료!", mode="log")

TARGET_DATES = ["2026-05-23", "2026-05-24", "2026-05-25"]
API_URL = "https://museum-tickets.nintendo.com/en/api/calendar?target_year=2026&target_month=5"
MAIN_URL = "https://museum-tickets.nintendo.com/en/calendar"

# ==========================================
# 🍪 2. 보안 세션 확립 (Main Page 접근)
# ==========================================
send_discord("🍪 세션 초기화 및 보안 쿠키 획득 시도...", mode="log")
try:
    driver.get(MAIN_URL)
    time.sleep(random.uniform(3, 5)) # 페이지 로드 대기
except Exception as e:
    send_discord(f"⚠️ 초기 접속 실패: {e}", mode="log")

start_time = time.time()
MAX_RUNTIME = 270 # 4분 30초
loop_count = 0

send_discord(f"## 🚀 감시 루프 시작 (최대 {MAX_RUNTIME}초)", mode="log")

while True:
    current_elapsed = time.time() - start_time
    if current_elapsed > MAX_RUNTIME:
        send_discord(f"⏰ 설정 시간 종료 ({loop_count}회 시도)", mode="log")
        break

    loop_count += 1
    timestamp = datetime.now().strftime('%H:%M:%S')

    try:
        # 패턴 분석 방지를 위해 5회마다 메인 페이지 재방문
        if loop_count % 5 == 0:
            driver.get(MAIN_URL)
            time.sleep(random.uniform(2, 4))

        driver.get(API_URL)
        time.sleep(1) # 응답 대기
        
        body_element = driver.find_element(By.TAG_NAME, "body")
        raw_text = body_element.text
        
        # 보안 장벽에 막혔는지 텍스트 검사
        if not raw_text or "Access Denied" in raw_text or "Something went wrong" in raw_text:
            raise json.JSONDecodeError("Bot detected or Empty response", raw_text, 0)

        data = json.loads(raw_text)
        calendar_data = data.get("data", {}).get("calendar", {})
        available_dates = []

        for date in TARGET_DATES:
            day_info = calendar_data.get(date)
            # sale_status가 1이면 예매 가능
            if day_info and day_info.get("sale_status") == 1:
                available_dates.append(date)

        if available_dates:
            send_discord(f"🚨🎉 [발견] {available_dates} 예매 가능!!\n👉 {MAIN_URL}", mode="all")
            # 발견 시 스크린샷 등을 찍거나 루프 종료
            break
        else:
            send_discord(f"-# [{timestamp}] {loop_count}회차 감시 중... 매진 상태", mode="log")

    except json.JSONDecodeError:
        # 차단되었을 때의 페이지 상태를 로깅 (디버깅용)
        send_discord(f"⚠️ [{timestamp}] 보안 장벽 감지! 세션 재설정 중...", mode="log")
        driver.delete_all_cookies() # 쿠키 초기화 후 재시도
        driver.get(MAIN_URL)
        time.sleep(random.uniform(10, 15)) # 차단 시엔 좀 더 오래 쉽니다.

    except Exception as e:
        err_traceback = traceback.format_exc()
        send_discord(f"⚠️ [실행 에러]\n```python\n{err_traceback[:1000]}\n
```", mode="all")
        break

    time.sleep(random.uniform(3.0, 10.0))

driver.quit()
send_discord(f"## 🏁 [시스템] 프로그램 종료 (총 {loop_count}회 시도)", mode="log")
