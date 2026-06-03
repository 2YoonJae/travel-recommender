# 🗺️ 국내 여행지 추천 서비스

날짜와 지역을 선택하고 3가지 취향 질문에 답하면, 날씨 정보와 함께 나에게 딱 맞는 국내 여행지를 추천해주는 웹 서비스입니다.

---

## 주요 기능

- **날씨 예보** — 기상청 단기예보 + 중기예보 API로 오늘부터 7일치 날씨(기온, 현재 온도, 강수확률) 제공
- **취향 기반 추천** — 여행지·활동·날씨 3가지 질문으로 맞춤 여행지 추천
  - Q1 "어떤 여행지를 찾으세요?" (산/바다/도심/유적)
  - Q2 "여행에서 무엇을 하고 싶나요?" (액티비티/미식/문화/힐링)
  - Q3 "어떤 날씨를 원하나요?" (맑음/비/흐림/눈)
- **날씨 기반 정렬** — 실제 예보에 맞춰 맑음→야외, 비·눈→실내 우선 배치(없으면 보강), 흐림→중립
- **희망 날씨 매칭** — 원한 날씨를 예보와 대조. 7일 내 맞는 날이 없으면 다른 여행지/날씨 안내
- **전국 날씨 요약** — cron이 기상청 발표시각마다 17개 시·도 날씨 요약 페이지(`weather.html`)를 자동 생성/갱신
- **상세정보 조회** — 카드 클릭 시 모달로 여행지 소개, 이미지, 주소, 홈페이지, 네이버 지도 링크 제공

---

## 서비스 흐름

```
지역 + 날짜 선택 (오늘~7일)
       ↓
3가지 취향 질문 응답
       ↓
기상청 API → 날씨 정보 조회 (캐시 우선)
한국관광공사 API → 후보 여행지 수집
       ↓
결과 페이지: 7일 날씨 카드(선택일 강조 + 헤더에 현재 온도) + 추천 여행지 카드
       ↓
카드 클릭 → 상세정보 모달
```

별도로, **cron 데몬**이 발표시각마다 전국 날씨 요약 HTML을 미리 생성(사전 렌더링/캐싱)하여 `/weather.html` 로 서빙합니다. 사용자 접속 시 외부 API 호출 없이 완성된 정적 파일을 즉시 받습니다.

```
[cron 데몬] 기상청 발표시각(+15분, 하루 10회)
       ↓
generate_weather_html.py → 17개 지역 날씨 조회 → weather.html 생성/갱신(원자적 교체)
       ↓
nginx 서빙 → http://localhost:2735/weather.html
```

> 단기예보(02·05·08·11·14·17·20·23시)와 중기예보(06·18시) 발표 시각을 합쳐 하루 10회 실행하며, 매 실행 시 단기+중기를 모두 받아 전체를 다시 생성합니다.

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| Frontend | HTML / CSS / Vanilla JS |
| Backend | Python FastAPI |
| 스케줄링 | cron (전국 날씨 HTML 생성), APScheduler (백엔드 날씨 캐싱) |
| 외부 API | 기상청 단기예보 + 중기예보 API, 한국관광공사 KorService2 API |
| 인프라 | Docker, Docker Compose, Nginx |

---

## 필요한 API 키

| API | 발급처 | 비용 |
|-----|--------|------|
| 기상청 단기예보 / 중기예보 | [공공데이터포털](https://www.data.go.kr) | 무료 |
| 한국관광공사 국문 관광정보 서비스 | [공공데이터포털](https://www.data.go.kr) | 무료 |

---

## 실행 방법

### 1. 레포지토리 클론

```bash
git clone https://github.com/2YoonJae/travel-recommender.git
cd travel-recommender
```

### 2. 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열어 API 키 입력:

```
WEATHER_API_KEY=기상청_API_키
TOUR_API_KEY=한국관광공사_API_키
```

> 공공데이터포털에서 발급받은 **URL 인코딩된 키**를 그대로 붙여넣으세요.

### 3. Docker로 실행

```bash
docker compose up --build
```

- 여행지 추천: `http://localhost:2735`
- 전국 날씨 요약: `http://localhost:2735/weather.html`

> 호스트 포트는 `docker-compose.yml`의 nginx `ports`에서 변경할 수 있습니다(예: 다른 서버와 80/8080 충돌 회피용 `2735:80`).

---

## 프로젝트 구조

```
travel-recommender/
├── backend/
│   ├── main.py          # FastAPI 서버 (날씨/관광 API + APScheduler 날씨 캐싱)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html       # 단일 페이지 구조 (추천 앱)
│   ├── style.css        # 전체 스타일
│   ├── app.js           # 화면 전환, API 통신, 모달
│   └── weather.html     # cron이 자동 생성하는 전국 날씨 요약 (런타임 생성물, 빌드 산출물)
├── cron/
│   ├── Dockerfile
│   ├── weather-cron               # crontab (발표시각마다 실행)
│   ├── entrypoint.sh              # 시작 시 1회 생성 후 cron 데몬 포그라운드
│   └── generate_weather_html.py   # 날씨 조회 → weather.html 생성
├── nginx/
│   └── Dockerfile       # nginx 이미지 (정적 서빙 + /api 프록시 설정 내장)
├── docker-compose.yml   # backend + cron + nginx 오케스트레이션
├── .gitattributes       # cron 스크립트 LF 고정
├── .env.example
└── .gitignore
```

> nginx 설정은 별도 `.conf` 파일 없이 `nginx/Dockerfile` 안에 직접 내장(`COPY <<EOF`)되어 있습니다.

---

## 지원 지역

서울, 인천, 대전, 대구, 광주, 부산, 울산, 세종,
경기도, 강원도, 충청북도, 충청남도, 경상북도, 경상남도, 전라북도, 전라남도, 제주도

> 날씨 예보는 오늘부터 7일 이내 날짜만 제공됩니다.
