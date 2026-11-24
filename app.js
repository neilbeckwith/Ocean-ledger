/* Ocean Ledger — annual ocean CO2 uptake by basin.
   Data: data.json, built by scripts/fetch_data.py from the Global Carbon
   Budget 2025 (GCB) and Fay et al. 2024 Table 1.
   Units: GtC/yr for the global series (1 GtC = 1 PgC = 3.664 GtCO2);
   basin fluxes in PgC/yr. Uptake is POSITIVE on this page.
   Live counter: spreads the latest annual ocean rate evenly across the
   year. It is an estimate, not a measurement. */
let DATA = null;
let selectedBasin = null;

const $ = (id) => document.getElementById(id);
const fmt = (n, d = 0) => n == null || isNaN(n) ? "—" : Number(n).toLocaleString("en-CA", { maximumFractionDigits: d, minimumFractionDigits: d });
const pct = (n) => n == null || isNaN(n) ? "—" : (n > 0 ? "+" : "") + n.toFixed(1) + "%";

function basinList() {
  return Object.entries(DATA.basins).map(([name, b]) => ({ name, ...b }));
}

function drawChart() {
  const svg = $("worldChart");
  const W = 900, H = 320, PL = 56, PR = 16, PT = 18, PB = 34;
  const world = DATA.world;
  const maxV = Math.max(...world.map((w) => w.socean_gtc));
  const minY = world[0].year, maxY = world[world.length - 1].year;
  const x = (y) => PL + (y - minY) / (maxY - minY) * (W - PL - PR);
  const y = (v) => PT + (1 - v / (maxV * 1.05)) * (H - PT - PB);
  let s = "";
  for (let g = 0; g <= 4; g++) {
    const v = maxV * g / 4, yy = y(v);
    s += `<line x1="${PL}" y1="${yy}" x2="${W - PR}" y2="${yy}" stroke="#e3eae6"/><text x="${PL - 8}" y="${yy + 4}" text-anchor="end" font-size="11" fill="#5a6b64">${fmt(v, 1)}</text>`;
  }
  for (const yr of [1960, 1975, 1990, 2005, 2024]) {
    s += `<text x="${x(yr)}" y="${H - 10}" text-anchor="middle" font-size="11" fill="#5a6b64">${yr}</text>`;
  }
  s += `<text x="${PL}" y="${PT - 4}" font-size="11" fill="#5a6b64">GtC per year</text>`;
  s += `<path d="${world.map((w, i) => (i ? "L" : "M") + x(w.year).toFixed(1) + "," + y(w.socean_gtc).toFixed(1)).join(" ")}" fill="none" stroke="#0b5a6b" stroke-width="2.5"/>`;
  svg.innerHTML = s;
  const v = (yr) => (world.find((w) => w.year === yr) || {}).socean_gtc;
  const dec = DATA.summary.decadal_means_gtc;
  $("worldStats").innerHTML =
    `<span>1960: ${fmt(v(1960), 2)} GtC</span><span>1980: ${fmt(v(1980), 2)} GtC</span>` +
    `<span>2000: ${fmt(v(2000), 2)} GtC</span><span>2010: ${fmt(v(2010), 2)} GtC</span>` +
    `<span>2024: ${fmt(v(2024), 2)} GtC (${pct(DATA.summary.yoy_pct)} vs 2023)</span>` +
    `<span>1960s mean: ${fmt(dec["1960"], 2)}</span><span>2010s mean: ${fmt(dec["2010"], 2)}</span>` +
    `<span>2015–2024 mean: ${fmt(DATA.summary.mean_2015_2024_gtc, 2)} GtC</span>`;
}

function renderPumps() {
  $("pumpGrid").innerHTML = DATA.pumps.map((p) => {
    const wide = p.abbr === "BCMS" ? " wide" : "";
    return `<div class="pump${wide}"><div class="abbr">${p.abbr}</div><h3>${p.name}</h3><p>${p.role}</p><p class="caption">Source: ${p.source}</p></div>`;
  }).join("");
}

function renderTable() {
  const sort = $("sort").value;
  let rows = basinList();
  if (sort === "name") rows.sort((a, b) => a.name.localeCompare(b.name));
  else if (sort === "density") rows.sort((a, b) => b.flux_density_gC_m2_yr - a.flux_density_gC_m2_yr);
  else if (sort === "area") rows.sort((a, b) => b.area_mkm2 - a.area_mkm2);
  else rows.sort((a, b) => b.uptake_pgC - a.uptake_pgC);
  $("tbody").innerHTML = rows.map((r) => {
    const cls = r.uptake_pgC >= 0 ? "pos" : "neg";
    const pumps = (DATA.basin_detail[r.name] || {}).pumps || [];
    return `<tr data-basin="${r.name}"><td>${r.name}</td>` +
      `<td class="${cls}">${r.uptake_pgC.toFixed(2)}</td>` +
      `<td>${r.share_of_printed_total_pct.toFixed(1)}%</td>` +
      `<td>${fmt(r.area_mkm2, 1)}</td>` +
      `<td class="${cls}">${r.flux_density_gC_m2_yr.toFixed(1)}</td>` +
      `<td>${pumps.join(" + ")}</td></tr>`;
  }).join("");
  document.querySelectorAll("#tbody tr").forEach((tr) =>
    tr.addEventListener("click", () => selectBasin(tr.dataset.basin)));
}

function pumpLong(abbr) {
  const p = DATA.pumps.find((x) => x.abbr === abbr);
  return p ? `${p.abbr} — ${p.name}` : abbr;
}

function selectBasin(name) {
  selectedBasin = name;
  const b = DATA.basins[name];
  const d = DATA.basin_detail[name] || {};
  if (!b) return;
  const biomeRows = b.biomes.map((x) => {
    const cls = x.uptake_pgC >= 0 ? "pos" : "neg";
    return `<tr><td>${x.biome}</td><td class="${cls}">${x.uptake_pgC.toFixed(2)}</td><td>${fmt(x.area_mkm2, 1)}</td><td>${x.d_fco2_uatm.toFixed(1)}</td></tr>`;
  }).join("");
  const eovTags = (d.eovs || []).map((e) => `<span class="eov-tag">${e}</span>`).join("");
  const pumps = (d.pumps || []).map(pumpLong).join("; ");
  $("detail").innerHTML =
    `<h3>${name}</h3>` +
    `<p>Climatological mean net uptake <strong>${b.uptake_pgC.toFixed(2)} PgC/yr</strong> ` +
    `(${b.share_of_printed_total_pct.toFixed(1)}% of the eight printed basins), over ` +
    `${fmt(b.area_mkm2, 1)} million km² — <strong>${b.flux_density_gC_m2_yr.toFixed(1)} g C/m²/yr</strong>.</p>` +
    `<h3>Why it takes up what it does</h3><p>${d.drivers || ""}</p>` +
    `<p class="caption">Drivers source: ${d.driver_source || ""}</p>` +
    `<h3>Pumps behind it</h3><p>${pumps}</p>` +
    `<p class="caption">Pump framing: Global ONCE Science Plan. No published source splits a basin's uptake into pump shares; the attribution above is qualitative.</p>` +
    `<h3>GOOS variables that watch this basin</h3><p>${eovTags}</p>` +
    `<p class="caption">EOV names and categories: Martín Míguez, Heslop et al. 2026.</p>` +
    `<h3>Biomes inside this basin (Fay et al. 2024, Table 1)</h3>` +
    `<div class="table-wrap"><table><thead><tr><th>Biome</th><th>Uptake (PgC/yr)</th><th>Area (M km²)</th><th>Mean ΔfCO₂ (µatm)</th></tr></thead><tbody>${biomeRows}</tbody></table></div>` +
    `<p class="caption">ΔfCO₂ is the surface-ocean minus atmosphere CO₂ fugacity: negative means the ocean is undersaturated and takes CO₂ up; positive means it outgasses. Fluxes are net air–sea fluxes as printed by Fay et al., sign flipped so uptake is positive.</p>`;
  $("detail").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function renderCompare() {
  const names = basinList().map((b) => b.name);
  for (const id of ["cmp1", "cmp2", "cmp3"]) {
    const sel = $(id);
    sel.innerHTML = `<option value="">—</option>` + names.map((n) => `<option value="${n}">${n}</option>`).join("");
  }
  $("cmp1").value = "Southern Ocean";
  $("cmp2").value = "North Atlantic";
  $("cmp3").value = "Equatorial Pacific";
  const draw = () => {
    const picks = ["cmp1", "cmp2", "cmp3"].map((id) => $(id).value).filter(Boolean);
    $("compareGrid").innerHTML = picks.map((name) => {
      const b = DATA.basins[name];
      const d = DATA.basin_detail[name] || {};
      return `<div class="compare-card"><h3>${name}</h3>` +
        `<div class="kv"><span>Uptake</span><span>${b.uptake_pgC.toFixed(2)} PgC/yr</span></div>` +
        `<div class="kv"><span>Share</span><span>${b.share_of_printed_total_pct.toFixed(1)}%</span></div>` +
        `<div class="kv"><span>Area</span><span>${fmt(b.area_mkm2, 1)} M km²</span></div>` +
        `<div class="kv"><span>Flux per area</span><span>${b.flux_density_gC_m2_yr.toFixed(1)} g C/m²/yr</span></div>` +
        `<div class="kv"><span>Dominant pumps</span><span>${(d.pumps || []).join(" + ")}</span></div>` +
        `<p class="sub" style="margin-top:10px">${d.drivers || ""}</p>` +
        `<p class="caption">Drivers: ${d.driver_source || ""}</p></div>`;
    }).join("");
  };
  for (const id of ["cmp1", "cmp2", "cmp3"]) $(id).addEventListener("change", draw);
  draw();
}

function renderEOV() {
  const order = ["Physical", "Biogeochemical", "Biology & Ecosystems", "Cross-disciplinary"];
  const rows = [];
  for (const cat of order) {
    DATA.eovs.filter((e) => e.category === cat).forEach((e) => {
      rows.push(`<tr><td>${e.name}</td><td>${e.category}</td><td>${e.pilot ? "Pilot" : "—"}</td><td>${e.ecv}</td></tr>`);
    });
  }
  $("eovBody").innerHTML = rows.join("");
}

function downloadCSV(filename, text) {
  const blob = new Blob([text], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

function startCounter() {
  // 2024 ocean rate, spread evenly. 2024 is a leap year (366 days);
  // the counter applies the annual rate over the current year (2026, 365 days).
  const annualTonnesCO2 = DATA.summary.latest_socean_gtco2 * 1e9; // t CO2/yr
  const ratePerSec = annualTonnesCO2 / (365 * 24 * 3600); // ≈ 394 t/s
  const cumulativeEnd2024GtC = DATA.summary.cumulative_1959_latest_gtc;
  const prelim2025GtC = DATA.summary.preliminary_2025_gtc;
  const start2026 = Date.UTC(2026, 0, 1);
  const openedAt = Date.now();
  $("rateLine").textContent = `${fmt(ratePerSec, 0)} tonnes of CO₂ per second (2024 ocean rate, spread evenly)`;
  function tick() {
    const now = Date.now();
    const sinceOpenedT = ratePerSec * (now - openedAt) / 1000;
    $("sinceOpened").textContent = `${fmt(sinceOpenedT, 1)} t`;
    const elapsed2026Sec = Math.max(0, (now - start2026) / 1000);
    const cumGtC2 = cumulativeEnd2024GtC + prelim2025GtC + (ratePerSec / 3.664) * elapsed2026Sec / 1e9;
    $("cumulativeLive").textContent = `${fmt(cumGtC2, 2)} GtC`;
    $("cumulativeSub").textContent = `146.0 GtC at end-2024 + 3.11 GtC preliminary 2025 + ${fmt((ratePerSec / 3.664) * elapsed2026Sec / 1e9, 2)} GtC estimated in 2026 to date`;
  }
  tick();
  setInterval(tick, 250);
}

async function init() {
  const res = await fetch("data.json");
  DATA = await res.json();
  $("latestYear").textContent = DATA.meta.latest_year;
  const s = DATA.summary;
  $("world2024").textContent = `${fmt(s.latest_socean_gtc, 2)} GtC`;
  $("worldYoY").textContent = `${pct(s.yoy_pct)} vs ${s.latest_year - 1} · ${fmt(s.latest_socean_gtco2, 2)} GtCO₂`;
  drawChart();
  renderPumps();
  renderTable();
  renderCompare();
  renderEOV();
  startCounter();
  $("sort").addEventListener("change", renderTable);
  $("pickSouthern").addEventListener("click", () => selectBasin("Southern Ocean"));
  $("csvBasins").addEventListener("click", () => {
    const head = "Basin,Uptake (PgC/yr),Share (%),Area (M km2),Flux per area (g C/m2/yr),Dominant pumps\n";
    const body = basinList().map((b) => {
      const pumps = (DATA.basin_detail[b.name] || {}).pumps || [];
      return `"${b.name}",${b.uptake_pgC},${b.share_of_printed_total_pct},${b.area_mkm2},${b.flux_density_gC_m2_yr},"${pumps.join(" + ")}"`;
    }).join("\n");
    downloadCSV("ocean-ledge-basins.csv", head + body + "\n");
  });
  $("csvGlobal").addEventListener("click", () => {
    const head = "Year,Ocean sink (GtC/yr),Ocean sink (GtCO2/yr),Fossil emissions (GtC/yr),Land-use change (GtC/yr),Atmospheric growth (GtC/yr),Land sink (GtC/yr)\n";
    const body = DATA.world.map((w) => `${w.year},${w.socean_gtc},${w.socean_gtco2},${w.efos_gtc},${w.eluc_gtc},${w.gatm_gtc},${w.sland_gtc}`).join("\n");
    downloadCSV("ocean-ledge-global-series.csv", head + body + "\n");
  });
}
init().catch((e) => { document.querySelector("main").insertAdjacentHTML("afterbegin", `<p class="note">Could not load data.json — ${e.message}. Serve this folder over HTTP (not file://) or check the data file.</p>`); });
