from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import httpx
import os
import json
import logging
import google.generativeai as genai
from datetime import datetime, timedelta
from urllib.parse import unquote

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Travel Recommender API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WEATHER_API_KEY = unquote(os.getenv("WEATHER_API_KEY", ""))
TOUR_API_KEY = unquote(os.getenv("TOUR_API_KEY", ""))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

REGION_COORDS = {
    "서울": (60, 127), "인천": (55, 124), "대전": (67, 100),
    "대구": (89, 90), "광주": (58, 74), "부산": (98, 76),
    "울산": (102, 84), "세종": (66, 103), "경기도": (60, 121),
    "강원도": (73, 134), "충청북도": (69, 107), "충청남도": (68, 100),
    "경상북도": (89, 111), "경상남도": (91, 77), "전라북도": (63, 89),
    "전라남도": (51, 67), "제주도": (52, 38),
}

AREA_CODES = {
    "서울": 1, "인천": 2, "대전": 3, "대구": 4, "광주": 5,
    "부산": 6, "울산": 7, "세종": 8, "경기도": 31, "강원도": 32,
    "충청북도": 33, "충청남도": 34, "경상북도": 35, "경상남도": 36,
    "전라북도": 37, "전라남도": 38, "제주도": 39,
}

CONTENT_TYPE_NAMES = {
    12: "관광지", 14: "문화시설", 15: "축제/행사",
    28: "레포츠", 32: "숙박", 38: "쇼핑", 39: "음식점",
}

SKY_MAP = {1: ("맑음", "☀️"), 3: ("구름많음", "⛅"), 4: ("흐림", "☁️")}
PTY_MAP = {0: ("없음", ""), 1: ("비", "🌧️"), 2: ("비/눈", "🌨️"), 3: ("눈", "❄️"), 4: ("소나기", "🌦️")}


def get_forecast_base():
    now = datetime.now()
    hours = [2, 5, 8, 11, 14, 17, 20, 23]
    base_hour = None
    for h in hours:
        if now.hour >= h:
            base_hour = h
    if base_hour is None:
        yesterday = now - timedelta(days=1)
        return yesterday.strftime("%Y%m%d"), "2300"
    return now.strftime("%Y%m%d"), f"{base_hour:02d}00"


def map_answers_to_content_types(answers: List[str]) -> List[int]:
    # Q1: mountain/sea/city/heritage
    # Q2: activity/food/culture/healing
    # Q3: solo/couple/family/friends
    # Q4: sns/nature_q/experience/history
    # Q5: under30k/30to70k/70to150k/over150k

    env     = answers[0] if len(answers) > 0 else "mountain"
    style   = answers[1] if len(answers) > 1 else "healing"
    social  = answers[2] if len(answers) > 2 else "solo"
    interest = answers[3] if len(answers) > 3 else "nature_q"
    budget  = answers[4] if len(answers) > 4 else "30to70k"

    types = []

    # 환경 기반
    if env in ("mountain", "sea"):
        types.append(12)   # 관광지
    elif env == "heritage":
        types.append(14)   # 문화시설
    else:  # city
        types.append(39)   # 음식점

    # 스타일 기반
    if style == "activity":
        types.append(28)   # 레포츠
    elif style == "food":
        if 39 not in types:
            types.append(39)
    elif style == "culture":
        if 14 not in types:
            types.append(14)
    else:  # healing
        if 12 not in types:
            types.append(12)

    # 관심사 기반
    if interest == "experience":
        if 28 not in types:
            types.append(28)
    elif interest == "history":
        if 14 not in types:
            types.append(14)
    elif interest == "sns":
        if 12 not in types:
            types.append(12)

    # 동행 기반
    if social in ("family", "friends") and 15 not in types:
        types.append(15)   # 축제/행사

    # 예산 기반 보정
    if budget == "over150k":
        if 32 not in types:
            types.append(32)  # 숙박
    elif budget == "under30k":
        if 12 not in types:
            types.append(12)

    # 관광지(12) 항상 포함
    if 12 not in types:
        types.insert(0, 12)

    return list(dict.fromkeys(types))[:3]


ANSWER_LABELS = {
    "mountain": "산·숲·계곡", "sea": "바다·해변", "city": "도심·거리·핫플", "heritage": "고궁·사찰·유적지",
    "activity": "액티비티·스포츠", "food": "미식·맛집 탐방", "culture": "문화·예술 감상", "healing": "휴양·힐링",
    "solo": "혼자", "couple": "연인", "family": "가족(아이 포함)", "friends": "친구·단체",
    "sns": "인증샷·SNS 핫플", "nature_q": "자연·경관 감상", "experience": "체험·참여 활동", "history": "역사·교육",
    "under30k": "3만원 이하", "30to70k": "3~7만원", "70to150k": "7~15만원", "over150k": "15만원 이상",
}

Q_LABELS = ["여행 분위기", "하고 싶은 것", "동행", "중요하게 생각하는 것", "하루 예산(숙박 제외)"]


async def refine_with_claude(places: list, answers: List[str], region: str) -> list:
    if not GEMINI_API_KEY or not places:
        return places

    profile_lines = []
    for i, ans in enumerate(answers):
        label = Q_LABELS[i] if i < len(Q_LABELS) else f"Q{i+1}"
        val = ANSWER_LABELS.get(ans, ans)
        profile_lines.append(f"- {label}: {val}")
    profile = "\n".join(profile_lines)

    places_json = json.dumps(
        [{"index": i, "title": p["title"], "address": p["address"], "content_type": p["content_type"]} for i, p in enumerate(places)],
        ensure_ascii=False
    )

    prompt = f"""당신은 국내 여행 전문가입니다. 아래 여행자 프로필과 후보 여행지 목록을 보고, 이 여행자에게 가장 잘 맞는 여행지 최대 9곳을 선별해 주세요.

## 여행자 프로필
지역: {region}
{profile}

## 후보 여행지 (JSON)
{places_json}

## 출력 형식 (JSON 배열만, 다른 텍스트 없이)
[
  {{"index": 숫자, "reason": "이 여행자에게 맞는 이유 (한국어, 2문장 이내)"}},
  ...
]

중요: JSON 배열만 출력하세요. 마크다운 코드블록(```)이나 설명 텍스트를 포함하지 마세요."""

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = await model.generate_content_async(prompt)
        raw = response.text.strip()

        # Gemini가 ```json ... ``` 블록으로 감쌀 때 벗겨냄
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        ranked = json.loads(raw)

        result = []
        seen_indices = set()
        for item in ranked:
            idx = item.get("index")
            if idx is None or idx in seen_indices or idx >= len(places):
                continue
            seen_indices.add(idx)
            place = dict(places[idx])
            place["reason"] = item.get("reason", "")
            result.append(place)

        for i, p in enumerate(places):
            if i not in seen_indices and len(result) < 9:
                place = dict(p)
                place["reason"] = ""
                result.append(place)

        return result[:9]

    except Exception as e:
        logging.error("Gemini API error: %s", e)
        return places


class RecommendRequest(BaseModel):
    region: str
    date: str
    answers: List[str]


@app.get("/api/debug/tour")
async def debug_tour(region: str = Query("서울")):
    """관광공사 API 원본 응답 확인용"""
    if not TOUR_API_KEY:
        return {"error": "TOUR_API_KEY 가 .env 에 없거나 비어있음"}

    area_code = AREA_CODES.get(region, 1)
    params = {
        "serviceKey": TOUR_API_KEY,
        "numOfRows": 5,
        "pageNo": 1,
        "MobileOS": "ETC",
        "MobileApp": "TravelApp",
        "_type": "json",
        "areaCode": area_code,
        "contentTypeId": 12,
        "arrange": "C",
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://apis.data.go.kr/B551011/KorService2/areaBasedList2",
                params=params, timeout=15
            )
            try:
                body = resp.json()
            except Exception:
                body = resp.text[:1000]
            return {
                "status_code": resp.status_code,
                "request_url": str(resp.url),
                "key_length": len(TOUR_API_KEY),
                "key_preview": TOUR_API_KEY[:12] + "...",
                "response": body,
            }
    except Exception as e:
        return {"error": str(e), "key_length": len(TOUR_API_KEY)}


@app.get("/api/regions")
async def get_regions():
    return {"regions": list(REGION_COORDS.keys())}


@app.get("/api/weather")
async def get_weather(region: str = Query(...), date: str = Query(...)):
    if region not in REGION_COORDS:
        raise HTTPException(400, f"지원하지 않는 지역: {region}")

    try:
        target_date = datetime.strptime(date, "%Y%m%d")
    except ValueError:
        raise HTTPException(400, "날짜 형식 오류 (YYYYMMDD)")

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    diff = (target_date - today).days

    if diff < 0:
        raise HTTPException(400, "과거 날짜는 조회할 수 없습니다.")
    if diff > 3:
        raise HTTPException(400, "단기예보는 오늘부터 3일 이내만 가능합니다.")

    nx, ny = REGION_COORDS[region]
    base_date, base_time = get_forecast_base()

    params = {
        "serviceKey": WEATHER_API_KEY,
        "pageNo": 1,
        "numOfRows": 1000,
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny,
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst",
                params=params, timeout=15
            )
            data = resp.json()
        except Exception as e:
            raise HTTPException(503, f"날씨 API 오류: {str(e)}")

    result_code = data.get("response", {}).get("header", {}).get("resultCode", "")
    if result_code != "00":
        msg = data.get("response", {}).get("header", {}).get("resultMsg", "API 오류")
        raise HTTPException(502, f"날씨 API: {msg}")

    items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
    target_str = target_date.strftime("%Y%m%d")

    weather_by_time = {}
    for item in items:
        if item.get("fcstDate") == target_str:
            cat = item.get("category")
            t = item.get("fcstTime")
            if cat in ("SKY", "PTY", "TMP", "REH", "POP"):
                if t not in weather_by_time:
                    weather_by_time[t] = {}
                weather_by_time[t][cat] = item.get("fcstValue")

    weather_data = weather_by_time.get("1200") or (
        list(weather_by_time.values())[0] if weather_by_time else {}
    )

    if not weather_data:
        raise HTTPException(404, "해당 날짜의 예보 데이터가 없습니다.")

    sky_val = int(weather_data.get("SKY", 1))
    pty_val = int(weather_data.get("PTY", 0))
    sky_desc, sky_icon = SKY_MAP.get(sky_val, ("알 수 없음", "🌤️"))
    pty_desc, pty_icon = PTY_MAP.get(pty_val, ("없음", ""))

    return {
        "region": region,
        "date": date,
        "icon": pty_icon if pty_val > 0 else sky_icon,
        "weather": pty_desc if pty_val > 0 else sky_desc,
        "temperature": weather_data.get("TMP", "N/A"),
        "humidity": weather_data.get("REH", "N/A"),
        "pop": weather_data.get("POP", "N/A"),
    }


@app.post("/api/recommend")
async def get_recommendations(req: RecommendRequest):
    if req.region not in AREA_CODES:
        raise HTTPException(400, f"지원하지 않는 지역: {req.region}")

    area_code = AREA_CODES[req.region]
    content_types = map_answers_to_content_types(req.answers)
    all_places = []

    async with httpx.AsyncClient() as client:
        for ct_id in content_types:
            params = {
                "serviceKey": TOUR_API_KEY,
                "numOfRows": 10,
                "pageNo": 1,
                "MobileOS": "ETC",
                "MobileApp": "TravelApp",
                "_type": "json",
                "areaCode": area_code,
                "contentTypeId": ct_id,
                "arrange": "C",
            }
            try:
                resp = await client.get(
                    "https://apis.data.go.kr/B551011/KorService2/areaBasedList2",
                    params=params, timeout=15
                )
                logging.info("TOUR API status=%s url=%s", resp.status_code, resp.url)
                data = resp.json()
                logging.info("TOUR API response=%s", str(data)[:500])
            except Exception as e:
                logging.error("TOUR API exception: %s", e)
                continue

            result_code = data.get("response", {}).get("header", {}).get("resultCode", "")
            result_msg = data.get("response", {}).get("header", {}).get("resultMsg", "")
            if result_code != "0000":
                logging.warning("TOUR API resultCode=%s msg=%s", result_code, result_msg)

            items = data.get("response", {}).get("body", {}).get("items", {})
            if not items or not isinstance(items, dict) or not items.get("item"):
                logging.info("TOUR API no items for contentTypeId=%s areaCode=%s", ct_id, area_code)
                continue

            item_list = items["item"]
            if isinstance(item_list, dict):
                item_list = [item_list]

            for item in item_list[:5]:
                all_places.append({
                    "title": item.get("title", ""),
                    "address": (item.get("addr1", "") + " " + item.get("addr2", "")).strip(),
                    "image": item.get("firstimage", ""),
                    "content_type": CONTENT_TYPE_NAMES.get(ct_id, "관광지"),
                    "tel": item.get("tel", ""),
                    "mapx": item.get("mapx", ""),
                    "mapy": item.get("mapy", ""),
                    "contentid": item.get("contentid", ""),
                    "contenttypeid": ct_id,
                })

    seen = set()
    unique = []
    for p in all_places:
        if p["title"] and p["title"] not in seen:
            seen.add(p["title"])
            unique.append(p)

    refined = await refine_with_claude(unique, req.answers, req.region)

    return {
        "region": req.region,
        "date": req.date,
        "places": refined,
        "total": len(refined),
    }


@app.get("/api/debug/detail")
async def debug_detail(contentid: str = Query("126508"), contenttypeid: int = Query(12)):
    """상세정보 API 원본 응답 확인용"""
    if not TOUR_API_KEY:
        return {"error": "TOUR_API_KEY 없음"}
    params = {
        "serviceKey": TOUR_API_KEY,
        "MobileOS": "ETC",
        "MobileApp": "TravelApp",
        "_type": "json",
        "contentId": contentid,
    }
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                "https://apis.data.go.kr/B551011/KorService2/detailCommon2",
                params=params, timeout=15
            )
            try:
                body = resp.json()
            except Exception:
                body = resp.text[:2000]
            return {"status_code": resp.status_code, "request_url": str(resp.url), "response": body}
        except Exception as e:
            return {"error": str(e)}


@app.get("/api/detail")
async def get_detail(contentid: str = Query(...), contenttypeid: int = Query(...)):
    if not TOUR_API_KEY:
        raise HTTPException(503, "TOUR_API_KEY 없음")

    params = {
        "serviceKey": TOUR_API_KEY,
        "MobileOS": "ETC",
        "MobileApp": "TravelApp",
        "_type": "json",
        "contentId": contentid,
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                "https://apis.data.go.kr/B551011/KorService2/detailCommon2",
                params=params, timeout=15
            )
            data = resp.json()
            logging.info("DETAIL API contentid=%s status=%s body=%s", contentid, resp.status_code, str(data)[:500])
        except Exception as e:
            logging.error("DETAIL API exception: %s", e)
            raise HTTPException(503, f"관광 API 오류: {str(e)}")

    # KorService2는 오류 시 flat 구조로 반환
    if "resultCode" in data and data.get("resultCode") != "00":
        raise HTTPException(502, f"관광 API 오류: {data.get('resultMsg', '')}")

    result_code = data.get("response", {}).get("header", {}).get("resultCode", "")
    result_msg = data.get("response", {}).get("header", {}).get("resultMsg", "")
    logging.info("DETAIL API resultCode=%s msg=%s", result_code, result_msg)

    if result_code not in ("0000", "00", ""):
        raise HTTPException(502, f"관광 API 오류: {result_msg}")

    body = data.get("response", {}).get("body", {})
    items = body.get("items", {})
    if not items or not isinstance(items, dict):
        raise HTTPException(404, "상세정보가 없습니다.")

    item = items.get("item")
    if not item:
        raise HTTPException(404, "상세정보가 없습니다.")
    if isinstance(item, list):
        item = item[0]
    if not isinstance(item, dict):
        raise HTTPException(404, "상세정보가 없습니다.")

    return {
        "title": item.get("title", ""),
        "address": (item.get("addr1", "") + " " + item.get("addr2", "")).strip(),
        "tel": item.get("tel", ""),
        "image": item.get("firstimage", ""),
        "image2": item.get("firstimage2", ""),
        "homepage": item.get("homepage", ""),
        "overview": item.get("overview", ""),
        "mapx": item.get("mapx", ""),
        "mapy": item.get("mapy", ""),
        "contenttypeid": contenttypeid,
    }
