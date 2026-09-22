/* УрФУ Кликер — строй кампус тапами */
const LS_KEY = "urfu_clicker_v1";
const $ = (id) => document.getElementById(id);

const SHOP_ITEMS = [
  { id: "click", icon: "👆", name: "Усилитель клика", desc: "+1 к клику", base: 25, mul: 1.45 },
  { id: "auto", icon: "👷", name: "Стройотряд", desc: "+1 в секунду", base: 100, mul: 1.6 },
  { id: "mult", icon: "🚀", name: "Грант УрФУ", desc: "x1.5 ко всему", base: 750, mul: 2.2, oneShot: false },
];

let state = load();

function load() {
  try {
    const s = JSON.parse(localStorage.getItem(LS_KEY) || "null");
    if (s && typeof s.coins === "number") return {
      coins: s.coins || 0,
      totalClicks: s.totalClicks || 0,
      clickPower: s.clickPower || 1,
      autoPower: s.autoPower || 0,
      mult: s.mult || 1,
      prestige: s.prestige || 0,
      levels: s.levels || { click: 0, auto: 0, mult: 0 },
      built: s.built || 0,
    };
  } catch {}
  return { coins: 0, totalClicks: 0, clickPower: 1, autoPower: 0, mult: 1, prestige: 0, levels: { click: 0, auto: 0, mult: 0 }, built: 0 };
}

function save() { localStorage.setItem(LS_KEY, JSON.stringify(state)); }

function price(item) {
  const lvl = state.levels[item.id] || 0;
  return Math.floor(item.base * Math.pow(item.mul, lvl));
}

function format(n) {
  if (n >= 1e9) return (n/1e9).toFixed(1) + "B";
  if (n >= 1e6) return (n/1e6).toFixed(1) + "M";
  if (n >= 1e3) return (n/1e3).toFixed(n >= 10000 ? 0 : 1) + "K";
  return String(Math.floor(n));
}

function levelInfo() {
  const thresholds = [0, 100, 500, 1500, 4000, 10000, 25000, 60000, 120000, 300000];
  let lvl = 1;
  for (let i = thresholds.length - 1; i >= 0; i--) if (state.coins + state.built * 10000 >= thresholds[i]) { lvl = i + 1; break; }
  const next = thresholds[lvl] || thresholds[thresholds.length - 1] * 2;
  const prev = thresholds[lvl - 1] || 0;
  const pct = Math.min(100, Math.max(4, ((state.coins + state.built * 10000 - prev) / (next - prev)) * 100));
  return { lvl, next, pct, toNext: next - (state.coins + state.built * 10000) };
}

function render() {
  $("score").textContent = format(state.coins);
  $("statClick").innerHTML = `👆 <b>${format(state.clickPower * state.mult)}</b> за клик`;
  $("statAuto").innerHTML = `⚡ <b>${format(state.autoPower * state.mult)}</b>/сек`;
  $("statTotal").innerHTML = `🎯 <b>${format(state.totalClicks)}</b> кликов`;
  const lv = levelInfo();
  $("levelFill").style.width = lv.pct + "%";
  $("levelText").textContent = `Уровень ${lv.lvl} · до следующего ${format(lv.toNext)}`;

  const shop = $("shop");
  shop.innerHTML = "";
  SHOP_ITEMS.forEach(item => {
    const p = price(item);
    const lvl = state.levels[item.id] || 0;
    const can = state.coins >= p;
    const row = document.createElement("div");
    row.className = "shop-item" + (can ? "" : " disabled");
    row.innerHTML = `
      <div class="shop-icon">${item.icon}</div>
      <div class="shop-main">
        <div class="shop-name">${item.name} <span class="shop-lvl">ур. ${lvl}</span></div>
        <div class="shop-desc">${item.desc} · цена ${format(p)}</div>
      </div>
      <button class="shop-buy" ${can ? "" : "disabled"}>${can ? "Купить" : format(p)}</button>
    `;
    row.querySelector("button").onclick = () => buy(item);
    shop.appendChild(row);
  });

  const prestigeCost = 10000;
  const canPrestige = state.coins >= prestigeCost;
  $("prestigeBtn").disabled = !canPrestige;
  $("prestigeBtn").textContent = canPrestige ? `Построить корпус! (+x2 навсегда)` : `Построить корпус (${format(state.coins)} / ${format(prestigeCost)})`;
  $("prestigeDesc").textContent = state.built ? `Построено корпусов: ${state.built} · текущий множитель x${state.mult.toFixed(1)}` : "Сбросит прогресс, но даст постоянный x2 множитель";

  // эмодзи меняется по уровню
  const emojis = ["🏛️","🏗️","🏢","🎓","🚀","🏆","🌟","💎"];
  $("clickEmoji").textContent = emojis[Math.min(emojis.length - 1, lv.lvl - 1)];
  save();
}

function buy(item) {
  const p = price(item);
  if (state.coins < p) return;
  state.coins -= p;
  state.levels[item.id] = (state.levels[item.id] || 0) + 1;
  if (item.id === "click") state.clickPower += 1;
  if (item.id === "auto") state.autoPower += 1;
  if (item.id === "mult") state.mult = +(state.mult * 1.5).toFixed(2);
  spawnFloat(`-${format(p)}`, "#94a3b8");
  render();
}

function doClick(e) {
  const gain = state.clickPower * state.mult;
  state.coins += gain;
  state.totalClicks += 1;
  const btn = $("clickBtn");
  btn.classList.remove("pop"); void btn.offsetWidth; btn.classList.add("pop");
  // координата для浮動 текста
  let x = 50, y = 30;
  if (e && e.touches) { /* touch */ }
  else if (e && e.clientX) {
    const r = btn.getBoundingClientRect();
    x = ((e.clientX - r.left) / r.width) * 100;
    y = ((e.clientY - r.top) / r.height) * 100;
  }
  spawnFloat(`+${format(gain)}`, "#1e6fff", x, y);
  render();
}

function spawnFloat(text, color, x = 50 + (Math.random()*30-15), y = 40 + (Math.random()*20-10)) {
  const el = document.createElement("div");
  el.className = "float";
  el.textContent = text;
  el.style.left = x + "%";
  el.style.top = y + "%";
  el.style.color = color;
  $("floatLayer").appendChild(el);
  setTimeout(() => el.remove(), 700);
}

$("clickBtn").addEventListener("click", doClick);
$("clickBtn").addEventListener("touchstart", (e) => { e.preventDefault(); doClick(e.touches[0]); }, { passive: false });

// автоклик
setInterval(() => {
  if (state.autoPower > 0) {
    state.coins += (state.autoPower * state.mult) / 10; // 10 тиков в сек
    // render throttled
  }
}, 100);
setInterval(() => { if (state.autoPower > 0) render(); }, 500);

$("prestigeBtn").onclick = () => {
  if (state.coins < 10000) return;
  state.coins = 0;
  state.clickPower = 1;
  state.autoPower = 0;
  state.levels = { click: 0, auto: 0, mult: state.levels.mult || 0 };
  state.built += 1;
  state.mult = +(state.mult * 2).toFixed(2);
  spawnFloat("🏗️ КОРПУС!", "#16a34a", 50, 20);
  render();
};

$("resetBtn").onclick = () => {
  if (!confirm("Сбросить весь прогресс кликера?")) return;
  localStorage.removeItem(LS_KEY);
  state = load();
  render();
};

// удержание для автоклика мышью
let holdTimer = null;
$("clickBtn").addEventListener("mousedown", () => {
  holdTimer = setInterval(() => doClick(), 90);
});
window.addEventListener("mouseup", () => clearInterval(holdTimer));

render();
