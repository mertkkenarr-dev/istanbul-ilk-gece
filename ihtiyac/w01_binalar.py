"""Web 3B bina katmanı: Esenyurt ve komşu ilçelerin Overture bina tabanları, yükseklikle, PMTiles olarak.

Yükseklik (öncelik sırası; her binada `kaynak` alanı hangisinin kullanıldığını söyler):
  overture_yukseklik  Overture `height` (m)                                            GÖZLEM (lidar/OSM etiketi)
  overture_kat        Overture `num_floors` × 3 m                                       GÖZLEM
  ml                  LightGBM kat tahmini (ml/ml_04_bina_kat.py): ilçe dışı sınamada sınıf isabeti %67, ortalama hata 1,7 kat   MODEL
  tahmin              (ML tahmini yoksa) İBB 2017 mahalle kat dağılımı (1–4 / 5–9 / 9+) taban alanı sırasına göre dağıtılır: mahallenin en büyük
                      tabanlı binaları en yüksek sınıfa düşer (site blokları geniş, müstakil evler küçük tabanlı). Sınıf içinde kat
                      sayısı taban alanı sırasıyla doğrusal: 1–4 → 1..4, 5–9 → 5..8, 9+ → 9..15. Kat yüksekliği 3 m.   VARSAYIM
  < 30 m² taban       1 kat (kulübe, trafo, depo)
Bu bir görselleştirme katmanıdır; hasar ve ihtiyaç hesaplarına girmez (onlar İBB sınıf sayılarını kullanır).
Çıktı: data/processed/web_tiles/binalar.pmtiles (katman "bina": h, kaynak, uavt, turgut), binalar.parquet
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import wkb

KOK = Path(__file__).resolve().parents[1]
P = KOK / "data/processed"; OUT = P / "web_tiles"; OUT.mkdir(exist_ok=True)
ILCELER = ["ESENYURT", "AVCILAR", "BEYLİKDÜZÜ", "KÜÇÜKÇEKMECE", "BÜYÜKÇEKMECE", "BAŞAKŞEHİR"]
TURGUT = 181502
KAT_ARALIK = {0: (1, 4), 1: (5, 8), 2: (9, 15)}


def tahmini_kat(d: pd.DataFrame, pay: np.ndarray) -> np.ndarray:
    """d: bir mahallenin binaları (taban_m2), pay: İBB [1–4, 5–9, 9+] oranları. Büyük taban → yüksek sınıf."""
    n = len(d)
    sira = np.argsort(-d.taban_m2.values)                    # büyükten küçüğe
    sinir = np.round(np.cumsum(pay[::-1]) * n).astype(int)   # 9+, 5–9, 1–4 sırasıyla kümülatif
    kat = np.empty(n)
    bas = 0
    for sinif, son in zip((2, 1, 0), sinir, strict=True):
        ix = sira[bas:son]
        lo, hi = KAT_ARALIK[sinif]
        if len(ix):
            kat[ix] = np.round(np.linspace(hi, lo, len(ix)))
        bas = son
    kat[sira[bas:]] = 1
    return kat


if __name__ == "__main__":
    m = pd.read_parquet(P / "mahalle.parquet", columns=["uavt", "ilce", "kat_1_4", "kat_5_9", "kat_9_19"])
    sinir = gpd.read_parquet(P.parent / "interim/mahalle_sinir.parquet")[["uavt", "geometry"]].merge(m, on="uavt")
    sinir = sinir[sinir.ilce.isin(ILCELER)].to_crs(4326)
    x0, y0, x1, y1 = sinir.total_bounds
    b = pd.read_parquet(P.parent / "interim/bina_istanbul.parquet", columns=["id", "lon", "lat", "taban_m2", "height", "num_floors", "geom_wkb"])
    b = b[b.lon.between(x0, x1) & b.lat.between(y0, y1)]
    g = gpd.GeoDataFrame(b, geometry=gpd.points_from_xy(b.lon, b.lat), crs=4326)
    g = gpd.sjoin(g, sinir[["uavt", "geometry"]], predicate="within").drop(columns="index_right")
    g = g[~g.index.duplicated()]
    kat = np.full(len(g), np.nan)
    pay = m.set_index("uavt")[["kat_1_4", "kat_5_9", "kat_9_19"]]
    pay = pay.div(pay.sum(1).replace(0, np.nan), axis=0).fillna(1 / 3)
    g = g.reset_index(drop=True)
    for u, d in g.groupby("uavt"):
        kat[d.index] = tahmini_kat(d, pay.loc[u].values)
    ml = pd.read_parquet(P / "ml/bina_kat.parquet").set_index("id").kat_ml          # ml/ml_04: ilçe dışı sınıf isabeti %67 (kural %59)
    kat_ml = g.id.map(ml)
    g["h"] = np.where(kat_ml.notna(), kat_ml, kat) * 3.0
    g["kaynak"] = np.where(kat_ml.notna(), "ml", "tahmin")
    nf = g.num_floors.notna() & (g.num_floors > 0)
    g.loc[nf, "h"] = g.loc[nf, "num_floors"] * 3.0; g.loc[nf, "kaynak"] = "overture_kat"
    hh = g.height.notna() & (g.height > 2)
    g.loc[hh, "h"] = g.loc[hh, "height"]; g.loc[hh, "kaynak"] = "overture_yukseklik"
    kucuk = g.taban_m2 < 30
    g.loc[kucuk & g.kaynak.isin(["tahmin", "ml"]), "h"] = 3.0
    g["h"] = g.h.round(1)
    g["turgut"] = (g.uavt == TURGUT).astype(int)
    geo = gpd.GeoSeries([wkb.loads(x) for x in g.geom_wkb], crs=4326)
    out = gpd.GeoDataFrame(g[["h", "kaynak", "uavt", "turgut"]], geometry=geo, crs=4326)
    seq = OUT / "binalar.geojsonseq"
    out.to_parquet(OUT / "binalar.parquet")                       # önizleme ve doğrulama için
    out.to_file(seq, driver="GeoJSONSeq")
    subprocess.run(["tippecanoe", "-fo", str(OUT / "binalar.pmtiles"), "-l", "bina", "-Z12", "-z16", "--drop-densest-as-needed",
                    "--extend-zooms-if-still-dropping", "-P", str(seq)], check=True, capture_output=True)
    seq.unlink()
    print(f"{len(out):,} bina; kaynak: {out.kaynak.value_counts().to_dict()}")
    t = out[out.turgut == 1]
    print(f"Turgut Özal: {len(t)} bina, yükseklik medyan {t.h.median():.0f} m, 9+ kat (≥27 m) {int((t.h >= 27).sum())}")
    print(f"PMTiles {(OUT / 'binalar.pmtiles').stat().st_size / 1e6:.1f} MB")
