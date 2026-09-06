/* Квест УрФУ: 4 экрана. Этап 2: ответ проверяет СЕРВЕР (correct клиент не знает) */
const TOTAL = 10;
const $ = (id) => document.getElementById(id);

function locationId() {
  // Два формата ссылок: /location/N (ТЗ этапа 4, QR-коды) и короткий /l/N
  const m = location.pathname.match(/^\/(?:l|location)\/(\d+)/);
  if (m) return Math.min(TOTAL, Math.max(1, parseInt(m[1], 10)));
  const q = new URLSearchParams(location.search).get("loc");
  const n = parseInt(q || "1", 10);
  return Number.isNaN(n) ? 1 : Math.min(TOTAL, Math.max(1, n));
}
const LOC = locationId();
let loc = null;
let user = JSON.parse(localStorage.getItem("campus_user") || "null"); // {user_id, name}
let already = false;
let myCount = 0;
let checking = false;

function show(id) {
  document.querySelectorAll(".screen").forEach((s) => s.classList.remove("active"));
  $(id).classList.add("active");
  window.scrollTo(0, 0);
}

async function api(path, opts = {}) {
  const r = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error || "Ошибка сети");
  return j;
}

async function init() {
  // Задача 2.2: локация без правильного ответа (проверяет только сервер)
  loc = await api(`/api/location/${LOC}`);
  $("locBadge").textContent = `Локация ${loc.id} из ${TOTAL}`;
  $("locTitle").textContent = `${loc.id}. ${loc.title}`;
  $("locInfo").textContent = loc.info;
  renderPhoto();
  $("quizQ").textContent = loc.question;

  if (user && user.name) {
    $("nameInput").value = user.name;
    $("returnHint").textContent = `Ранее входили как: ${user.name}. Нажмите «Продолжить», чтобы загрузить прогресс.`;
  }
  wireQuiz();
}

// Задача 3.3: фотография локации.
// Цепочка: locNN.jpg (реальное фото) -> locNN.svg (заглушка из
// backend/make_placeholders.py) -> эмодзи на градиенте.
function renderPhoto() {
  const box = $("locPhoto");
  box.style.background = `linear-gradient(135deg, ${loc.color}, #0f172a)`;
  box.textContent = loc.emoji; // мгновенный фон, пока грузится картинка
  const img = document.createElement("img");
  img.alt = loc.title;
  img.onload = () => {
    box.textContent = "";
    box.appendChild(img);
  };
  img.onerror = () => {
    if (img.src.endsWith(".jpg")) {
      // Пробуем SVG-заглушку: сначала с базовым URL, потом без
      const svgSrc = loc.photo.replace(/\.jpg$/, ".svg");
      if (img.src !== svgSrc) {
        img.src = svgSrc;
      }
    }
    // svg тоже нет — остаётся эмодзи
  };
  img.src = loc.photo;
}

// Задача 2.1: регистрация / вход по full_name
async function register() {
  const name = $("nameInput").value.trim();
  if (name.length < 2) {
    $("regErr").textContent = "Введите имя и фамилию";
    return;
  }
  $("regErr").textContent = "";
  try {
    const j = await api("/api/user", {
      method: "POST",
      body: JSON.stringify({ full_name: name }),
    });
    user = { user_id: j.id, name: j.full_name };
    localStorage.setItem("campus_user", JSON.stringify(user));
    myCount = j.completed_locations;
    await openLecture();
  } catch (e) {
    $("regErr").textContent = e.message;
  }
}

// Задача 2.3: проходил ли пользователь эту локацию
async function openLecture() {
  const st = await api(`/api/location/${loc.id}/status?user_id=${user.user_id}`);
  already = st.isPassed;
  $("alreadyNotice").classList.toggle("hidden", !already);
  // Повторный визит: прогресс уже засчитан, дальше идти некуда — кнопку прячем
  $("btnToQuiz").classList.toggle("hidden", already);
  show("screen2");
}

function wireQuiz() {
  const box = $("quizOpts");
  box.innerHTML = "";
  checking = false;
  $("btnToProgress").classList.add("hidden");
  loc.options.forEach((text, i) => {
    const b = document.createElement("button");
    b.className = "opt";
    b.textContent = text;
    b.onclick = () => answer(i, b);
    box.appendChild(b);
  });
}

// Задача 2.4: клик -> сервер решает, верный ли ответ, и засчитывает визит
async function answer(i, btn) {
  const btns = [...document.querySelectorAll("#quizOpts .opt")];
  if (checking || btns.some((b) => b.classList.contains("correct"))) return;
  checking = true;
  btns.forEach((b) => (b.disabled = true));
  try {
    const r = await api("/api/quiz/check", {
      method: "POST",
      body: JSON.stringify({
        user_id: user.user_id,
        location_id: loc.id,
        selected_option: i,
      }),
    });
    if (r.isCorrect) {
      btn.classList.add("correct");
      myCount = r.newCompletedCount;
      already = true;
      $("btnToProgress").classList.remove("hidden");
    } else {
      btn.classList.add("wrong");
      btns.forEach((b) => {
        if (!b.classList.contains("wrong")) b.disabled = false;
      });
    }
  } catch {
    btns.forEach((b) => {
      if (!b.classList.contains("wrong")) b.disabled = false;
    });
  } finally {
    checking = false;
  }
}

async function completeAndShowProgress() {
  if (!already) {
    // Визит засчитывается сервером в момент верного ответа (2.4).
    // Страховка: обновим счётчик идемпотентным /api/user.
    try {
      const u = await api("/api/user", {
        method: "POST",
        body: JSON.stringify({ full_name: user.name }),
      });
      myCount = u.completed_locations;
      already = true;
    } catch {
      /* покажем локальный счётчик */
    }
  }
  const count = myCount;
  const milestone = count >= TOTAL ? 10 : [3, 6].includes(count) ? count : null;
  renderProgress(count, milestone);
  show("screen4");
}

function renderProgress(count, milestone) {
  $("wellDone").textContent = `Молодец, ${user.name}!`;
  $("progressText").textContent =
    count >= TOTAL
      ? "Поздравляю! Ты изучил(а) все локации!"
      : `Ты изучил(а) ${count} локаций из ${TOTAL}. Не останавливайся на достигнутом!`;
  $("progressFill").style.width = `${(count / TOTAL) * 100}%`;
  buildConfidence(milestone);
}

function confKey(milestone) {
  return `campus_conf_${user.user_id}_${milestone}`;
}

// Задача 2.5: оценка уверенности 1..10 на этапах 3/6/10
function buildConfidence(milestone) {
  const block = $("confBlock");
  const grid = $("confGrid");
  const thanks = $("confThanks");
  grid.innerHTML = "";
  thanks.classList.add("hidden");
  if (!milestone) {
    block.classList.add("hidden");
    return;
  }
  block.classList.remove("hidden");
  if (localStorage.getItem(confKey(milestone))) {
    thanks.classList.remove("hidden");
    return;
  }
  for (let v = 1; v <= 10; v++) {
    const b = document.createElement("button");
    b.textContent = v;
    b.onclick = async () => {
      await api("/api/confidence", {
        method: "POST",
        body: JSON.stringify({
          user_id: user.user_id,
          location_number: milestone,
          score: v,
        }),
      });
      localStorage.setItem(confKey(milestone), String(v));
      grid.innerHTML = "";
      thanks.classList.remove("hidden");
    };
    grid.appendChild(b);
  }
}

$("btnToLecture").onclick = register;
$("nameInput").addEventListener("keydown", (e) => {
  if (e.key === "Enter") register();
});
$("btnToQuiz").onclick = () => {
  if (already) completeAndShowProgress();
  else {
    wireQuiz();
    show("screen3");
  }
};
$("btnToProgress").onclick = completeAndShowProgress;

init();
