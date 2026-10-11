"""Kalibrasyon depremleri için mahalle yer hareketi alanları: 1999 İzmit Mw 7,4 ve 2025 Silivri Mw 6,2.

Senaryoyla aynı makine (8 GMPE, LMC olay içi korelasyon), tek fark: olaylar arası terim serbest değil, her GMPE için o depremin
kayıtlarından ölçülen olay terimiyle sabitlenir (η_norm = η/τ, tüm periyotlara aynı normalize değer). Böylece kalibrasyon
"bu depremin gerçek şiddeti" üzerinden yapılır; kalan belirsizlik yalnızca olay içi (mahalle mahalle) saçılımdır.
Çıktı: data/processed/yer_hareketi/gecmis_{izmit1999,silivri2025}.npz (E × M × N, mahalle sırası mahalle.parquet ile aynı)
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from openquake.hazardlib.geo import Point
from yh_korelasyon import LMC
from yh_ortak import CIKTI, GMPE, IMT_SENARYO, KOK, iz_yonu, kirilma, medyan_sigma, sahalar

E = 400
rng = np.random.default_rng(1999)
kisa = list(GMPE)
s = pd.read_parquet(CIKTI / "sahalar.parquet"); s = s[s.tip == "mahalle"]
uavt = pd.read_parquet(KOK / "data/processed/mahalle.parquet", columns=["uavt"]).uavt.values
s = s.set_index(s.kaynak_id.astype(int)).loc[uavt]
sc = sahalar(s.lon, s.lat, s.vs30)
lmc = LMC(IMT_SENARYO, s.lon.values, s.lat.values)
w = pd.Series(json.loads((CIKTI / "mantik_agaci.json").read_text())["agirlik"])[kisa].values

# olay terimleri (normalize): 2025 tüm IMT'lerden PGA; 1999 yalnızca PGA ölçülmüş
eta25 = {r["gmpe"]: r["olay_terimi_norm"] for r in json.loads((CIKTI / "gmpe_skor.json").read_text())["skor"] if r["imt"] == "PGA"}
eta99 = {k: v["olay_terimi_norm"] for k, v in json.loads((CIKTI / "izmit_skor.json").read_text())["sonuc"]["7.4"].items()}

iz13 = np.array(json.loads((KOK / "data/raw/external/gem_marmara_faults.geojson").read_text())["features"][1]["geometry"]["coordinates"])
EPI = (28.1897, 40.8342, 12.7); az = iz_yonu(iz13, *EPI[:2])
L, W = 10 ** (-2.57 + 0.62 * 6.2), 10 ** (-0.76 + 0.27 * 6.2)
e = Point(*EPI[:2]); a, b = e.point_at(L / 2, 0, az + 180), e.point_at(L / 2, 0, az)
RUP = {
    "silivri2025": (kirilma([(a.longitude, a.latitude), (b.longitude, b.latitude)], 6.2, EPI[2] - W / 2, EPI[2] + W / 2, hipo=EPI), eta25),
    "izmit1999": (kirilma([(29.20, 40.70), (29.35, 40.72), (29.60, 40.72), (29.95, 40.73), (30.25, 40.70), (30.60, 40.68),
                           (30.95, 40.73), (31.05, 40.75)], 7.4, 0.0, 18.0, hipo=(29.97, 40.76, 17.0)), eta99),
}
for ad, (rup, eta) in RUP.items():
    mu, sig, tau, phi, ctx = medyan_sigma(kisa, rup, sc, IMT_SENARYO)
    adet = np.floor(w * E).astype(int); adet[np.argsort(-(w * E - adet))[: E - adet.sum()]] += 1
    g = rng.permutation(np.repeat(np.arange(len(kisa)), adet))
    en = np.array([eta[k] for k in kisa])[g]                       # (E,)
    lnY = mu[g] + tau[g] * en[:, None, None] + phi[g] * lmc.ornekle(E, rng)
    lnY = np.minimum(lnY, mu[g] + tau[g] * en[:, None, None] + 3 * phi[g]).astype(np.float32)
    np.savez_compressed(CIKTI / f"gecmis_{ad}.npz", ln_sa=lnY, gmpe_idx=g, imts=np.array(IMT_SENARYO), uavt=uavt)
    pga = np.exp(lnY[:, 0])
    print(f"{ad}: Rjb {ctx.rjb.min():.0f}–{ctx.rjb.max():.0f} km, mahalle PGA medyanı {np.median(pga):.3f} g, %95 {np.percentile(pga, 95):.3f} g")
