/* Админка квеста: статистика уверенности (этапы 3/6/10) + общий срез */
const $ = (id) => document.getElementById(id);
const BASE = window.API_BASE || "";
const MILE_TITLES = { 3: "После 3 локаций", 6: "После 6 локаций", 10: "После 10 локаций" };

async function load() {
  $("admErr").textContent = "";
  try {
    const [ov, cf] = await Promise.all([
      fetch(BASE + "/api/admin/overview").then((r) => {
        if (!r.ok) throw new Error("overview: " + r.status);
        return r.json();
      }),
      fetch(BASE + "/api/admin/confidence").then((r) => {
        if (!r.ok) throw new Error("confidence: " + r.status);
        return r.json();
      }),
    ]);
    renderOverview(ov);
    renderConfidence(cf);
    $("updTime").textContent = "Обновлено: " + new Date().toLocaleTimeString();
  } catch (e) {
    $("admErr").textContent = "Не удалось загрузить: " + e.message;
  }
}

function renderOverview(ov) {
  $("stUsers").textContent = ov.users;
  $("stVisits").textContent = ov.visits;
  const sum = ov.usersTable.reduce((a, u) => a + u.completed, 0);
  $("stAvg").textContent = ov.users
    ? (sum / ov.users).toFixed(1) + " из " + ov.total
    : "—";

  const box = $("locBars");
  box.innerHTML = "";
  const max = Math.max(1, ...ov.byLocation.map((l) => l.passed));
  for (let id = 1; id <= ov.total; id++) {
    const row = ov.byLocation.find((l) => l.location_id === id);
    const n = row ? row.passed : 0;
    const div = document.createElement("div");
    div.className = "bar-row";
    div.innerHTML =
      `<span>Локация ${id}</span>` +
      `<div class="bar"><div style="width:${(n / max) * 100}%"></div></div>` +
      `<b>${n}</b>`;
    box.appendChild(div);
  }

  const tb = $("usersBody");
  tb.innerHTML = "";
  const dash = "—";
  ov.usersTable.forEach((u) => {
    const tr = document.createElement("tr");
    [u.full_name, u.completed + " из " + ov.total,
     u.c3 ?? dash, u.c6 ?? dash, u.c10 ?? dash].forEach((v) => {
      const td = document.createElement("td");
      td.textContent = v;
      tr.appendChild(td);
    });
    tb.appendChild(tr);
  });
  if (!ov.usersTable.length) {
    tb.innerHTML = `<tr><td colspan="5" class="muted">Пока нет участников</td></tr>`;
  }
}

function renderConfidence(cf) {
  const box = $("confBlocks");
  box.innerHTML = "";
  ["3", "6", "10"].forEach((m) => {
    const s = cf.milestones[m];
    const div = document.createElement("div");
    div.className = "mile";
    const head =
      `<h3>${MILE_TITLES[m]} — ` +
      (s.count
        ? `средний балл <b>${s.avg}</b> (ответов: ${s.count}, мин ${s.min}, макс ${s.max})`
        : "ответов пока нет") + `</h3>`;
    const peak = Math.max(1, ...Object.values(s.dist));
    let dist = `<div class="dist">`;
    for (let v = 1; v <= 10; v++) {
      const c = s.dist[String(v)];
      dist += `<div class="dcol"><div class="db" style="height:${Math.max(
        3, (c / peak) * 70
      )}px" title="${c}"></div>${v}<br><b>${c}</b></div>`;
    }
    dist += `</div>`;
    let tbl = "";
    if (s.answers.length) {
      tbl = `<table class="tbl"><thead><tr><th>Кто</th><th>Балл</th><th>Когда</th></tr></thead><tbody>` +
        s.answers
          .map(
            (a) =>
              `<tr><td>${escapeHtml(a.user)}</td><td><b>${a.score}</b></td><td class="muted">${a.at}</td></tr>`
          )
          .join("") +
        `</tbody></table>`;
    }
    div.innerHTML = head + dist + tbl;
    box.appendChild(div);
  });
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

$("btnRefresh").onclick = load;
load();
setInterval(load, 15000);
