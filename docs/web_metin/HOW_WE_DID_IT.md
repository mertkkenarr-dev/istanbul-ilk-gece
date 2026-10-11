# "How we did it" page (English version of NASIL_YAPTIK.md)

> Target reader: someone non-technical. Every section follows the same pattern: **What**, **Why**, **How**, **What came out**,
> **What the limits are**. Each section ends with the code and method document for readers who want detail. All code is open.

---

## In short

The study has five steps:

1. **Data:** Neighbourhood, building, population, road, hospital and open-space data for Istanbul were collected from more than 25 open
   sources, cleaned and joined into a single table of 959 neighbourhoods.
2. **Shaking:** Models that estimate how strongly each neighbourhood would shake were tested against recordings of real earthquakes.
3. **Damage and the test:** Methods that estimate how buildings behave under that shaking were tested against the 6 February 2023
   earthquake; because they consistently underestimated a large earthquake, we decided not to publish death counts.
4. **Capacity:** Where survivors could go on the first night was solved as an optimisation problem; transport, communication, hospital
   and shelter needs were estimated.
5. **Visualisation:** The results were placed on a 3D map with real building footprints and heights estimated with machine learning.

---

## 1. Data: where it came from

| What | Source | Used for |
|---|---|---|
| Neighbourhood population (2025) | TÜİK (Turkish Statistical Institute), address-based population register | The basis of every calculation: how many people |
| Building stock (2017): age and floor classes | Istanbul Metropolitan Municipality (İBB) Open Data | Damage classes, floor distribution |
| İBB earthquake scenario (Mw 7.5, night) | İBB Open Data | Comparison, shelter needs |
| Building footprints (1.15 million) | Overture Maps (September 2026) | Building shape and count, 3D map |
| Road network, neighbourhood boundaries, park and hospital tags | OpenStreetMap | Distance, access, assembly areas |
| Bridges and viaducts, emergency transport routes | İBB Open Data | Critical parts of the road network |
| Open and green spaces | İBB Open Data + OpenStreetMap | Assembly area candidates |
| Hospitals, fire stations | İBB Open Data; provincial bed total from a parliamentary record | Capacity and access |
| Soil (Vs30) | United States Geological Survey (USGS) | Local amplification of shaking |
| Marmara fault traces | GEM Global Active Faults | Earthquake scenarios |
| Recordings of the 2025 Silivri and 2023 earthquakes | USGS ShakeMap | Testing the models |
| 1999 İzmit recordings | KOERI (2010) report | Testing the models |
| Satellite built-up and population layers | European Commission GHSL | Proxy for building age, 6 February population |
| 6 February damage and casualty figures | AFAD, Presidency of Strategy and Budget (2023) | The test |
| Building permits (2010–2024), social assistance, household size | İBB Open Data | Renewal rate, needs |

**Limits:** The official AFAD list of assembly areas, İBB's microzonation (soil) map and per-facility hospital bed counts are not openly
available in bulk; open-data proxies were used instead and each one is marked.

---

## 2. Cleaning: what we fixed and how

**What:** Raw data arrives with errors. Every fix was logged as a "decision" (55 decisions) and every intermediate product passed
automated checks (56 checks, all passing). The whole pipeline can be rebuilt from the raw files in about 2.5 minutes.

**Examples:**

| Problem | What we did | Why it matters |
|---|---|---|
| Excel had turned the neighbourhood names "19 Mayıs" and "15 Temmuz" into dates | Names restored | Otherwise 5 neighbourhoods would lose their assistance data |
| İBB files use a Turkish character encoding (cp1254) | Read with the correct encoding | "HEYBELİADA" was garbled and broke the matching |
| In the headman office list, the "Neighbourhood name" column points to the wrong neighbourhood (115 records) | Name derived from the office's own name | So neighbourhoods match correctly |
| The OpenStreetMap boundary of Istanbul includes the sea (11,281 km²) | A separate land boundary was built | Sea area would distort densities |
| Emergency, outpatient and annex records of the same hospital listed separately (472 records) | Records within 120 m merged into one facility (328) | So capacity is not double counted |
| 56 fake "City Hospital" records in the hospital list, such as "istanbul Şehir" or "Mega Şehir" | Removed | They distorted bed allocation and the "earthquake-resistant hospital" assumption |
| Latitude and longitude columns swapped in the fire station data | Fixed by value range | Stations appeared in the sea |
| The same park drawn separately in İBB and OSM (in pieces in OSM) | 11,390 pieces merged into 9,144 areas | So assembly capacity is not inflated |
| Medians, junctions and metro exits appear as "green space" (539) | Removed from assembly areas | A traffic island is not an assembly area |
| Neighbourhoods created after 2017 (e.g. 15 Temmuz, 5. Levent) | Merged with their former parent neighbourhood | Building data follows the old boundaries |

**Joining:** The unit of analysis is the neighbourhood (959). Names differ between İBB 2017, TÜİK 2025 and OSM 2026; matching used the
official neighbourhood code (UAVT) first, then name, headman office location and, where needed, fuzzy name matching; the method and
confidence of every match are recorded.

Code: `scripts/00–09`, report: `docs/VERI_RAPORU.md`.

---

## 3. Shaking: the ground-motion model

**What:** Equations that estimate how strongly a point will shake in an earthquake ("ground-motion models"). Inputs: magnitude,
distance to the fault, soil. Output: ground acceleration.

**Why:** Everything starts with shaking; wrong shaking makes every later calculation wrong.

**How:**
- 8 widely used equations (including those used in Istanbul scenario studies) were run side by side.
- Each was tested against recordings of two real earthquakes: 2025 Silivri (47 stations in Istanbul) and 1999 İzmit (25 stations).
- They were weighted by how well they matched the recordings; the result is a weighted mix, not a single equation.
- The same earthquake was generated 1,000 times, each time keeping the fact that neighbouring areas shake similarly (spatial
  correlation). This shows a "bad night" alongside the "most likely" value.
- Three rupture scenarios: Central Marmara (Mw 7.5), Islands–Çınarcık (Mw 7.4) and the whole Marmara (Mw 7.7).

**What came out:** Some equations overestimate shaking in a moderate earthquake like 2025 (largest difference ~2.3×) but are consistent
in a large one like 1999; this is expected, since they were developed for large earthquakes. The weighted mix is consistent for both.

**Limits:** The soil data is coarse (about 900 m resolution); local effects such as coastal fill are not visible. 2025 was a moderate
earthquake; the test gets weaker as magnitude grows.

Code: `model/yh_*`, document: `docs/YONTEM_1_YER_HAREKETI.md`.

---

## 4. Damage and the 6 February test: why there is no death count

**What:** "Fragility curves" that give the probability of a building suffering light, moderate or heavy damage or collapsing under a
given shaking, and fatality rates in collapsed buildings. The standard method of scenario studies worldwide and in Türkiye.

**Why we tested it:** The only way to see what a model does in a large earthquake is to test it against one.

**How:**
- First we checked that we had implemented the method correctly: we reproduced the number of very heavily damaged buildings in İBB's
  open scenario data (13,496) with the same method (13,510).
- Then we ran the method with the real shaking of 6 February 2023 (USGS), the region's night-time population (satellite) and building
  age seen from satellite.
- Next we tried to calibrate our own model against four real earthquakes (2025 Silivri, 1999 Istanbul, 1999 fault zone, 6 February):
  we added shaking duration, lethality by height of the collapsed building and regional differences in building quality.

**What came out:**

| Model | Estimate for 6 February | Actual |
|---|---|---|
| Standard fragility method (KOERI/HAZUS curves) | ~15,400 | 53,537 |
| USGS empirical model calibrated for Türkiye | ~21,300 | |
| This project, calibrated to Istanbul earthquakes | ~2,200 | |
| This project, calibrated to all four earthquakes | ~24,700 | |

Even the best version overestimated 1999 Istanbul by about 3× and underestimated 6 February by about 2×, and it assigned far more of
the deaths to masonry buildings than actually happened. Fixing this takes real damage data broken down by building type and floor count,
not parameter tuning (the Ministry inspected 2.15 million buildings one by one; this data is not openly available in bulk).

That all methods underestimate losses in large, long-duration earthquakes is a known difficulty in the literature too.

**Decision:** No death count is published for Istanbul. The damage model is used only for rough magnitudes (how many people in which
neighbourhood live in damaged buildings); the assembly calculation rests mainly on population and area.

Code: `model/hs_*`, `sinama/`, document: `docs/YONTEM_2_HASAR.md`.

---

## 5. Assembly: an optimisation problem

**What:** On the night of an earthquake, is there space within walking distance for everyone who goes outside?

**Why a simple ratio is not enough:** "Park area in the neighbourhood ÷ population" is misleading: one park serves several
neighbourhoods, and people only go where they can walk.

**Toy example:** Picture three streets (A, B, C; 100 people each) and two parks: P1 holds 100 people, P2 holds 250. Total capacity is
350 and there are 300 people, so on paper there is room for everyone. But A and B can only walk to P1, and P2 is only near C. The 200
people of A and B do not fit into P1's 100 places: **100 people find no space**, while 150 places sit empty in P2. The total says
"enough"; the location says "not enough".

**How (at full scale):**
- Istanbul was divided into ~49,000 blocks (squares of about 250 m); each block's population was distributed by building volume.
- 2,960 open spaces over 2,000 m² are candidates (the same order of magnitude as the 3,021 areas announced by AFAD). The usable share
  of each depends on its type: pitches and squares 90%, parks 60%, school grounds 50%, groves and forest 20%. 1.5 m² per person.
- Each block is assigned to open spaces within 1 km walking distance; no space can exceed its capacity. The goal is first to find space
  for as many people as possible, then to minimise total walking. This is a "transportation problem"; the linear program has about
  170,000 variables and solves in half a second.
- How many people go outside: those living in damaged buildings plus a fear share that rises with shaking (10% at 0.05 g, 80% at 0.30 g).

**What came out:** In the median earthquake, **2.7 million** of the 9.1 million people outside on the first night find no space within
1 km.

| If the assumption changes | No space |
|---|---|
| 2 m² per person | 3.4 million |
| Walking limit 1.5 km | 1.6 million |
| Half as many people go outside | 0.85 million |
| Everyone goes outside | 6.4 million |

**Limits:** "How many people go outside" is the assumption that matters most; that is why a range is given. The open-space layer is not
the official list.

Code: `ihtiyac/i01–i02`, document: `docs/YONTEM_5_IHTIYAC.md`.

---

## 6. Machine learning: where we used it and where we gave up

**a) Building height (used on the site).** Only 4% of the buildings on the 3D map have a known height. We trained a model (LightGBM) on
72,000 Istanbul buildings with a known floor count. For each building it looks at footprint area and shape, the surrounding buildings,
the average height measured from satellite and the neighbourhood's İBB floor distribution. It was tested on districts it never saw: it
gets the floor class (1–4 / 5–8 / 9+) right 67% of the time, against 59% for a simple rule. It still underestimates tall buildings;
heights on the map are marked as "estimated".

**b) Understanding the open scenario data.** We built a model that explains the neighbourhood damage rates published by İBB and looked at
which information weighs most (SHAP). Result: distance to the fault dominates the scenario's damage pattern by far, followed by the share
of pre-1980 buildings and the share of buildings over 5 floors. On districts it never saw, our physics-based calculation explains 50% of
the variance, and 59% together with machine learning; a randomly split test inflates this by about 0.1, which is why district hold-out
testing was used.

**c) An attempt we dropped: learning from 6 February.** We tried to build a "which building collapsed under how much shaking" model
from 47,000 building damage labels that the European Copernicus service marked on satellite images. In regions it never saw, the model
separated collapsed buildings only slightly better than a coin flip (AUC 0.54–0.68). The reason was the labels: each region was marked
on a different date with different imagery. This attempt was left out of the results.

**d) A fast surrogate of the simulator.** We built a model (R² 0.96) that imitates the 72-hour simulator and runs instantly in the
browser; once the simulator left the main story, this model was no longer used on the site.

Code: `ml/`, document: `docs/YONTEM_4_ML.md`.

---

## 7. The 72-hour simulator: how it works, and why it is not in the main story

**What:** A model that plays out the 72 hours after the earthquake in 15-minute steps: the falling survival chances of people trapped
under rubble, teams moving between neighbourhoods on a damaged road network, bridge and debris closures, hospitals filling up.

**How:** Victims are tracked as pools per neighbourhood and teams as individual agents. The survival curve comes from rescue data of past
earthquakes (Coburn et al. 1992); bridge damage from HAZUS curves. Four team dispatch rules and one optimised plan were compared on the
same random earthquakes; field hospital locations were optimised separately.

**Why it is not in the main story:** The simulator's input is who is trapped under rubble. That comes from the damage model that failed
the 6 February test. The mechanisms (e.g. rescue slowed by crowds) are sound, but the absolute numbers are not reliable enough.

Code: `sim/`, document: `docs/YONTEM_3_SIMULASYON.md`.

---

## 8. Esenyurt figures

| Item | Value | How |
|---|---|---|
| Walkable street space (Turgut Özal) | ~84,000 m² | OSM road length × width by road type, minus cars parked overnight |
| Vehicles (Esenyurt) | 150–240k | TÜİK Istanbul: 241 cars per 1,000 people; lower bound 150 |
| District exit capacity | ~68,000 vehicles/hour | Lanes × per-lane capacity of motorways, primary and secondary roads crossing the boundary |
| Hospital beds | ~720 (0.7 per 1,000) | Provincial bed total distributed by the building area of hospital campuses |
| Camp area needed (Turgut Özal) | 346,050 m² | İBB's shelter need of 7,690 people × 45 m² per person (Sphere) |

---

## 9. Maps

The basemap comes from OpenStreetMap data (Protomaps build, October 2026) and is served from within the site as a single file. Buildings
are Overture footprints; their heights come from the model in section 6 (the real value where it is known). The assembly flows are the
direct output of the optimisation in section 5.

---

## 10. Limitations and honesty notes

- This is an independent portfolio study; it does not forecast earthquakes and does not evaluate the plans or work of official
  institutions.
- The assembly result is not an evaluation of the official assembly area plan; it uses potential areas derived from open data.
- No death count is published (section 4).
- The assembly result depends most on the "how many people go outside" assumption; a range is given.
- The data comes from different years: population 2025, open spaces and roads 2026, while building age and floor classes and the İBB
  earthquake scenario rest on the 2017 building stock. That is why age and floor shares are given "in the 2017 census", people per
  building is given as a range using both the 2017 census and current footprints, and the shelter need is treated as a lower bound. The
  assembly calculation uses only 2025 population and current open spaces; it does not rely on the old building data.
- Soil data is coarse; hospital beds are an estimate distributed from the provincial total.
- Errors we found in our own calculations along the way (e.g. a ratio computed with the wrong population) were corrected and noted in the
  documents.

## Reproducing

All code and the order of steps are in the repository (`docs/ILERLEME.md`). Raw data is downloaded with `scripts/00_indir.py`; the
pipeline runs with a single command.
