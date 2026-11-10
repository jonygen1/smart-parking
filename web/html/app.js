// ===== Smart Parking dashboard =====
// Polls the API every 2 seconds with fetch() and rebuilds the page with DOM methods.
// "/api" is relative: Nginx (same origin) forwards it to the api container.

const API = "/api";
const POLL_MS = 2000;

const $ = (id) => document.getElementById(id);
let knownPlates = null; // plates seen in the previous poll (null = first load)

// ---------- helpers ----------
function formatDuration(totalSeconds) {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  return [h, m, s].map((n) => String(n).padStart(2, "0")).join(":");
}

function formatTime(epochSeconds) {
  return new Date(epochSeconds * 1000).toLocaleTimeString("he-IL");
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text; // textContent, never innerHTML -> no XSS
  return node;
}

function toast(text, type = "") {
  const t = el("div", `toast ${type}`, text);
  $("toasts").appendChild(t);
  setTimeout(() => t.remove(), 4500);
}

// ---------- rendering ----------
function plateElement(plate) {
  const p = el("div", "plate");
  p.appendChild(el("span", "il", "IL"));
  p.appendChild(el("span", "num", plate));
  return p;
}

function row(label, value, valueClass) {
  const r = el("div", "row");
  r.appendChild(el("span", "", label));
  r.appendChild(el("span", valueClass || "", value));
  return r;
}

function renderCars(cars) {
  const container = $("cars");
  container.replaceChildren(); // clear old cards
  $("emptyState").hidden = cars.length > 0;

  const current = new Set(cars.map((c) => c.plate));

  for (const car of cars) {
    const isNew = knownPlates !== null && !knownPlates.has(car.plate);
    const card = el("div", isNew ? "car new" : "car");

    card.appendChild(plateElement(car.plate));
    card.appendChild(row("נכנס בשעה", formatTime(car.entered_at)));
    card.appendChild(row("זמן בחניון", formatDuration(car.duration_seconds)));
    card.appendChild(row("שער", car.gate));
    card.appendChild(row("לתשלום כרגע", `${car.price} ₪`, "price"));
    card.appendChild(el("div", "msg", car.message));

    const btn = el("button", "release", "שחרור רכב 🚪");
    btn.addEventListener("click", () => releaseCar(car.plate));
    card.appendChild(btn);

    container.appendChild(card);

    // A car the camera added since the last poll -> show its funny message
    if (isNew) toast(`🚗 ${car.plate}: ${car.message}`);
  }

  knownPlates = current;
}

function renderStats(s) {
  // ⁦ ... ⁩ = "left-to-right isolate". Without it, the RTL page shows "1 / 15" as "15 / 1".
  $("statInside").textContent = `⁦${s.inside} / ${s.capacity}⁩`;
  $("statFree").textContent = s.free;
  $("statTotal").textContent = s.total_entries;
  $("statRevenue").textContent = `${s.revenue} ₪`;

  const pct = s.capacity ? Math.round((s.inside / s.capacity) * 100) : 0;
  const fill = $("capacityFill");
  fill.style.width = `${pct}%`;
  fill.style.background = pct >= 100 ? "var(--danger)" : pct >= 80 ? "#f79009" : "var(--ok)";
  $("capacityText").textContent = `${pct}% תפוסה`;
  $("fullAlert").hidden = !s.is_full;

  const unit = s.pricing.unit_seconds === 3600 ? "שעה" : `${s.pricing.unit_seconds} שניות (מצב דמו)`;
  $("pricing").textContent =
    `תעריף: ${s.pricing.first_unit} ₪ ליחידה הראשונה, ${s.pricing.next_unit} ₪ לכל יחידה נוספת. יחידה = ${unit}.`;

  const tbody = $("history");
  tbody.replaceChildren();
  for (const h of s.history) {
    const tr = el("tr");
    tr.appendChild(el("td", "", h.plate));
    tr.appendChild(el("td", "", formatDuration(h.duration_seconds)));
    tr.appendChild(el("td", "", `${h.price} ₪`));
    tr.appendChild(el("td", "", formatTime(h.left_at)));
    tbody.appendChild(tr);
  }
}

// ---------- API calls ----------
async function refresh() {
  try {
    const [carsRes, statsRes] = await Promise.all([fetch(`${API}/cars`), fetch(`${API}/stats`)]);
    if (!carsRes.ok || !statsRes.ok) throw new Error("API error");
    renderCars(await carsRes.json());
    renderStats(await statsRes.json());
    $("connection").className = "dot ok";
  } catch (err) {
    $("connection").className = "dot err";
    console.error("refresh failed:", err);
  }
}

async function enterCar(plate) {
  const res = await fetch(`${API}/cars`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plate, gate: "ידני" }),
  });
  const data = await res.json();
  if (!res.ok) {
    toast(`❌ ${data.error}`, "error");
    return;
  }
  // Mark it as known so the poll doesn't toast it a second time
  if (knownPlates) knownPlates.add(data.plate);
  toast(`🚗 ${data.plate}: ${data.message}`, "success");
  refresh();
}

async function releaseCar(plate) {
  if (!confirm(`לשחרר את ${plate}?`)) return;
  const res = await fetch(`${API}/cars/${encodeURIComponent(plate)}`, { method: "DELETE" });
  const data = await res.json();
  if (!res.ok) {
    toast(`❌ ${data.error}`, "error");
    return;
  }
  toast(`👋 ${plate} יצא אחרי ${formatDuration(data.duration_seconds)}. לתשלום: ${data.price} ₪`, "success");
  refresh();
}

// ---------- dark mode ----------
function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  $("themeToggle").textContent = theme === "dark" ? "☀️" : "🌙";
}

function initTheme() {
  let saved = null;
  try { saved = localStorage.getItem("theme"); } catch (e) { /* storage blocked */ }
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  applyTheme(saved || (prefersDark ? "dark" : "light"));

  $("themeToggle").addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    applyTheme(next);
    try { localStorage.setItem("theme", next); } catch (e) { /* ignore */ }
  });
}

// ---------- start ----------
$("enterForm").addEventListener("submit", (e) => {
  e.preventDefault(); // don't reload the page
  const input = $("plateInput");
  enterCar(input.value.trim());
  input.value = "";
});

setInterval(() => { $("clock").textContent = new Date().toLocaleTimeString("he-IL"); }, 1000);

console.log("%c🅿️ שלום מפתח/ת! אם הגעת לפה - לוחית פלינדרום חונה בחינם 😉", "font-size:16px;color:#2f6fed");

initTheme();
refresh();
setInterval(refresh, POLL_MS);
