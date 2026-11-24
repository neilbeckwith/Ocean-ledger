#!/usr/bin/env python3
"""Fetch ocean CO2 uptake data for Ocean Ledger and build data.json.

Sources (all public, all cited on the page):
  1. Global Carbon Budget 2025 spreadsheet (Friedlingstein et al. 2025,
     Earth Syst. Sci. Data 18, 3211, doi:10.18160/GCP-2025), via the ICOS
     Carbon Portal. The file sits behind a licence click: the first GET to
     the licence_accept URL sets a cookie, the second GET with that cookie
     returns the .xlsx. Sheets used: "Ocean Sink" (GCB adjusted annual
     ocean sink, GtC/yr, 1959-2024) and "Historical Budget" (fossil,
     land-use, atmospheric growth, ocean and land sinks, 1750-2024).
  2. Fay et al. 2024, Earth Syst. Sci. Data 16, 2123-2139,
     doi:10.5194/essd-16-2123-2024, Table 1: climatological mean net
     air-sea CO2 flux and area for 14 open-ocean biomes (SOCATv2022,
     1980-2021, fluxes computed with 2010 inputs). Transcribed below
     verbatim from the published table -- there is no machine-readable
     CSV of this table, so the values are a literal with the citation.
     These are NET air-sea fluxes (they include the natural outgassing
     of river-borne carbon), NOT the anthropogenic ocean sink, and they
     are a climatological mean, not an annual series. The script aggregates
     the 14 biomes into 8 basin regions and computes flux densities.
  3. Ciais et al. 2026 (low-latency global carbon budget 2025, arXiv
     2609.34226): preliminary 2025 ocean uptake, quoted in the page text
     only, not in the annual series.

Unit note: 1 GtC = 1 PgC = 3.664 GtCO2 (the GCB spreadsheet factor).
Sign convention on the page: uptake is POSITIVE (carbon into the ocean);
Fay et al. print fluxes negative for uptake, so signs are flipped here
and the flip is stated on the page.
"""
import http.cookiejar
import json
import os
import urllib.request

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "data.json")

GCB_URL = ("https://data.icos-cp.eu/licence_accept"
           "?ids=%5B%22qSjPBsV1drZnYdH-yCJMmkGn%22%5D")
GCB_XLSX = os.path.join(ROOT, "Global_Carbon_Budget_2025_v1.0.xlsx")
GTCO2_PER_GTC = 3.664

# --- Fay et al. 2024, Table 1, transcribed verbatim -----------------------
# flux_pgC: net air-sea CO2 flux, PgC/yr, as printed (negative = into ocean).
# area: 10^6 km2. d_fco2: mean delta-fCO2, micro-atm, as printed.
FAY_BIOMES = [
    # (biome, basin, flux_pgC, area_mkm2, d_fco2_uatm)
    ("NP ice", "North Pacific", -0.02, 4.2, -24.6),
    ("NP SPSS", "North Pacific", -0.11, 12.8, -11.5),
    ("NP subtropics", "North Pacific", -0.40, 47.9, -8.2),
    ("Pacific equatorial", "Equatorial Pacific", 0.35, 26.4, 35.0),
    ("SP subtropics", "South Pacific", -0.14, 52.7, -2.3),
    ("NA ice", "North Atlantic", -0.04, 4.5, -19.3),
    ("NA SPSS", "North Atlantic", -0.27, 9.7, -36.2),
    ("NA subtropics", "North Atlantic", -0.24, 23.4, -10.0),
    ("Atlantic equatorial", "Equatorial Atlantic", 0.04, 7.4, 14.7),
    ("SA subtropics", "South Atlantic", 0.01, 18.1, 5.6),
    ("Indian subtropics", "Indian Ocean", -0.18, 35.9, -4.5),
    ("SO STSS", "Southern Ocean", -0.59, 29.6, -22.1),
    ("SO SPSS", "Southern Ocean", -0.21, 30.7, -6.0),
    ("SO ice", "Southern Ocean", -0.08, 18.7, -6.8),
]
FAY_GLOBAL_NET_PGC = -1.79   # paper's global open-ocean net flux, PgC/yr
FAY_GLOBAL_UNC = 0.7


def download_gcb(path):
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj))
    opener.addheaders = [("User-Agent", "ocean-ledge fetch_data.py")]
    opener.open(GCB_URL)          # sets the licence cookie (302)
    with opener.open(GCB_URL) as r:  # with cookie -> the .xlsx
        data = r.read()
    if data[:2] != b"PK":
        raise SystemExit("GCB download did not return an xlsx file")
    with open(path, "wb") as f:
        f.write(data)
    print(f"downloaded {path} ({len(data)} bytes)")


def parse_gcb(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    # Ocean Sink sheet: header row 32, data from row 33, col1 year, col2 GCB
    ws = wb["Ocean Sink"]
    assert ws.cell(row=32, column=1).value == "year"
    assert ws.cell(row=32, column=2).value == "GCB"
    series = []
    r = 33
    while True:
        y = ws.cell(row=r, column=1).value
        if y is None:
            break
        series.append((int(y), float(ws.cell(row=r, column=2).value)))
        r += 1
    # Historical Budget sheet: header row 16; col2 EFOS excl. carbonation,
    # col3 ELUC, col4 GATM, col5 SOCEAN, col6 SLAND, col7 cement carb, col8 BIM
    ws = wb["Historical Budget"]
    assert str(ws.cell(row=16, column=1).value).strip() == "Year"
    hist = {}
    r = 17
    while True:
        y = ws.cell(row=r, column=1).value
        if y is None:
            break
        hist[int(y)] = {
            "efos": ws.cell(row=r, column=2).value,
            "eluc": ws.cell(row=r, column=3).value,
            "gatm": ws.cell(row=r, column=4).value,
            "socean": ws.cell(row=r, column=5).value,
            "sland": ws.cell(row=r, column=6).value,
            "cement": ws.cell(row=r, column=7).value,
            "bim": ws.cell(row=r, column=8).value,
        }
        r += 1
    # cross-check: Ocean Sink GCB column must match Historical Budget SOCEAN
    worst = 0.0
    for y, v in series:
        hv = hist[y]["socean"]
        worst = max(worst, abs(v - hv))
    print(f"cross-check Ocean Sink vs Historical Budget: worst diff "
          f"{worst:.6f} GtC/yr over {len(series)} years")
    assert worst < 0.01, "GCB series disagree between sheets"
    return series, hist


def build_basins():
    basins = {}
    for biome, basin, flux, area, dfco2 in FAY_BIOMES:
        b = basins.setdefault(basin, {"biomes": [], "flux_pgC": 0.0,
                                      "area_mkm2": 0.0})
        # flip sign: uptake positive
        b["biomes"].append({"biome": biome, "uptake_pgC": round(-flux, 2),
                            "area_mkm2": area, "d_fco2_uatm": dfco2})
        b["flux_pgC"] += -flux
        b["area_mkm2"] += area
    total_printed = sum(b["flux_pgC"] for b in basins.values())
    total_area = sum(b["area_mkm2"] for b in basins.values())
    for b in basins.values():
        b["uptake_pgC"] = round(b["flux_pgC"], 2)
        b["area_mkm2"] = round(b["area_mkm2"], 1)
        b["flux_density_gC_m2_yr"] = round(
            b["flux_pgC"] / b["area_mkm2"] * 1000, 1)
        b["share_of_printed_total_pct"] = round(
            b["flux_pgC"] / total_printed * 100, 1)
        del b["flux_pgC"]
    print(f"basins: printed values sum to {total_printed:.2f} PgC/yr vs "
          f"Fay global {FAY_GLOBAL_NET_PGC} (gap "
          f"{total_printed + FAY_GLOBAL_NET_PGC:.2f}; rounding in the "
          f"printed table, within the +-0.7 uncertainty)")
    print(f"covered area {total_area:.1f} M km2 of ~361 M km2 global ocean")
    return basins, round(total_printed, 2), total_area


# --- GOOS Essential Ocean Variables ----------------------------------------
# Martin Miguez, Heslop et al. 2026, Front. Mar. Sci. 13:1737002 (CC BY 4.0).
# 36 EOVs. Categories follow the paper: ocean colour is cross-disciplinary
# in the paper ("The ocean color ECV is a cross-disciplinary GOOS EOV"),
# although the poster colours it with the physical set -- the paper's
# classification is used here and the difference is noted on the page.
# ECV overlap verified against the GCOS ECV list (gcos.wmo.int) and the
# paper's section 3.2.1: 11 physics EOVs, 5 biogeochemistry EOVs, ocean
# colour, and two biological ECVs that are compounds of EOVs (marine
# habitats = mangrove + seagrass + macroalgae + coral; plankton =
# phytoplankton + zooplankton). Pilot EOVs per the poster/paper.
EOVS = [
    # (name, category, pilot, ecv status)
    ("Turbulent diapycnal fluxes", "Physical", True, "—"),
    ("Ocean surface heat flux", "Physical", False, "ECV"),
    ("Sea state", "Physical", False, "ECV"),
    ("Sea surface height", "Physical", False, "ECV"),
    ("Ocean surface stress", "Physical", False, "ECV"),
    ("Sea surface salinity", "Physical", False, "ECV"),
    ("Subsurface salinity", "Physical", False, "ECV"),
    ("Subsurface temperature", "Physical", False, "ECV"),
    ("Sea ice", "Physical", False, "ECV"),
    ("Sea surface temperature", "Physical", False, "ECV"),
    ("Surface currents", "Physical", False, "ECV"),
    ("Ocean bottom pressure", "Physical", False, "—"),
    ("Subsurface currents", "Physical", False, "ECV"),
    ("Oxygen", "Biogeochemical", False, "ECV"),
    ("Nutrients", "Biogeochemical", False, "ECV"),
    ("Inorganic carbon", "Biogeochemical", False, "ECV"),
    ("Stable carbon isotopes", "Biogeochemical", False, "—"),
    ("Dissolved organic carbon", "Biogeochemical", False, "—"),
    ("Transient tracers", "Biogeochemical", False, "ECV"),
    ("Particulate matter", "Biogeochemical", False, "—"),
    ("Nitrous oxide", "Biogeochemical", False, "ECV"),
    ("Microbes — biomass & diversity", "Biology & Ecosystems", True, "—"),
    ("Benthic invertebrates — abundance & distribution",
     "Biology & Ecosystems", True, "—"),
    ("Seabirds — abundance & distribution", "Biology & Ecosystems", False, "—"),
    ("Sea turtles — abundance & distribution", "Biology & Ecosystems", False, "—"),
    ("Phytoplankton — biomass & diversity", "Biology & Ecosystems", False,
     "Part of the Plankton ECV"),
    ("Fish — abundance & distribution", "Biology & Ecosystems", False, "—"),
    ("Zooplankton — biomass & diversity", "Biology & Ecosystems", False,
     "Part of the Plankton ECV"),
    ("Marine mammals — abundance & distribution",
     "Biology & Ecosystems", False, "—"),
    ("Mangroves — cover & composition", "Biology & Ecosystems", False,
     "Part of the Marine Habitats ECV"),
    ("Coral — cover & composition", "Biology & Ecosystems", False,
     "Part of the Marine Habitats ECV"),
    ("Macroalgal canopy — cover & composition", "Biology & Ecosystems", False,
     "Part of the Marine Habitats ECV"),
    ("Seagrass — cover & composition", "Biology & Ecosystems", False,
     "Part of the Marine Habitats ECV"),
    ("Ocean colour", "Cross-disciplinary", False, "ECV"),
    ("Ocean sound", "Cross-disciplinary", False, "—"),
    ("Marine debris", "Cross-disciplinary", False, "—"),
]

# --- Global ONCE four pumps -------------------------------------------------
# Global Ocean Negative Carbon Emissions Program (Global ONCE) Science Plan,
# Chief Scientist Nianzhi Jiao. PSI factor: Frankignoulle et al. 1994.
# Temperature effect: Takahashi et al. 1993 (pCO2 +4.23%/degC).
PUMPS = [
    {"abbr": "SCP", "name": "Solubility Carbon Pump",
     "role": "Cold water dissolves more CO2 than warm water, so cooling "
             "surface water and strong winds pull CO2 from the air into "
             "the sea. This is the physical entry point for the sink: it "
             "sets the air-sea CO2 gradient the other pumps work with.",
     "source": "Global ONCE Science Plan; Takahashi et al. 1993"},
    {"abbr": "BCP", "name": "Biological Carbon Pump",
     "role": "Photosynthesis fixes CO2 into organic carbon; a fraction "
             "sinks as particles (POC) below the surface, where it is "
             "eaten, respired or buried. Plankton, zooplankton and fish "
             "repackage it on the way down.",
     "source": "Global ONCE Science Plan"},
    {"abbr": "MCP", "name": "Microbial Carbon Pump",
     "role": "Microbes transform dissolved organic carbon (DOC) that "
             "would otherwise be eaten within days into recalcitrant "
             "dissolved organic carbon (RDOC), which resists breakdown "
             "for centuries to millennia. It is the ocean's long-term "
             "dissolved store.",
     "source": "Global ONCE Science Plan; Jiao et al. 2010, "
               "Nat. Rev. Microbiol."},
    {"abbr": "CCP", "name": "Carbonate Counter Pump",
     "role": "Calcifiers (coccolithophores, corals, shellfish) build "
             "calcium carbonate shells. Each mole of CaCO3 precipitated "
             "releases about 0.6 mol of CO2 (Psi ~ 0.6), so calcification "
             "partly offsets the biological pump -- and the ratio rises "
             "as seawater loses buffer capacity.",
     "source": "Global ONCE Science Plan; Frankignoulle et al. 1994"},
    {"abbr": "BCMS", "name": "Synergistic Coupling of Four Pumps",
     "role": "The pumps do not act alone. Biological drawdown lowers "
             "surface pCO2 and primes the solubility pump; the microbial "
             "pump locks the biological pump's DOC into RDOC; the "
             "carbonate counter-pump offsets the biological pump. "
             "Warming weakens the solubility pump while the biological "
             "and microbial responses remain uncertain.",
     "source": "Global ONCE Science Plan"},
]

# --- Basin drivers: why each basin takes up what it does --------------------
# Qualitative attribution only -- no published source splits a basin's
# uptake into pump shares, and the page says so. Drivers are as stated in
# Fay et al. 2024 (and Muller et al. 2025 for the equatorial Pacific).
BASIN_DETAIL = {
    "North Atlantic": {
        "drivers": "Cooling of warm Gulf Stream water as it flows north, "
                   "plus strong winds, makes this the most intense sink "
                   "per unit area. Spring phytoplankton blooms draw CO2 "
                   "down further, and the water then sinks, carrying "
                   "anthropogenic carbon into the deep ocean.",
        "driver_source": "Fay et al. 2024; Ridge & McKinley 2020 (via Fay et al. 2024)",
        "pumps": ["SCP", "BCP"],
        "eovs": ["Sea surface temperature", "Sea surface salinity",
                 "Subsurface currents", "Sea surface height", "Sea state",
                 "Inorganic carbon", "Oxygen", "Nutrients", "Ocean colour"],
    },
    "North Pacific": {
        "drivers": "Subpolar cooling and spring blooms in the north; "
                   "subtropical gyres where the seasonal cycle is set by "
                   "temperature. The largest basin by area, but a modest "
                   "sink per square metre.",
        "driver_source": "Fay et al. 2024",
        "pumps": ["SCP", "BCP"],
        "eovs": ["Sea surface temperature", "Sea surface salinity",
                 "Sea state", "Inorganic carbon", "Ocean colour", "Oxygen",
                 "Nutrients"],
    },
    "Equatorial Pacific": {
        "drivers": "Upwelling brings cold, CO2-rich deep water to the "
                   "surface, so this is the ocean's largest natural "
                   "source. During El Niño the upwelling weakens and "
                   "outgassing falls by roughly 0.1-0.2 PgC/yr.",
        "driver_source": "Fay et al. 2024; Müller et al. 2025, "
                         "Nat. Clim. Change",
        "pumps": ["Upwelling — source (overwhelms the pumps)"],
        "eovs": ["Sea surface temperature", "Subsurface temperature",
                 "Surface currents", "Sea surface height",
                 "Inorganic carbon"],
    },
    "South Pacific": {
        "drivers": "A weak sink spread over the largest subtropical "
                   "area. The southeast Pacific is the most data-sparse "
                   "region in the SOCAT record, so this number carries "
                   "the largest uncertainty.",
        "driver_source": "Fay et al. 2024",
        "pumps": ["SCP"],
        "eovs": ["Sea surface temperature", "Inorganic carbon",
                 "Ocean colour", "Oxygen"],
    },
    "Equatorial Atlantic": {
        "drivers": "A small source from equatorial upwelling.",
        "driver_source": "Fay et al. 2024",
        "pumps": ["Upwelling — source (overwhelms the pumps)"],
        "eovs": ["Sea surface temperature", "Surface currents",
                 "Inorganic carbon"],
    },
    "South Atlantic": {
        "drivers": "Near-neutral in the Fay climatology -- a very small "
                   "source, within uncertainty of zero.",
        "driver_source": "Fay et al. 2024",
        "pumps": ["SCP (weak)"],
        "eovs": ["Sea surface temperature", "Inorganic carbon",
                 "Ocean colour"],
    },
    "Indian Ocean": {
        "drivers": "A subtropical sink, cut into each summer by "
                   "monsoon-driven upwelling in the northwest Indian "
                   "Ocean, which brings CO2-rich water up and vents it.",
        "driver_source": "Fay et al. 2024",
        "pumps": ["SCP", "BCP"],
        "eovs": ["Sea surface temperature", "Sea state",
                 "Inorganic carbon", "Oxygen"],
    },
    "Southern Ocean": {
        "drivers": "The largest sink. Strong winds and cooling in the "
                   "subtropical band hold the single biggest biome sink "
                   "(-0.59 PgC/yr); summer biology and winter sea ice "
                   "shape the subpolar and ice zones, where ice cover "
                   "cuts gas exchange in winter.",
        "driver_source": "Fay et al. 2024",
        "pumps": ["SCP", "BCP"],
        "eovs": ["Sea ice", "Sea surface temperature",
                 "Sea surface salinity", "Subsurface temperature",
                 "Subsurface salinity", "Inorganic carbon", "Oxygen",
                 "Nutrients", "Ocean colour", "Stable carbon isotopes"],
    },
}


def main():
    if not os.path.exists(GCB_XLSX):
        download_gcb(GCB_XLSX)
    series, hist = parse_gcb(GCB_XLSX)
    basins, printed_total, covered_area = build_basins()

    world = []
    for y, v in series:
        h = hist[y]
        world.append({
            "year": y,
            "socean_gtc": round(v, 3),
            "socean_gtco2": round(v * GTCO2_PER_GTC, 2),
            "efos_gtc": round(h["efos"], 3),
            "eluc_gtc": round(h["eluc"], 3),
            "gatm_gtc": round(h["gatm"], 3),
            "sland_gtc": round(h["sland"], 3),
        })
    latest = world[-1]
    prev = world[-2]
    cum_gtc = round(sum(w["socean_gtc"] for w in world), 1)
    cum_emis = round(sum(hist[y]["efos"] + hist[y]["eluc"]
                         for y, _ in series), 1)
    decadal = {}
    for start in (1960, 1970, 1980, 1990, 2000, 2010):
        vals = [w["socean_gtc"] for w in world if start <= w["year"] < start + 10]
        decadal[str(start)] = round(sum(vals) / len(vals), 2)
    vals1524 = [w["socean_gtc"] for w in world if 2015 <= w["year"] <= 2024]
    total_emis_latest = latest["efos_gtc"] + latest["eluc_gtc"]

    data = {
        "meta": {
            "title": "Ocean Ledger — annual ocean CO2 uptake by basin",
            "latest_year": latest["year"],
            "first_year": world[0]["year"],
            "units": "GtC/yr (1 GtC = 1 PgC = 3.664 GtCO2)",
            "sources": {
                "gcb": "Friedlingstein et al. 2025, Global Carbon Budget 2025, "
                       "Earth Syst. Sci. Data 18, 3211-3302, "
                       "doi:10.18160/GCP-2025 (spreadsheet via ICOS Carbon Portal)",
                "fay": "Fay et al. 2024, Earth Syst. Sci. Data 16, 2123-2139, "
                       "doi:10.5194/essd-16-2123-2024, Table 1",
                "goos": "Martin Miguez, Heslop et al. 2026, Frontiers in "
                        "Marine Science 13:1737002, "
                        "doi:10.3389/fmars.2026.1737002 (CC BY 4.0)",
                "once": "Global Ocean Negative Carbon Emissions Program "
                        "(Global ONCE) Science Plan, Chief Scientist "
                        "Nianzhi Jiao",
            },
            "notes": [
                "GCB ocean sink (SOCEAN) is the anthropogenic uptake: the "
                "average of 10 global ocean biogeochemistry models and 9 "
                "surface-ocean fCO2 data products, uncertainty +-0.4 GtC/yr.",
                "Fay et al. basin fluxes are NET air-sea fluxes (they "
                "include the natural outgassing of river-borne carbon, "
                "~0.65 GtC/yr in the GCB adjustment), as a climatological "
                "mean, not an annual series. No published annual "
                "basin-level series exists in one clean table.",
                "Sign convention on this page: uptake is positive "
                "(carbon into the ocean). Fay et al. print the opposite "
                "sign; signs are flipped here.",
            ],
        },
        "world": world,
        "summary": {
            "latest_year": latest["year"],
            "latest_socean_gtc": latest["socean_gtc"],
            "latest_socean_gtco2": latest["socean_gtco2"],
            "prev_socean_gtc": prev["socean_gtc"],
            "yoy_pct": round((latest["socean_gtc"] - prev["socean_gtc"])
                             / prev["socean_gtc"] * 100, 1),
            "latest_total_emissions_gtc": round(total_emis_latest, 2),
            "latest_ocean_share_of_emissions_pct": round(
                latest["socean_gtc"] / total_emis_latest * 100, 1),
            "mean_2015_2024_gtc": round(sum(vals1524) / len(vals1524), 2),
            "cumulative_1959_latest_gtc": cum_gtc,
            "cumulative_1959_latest_gtco2": round(cum_gtc * GTCO2_PER_GTC, 0),
            "cumulative_emissions_1959_latest_gtc": cum_emis,
            "cumulative_ocean_share_pct": round(cum_gtc / cum_emis * 100, 1),
            "decadal_means_gtc": decadal,
            "preliminary_2025_gtc": 3.11,
            "preliminary_2025_source": "Ciais et al. 2026, low-latency "
                "global carbon budget 2025, arXiv:2609.34226 "
                "(3.11 +- 0.36 GtC/yr; preliminary, not in the GCB series)",
        },
        "basins": basins,
        "basin_detail": BASIN_DETAIL,
        "eovs": [{"name": n, "category": c, "pilot": p, "ecv": e}
                 for n, c, p, e in EOVS],
        "pumps": PUMPS,
        "basin_reconciliation": {
            "printed_biome_sum_pgC": printed_total,
            "fay_global_net_pgC": FAY_GLOBAL_NET_PGC,
            "fay_global_uncertainty_pgC": FAY_GLOBAL_UNC,
            "gap_pgC": round(printed_total + FAY_GLOBAL_NET_PGC, 2),
            "covered_area_mkm2": covered_area,
            "note": "The 14 printed biome values sum to -1.88 PgC/yr "
                    "against the paper's global -1.79 +- 0.7 PgC/yr. The "
                    "0.09 gap is rounding in the printed table (values "
                    "given to 0.01) and coverage differences; it sits well "
                    "inside the stated uncertainty. Basin shares on the "
                    "page are shares of the printed-basin total so they "
                    "sum to 100%.",
        },
    }
    with open(OUT, "w") as f:
        json.dump(data, f, indent=1)
    print(f"wrote {OUT}")
    print(f"latest: {latest['year']} SOCEAN {latest['socean_gtc']} GtC/yr "
          f"({latest['socean_gtco2']} GtCO2/yr), "
          f"{data['summary']['yoy_pct']:+.1f}% vs {prev['year']}, "
          f"{data['summary']['latest_ocean_share_of_emissions_pct']}% of "
          f"total emissions")
    print(f"cumulative {world[0]['year']}-{latest['year']}: {cum_gtc} GtC")


if __name__ == "__main__":
    main()
