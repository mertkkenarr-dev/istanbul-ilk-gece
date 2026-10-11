"""Yer hareketinin hesaplanacağı sahalar: mahalle erişim noktaları, hastaneler, itfaiye birimleri, köprü/viyadük/tünel.

Ana ortamda (.venv) çalışır; Vs30 rasterını burada örnekler, OpenQuake ortamı yalnızca bu tabloyu okur.
Çıktı: data/processed/yer_hareketi/sahalar.parquet (saha_id, tip, kaynak_id, lon, lat, vs30)
"""
from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from ortak import CRS_METRIK, INTERIM, PROCESSED  # noqa: E402

CIKTI = PROCESSED / "yer_hareketi"; CIKTI.mkdir(exist_ok=True)
m = pd.read_parquet(PROCESSED / "mahalle.parquet", columns=["uavt", "lon_bina", "lat_bina", "vs30"])
parca = [pd.DataFrame(dict(tip="mahalle", kaynak_id=m.uavt.astype(str), lon=m.lon_bina, lat=m.lat_bina, vs30=m.vs30))]
for tip, dosya, kimlik in (("hastane", "hastane", None), ("itfaiye", "itfaiye", None), ("sanat_yapisi", "sanat_yapisi", "ID")):
    g = gpd.read_parquet(PROCESSED / f"{dosya}.parquet")
    p = g.to_crs(CRS_METRIK).geometry.interpolate(0.5, normalized=True) if tip == "sanat_yapisi" else g.to_crs(CRS_METRIK).geometry
    p = gpd.GeoSeries(p, crs=CRS_METRIK).to_crs(4326)
    parca.append(pd.DataFrame(dict(tip=tip, kaynak_id=(g[kimlik].astype(str) if kimlik else pd.Series(range(len(g))).astype(str)).values,
                                   lon=p.x.values, lat=p.y.values, vs30=np.nan)))
s = pd.concat(parca, ignore_index=True)
with rasterio.open(INTERIM / "vs30_istanbul.tif") as r:
    v = np.array([x[0] for x in r.sample(np.c_[s.lon, s.lat])], dtype=float)
v[(v == 600.0) | ~np.isfinite(v)] = np.nan
bos = s.vs30.isna()
s.loc[bos, "vs30"] = v[bos.values]
# Kıyıdaki tesis rasterın su hücresine düşerse en yakın mahallenin Vs30'u (köprü ayakları çoğunlukla kıyıda)
eksik = s.vs30.isna()
if eksik.any():
    mm = gpd.GeoDataFrame(m, geometry=gpd.points_from_xy(m.lon_bina, m.lat_bina), crs=4326).to_crs(CRS_METRIK)
    q = gpd.GeoDataFrame(s[eksik], geometry=gpd.points_from_xy(s.lon[eksik], s.lat[eksik]), crs=4326).to_crs(CRS_METRIK)
    s.loc[eksik, "vs30"] = gpd.sjoin_nearest(q, mm[["vs30", "geometry"]].rename(columns={"vs30": "v_m"})).groupby(level=0).v_m.first()
s.insert(0, "saha_id", range(len(s)))
s.to_parquet(CIKTI / "sahalar.parquet", index=False)
print(s.groupby("tip").agg(n=("saha_id", "size"), vs30_med=("vs30", "median")), f"\nVs30 eksik: {int(s.vs30.isna().sum())}, en yakından doldurulan: {int(eksik.sum())}")
