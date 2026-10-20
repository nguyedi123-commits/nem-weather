// Weather screen (same way of working as NEM Trader): pages (tabs) of panels on a 24 × 36 grid.
// Normal mode: locked; minimise / ⓘ only. Edit mode (Edit button or Ctrl+E): drag by the title bar, resize from the
// edges, A− / A+ text size, ✕ remove, "+ Add panel", pages: + Page / Rename / Copy / Delete / Reset.
// Every change is saved straight away (settings/layouts/<page>.json). Built-in pages: web/layouts/<page>.json.
// Data: /api/<source> per panel kind (fetched once for all panels, again after a refresh); /api/status every 5 s.
import { PANELS, REGIONS, REGION_COLOURS, FIELDS, MAP_SOURCES, progressText, esc } from "./panels.js";

const FONT_MIN = 0.5, FONT_MAX = 3, FONT_STEP = 0.1;
const S = {
  layout: null, page: null, grid: null, panels: new Map(), editing: false, loading: false,
  data: {}, status: null, version: null, builtIn: [], runs: {},
};
window.__weather = S;   // for testing

// ---------- one panel box ----------
function button(label, title, onclick, cls = "") {
  const b = document.createElement("button");
  b.className = `ctl ${cls}`;
  b.textContent = label;
  b.title = title;
  b.onclick = (e) => { e.stopPropagation(); onclick(); };
  return b;
}

const PICKER = {
  region: { opts: REGIONS.map(([r, c]) => [r, `${r} · ${c}`]), def: "NSW", title: "Region" },
  field: { opts: Object.entries(FIELDS), def: "temp", title: "What to show" },
  src: { opts: Object.entries(MAP_SOURCES), def: "ifs", title: "Model" },
  model: { opts: [["ens", "Ensemble middle"], ["ifs", "IFS"], ["aifs", "AIFS (AI)"]], def: "ens", title: "Model" },
};

// run / vs pickers (W-017): runs on disk for the panel's feed; vs = an older run, "auto" or none
function fillRuns(panel) {
  const kind = PANELS[panel.item.kind];
  if (!kind?.runFeed || !panel.runSel) return;
  const o = panel.opts, feed = kind.runFeed(o);
  let list = S.runs?.[feed] || [];
  if (kind.map) list = list.filter((r) => r.map);
  const short = (t) => t.replace(/^[A-Z][a-z]{2} /, "");   // "Sun 18 Oct 10:00" -> "18 Oct 10:00"
  panel.runSel.replaceChildren(new Option(list[0] ? `Latest ${short(list[0].text)}` : "Latest", "latest"),
    ...list.slice(1).map((r) => new Option(short(r.text), r.id)));
  panel.runSel.value = list.some((r, i) => i > 0 && r.id === o.run) ? o.run : "latest";
  const rid = panel.runSel.value === "latest" ? list[0]?.id : panel.runSel.value;
  const older = list.filter((r) => r.id < rid);
  panel.vsSel.replaceChildren(new Option("vs – none –", "none"),
    new Option(feed === "seasonal" ? "vs last month" : "vs yesterday (auto)", "auto"),
    ...older.map((r) => new Option(`vs ${short(r.text)}`, r.id)));
  const def = kind.vsDefault || "auto";
  panel.vsSel.value = [...panel.vsSel.options].some((x) => x.value === o.vs) ? o.vs : def;
  panel.runSel.title = `Which ${feed === "seasonal" ? "forecast month" : "run"} this panel shows`;
  panel.vsSel.title = older.length ? "Compare with an earlier run (dashed / ◆ / change column; map: change map)"
    : "No earlier run on disk yet – each refresh adds one";
}
const dataKey = (panel) => {
  const kind = PANELS[panel.item.kind];
  return kind?.source ? `${kind.source}?${new URLSearchParams(kind.query ? kind.query(panel.opts) : {})}` : null;
};

function makePanel(item) {
  const kind = PANELS[item.kind];
  const el = document.createElement("div");
  el.className = "panel";
  el.style.setProperty("--fs", item.font || 1);
  el.innerHTML = `<div class="panel-head"><span class="code"></span><span class="swatch"></span><span class="pickers"></span>
    <span class="title"></span><span class="runs"></span><span class="sub"></span><span class="ctls"></span></div><div class="panel-body"></div>`;
  const head = el.querySelector(".panel-head"), body = el.querySelector(".panel-body");
  const opts = item.opts || (item.opts = {});
  const panel = {
    item, el, opts,
    setSub: (t) => { head.querySelector(".sub").textContent = t || ""; },
    onPick: null,
  };
  head.querySelector(".code").textContent = kind?.code || "?";
  head.querySelector(".title").textContent = kind ? kind.title : item.kind;
  const swatch = () => {
    const s = head.querySelector(".swatch");
    s.style.background = REGION_COLOURS[opts.region] || "transparent";
    s.style.display = opts.region ? "" : "none";
  };
  // pickers in the title bar (region / field / model), remembered in the page
  for (const key of kind?.pickers || []) {
    const p = PICKER[key];
    if (!opts[key]) opts[key] = p.def;
    const sel = document.createElement("select");
    sel.title = p.title;
    sel.dataset.key = key;
    let list = p.opts;
    if (key === "field" && item.kind === "seasonal") list = list.map(([k, l]) => [k, k === "wind" ? "Wind 10 m" : l]);
    sel.append(...list.map(([v, l]) => new Option(l, v, false, v === opts[key])));
    sel.onchange = () => {
      opts[key] = sel.value;
      swatch();
      saveSoon();
      if (key === "src" || key === "model") fillRuns(panel);   // other model, other runs
      if (panel.onPick) panel.onPick(key);
      else if (key === "model") loadData().then(() => feed(panel));
      else panel.impl.redraw?.();
    };
    sel.onmousedown = (e) => e.stopPropagation();   // don't start a drag in edit mode
    head.querySelector(".pickers").appendChild(sel);
  }
  if (kind?.runFeed) {
    for (const key of ["run", "vs"]) {
      const sel = document.createElement("select");
      sel.className = `run-pick ${key}`;
      sel.dataset.key = key;
      sel.onmousedown = (e) => e.stopPropagation();
      sel.onchange = () => {
        opts[key] = sel.value;
        if (key === "run") fillRuns(panel);   // vs list = runs older than the chosen one
        opts.vs = panel.vsSel.value;
        saveSoon();
        if (panel.onPick) panel.onPick(key);
        else loadData().then(() => feed(panel));
      };
      head.querySelector(".runs").appendChild(sel);
      panel[key === "run" ? "runSel" : "vsSel"] = sel;
    }
  }
  swatch();
  const ctls = head.querySelector(".ctls");
  if (HELP[item.kind]) ctls.append(button("ⓘ", "How to read this panel", () => showHelp(item.kind), "help-btn"));
  ctls.append(
    button("A−", "Smaller text", () => setFont(panel, -FONT_STEP), "edit-only"),
    button("A+", "Bigger text", () => setFont(panel, +FONT_STEP), "edit-only"),
    button("▁", "Minimise / restore", () => setMin(panel, !item.min)),
    button("✕", "Remove this panel", () => removePanel(panel), "edit-only remove"),
  );
  head.addEventListener("click", (e) => {   // a minimised panel: click its title bar to restore
    if (item.min && !e.target.closest("button, select")) setMin(panel, false);
  });
  fillRuns(panel);
  panel.impl = kind ? kind.create(body, panel) : { update() {}, resize() {} };
  el.classList.toggle("min", !!item.min);
  return panel;
}

function feed(panel) {   // give a panel its data
  const kind = PANELS[panel.item.kind];
  if (!kind) return;
  if (kind.status) panel.impl.update(null, S.status);
  else if (kind.source) panel.impl.update(S.data[dataKey(panel)], S.status);
}

function setFont(panel, step) {
  const f = Math.round(Math.min(FONT_MAX, Math.max(FONT_MIN, (panel.item.font || 1) + step)) * 10) / 10;
  panel.item.font = f;
  panel.el.style.setProperty("--fs", f);
  panel.impl.resize();
  panel.impl.redraw?.();
  saveSoon();
}

function setMin(panel, on) {
  const it = panel.item, node = panel.widget.gridstackNode;
  if (on) { it.hFull = node.h; it.min = true; S.grid.update(panel.widget, { h: 1 }); }
  else { it.min = false; S.grid.update(panel.widget, { h: it.hFull || 12 }); }
  panel.el.classList.toggle("min", !!it.min);
  panel.impl.resize();
  saveSoon();
}

function removePanel(panel) {
  panel.impl.dispose?.();
  S.grid.removeWidget(panel.widget);
  S.panels.delete(panel.item.id);
  document.body.classList.toggle("empty-page", !S.panels.size);
  saveSoon();
}

// ---------- grid ----------
const rows = () => S.layout?.rows || 36;
const cellHeight = () => Math.max(10, Math.floor((window.innerHeight - document.getElementById("bar").offsetHeight) / rows()));

function initGrid() {
  S.grid = GridStack.init({
    column: 24, cellHeight: cellHeight(), margin: 0, float: true, staticGrid: true, maxRow: rows(),
    animate: false, disableOneColumnMode: true, columnOpts: { breakpoints: [] },
    draggable: { handle: ".panel-head" }, resizable: { handles: "e, se, s, sw, w" },
  }, document.getElementById("grid"));
  S.grid.on("change", (e, nodes) => {
    for (const n of nodes || []) {
      const p = S.panels.get(n.id);
      if (!p) continue;
      Object.assign(p.item, { x: n.x, y: n.y, w: n.w });
      if (!p.item.min) p.item.h = n.h;
    }
    saveSoon();
  });
  window.addEventListener("resize", () => {
    S.grid.cellHeight(cellHeight());
    for (const p of S.panels.values()) p.impl.resize();
  });
}

function addPanel(item) {
  const pos = item.x === undefined ? { autoPosition: true } : { x: item.x, y: item.y };
  const w = S.grid.addWidget({ ...pos, w: item.w, h: item.min ? 1 : item.h, id: item.id });
  Object.assign(item, { x: w.gridstackNode.x, y: w.gridstackNode.y });
  const panel = makePanel(item);
  panel.widget = w;
  w.querySelector(".grid-stack-item-content").appendChild(panel.el);
  S.panels.set(item.id, panel);
  new ResizeObserver(() => panel.impl.resize()).observe(panel.el);
  return panel;
}

function loadLayout(layout) {
  S.loading = true;   // opening a page is not a change: don't save it
  for (const p of S.panels.values()) p.impl.dispose?.();
  S.layout = layout;
  S.grid.removeAll();
  S.panels.clear();
  S.grid.batchUpdate();
  S.grid.opts.maxRow = rows();
  for (const item of layout.panels) addPanel(item);
  S.grid.batchUpdate(false);
  S.grid.cellHeight(cellHeight());
  clearTimeout(saveTimer);
  S.loading = false;
  document.body.classList.toggle("empty-page", !layout.panels.length);
  loadData();
}

// ---------- pages ----------
const current = () => ({ ...S.layout, name: S.page, panels: [...S.panels.values()].map((p) => p.item) });
let saveTimer = null;
function saveSoon() {
  if (S.loading) return;
  clearTimeout(saveTimer);
  const name = S.page, layout = current();   // save to the page that changed, even if another opens meanwhile
  saveTimer = setTimeout(() => putLayout(name, layout), 600);
}
const putLayout = (name, layout) =>
  fetch(`/api/layout/${encodeURIComponent(name)}`, { method: "PUT", body: JSON.stringify({ ...layout, name }) });
async function saveNow(name = S.page) { clearTimeout(saveTimer); if (S.layout) await putLayout(name, current()); }
const builtIn = (name) => fetch(`layouts/${encodeURIComponent(name)}.json`).then((r) => (r.ok ? r.json() : null)).catch(() => null);
const empty = () => ({ columns: 24, rows: 36, panels: [] });
const deepCopy = (x) => JSON.parse(JSON.stringify(x));

async function openPage(name) {
  let layout = await fetch(`/api/layout/${encodeURIComponent(name)}`).then((r) => r.json()).catch(() => ({}));
  if (!layout?.panels) layout = (await builtIn(name)) || empty();   // never saved: built-in layout (or empty)
  S.page = name;
  loadLayout(layout);
  fetch("/api/settings", { method: "POST", body: JSON.stringify({ page: name }) });
  await fillTabs();
}
async function showPage(name) {
  if (name === S.page) return;
  await saveNow();
  await openPage(name);
}
window.__showPage = showPage;
const pageNames = () => fetch("/api/layouts").then((r) => r.json()).catch(() => S.builtIn);

async function fillTabs() {
  const tabs = document.getElementById("tabs");
  const names = await pageNames();
  tabs.replaceChildren(...names.map((n) => {
    const b = document.createElement("button");
    b.className = "tab" + (n === S.page ? " on" : "");
    b.textContent = n;
    b.onclick = () => showPage(n);
    return b;
  }));
  const add = document.createElement("button");
  add.className = "tab add edit-only";
  add.textContent = "+ Page";
  add.title = "Add a new (empty) page";
  add.onclick = newPage;
  tabs.appendChild(add);
}

const cleanName = (t) => (t || "").replace(/[^\w &\-]/g, "").replace(/\s+/g, " ").trim();
async function newPage() {
  const name = cleanName(await ask("Name of the new page (e.g. NSW detail):", { input: "", ok: "Add page" }));
  if (!name) return;
  if ((await pageNames()).includes(name)) return ask(`There is already a page called "${name}".`);
  await saveNow();
  S.page = name;
  loadLayout(empty());
  await saveNow(name);
  await openPage(name);
}
async function renamePage() {
  const old = S.page;
  if (S.builtIn.includes(old)) return ask(`"${old}" is a built-in page and keeps its name. Use "Copy…" to make your own version.`);
  const name = cleanName(await ask(`New name for the page "${old}":`, { input: old, ok: "Rename" }));
  if (!name || name === old) return;
  if ((await pageNames()).includes(name)) return ask(`There is already a page called "${name}".`);
  clearTimeout(saveTimer);
  await putLayout(name, current());
  await fetch(`/api/layout/${encodeURIComponent(old)}`, { method: "DELETE" });
  await openPage(name);
}
async function copyPage() {
  const name = cleanName(await ask("Save a copy of this page called:", { input: `${S.page} copy`, ok: "Save copy" }));
  if (!name) return;
  if ((await pageNames()).includes(name)) return ask(`There is already a page called "${name}".`);
  await saveNow();
  await putLayout(name, deepCopy(current()));
  await openPage(name);
}
async function deletePage() {
  if (S.builtIn.includes(S.page)) return ask(`"${S.page}" is a built-in page and can't be deleted – use Reset to put it back.`);
  if (!(await ask(`Delete the page "${S.page}"?`, { ok: "Delete" }))) return;
  clearTimeout(saveTimer);   // a save still waiting would bring it back
  await fetch(`/api/layout/${encodeURIComponent(S.page)}`, { method: "DELETE" });
  await openPage(S.builtIn[0]);
}
async function resetPage() {
  const b = await builtIn(S.page);
  if (!b) return ask(`"${S.page}" is your own page – it has no built-in layout to go back to.`);
  if (!(await ask(`Put "${S.page}" back to its built-in layout?`, { ok: "Reset" }))) return;
  loadLayout(b);
  await saveNow();
}

function fillAddList() {
  const sel = document.getElementById("add-panel");
  sel.replaceChildren(new Option("+ Add panel…", ""),
    ...Object.entries(PANELS).map(([kind, p]) => new Option(`${p.code} · ${p.title}`, kind)));
}
function addNewPanel(kind) {
  const sizes = kind === "map" ? [[12, 30], [10, 24], [8, 18]] : kind === "about" ? [[6, 18], [5, 12]] : [[8, 18], [6, 14], [5, 10]];
  const size = sizes.find(([w, h]) => S.grid.willItFit({ w, h, autoPosition: true }));
  if (!size) return ask("No free space for a new panel. Make room first: shrink, minimise or remove a panel.");
  const item = { id: `${kind}-${Date.now().toString(36)}`, kind, w: size[0], h: size[1], font: 1, opts: {} };
  const p = addPanel(item);
  document.body.classList.remove("empty-page");
  loadData().then(() => feed(p));
  saveSoon();
}

// ---------- dialogs (same look in the program window and a browser) ----------
function dialog(html, onOpen) {
  return new Promise((resolve) => {
    const back = document.createElement("div");
    back.className = "modal-back";
    back.innerHTML = `<div class="modal">${html}</div>`;
    document.body.appendChild(back);
    const close = (v) => { back.remove(); document.removeEventListener("keydown", key, true); resolve(v); };
    const key = (e) => {
      if (e.key === "Escape") { e.stopPropagation(); close(null); }
      if (e.key === "Enter" && e.target.tagName !== "BUTTON") { e.preventDefault(); back.querySelector(".ok").click(); }
    };
    document.addEventListener("keydown", key, true);
    back.querySelector(".cancel").onclick = () => close(null);
    back.onclick = (e) => { if (e.target === back) close(null); };
    onOpen(back.querySelector(".modal"), close);
  });
}
function ask(message, { input = null, ok = "OK" } = {}) {
  return dialog(`<p>${esc(message)}</p>${input !== null ? `<input class="field" value="${esc(input)}">` : ""}
    <div class="btns"><button class="cancel">Cancel</button><button class="ok primary">${esc(ok)}</button></div>`,
  (box, close) => {
    const field = box.querySelector(".field");
    (field || box.querySelector(".ok")).focus();
    box.querySelector(".ok").onclick = () => close(field ? field.value : true);
  });
}
let HELP = {};
function showHelp(kind) {
  const h = HELP[kind];
  dialog(`<div class="help-pop"><h3>${esc(h.code)} – ${esc(h.title)}</h3>${h.html}</div>
    <div class="btns"><button class="cancel ok primary">Close</button></div>`, (box) => { box.classList.add("wide"); box.querySelector(".ok").focus(); });
}

// ---------- Refresh (W-018): the program downloads; the choice sets how much ----------
async function refreshDialog() {
  if (S.status?.refreshing) return ask("A refresh is already running – its progress is in the header and the About panel.");
  const mode = await dialog(`<h3>Refresh – download the newest forecasts</h3>
    <p>Only the east coast is kept (the rest is thrown away as it downloads). The screen keeps working meanwhile;
    if the PC is turned off, the next refresh carries on where it stopped.</p>
    <div class="refresh-choices">
      <button class="choice" data-mode="cloud"><b>From the cloud (recommended)</b><span>Only the new NEM-only files the GitHub job made ·
        <b>~60 MB per new run</b>, seconds · happens by itself every hour</span></button>
      <p class="hint-text">Back-up – download directly from ECMWF on this PC:</p>
      <button class="choice" data-mode="full"><b>Full</b><span>BOM + main model + AI model + <b>ensemble</b> + seasonal ·
        <b>~18 GB</b> · home internet (≈ 30 min fast, ≈ 4 h at 10 Mbit/s)</span></button>
      <button class="choice" data-mode="light"><b>Without ensemble</b><span>BOM + main model + AI model + seasonal ·
        <b>~1.5 GB</b> · the range bands stay on the last full refresh</span></button>
      <button class="choice" data-mode="bom"><b>BOM only</b><span>BOM forecasts + observations · <b>a few KB</b> · fine on any internet</span></button>
    </div>
    <div class="btns"><button class="cancel">Cancel</button><button class="ok" style="display:none"></button></div>`,
  (box, close) => { box.querySelectorAll(".choice").forEach((b) => { b.onclick = () => close(b.dataset.mode); }); });
  if (!mode) return;
  const r = await fetch("/api/refresh", { method: "POST", body: JSON.stringify({ mode }) }).then((x) => x.json()).catch((e) => ({ error: e.message }));
  if (!r.ok) return ask(`Refresh didn't start: ${r.error}`);
  pollStatus();
}

// ---------- edit mode ----------
function setEditing(on) {
  S.editing = on;
  document.body.classList.toggle("editing", on);
  S.grid.setStatic(!on);
  document.getElementById("edit").textContent = on ? "Done" : "Edit";
  if (!on) saveNow();
}

// ---------- data ----------
async function loadData(force = false) {
  const need = new Set([...S.panels.values()].map(dataKey).filter(Boolean));
  await Promise.all([...need].filter((k) => force || !S.data[k]).map(async (k) => {
    S.data[k] = await fetch(`/api/${k}`).then((r) => r.json()).catch((e) => ({ error: `Server not reachable (${e.message})` }));
  }));
  for (const p of S.panels.values()) feed(p);
}

async function pollStatus() {
  try {
    const st = await fetch("/api/status").then((r) => r.json());
    const changed = S.version !== null && st.version !== S.version;
    S.status = st;
    S.version = st.version;
    showStatus(st);
    const rb = document.getElementById("refresh");
    rb.textContent = st.refreshing ? "Refreshing…" : "Refresh";
    rb.classList.toggle("busy", !!st.refreshing);
    if (changed) {   // a refresh finished a run: new runs to pick, new data for every panel
      S.data = {};
      S.runs = await fetch("/api/runs").then((r) => r.json()).catch(() => S.runs);
      for (const p of S.panels.values()) fillRuns(p);
      await loadData(true);
    } else {
      for (const p of S.panels.values()) if (PANELS[p.item.kind]?.status) feed(p);
    }
  } catch {
    document.getElementById("status").innerHTML = '<span class="old">Server not reachable</span>';
  }
}
function showStatus(st) {
  const short = { ifs: "IFS", aifs: "AIFS", ens: "Ens", bom: "BOM" };
  const runs = st.feeds.filter((f) => short[f.feed]).map((f) => f.run
    ? `${short[f.feed]} <span class="${f.age_h > 30 ? "old" : ""}">${esc(f.run_text)}</span>` : `${short[f.feed]} –`).join(" · ");
  const p = st.progress, pt = progressText(p);
  const cls = p?.active && !p.stalled ? "dl" : (p?.error || p?.stalled ? "old" : "");
  document.getElementById("status").innerHTML = (pt ? `<span class="${cls}">${esc(pt)}</span> · ` : "") + runs;
}
function clock() {
  const t = new Date(Date.now() + 10 * 3600e3);   // NEM time = UTC+10
  const day = t.toLocaleDateString("en-AU", { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" });
  document.getElementById("clock").textContent = `${day} ${t.toISOString().slice(11, 16)} NEM`;
}

// ---------- theme: charts pick it up when rebuilt ----------
function setTheme(name) {
  document.body.classList.toggle("theme-dark", name === "dark");
  document.body.classList.toggle("theme-light", name !== "dark");
  for (const [id, p] of S.panels) {
    p.impl.dispose?.();
    const host = p.el.parentElement;
    p.el.remove();
    const fresh = makePanel(p.item);
    fresh.widget = p.widget;
    host.appendChild(fresh.el);
    S.panels.set(id, fresh);
    new ResizeObserver(() => fresh.impl.resize()).observe(fresh.el);
    feed(fresh);
  }
}

async function start() {
  const settings = await fetch("/api/settings").then((r) => r.json()).catch(() => ({}));
  HELP = await fetch("help.json").then((r) => r.json()).catch(() => ({}));
  S.builtIn = (await pageNames()).slice(0, 5);
  S.runs = await fetch("/api/runs").then((r) => r.json()).catch(() => ({}));
  document.body.classList.add(settings.theme === "dark" ? "theme-dark" : "theme-light");
  initGrid();
  fillAddList();
  clock();
  setInterval(clock, 15000);
  await pollStatus();
  await openPage((await pageNames()).includes(settings.page) ? settings.page : S.builtIn[0]);
  setInterval(pollStatus, 5000);   // local and tiny: download progress moves every few seconds

  const $ = (id) => document.getElementById(id);
  $("theme").onclick = () => {
    const next = document.body.classList.contains("theme-dark") ? "light" : "dark";
    setTheme(next);
    fetch("/api/settings", { method: "POST", body: JSON.stringify({ theme: next }) });
  };
  $("edit").onclick = () => setEditing(!S.editing);
  $("refresh").onclick = refreshDialog;
  $("add-panel").onchange = (e) => { if (e.target.value) addNewPanel(e.target.value); e.target.value = ""; };
  $("rename-page").onclick = renamePage;
  $("copy-page").onclick = copyPage;
  $("delete-page").onclick = deletePage;
  $("reset-page").onclick = resetPage;
  document.addEventListener("keydown", (e) => {
    if (e.ctrlKey && (e.key === "e" || e.key === "E")) { e.preventDefault(); setEditing(!S.editing); }
    if (e.key === "Escape" && S.editing && !document.querySelector(".modal-back")) setEditing(false);
  });
}

start();
