from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import asyncio
import httpx
import os
import logging
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

MID_WEATHER_ICONS = {
    "맑음": "☀️", "구름많음": "⛅", "구름많고 비": "🌦️",
    "구름많고 눈": "🌨️", "구름많고 비/눈": "🌨️", "흐림": "☁️",
    "흐리고 비": "🌧️", "흐리고 눈": "❄️", "흐리고 비/눈": "🌨️",
    "흐리고 눈/비": "🌨️",
}

MID_LAND_CODES = {
    "서울": "11B00000", "인천": "11B00000", "경기도": "11B00000",
    "강원도": "11D10000",
    "충청북도": "11C10000",
    "충청남도": "11C20000", "대전": "11C20000", "세종": "11C20000",
    "전라북도": "11F10000",
    "전라남도": "11F20000", "광주": "11F20000",
    "경상북도": "11H10000", "대구": "11H10000",
    "경상남도": "11H20000", "부산": "11H20000", "울산": "11H20000",
    "제주도": "11G00000",
}

MID_TA_CODES = {
    "서울": "11B10101", "인천": "11B20201", "대전": "11C20401",
    "대구": "11H10701", "광주": "11F20501", "부산": "11H20201",
    "울산": "11H20101", "세종": "11C20404", "경기도": "11B20601",
    "강원도": "11D10301", "충청북도": "11C10301", "충청남도": "11C20101",
    "경상북도": "11H10201", "경상남도": "11H20301",
    "전라북도": "11F10201", "전라남도": "11F20401", "제주도": "11G00201",
}


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


def get_kst_now():
    return datetime.utcnow() + timedelta(hours=9)


def get_mid_forecast_base():
    now = get_kst_now()
    if now.hour >= 18:
        return now.strftime("%Y%m%d") + "1800"
    elif now.hour >= 6:
        return now.strftime("%Y%m%d") + "0600"
    else:
        return (now - timedelta(days=1)).strftime("%Y%m%d") + "1800"


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


@app.get("/api/debug/midweather")
async def debug_mid_weather(region: str = Query("서울")):
    tmFc = get_mid_forecast_base()
    land_code = MID_LAND_CODES.get(region, "11B00000")
    ta_code = MID_TA_CODES.get(region, "11B10101")
    async with httpx.AsyncClient() as client:
        lr, tr = await asyncio.gather(
            client.get(
                "http://apis.data.go.kr/1360000/MidFcstInfoService/getMidLandFcst",
                params={"serviceKey": WEATHER_API_KEY, "pageNo": 1, "numOfRows": 10,
                        "dataType": "JSON", "regId": land_code, "tmFc": tmFc},
                timeout=15
            ),
            client.get(
                "http://apis.data.go.kr/1360000/MidFcstInfoService/getMidTa",
                params={"serviceKey": WEATHER_API_KEY, "pageNo": 1, "numOfRows": 10,
                        "dataType": "JSON", "regId": ta_code, "tmFc": tmFc},
                timeout=15
            ),
        )
    def safe_json(r):
        try:
            return r.json()
        except Exception:
            return r.text[:2000]

    return {
        "tmFc": tmFc,
        "land_code": land_code,
        "ta_code": ta_code,
        "land_url": str(lr.url),
        "land_status": lr.status_code,
        "ta_status": tr.status_code,
        "land_response": safe_json(lr),
        "ta_response": safe_json(tr),
    }


@app.get("/api/weather")
async def get_weather(region: str = Query(...)):
    if region not in REGION_COORDS:
        raise HTTPException(400, f"지원하지 않는 지역: {region}")

    today = get_kst_now().replace(hour=0, minute=0, second=0, microsecond=0)
    short_dates = [(today + timedelta(days=i)).strftime("%Y%m%d") for i in range(4)]

    # ── 단기예보 (오늘~모레) ──────────────────────────────────────────
    nx, ny = REGION_COORDS[region]
    base_date, base_time = get_forecast_base()

    short_params = {
        "serviceKey": WEATHER_API_KEY,
        "pageNo": 1, "numOfRows": 1000, "dataType": "JSON",
        "base_date": base_date, "base_time": base_time,
        "nx": nx, "ny": ny,
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst",
                params=short_params, timeout=15
            )
            short_data = resp.json()
        except Exception as e:
            raise HTTPException(503, f"단기예보 API 오류: {str(e)}")

    rc = short_data.get("response", {}).get("header", {}).get("resultCode", "")
    if rc != "00":
        msg = short_data.get("response", {}).get("header", {}).get("resultMsg", "API 오류")
        raise HTTPException(502, f"단기예보 API: {msg}")

    short_items = short_data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
    by_date = {d: {"times": {}, "tmx": None, "tmn": None} for d in short_dates}

    for item in short_items:
        fd = item.get("fcstDate")
        if fd not in by_date:
            continue
        cat, t, val = item.get("category"), item.get("fcstTime"), item.get("fcstValue")
        if cat == "TMX":
            by_date[fd]["tmx"] = val
        elif cat == "TMN":
            by_date[fd]["tmn"] = val
        elif cat in ("SKY", "PTY", "TMP", "POP"):
            by_date[fd]["times"].setdefault(t, {})[cat] = val

    short_day_labels = ["오늘", "내일", "모레",
                        f"{(today + timedelta(days=3)).month}/{(today + timedelta(days=3)).day}"]
    days = []
    for i, d in enumerate(short_dates):
        entry = by_date[d]
        times = entry["times"]
        noon = times.get("1200") or (list(times.values())[0] if times else {})
        sky_val = int(noon.get("SKY", 1))
        pty_val = int(noon.get("PTY", 0))
        sky_desc, sky_icon = SKY_MAP.get(sky_val, ("맑음", "☀️"))
        pty_desc, pty_icon = PTY_MAP.get(pty_val, ("없음", ""))
        tmp_vals = [float(v["TMP"]) for v in times.values() if v.get("TMP")]
        tmx = entry["tmx"] if entry["tmx"] is not None else (str(int(max(tmp_vals))) if tmp_vals else "N/A")
        tmn = entry["tmn"] if entry["tmn"] is not None else (str(int(min(tmp_vals))) if tmp_vals else "N/A")
        pop_vals = [int(v["POP"]) for v in times.values() if v.get("POP")]
        days.append({
            "label": short_day_labels[i],
            "date": d,
            "icon": pty_icon if pty_val > 0 else sky_icon,
            "weather": pty_desc if pty_val > 0 else sky_desc,
            "temp_max": tmx,
            "temp_min": tmn,
            "pop": max(pop_vals) if pop_vals else 0,
        })

    # ── 중기예보 (D+3 ~ D+9) ─────────────────────────────────────────
    tmFc = get_mid_forecast_base()
    land_code = MID_LAND_CODES.get(region)
    ta_code = MID_TA_CODES.get(region)

    def extract_mid_item(data: dict):
        rc = data.get("response", {}).get("header", {}).get("resultCode", "")
        msg = data.get("response", {}).get("header", {}).get("resultMsg", "")
        logging.info("중기예보 resultCode=%s msg=%s", rc, msg)
        item = data.get("response", {}).get("body", {}).get("items", {}).get("item")
        if isinstance(item, list):
            return item[0] if item else None
        if isinstance(item, dict):
            return item
        return None

    mid_land, mid_ta = None, None
    if land_code and ta_code:
        async with httpx.AsyncClient() as mid_client:
            try:
                lr, tr = await asyncio.gather(
                    mid_client.get(
                        "http://apis.data.go.kr/1360000/MidFcstInfoService/getMidLandFcst",
                        params={"serviceKey": WEATHER_API_KEY, "pageNo": 1, "numOfRows": 10,
                                "dataType": "JSON", "regId": land_code, "tmFc": tmFc},
                        timeout=15
                    ),
                    mid_client.get(
                        "http://apis.data.go.kr/1360000/MidFcstInfoService/getMidTa",
                        params={"serviceKey": WEATHER_API_KEY, "pageNo": 1, "numOfRows": 10,
                                "dataType": "JSON", "regId": ta_code, "tmFc": tmFc},
                        timeout=15
                    ),
                )
                land_data, ta_data = lr.json(), tr.json()
                logging.info("중기육상 raw=%s", str(land_data)[:300])
                logging.info("중기기온 raw=%s", str(ta_data)[:300])
                mid_land = extract_mid_item(land_data)
                mid_ta = extract_mid_item(ta_data)
                logging.info("mid_land keys=%s", list(mid_land.keys())[:8] if mid_land else None)
                logging.info("mid_ta keys=%s", list(mid_ta.keys())[:8] if mid_ta else None)
            except Exception as e:
                logging.error("중기예보 API 예외: %s", e)

    # tmFc 기준일 계산 (YYYYMMDD0600 or YYYYMMDD1800)
    tmFc_date = datetime.strptime(tmFc[:8], "%Y%m%d").replace(hour=0, minute=0, second=0, microsecond=0)

    for offset in range(4, 10):
        _d = today + timedelta(days=offset)
        d = _d.strftime("%Y%m%d")
        label = f"{_d.month}/{_d.day}"
        # tmFc 기준일로부터 며칠 뒤인지 계산
        m = ((_d - tmFc_date).days)

        if mid_land and mid_ta and 3 <= m <= 10:
            wf_am = mid_land.get(f"wf{m}Am", "") or mid_land.get(f"wf{m}", "")
            wf_pm = mid_land.get(f"wf{m}Pm", "") or wf_am
            wf = wf_pm or wf_am or "맑음"
            icon = MID_WEATHER_ICONS.get(wf, "🌤️")
            pop_am = int(mid_land.get(f"rnSt{m}Am", 0) or 0)
            pop_pm = int(mid_land.get(f"rnSt{m}Pm", 0) or mid_land.get(f"rnSt{m}", 0) or 0)
            pop = max(pop_am, pop_pm)
            tmx = str(mid_ta.get(f"taMax{m}", "N/A"))
            tmn = str(mid_ta.get(f"taMin{m}", "N/A"))
        else:
            wf, icon, pop, tmx, tmn = "-", "🌤️", 0, "-", "-"

        days.append({
            "label": label,
            "date": d,
            "icon": icon,
            "weather": wf,
            "temp_max": tmx,
            "temp_min": tmn,
            "pop": pop,
        })

    return {"region": region, "days": days}


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

    return {
        "region": req.region,
        "date": req.date,
        "places": unique[:9],
        "total": len(unique[:9]),
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
