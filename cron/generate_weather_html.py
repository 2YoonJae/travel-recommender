"""cron이 주기적으로 실행 → 전국 날씨를 받아 정적 HTML(weather.html)을 생성/갱신.

기상청 단기예보(02·05·08·11·14·17·20·23시) + 중기예보(06·18시) 발표 시각에 맞춰
crontab이 이 스크립트를 돌린다. 결과 HTML은 nginx가 서빙하는 폴더에 저장되어
사용자는 /weather.html 로 항상 최신 전국 날씨 요약 페이지를 본다.
"""
import json
import os
import time
import html as htmllib
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/output")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "weather.html")
KST = timezone(timedelta(hours=9))

REGIONS = [
    "서울", "인천", "대전", "대구", "광주", "부산", "울산", "세종",
    "경기도", "강원도", "충청북도", "충청남도", "경상북도", "경상남도",
    "전라북도", "전라남도", "제주도",
]


def fetch_region(region, retries=4):
    """backend /api/weather 호출. 부팅 직후 backend 미준비 대비 재시도."""
    url = f"{BACKEND_URL}/api/weather?region=" + urllib.parse.quote(region)
    for i in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            print(f"[warn] {region} 조회 실패 ({i + 1}/{retries}): {e}", flush=True)
            time.sleep(3)
    return None


def esc(s):
    return htmllib.escape(str(s if s is not None else ""))


def render_region_card(data):
    region = esc(data.get("region", ""))
    days = data.get("days", [])
    cells = []
    for i, d in enumerate(days):
        today = (i == 0)
        cur = d.get("temp_current")
        cur_html = f'<div class="cur">{esc(cur)}°</div>' if (today and cur is not None) else ""
        cells.append(f"""
            <div class="day{' today' if today else ''}">
                <div class="lbl">{esc(d.get('label'))}</div>
                <div class="ico">{esc(d.get('icon'))}</div>
                <div class="wx">{esc(d.get('weather'))}</div>
                {cur_html}
                <div class="tmp"><span class="mx">{esc(d.get('temp_max'))}°</span>
                    <span class="dv">/</span>
                    <span class="mn">{esc(d.get('temp_min'))}°</span></div>
                <div class="pop">☔ {esc(d.get('pop'))}%</div>
            </div>""")
    return f"""
        <section class="card">
            <h2>{region}</h2>
            <div class="days">{''.join(cells)}</div>
        </section>"""


def render(all_data, now):
    cards = "".join(render_region_card(d) for d in all_data)
    ts = now.strftime("%Y-%m-%d %H:%M")
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>전국 날씨 요약</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, "Segoe UI", "Malgun Gothic", sans-serif;
         background: #0F172A; color: #E2E8F0; padding: 32px 20px 64px; }}
  .head {{ max-width: 1100px; margin: 0 auto 28px; }}
  .head h1 {{ font-size: 28px; font-weight: 900; color: #fff; letter-spacing: -0.5px; }}
  .head .meta {{ margin-top: 8px; font-size: 13px; color: #94A3B8; }}
  .head .meta b {{ color: #FDE68A; }}
  .head a {{ color: #818CF8; text-decoration: none; font-size: 13px; }}
  .grid {{ max-width: 1100px; margin: 0 auto;
          display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }}
  .card {{ background: linear-gradient(135deg, #1E3A8A 0%, #0369A1 100%);
          border-radius: 18px; padding: 16px 18px;
          box-shadow: 0 12px 32px rgba(3,105,161,.3); }}
  .card h2 {{ font-size: 16px; font-weight: 800; color: #fff; margin-bottom: 12px; }}
  .days {{ display: flex; }}
  .day {{ flex: 1 1 0; min-width: 0; text-align: center; padding: 4px 2px;
         border-right: 1px solid rgba(255,255,255,.12); }}
  .day:last-child {{ border-right: none; }}
  .day.today {{ flex: 1.3 1 0; background: rgba(255,255,255,.10);
               border-radius: 12px; border-right: none; }}
  .day.today + .day {{ border-left: 1px solid rgba(255,255,255,.12); }}
  .lbl {{ font-size: 10px; font-weight: 700; color: rgba(255,255,255,.55);
         margin-bottom: 4px; text-transform: uppercase; }}
  .day.today .lbl {{ color: #FDE68A; }}
  .ico {{ font-size: 22px; line-height: 1; margin-bottom: 3px; }}
  .day.today .ico {{ font-size: 28px; }}
  .wx {{ font-size: 10px; color: rgba(255,255,255,.8); margin-bottom: 4px; }}
  .cur {{ font-size: 20px; font-weight: 900; color: #fff; margin-bottom: 3px; }}
  .tmp {{ font-size: 12px; }}
  .mx {{ color: #FCA5A5; font-weight: 800; }}
  .mn {{ color: #BAE6FD; font-weight: 800; }}
  .dv {{ color: rgba(255,255,255,.35); }}
  .pop {{ font-size: 10px; color: rgba(255,255,255,.6); margin-top: 2px; }}
</style>
</head>
<body>
  <div class="head">
    <h1>🌤️ 전국 날씨 요약</h1>
    <div class="meta">마지막 갱신: <b>{ts} KST</b> · cron 자동 생성 ·
      <a href="/index.html">여행지 추천하러 가기 →</a></div>
  </div>
  <div class="grid">{cards}</div>
</body>
</html>"""


def main():
    now = datetime.now(KST)
    collected = []
    for region in REGIONS:
        d = fetch_region(region)
        if d and d.get("days"):
            collected.append(d)
    html_out = render(collected, now)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    tmp = OUTPUT_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(html_out)
    os.replace(tmp, OUTPUT_FILE)   # 원자적 교체(반쯤 쓰인 파일 노출 방지)
    print(f"[ok] {OUTPUT_FILE} 생성 ({len(collected)}/{len(REGIONS)} 지역) @ {now.isoformat()}",
          flush=True)


if __name__ == "__main__":
    main()
