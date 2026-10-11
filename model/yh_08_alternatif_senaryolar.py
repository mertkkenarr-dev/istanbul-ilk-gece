"""Alternatif Marmara kırılmaları: yh_03 ile aynı makine (8 GMPE mantık ağacı, BJ08 + LMC korelasyonlu 1.000 alan, 3σ kırpma),
farklı kırılma. Neden: İstanbul tahminindeki en büyük epistemik belirsizlik hangi parçanın, ne büyüklükte kırılacağıdır;
İBB/KOERI tek senaryo (Orta Marmara, Mw 7,5) kullanır.

  dogu    Orta Marmara'nın doğu yarısı (Kumburgaz → Adalar, 28,6° D sonrası) + Çınarcık (ME_TRCS012'nin 29,9° D'ye kadarki batı kesimi;
          1999'da kırılmadı). Anadolu yakası kıyısına en yakın kırılma. ~110 km × 15 km.
  buyuk   Ganos açığı (ME_TRCS996'nın 27,5° D sonrası) + Orta Marmara + Çınarcık: "tüm Marmara" kırılması. ~230 km.
Büyüklük Wells & Coppersmith (1994) doğrultu atımlı yüzey kırılma uzunluğu bağıntısıyla: Mw = 5,16 + 1,12·log10(L km); Orta Marmara
(~105 km) için 7,4 verir, KOERI'nin 7,5 seçimiyle tutarlı (alan bağıntısı ince-uzun Marmara fayında büyüklüğü ~0,3 düşük verir).
Çıktı: data/processed/yer_hareketi/senaryo_alanlar_{ad}.npz (yh_03 ile aynı biçim), sure_ds595_{ad}.npy
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from openquake.hazardlib.geo import Line, Point
from yh_07_sure import ln_ds
from yh_korelasyon import LMC
from yh_ortak import CIKTI, GMPE, IMT_SENARYO, KOK, kirilma, medyan_sigma, sahalar

E = 1000
F = json.loads((KOK / "data/raw/external/gem_marmara_faults.geojson").read_text())["features"]
iz = {f["properties"]["catalog_id"]: [tuple(c) for c in f["geometry"]["coordinates"]] for f in F}
SENARYO = {
    "dogu": [c for c in iz["ME_TRCS013"] if c[0] >= 28.6] + [c for c in iz["ME_TRCS012"] if c[0] <= 29.9],
    "buyuk": [c for c in iz["ME_TRCS996"] if c[0] >= 27.5] + iz["ME_TRCS013"] + [c for c in iz["ME_TRCS012"] if c[0] <= 29.9],
}


def uzunluk(nokta: list[tuple[float, float]]) -> float:
    return float(Line([Point(x, y) for x, y in nokta]).get_length())


if __name__ == "__main__":
    ad = sys.argv[1]
    nok = SENARYO[ad]
    L = uzunluk(nok); mw = round(5.16 + 1.12 * np.log10(L), 1)
    print(f"{ad}: iz {L:.0f} km, Mw {mw}")
    s = pd.read_parquet(CIKTI / "sahalar.parquet")
    kisa = list(GMPE)
    w = pd.Series(json.loads((CIKTI / "mantik_agaci.json").read_text())["agirlik"])[kisa].values
    rup = kirilma(nok, mw, 0.0, 15.0)
    mu, sig, tau, phi, ctx = medyan_sigma(kisa, rup, sahalar(s.lon, s.lat, s.vs30), IMT_SENARYO)
    rng = np.random.default_rng({"dogu": 731, "buyuk": 778}[ad])
    adet = np.floor(w * E).astype(int); adet[np.argsort(-(w * E - adet))[: E - adet.sum()]] += 1
    gidx = rng.permutation(np.repeat(np.arange(len(kisa)), adet))
    lmc = LMC(IMT_SENARYO, s.lon.values, s.lat.values)
    eps = lmc.ornekle(E, rng)
    eta = rng.multivariate_normal(np.zeros(len(IMT_SENARYO)), lmc.C0, size=E)
    lnY = mu[gidx] + tau[gidx] * eta[:, :, None] + phi[gidx] * eps
    lnY = np.minimum(lnY, mu[gidx] + 3 * sig[gidx]).astype(np.float32)
    np.savez_compressed(CIKTI / f"senaryo_alanlar_{ad}.npz", ln_sa=lnY, gmpe_idx=gidx, eta=eta.astype(np.float32),
                        imts=np.array(IMT_SENARYO), gmpe=np.array(kisa), saha_id=s.saha_id.values, mw=mw, iz_km=L)
    mah = (s.tip == "mahalle").values
    m = s[mah]
    mm = pd.read_parquet(KOK / "data/processed/mahalle.parquet", columns=["uavt"]).uavt.values
    m = m.set_index(m.kaynak_id.astype(int)).loc[mm]
    np.save(CIKTI / f"sure_ds595_{ad}.npy", ln_ds(rup, m.lon, m.lat, m.vs30))
    pga = np.exp(lnY[:, 0, mah])
    print(f"mahalle PGA medyanı {np.median(pga):.3f} g, %95 {np.percentile(pga, 95):.3f} g; Rjb {ctx.rjb[mah].min():.1f}–{ctx.rjb[mah].max():.1f} km")
