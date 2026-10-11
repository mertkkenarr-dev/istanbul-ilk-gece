"""İstanbul hasar ve can kaybı, model v3 (hs_08 posterioru), üç kırılma senaryosu × iki stok varsayımı.

Senaryolar   temel (Orta Marmara Mw 7,5; yh_03), dogu (Adalar–Çınarcık Mw 7,4), buyuk (tüm Marmara Mw 7,7) — yh_08
Stok         ist        δ = 1: İstanbul binaları kalibrasyonun İstanbul'a ait gözlemleriyle (2025, 1999) uyumlu
             maras_gibi δ = posteriordaki 6 Şubat bölgesi δ'sı: İstanbul binaları 6 Şubat bölgesi kadar zayıf (üst uç)
Ölüm         Σ_kat λ·m_kat·P(göçme)·kişi + 0,001·P(DS4, göçmeyen)·kişi
Simülatör girdisi (enkaz havuzu): göçmede ölenlerin %60'ı anında (VARSAYIM; Coburn vd. 1992 – çöken betonarme binada ölümlerin
çoğu ilk dakikalarda), kalan canlıların yarısı kendi çıkamaz → sikisan_canli. Simülatör bunların akıbetini ekip/hastane ile üretir.
Çıktı: data/processed/hasar/v3/{senaryo}_{stok}.npz, v3/ozet.parquet
"""
from __future__ import annotations

import sys
import time

import numpy as np
import pandas as pd
from hasar_motoru import KOK, a_katsayi, hasar_olasilik, kap, kir, performans_sd, sa_periyot, yaralanma
from scipy.special import ndtr

YH = KOK / "data/processed/yer_hareketi"; HS = KOK / "data/processed/hasar"; CIKTI = HS / "v3"; CIKTI.mkdir(exist_ok=True)
NC_OLUM, ANINDA, SIKISMA = 0.001, 0.6, 0.5
KAT = ("1-4", "5-8", "9-")
COKMUS_ORAN = {"yarali_agir": 0.10, "yarali_hastane": 0.15}
env = pd.read_parquet(HS / "envanter.parquet")
uavt = pd.read_parquet(KOK / "data/processed/mahalle.parquet", columns=["uavt"]).uavt.values
N = len(uavt); pos = pd.Series(np.arange(N), index=uavt)
saha = pd.read_parquet(YH / "sahalar.parquet")
ms = saha[saha.tip == "mahalle"].set_index(saha[saha.tip == "mahalle"].kaynak_id.astype(int)).reindex(uavt)
a = a_katsayi(ms.vs30.values)
SINIF = []
for (s, t, k), g in env.groupby(["sinif", "tip", "kat"]):
    b = np.zeros(N); kk = np.zeros(N)
    b[pos[g.uavt].values] = g.bina.values; kk[pos[g.uavt].values] = g.kisi.values
    SINIF.append((s, t, k, b, kk))
ANAH = ("hafif", "orta", "agir", "cokagir", "cokmus_bina", "cokmus_kisi", "olu_cokme", "olu_diger", "yarali_hafif", "yarali_hastane", "yarali_agir",
        "orta_kisi", "agir_ustu_kisi")


def alanlar(sen: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    f = YH / ("senaryo_alanlar.npz" if sen == "temel" else f"senaryo_alanlar_{sen}.npz")
    z = np.load(f)
    imts = list(z["imts"]); sa = [i for i in imts if i != "PGA"]
    sira = pd.Series(np.arange(len(z["saha_id"])), index=z["saha_id"])[ms.saha_id].values
    ln = z["ln_sa"][:, [imts.index(i) for i in sa], :][:, :, sira].transpose(0, 2, 1)
    lnds = np.load(YH / "sure_ds595.npz")["senaryo"] if sen == "temel" else np.load(YH / f"sure_ds595_{sen}.npy")
    return ln, np.array([float(i[3:-1]) for i in sa]), lnds


def hesapla(ln: np.ndarray, per: np.ndarray, lnds: np.ndarray, r: pd.Series, delta: float) -> dict:
    f = (np.exp(r.c * (np.nan_to_num(lnds, nan=np.log(20.0)) - np.log(20.0))) / delta)[None, :]
    th = (r.theta_ho, r.theta_ho, r.theta_ac, r.theta_ac)
    km = dict(zip(KAT, (1.0, r.mu, r.mu ** 1.5), strict=True))
    o = {k: np.zeros((ln.shape[0], N), np.float32) for k in ANAH}
    for s, t, k, b, kk in SINIF:
        sd = performans_sd(sa_periyot(ln, per, kap.at[s, "T_s"]), s, a[None, :]) * f
        p = hasar_olasilik(sd, s, r.s_beta, th)
        for i, ad in enumerate(("hafif", "orta", "agir", "cokagir")):
            o[ad] += p[..., i + 1] * b
        o["orta_kisi"] += p[..., 2] * kk; o["agir_ustu_kisi"] += (p[..., 3] + p[..., 4]) * kk
        pg = p[..., 4] * ndtr((np.log(np.maximum(sd, 1e-9) / (r.theta_ac * kir.at[s, "sd_cokagir_cm"])) - np.log(r.theta_g)) / r.beta_g)
        o["cokmus_bina"] += pg * b; o["cokmus_kisi"] += pg * kk
        o["olu_cokme"] += min(r.lam * km[k], 0.9) * pg * kk
        o["olu_diger"] += NC_OLUM * (p[..., 4] - pg) * kk
        y, _ = yaralanma(p, np.broadcast_to(kk, p.shape[:-1]), t, k)
        for i, ad in enumerate(("yarali_hafif", "yarali_hastane", "yarali_agir")):
            o[ad] += y[..., i]
    for ad, oran in COKMUS_ORAN.items():
        o[ad] = np.maximum(o[ad] - oran * o["cokmus_kisi"], 0)
    return o


if __name__ == "__main__":
    kal = pd.read_parquet(HS / "kalibrasyon_v3.parquet")
    senaryolar = [a for a in sys.argv[1:] if not a.startswith("--")] or ["temel", "dogu", "buyuk"]
    ozet = []
    for sen in senaryolar:
        ln, per, lnds = alanlar(sen)
        E = ln.shape[0]
        secim = np.random.default_rng(7275).choice(len(kal), size=E, p=kal.agirlik.values)
        for stok in ("ist", "maras_gibi"):
            t0 = time.time()
            o = {k: np.zeros((E, N), np.float32) for k in ANAH}
            for j in np.unique(secim):
                ev = np.where(secim == j)[0]; r = kal.iloc[j]
                sonuc = hesapla(ln[ev], per, lnds, r, 1.0 if stok == "ist" else float(r.d23))
                for k in o:
                    o[k][ev] = sonuc[k]
            olu = o["olu_cokme"] + o["olu_diger"]
            aninda = ANINDA * o["olu_cokme"] + o["olu_diger"]
            sikisan = SIKISMA * (o["cokmus_kisi"] - ANINDA * o["olu_cokme"])
            if "--yalniz-kisi" not in sys.argv:
                np.savez_compressed(CIKTI / f"{sen}_{stok}.npz", uavt=uavt, kal_secim=secim, can_kaybi=olu, olu_aninda=aninda,
                                    sikisan_canli=sikisan, **o)
            np.savez_compressed(CIKTI / f"{sen}_{stok}_kisi.npz", uavt=uavt, orta_kisi=o["orta_kisi"], agir_ustu_kisi=o["agir_ustu_kisi"],
                                cokmus_kisi=o["cokmus_kisi"], yarali_agir=o["yarali_agir"], yarali_hastane=o["yarali_hastane"],
                                sikisan_canli=sikisan)
            top = olu.sum(1)
            ozet.append(dict(senaryo=sen, stok=stok, olu_p5=np.percentile(top, 5), olu_p50=np.median(top), olu_ort=top.mean(),
                             olu_p95=np.percentile(top, 95), cokmus_bina_ort=o["cokmus_bina"].sum(1).mean(),
                             agir_ustu_ort=(o["agir"] + o["cokagir"]).sum(1).mean(), sikisan_ort=sikisan.sum(1).mean()))
            print(f"{sen}/{stok}: ölü medyan {ozet[-1]['olu_p50']:,.0f}, ort {ozet[-1]['olu_ort']:,.0f}, %95 {ozet[-1]['olu_p95']:,.0f} "
                  f"({time.time() - t0:.0f} sn)", flush=True)
    oz = pd.DataFrame(ozet)
    yol = CIKTI / "ozet.parquet"
    if yol.exists() and set(senaryolar) != {"temel", "dogu", "buyuk"}:
        oz = pd.concat([pd.read_parquet(yol).query("senaryo not in @senaryolar"), oz])
    oz.to_parquet(yol, index=False)
    print(oz.round(0).to_string(index=False))
