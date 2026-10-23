// Weather panels. Each kind: { code, title, source, pickers, create(body, panel) -> { update(data, status), resize() } }.
// `source` = the /api/<source> data the panel needs (fetched once for all panels). Cards: 4. Docs\panels\<code>_*.md
// Panel options (remembered in the page): opts.region (NSW…), opts.field (temp / wind / solar / rain), map: opts.src.

export const REGIONS = [["NSW", "Sydney"], ["QLD", "Brisbane"], ["VIC", "Melbourne"], ["SA", "Adelaide"], ["TAS", "Hobart"]];
export const REGION_COLOURS = { NSW: "#1f77b4", QLD: "#d62728", SA: "#ff7f0e", VIC: "#2ca02c", TAS: "#9467bd" };
export const FIELDS = { temp: "Temperature", wind: "Wind 100 m", solar: "Solar", rain: "Rain" };
const UNIT = { temp: "°C", wind: "km/h", solar: "W/m²", rain: "mm" };
const SEAS_UNIT = { temp: "°C", rain: "mm/day", wind: "km/h (10 m)", solar: "W/m²" };
const C_IFS = "#1e88e5", C_AI = "#8e5cc4", C_ENS = "#607d8b";

export const fmt = (v, d = 0) => (v === null || v === undefined || Number.isNaN(v)) ? "–"
  : Number(v).toLocaleString("en-AU", { minimumFractionDigits: d, maximumFractionDigits: d });
export const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const dark = () => document.body.classList.contains("theme-dark");

// ---------- chart basics (sizes follow the panel's text size) ----------
function style(panel) {
  const f = parseFloat(getComputedStyle(panel.el).fontSize) * 0.8;
  const txt = dark() ? "#c8d0d8" : "#333";
  return {
    f, label: { fontSize: f, color: txt },
    split: { lineStyle: { color: dark() ? "#2a313b" : "#e6e9ec" } },
    legend: { top: 0, textStyle: { fontSize: f, color: txt }, itemWidth: f * 1.4, itemHeight: f * 0.7 },
    grid: { left: f * 3.6, right: f * 3.2, top: f * 2.6, bottom: f * 2.2 },
  };
}
const timeAxis = (a) => ({
  type: "time", axisLabel: { ...a.label, hideOverlap: true, formatter: { day: "{ee} {d}", hour: "{HH}:{mm}", month: "{MMM}" } },
  splitLine: { show: true, ...a.split },
});
const valueAxis = (a, name, extra = {}) => ({
  type: "value", name, nameTextStyle: { fontSize: a.f, color: a.label.color }, nameGap: a.f * 0.6,
  axisLabel: { ...a.label }, splitLine: a.split, scale: true, ...extra,
});
const pairs = (t, v) => t.map((x, i) => [x, v[i]]);
const line = (name, t, v, color, extra = {}) => ({
  name, type: "line", showSymbol: false, lineStyle: { width: 2 }, color, data: pairs(t, v), ...extra,
});
// Range (10–90 %) as a shaded band: invisible lower line + stacked difference
function band(name, t, lo, hi, color) {
  return [
    { name, type: "line", stack: name, showSymbol: false, lineStyle: { opacity: 0 }, color, data: pairs(t, lo), tooltip: { show: false } },
    { name, type: "line", stack: name, showSymbol: false, lineStyle: { opacity: 0 }, color,
      areaStyle: { color, opacity: 0.28 }, data: t.map((x, i) => [x, hi[i] === null || lo[i] === null ? null : hi[i] - lo[i]]),
      tooltip: { show: false } },
  ];
}
// Vertical 10–90 % whiskers on a category axis (shift: sideways, for grouped bars)
function whiskers(name, lo, hi, color, shift = 0) {
  return {
    name, type: "custom", z: 10, color, encode: { x: 0, y: [1, 2] },
    renderItem: (p, a) => {
      const x = a.value(0), bw = a.size([1, 0])[0], w = bw * (shift ? 0.06 : 0.12);
      const l = a.coord([x, a.value(1)]), h = a.coord([x, a.value(2)]);
      l[0] += bw * shift; h[0] += bw * shift;
      const st = { stroke: color, lineWidth: 1.5 };
      return { type: "group", children: [
        { type: "line", shape: { x1: l[0], y1: l[1], x2: h[0], y2: h[1] }, style: st },
        { type: "line", shape: { x1: l[0] - w, y1: l[1], x2: l[0] + w, y2: l[1] }, style: st },
        { type: "line", shape: { x1: h[0] - w, y1: h[1], x2: h[0] + w, y2: h[1] }, style: st }] };
    },
    data: lo.map((v, i) => [i, v, hi[i]]),
  };
}
// BOM's daily high (▲ at 3 pm) and low (▼ at 6 am) on a time axis
function bomMarks(a, marks, t0, t1) {
  const pick = (k, hh) => (marks || []).filter((m) => m[k] !== null).map((m) => [`${m.date}T${hh}`, m[k]])
    .filter((p) => p[0] >= t0 && p[0] <= t1);
  const border = { borderColor: dark() ? "#fff" : "#000", borderWidth: 0.8 };
  return [
    { name: "BOM high", type: "scatter", symbol: "triangle", symbolSize: a.f, color: "#d32f2f", z: 12, data: pick("high", "15:00"), itemStyle: border },
    { name: "BOM low", type: "scatter", symbol: "triangle", symbolRotate: 180, symbolSize: a.f, color: "#1976d2", z: 12,
      data: pick("low", "06:00"), itemStyle: border },
  ];
}
function bomCell(b) {
  if (!b || (b.high === null && b.low === null && b.chance === null)) return '<td class="rng">–</td>';
  const rain = b.rain_hi === null ? "" : (b.rain_lo === b.rain_hi ? `${fmt(b.rain_hi)} mm` : `${fmt(b.rain_lo)}–${fmt(b.rain_hi)} mm`);
  return `<td title="BOM: ${esc(b.words)}">${fmt(b.high)} / ${fmt(b.low)} <span class="rng">${rain}${b.chance !== null ? ` ${fmt(b.chance)}%` : ""}</span></td>`;
}
// Axis tooltip: one line per series; the band shown as "Range 10–90%: a – b" when the time matches
function tipWithBand(t, lo, hi) {
  return (ps) => {
    if (!ps.length) return "";
    let s = `${esc(echarts.time.format(ps[0].axisValue, "{ee} {d} {MMM} {HH}:{mm}"))}<br>`;
    const i = t ? t.indexOf(echarts.time.format(ps[0].axisValue, "{yyyy}-{MM}-{dd}T{HH}:{mm}")) : -1;
    if (i >= 0) s += `Range 10–90%: ${fmt(lo[i], 1)} – ${fmt(hi[i], 1)}<br>`;
    ps.filter((p) => !p.seriesName.startsWith("Range")).forEach((p) => {
      s += `${p.marker}${esc(p.seriesName)}: ${fmt(Array.isArray(p.value) ? p.value[1] : p.value, 1)}<br>`;
    });
    return s;
  };
}
const base = (a) => ({ animation: false, backgroundColor: "transparent", grid: a.grid, legend: a.legend });
const dashed = (name, t, v, color, extra = {}) => line(name, t, v, color, { lineStyle: { width: 1.6, type: "dashed" }, ...extra });
const vsName = (d) => `vs ${d.vs_text}`;
// change vs the older run: "+2.1", yellow when |change| >= limit
function chg(n, o, lim, dp = 1) {
  if (n === null || n === undefined || o === null || o === undefined) return '<span class="rng">–</span>';
  const c = n - o;
  return `<span class="${Math.abs(c) >= lim ? "chg-big" : ""}">${c > 0 ? "+" : ""}${fmt(c, dp)}</span>`;
}
// ◆ on a category axis (shift: sideways, for grouped bars)
function diamonds(name, vals, color, shift = 0) {
  return {
    name, type: "custom", z: 11, color, encode: { x: 0, y: 1 },
    renderItem: (p, a) => {
      if (a.value(1) === null || Number.isNaN(a.value(1))) return null;
      const bw = a.size([1, 0])[0], c = a.coord([a.value(0), a.value(1)]), r = Math.max(4, bw * 0.08);
      c[0] += bw * shift;
      return { type: "polygon", shape: { points: [[c[0], c[1] - r], [c[0] + r, c[1]], [c[0], c[1] + r], [c[0] - r, c[1]]] },
        style: { fill: "#fff", stroke: color, lineWidth: 2 } };
    },
    data: vals.map((v, i) => [i, v]),
  };
}

// ---------- S1 Short ----------
function shortChart(c, r, field, a, d) {
  const series = [];
  const v = r.vs;
  const y = [valueAxis(a, UNIT[field])];
  const b = r.band;
  const t0 = r.time[0], t1 = r.time[r.time.length - 1];
  let tip = { trigger: "axis", valueFormatter: (v) => fmt(v, 1) };
  if (field === "temp" || field === "wind") {
    if (b) series.push(...band("Range 10–90%", b.time, b[field].p10, b[field].p90, C_ENS));
    series.push(line("IFS", r.time, r[field], C_IFS));
    if (r.aifs) series.push(line("AIFS (AI)", r.aifs.time, r.aifs[field], C_AI, { lineStyle: { width: 1.5 } }));
    if (field === "temp") series.push(...bomMarks(a, r.bom_marks, t0, t1));
    if (v) series.push(dashed(`IFS ${vsName(d)}`, v.time, v[field], C_IFS));
    if (b) tip = { trigger: "axis", formatter: tipWithBand(b.time, b[field].p10, b[field].p90) };
  }
  if (field === "solar") {
    if (b) series.push(...band("Range 10–90%", b.time_mid, b.solar.p10, b.solar.p90, "#c9a227"));
    series.push(line("IFS solar", r.time_mid, r.solar, "#f2a900", { areaStyle: { opacity: 0.25 } }));
    if (v) series.push(dashed(`IFS solar ${vsName(d)}`, v.time_mid, v.solar, "#b07800"));
    if (b) tip = { trigger: "axis", formatter: tipWithBand(b.time_mid, b.solar.p10, b.solar.p90) };
    series.push(line("Cloud %", r.time, r.cloud, "#90a4ae", { yAxisIndex: 1, lineStyle: { width: 1.5, type: "dashed" } }));
    y[0].min = 0;
    y.push(valueAxis(a, "cloud %", { min: 0, max: 100, splitLine: { show: false } }));
  }
  if (field === "rain") {
    series.push({ name: "Rain (mm per 3 h)", type: "bar", color: "#2a7ab0", data: pairs(r.time_mid, r.rain), barMaxWidth: 12 });
    if (v) series.push({ name: `Rain ${vsName(d)}`, type: "bar", barGap: "-100%", barMaxWidth: 12, color: "transparent",
      itemStyle: { borderColor: "#e65100", borderWidth: 1.5, borderType: "dashed" }, data: pairs(v.time_mid, v.rain), z: 3 });
    y[0].min = 0;
    y[0].scale = false;
  }
  c.setOption({ ...base(a), tooltip: tip, xAxis: { ...timeAxis(a), min: t0, max: t1 }, yAxis: y, series }, true);
}
function shortTable(r, field, d) {
  const v = r.vs?.daily;
  return `<table class="grid"><tr><th class="l">Day</th><th>High °C</th><th>Low °C</th>
    <th title="IFS day total; % = share of the 50 ensemble runs with at least 1 mm">Rain mm · chance</th>
    <th>Wind km/h</th><th>Sun kWh/m²</th><th title="BOM's city forecast: high / low, rain range, chance of rain">BOM</th>
    ${v ? `<th title="Change since the ${esc(d.vs_text)} run: high / low °C · rain mm">Change vs ${esc(d.vs_text.slice(4))}</th>` : ""}</tr>
    ${r.daily.map((d) => `<tr data-date="${d.date}" class="${d.part ? "part" : ""} ${d.date === DAY.date ? "dayon" : ""}"
    title="${d.part ? "Part day – the forecast starts or ends during this day" : ""}"><td class="l">${esc(d.day)}${d.part ? " (part)" : ""}</td>
    <td>${fmt(d.high, 1)}</td><td>${fmt(d.low, 1)}</td>
    <td>${fmt(d.rain, 1)}${d.rain_chance !== null && d.rain_chance !== undefined ? ` <span class="rng">${d.rain_chance}%</span>` : ""}</td>
    <td>${fmt(d.wind)}</td><td>${fmt(d.solar, 1)}</td>${bomCell(d.bom)}${v ? `<td>${v[d.date] && !d.part && v[d.date].hours >= 20
      ? `${chg(d.high, v[d.date].high, 2)} / ${chg(d.low, v[d.date].low, 2)} · ${chg(d.rain, v[d.date].rain, 5)}`
      : '<span class="rng" title="Part day in one of the runs – not comparable">–</span>'}</td>` : ""}</tr>`).join("")}</table>`;
}

// ---------- M1 Medium ----------
const rng = (v, d = 0) => `${fmt(v[1], d)} <span class="rng">(${fmt(v[0], d)}–${fmt(v[2], d)})</span>`;
function mediumChart(c, r, field, a, d) {
  let opt;
  const v = r.vs;
  if (field === "temp" || field === "wind") {
    const q = r[field];
    const series = [...band("Range 10–90%", r.time, q.p10, q.p90, C_ENS),
      line("Ensemble middle", r.time, q.p50, C_ENS, { lineStyle: { width: 2.5 } })];
    if (r.lines.ifs) series.push(line("IFS", r.lines.ifs.time, r.lines.ifs[field], C_IFS, { lineStyle: { width: 1.5 } }));
    if (r.lines.aifs) series.push(line("AIFS (AI)", r.lines.aifs.time, r.lines.aifs[field], C_AI, { lineStyle: { width: 1.5 } }));
    const tMin = r.time[0], tMax = r.time[r.time.length - 1];
    if (field === "temp") series.push(...bomMarks(a, r.bom_marks, tMin, tMax));
    if (v) {
      const vc = dark() ? "#cfd8dc" : "#37474f";
      series.push(dashed(`Middle ${vsName(d)}`, v.time, v[field].p50, vc, { lineStyle: { width: 2, type: "dashed" } }),
        dashed(`Range ${vsName(d)} (edges)`, v.time, v[field].p10, vc, { lineStyle: { width: 0.8, type: "dotted" }, tooltip: { show: false } }),
        dashed(`Range ${vsName(d)} (edges) `, v.time, v[field].p90, vc, { lineStyle: { width: 0.8, type: "dotted" }, tooltip: { show: false } }));
    }
    opt = { xAxis: { ...timeAxis(a), min: tMin, max: tMax }, yAxis: [valueAxis(a, UNIT[field])], series,
      tooltip: { trigger: "axis", formatter: tipWithBand(r.time, q.p10, q.p90) } };
  } else {
    const key = field;
    const days = r.daily.map((d) => d.day.slice(0, 6));
    const series = [
      { name: "Ensemble middle", type: "bar", color: C_ENS, barMaxWidth: 14, data: r.daily.map((d) => d[key][1]) },
      whiskers("Range 10–90%", r.daily.map((d) => d[key][0]), r.daily.map((d) => d[key][2]), dark() ? "#cfd8dc" : "#37474f"),
      { name: "IFS", type: "scatter", color: C_IFS, symbolSize: a.f * 0.7, data: r.daily.map((d) => d.ifs?.[key] ?? null) },
      { name: "AIFS (AI)", type: "scatter", color: C_AI, symbolSize: a.f * 0.7, symbol: "diamond", data: r.daily.map((d) => d.aifs?.[key] ?? null) },
    ];
    if (v) series.push({ name: `Middle ${vsName(d)}`, type: "scatter", symbol: "emptyCircle", symbolSize: a.f * 0.9, color: "#e65100",
      data: r.daily.map((x) => v.daily[x.date]?.[key]?.[1] ?? null), z: 12 });
    opt = { xAxis: { type: "category", data: days, axisLabel: { ...a.label, hideOverlap: true } },
      yAxis: [valueAxis(a, field === "rain" ? "mm / day" : "kWh/m² / day", { min: 0, scale: false })], series,
      tooltip: { trigger: "axis", formatter: (ps) => {
        const d = r.daily[ps[0].dataIndex];
        return `${esc(d.day)}<br>Ensemble middle: ${fmt(d[key][1], 1)} (range ${fmt(d[key][0], 1)}–${fmt(d[key][2], 1)})<br>
          IFS: ${fmt(d.ifs?.[key], 1)} · AIFS: ${fmt(d.aifs?.[key], 1)}${key === "rain" ? `<br>Chance of 1 mm+: ${d.rain_chance}%` : ""}${
          v?.daily[d.date] ? `<br>Middle in the earlier run: ${fmt(v.daily[d.date][key][1], 1)}` : ""}`;
      } } };
  }
  c.setOption({ ...base(a), ...opt }, true);
}
function mediumTable(r, field, d) {
  const v = r.vs?.daily;
  const change = (x) => {
    const o = v?.[x.date];
    if (!o) return '<td><span class="rng">–</span></td>';
    const rc = Math.abs(x.rain_chance - o.rain_chance) >= 30 ? "chg-big" : "";
    return `<td>${chg(x.high[1], o.high[1], 2)} / ${chg(x.low[1], o.low[1], 2)} · <span class="${rc}">rain ${o.rain_chance}→${x.rain_chance}%</span></td>`;
  };
  return `<table class="grid"><tr><th class="l">Day</th><th>High °C</th><th>Low °C</th><th>Rain mm</th>
    <th>Wind km/h</th><th>Sun kWh/m²</th><th title="BOM's city forecast (7 days): high / low, rain range, chance">BOM</th>
    ${v ? `<th title="Change of the middle run since the ${esc(d.vs_text)} run: high / low °C · rain chance">Change vs ${esc(d.vs_text.slice(4))}</th>` : ""}</tr>
    ${r.daily.map((x) => `<tr data-date="${x.date}" class="${x.date === DAY.date ? "dayon" : ""}"><td class="l">${esc(x.day)}</td>
    <td>${rng(x.high)}</td><td>${rng(x.low)}</td><td>${fmt(x.rain[1], 1)} <span class="rng">${x.rain_chance}%</span></td>
    <td>${fmt(x.wind[1])}</td><td>${fmt(x.solar[1], 1)}</td>${bomCell(x.bom)}${v ? change(x) : ""}</tr>`).join("")}</table>`;
}

// ---------- C1 AI vs IFS ----------
function compareChart(c, r, field, a) {
  let opt;
  if (field === "temp" || field === "wind") {
    opt = { xAxis: timeAxis(a), yAxis: [valueAxis(a, UNIT[field])],
      series: [line("IFS", r.ifs.time, r.ifs[field], C_IFS), line("AIFS (AI)", r.aifs.time, r.aifs[field], C_AI)],
      tooltip: { trigger: "axis", valueFormatter: (v) => fmt(v, 1) } };
  } else {
    const days = r.daily.map((d) => d.day.slice(0, 6));
    opt = { xAxis: { type: "category", data: days, axisLabel: { ...a.label, hideOverlap: true } },
      yAxis: [valueAxis(a, field === "rain" ? "mm / day" : "kWh/m² / day", { min: 0, scale: false })],
      series: [{ name: "IFS", type: "bar", color: C_IFS, data: r.daily.map((d) => d[field][0]) },
        { name: "AIFS (AI)", type: "bar", color: C_AI, data: r.daily.map((d) => d[field][1]) }],
      tooltip: { trigger: "axis", valueFormatter: (v) => fmt(v, 1) } };
  }
  c.setOption({ ...base(a), ...opt }, true);
}
const LIMIT = { high: 3, low: 3, rain: 5, solar: 1.5, wind: 10 };
function compareTable(r) {
  const cell = (v, k, d) => `<td class="${Math.abs(v[0] - v[1]) >= LIMIT[k] ? "big" : ""}">${fmt(v[0], d)} / ${fmt(v[1], d)}</td>`;
  return `<table class="grid"><tr><th class="l">Day</th><th>High</th><th>Low</th><th>Rain</th><th>Wind</th>
    <th>Sun</th></tr>${r.daily.map((x) => `<tr><td class="l">${esc(x.day)}</td>${cell(x.high, "high", 1)}
    ${cell(x.low, "low", 1)}${cell(x.rain, "rain", 1)}${cell(x.wind, "wind", 0)}${cell(x.solar, "solar", 1)}</tr>`).join("")}</table>`;
}

// ---------- L1 Seasonal ----------
const SEAS_COL = { temp: ["#2166ac", "#b2182b"], rain: ["#a6611a", "#018571"], wind: ["#5e3c99", "#e66101"], solar: ["#5e3c99", "#e6a100"] };
const WORD = { temp: ["warmer", "cooler"], rain: ["wetter", "drier"], wind: ["windier", "calmer"], solar: ["sunnier", "duller"] };
// ECMWF solid, BOM lighter, CFS (US) outline only; each with its own whiskers and ◆ (W-007, W-011a)
function seasModels(r, field) {
  return [["ECMWF", r[field], r.vs, 1], ["BOM", r.bom?.[field], r.vs_bom, 0.45], ["CFS (US)", r.cfs?.[field], r.vs_cfs, 0]]
    .filter((m) => m[1]).map(([name, q, vs, op]) => ({ name, q, vs, op }));
}
function seasonalChart(c, r, field, a, d) {
  const [neg, pos] = SEAS_COL[field], ms = seasModels(r, field), n = ms.length;
  const w = n === 1 ? 0.45 : n === 2 ? 0.30 : 0.26, shift = (k) => n === 1 ? 0 : (k - (n - 1) / 2) * w;
  const vsOf = (vs) => vs?.[field] ? r.months.map((m) => { const k = vs.months.indexOf(m); return k >= 0 ? vs[field].mean[k] : null; }) : null;
  const wc = dark() ? "#cfd8dc" : "#37474f";
  c.setOption({
    ...base(a), legend: { ...a.legend, data: ms.map((m) => m.name) },
    xAxis: { type: "category", data: r.months.map((m) => m.slice(0, 3)), axisLabel: a.label },
    yAxis: [valueAxis(a, `vs normal, ${SEAS_UNIT[field]}`, { scale: false })],
    tooltip: { trigger: "axis", formatter: (ps) => { const i = ps[0].dataIndex;
      const one = (n, x) => `<b>${n}</b>: ${fmt(x.mean[i], 2)} ${SEAS_UNIT[field]} (range ${fmt(x.p10[i], 1)} to ${fmt(x.p90[i], 1)}),
        chance above normal ${fmt(x.above[i])}%`;
      return `${esc(r.months[i])} vs normal<br>${ms.map((m) => one(m.name, m.q)).join("<br>")}`; } },
    series: [
      ...ms.map((m, k) => ({ name: m.name, type: "bar", barWidth: `${w * 100}%`, barGap: "0%",
        itemStyle: m.op ? { color: pos, opacity: m.op, borderColor: pos, borderWidth: m.op < 1 ? 1.5 : 0 } : { color: pos + "22", borderColor: pos, borderWidth: 2 },
        data: m.q.mean.map((v) => { const col = v >= 0 ? pos : neg;   // op 0 = outline bar (CFS): faint fill, solid edge
          return { value: v, itemStyle: m.op ? { color: col, opacity: m.op, borderColor: col, borderWidth: m.op < 1 ? 1.5 : 0 }
            : { color: col + "22", borderColor: col, borderWidth: 2 } }; }),
        ...(k === 0 ? { markLine: { silent: true, symbol: "none", data: [{ yAxis: 0 }], lineStyle: { color: a.label.color }, label: { show: false } } } : {}) })),
      ...ms.map((m, k) => whiskers(`Range ${m.name}`, m.q.p10, m.q.p90, wc, shift(k))),
      ...ms.flatMap((m, k) => { const v = vsOf(m.vs); return v ? [diamonds(`${m.name} ${vsName(d)}`, v, "#e65100", shift(k))] : []; })],
  }, true);
}
function seasonalTable(r, field, d) {
  const ms = seasModels(r, field), q = ms[0].q, [up, down] = WORD[field];
  const vs = r.vs?.[field] ? r.vs : null;
  const was = (m) => { const k = vs ? vs.months.indexOf(m) : -1; return k >= 0 ? vs[field].above[k] : null; };
  const dp = field === "temp" ? 1 : 2;
  const avg = (x, i) => `${x.mean[i] > 0 ? "+" : ""}${fmt(x.mean[i], dp)}`;
  const ch = (x, i) => `<td class="${x.above[i] >= 70 || x.above[i] <= 30 ? "big" : ""}" title="${x.above[i] <= 30 ? `Lean ${down}` : ""}">${fmt(x.above[i])}%</td>`;
  const short = (n) => n.replace(" (US)", "");
  return `<table class="grid"><tr><th class="l">Month</th>${ms.map((m) => `<th>${short(m.name)} avg</th><th>Chance ${up}</th>`).join("")}
    ${vs ? `<th title="ECMWF chance ${up}: ${esc(d.vs_text)} forecast → this one">Change vs ${esc(d.vs_text)}</th>` : ""}</tr>
    ${r.months.map((m, i) => `<tr><td class="l">${esc(m)}</td>
    ${ms.map((x) => `<td>${avg(x.q, i)}</td>${ch(x.q, i)}`).join("")}${vs ? `<td>${was(m) === null ? '<span class="rng">–</span>'
      : `<span class="${Math.abs(q.above[i] - was(m)) >= 20 ? "chg-big" : ""}">${fmt(was(m))} → ${fmt(q.above[i])}%</span>`}</td>` : ""}</tr>`).join("")}</table>`;
}

// ---------- one region, one field: chart above, daily table below ----------
// ---------- W-029 linked charts: one highlighted day for every page; hover linked per chart kind ----------
export const DAY = { date: null, onChange: null };
export function setDay(date, toggle = true) {
  DAY.date = toggle && DAY.date === date ? null : date;
  DAY.onChange?.();
}
const ymd = (t) => `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
function dayBand(chart, r) {   // yellow band over the highlighted day (times on the charts are NEM time)
  const opt = chart.getOption();
  if (!opt?.series?.length) return;
  const ax = opt.xAxis?.[0];
  let data = [];
  if (DAY.date && ax?.type === "category" && r.daily) {
    const i = r.daily.findIndex((x) => x.date === DAY.date);
    if (i >= 0) data = [[{ xAxis: ax.data[i] }, { xAxis: ax.data[i] }]];
  } else if (DAY.date && ax?.type === "time") {
    const n = new Date(`${DAY.date}T00:00`);
    n.setDate(n.getDate() + 1);
    data = [[{ xAxis: `${DAY.date}T00:00` }, { xAxis: `${ymd(n)}T00:00` }]];
  }
  chart.setOption({ series: [{ markArea: { silent: true, itemStyle: { color: "rgba(255, 193, 7, 0.25)" }, data } }] });
}
function clickedDay(chart, r, e) {   // the day under a click on the chart, or null
  const p = [e.offsetX, e.offsetY];
  if (!chart.containPixel("grid", p)) return null;
  const ax = chart.getOption().xAxis?.[0];
  const v = chart.convertFromPixel({ xAxisIndex: 0 }, p)[0];
  if (ax?.type === "category") return r.daily?.[Math.round(v)]?.date || null;
  return ax?.type === "time" ? ymd(new Date(v)) : null;
}

function regionPanel(draw, table, subtitle) {
  return (body, panel) => {
    body.innerHTML = '<div class="chart"></div><div class="table"></div>';
    const chEl = body.querySelector(".chart"), tb = body.querySelector(".table");
    const chart = echarts.init(chEl, dark() ? "dark" : null, { renderer: "canvas" });
    new ResizeObserver(() => chart.resize()).observe(chEl);   // the table below fills in after the chart: re-fit
    let last = null;
    chart.getZr().on("click", (e) => {   // W-029: click a day on the chart = highlight it everywhere
      const r = last?.regions?.[panel.opts.region];
      const day = r && clickedDay(chart, r, e);
      if (day) setDay(day);
    });
    tb.onclick = (e) => { const tr = e.target.closest("tr[data-date]"); if (tr) setDay(tr.dataset.date); };
    const draw_ = () => {
      const d = last;
      if (!d) { chart.clear(); tb.innerHTML = '<div class="empty">Loading…</div>'; return; }
      if (d.error) { chart.clear(); tb.innerHTML = `<div class="err">${esc(d.error)}</div>`; return; }
      const r = d.regions?.[panel.opts.region];
      if (!r) return;
      try {
        draw(chart, r, panel.opts.field, style(panel), d);
        dayBand(chart, r);
        const g = `${panel.item.kind}-${panel.opts.field}`;   // W-029: linked hover with the same kind of chart
        if (chart.group !== g) { chart.group = g; echarts.connect(g); }
        tb.innerHTML = table(r, panel.opts.field, d);
        chart.resize();
      } catch (e) { tb.innerHTML = `<div class="err">Could not draw: ${esc(e.message)}</div>`; console.error(e); }
      panel.setSub(subtitle(d));
    };
    return {
      update(d) { last = d; draw_(); },
      redraw: draw_,
      resize() { chart.resize(); },
      dispose() { chart.dispose(); },
    };
  };
}

// ---------- G1 Map (its controls inside the panel) ----------
const MAP_SRC = { ifs: "IFS", aifs: "AIFS (AI)", ens: "Ensemble middle", seasonal: "Seasonal", seasonal_cfs: "Seasonal CFS (US)" };
const MAP_UNIT = { temp: "°C", wind: "km/h", solar: "W/m²", rain: "mm/h" };
const SCALES = {
  temp: ["#313695", "#4575b4", "#74add1", "#abd9e9", "#e0f3f8", "#ffffbf", "#fee090", "#fdae61", "#f46d43", "#d73027", "#a50026"],
  wind: ["#f7fcfd", "#bfd3e6", "#8c96c6", "#8c6bb1", "#88419d", "#4d004b"],
  solar: ["#222244", "#4b3f72", "#9c6b30", "#e0a526", "#ffe066", "#fffbe0"],
  rain: ["#f7fbff", "#c6dbef", "#6baed6", "#2171b5", "#08306b"],
  anom: ["#2166ac", "#67a9cf", "#d1e5f0", "#f7f7f7", "#fddbc7", "#ef8a62", "#b2182b"],
  anomRain: ["#8c510a", "#d8b365", "#f6e8c3", "#f5f5f5", "#c7eae5", "#5ab4ac", "#01665e"],
};
function mapPanel(body, panel) {
  body.innerHTML = `<div class="chart"></div><div class="map-strip"><button class="ctl m-play" title="Play: step through the times by itself">⏵ Play</button>
    <select class="m-speed" title="Play speed"><option value="1500">Slow</option><option value="800" selected>Normal</option><option value="400">Fast</option></select>
    <button class="ctl m-prev" title="Earlier">◀</button>
    <input type="range" class="m-i" min="0" max="0" value="0"><button class="ctl m-next" title="Later">▶</button>
    <span class="m-time"></span><span class="note m-note"></span></div>`;
  const el = body.querySelector(".chart"), $ = (s) => body.querySelector(s);
  const chart = echarts.init(el, dark() ? "dark" : null, { renderer: "canvas" });
  let i = null, d = null, busy = false;
  // W-030: click a city dot = open its chart page at the map's day
  chart.on("click", (p) => {
    if (p.seriesIndex !== 2 || !d || d.error) return;
    const src = panel.opts.src, days = d.date ? (new Date(`${d.date}T00:00`) - new Date(new Date().toDateString())) / 864e5 : 0;
    const page = src.startsWith("seasonal") ? "Seasonal" : src === "ens" || days > 3 ? "Medium" : "Short";
    window.__openRegion?.(page, d.date, p.data.region);
  });
  async function load() {
    if (busy) return;
    busy = true;
    try {
      const o = panel.opts;
      const q = (k) => `/api/map?src=${o.src}&field=${o.field}&i=${k}&run=${o.run || "latest"}&vs=${o.vs || "none"}`;
      d = await fetch(q(i ?? 0)).then((r) => r.json());
      if (!d.error && i === null && !d.anomaly && d.now_i !== d.i) {   // first time: the next forecast time from now
        i = d.now_i;
        d = await fetch(q(i)).then((r) => r.json());
      }
    } finally { busy = false; }
    draw();
  }
  function draw() {
    if (!d) return;
    if (d.error) { chart.clear(); $(".m-note").textContent = d.error; return; }
    const o = panel.opts, a = style(panel);
    i = d.i;
    $(".m-i").max = d.times.length - 1;
    $(".m-i").value = d.i;
    $(".m-time").textContent = d.times[d.i];
    const baseUnit = d.anomaly ? `${SEAS_UNIT[o.field]} vs normal` : MAP_UNIT[o.field];
    const unit = d.diff ? `change, ${baseUnit}` : baseUnit;
    $(".m-note").textContent = d.note || (d.diff ? `Change map: ${d.run_text} minus ${d.vs_text} at the same time.`
      : d.anomaly ? `Monthly difference from normal, average of ${d.src === "seasonal_cfs" ? "120 CFS (US)" : "51 ECMWF"} runs (1° squares).`
      : `${o.src === "ens" ? "Middle of the 50 ensemble runs. " : ""}${o.field === "rain" ? "mm per hour over the step before this time. " : ""}${o.field === "solar" ? "Average over the step before this time. " : ""}`);
    const { lat, lon, values } = d;
    const pts = [];
    let lo = Infinity, hi = -Infinity;
    lat.forEach((la, r) => lon.forEach((ln, c) => {
      const v = values[r * lon.length + c];
      if (v === null) return;
      pts.push([ln, la, v]);
      lo = Math.min(lo, v); hi = Math.max(hi, v);
    }));
    let colours = SCALES[o.field], vmin = lo, vmax = hi;
    if (d.anomaly || d.diff) {
      const m = Math.max(Math.abs(lo), Math.abs(hi)) || 1;
      vmin = -m; vmax = m;
      colours = o.field === "rain" ? SCALES.anomRain : SCALES.anom;
    } else if (o.field === "rain") { vmin = 0; vmax = Math.max(2, Math.ceil(hi)); }
    else if (o.field === "solar") { vmin = 0; vmax = 1100; }
    else if (o.field === "wind") { vmin = 0; }
    // keep squares square: 1° of longitude is ~0.9 of 1° of latitude at these latitudes
    const step = Math.abs(lon[1] - lon[0]);
    const x0 = Math.min(...lon) - step / 2, x1 = Math.max(...lon) + step / 2;
    const y0 = Math.min(...lat) - step / 2, y1 = Math.max(...lat) + step / 2;
    const W = el.clientWidth, H = el.clientHeight, padR = Math.max(70, a.f * 7), pad = 6;
    if (W < 50 || H < 50) return;
    const ratio = ((x1 - x0) * Math.cos((26.5 * Math.PI) / 180)) / (y1 - y0);
    let w = W - padR - pad * 2, h = H - pad * 2;
    if (w / h > ratio) w = h * ratio; else h = w / ratio;
    const left = (W - padR - w) / 2, top = (H - h) / 2;
    const cell = [(w / (x1 - x0)) * step + 1, (h / (y1 - y0)) * step + 1];
    const txt = dark() ? "#e1e5ea" : "#1d2327";
    chart.setOption({
      animation: false, backgroundColor: "transparent",
      grid: { left, top, width: w, height: h },
      xAxis: { type: "value", min: x0, max: x1, show: false }, yAxis: { type: "value", min: y0, max: y1, show: false },
      visualMap: { type: "continuous", min: vmin, max: vmax, dimension: 2, seriesIndex: 0, inRange: { color: colours },
        left: left + w + 12, top: "middle", itemHeight: h * 0.6, calculable: false,
        text: [`${fmt(vmax, d.anomaly || d.diff ? 1 : 0)} ${unit}`, `${fmt(vmin, d.anomaly || d.diff ? 1 : 0)}`],
        textStyle: { color: txt, fontSize: a.f } },
      tooltip: { formatter: (p) => p.seriesIndex === 0
        ? `${fmt(p.value[1], 2)}, ${fmt(p.value[0], 2)}<br><b>${fmt(p.value[2], 1)} ${esc(unit)}</b>` : esc(p.name) },
      series: [
        { type: "scatter", symbol: "rect", symbolSize: cell, data: pts, itemStyle: { opacity: 1 }, z: 1, progressive: 0 },
        { type: "lines", coordinateSystem: "cartesian2d", silent: true, polyline: false, z: 5,
          lineStyle: { color: "#222", width: 1.2, opacity: 0.9 }, data: d.coast.map((s) => ({ coords: s })) },   // map is always colourful: dark line in both themes
        { type: "scatter", symbolSize: 10, z: 6, cursor: "pointer", itemStyle: { color: "#000", borderColor: "#fff", borderWidth: 1.5 },
          label: { show: true, position: "right", color: "#1d2327", fontWeight: 600, fontSize: a.f, textBorderColor: "#fff",
            textBorderWidth: 2, formatter: (p) => p.name },
          data: d.cities.map((c) => ({ name: c.city, value: [c.lon, c.lat], region: c.region })) },
      ],
    }, true);
  }
  // W-023: Play steps through the times by itself (back to the first time at the end); manual moves pause it
  let playing = false, timer = null;
  const setPlay = (on) => {
    playing = on;
    clearTimeout(timer);
    $(".m-play").textContent = on ? "⏸ Pause" : "⏵ Play";
    $(".m-play").classList.toggle("on", on);
    if (on) tick();
  };
  async function tick() {
    if (!playing) return;
    const n = +$(".m-i").max + 1;
    i = ((i ?? 0) + 1) % Math.max(n, 1);
    await load();
    if (playing) timer = setTimeout(tick, +$(".m-speed").value);
  }
  $(".m-play").onclick = () => setPlay(!playing);
  $(".m-i").oninput = (e) => { setPlay(false); i = +e.target.value; load(); };
  $(".m-prev").onclick = () => { setPlay(false); i = Math.max(0, (i ?? 0) - 1); load(); };
  $(".m-next").onclick = () => { setPlay(false); i = Math.min(+$(".m-i").max, (i ?? 0) + 1); load(); };
  panel.onPick = (key) => { if (key === "src" || key === "run") i = panel.opts.src.startsWith("seasonal") ? 0 : null; load(); };
  load();
  return {
    update() { load(); },   // new data after a refresh
    redraw: draw,
    resize() { chart.resize(); draw(); },
    dispose() { playing = false; clearTimeout(timer); chart.dispose(); },
  };
}

// ---------- D1 What changed between two runs ----------
function changesPanel(body, panel) {
  body.innerHTML = '<div class="changes"></div>';
  const box = body.firstChild;
  return {
    update(d) {
      if (!d) { box.innerHTML = '<div class="empty">Loading…</div>'; return; }
      if (d.error) { box.innerHTML = `<div class="err">${esc(d.error)}</div>`; return; }
      panel.setSub(d.vs ? `${d.label}: ${d.run_text} vs ${d.vs_text}` : d.label);
      if (d.note) { box.innerHTML = `<div class="empty">${esc(d.note)}</div>`; return; }
      if (!d.rows.length) { box.innerHTML = `<div class="empty">No big changes since the ${esc(d.vs_text)} run.</div>`; return; }
      box.innerHTML = `<table class="grid"><tr><th class="l">Region</th><th class="l">Day</th><th class="l">What changed (old → new)</th></tr>
        ${d.rows.map((x) => `<tr><td class="l"><span class="dot" style="background:${REGION_COLOURS[x.region]}"></span>${esc(x.region)}</td>
        <td class="l">${esc(x.day)}</td><td class="l">${x.items.map((it) => `<span class="${it.big ? "chg-big" : ""}">${esc(it.what)}
        ${fmt(it.old, it.unit === "%" ? 0 : 1)} → ${fmt(it.new, it.unit === "%" ? 0 : 1)}${it.unit === "%" ? "%" : ` ${esc(it.unit)}`}
        (${it.change > 0 ? "+" : ""}${fmt(it.change, it.unit === "%" ? 0 : 1)})</span>`).join(" · ")}</td></tr>`).join("")}</table>
        <p class="note">Notable = high / low ±2 °C · rain ±5 mm · rain chance ±30 points · wind ±10 km/h · sun ±1.5 kWh/m². Bold = twice that.</p>`;
    },
    resize() {},
  };
}

// ---------- I1 Insights: what the latest run says + what changed (rules, card I1) ----------
const IKIND = { heat: "ins-heat", cold: "ins-cold", wind: "ins-wind", solar: "ins-solar", rain: "ins-rain", change: "ins-change", info: "ins-info" };
function insightsPanel(body, panel) {
  body.innerHTML = '<div class="insights"></div>';
  const box = body.firstChild;
  // W-025: price tag = the direction this weather usually pushes prices, with the reason (card I1)
  const tag = (b) => b.price ? ` <span class="ptag ${b.price}" title="What this weather usually does to power prices – a direction, not a forecast">→ ${esc(b.why)} · price ${b.price === "up" ? "▲" : "▼"}</span>` : "";
  const li = (b) => `<li class="${IKIND[b.kind] || ""}">${esc(b.text)}${tag(b)}</li>`;
  return {
    update(d) {
      if (!d) { box.innerHTML = '<div class="empty">Loading…</div>'; return; }
      if (d.error) { box.innerHTML = `<div class="err">${esc(d.error)}</div>`; return; }
      panel.setSub(d.vs_text ? `${d.run_text} vs ${d.vs_text}` : d.run_text);
      const regions = Object.entries(d.regions).map(([r, items]) => `<div class="ins-region">
        <h5><span class="dot" style="background:${REGION_COLOURS[r]}"></span>${esc(r)}</h5>
        <ul>${items.length ? items.map(li).join("") : '<li class="ins-info">Nothing stands out</li>'}</ul></div>`).join("");
      box.innerHTML = `<h4>Headlines</h4><ul class="ins-head">${d.headlines.length ? d.headlines.map(li).join("") : '<li class="ins-info">Nothing stands out</li>'}</ul>
        <h4>By region</h4><div class="ins-grid">${regions}</div>
        <h4>${d.vs_text ? `Changed since ${esc(d.vs_text)}` : "Changed"}</h4>
        ${d.note ? `<p class="note">${esc(d.note)}</p>` : `<ul>${d.changes.length ? d.changes.map(li).join("") : '<li class="ins-info">No big changes</li>'}</ul>`}`;
    },
    resize() {},
  };
}

// ---------- W1 Week ahead (W-026, card W1): states × days, colour + tags + price arrow; click = that page ----------
const ARROW = { up: "▲", down: "▼", both: "▲▼" };
function weekPanel(body, panel) {
  body.innerHTML = '<div class="week"></div>';
  const box = body.firstChild;
  let last = null;
  const tip = (c, day, city) => [`${city} · ${day.label} (${c.src === "IFS" ? "IFS main model" : "ensemble middle"})`,
    `High ${fmt(c.high, 1)} °C · low ${fmt(c.low, 1)} °C`, `Wind ${fmt(c.wind)} km/h at 100 m · sun ${fmt(c.solar, 1)} kWh/m²`,
    `Rain ${fmt(c.rain, 1)} mm${c.chance !== null && c.chance !== undefined ? ` · chance ${fmt(c.chance)} %` : ""}`,
    ...(c.areas?.wind ? [`Wind areas: ${Object.entries(c.areas.wind).map(([a, v]) => `${a} ${fmt(v)}`).join(" · ")}`] : []),
    ...(c.areas?.solar ? [`Sun areas: ${Object.entries(c.areas.solar).map(([a, v]) => `${a} ${fmt(v, 1)}`).join(" · ")}`] : []),
    ...c.up.map((w) => `▲ price: ${w}`), ...c.down.map((w) => `▼ price: ${w}`), "Click: open the chart"].join("\n");
  return {
    redraw() { this.update(last); },
    update(d) {
      last = d;
      if (!d) { box.innerHTML = '<div class="empty">Loading…</div>'; return; }
      if (d.error) { box.innerHTML = `<div class="err">${esc(d.error)}</div>`; return; }
      panel.setSub(d.run_text);
      const on = (x) => (x.date === DAY.date ? " dayon" : "");
      const head = d.days.map((x) => `<th class="${x.src === "Ens" ? "ens" : ""}${on(x)}">${esc(x.label)}${x.src === "Ens" ? '<small>Ens</small>' : ""}</th>`).join("");
      const rows = Object.entries(d.regions).map(([r, reg]) => `<tr><th class="reg"><span class="dot" style="background:${REGION_COLOURS[r]}"></span>${esc(r)}<small>${esc(reg.city || "")}</small></th>
        ${d.days.map((x) => { const c = reg.cells[x.date];
          if (!c) return '<td class="none">–</td>';
          return `<td class="cell ${c.level} ${c.src === "Ens" ? "ens" : ""}${on(x)}" data-r="${r}" data-src="${c.src}" data-date="${x.date}" title="${esc(tip(c, x, reg.city))}">
            ${c.price ? `<span class="arr ${c.price}">${ARROW[c.price]}</span>` : ""}
            <b>${fmt(c.high)}°</b><span class="lo">${fmt(c.low)}°</span>
            <span class="tags">${c.tags.map((t) => `<i class="t-${t.toLowerCase()}">${esc(t)}</i>`).join("")}</span></td>`; }).join("")}</tr>`).join("");
      box.innerHTML = `<table><tr><th></th>${head}</tr>${rows}</table>`;
      box.querySelectorAll("td.cell").forEach((td) => {
        td.onclick = () => { setDay(td.dataset.date, false); window.__showPage?.(td.dataset.src === "IFS" ? "Short" : "Medium"); };
      });
    },
    resize() {},
  };
}

// ---------- F1 Forecast check (W-014, card F1): forecasts vs what BOM measured ----------
const CHECK_COL = { IFS: C_IFS, AIFS: C_AI, Ensemble: C_ENS, BOM: "#d32f2f" };
function checkPanel(body, panel) {
  body.innerHTML = '<div class="chart"></div><div class="table"></div>';
  const chEl = body.querySelector(".chart"), tb = body.querySelector(".table");
  const chart = echarts.init(chEl, dark() ? "dark" : null, { renderer: "canvas" });
  new ResizeObserver(() => chart.resize()).observe(chEl);
  let last = null;
  const cell = (v, m) => {
    if (m === "high" || m === "low") {
      const x = v[m];
      if (!x.n) return { html: "–", score: null, n: 0 };
      const lean = Math.abs(x.lean) < 0.25 ? "even" : `${fmt(Math.abs(x.lean), 1)} ${x.lean > 0 ? "warm" : "cool"}`;
      return { html: `${fmt(x.miss, 1)}° <span class="rng">${lean}</span>`, score: -x.miss, n: x.n };
    }
    const x = m === "rain" ? v.rain : v.sun, val = m === "rain" ? x.right : x.match;
    return val === null || val === undefined ? { html: "–", score: null, n: x.n } : { html: `${fmt(val)} %`, score: val, n: x.n };
  };
  const draw = () => {
    const d = last;
    if (!d) { chart.clear(); tb.innerHTML = '<div class="empty">Loading…</div>'; return; }
    if (d.error) { chart.clear(); tb.innerHTML = `<div class="err">${esc(d.error)}</div>`; return; }
    const r = d.regions?.[panel.opts.region], m = panel.opts.measure || "high";
    if (!r) return;
    panel.setSub(`${r.days} day${r.days === 1 ? "" : "s"} checked · last ${d.period} days`);
    const a = style(panel), c = r.chart;
    if (m === "sun" && !r.sun_measured) {
      chart.clear();
      tb.innerHTML = `<div class="empty">Sunshine is not measured at the ${esc(r.city)} station – only Sydney and Brisbane record it.</div>`;
      return;
    }
    const what = { high: "Average miss of the high (°C) and its lean (warm / cool)", low: "Average miss of the low (°C) and its lean (warm / cool)",
      rain: "Rain or dry called right (1 mm or more)", sun: "How well sunny and dull days matched (70 %+ = good)" }[m];
    const head = { high: "High: miss · lean", low: "Low: miss · lean", rain: "Rain: % right", sun: "Sun: % match" }[m];
    const cells = Object.fromEntries(d.models.map((mod) => [mod, Object.fromEntries(d.leads.map((l) => [l, cell(r.table[mod][String(l)], m)]))]));
    const best = Object.fromEntries(d.leads.map((l) => {
      const s = d.models.map((mod) => cells[mod][l].score).filter((x) => x !== null);
      return [l, s.length > 1 ? Math.max(...s) : null];
    }));
    tb.innerHTML = `<table class="grid check"><tr><th class="l" title="${esc(what)}">${esc(head)}</th>${d.leads.map((l) => `<th>Day ${l}</th>`).join("")}</tr>
      ${d.models.map((mod) => `<tr><td class="l"><span class="dot" style="background:${CHECK_COL[mod]}"></span>${esc(mod)}</td>
        ${d.leads.map((l) => { const x = cells[mod][l];
          return `<td class="${x.score !== null && x.score === best[l] ? "best" : ""}" title="${x.n} day${x.n === 1 ? "" : "s"} checked">${x.html}</td>`; }).join("")}</tr>`).join("")}</table>`;
    const unit = { high: "°C", low: "°C", rain: "mm", sun: "sun hours" }[m];
    const series = [];
    let shown = d.models;
    if (m === "rain") {
      series.push({ name: "Measured", type: "bar", color: "#78909c", data: c.obs.rain });
      d.models.forEach((mod, k) => series.push({ name: mod, type: "scatter", yAxisIndex: 1, color: CHECK_COL[mod], symbolSize: a.f * 0.7,
        symbolOffset: [(k - 1.5) * a.f * 0.75, 0],   // side by side when several models said the same
        data: c.models[mod].rain.map((v) => (v === null ? null : v ? "said rain" : "said dry")) }));
    } else if (m === "sun") {
      shown = d.models.filter((x) => x !== "BOM");
      series.push({ name: "Measured", type: "bar", color: "#78909c", data: c.obs.sun });
      for (const mod of shown) series.push({ name: mod, type: "line", yAxisIndex: 1, color: CHECK_COL[mod], symbolSize: 5, data: c.models[mod].sun });
    } else {
      series.push({ name: "Measured", type: "line", color: dark() ? "#eceff1" : "#000", lineStyle: { width: 2.5 }, symbolSize: 6, data: c.obs[m] });
      for (const mod of d.models) series.push({ name: mod, type: "line", color: CHECK_COL[mod], symbolSize: 5, data: c.models[mod][m] });
    }
    const yR = m === "rain" ? { type: "category", data: ["said dry", "said rain"], axisLabel: a.label }
      : m === "sun" ? valueAxis(a, "kWh/m²", { min: 0, scale: false }) : null;
    chart.setOption({ ...base(a), legend: { ...a.legend, data: ["Measured", ...shown] },
      xAxis: { type: "category", data: c.labels, axisLabel: { ...a.label, hideOverlap: true } },
      yAxis: [valueAxis(a, unit, m === "rain" || m === "sun" ? { min: 0, scale: false } : {}), ...(yR ? [yR] : [])],
      tooltip: { trigger: "axis" }, series }, true);
    chart.resize();
  };
  return { update(d) { last = d; draw(); }, redraw: draw, resize() { chart.resize(); }, dispose() { chart.dispose(); } };
}

// ---------- A1 About: runs on screen + download progress ----------
export function progressText(p) {
  if (!p) return "";
  if (p.active && !p.stalled && !p.total) return `Refreshing: ${p.label}…`;
  if (p.active && !p.stalled) {
    const pct = p.total ? Math.round((100 * p.done) / p.total) : 0;
    return `Downloading ${p.label}${p.part ? ` (part ${p.part})` : ""}: ${p.done} of ${p.total} steps · ${pct}%`
      + (p.bytes ? ` · ${fmt(p.bytes / 1e9, 1)} GB` : "");
  }
  if (p.active && p.stalled) return `Refresh stopped at ${p.label} ${p.done} of ${p.total} – the next refresh carries on`;
  if (p.error) return `Last refresh stopped: ${p.error}`;
  return "";
}
const nem = (iso) => iso ? new Date(new Date(iso).getTime() + 10 * 3600e3).toISOString().slice(5, 16).replace("T", " ") : "–";
function cloudLines(c) {
  if (!c || !c.last_check) return '<h4>Cloud</h4><p class="note">Not checked yet – first check shortly after start, then every 15 minutes.</p>';
  const job = c.last_job;
  return `<h4>Cloud (GitHub, every 15 min)</h4><table>
    <tr><td>Cloud last made data</td><td>${nem(c.cloud_updated)} NEM${job?.errors?.length ? ` <span class="old" title="${esc(job.errors.join("; "))}">(with problems)</span>` : ""}</td></tr>
    <tr><td>This PC last checked</td><td>${nem(c.last_check)} · next ${nem(c.next_check)}</td></tr>
    ${c.error ? `<tr><td colspan="2" class="old">${esc(c.error)}</td></tr>` : ""}</table>`;
}
function aboutPanel(body) {
  body.innerHTML = '<div class="about"></div>';
  const box = body.firstChild;
  return {
    update(_, st) {
      if (!st) return;
      const rows = st.feeds.map((f) => `<tr><td>${esc(f.label)}</td><td>${f.run ? esc(f.run_text) : "no data"}</td>
        <td class="${f.age_h > 30 && !f.feed.startsWith("seasonal") ? "old" : ""}">${f.run && !f.feed.startsWith("seasonal") ? `${fmt(f.age_h)} h old` : ""}</td></tr>`);
      const p = progressText(st.progress);
      box.innerHTML = `${p ? `<div class="progress-box">${esc(p)}${st.progress?.active && !st.progress.stalled && st.progress.total
        ? `<div class="bar"><div style="width:${(100 * st.progress.done) / st.progress.total}%"></div></div>` : ""}</div>` : ""}
        <h4>Colours on the charts</h4><ul>
        <li><b style="color:${C_IFS}">Blue</b> = ECMWF main model (IFS) – the best guess.</li>
        <li><b style="color:${C_AI}">Purple</b> = ECMWF AI model (AIFS).</li>
        <li><b style="color:${C_ENS}">Grey band / whiskers</b> = 8 in 10 of the 50 ensemble runs fall inside; grey line = middle run.</li>
        <li><b style="color:#d32f2f">▲</b> <b style="color:#1976d2">▼</b> = BOM's forecast high / low.</li>
        <li>Seasonal: solid bars ECMWF, light bars BOM, outline bars CFS (US). Times are NEM time (AEST).</li>
        <li>Each panel's <b>ⓘ</b> explains it in full.</li></ul>
        <h4>Forecast runs on screen</h4><table>${rows.join("")}</table>
        ${farmLine(st.feeds)}
        ${cloudLines(st.cloud)}
        <p class="note">New data arrives from the cloud by itself (Refresh = check now). Data: ECMWF (CC BY 4.0), BOM, Copernicus (NOAA CFS).</p>`;
    },
    resize() {},
  };
}

// W-027: where wind / solar on screen come from (farm areas from the 23 Oct evening run; older runs: the city)
function farmLine(feeds) {
  const f = (feeds || []).filter((x) => x.run && "farms" in x);
  if (!f.length) return "";
  const name = { ifs: "IFS", aifs: "AIFS", ens: "ensemble" };
  const city = f.filter((x) => !x.farms).map((x) => name[x.feed]);
  if (!city.length) return '<p class="note">Wind and solar: <b>farm areas</b> (state average, see MODELS).</p>';
  if (city.length === f.length) return '<p class="note">Wind and solar: <b>city squares</b> – these runs came before the farm-area switch; the next runs use the farm areas.</p>';
  return `<p class="note">Wind and solar: <b>farm areas</b>, except ${esc(city.join(", "))} (older run: city square).</p>`;
}

// ---------- the panel list ("+ Add panel") ----------
const regionSub = (what) => (d) => d?.run_text ? `${what}` : "";
const runQ = (o) => ({ run: o.run || "latest", vs: o.vs || "auto" });
export const PANELS = {
  short: { code: "S1", title: "Next 3 days", source: "short", pickers: ["region"], pageField: true, runFeed: () => "ifs", query: runQ,
    create: regionPanel(shortChart, shortTable, regionSub("IFS run")) },
  medium: { code: "M1", title: "Next 15 days – range", source: "medium", pickers: ["region"], pageField: true, runFeed: () => "ens", query: runQ,
    create: regionPanel(mediumChart, mediumTable, regionSub("Ensemble run")) },
  compare: { code: "C1", title: "AI model vs main model", source: "compare", pickers: ["region"], pageField: true,
    create: regionPanel(compareChart, compareTable, (d) => d?.runs ? `IFS ${d.runs.ifs} · AIFS ${d.runs.aifs}` : "") },
  seasonal: { code: "L1", title: "6 months vs normal", source: "seasonal", pickers: ["region"], pageField: true, runFeed: () => "seasonal",
    query: runQ, create: regionPanel(seasonalChart, seasonalTable, () => "Forecast") },
  map: { code: "G1", title: "East-coast map", source: null, pickers: ["src", "field"], create: mapPanel, map: true,
    runFeed: (o) => o.src, vsDefault: "none" },
  insights: { code: "I1", title: "Insights", source: "insights", pickers: ["ipage"],
    query: (o) => ({ page: o.ipage || "short" }), create: insightsPanel },
  changes: { code: "D1", title: "What changed", source: "changes", pickers: ["model"], runFeed: (o) => o.model,
    query: (o) => ({ model: o.model || "ens", ...runQ(o) }), create: changesPanel },
  check: { code: "F1", title: "Forecast check", source: "check", pickers: ["region", "measure", "period"],
    query: (o) => ({ period: o.period || "30" }), create: checkPanel },
  week: { code: "W1", title: "Week ahead", source: "week", pickers: [], create: weekPanel },
  about: { code: "A1", title: "About · runs · download", source: null, pickers: [], create: aboutPanel, status: true },
};
export const MAP_SOURCES = MAP_SRC;
