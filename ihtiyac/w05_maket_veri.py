"""Harita maketi için enlem-boylamlı odak verisi: Turgut Özal sınırı ve merkezi, Esenyurt merkezi, yakın büyük hastaneler, kamp alanı.
hikaye.json yerel km düzleminde; MapLibre/deck.gl WGS84 ister. Çıktı: data/processed/web_tiles/maket.json
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import mapping

KOK = Path(__file__).resolve().parents[1]
P = KOK / "data/processed"; T = P / "web_tiles"
TURGUT = 181502

if __name__ == "__main__":
    m = pd.read_parquet(P / "mahalle.parquet", columns=["uavt", "ilce"])
    s = gpd.read_parquet(P.parent / "interim/mahalle_sinir.parquet")[["uavt", "geometry"]].merge(m, on="uavt").to_crs(4326)
    tg = s[s.uavt == TURGUT].geometry.iloc[0]
    es = s[s.ilce == "ESENYURT"].union_all()
    tm = gpd.GeoSeries([tg], crs=4326).to_crs(32635).iloc[0]
    h = json.loads((T / "hikaye.json").read_text())
    hs = gpd.read_parquet(P / "hastane.parquet").to_crs(32635).merge(m, on="uavt", how="left")
    hs["km"] = hs.distance(tm.centroid) / 1000
    yakin = hs[(hs.km < 11) & (hs.yatak_tahmini >= 100)].to_crs(4326).sort_values("km")
    veri = dict(
        turgut=dict(sinir=mapping(tg.simplify(0.00005)), merkez=[round(tg.centroid.x, 5), round(tg.centroid.y, 5)]),
        esenyurt=dict(sinir=mapping(es.simplify(0.0003)), merkez=[round(es.centroid.x, 5), round(es.centroid.y, 5)]),
        hastane=[dict(ad=r.ad, ilce=str(r.ilce).title(), km=round(float(r.km), 1), yatak=int(r.yatak_tahmini), lonlat=[round(r.geometry.x, 5), round(r.geometry.y, 5)])
                 for r in yakin.itertuples()],
        kamp_m2=h["barinma"]["kamp_m2"], mevcut_m2=h["turgut"]["toplanma_m2"], barinma_kisi=h["barinma"]["kisi"])
    (T / "maket.json").write_text(json.dumps(veri, ensure_ascii=False, separators=(",", ":")))
    print(veri["turgut"]["merkez"], veri["esenyurt"]["merkez"], len(veri["hastane"]))
