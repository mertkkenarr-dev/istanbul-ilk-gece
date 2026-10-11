"""Sahra hastanesi yer seçimi: hasarlı yol ağında örneklem ortalaması yaklaşımıyla (SAA) maksimum kapsama, simülasyonla sınama.

Adaylar: ≥ 1 ha açık alanlar (830). Talep d_is: s gerçekleşmesinde mahalle i'de hastane kapasitesi yetmediği için tedavi
beklerken ölen (simülatör, sahra hastanesi yok, "fayda" politikası). Kapsama: 12–24. saat yol durumunda, trafikle ≤ 45 dk.
MİP: max Σ_s Σ_i d_is·y_is ; y_is ≤ Σ_c a_ics·x_c ; Σ x_c = K ; x ∈ {0,1}, 0 ≤ y ≤ 1 (Church & ReVelle 1974; SAA: Kleywegt vd. 2002).
Sınama (örneklem DIŞI 24 gerçekleşme): 150 yataklı, 12. saatte açılan K hastane; kıyas: hiç yok, en büyük K alan,
yol ağını yok sayan kuş uçuşu (≤ 15 km) MCLP. Çıktı: data/processed/sim/sahra_*.parquet|json
Kullanım: python sim/sahra.py [işçi]
"""
from __future__ import annotations

import json
import multiprocessing as mp
import sys
import time
from dataclasses import replace
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "sim"))
OUT = KOK / "data/processed/sim"
S_EGITIM, S_TEST, K_LISTE, YATAK, ACILIS, ESIK_DK = 24, 24, (5, 10, 20), 150.0, 12.0, 45.0
_W = None


def dunya():
    global _W
    if _W is None:
        from kurulum import Dunya
        _W = Dunya()
    return _W


def adaylar() -> pd.DataFrame:
    a = gpd.read_parquet(KOK / "data/processed/toplanma_alani.parquet")
    a = a[a.alan_m2 >= 10_000].reset_index(drop=True)
    p = a.to_crs(32635).representative_point().to_crs(4326)
    i, t = dunya().ag.bagla(p.x.values, p.y.values)
    return pd.DataFrame(dict(lon=p.x.values, lat=p.y.values, alan_m2=a.alan_m2.values, tur=a.tur.values, dugum=i, yerel_sn=t))


def senaryo_kos(arg):
    """Bir gerçekleşme: yol durumu (adaylar dahil), sahra hastanesiz temel koşu; isteğe bağlı yerleşimlerle ek koşular."""
    e, yerlesimler = arg
    from parametreler import Parametre
    W = dunya(); par = replace(Parametre(), politika="fayda")
    c = adaylar()
    D = W.ag_durumu(e, par, tohum=50_000 + e, ek=c[["dugum", "yerel_sn"]])
    temel = W.kos(D, par, tohum=e)
    sonuc = dict(e=e, temel=temel["ozet"], talep=temel["mahalle"]["olu_bekleme"], mah_ek=D["ag"]["mats"][2]["mah_ek"] * 1.8)
    for ad, sec in (yerlesimler or {}).items():
        mats = [{**m, "mah_ek": m["mah_ek"][:, sec]} for m in D["ag"]["mats"]]
        r = W.kos({**D, "ag": {**D["ag"], "mats": mats}}, par, tohum=e, ek_hastane=dict(kap=np.full(len(sec), YATAK), acilis_sa=ACILIS))
        sonuc[ad] = r["ozet"]
    return sonuc


def mclp(talep: np.ndarray, kapsar: np.ndarray, K: int) -> np.ndarray:
    """talep (S, N), kapsar (S, N, C) bool → seçilen aday indeksleri."""
    S, N, C = kapsar.shape
    s_i = np.argwhere(talep > 1e-3)
    n = len(s_i)
    rows, cols = [], []
    for r, (s, i) in enumerate(s_i):
        cc = np.where(kapsar[s, i])[0]
        rows += [r] * len(cc); cols += list(cc)
    A = coo_matrix((-np.ones(len(rows)), (rows, cols)), shape=(n, C)).tocsr()
    from scipy.sparse import hstack, identity
    Ay = hstack([A, identity(n)]).tocsr()
    cobj = np.r_[np.zeros(C), -talep[s_i[:, 0], s_i[:, 1]]]
    kisit = [LinearConstraint(Ay, -np.inf, 0), LinearConstraint(np.r_[np.ones(C), np.zeros(n)][None, :], K, K)]
    res = milp(cobj, constraints=kisit, integrality=np.r_[np.ones(C), np.zeros(n)], bounds=Bounds(0, 1),
               options=dict(time_limit=300, mip_rel_gap=1e-3))
    return np.where(res.x[:C] > 0.5)[0]


def main(isci: int = 3) -> None:
    z = np.load(KOK / "data/processed/hasar/simulasyon_girdi.npz")
    tot = (z["agir"] + z["cokagir"]).sum(1); sira = np.argsort(tot)
    ust = sira[len(sira) // 2:]  # sahra hastanesinin anlamlı olduğu büyük olaylar: dağılımın üst yarısı
    rng = np.random.default_rng(4)
    sec = rng.choice(ust, S_EGITIM + S_TEST, replace=False)
    egitim, test = sec[:S_EGITIM], sec[S_EGITIM:]
    t0 = time.time()
    # spawn: ana süreç ağı yükledikten sonra fork etmek (pyarrow/BLAS iş parçacıklarıyla) macOS'ta kilitleniyordu
    with mp.get_context("spawn").Pool(isci) as h:
        eg = h.map(senaryo_kos, [(int(e), None) for e in egitim])
    print(f"eğitim senaryoları: {time.time() - t0:.0f} sn")
    c = adaylar()
    talep = np.stack([r["talep"] for r in eg]); sure = np.stack([r["mah_ek"] for r in eg]) / 60
    kapsar = sure <= ESIK_DK
    mm = pd.read_parquet(KOK / "data/processed/mahalle.parquet", columns=["lon_bina", "lat_bina"])
    dx = (mm.lon_bina.values[:, None] - c.lon.values[None]) * 84_000; dy = (mm.lat_bina.values[:, None] - c.lat.values[None]) * 111_000
    kus = np.broadcast_to(np.hypot(dx, dy) <= 15_000, kapsar.shape)
    yer = {}
    for K in K_LISTE:
        t1 = time.time()
        yer[f"mclp_ag_K{K}"] = mclp(talep, kapsar, K)
        yer[f"mclp_kus_K{K}"] = mclp(talep, kus, K)
        yer[f"en_buyuk_K{K}"] = np.argsort(-c.alan_m2.values)[:K]
        kap = (talep[:, :, None] * kapsar[:, :, yer[f"mclp_ag_K{K}"]].any(2, keepdims=True)).sum() / talep.sum()
        print(f"K={K}: MİP {time.time() - t1:.0f} sn, eğitimde kapsanan bekleme ölümü payı %{100 * kap:.0f}")
    t0 = time.time()
    with mp.get_context("spawn").Pool(isci) as h:
        ts = h.map(senaryo_kos, [(int(e), yer) for e in test])
    print(f"test senaryoları: {time.time() - t0:.0f} sn")
    satir = []
    for r in ts:
        for ad in ["temel", *yer]:
            satir.append(dict(e=r["e"], yerlesim=ad, **r[ad]))
    d = pd.DataFrame(satir); d.to_parquet(OUT / "sahra_test.parquet", index=False)
    c.assign(**{f"sec_{k}": c.index.isin(v) for k, v in yer.items()}).to_parquet(OUT / "sahra_adaylar.parquet", index=False)
    tem = d[d.yerlesim == "temel"].set_index("e").olu_toplam
    ozet = {}
    for ad in yer:
        fark = tem - d[d.yerlesim == ad].set_index("e").olu_toplam
        ozet[ad] = dict(kurtarilan_ort=float(fark.mean()), kurtarilan_se=float(fark.std(ddof=1) / np.sqrt(len(fark))),
                        bekleme_olu_ort=float(d[d.yerlesim == ad].olu_bekleme.mean()))
    ozet["temel_bekleme_olu_ort"] = float(d[d.yerlesim == "temel"].olu_bekleme.mean())
    (OUT / "sahra_ozet.json").write_text(json.dumps(dict(egitim=egitim.tolist(), test=test.tolist(), sonuc=ozet), indent=1))
    print(pd.DataFrame({k: v for k, v in ozet.items() if isinstance(v, dict)}).T.round(1))


if __name__ == "__main__":
    main(*[int(x) for x in sys.argv[1:]])
