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
        text: "어떤 여행지를 찾으세요?",
        options: [
            { value: "mountain", icon: "🏔️", label: "산·숲·계곡",    desc: "트레킹, 계곡, 청정 자연" },
            { value: "sea",      icon: "🌊", label: "바다·해변",      desc: "해수욕, 일몰, 해안 드라이브" },
            { value: "city",     icon: "🏙️", label: "도심·거리·핫플", desc: "카페거리, 쇼핑, 야경" },
            { value: "heritage", icon: "🏯", label: "고궁·사찰·유적지", desc: "역사 탐방, 전통 문화" }
        ]
    },
    {
        text: "여행에서 무엇을 하고 싶나요?",
        options: [
            { value: "activity", icon: "🏄", label: "액티비티·스포츠", desc: "서핑, 래프팅, 클라이밍" },
            { value: "food",     icon: "🍽️", label: "미식·맛집 탐방",  desc: "로컬 맛집, 특산 음식" },
            { value: "culture",  icon: "🎨", label: "문화·예술 감상",   desc: "미술관, 전시, 공연" },
            { value: "healing",  icon: "😌", label: "휴양·힐링",        desc: "온천, 펜션, 느긋한 산책" }
        ]
    },
    {
        text: "어떤 날씨를 원하나요?",
        options: [
            { value: "rainy",  icon: "🌧️", label: "비 오는 날의 낭만",   desc: "촉촉한 감성, 빗소리, 실내 명소" },
            { value: "sunny",  icon: "☀️", label: "햇빛 쨍쨍 맑은 날",   desc: "파란 하늘, 야외 활동, 산책" },
            { value: "cloudy", icon: "☁️", label: "구름 많고 흐린 날",   desc: "선선한 공기, 부담 없는 나들이" },
            { value: "snowy",  icon: "❄️", label: "눈 내리는 겨울날",     desc: "설경, 포근한 실내, 겨울 감성" }
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
        if (dateInput.value && dateInput.value > getLocalDateString(6)) {
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
    const regionSel = document.getElementById("region-select");
    const regionError = document.getElementById("region-error");
    const dateInputEl = document.getElementById("date-input");
    const dateErrorEl = document.getElementById("date-error");

    // 에러 초기화
    regionError.style.display = "none";
    regionSel.style.borderColor = "";
    dateErrorEl.style.display = "none";
    dateInputEl.style.borderColor = "";

    let invalid = false;
    if (!region) {
        regionError.textContent = "⚠️ 여행지를 선택해주세요.";
        regionError.style.display = "block";
        regionSel.style.borderColor = "#EF4444";
        invalid = true;
    }
    if (!dateVal) {
        dateErrorEl.textContent = "⚠️ 여행 날짜를 선택해주세요.";
        dateErrorEl.style.display = "block";
        dateInputEl.style.borderColor = "#EF4444";
        invalid = true;
    }
    if (invalid) return;

    const maxDate = getLocalDateString(6);
    if (dateVal > maxDate) {
        dateErrorEl.textContent = "⚠️ 오늘부터 일주일 이내 날짜만 선택할 수 있어요.";
        dateErrorEl.style.display = "block";
        dateInputEl.style.borderColor = "#EF4444";
        dateInputEl.scrollIntoView({ behavior: "smooth", block: "center" });
        return;
    }
    document.getElementById("date-error").style.display = "none";
    document.getElementById("date-input").style.borderColor = "";

    state.region = region;
    state.date = dateVal.replace(/-/g, "");
    state.answers = [];
    state.questionIndex = 0;
    state.weather = null;

    fetchWeather(state.region);
    showQuestion(0);
}

async function fetchWeather(region) {
    try {
        const resp = await fetch(`/api/weather?region=${encodeURIComponent(region)}`);
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
    grid.className = "options-grid" + (q.options.length === 4 ? " four" : q.options.length === 3 ? " three" : "");
    grid.innerHTML = q.options.map(opt => `
        <div class="option-card" onclick="selectAnswer('${opt.value}')">
            <span class="option-icon">${opt.icon}</span>
            <div class="option-label">${opt.label}</div>
            <div class="option-desc">${opt.desc}</div>
        </div>
    `).join("");

    const backBtn = document.getElementById("back-btn");
    backBtn.style.display = "block";
    backBtn.textContent = index === 0 ? "🏠 홈 화면으로 돌아가기" : "← 이전 질문으로 돌아가기";

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
        renderResults(state.weather, data);

    } catch (e) {
        showToast(e.message);
        showStep("step-1");
    }
}

function renderResults(weather, data) {
    const places = data.places;
    const note = data.weather_note;

    document.getElementById("result-region").textContent = state.region;

    // Weather
    const weatherEl = document.getElementById("weather-card");
    if (weather && weather.days && weather.days.length) {
        const cur = weather.days[0] && weather.days[0].temp_current;
        const headerExtra = (cur != null) ? ` · 현재 ${cur}°` : "";
        weatherEl.innerHTML = `
            <div class="weather-header">${weather.region} 날씨${headerExtra}</div>
            <div class="weather-days">
                ${weather.days.map((day, i) => {
                    const isSelected = day.date && day.date === state.date;
                    return `
                    <div class="weather-day${isSelected ? " today" : ""}">
                        <div class="weather-day-label">${day.label}</div>
                        <div class="weather-day-icon">${day.icon}</div>
                        <div class="weather-day-name">${day.weather}</div>
                        <div class="weather-day-temp">
                            <span class="temp-max">${day.temp_max}°</span>
                            <span class="temp-divider">/</span>
                            <span class="temp-min">${day.temp_min}°</span>
                        </div>
                        <div class="weather-day-pop">☔ ${day.pop}%</div>
                    </div>`;
                }).join("")}
            </div>
        `;
    } else {
        weatherEl.innerHTML = `
            <div class="weather-unavailable">
                ⚠️ 날씨 정보를 불러올 수 없습니다
            </div>
        `;
    }

    // Places
    const placesEl = document.getElementById("places-grid");

    // 분위기 + 날씨 안내 배너
    let noteEl = document.getElementById("weather-note");
    if (note) {
        if (!noteEl) {
            noteEl = document.createElement("div");
            noteEl.id = "weather-note";
            noteEl.style.cssText = "margin:16px 0;padding:12px 16px;background:#EEF2FF;border-radius:12px;color:#3730A3;font-size:14px;line-height:1.5;";
            placesEl.parentNode.insertBefore(noteEl, placesEl);
        }
        noteEl.textContent = "✨ " + note;
        noteEl.style.display = "";
    } else if (noteEl) {
        noteEl.style.display = "none";
    }

    const footer = document.getElementById("results-footer");
    if (footer) footer.style.display = data.mood_available === false ? "none" : "";

    if (data.mood_available === false) {
        placesEl.innerHTML = `
            <div class="no-results">
                다른 여행지나 다른 날씨를 골라보세요. 😢<br>
                <button onclick="restart()"
                    style="margin-top:16px;padding:10px 18px;background:#4F46E5;color:#fff;border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;">
                    🏠 처음으로 돌아가기</button>
            </div>
        `;
    } else if (!places || places.length === 0) {
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
                        ${place.eventstartdate ? `<div class="place-event">📅 ${fmtEventDate(place.eventstartdate)} ~ ${fmtEventDate(place.eventenddate)}</div>` : ""}
                        ${place.tel ? `<div class="place-tel">📞 ${escHtml(place.tel)}</div>` : ""}
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
function fmtEventDate(s) {
    s = String(s || "");
    if (s.length !== 8) return s;
    return `${s.slice(0, 4)}.${s.slice(4, 6)}.${s.slice(6, 8)}`;
}

function escHtml(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}
