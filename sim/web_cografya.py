"""Web için coğrafya: sadeleştirilmiş mahalle poligonları, ana arterler, fay izi, kara sınırı (data/processed/web_tiles/cografya.json).

Koordinatlar yerel bir metrik düzleme (UTM 35N, merkez çıkarılmış, km) çevrilir: tarayıcıda harita projeksiyonu yapılmaz,
three.js sahnesi doğrudan km biriminde çalışır. Sadeleştirme: mahalle 40 m, arter 30 m (Douglas–Peucker, topoloji korumalı).
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parent.parent
P = KOK / "data/processed"
OUT = KOK / "data/processed/web_tiles"; OUT.mkdir(parents=True, exist_ok=True)
CRS = 32635

mah = gpd.read_parquet(P / "mahalle.parquet", columns=["uavt", "ilce", "mahalle", "nufus_2025", "bina_toplam", "geometry"]).to_crs(CRS)
x0, y0 = mah.total_bounds[[0, 1]].tolist()
cx, cy = (mah.total_bounds[0] + mah.total_bounds[2]) / 2, (mah.total_bounds[1] + mah.total_bounds[3]) / 2


def tr_baslik(s: str) -> str:
    """Türkçe başlık harfi: 'KISIM' → 'Kısım', 'İSTİKLAL' → 'İstiklal' (str.title() noktasız ı'yı bilmez)."""
    kucuk = s.replace("I", "ı").replace("İ", "i").lower()
    return " ".join((w[0].replace("i", "İ").replace("ı", "I").upper() + w[1:]) if w else w for w in kucuk.split(" "))


def halka(geom, tol: float) -> list:
    g = geom.simplify(tol, preserve_topology=True)
    parca = list(g.geoms) if g.geom_type == "MultiPolygon" else [g]
    out = []
    for p in parca:
        if p.area < 2500:  # 0,25 ha altı adacıklar görünmez
            continue
        xy = np.asarray(p.exterior.coords)
        out.append(np.round(np.c_[(xy[:, 0] - cx) / 1000, (xy[:, 1] - cy) / 1000], 3).ravel().tolist())
    return out


mahalle = [dict(i=i, u=int(r.uavt), ad=tr_baslik(r.mahalle), ilce=tr_baslik(r.ilce), n=int(r.nufus_2025), b=int(r.bina_toplam),
                p=halka(r.geometry, 40)) for i, r in enumerate(mah.itertuples())]
mm = mah.representative_point()
for m, p in zip(mahalle, mm):
    m["c"] = [round((p.x - cx) / 1000, 3), round((p.y - cy) / 1000, 3)]

k = gpd.read_parquet(P / "yol_kenar.parquet", columns=["sinif", "acil_yol", "geometry"])
k = k[k.sinif.isin(["motorway", "trunk", "primary"])].to_crs(CRS)
k["geometry"] = k.geometry.simplify(30)
yol = []
for r in k.itertuples():
    xy = np.asarray(r.geometry.coords)
    yol.append(dict(s={"motorway": 0, "trunk": 1, "primary": 2}[r.sinif], a=int(r.acil_yol),
                    p=np.round(np.c_[(xy[:, 0] - cx) / 1000, (xy[:, 1] - cy) / 1000], 2).ravel().tolist()))

fay = gpd.read_file(KOK / "data/raw/external/gem_marmara_faults.geojson").to_crs(CRS)
fay = fay[fay.catalog_id.isin(["ME_TRCS013", "ME_TRCS996", "ME_TRCS012"])]
fay_xy = [np.round(np.c_[(np.asarray(g.coords)[:, 0] - cx) / 1000, (np.asarray(g.coords)[:, 1] - cy) / 1000], 2).ravel().tolist() for g in fay.geometry]
kara = gpd.read_file(P.parent / "interim/istanbul_kara.geojson").to_crs(CRS).geometry.iloc[0]

nok = pd.read_parquet(P / "sim/noktalar.parquet")
has = gpd.read_parquet(P / "sim/hastane_sim.parquet").query("~gecersiz").to_crs(CRS)
itf = gpd.read_parquet(P / "itfaiye.parquet").to_crs(CRS)
xyk = lambda g: [[round((p.x - cx) / 1000, 3), round((p.y - cy) / 1000, 3)] for p in g.geometry]
veri = dict(merkez_utm=[cx, cy], mahalle=mahalle, yol=yol, fay=fay_xy, kara=halka(kara, 60),
            hastane=[dict(xy=xy, ad=a, yatak=int(y), sektor=s) for xy, a, y, s in zip(xyk(has), has.ad, has.yatak_tahmini, has.sektor)],
            itfaiye=[dict(xy=xy, ad=a, pro=bool(p)) for xy, a, p in zip(xyk(itf), itf.ad, itf.sar_ekip_kaynagi)])
(OUT / "cografya.json").write_text(json.dumps(veri, ensure_ascii=False, separators=(",", ":")))
print(f"cografya.json {(OUT / 'cografya.json').stat().st_size / 1e6:.2f} MB; mahalle {len(mahalle)}, yol {len(yol)}, hastane {len(veri['hastane'])}")
