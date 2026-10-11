"""8 aday GMPE'yi 23.04.2025 Silivri Mw 6,2 kayıtlarıyla sınar ve mantık ağacı ağırlıklarını verilerden türetir.

Girdi : data/raw/usgs_silivri_2025/stationlist.json (81 ivmeölçer), gem_marmara_faults.geojson (doğrultu için)
Çıktı : data/processed/yer_hareketi/silivri_rezidu.parquet  (istasyon × GMPE × IMT)
        data/processed/yer_hareketi/gmpe_skor.json          (olay terimi, φ, LLH, ağırlık, eğilim testleri)

Yöntem
- Gözlem: iki yatay bileşenin geometrik ortalaması. ShakeMap'in 'pga' alanı yatayların en büyüğüdür; GMPE'ler ise
  geometrik ortalama / RotD50 tahmin eder. En büyük yatay kullanılsaydı her model ~%15 düşük tahmin ediyor görünürdü.
- Rezidü r = ln(gözlem) − ln(medyan). Tek deprem olduğundan olay terimi kapalı formla (Abrahamson & Youngs 1992):
  η = τ² Σr / (nτ² + φ²); olay içi rezidü δW = r − η.
- Sıralama: LLH (Scherbaum, Delavaud & Riggelsen 2009) = −(1/N) Σ log2 f(x_i), f modelin toplam sigmalı normal yoğunluğu.
  Ağırlık w_k ∝ 2^(−LLH_k). Düşük LLH = veriye daha yakın ve sigması dürüst model.
- Kapsam sınırı: tek olay, M 6,2. Mesafe sönümünü ve zemin ölçeklemesini Marmara'da sınar; M 7,5'e büyüklük ölçeklemesini
  sınamaz (o, modellerin kendi veri setlerinden gelir). Bu yüzden ağırlıklar bilgilendirici ama tek başına karar verici değil.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import statsmodels.api as sm
from openquake.hazardlib.geo import Point
from scipy.stats import norm
from yh_ortak import CIKTI, GMPE, IMT_DOGRULAMA, KOK, iz_yonu, kirilma, medyan_sigma, sahalar

USGS = KOK / "data" / "raw" / "usgs_silivri_2025"
EPI = (28.1897, 40.8342, 12.7); MW = 6.2
GEN = {"PGA": "pga", "SA(0.3)": "sa(0.3)", "SA(1.0)": "sa(1.0)", "SA(3.0)": "sa(3.0)"}

# ---------------- gözlemler ----------------
rows = []
for f in json.loads((USGS / "stationlist.json").read_text())["features"]:
    p = f["properties"]
    if p.get("station_type") != "seismic":
        continue
    yatay = {}
    for ch in p["channels"]:
        if ch["name"][-1] in "Z":
            continue
        for a in ch["amplitudes"]:
            if a["flag"] == "0" and a["value"] not in (None, "null") and float(a["value"]) > 0:
                yatay.setdefault(a["name"], []).append(float(a["value"]))
    r = dict(kod=p["code"], ag=p["network"], lon=f["geometry"]["coordinates"][0], lat=f["geometry"]["coordinates"][1], vs30=p["vs30"])
    for imt, ad in GEN.items():
        v = yatay.get(ad, [])
        r[imt] = np.exp(np.mean(np.log(v))) / 100 if len(v) == 2 else np.nan  # %g -> g, iki yatayın geometrik ortalaması
    rows.append(r)
obs = pd.DataFrame(rows)
print(f"istasyon: {len(obs)}, iki yatay bileşeni tam olan: {int(obs.PGA.notna().sum())}")

# ---------------- kırılma: Wells & Coppersmith (1994) doğrultu atımlı, düşey ----------------
iz = np.array(json.loads((KOK / "data/raw/external/gem_marmara_faults.geojson").read_text())["features"][1]["geometry"]["coordinates"])
az = iz_yonu(iz, EPI[0], EPI[1])
L = 10 ** (-2.57 + 0.62 * MW); W = 10 ** (-0.76 + 0.27 * MW)
e = Point(*EPI[:2]); a, b = e.point_at(L / 2, 0, az + 180), e.point_at(L / 2, 0, az)
rup = kirilma([(a.longitude, a.latitude), (b.longitude, b.latitude)], MW, EPI[2] - W / 2, EPI[2] + W / 2, hipo=EPI)
print(f"kırılma: doğrultu {az:.0f}°, L={L:.1f} km, W={W:.1f} km")

sc = sahalar(obs.lon, obs.lat, obs.vs30)
kisa = list(GMPE)
mu, sig, tau, phi, ctx = medyan_sigma(kisa, rup, sc, IMT_DOGRULAMA)
obs["rjb"] = ctx.rjb; obs["rrup"] = ctx.rrup
menzil = obs.rjb <= 200
print(f"Rjb ≤ 200 km (GMPE geçerlilik aralığı): {int(menzil.sum())}")

# ---------------- rezidüler ----------------
uzun, skor = [], []
for g, k in enumerate(kisa):
    for m, imt in enumerate(IMT_DOGRULAMA):
        ok = (menzil & obs[imt].notna()).values
        r = np.log(obs[imt].values[ok]) - mu[g, m, ok]
        t, p_, s = tau[g, m, ok].mean(), phi[g, m, ok].mean(), sig[g, m, ok]
        n = len(r)
        eta = t**2 * r.sum() / (n * t**2 + p_**2)
        dw = r - eta
        llh = -np.mean(np.log2(norm.pdf(r, 0, s)))
        X = sm.add_constant(np.c_[np.log(obs.rjb.values[ok] + 1), np.log(obs.vs30.values[ok])])
        fit = sm.OLS(dw, X).fit()
        skor.append(dict(gmpe=k, oq=GMPE[k], imt=imt, n=n, ort_rezidu=float(r.mean()), olay_terimi=float(eta),
                         olay_terimi_norm=float(eta / t), phi_model=float(p_), phi_gozlenen=float(dw.std(ddof=1)),
                         sigma_model=float(s.mean()), llh=float(llh),
                         egim_lnrjb=float(fit.params[1]), p_lnrjb=float(fit.pvalues[1]),
                         egim_lnvs30=float(fit.params[2]), p_lnvs30=float(fit.pvalues[2])))
        uzun.append(pd.DataFrame(dict(kod=obs.kod.values[ok], gmpe=k, imt=imt, rjb=obs.rjb.values[ok], vs30=obs.vs30.values[ok],
                                      gozlem=obs[imt].values[ok], tahmin=np.exp(mu[g, m, ok]), rezidu=r, olay_ici=dw)))
skor = pd.DataFrame(skor)

# ---------------- ağırlıklar: IMT'ler üzerinden ortalama LLH ----------------
llh = skor.groupby("gmpe").llh.mean()
w = 2.0 ** (-llh); w = w / w.sum()
skor["agirlik_gmpe"] = skor.gmpe.map(w)
pd.concat(uzun).to_parquet(CIKTI / "silivri_rezidu.parquet", index=False)
obs.to_parquet(CIKTI / "silivri_gozlem.parquet", index=False)
ozet = dict(olay=dict(mw=MW, epi=EPI, dogrultu=az, L_km=L, W_km=W, istasyon=int(menzil.sum())),
            llh=llh.round(4).to_dict(), agirlik=w.round(4).to_dict(), skor=skor.round(4).to_dict(orient="records"))
(CIKTI / "gmpe_skor.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1))

pd.set_option("display.width", 200)
print(skor.pivot(index="gmpe", columns="imt", values="olay_terimi").round(2).assign(LLH=llh.round(3), w=w.round(3)).sort_values("LLH"))
print("\nOlay içi eğilim (ln Rjb eğimi; p<0,05 ise mesafe sönümü bölgeye uymuyor):")
print(skor.pivot(index="gmpe", columns="imt", values="egim_lnrjb").round(2))
print(skor.pivot(index="gmpe", columns="imt", values="p_lnrjb").round(3))

# ---------------- duyarlılık: olay terimi kaynak belirsizliğine ne kadar bağlı? ----------------
# Ajanslar arası Mw farkı (USGS 6,2; İTÜ 6,3), derinlik (USGS 12,7; Kandilli ~10 km) ve kırılma boyu (W&C ±1σ ≈ ×/÷1,5)
durumlar = {"temel": (MW, EPI[2], 1.0), "Mw 6,3": (6.3, EPI[2], 1.0), "Mw 6,1": (6.1, EPI[2], 1.0),
            "derinlik 10 km": (MW, 10.0, 1.0), "kırılma ×1,5": (MW, EPI[2], 1.5), "kırılma ÷1,5": (MW, EPI[2], 1 / 1.5)}
ok = (menzil & obs.PGA.notna()).values
duy = []
for ad, (mw, z, carpan) in durumlar.items():
    Lx = 10 ** (-2.57 + 0.62 * mw) * carpan; Wx = min(10 ** (-0.76 + 0.27 * mw) * carpan, 2 * z)
    a2, b2 = e.point_at(Lx / 2, 0, az + 180), e.point_at(Lx / 2, 0, az)
    r2 = kirilma([(a2.longitude, a2.latitude), (b2.longitude, b2.latitude)], mw, max(z - Wx / 2, 0), z + Wx / 2, hipo=(EPI[0], EPI[1], z))
    m2, s2, t2, p2, _ = medyan_sigma(kisa, r2, sahalar(obs.lon[ok], obs.lat[ok], obs.vs30[ok]), ["PGA", "SA(1.0)"])
    for g, k in enumerate(kisa):
        for mm, imt in enumerate(["PGA", "SA(1.0)"]):
            o_ = obs[imt].values[ok]; v = np.isfinite(o_)
            r = np.log(o_[v]) - m2[g, mm, v]; t, pp = t2[g, mm, v].mean(), p2[g, mm, v].mean()
            duy.append(dict(durum=ad, gmpe=k, imt=imt, olay_terimi=t**2 * r.sum() / (len(r) * t**2 + pp**2)))
duy = pd.DataFrame(duy)
duy.to_parquet(CIKTI / "silivri_duyarlilik.parquet", index=False)
print("\nOlay terimi (PGA) kaynak varsayımlarına göre:")
print(duy[duy.imt == "PGA"].pivot(index="gmpe", columns="durum", values="olay_terimi").round(2))
