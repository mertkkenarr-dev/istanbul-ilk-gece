"""Mw 7,5 Marmara senaryosu: mantık ağacı + korelasyonlu Monte Carlo yer hareketi alanları.

Girdi : sahalar.parquet (yh_03a), gmpe_skor.json (yh_01), izmit_skor.json (yh_02), GEM ME_TRCS013 fay izi
Çıktı : data/processed/yer_hareketi/senaryo_medyan.parquet  (saha × GMPE × IMT ln medyan, τ, φ)
        data/processed/yer_hareketi/senaryo_alanlar.npz      (E × M × N ln Sa, olay başına GMPE ve η)
        data/processed/yer_hareketi/mantik_agaci.json

Kaynak: KOERI/İBB senaryosuyla karşılaştırılabilir olsun diye aynı büyüklük (Mw 7,5) ve aynı kesim: Ana Marmara Fayı'nın
kırılmamış orta kesimi (GEM EMME ME_TRCS013, Orta Marmara Çukuru → Adalar). Düşey, sağ yanal; sismojenik taban 15 km (GEM).
Not: 105 km × 15 km alan Leonard (2010) ile ~Mw 7,2'ye karşılık gelir; Mw 7,5 KOERI'nin tercihidir, alternatif kaynaklar
duyarlılık analizinde ayrı senaryo olarak koşulur.

Belirsizlik katmanları: epistemik (hangi GMPE: olay başına ağırlıkla örneklenir), olaylar arası η (BJ08 korelasyonlu, τ),
olay içi ε (LMC ile uzamsal + periyotlar arası korelasyonlu, φ). Her sahada ln Sa, μ + 3σ_toplam'da kırpılır.
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd
from yh_korelasyon import LMC
from yh_ortak import CIKTI, GMPE, IMT_SENARYO, KOK, kirilma, medyan_sigma, sahalar

E = 1000
TOHUM = 72
rng = np.random.default_rng(TOHUM)

# ---------------- mantık ağacı ağırlıkları: iki depremin LLH ortalaması ----------------
s25 = json.loads((CIKTI / "gmpe_skor.json").read_text())["llh"]
s99 = {k: v["llh"] for k, v in json.loads((CIKTI / "izmit_skor.json").read_text())["sonuc"]["7.4"].items()}
llh = pd.DataFrame({"silivri2025": s25, "izmit1999": s99})
llh["ortalama"] = llh.mean(axis=1)
w = 2.0 ** (-llh.ortalama); w /= w.sum()
llh["agirlik"] = w
print(llh.round(3).sort_values("agirlik", ascending=False))

# ---------------- kırılma ve medyanlar ----------------
iz = json.loads((KOK / "data/raw/external/gem_marmara_faults.geojson").read_text())["features"][1]
assert iz["properties"]["catalog_id"] == "ME_TRCS013"
rup = kirilma([tuple(c) for c in iz["geometry"]["coordinates"]], 7.5, 0.0, 15.0)
s = pd.read_parquet(CIKTI / "sahalar.parquet")
kisa = list(GMPE)
t0 = time.time()
mu, sig, tau, phi, ctx = medyan_sigma(kisa, rup, sahalar(s.lon, s.lat, s.vs30), IMT_SENARYO)
print(f"medyanlar: {mu.shape} ({time.time() - t0:.0f} sn); Rjb {ctx.rjb.min():.1f}–{ctx.rjb.max():.1f} km")
uzun = []
for g, k in enumerate(kisa):
    for m, imt in enumerate(IMT_SENARYO):
        uzun.append(pd.DataFrame(dict(saha_id=s.saha_id, gmpe=k, imt=imt, ln_medyan=mu[g, m], tau=tau[g, m], phi=phi[g, m])))
med = pd.concat(uzun)
med.to_parquet(CIKTI / "senaryo_medyan.parquet", index=False)
pd.DataFrame(dict(saha_id=s.saha_id, rjb_km=ctx.rjb, rrup_km=ctx.rrup)).to_parquet(CIKTI / "senaryo_mesafe.parquet", index=False)

# ---------------- Monte Carlo ----------------
# GMPE seçimi tabakalı: her model tam olarak round(w·E) olayda kullanılır (rastgele seçimin örnekleme gürültüsü yok)
adet = np.floor(w.values * E).astype(int)
adet[np.argsort(-(w.values * E - adet))[: E - adet.sum()]] += 1
gmpe_idx = rng.permutation(np.repeat(np.arange(len(kisa)), adet))
lmc = LMC(IMT_SENARYO, s.lon.values, s.lat.values)
t0 = time.time()
eps_w = lmc.ornekle(E, rng)                                   # (E, M, N)
eta = rng.multivariate_normal(np.zeros(len(IMT_SENARYO)), lmc.C0, size=E)  # (E, M)
lnY = (mu[gmpe_idx] + tau[gmpe_idx] * eta[:, :, None] + phi[gmpe_idx] * eps_w).astype(np.float32)
ust = mu[gmpe_idx] + 3 * sig[gmpe_idx]
kirpilan = float((lnY > ust).mean())
lnY = np.minimum(lnY, ust).astype(np.float32)
print(f"alanlar: {lnY.shape} ({time.time() - t0:.0f} sn); 3σ kırpılan oran {kirpilan:.5f}")
np.savez_compressed(CIKTI / "senaryo_alanlar.npz", ln_sa=lnY, gmpe_idx=gmpe_idx, eta=eta.astype(np.float32),
                    imts=np.array(IMT_SENARYO), gmpe=np.array(kisa), saha_id=s.saha_id.values)

# ---------------- özet ve kontroller ----------------
mah = (s.tip == "mahalle").values
pga = np.exp(lnY[:, 0, :][:, mah])
agirlikli_medyan = np.exp((w.values[:, None] * mu[:, 0, mah]).sum(0))
ozet = dict(kaynak=dict(iz="GEM ME_TRCS013", mw=7.5, ust_km=0, alt_km=15, egim=90, rake=180),
            olay_sayisi=E, tohum=TOHUM, kirpilan_oran=kirpilan, imts=IMT_SENARYO,
            agirlik=w.round(4).to_dict(), llh=llh.round(4).to_dict(),
            korelasyon=dict(model="LMC: BJ08 periyotlar arası + JB09 (Vs30 kümelenmeli) uzamsal", bilesen_menzil_km=lmc.b_bilesen.round(1).tolist()),
            pga_mahalle=dict(agirlikli_medyan_medyani=float(np.median(agirlikli_medyan)), agirlikli_medyan_maks=float(agirlikli_medyan.max()),
                             mc_p50=float(np.median(pga)), mc_p95=float(np.percentile(pga, 95))),
            olay_ortalamasi_pga=dict(p5=float(np.percentile(pga.mean(1), 5)), p50=float(np.median(pga.mean(1))), p95=float(np.percentile(pga.mean(1), 95))))
(CIKTI / "mantik_agaci.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1))
print(json.dumps({k: ozet[k] for k in ("pga_mahalle", "olay_ortalamasi_pga")}, indent=1))
for g, k in enumerate(kisa):
    print(f"  {k:7s} mahalle PGA medyanı {np.exp(np.median(mu[g, 0, mah])):.3f} g, maks {np.exp(mu[g, 0, mah].max()):.3f} g, olay {int((gmpe_idx == g).sum())}")
