import os
import requests
import time
import random
import traceback
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==========================================
# 🔐 Webhook 링크 (GitHub Secrets에서 불러오기)
# ==========================================
GENERAL_WEBHOOK = os.getenv("GENERAL_WEBHOOK")
LOG_WEBHOOK = os.getenv("LOG_WEBHOOK")

def send_discord(message, mode="all"):
    print(message)
    # 웹훅 환경변수 누락 시 방어 로직
    if not GENERAL_WEBHOOK or not LOG_WEBHOOK:
        print("⚠️ 환경변수(Webhook)가 설정되지 않았습니다.")
        return

    targets = []
    if mode == "all":
        targets.extend([GENERAL_WEBHOOK, LOG_WEBHOOK])
    elif mode == "log":
        targets.append(LOG_WEBHOOK)

    for url in targets:
        try:
            requests.post(url, json={'content': message}, timeout=3)
        except Exception as e:
            print(f"웹훅 전송 실패: {e}")

# ==========================================
# 🤖 크롬 브라우저 세팅 (GitHub Actions Ubuntu 최적화)
# ==========================================
send_discord("⚙️ [시스템] GitHub Actions Ubuntu 엔진 기동 중...", mode="log")

options = Options()
options.add_argument('--headless=new')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument('--window-size=1920,1080')
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

try:
    # 환경 PATH에 등록된 chromedriver를 자동으로 사용
    driver = webdriver.Chrome(options=options)
    
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
except Exception as e:
    send_discord(f"❌ 크롬 기동 실패:\n{e}", mode="all")
    exit(1)

TARGET_DATES = ["2026-05-23", "2026-05-24", "2026-05-25"]
MAIN_URL = "https://museum-tickets.nintendo.com/en/calendar"
wait = WebDriverWait(driver, 1)

# ==========================================
# 🚀 DOM 파싱 루프 (타이머 적용)
# ==========================================

driver.get(MAIN_URL)
time.sleep(2)

send_discord("# 🚀 닌텐도 뮤지엄 감시 시작", mode="log")

loop_count = 0

# GitHub Actions 6시간 제한을 대비한 시작 시간 기록
start_time = datetime.now(ZoneInfo("Asia/Seoul"))
max_duration = timedelta(hours=5, minutes=55)

while True:
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    loop_count += 1
    timestamp = now.strftime('%H:%M:%S')

    # ⏱️ 5시간 55분 경과 시 안전 종료
    if now - start_time > max_duration:
        send_discord("⏱️ [시스템] GitHub Actions 타임아웃 임박. 릴레이를 위해 스크립트를 안전 종료합니다.", mode="log")
        break

    try:
        # 1. 5월 탭 찾아서 클릭
        may_tab_xpath = "//span[contains(text(), 'May')]/ancestor::a[contains(@class, 'p-period__month')]"
        may_tab = wait.until(EC.element_to_be_clickable((By.XPATH, may_tab_xpath)))
        may_tab.click()
        time.sleep(0.2)

        available_dates = []

        # 2. 날짜별 'soldOut' 클래스 유무 확인
        for date in TARGET_DATES:
            td_xpath = f"//td[@data-date='{date}']"
            try:
                day_cell = wait.until(EC.presence_of_element_located((By.XPATH, td_xpath)))
                sold_out_elements = day_cell.find_elements(By.CLASS_NAME, "soldOut")
                
                # soldOut 요소가 없다면 자리가 난 것!
                if len(sold_out_elements) == 0:
                    available_dates.append(date)
            except:
                pass

        # 3. 결과 판별
        if available_dates:
            send_discord(f"🚨🎉 [발견] {available_dates} 예매 가능!!\n👉 {MAIN_URL}", mode="all")
            time.sleep(30) #30초 대기 후 계속 탐색
        else:
            if loop_count % 10 == 0:
                send_discord(f"-# [{timestamp}] {loop_count}회차 감시 중... 전부 매진", mode="log")

        time.sleep(random.uniform(4.0, 9.0))
        driver.refresh()
        time.sleep(0.1)

    except Exception as e:
        send_discord(f"⚠️ [루프 에러] 새로고침 중...\n{str(e)[:500]}", mode="log")
        time.sleep(1)
        driver.refresh()

driver.quit()
