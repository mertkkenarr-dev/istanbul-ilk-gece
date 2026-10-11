"""1999 İzmit depreminin fay bölgesi (Kocaeli, Sakarya, Yalova, Bolu+Düzce) için maruziyet ızgarası: kalibrasyonun yüksek şiddet ucu.

Girdi : data/raw/buyuk/worldpop_tur_2000_1km.tif (WorldPop 2000, 1 km), vs30_mosaic_median_30c.tif, data/interim/dogu_iller_1999.geojson
Çıktı : data/processed/hasar/bolge1999_hucre.parquet (lon, lat, il, nufus, vs30)

Nüfus 0,025° (~2,5 km) hücrelere toplanır (Cholesky boyutu için). WorldPop 2000 zaten nüfus sayımı/BM toplamlarına
kalibre edilmiş olduğundan yeniden ölçeklenmez (elde doğrulanmış il bazlı 2000 sayım tablosu yok; uydurma sabit kullanılmadı).
Bolu 1999'da Düzce'yi de içeriyordu (Düzce 9 Aralık 1999'da il oldu); ikisi tek birim sayılır.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio import features

KOK = Path(__file__).resolve().parent.parent
HS = KOK / "data/processed/hasar"
HUCRE = 0.025

il = gpd.read_file(KOK / "data/interim/dogu_iller_1999.geojson")
il["birim"] = il.name.replace({"Düzce": "Bolu"})
il = il.dissolve("birim").reset_index()
with rasterio.open(KOK / "data/raw/buyuk/worldpop_tur_2000_1km.tif") as r:
    win = rasterio.windows.from_bounds(*il.total_bounds, r.transform).round_offsets().round_lengths()
    A = r.read(1, window=win).astype(float); T = r.window_transform(win)
A[~np.isfinite(A) | (A < 0)] = 0
lab = features.rasterize([(g, i + 1) for i, g in enumerate(il.geometry)], A.shape, transform=T, fill=0)
rr, cc = np.nonzero((A > 0) & (lab > 0))
lon, lat = rasterio.transform.xy(T, rr, cc)
d = pd.DataFrame(dict(lon=lon, lat=lat, nufus=A[rr, cc], il=il.birim.values[lab[rr, cc] - 1]))
d["hx"] = np.floor(d.lon / HUCRE); d["hy"] = np.floor(d.lat / HUCRE)
g = d.groupby(["il", "hx", "hy"]).apply(lambda x: pd.Series(dict(lon=np.average(x.lon, weights=x.nufus), lat=np.average(x.lat, weights=x.nufus),
                                                                 nufus=x.nufus.sum())), include_groups=False).reset_index()
wp = g.groupby("il").nufus.sum()
g = g[g.nufus >= 50].reset_index(drop=True)
with rasterio.open(KOK / "data/raw/buyuk/vs30_mosaic_median_30c.tif") as r:
    v = np.array([x[0] for x in r.sample(np.c_[g.lon, g.lat])], float)
v[(v == 600.0) | ~np.isfinite(v)] = np.nan
g["vs30"] = pd.Series(v).fillna(pd.Series(v).median()).values
g[["il", "lon", "lat", "nufus", "vs30"]].to_parquet(HS / "bolge1999_hucre.parquet", index=False)
print(f"hücre: {len(g)}; WorldPop il toplamları: {wp.round(0).to_dict()}")
print(g.groupby("il").agg(hucre=("nufus", "size"), nufus=("nufus", "sum"), vs30_med=("vs30", "median")).round(0))
