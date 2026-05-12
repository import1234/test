import requests
import time
import random
import os
from datetime import datetime

# 설정 불러오기
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
MY_COOKIE = os.environ.get("NINTENDO_COOKIE")
MY_XSRF = os.environ.get("NINTENDO_XSRF")
# 수동 실행인지 확인하기 위한 환경 변수 (YML에서 설정)
IS_MANUAL = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"

def send_discord(message):
    try:
        requests.post(WEBHOOK_URL, json={'content': message})
    except Exception as e:
        print(f"디스코드 전송 실패: {e}")

# 1. 수동 시작 알림 (버튼 눌렀을 때만 실행)
if IS_MANUAL:
    send_discord("▶️ [시스템] 닌텐도 뮤지엄 예매 사이트 감시 시작!")

# 2. 생존 신호 알림 (매시간 정각~5분 사이에 실행되는 회차에서만)
now = datetime.now()
if now.minute < 5:
    send_discord(f"🟢 [생존신호] {now.hour}시 정각 감시 중... (현재 쿠키 생존 확인)")

# 헤더 설정
headers = {
    'accept': 'application/json, text/plain, */*',
    'referer': 'https://museum-tickets.nintendo.com/en/calendar',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
    'x-xsrf-token': MY_XSRF,
    'cookie': MY_COOKIE
}
params = {'target_year': '2026', 'target_month': '5'}
URL = 'https://museum-tickets.nintendo.com/en/api/calendar'
TARGET_DATES = ["2026-05-23", "2026-05-24", "2026-05-25"]

# 시간 측정 시작
start_time = time.time()
MAX_RUNTIME = 290  # 4분 50초

print("🚀 4분 50초 감시 시작...")

while True:
    # 4분 50초가 지나면 종료 (다음 5분 스케줄러를 위해 비켜줌)
    if time.time() - start_time > MAX_RUNTIME:
        print("⏰ 예정된 가동 시간 종료. 다음 스케줄을 기다립니다.")
        break

    try:
        response = requests.get(URL, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            calendar_data = data.get("data", {}).get("calendar", {})
            available_dates = []

            for date in TARGET_DATES:
                day_info = calendar_data.get(date)
                if day_info and day_info.get("sale_status") == 1: # 예매 가능!
                    available_dates.append(date)

            if available_dates:
                send_discord(f"🚨🎉 [발견] {available_dates} 예매 가능!!\n👉 https://museum-tickets.nintendo.com/en/calendar")
                break # 자리 났으면 알림 쏘고 종료

        elif response.status_code == 403:
            send_discord("❌ [에러] 403 Forbidden! 쿠키가 만료된 것 같습니다. 새로 갱신해주세요.")
            break # 차단됐으면 종료
        
        else:
            # 500번대 서버 에러 등은 일시적일 수 있으니 디코 안 쏘고 그냥 출력만
            print(f"서버 응답 상태 이상: {response.status_code}")

    except Exception as e:
        # 예상치 못한 에러(인터넷 끊김 등) 발생 시 디코 알림
        send_discord(f"⚠️ [시스템 에러] 파이썬 실행 중 오류 발생: {str(e)}")
        break # 에러 나면 일단 종료 (전역변수 초기화 효과)

    # 3~7초 랜덤 대기
    time.sleep(random.uniform(3.0, 7.0))
