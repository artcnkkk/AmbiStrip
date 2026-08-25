/**
 * @typedef {Object} DeviceState
 * @property {string} address
 * @property {string} name
 */

/**
 * @typedef {Object} UiState
 * @property {DeviceState | null} device
 * @property {boolean} connected
 * @property {boolean} [auto_connect]
 */

/**
 * @typedef {Object} UiMessage
 * @property {string} text
 * @property {string} kind
 * @property {UiState} state
 */

/**
 * @typedef {Object} ScanHit
 * @property {string} name
 * @property {string} address
 * @property {boolean} lednetwf
 * @property {number | null} rssi
 */

/**
 * @typedef {Object} ScanEvent
 * @property {string} text
 * @property {string} kind
 * @property {UiState} state
 * @property {ScanHit[]} hits
 * @property {DeviceState | null} [device]
 */

/**
 * @typedef {Object} LedBridge
 * @property {function(ScanEvent): void} onScan
 * @property {function(UiMessage): void} onSelected
 * @property {function(UiMessage): void} onMsg
 * @property {function(UiMessage): void} onGatt
 * @property {function(UiMessage): void} onForgot
 */

const PRESETS = [
  ["Красный", 255, 0, 0],
  ["Зелёный", 0, 255, 0],
  ["Синий", 0, 0, 255],
  ["Белый", 255, 255, 255],
];

const hsv = { h: 0.02, s: 0.9, v: 1 };
let dragging = null;
let syncing = false;

function api() {
  return window.pywebview.api;
}

function hsvToRgb(h, s, v) {
  const i = Math.floor(h * 6);
  const f = h * 6 - i;
  const p = v * (1 - s);
  const q = v * (1 - f * s);
  const t = v * (1 - (1 - f) * s);
  const table = [
    [v, t, p],
    [q, v, p],
    [p, v, t],
    [p, q, v],
    [t, p, v],
    [v, p, q],
  ];
  const [r, g, b] = table[i % 6];
  return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)];
}

function rgbToHsv(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const d = max - min;
  let h = 0;
  if (d !== 0) {
    if (max === r) h = ((g - b) / d) % 6;
    else if (max === g) h = (b - r) / d + 2;
    else h = (r - g) / d + 4;
    h /= 6;
    if (h < 0) h += 1;
  }
  const s = max === 0 ? 0 : d / max;
  return [h, s, max];
}

function rgbHex(r, g, b) {
  return "#" + [r, g, b].map((n) => n.toString(16).padStart(2, "0")).join("");
}

function luminance(r, g, b) {
  return (r * 299 + g * 587 + b * 114) / 1000;
}

function setStatus(el, text, kind) {
  el.textContent = text || "";
  el.className = "status" + (kind ? " " + kind : "");
}

function showDevice() {
  document.body.classList.add("screen-device");
  document.body.classList.remove("screen-color");
  document.getElementById("view-device").hidden = false;
  document.getElementById("view-color").hidden = true;
  document.getElementById("top-actions").hidden = true;
}

function showColor() {
  document.body.classList.add("screen-color");
  document.body.classList.remove("screen-device");
  document.getElementById("view-device").hidden = true;
  document.getElementById("view-color").hidden = false;
  document.getElementById("top-actions").hidden = false;
  sizePicker();
  paintColor();
  loadMonitors();
}

function paintColor() {
  const [r, g, b] = hsvToRgb(hsv.h, hsv.s, hsv.v);
  const hex = rgbHex(r, g, b);
  const strip = document.getElementById("strip");
  strip.style.background = hex;
  strip.style.setProperty("--strip", hex);
  strip.querySelector("span").style.color = luminance(r, g, b) > 160 ? "#111" : "#f4f1ec";
  document.getElementById("rgb-readout").textContent = `${r}  ${g}  ${b}   ${hex.toUpperCase()}`;
}

function sizePicker() {
  const sv = document.getElementById("sv");
  const hue = document.getElementById("hue");
  const box = document.querySelector(".picker");
  const cssW = Math.max(160, Math.floor(box.clientWidth || 280));
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  sv.width = Math.round(cssW * dpr);
  sv.height = Math.round(cssW * dpr);
  hue.width = Math.round(cssW * dpr);
  hue.height = Math.round(18 * dpr);
  drawPicker();
}

function drawPicker() {
  const sv = document.getElementById("sv");
  const hue = document.getElementById("hue");
  const svx = sv.getContext("2d");
  const hx = hue.getContext("2d");
  const w = sv.width;
  const h = sv.height;
  const img = svx.createImageData(w, h);
  const data = img.data;
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const [r, g, b] = hsvToRgb(hsv.h, x / Math.max(w - 1, 1), 1 - y / Math.max(h - 1, 1));
      const i = (y * w + x) * 4;
      data[i] = r;
      data[i + 1] = g;
      data[i + 2] = b;
      data[i + 3] = 255;
    }
  }
  svx.putImageData(img, 0, 0);
  svx.beginPath();
  svx.arc(hsv.s * (w - 1), (1 - hsv.v) * (h - 1), 7, 0, Math.PI * 2);
  svx.strokeStyle = "#111";
  svx.lineWidth = 3;
  svx.stroke();
  svx.strokeStyle = "#fff";
  svx.lineWidth = 1.5;
  svx.stroke();

  for (let x = 0; x < hue.width; x++) {
    const [r, g, b] = hsvToRgb(x / Math.max(hue.width - 1, 1), 1, 1);
    hx.fillStyle = rgbHex(r, g, b);
    hx.fillRect(x, 0, 1, hue.height);
  }
  hx.strokeStyle = "#fff";
  hx.lineWidth = 2;
  const hxpos = hsv.h * (hue.width - 1);
  hx.strokeRect(hxpos - 3, 1, 6, hue.height - 2);
}

function applyRgb(r, g, b, send) {
  if (syncing && send) return;
  const [h, s, v] = rgbToHsv(r, g, b);
  hsv.h = h; hsv.s = s; hsv.v = v;
  paintColor();
  drawPicker();
  if (send) sendColor();
}

function sendColor() {
  if (syncing) return;
  const [r, g, b] = hsvToRgb(hsv.h, hsv.s, hsv.v);
  api().set_color(r, g, b);
}

let hueFrame = 0;

function bindPicker(canvas, kind) {
  const pos = (ev) => {
    const rect = canvas.getBoundingClientRect();
    const x = Math.min(1, Math.max(0, (ev.clientX - rect.left) / rect.width));
    const y = Math.min(1, Math.max(0, (ev.clientY - rect.top) / rect.height));
    if (kind === "sv") { hsv.s = x; hsv.v = 1 - y; }
    else hsv.h = x;
    paintColor();
    if (kind === "hue" && !hueFrame) {
      hueFrame = requestAnimationFrame(() => {
        hueFrame = 0;
        drawPicker();
      });
    }
    sendColor();
  };
  canvas.addEventListener("pointerdown", (ev) => {
    if (syncing) return;
    canvas.setPointerCapture(ev.pointerId);
    dragging = kind;
    pos(ev);
  });
  canvas.addEventListener("pointermove", (ev) => { if (dragging === kind) pos(ev); });
  canvas.addEventListener("pointerup", () => {
    dragging = null;
    drawPicker();
  });
}

/**
 * @param {ScanHit[]} hits
 * @param {DeviceState | null} [selected]
 */
function renderDevices(hits, selected) {
  const root = document.getElementById("device-list");
  root.innerHTML = "";
  if (!hits.length) return;
  hits.forEach((hit) => {
    const card = document.createElement("div");
    card.className = "card" + (hit.lednetwf ? " likely" : "");
    card.setAttribute("role", "button");
    card.tabIndex = 0;
    card.innerHTML =
      (hit.lednetwf ? '<span class="badge">похоже на ленту</span>' : "") +
      `<span class="name">${escapeHtml(hit.name || "без имени")}</span>` +
      `<span class="addr">${escapeHtml(hit.address)}</span>`;
    const pick = () => chooseDevice(hit.address);
    card.addEventListener("click", pick);
    card.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        pick();
      }
    });
    if (selected && selected.address === hit.address) card.style.outline = "1px solid #8aa57a";
    root.appendChild(card);
  });
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function chooseDevice(address) {
  setStatus(document.getElementById("device-status"), "Подключаемся…", "busy");
  api().select_device(address);
}

function paintSyncPreview(r, g, b, running) {
  const preview = document.getElementById("sync-preview");
  const readout = document.getElementById("sync-rgb");
  if (!running && (r === 0 && g === 0 && b === 0) && !readout.textContent) {
    preview.style.background = "";
    preview.querySelector("span").style.color = "";
    readout.textContent = "";
    return;
  }
  const hex = rgbHex(r, g, b);
  preview.style.background = hex;
  preview.querySelector("span").style.color = luminance(r, g, b) > 160 ? "#111" : "#f4f1ec";
  readout.textContent = `${r}  ${g}  ${b}   ${hex.toUpperCase()}`;
}

function setSyncing(on, text, kind) {
  syncing = on;
  const view = document.getElementById("view-color");
  view.classList.toggle("is-sync", on);
  const btn = document.getElementById("btn-sync");
  btn.textContent = on ? "Остановить" : "Экран → лента";
  document.getElementById("monitor-select").disabled = on;
  const presets = document.getElementById("presets");
  presets.querySelectorAll("button").forEach((el) => { el.disabled = on; });
  if (text) setStatus(document.getElementById("sync-status"), text, kind);
}

async function loadMonitors() {
  const sel = document.getElementById("monitor-select");
  const data = await api().list_monitors();
  sel.innerHTML = "";
  (data.monitors || []).forEach((item) => {
    const opt = document.createElement("option");
    opt.value = item.id;
    opt.textContent = item.label;
    sel.appendChild(opt);
  });
  if (data.selected_id) sel.value = data.selected_id;
  if (data.note) setStatus(document.getElementById("sync-status"), data.note, "info");
}

function goColor() {
  showColor();
  api().get_state().then((state) => refreshHeader(state));
}

/** @param {UiState | null | undefined} state */
function refreshHeader(state) {
  if (!state) return;
  const dot = document.getElementById("link-dot");
  const link = document.getElementById("link-text");
  const label = document.getElementById("device-label");
  const toggle = document.getElementById("btn-toggle");
  if (!state.device) {
    label.textContent = "лента не выбрана";
    link.textContent = "Нет устройства";
    dot.className = "dot off";
    toggle.textContent = "Подключить";
    return;
  }
  label.textContent = `${state.device.name || "без имени"} · ${state.device.address}`;
  if (state.connected) {
    link.textContent = "Подключено";
    dot.className = "dot on";
    toggle.textContent = "Отключить";
  } else {
    link.textContent = "Не подключено";
    dot.className = "dot";
    toggle.textContent = "Подключить";
  }
}

function closeSheet() {
  document.getElementById("overlay").hidden = true;
}

function openSheet(html) {
  document.getElementById("sheet").innerHTML = html;
  document.getElementById("overlay").hidden = false;
  const close = document.getElementById("sheet-close");
  if (close) close.addEventListener("click", closeSheet);
}

/** @type {LedBridge} */
window.__led = {
  /** @param {ScanEvent} result */
  onScan(result) {
    const btn = document.getElementById("btn-scan");
    btn.disabled = false;
    btn.textContent = "Найти ленту";
    renderDevices(result.hits || [], result.device);
    setStatus(document.getElementById("device-status"), result.text, result.kind);
  },
  /** @param {UiMessage} msg */
  onSelected(msg) {
    goColor();
    setStatus(document.getElementById("color-status"), msg.text, msg.kind);
    refreshHeader(msg.state);
  },
  /** @param {UiMessage} msg */
  onMsg(msg) {
    setStatus(document.getElementById("color-status"), msg.text, msg.kind);
    refreshHeader(msg.state);
  },
  /** @param {UiMessage} msg */
  onGatt(msg) {
    if (msg.kind === "err") {
      setStatus(document.getElementById("color-status"), msg.text, "err");
      return;
    }
    openSheet(`<h3>GATT</h3><pre>${escapeHtml(msg.text)}</pre><div class="row"><button class="ghost" id="sheet-close">Закрыть</button></div>`);
  },
  /** @param {UiMessage} msg */
  onForgot(msg) {
    closeSheet();
    setSyncing(false, "", "");
    showDevice();
    setStatus(document.getElementById("device-status"), msg.text, msg.kind);
    refreshHeader(msg.state);
  },
  /** @param {{text: string, kind: string, state: UiState, running: boolean, r: number, g: number, b: number}} ev */
  onSync(ev) {
    setSyncing(ev.running, ev.text, ev.kind);
    paintSyncPreview(ev.r, ev.g, ev.b, ev.running);
    refreshHeader(ev.state);
    if (ev.kind === "err") {
      setStatus(document.getElementById("color-status"), ev.text, "err");
    }
  },
};

window.addEventListener("pywebviewready", async () => {
  PRESETS.forEach(([name, r, g, b]) => {
    const el = document.createElement("button");
    el.type = "button";
    el.className = "preset";
    el.innerHTML = `<div class="swatch" style="background:${rgbHex(r, g, b)}"></div>${name}`;
    el.addEventListener("click", () => applyRgb(r, g, b, true));
    document.getElementById("presets").appendChild(el);
  });
  bindPicker(document.getElementById("sv"), "sv");
  bindPicker(document.getElementById("hue"), "hue");

  document.getElementById("btn-scan").addEventListener("click", () => {
    const btn = document.getElementById("btn-scan");
    btn.disabled = true;
    btn.textContent = "Ищем…";
    setStatus(document.getElementById("device-status"), "Ищем устройства рядом…", "busy");
    api().scan();
  });

  document.getElementById("btn-back").addEventListener("click", () => {
    setSyncing(false, "", "");
    api().stop_sync();
    showDevice();
  });
  document.getElementById("btn-toggle").addEventListener("click", () => {
    setStatus(document.getElementById("color-status"), "Секунду…", "busy");
    api().toggle_connection();
  });
  document.getElementById("btn-off").addEventListener("click", () => api().power_off());
  document.getElementById("btn-on").addEventListener("click", () => api().power_on());
  document.getElementById("btn-sync").addEventListener("click", () => {
    if (syncing) api().stop_sync();
    else {
      setStatus(document.getElementById("sync-status"), "Запускаем захват…", "busy");
      api().start_sync();
    }
  });
  document.getElementById("monitor-select").addEventListener("change", (ev) => {
    api().select_monitor(ev.target.value);
  });
  document.getElementById("overlay").addEventListener("click", (ev) => {
    if (ev.target.id === "overlay") closeSheet();
  });
  document.getElementById("btn-gatt").addEventListener("click", () => {
    setStatus(document.getElementById("color-status"), "Читаем GATT…", "busy");
    api().gatt();
  });
  document.getElementById("btn-settings").addEventListener("click", async () => {
    const s = await api().get_settings();
    openSheet(`
      <h3>Настройки</h3>
      <label>Поиск ленты, секунды</label>
      <input id="set-scan" type="text" value="${s.scan_timeout}" />
      <label>Подключение, секунды</label>
      <input id="set-conn" type="text" value="${s.connect_timeout}" />
      <label class="check"><input id="set-verbose" type="checkbox" ${s.verbose ? "checked" : ""} /> Подробный GATT после команд</label>
      <div class="row">
        <button class="primary" id="set-save">Сохранить</button>
        <button class="ghost" id="set-forget">Забыть ленту</button>
        <button class="text-btn" id="sheet-close">Закрыть</button>
      </div>
    `);
    document.getElementById("set-save").addEventListener("click", async () => {
      const msg = await api().save_settings(
        document.getElementById("set-scan").value,
        document.getElementById("set-conn").value,
        document.getElementById("set-verbose").checked
      );
      closeSheet();
      setStatus(document.getElementById("color-status"), msg.text, msg.kind);
    });
    document.getElementById("set-forget").addEventListener("click", () => {
      api().forget_device();
    });
  });

  const state = await api().get_state();
  refreshHeader(state);
  if (state.device) {
    showColor();
    if (state.auto_connect) api().connect();
  } else {
    showDevice();
  }
  paintColor();
  sizePicker();
});
