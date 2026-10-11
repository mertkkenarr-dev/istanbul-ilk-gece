"""6 Şubat 2023 sınaması, adım 1: deprem bölgesinin gece nüfusu, gerçek sarsıntısı ve yapı stoku (ShakeMap ızgara düğümü başına).

Birim: ShakeMap ızgarası (30″ ≈ 0,9 km). Sarsıntı zaten bu çözünürlükte; GHSL nüfusu (3″) ve yapılaşma dönemleri bu düğümlere toplanır.
  nufus        GHS_POP 2020 (gece, yerleşik nüfus; deprem 04:17'de, İstanbul senaryosuyla aynı "herkes evde" koşulu)
  ln_sa*       iki ana şokun düğüm başına büyüğü, RotD50'ye çevrilmiş (ders2023/sarsinti.py)
  pay_80, pay_00  GHSL: 2020 yapılı alanının 1980 / 2000'de var olan payı → yaş sınıfı payları (yapı-sayısı ∝ yapılı alan, VARSAYIM)
  il           geoBoundaries ADM1
Çıktı: data/processed/sinama/maras2023_dugum.parquet
"""
from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import from_bounds

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "ders2023"))
import sarsinti  # noqa: E402

CIKTI = KOK / "data/processed/sinama"; CIKTI.mkdir(parents=True, exist_ok=True)
G = KOK / "data/raw/buyuk/ghsl"
BBOX = (34.9, 35.8, 39.99, 39.09)        # R6_C22 karosunun içinde kalmalı: dışarı taşan pencere satırları kaydırır


def oku(desen: str) -> tuple[np.ndarray, object]:
    f = next(G.glob(f"{desen}*R6_C22.tif"))
    with rasterio.open(f) as r:
        w = from_bounds(*BBOX, r.transform).round_offsets().round_lengths()
        assert w.row_off >= 0 and w.col_off >= 0 and w.row_off + w.height <= r.height and w.col_off + w.width <= r.width, w
        return r.read(1, window=w).astype(np.float64), r.window_transform(w)


pop, tr = oku("GHS_POP_E2020")
pop[pop < 0] = 0
s = {e: oku(f"GHS_BUILT_S_E{e}_")[0] for e in (1980, 2000, 2020)}
g1 = sarsinti.oku(KOK / "data/raw/external/usgs_2023/jllz_grid.xml")
g2 = sarsinti.oku(KOK / "data/raw/external/usgs_2023/jlqa_grid.xml")
dlon = g1["lon"][1] - g1["lon"][0]; dlat = g1["lat"][1] - g1["lat"][0]
n, m = pop.shape
lon = tr.c + tr.a * (np.arange(m) + 0.5); lat = tr.f + tr.e * (np.arange(n) + 0.5)
ix = np.rint((lon - g1["lon"][0]) / dlon).astype(int); iy = np.rint((lat - g1["lat"][0]) / dlat).astype(int)
anahtar = (iy[:, None] * 10_000 + ix[None, :]).ravel()
df = pd.DataFrame({"k": anahtar, "nufus": pop.ravel(), "s80": s[1980].ravel(), "s00": s[2000].ravel(), "s20": s[2020].ravel()})
df = df[(df.nufus > 0) | (df.s20 > 0)].groupby("k").sum()
df = df[df.nufus > 1]
df["iy"] = df.index // 10_000; df["ix"] = df.index % 10_000
df = df[df.ix.between(0, len(g1["lon"]) - 1) & df.iy.between(0, len(g1["lat"]) - 1)]
df["lon"] = g1["lon"][df.ix]; df["lat"] = g1["lat"][df.iy]
a, b = sarsinti.ornekle(g1, df.lon.values, df.lat.values), sarsinti.ornekle(g2, df.lon.values, df.lat.values)
for k in a:
    if k in ("vs30", "mmi"):
        df[k] = a[k] if k == "vs30" else np.fmax(np.nan_to_num(a[k]), np.nan_to_num(b[k]))
        continue
    df[k] = np.fmax(a[k], np.nan_to_num(b[k], nan=-99))
    df[f"{k}_s1"] = a[k]; df[f"{k}_s2"] = np.nan_to_num(b[k], nan=np.log(1e-6))   # iki ana şok ayrı (birikimli hasar için)
df["pay_80"] = np.where(df.s20 > 0, np.minimum(df.s80 / df.s20.clip(lower=1e-9), 1), 1.0)
df["pay_00"] = np.where(df.s20 > 0, np.minimum(df.s00 / df.s20.clip(lower=1e-9), 1), 1.0)
il = gpd.read_file(KOK / "data/raw/external/geoboundaries/tur_adm1.geojson")[["shapeName", "geometry"]]
p = gpd.GeoDataFrame(df.reset_index(drop=True), geometry=gpd.points_from_xy(df.lon, df.lat), crs=4326)
p = gpd.sjoin(p, il, predicate="within", how="left").drop(columns=["index_right", "geometry"]).rename(columns={"shapeName": "il"})
p = pd.DataFrame(p)
p.to_parquet(CIKTI / "maras2023_dugum.parquet", index=False)
pga = np.exp(p.ln_pga)
print(f"{len(p):,} düğüm, nüfus {p.nufus.sum():,.0f}; PGA ≥ 0,1 g altında {p.nufus[pga >= 0.1].sum():,.0f} kişi, ≥ 0,3 g {p.nufus[pga >= 0.3].sum():,.0f}")
print(p.groupby("il").agg(nufus=("nufus", "sum"), pga_med=("ln_pga", lambda x: float(np.exp(np.median(x))))).sort_values("nufus", ascending=False).head(16).round(3))
