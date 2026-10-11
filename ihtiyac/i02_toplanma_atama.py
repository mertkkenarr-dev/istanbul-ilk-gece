"""İhtiyaç analizi, adım 2: ilk gece dışarı çıkan herkese yürüme mesafesinde toplanma alanında yer var mı?

Mahalle başına "alan / nüfus" oranı yanıltıcıdır: bir park birden çok mahalleye hizmet eder, insanlar yalnızca yürüme mesafesindeki
alana gidebilir. Bu yüzden kapasite kısıtlı atama (ulaştırma problemi, HiGHS):
    min Σ d_ij x_ij + M Σ u_i     s.t.  Σ_j x_ij + u_i = D_i   (blok i'nin dışarıdaki kişileri)
                                        Σ_i x_ij ≤ C_j         (alan j'nin kapasitesi)
                                        x_ij = 0, d_ij > R      (yürüme sınırı)
u_i = yer bulamayan kişi. M büyük: önce olabildiğince çok kişiye yer, sonra en kısa toplam yürüme.
Birimler
  blok   GHSL 3×3 hücre (~250 m); mahalle nüfusu bloklara yapı hacmi vekiliyle (yapılı alan × (1 + yükseklik/3 m)) dağıtılır
  alan   2.000 m²'den büyük açık alan (2.960; AFAD'ın 3.021'iyle aynı mertebe). Kullanılabilir pay türe göre (VARSAYIM):
         saha/stadyum/meydan 0,9 · park/bahçe 0,6 · kamu (okul bahçesi vb.) 0,5 · koru/orman/mesire 0,2
  kapasite kullanılabilir alan / 1,5 m² (duyarlılık: 2 m²)
  R      1.000 m yürüme ≈ 770 m kuş uçuşu (dolambaç katsayısı 1,3); duyarlılık 1.500 m
Talep: i01'in ilk gece dağılımında medyan ve %90'lık gerçekleşme (temel senaryo, İstanbul stoğu); korku_yarim: korku payı × 0,5.
Çıktı: data/processed/ihtiyac/toplanma_{durum}.parquet (mahalle), toplanma_ozet.json
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
from scipy.spatial import cKDTree

KOK = Path(__file__).resolve().parents[1]
P = KOK / "data/processed"; C = P / "ihtiyac"
PAY = {"pitch": 0.9, "stadium": 0.9, "sports_centre": 0.9, "Meydan": 0.9, "recreation_ground": 0.9, "Park": 0.6, "park": 0.6,
       "garden": 0.6, "Kamu": 0.5, "Koru": 0.2, "Kent Ormanı": 0.2, "Hatıra Ormanı": 0.2, "Mesire Alanı": 0.2, "Ağaçlandırma Sahası": 0.2}
DOLAMBAC = 1.3


def metrik(lon, lat) -> np.ndarray:
    return np.c_[np.asarray(lon) * 111_320 * np.cos(np.radians(41.05)), np.asarray(lat) * 110_540]


def bloklar() -> pd.DataFrame:
    h = pd.read_parquet(C.parent / "ders2023/istanbul_hucre.parquet")
    h["hacim"] = h.yapili_2020 * (1 + h.yukseklik_m.fillna(0) / 3)
    b = h.groupby(["blok", "uavt"]).agg(lon=("lon", "mean"), lat=("lat", "mean"), hacim=("hacim", "sum")).reset_index()
    b["pay"] = b.hacim / b.groupby("uavt").hacim.transform("sum")
    return b


def alanlar(m2_kisi: float) -> pd.DataFrame:
    t = gpd.read_parquet(P / "toplanma_alani.parquet")
    t = t[t.toplanma_uygun].copy()
    c = t.to_crs(32635).representative_point().to_crs(4326)
    t["lon"], t["lat"] = c.x.values, c.y.values
    t["kapasite"] = t.alan_m2 * t.tur.map(PAY).fillna(0.5) / m2_kisi
    return pd.DataFrame(t.drop(columns="geometry"))


def ata(b: pd.DataFrame, a: pd.DataFrame, talep: np.ndarray, R_m: float, akis: bool = False) -> tuple:
    xb, xa = metrik(b.lon, b.lat), metrik(a.lon, a.lat)
    yakin = cKDTree(xa).query_ball_point(xb, r=R_m / DOLAMBAC)
    ii = np.repeat(np.arange(len(b)), [len(y) for y in yakin]); jj = np.concatenate([np.array(y, int) for y in yakin])
    d = np.hypot(*(xb[ii] - xa[jj]).T) * DOLAMBAC
    n, nb, na = len(ii), len(b), len(a)
    c = np.r_[d / 1000.0, np.full(nb, 1e3)]                          # u_i'nin maliyeti: 1.000 km'lik yürüme eşdeğeri
    A_eq = coo_matrix((np.r_[np.ones(n), np.ones(nb)], (np.r_[ii, np.arange(nb)], np.r_[np.arange(n), n + np.arange(nb)])), shape=(nb, n + nb))
    A_ub = coo_matrix((np.ones(n), (jj, np.arange(n))), shape=(na, n + nb))
    r = linprog(c, A_ub=A_ub.tocsr(), b_ub=a.kapasite.values, A_eq=A_eq.tocsr(), b_eq=talep, bounds=(0, None), method="highs")
    if r.status != 0:
        raise RuntimeError(r.message)
    x, u = r.x[:n], r.x[n:]
    yuruyus = np.bincount(ii, weights=x * d, minlength=nb) / np.maximum(np.bincount(ii, weights=x, minlength=nb), 1e-9)
    if akis:                                                          # web akış katmanı için blok → alan atamaları (w02)
        return u, yuruyus, (ii, jj, x, d)
    return u, yuruyus


if __name__ == "__main__":
    m = pd.read_parquet(P / "mahalle.parquet", columns=["uavt", "ilce", "mahalle", "nufus_2025"])
    b = bloklar()
    z = np.load(C / "disarida_temel_ist.npz")
    tot = z["ilk_gece"].sum(1)
    olay = {"medyan": int(np.argsort(tot)[len(tot) // 2]), "p90": int(np.argsort(tot)[int(len(tot) * 0.9)])}
    mix = pd.Series(np.arange(len(m)), index=m.uavt)
    ozet = {}
    for durum, (e, m2, R) in {"medyan": (olay["medyan"], 1.5, 1000), "p90": (olay["p90"], 1.5, 1000), "medyan_2m2": (olay["medyan"], 2.0, 1000),
                              "medyan_1500m": (olay["medyan"], 1.5, 1500), "herkes": (None, 1.5, 1000), "korku_yarim": (olay["medyan"], 1.5, 1000)}.items():
        a = alanlar(m2)
        alan_adi = "ilk_gece_dusuk" if durum == "korku_yarim" else "ilk_gece"
        dis = m.nufus_2025.values.astype(float) if e is None else z[alan_adi][e].astype(float)
        talep = dis[mix[b.uavt].values] * b.pay.values
        u, yur = ata(b, a, talep, R)
        bm = pd.DataFrame({"uavt": b.uavt, "talep": talep, "yersiz": u, "yuruyus_m": yur * (talep - u)})
        mm = bm.groupby("uavt").sum().reindex(m.uavt).fillna(0)
        mm["yuruyus_m"] = mm.yuruyus_m / np.maximum(mm.talep - mm.yersiz, 1e-9)
        mm = m.set_index("uavt").join(mm).reset_index()
        mm.to_parquet(C / f"toplanma_{durum}.parquet", index=False)
        il = mm.groupby("ilce")[["talep", "yersiz"]].sum(); il["oran"] = il.yersiz / il.talep
        ozet[durum] = dict(disarida=float(talep.sum()), yersiz=float(u.sum()), yersiz_oran=float(u.sum() / talep.sum()),
                           kapasite=float(a.kapasite.sum()), en_kotu_ilce=il.sort_values("yersiz", ascending=False).head(8).round(3).reset_index().to_dict("records"))
        print(f"{durum}: dışarıda {talep.sum() / 1e6:.2f} M, yer bulamayan {u.sum() / 1e6:.2f} M (%{100 * u.sum() / talep.sum():.0f}); "
              f"toplam kapasite {a.kapasite.sum() / 1e6:.2f} M kişi", flush=True)
    (C / "toplanma_ozet.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1, default=float))
