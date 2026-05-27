const REGIONS = [
    "서울", "인천", "대전", "대구", "광주", "부산", "울산", "세종",
    "경기도", "강원도", "충청북도", "충청남도", "경상북도", "경상남도",
    "전라북도", "전라남도", "제주도"
];

const CONTENT_ICONS = {
    "관광지": "🗺️", "문화시설": "🏛️", "축제/행사": "🎉",
    "레포츠": "🏄", "숙박": "🏨", "쇼핑": "🛍️", "음식점": "🍜"
};

const QUESTIONS = [
    {
        text: "어떤 분위기의 여행지를 원하나요?",
        options: [
            { value: "mountain", icon: "🏔️", label: "산·숲·계곡",    desc: "트레킹, 계곡, 청정 자연" },
            { value: "sea",      icon: "🌊", label: "바다·해변",      desc: "해수욕, 일몰, 해안 드라이브" },
            { value: "city",     icon: "🏙️", label: "도심·거리·핫플", desc: "카페거리, 쇼핑, 야경" },
            { value: "heritage", icon: "🏯", label: "고궁·사찰·유적지", desc: "역사 탐방, 전통 문화" }
        ]
    },
    {
        text: "여행에서 가장 하고 싶은 것은?",
        options: [
            { value: "activity", icon: "🏄", label: "액티비티·스포츠", desc: "서핑, 래프팅, 클라이밍" },
            { value: "food",     icon: "🍽️", label: "미식·맛집 탐방",  desc: "로컬 맛집, 특산 음식" },
            { value: "culture",  icon: "🎨", label: "문화·예술 감상",   desc: "미술관, 전시, 공연" },
            { value: "healing",  icon: "😌", label: "휴양·힐링",        desc: "온천, 펜션, 느긋한 산책" }
        ]
    },
    {
        text: "누구와 함께 여행하나요?",
        options: [
            { value: "solo",    icon: "🧑",        label: "혼자",          desc: "자유롭게 내 페이스로" },
            { value: "couple",  icon: "👫",        label: "연인",          desc: "둘만의 로맨틱 여행" },
            { value: "family",  icon: "👨‍👩‍👧‍👦", label: "가족 (아이 포함)", desc: "온 가족 체험·놀이 중심" },
            { value: "friends", icon: "👥",        label: "친구·단체",     desc: "왁자지껄 함께 즐기기" }
        ]
    },
    {
        text: "여행에서 특히 중요하게 생각하는 것은?",
        options: [
            { value: "sns",        icon: "📸", label: "인증샷·SNS 핫플", desc: "사진 잘 나오는 명소 위주" },
            { value: "nature_q",   icon: "🌿", label: "자연·경관 감상",   desc: "조용하고 아름다운 풍경" },
            { value: "experience", icon: "🎭", label: "체험·참여 활동",   desc: "직접 만들고 배우는 여행" },
            { value: "history",    icon: "📚", label: "역사·교육",        desc: "배움이 있는 의미 있는 여행" }
        ]
    },
    {
        text: "하루 여행 예산은? (1인 기준, 숙박 제외)",
        options: [
            { value: "under30k",   icon: "💚", label: "3만원 이하",    desc: "무료·저렴한 명소 위주" },
            { value: "30to70k",    icon: "💛", label: "3만원 ~ 7만원", desc: "식사 + 입장료 포함" },
            { value: "70to150k",   icon: "🧡", label: "7만원 ~ 15만원", desc: "액티비티·체험 포함" },
            { value: "over150k",   icon: "❤️", label: "15만원 이상",    desc: "프리미엄 식사·코스 여행" }
        ]
    }
];

const state = {
    region: "",
    date: "",
    answers: [],
    weather: null,
    questionIndex: 0,
};

// ─── Init ───────────────────────────────────────────────────────────
function getLocalDateString(offsetDays = 0) {
    const d = new Date();
    d.setDate(d.getDate() + offsetDays);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
}

document.addEventListener("DOMContentLoaded", () => {
    const select = document.getElementById("region-select");
    REGIONS.forEach(r => {
        const opt = document.createElement("option");
        opt.value = r;
        opt.textContent = r;
        select.appendChild(opt);
    });

    const dateInput = document.getElementById("date-input");
    const dateError = document.getElementById("date-error");
    dateInput.min = getLocalDateString(0);

    dateInput.addEventListener("change", () => {
        if (dateInput.value && dateInput.value > getLocalDateString(14)) {
            dateError.style.display = "block";
            dateInput.style.borderColor = "#EF4444";
        } else {
            dateError.style.display = "none";
            dateInput.style.borderColor = "";
        }
    });
});

// ─── Navigation ─────────────────────────────────────────────────────
function showStep(id) {
    document.querySelectorAll(".step").forEach(s => s.classList.remove("active"));
    document.getElementById(id).classList.add("active");
    window.scrollTo(0, 0);
}

// ─── Step 1 ─────────────────────────────────────────────────────────
async function handleStep1() {
    const region = document.getElementById("region-select").value;
    const dateVal = document.getElementById("date-input").value;

    if (!region) return showToast("여행지를 선택해주세요.");
    if (!dateVal) return showToast("날짜를 선택해주세요.");

    const maxDate = getLocalDateString(14);
    if (dateVal > maxDate) {
        const dateError = document.getElementById("date-error");
        const dateInput = document.getElementById("date-input");
        dateError.style.display = "block";
        dateInput.style.borderColor = "#EF4444";
        dateInput.scrollIntoView({ behavior: "smooth", block: "center" });
        return;
    }
    document.getElementById("date-error").style.display = "none";
    document.getElementById("date-input").style.borderColor = "";

    state.region = region;
    state.date = dateVal.replace(/-/g, "");
    state.answers = [];
    state.questionIndex = 0;
    state.weather = null;

    fetchWeather(state.region, state.date);
    showQuestion(0);
}

async function fetchWeather(region, date) {
    try {
        const resp = await fetch(`/api/weather?region=${encodeURIComponent(region)}&date=${date}`);
        if (resp.ok) {
            state.weather = await resp.json();
        }
    } catch (_) {
        state.weather = null;
    }
}

// ─── Questions ───────────────────────────────────────────────────────
function showQuestion(index) {
    state.questionIndex = index;
    const q = QUESTIONS[index];

    const pct = (index / QUESTIONS.length) * 100;
    document.getElementById("progress-fill").style.width = pct + "%";
    document.getElementById("progress-text").textContent = `${index + 1} / ${QUESTIONS.length}`;
    document.getElementById("q-number").textContent = `Q${index + 1}`;
    document.getElementById("q-text").textContent = q.text;

    const grid = document.getElementById("q-options");
    grid.className = "options-grid" + (q.options.length === 4 ? " four" : "");
    grid.innerHTML = q.options.map(opt => `
        <div class="option-card" onclick="selectAnswer('${opt.value}')">
            <span class="option-icon">${opt.icon}</span>
            <div class="option-label">${opt.label}</div>
            <div class="option-desc">${opt.desc}</div>
        </div>
    `).join("");

    document.getElementById("back-btn").style.display = index === 0 ? "none" : "block";

    showStep("step-questions");
}

function selectAnswer(value) {
    state.answers[state.questionIndex] = value;

    if (state.questionIndex < QUESTIONS.length - 1) {
        showQuestion(state.questionIndex + 1);
    } else {
        loadResults();
    }
}

function goBack() {
    if (state.questionIndex > 0) {
        showQuestion(state.questionIndex - 1);
    } else {
        showStep("step-1");
    }
}

// ─── Results ────────────────────────────────────────────────────────
async function loadResults() {
    showStep("step-loading");

    // Let weather fetch finish (max 1s wait)
    await new Promise(r => setTimeout(r, 800));

    try {
        const resp = await fetch("/api/recommend", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                region: state.region,
                date: state.date,
                answers: state.answers,
            }),
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || "추천 데이터를 가져오지 못했습니다.");
        }

        const data = await resp.json();
        renderResults(state.weather, data.places);

    } catch (e) {
        showToast(e.message);
        showStep("step-1");
    }
}

function renderResults(weather, places) {
    document.getElementById("result-region").textContent = state.region;

    const y = state.date.slice(0, 4);
    const m = state.date.slice(4, 6);
    const d = state.date.slice(6, 8);
    const dateObj = new Date(`${y}-${m}-${d}`);
    document.getElementById("result-date").textContent =
        dateObj.toLocaleDateString("ko-KR", {
            year: "numeric", month: "long", day: "numeric", weekday: "short"
        }) + " 기준";

    // Weather
    const weatherEl = document.getElementById("weather-card");
    if (weather && weather.temperature) {
        weatherEl.innerHTML = `
            <div class="weather-icon-big">${weather.icon}</div>
            <div class="weather-info">
                <h3>${weather.region} · ${weather.weather}</h3>
                <div class="weather-temp">${weather.temperature}°C</div>
                <div class="weather-details">
                    <div class="weather-detail">💧 습도 <span>${weather.humidity}%</span></div>
                    <div class="weather-detail">☔ 강수확률 <span>${weather.pop}%</span></div>
                </div>
            </div>
        `;
    } else {
        weatherEl.innerHTML = `
            <div class="weather-unavailable">
                ⚠️ 날씨 정보를 불러올 수 없습니다 (단기예보는 오늘부터 3일 이내만 제공)
            </div>
        `;
    }

    // Places
    const placesEl = document.getElementById("places-grid");
    if (!places || places.length === 0) {
        placesEl.innerHTML = `
            <div class="no-results">
                😢 해당 조건의 여행지를 찾지 못했습니다.<br>
                다른 조건으로 다시 시도해보세요.
            </div>
        `;
    } else {
        placesEl.innerHTML = places.map(place => {
            const icon = CONTENT_ICONS[place.content_type] || "📍";
            const imgHtml = place.image
                ? `<img class="place-image" src="${escHtml(place.image)}" alt="${escHtml(place.title)}"
                        onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
                   <div class="place-placeholder" style="display:none">${icon}</div>`
                : `<div class="place-placeholder">${icon}</div>`;

            const cid = escHtml(place.contentid || "");
            const ctid = place.contenttypeid || 12;

            return `
                <div class="place-card" onclick="openDetail('${cid}', ${ctid}, '${escHtml(place.content_type)}')">
                    ${imgHtml}
                    <div class="place-body">
                        <span class="place-type">${escHtml(place.content_type)}</span>
                        <div class="place-title">${escHtml(place.title)}</div>
                        ${place.address ? `<div class="place-address">📍 ${escHtml(place.address)}</div>` : ""}
                        ${place.tel ? `<div class="place-tel">📞 ${escHtml(place.tel)}</div>` : ""}
                        ${place.reason ? `<div class="place-reason">✨ ${escHtml(place.reason)}</div>` : ""}
                    </div>
                </div>
            `;
        }).join("");
    }

    showStep("step-results");
}

// ─── Restart ─────────────────────────────────────────────────────────
function restart() {
    state.region = "";
    state.date = "";
    state.answers = [];
    state.weather = null;
    state.questionIndex = 0;
    document.getElementById("region-select").value = "";
    document.getElementById("date-input").value = "";
    showStep("step-1");
}

// ─── Toast ───────────────────────────────────────────────────────────
let toastTimer;
function showToast(msg) {
    const el = document.getElementById("toast");
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove("show"), 3500);
}

// ─── Detail Modal ────────────────────────────────────────────────────
const CONTENT_TYPE_PLACEHOLDERS = {
    "관광지": "🗺️", "문화시설": "🏛️", "축제/행사": "🎉",
    "레포츠": "🏄", "숙박": "🏨", "쇼핑": "🛍️", "음식점": "🍜"
};

async function openDetail(contentid, contenttypeid, contentType) {
    if (!contentid) return;

    const modal = document.getElementById("detail-modal");
    const body = document.getElementById("modal-body");

    body.innerHTML = `
        <div class="loading-container" style="min-height:300px">
            <div class="loading-spinner"></div>
            <p>불러오는 중...</p>
        </div>`;
    modal.classList.add("open");
    document.body.style.overflow = "hidden";

    try {
        const resp = await fetch(`/api/detail?contentid=${encodeURIComponent(contentid)}&contenttypeid=${contenttypeid}`);
        if (!resp.ok) throw new Error("상세정보를 가져오지 못했습니다.");
        const d = await resp.json();

        const icon = CONTENT_TYPE_PLACEHOLDERS[contentType] || "📍";
        const imgHtml = d.image
            ? `<img class="modal-image" src="${escHtml(d.image)}" alt="${escHtml(d.title)}"
                    onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
               <div class="modal-placeholder" style="display:none">${icon}</div>`
            : `<div class="modal-placeholder">${icon}</div>`;

        const mapUrl = (d.mapy && d.mapx)
            ? `https://map.naver.com/v5/search/${encodeURIComponent(d.title)}`
            : null;

        const homepageText = d.homepage
            ? d.homepage.replace(/<[^>]+>/g, "").trim()
            : "";

        body.innerHTML = `
            ${imgHtml}
            <div class="modal-content">
                <span class="modal-type">${escHtml(contentType)}</span>
                <h2 class="modal-title">${escHtml(d.title)}</h2>
                <div class="modal-meta">
                    ${d.address ? `<div class="modal-meta-item">📍 <span>${escHtml(d.address)}</span></div>` : ""}
                    ${d.tel ? `<div class="modal-meta-item">📞 <span>${escHtml(d.tel)}</span></div>` : ""}
                    ${homepageText ? `<div class="modal-meta-item">🌐 <a href="${escHtml(homepageText)}" target="_blank" rel="noopener">${escHtml(homepageText)}</a></div>` : ""}
                </div>
                ${d.overview ? `<div class="modal-overview">${escHtml(d.overview)}</div>` : ""}
                ${mapUrl ? `<a class="modal-map-btn" href="${mapUrl}" target="_blank" rel="noopener">🗺️ 네이버 지도에서 보기</a>` : ""}
            </div>`;
    } catch (e) {
        body.innerHTML = `<div class="modal-content" style="padding:40px;text-align:center;color:#64748B">${e.message}</div>`;
    }
}

function closeDetailModal() {
    const modal = document.getElementById("detail-modal");
    modal.classList.remove("open");
    document.body.style.overflow = "";
}

function closeModal(e) {
    if (e.target === document.getElementById("detail-modal")) {
        closeDetailModal();
    }
}

document.addEventListener("keydown", e => {
    if (e.key === "Escape") closeDetailModal();
});

// ─── Utils ───────────────────────────────────────────────────────────
function escHtml(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}
