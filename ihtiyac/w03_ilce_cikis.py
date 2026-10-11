"""Web ilçe çıkışı katmanı: Esenyurt sınırından dışarı yönlenen ana yollar (otoyol, trunk, ana, ikincil), şerit sayısı ve kapasite;
Esenyurt sınırı; araç talebi aralığı. Kapasite varsayımları i04 ile aynı (otoyol 1.800, trunk 1.500, ana 900, ikincil 800 araç/sa/şerit).
Çıktı: data/processed/web_tiles/ilce_cikis.json
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point, mapping

KOK = Path(__file__).resolve().parents[1]
P = KOK / "data/processed"; OUT = P / "web_tiles"
SERIT = {"motorway": 3, "trunk": 3, "primary": 2, "secondary": 2}
KAP = {"motorway": 1800, "trunk": 1500, "primary": 900, "secondary": 800}

if __name__ == "__main__":
    m = pd.read_parquet(P / "mahalle.parquet", columns=["uavt", "ilce", "nufus_2025"])
    es_u = m[m.ilce == "ESENYURT"].uavt
    s = gpd.read_parquet(P.parent / "interim/mahalle_sinir.parquet")
    poly_m = s[s.uavt.isin(es_u)].to_crs(32635).union_all()
    k = gpd.read_parquet(P / "yol_kenar.parquet").to_crs(32635)
    k = k[k.sinif.isin(list(KAP)) & k.crosses(poly_m.boundary)]
    k = k[[poly_m.contains(Point(g.coords[0])) for g in k.geometry]].copy()
    k["serit"] = k.lanes.map(lambda x: pd.to_numeric(str(x).split("|")[0], errors="coerce")).fillna(k.sinif.map(SERIT))
    k["kap"] = k.serit * k.sinif.map(KAP)
    k["ad"] = k.name.fillna("").astype(str).str.split("|").str[0]
    k["geometry"] = k.geometry.intersection(poly_m.buffer(1500))      # uzun otoyol kenarları sınırdan en çok 1,5 km dışarı
    k = k[~k.geometry.is_empty & (k.geom_type == "LineString")]
    k4 = k.to_crs(4326)
    cikis = [dict(ad=r.ad, sinif=r.sinif, serit=int(r.serit), kap=int(r.kap), yol=np.round(np.asarray(g.coords), 5).tolist())
             for r, g in zip(k4.itertuples(), k4.geometry, strict=True)]
    nuf = float(m[m.ilce == "ESENYURT"].nufus_2025.sum())
    oto = 3_793_152 / float(m.nufus_2025.sum())
    veri = dict(sinir=mapping(gpd.GeoSeries([poly_m], crs=32635).to_crs(4326).simplify(0.0003).iloc[0]), cikis=cikis,
                toplam_kap=int(k.kap.sum()), arac=[round(nuf * 0.15, -3), round(nuf * oto, -3)])
    (OUT / "ilce_cikis.json").write_text(json.dumps(veri, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(cikis)} çıkış kenarı, toplam {veri['toplam_kap']:,} araç/sa; araç {veri['arac']}; "
          f"sınıf: {k.groupby('sinif').kap.sum().to_dict()}")
