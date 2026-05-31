# 🗺️ 국내 여행지 추천 서비스

날짜와 지역을 선택하고 5가지 취향 질문에 답하면, 날씨 정보와 함께 나에게 딱 맞는 국내 여행지를 추천해주는 웹 서비스입니다.

---

## 주요 기능

- **날씨 예보** — 기상청 단기예보 API를 통해 여행 날짜의 날씨(기온, 습도, 강수확률) 제공
- **취향 기반 추천** — 여행 분위기, 하고 싶은 것 등 취향 질문으로 맞춤 여행지 추천
- **상세정보 조회** — 카드 클릭 시 모달로 여행지 소개, 이미지, 주소, 홈페이지, 네이버 지도 링크 제공

---

## 서비스 흐름

```
지역 + 날짜 선택
       ↓
취향 질문 응답
       ↓
기상청 API → 날씨 정보 조회
한국관광공사 API → 후보 여행지 수집
       ↓
결과 페이지: 날씨 카드 + 추천 여행지 카드
       ↓
카드 클릭 → 상세정보 모달
```

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| Frontend | HTML / CSS / Vanilla JS |
| Backend | Python FastAPI |
| 외부 API | 기상청 단기예보 API, 한국관광공사 KorService2 API |
| 인프라 | Docker, Docker Compose, Nginx |

---

## 필요한 API 키

| API | 발급처 | 비용 |
|-----|--------|------|
| 기상청 단기예보 | [공공데이터포털](https://www.data.go.kr) | 무료 |
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
docker-compose up --build
```

브라우저에서 `http://localhost` 접속

---

## 프로젝트 구조

```
travel-recommender/
├── backend/
│   ├── main.py          # FastAPI 서버 (날씨, 관광 추천 API)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html       # 단일 페이지 구조
│   ├── style.css        # 전체 스타일
│   └── app.js           # 화면 전환, API 통신, 모달
├── nginx/
│   └── nginx.conf       # 정적 파일 서빙 + API 프록시
├── docker-compose.yml
├── .env.example
└── .gitignore
```

---

## 지원 지역

서울, 인천, 대전, 대구, 광주, 부산, 울산, 세종,
경기도, 강원도, 충청북도, 충청남도, 경상북도, 경상남도, 전라북도, 전라남도, 제주도

> 날씨 예보는 오늘부터 3일 이내 날짜만 제공됩니다.
