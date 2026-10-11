"""1999 İzmit fay bölgesi hücreleri için yer hareketi alanları (yh_05 ile aynı makine, 1999 olay terimleriyle koşullu).
Çıktı: data/processed/yer_hareketi/gecmis_bolge1999.npz
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from yh_korelasyon import LMC
from yh_ortak import CIKTI, GMPE, IMT_SENARYO, KOK, kirilma, medyan_sigma, sahalar

E = 300
rng = np.random.default_rng(17081999)
kisa = list(GMPE)
h = pd.read_parquet(KOK / "data/processed/hasar/bolge1999_hucre.parquet")
w = pd.Series(json.loads((CIKTI / "mantik_agaci.json").read_text())["agirlik"])[kisa].values
eta = {k: v["olay_terimi_norm"] for k, v in json.loads((CIKTI / "izmit_skor.json").read_text())["sonuc"]["7.4"].items()}
rup = kirilma([(29.20, 40.70), (29.35, 40.72), (29.60, 40.72), (29.95, 40.73), (30.25, 40.70), (30.60, 40.68), (30.95, 40.73), (31.05, 40.75)],
              7.4, 0.0, 18.0, hipo=(29.97, 40.76, 17.0))
mu, sig, tau, phi, ctx = medyan_sigma(kisa, rup, sahalar(h.lon, h.lat, h.vs30), IMT_SENARYO)
lmc = LMC(IMT_SENARYO, h.lon.values, h.lat.values)
adet = np.floor(w * E).astype(int); adet[np.argsort(-(w * E - adet))[: E - adet.sum()]] += 1
g = rng.permutation(np.repeat(np.arange(len(kisa)), adet))
en = np.array([eta[k] for k in kisa])[g]
lnY = mu[g] + tau[g] * en[:, None, None] + phi[g] * lmc.ornekle(E, rng)
lnY = np.minimum(lnY, mu[g] + tau[g] * en[:, None, None] + 3 * phi[g]).astype(np.float32)
np.savez_compressed(CIKTI / "gecmis_bolge1999.npz", ln_sa=lnY, gmpe_idx=g, imts=np.array(IMT_SENARYO), rjb=ctx.rjb)
pga = np.exp(lnY[:, 0]); agir = np.average(np.median(pga, 0), weights=h.nufus)
print(f"bölge 1999: {len(h)} hücre, Rjb {ctx.rjb.min():.0f}–{ctx.rjb.max():.0f} km; nüfus ağırlıklı medyan PGA {agir:.3f} g")
for il_, d in h.groupby("il"):
    print(f"  {il_:8s} nüfus ağırlıklı medyan PGA {np.average(np.median(pga[:, d.index], 0), weights=d.nufus):.3f} g")
