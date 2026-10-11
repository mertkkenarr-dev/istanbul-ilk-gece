"""Mw 7,5 senaryosu hasar ve can kaybı, üç katman:

  ibb_esdegeri : KOERI kırılganlığı, deterministik ε = 0 medyan yer hareketi (İBB'nin yöntemi; sonucu yeniden üretmeli)
  ana          : 1.000 korelasyonlu yer hareketi alanı × kalibrasyon posterior topluluğu (her olayda (s_β, θ_ho, θ_ac, κ)
                 hs_03 olabilirlik ağırlığıyla örneklenir; kalibrasyon belirsizliği sonuca taşınır)
  koeri_mc     : 1.000 alan × KOERI kırılganlığı (s_β = θ = κ = 1) – duyarlılık; GM belirsizliği iki kez sayılır, üst sınır

Girdi : hasar/{envanter.parquet, kalibrasyon.parquet}, yer_hareketi/{senaryo_alanlar.npz, senaryo_medyan.parquet, mantik_agaci.json, sahalar.parquet}
Çıktı : hasar/{olay_toplamlari.parquet, mahalle_ozet.parquet, simulasyon_girdi.npz, ibb_esdegeri.parquet}
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd
from hasar_motoru import KOK, a_katsayi, cokme_orani, hasar_olasilik, kap, performans_sd, sa_periyot, yaralanma

YH = KOK / "data/processed/yer_hareketi"; HS = KOK / "data/processed/hasar"
rng = np.random.default_rng(7275)
env = pd.read_parquet(HS / "envanter.parquet")
mah = pd.read_parquet(KOK / "data/processed/mahalle.parquet")
uavt = mah.uavt.values; N = len(uavt)
saha = pd.read_parquet(YH / "sahalar.parquet")
ms = saha[saha.tip == "mahalle"].set_index(saha[saha.tip == "mahalle"].kaynak_id.astype(int)).reindex(uavt)
a = a_katsayi(ms.vs30.values)
pos = pd.Series(np.arange(N), index=uavt)
SINIF = []
for (s, t, k), g in env.groupby(["sinif", "tip", "kat"]):
    b = np.zeros(N); kk = np.zeros(N)
    b[pos[g.uavt].values] = g.bina.values; kk[pos[g.uavt].values] = g.kisi.values
    SINIF.append((s, t, k, b, kk))


def hesapla(ln: np.ndarray, per: np.ndarray, s_beta: float = 1.0, theta=1.0, kappa: float = 1.0) -> dict:
    """ln: (E, N, P) ln Sa. Dönüş: (E, N) dizileri – hasar düzeyleri, çökmüş bina/kişi, yaralı dereceleri."""
    E = ln.shape[0]
    o = {k: np.zeros((E, N), np.float32) for k in ("hafif", "orta", "agir", "cokagir", "cokmus_bina", "cokmus_kisi",
                                                   "yarali_hafif", "yarali_hastane", "yarali_agir", "can_kaybi")}
    for s, t, k, b, kk in SINIF:
        p = hasar_olasilik(performans_sd(sa_periyot(ln, per, kap.at[s, "T_s"]), s, a[None, :]), s, s_beta, theta)
        for i, ad in enumerate(("hafif", "orta", "agir", "cokagir")):
            o[ad] += p[..., i + 1] * b
        c = cokme_orani(t, k)
        o["cokmus_bina"] += p[..., 4] * c * b
        y, ck = yaralanma(p, np.broadcast_to(kk, (E, N)), t, k)
        o["cokmus_kisi"] += ck
        for i, ad in enumerate(("yarali_hafif", "yarali_hastane", "yarali_agir", "can_kaybi")):
            o[ad] += kappa * y[..., i]
    return o


z = np.load(YH / "senaryo_alanlar.npz")
imts = list(z["imts"]); sa_imt = [i for i in imts if i != "PGA"]
per = np.array([float(i[3:-1]) for i in sa_imt])
sira = pd.Series(np.arange(len(saha)), index=saha.saha_id)[ms.saha_id].values
ln = z["ln_sa"][:, [imts.index(i) for i in sa_imt], :][:, :, sira].transpose(0, 2, 1)
E = ln.shape[0]

# ---------------- ana: posterior topluluğu ----------------
kal = pd.read_parquet(HS / "kalibrasyon.parquet")
secim = rng.choice(len(kal), size=E, p=kal.agirlik.values)
t0 = time.time()
ana = {k: np.zeros((E, N), np.float32) for k in hesapla(ln[:1], per)}
for j in np.unique(secim):
    ev = np.where(secim == j)[0]; r = kal.iloc[j]
    sonuc = hesapla(ln[ev], per, r.s_beta, (r.theta_ho, r.theta_ho, r.theta_ac, r.theta_ac), r.kappa)
    for k in ana:
        ana[k][ev] = sonuc[k]
print(f"ana: {E} olay, {len(np.unique(secim))} farklı kalibrasyon noktası, {time.time() - t0:.0f} sn")
koeri = hesapla(ln, per)

# ---------------- İBB eşdeğeri: ε = 0, mantık ağacı ağırlıklı medyan ----------------
med = pd.read_parquet(YH / "senaryo_medyan.parquet")
w = json.loads((YH / "mantik_agaci.json").read_text())["agirlik"]
med = med[med.saha_id.isin(ms.saha_id) & (med.imt != "PGA")]
lm = (med.assign(wl=med.ln_medyan * med.gmpe.map(w)).groupby(["saha_id", "imt"]).wl.sum().unstack()[sa_imt]
      .reindex(ms.saha_id).values)[None]
ibb_es = hesapla(lm, per)
pd.DataFrame({"uavt": uavt, **{k: v[0] for k, v in ibb_es.items()}}).to_parquet(HS / "ibb_esdegeri.parquet", index=False)

# ---------------- çıktılar ----------------
satir = []
for katman, o in (("ana", ana), ("koeri_mc", koeri)):
    d = pd.DataFrame({k: v.sum(1) for k, v in o.items()}); d["katman"] = katman; d["olay"] = np.arange(E)
    d["agir_ustu"] = d.agir + d.cokagir
    satir.append(d)
tot = pd.concat(satir, ignore_index=True)
tot["kal_s_beta"] = np.where(tot.katman == "ana", kal.s_beta.values[secim][tot.olay], 1.0)
tot.to_parquet(HS / "olay_toplamlari.parquet", index=False)
q = lambda x, p: np.percentile(x, p, axis=0)
au = ana["agir"] + ana["cokagir"]
pd.DataFrame({"uavt": uavt, **{f"agir_ustu_p{p}": q(au, p) for p in (5, 50, 95)}, "agir_ustu_ort": au.mean(0),
              **{f"can_kaybi_p{p}": q(ana["can_kaybi"], p) for p in (5, 50, 95)}, "can_kaybi_ort": ana["can_kaybi"].mean(0),
              "cokmus_kisi_ort": ana["cokmus_kisi"].mean(0), "orta_ust_ort": (ana["orta"] + au).mean(0),
              "ibb_esdegeri_agir_ustu": ibb_es["agir"][0] + ibb_es["cokagir"][0]}).to_parquet(HS / "mahalle_ozet.parquet", index=False)
np.savez_compressed(HS / "simulasyon_girdi.npz", uavt=uavt, **{k: v for k, v in ana.items()}, kal_secim=secim)

ibb = mah[["bina_cok_agir", "bina_agir", "bina_orta", "can_kaybi", "agir_yarali", "hastanede_tedavi"]].sum()
print("İBB (yayımlanan)  :", {k: int(v) for k, v in ibb.items()})
print("İBB eşdeğeri (biz):", {k: int(v.sum()) for k, v in ibb_es.items() if k in ("orta", "agir", "cokagir", "can_kaybi", "cokmus_bina")})
for katman in ("ana", "koeri_mc"):
    d = tot[tot.katman == katman]
    print(f"\n{katman} (p5 / p50 / p95 / ort):")
    for c in ("cokagir", "agir_ustu", "orta", "cokmus_bina", "cokmus_kisi", "can_kaybi", "yarali_agir", "yarali_hastane"):
        print(f"   {c:15s} {np.percentile(d[c], 5):>10,.0f} {np.percentile(d[c], 50):>10,.0f} {np.percentile(d[c], 95):>10,.0f} {d[c].mean():>10,.0f}")
