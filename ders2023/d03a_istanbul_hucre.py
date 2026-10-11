"""İstanbul'un yapılı GHSL hücreleri (3″ ≈ 70×90 m), öznitelikleri ve yer hareketi sahaları (3×3 hücre blok merkezi ≈ 250 m).

GMPE'ler 9″ blok merkezinde hesaplanır: Vs30 rasterı zaten 30″ çözünürlükte, mesafe 250 m içinde değişmez; 9 kat daha az saha.
Çıktı: data/processed/ders2023/istanbul_hucre.parquet, istanbul_saha.parquet (OpenQuake ortamı yalnızca bunu okur)
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from ghsl import katmanlar
from ortak_ders import CIKTI, KOK, log, qc

ADIM = "d03a_istanbul_hucre"
kat = katmanlar((27.95, 40.78, 29.96, 41.62), "R5_C21")
tr = kat["_tr"]; n, m = kat["yapili_2020"].shape
r, c = np.nonzero(kat["yapili_2020"] > 0)
h = pd.DataFrame({k: v[r, c] for k, v in kat.items() if not k.startswith("_")})
h["lon"] = tr.c + tr.a * (c + 0.5); h["lat"] = tr.f + tr.e * (r + 0.5); h["hucre"] = r * m + c
h["blok"] = (r // 3) * (m // 3 + 1) + c // 3

mah = gpd.read_parquet(KOK / "data/interim/mahalle_sinir.parquet")[["uavt", "geometry"]].to_crs(4326)
g = gpd.GeoDataFrame(h, geometry=gpd.points_from_xy(h.lon, h.lat), crs=4326)
g = gpd.sjoin(g, mah, predicate="within", how="left").drop(columns="index_right")
g = g[~g.index.duplicated()]
disarida = g.uavt.isna()
log(ADIM, "GHSL", "İstanbul penceresindeki yapılı hücrelerin bir kısmı il kara sınırı dışında (komşu il, deniz kenarı piksel)", int(disarida.sum()),
    "Mahalle poligonu dışındaki hücreler çıkarıldı", "Aktarım yalnızca İstanbul mahallelerine uygulanır; mahalle toplamları İBB ile karşılaştırılacak")
h = pd.DataFrame(g[~disarida].drop(columns="geometry")).astype({"uavt": int}).reset_index(drop=True)

s = h.groupby("blok").agg(lon=("lon", "mean"), lat=("lat", "mean")).reset_index()
with rasterio.open(KOK / "data/interim/vs30_istanbul.tif") as rr:
    v = np.array([x[0] for x in rr.sample(np.c_[s.lon, s.lat])], dtype=float)
v[(v == 600.0) | ~np.isfinite(v)] = np.nan
mv = pd.read_parquet(KOK / "data/processed/mahalle.parquet", columns=["uavt", "vs30"]).set_index("uavt").vs30
blok_mah = h.groupby("blok").uavt.agg(lambda x: x.mode()[0])
eks = np.isnan(v)
v[eks] = mv.reindex(blok_mah.loc[s.blok[eks]].values).values
log(ADIM, "Vs30", "Kıyı bloklarının bir kısmı Vs30 rasterında su/boş hücreye düşüyor", int(eks.sum()),
    "Bloğun bulunduğu mahallenin Vs30 değeri atandı", "Mahalle Vs30 değeri bina ağırlıklı, aynı kaynaktan")
s["vs30"] = v
qc(ADIM, "Tüm blokların Vs30 değeri var", bool(np.isfinite(s.vs30).all()), f"{len(s)} blok, {len(h)} hücre, {h.uavt.nunique()} mahalle")
h.to_parquet(CIKTI / "istanbul_hucre.parquet", index=False)
s.to_parquet(CIKTI / "istanbul_saha.parquet", index=False)
print(h[["yapili_2020", "pay_1990", "yapilasma_yili", "yukseklik_m"]].describe().round(3).to_string())
