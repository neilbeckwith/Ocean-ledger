# Ocean Ledger — ocean CO₂ uptake by basin

A static web app: annual ocean CO₂ uptake, 1959–2024, by basin — explained
by the four ocean carbon pumps and observed through the GOOS Essential
Ocean Variables.

## What it shows

- **The active ledger (live counter)** — tonnes of CO₂ taken up since the
  page opened, and a live running cumulative total since 1959. This spreads
  the latest annual ocean rate (2024: 3.39 GtC/yr) evenly across the year;
  it is an estimate, not a measurement.
- **Historic trend** — world annual ocean uptake 1959–2024, from 1.12 GtC/yr
  to 3.39 GtC/yr, with decadal means (1960s 1.27 → 2010s 3.07 GtC/yr).
- **The four pumps** — the science behind the numbers: solubility (SCP),
  biological (BCP), microbial (MCP) and the carbonate counter-pump (CCP),
  plus their synergistic coupling (BCMS). Warming pushes back on the
  solubility pump (pCO₂ +4.23%/°C; 2023 record SST cut uptake ~10%).
- **Every basin** — eight basins from Fay et al. 2024: uptake, share, area,
  flux per area and dominant pumps. Southern Ocean 0.88 PgC/yr (46.8%),
  North Atlantic 0.55 (29.3%), North Pacific 0.53 (28.2%); the equatorial
  Pacific is a net source (−0.35 PgC/yr). Click a row for the basin's
  biomes, drivers, pumps and observing variables.
- **Compare basins** — three pickers, side by side.
- **Accumulated carbon** — 146.0 GtC taken up 1959–2024 (535 GtCO₂), 27.2%
  of the 537 GtC humans emitted over the same period.
- **GOOS Essential Ocean Variables** — all 36 EOVs by category, with pilot
  flags and ECV overlap (verified against the GCOS ECV list and the paper's
  §3.2.1), plus the variables that constrain the uptake.
- **CSV downloads** — basin table and global series.

## Data

- Global annual ocean sink (SOCEAN), 1959–2024: Global Carbon Budget 2025
  (Friedlingstein et al. 2025, ESSD 18, 3211–3302), via the ICOS Carbon
  Portal spreadsheet. 2024: 3.39 GtC/yr (12.42 GtCO₂/yr), +3.5% vs 2023,
  28.8% of 2024 total human emissions (11.79 GtC). Uncertainty ±0.4 GtC/yr.
- Basin breakdown: Fay et al. 2024 (ESSD 16, 2123–2139), Table 1 —
  climatological mean net air–sea CO₂ flux by open-ocean biome (SOCATv2022,
  1980–2021), aggregated to eight basins. These are *net* fluxes (they
  include natural river-carbon outgassing, ~0.65 GtC/yr), not the
  anthropogenic sink, and a multi-decade mean, not an annual series. The
  printed biome values sum to 1.88 PgC/yr against the paper's global
  1.79 ± 0.7 PgC/yr — rounding in the printed table, inside the uncertainty.
- 2025 preliminary: 3.11 ± 0.36 GtC/yr (Ciais et al. 2026, low-latency
  budget) — quoted in the text, not in the series.
- Variables: Martín Míguez, Heslop et al. 2026, Frontiers in Marine
  Science 13:1737002 (CC BY 4.0). Pumps: Global ONCE Science Plan (Chief
  Scientist Nianzhi Jiao).

`data.json` is built by `scripts/fetch_data.py` from the Global Carbon
Budget 2025 spreadsheet (downloaded from ICOS) and Fay et al. 2024
Table 1 (transcribed). Re-run it to refresh the data when a new Global
Carbon Budget is published. Sources are credited in the captions on the
page and in the Methods section.

## Run locally

```bash
cd ocean-ledge
python3 -m http.server 8000
# open http://127.0.0.1:8000/
```

No build step, no dependencies. `index.html` + `styles.css` + `app.js` + `data.json`.

## Deploy

- **GitHub Pages:** publish this folder as-is to a new public repo
  (`ocean-ledge`) with Pages enabled. A workflow like the carbon-ledge
  one (`.github/workflows/deploy-pages.yml`) can publish it on push.
- **Any static host** (Vercel, Netlify, etc.): publish this folder as-is.

This repo is not created yet — build locally, present to Neil, push only
after he approves that specific push.
