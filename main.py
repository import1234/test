import requests
import time
import random
import os

# GitHub Secrets에서 숨겨둔 값을 안전하게 불러옵니다
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
MY_COOKIE = os.environ.get("NINTENDO_COOKIE")
MY_XSRF = os.environ.get("NINTENDO_XSRF")

# requests 라이브러리는 쿠키를 딕셔너리가 아닌 생 문자열(String)로 헤더에 넣어도 잘 작동합니다.
headers = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'ko-KR,ko;q=0.9',
    'priority': 'u=1, i',
    'referer': 'https://museum-tickets.nintendo.com/en/calendar',
    'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
    'x-requested-with': 'XMLHttpRequest',
    'x-xsrf-token': MY_XSRF,
    'cookie': MY_COOKIE
}

params = {
    'target_year': '2026',
    'target_month': '5',
}

URL = 'https://museum-tickets.nintendo.com/en/api/calendar'

# 추적할 날짜 (13일, 23일, 24일, 25일)
TARGET_DATES = ["2026-05-13", "2026-05-23", "2026-05-24", "2026-05-25"]

print("🚀 닌텐도 뮤지엄 5분 스탠스 (3~7초 간격) 추적 시작...")

# 50번 반복 (평균 5초 * 50번 = 약 250초 / 5분 이내 컷)
for i in range(50):
    try:
        response = requests.get(URL, params=params, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            calendar_data = data.get("data", {}).get("calendar", {})
            available_dates = []

            for date in TARGET_DATES:
                day_info = calendar_data.get(date)
                
                # 핵심: open_status == 1 (운영일) 이고 sale_status == 1 (예매 가능) 일 때
                if day_info and day_info.get("open_status") == 1 and day_info.get("sale_status") == 1:
                    available_dates.append(date)

            if available_dates:
                msg = f"🚨🎉 [긴급] 닌텐도 뮤지엄 예매 가능!: {available_dates}\n👉 바로가기: https://museum-tickets.nintendo.com/en/calendar"
                requests.post(DISCORD_WEBHOOK_URL, data={'content': msg})
                print(f"[{i+1}/50] 🎉 예매 가능! 디스코드 알림 전송 완료.")
                break # 알림을 한 번 보냈으면 이번 5분 사이클은 조기 종료
            else:
                print(f"[{i+1}/50] 모두 매진 상태입니다...")
        
        elif response.status_code == 403:
             print(f"[{i+1}/50] 🚨 차단됨 (403). 쿠키가 만료되었을 수 있습니다.")
             break
        else:
            print(f"[{i+1}/50] API 요청 실패 (상태 코드: {response.status_code})")
            
    except Exception as e:
        print(f"[{i+1}/50] 에러 발생: {e}")
        
    # 마지막 루프가 아니면 3~7초 랜덤 대기
    if i < 49:
        time.sleep(random.uniform(3.0, 7.0))
