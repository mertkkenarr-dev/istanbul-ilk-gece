"""Kalibrasyon v3: v2 + kat sayısına bağlı göçme ölümcüllüğü + 2023 çift şok + bölgesel stok kalitesi.

v2'nin bıraktığı gerilim: İstanbul 1999'u ×4 fazla, 6 Şubat'ı ×3 eksik tahmin ediyordu ve parametreler ızgara sınırına dayanıyordu.
Üç yapısal ek:
  ölümcüllük   λ_kat = λ · {1–4: 1, 5–8: μ, 9+: μ^1,5}, en çok 0,9. Yüksek binada enkaz derin, yaşam boşluğu az (So 2016; Ceferino vd. 2025:
               sünek olmayan betonarmede MCE altında %65). μ ∈ {1; 1,5; 2,2}.
  çift şok     2023'te iki ana şok vardı; talep olarak düğüm başına büyüğü alınır. Elbistan şokunun hasarlı binalara ek etkisi
               (≈550 bin kişi, çoğu Malatya) modellenmez — SINIRLILIK: bu yıkım kısmen "zayıf stok" olarak okunur, İstanbul'a hafif yukarı yanlılık.
  stok kalitesi δ_r: bölgenin kapasitesi İstanbul'unkinin δ katı (Sd talebi 1/δ ile ölçeklenir); İstanbul için δ = 1 tanım gereği.
               Önsel ln δ ~ N(0; 0,25). 6 Şubat'ı daha zayıf stokla açıklamak İstanbul tahminini düşürür; bu yüzden δ'nın
               posterioru ayrıca raporlanır ve İstanbul sonuçları δ'ya koşullu iki uçla da verilir (hs_09).
Diğer her şey hs_06 ile aynı. Çıktı: data/processed/hasar/kalibrasyon_v3.parquet, kalibrasyon_v3.json
"""
from __future__ import annotations

import json
import sys
import time

import hs_06_kalibrasyon_v2 as v2
import numpy as np
import pandas as pd
from hasar_motoru import KOK, hasar_olasilik, kap, kir, performans_sd, sa_periyot
from scipy.special import ndtr
from scipy.stats import norm, poisson

HS = KOK / "data/processed/hasar"
KAT = ("1-4", "5-8", "9-")


def m23_iki_sok(O: dict) -> None:
    sys.path.insert(0, str(KOK / "sinama"))
    import s02_maras2023_tahmin as s02
    d = pd.read_parquet(KOK / "data/processed/sinama/maras2023_dugum.parquet")
    m = d.il.isin(s02.IL11).values & (d.ln_pga.values > np.log(0.05))
    d = d[m].reset_index(drop=True)
    eps = np.random.default_rng(2023).normal(0, 0.45, (v2.E_2023, len(d), 1))
    per = np.array([0.3, 0.6, 1.0])
    O["m23"]["alan2"] = [(d[[f"ln_sa03_s{i}", f"ln_sa06_s{i}", f"ln_sa10_s{i}"]].values[None] + eps, per) for i in (1, 2)]


def sd_onbellek(O: dict) -> dict:
    S = v2.sd_onbellek({k: o for k, o in O.items() if k != "m23"})
    o = O["m23"]
    iki = [[performans_sd(sa_periyot(ln, per, kap.at[s, "T_s"]), s, o["a"][None, :]) for s, _, _ in o["sinif"]] for ln, per in o["alan2"]]
    S["m23_max"] = [np.maximum(a, b) for a, b in zip(*iki, strict=True)]
    S["m23_srss"] = [np.sqrt(a ** 2 + b ** 2) for a, b in zip(*iki, strict=True)]
    return S


def ozet(o: dict, sdl: list, f: np.ndarray, s_beta: float, theta: tuple, GOC: list) -> tuple:
    """v2.ozet ile aynı; göçmede kalan kişi kat grubuna göre ayrı (GOC × 3)."""
    r = dict(hafif_ustu=0.0, orta=0.0, agir_ustu=0.0, agir_ustu_kisi=0.0)
    gb = np.zeros(len(GOC)); gk = np.zeros((len(GOC), 3)); nk = np.zeros(len(GOC))
    for c, (s, _, k) in enumerate(o["sinif"]):
        if o["K"][c].sum() == 0:
            continue
        sd = sdl[c] * f
        p = hasar_olasilik(sd, s, s_beta, theta)
        pm = p.mean(0)
        r["hafif_ustu"] += (pm[:, 1:].sum(1) * o["B"][c]).sum(); r["orta"] += (pm[:, 2] * o["B"][c]).sum()
        r["agir_ustu"] += (pm[:, 3:].sum(1) * o["B"][c]).sum(); r["agir_ustu_kisi"] += (pm[:, 3:].sum(1) * o["K"][c]).sum()
        lsd = np.log(np.maximum(sd, 1e-9) / (theta[3] * kir.at[s, "sd_cokagir_cm"]))
        ki = KAT.index(k)
        for j, (tg, bg) in enumerate(GOC):
            pg = (p[..., 4] * ndtr((lsd - np.log(tg)) / bg)).mean(0)
            gb[j] += (pg * o["B"][c]).sum(); gk[j, ki] += (pg * o["K"][c]).sum(); nk[j] += ((pm[:, 4] - pg) * o["K"][c]).sum()
    return r, gb, gk, nk


def main() -> None:
    O = v2.olaylar(); m23_iki_sok(O)
    t0 = time.time(); S = sd_onbellek(O); print(f"Sd önbelleği {time.time() - t0:.0f} sn", flush=True)
    L = lambda x, m, s: norm.logpdf(np.log(np.maximum(x, 1e-9)), np.log(m), s)
    LAM = np.exp(np.linspace(np.log(0.05), np.log(0.8), 50))
    GOC = [(tg, bg) for tg in (2.6, 3.4, 4.4) for bg in (0.15, 0.3)]
    MU = (1.0, 1.5, 2.2)
    D99, D23 = (0.75, 1.0), (0.65, 0.8, 1.0)
    satir = []
    for c in (0.15, 0.3, 0.45):
        F = {k: np.exp(c * (np.nan_to_num(o["lnds"], nan=v2.DS_REF) - v2.DS_REF))[None, :] for k, o in O.items()}
        for s_beta in (0.15, 0.25, 0.4):
            for th_ho in (2.0, 3.0):
                for th_ac in (1.6, 2.0, 2.5):
                    th = (th_ho, th_ho, th_ac, th_ac)
                    s25 = ozet(O["s25"], S["s25"], F["s25"], s_beta, th, GOC)
                    i99 = ozet(O["i99"], S["i99"], F["i99"], s_beta, th, GOC)
                    b99 = {d: ozet(O["b99"], S["b99"], F["b99"] / d, s_beta, th, GOC) for d in D99}
                    m23 = {(cf, d): ozet(O["m23"], S[f"m23_{cf}"], F["m23"] / d, s_beta, th, GOC) for cf in ("max",) for d in D23}
                    ll_ist = (L(s25[0]["orta"], 200, 1.0) + poisson.logpmf(2, max(s25[0]["agir_ustu"], 1e-6))
                              + L(i99[0]["agir_ustu"], 3300, 0.45) + L(i99[0]["hafif_ustu"], 7000, 0.6) + norm.logpdf(c, 0.16, 0.12))
                    for d99 in D99:
                        for (cf, d23), R23 in m23.items():
                            ll_h = ll_ist + L(R23[0]["agir_ustu_kisi"], 2.0e6, 0.4) + norm.logpdf(np.log(d99), 0, 0.25) + norm.logpdf(np.log(d23), 0, 0.25)
                            for j, (tg, bg) in enumerate(GOC):
                                for mu in MU:
                                    km = np.array([1.0, mu, mu ** 1.5])
                                    olu = {}
                                    for ad, R in (("s25", s25), ("i99", i99), ("b99", b99[d99]), ("m23", R23)):
                                        olu[ad] = (np.minimum(LAM[:, None] * km[None], 0.9) * R[2][j][None]).sum(1) + v2.NC_OLUM * R[3][j]
                                    ll_o = (poisson.logpmf(0, np.maximum(olu["s25"], 1e-9)) + L(olu["i99"], 454, 0.4) + L(olu["b99"], 16142, 0.4)
                                            + L(olu["m23"], 53537, 0.3) + norm.logpdf(np.log(LAM), np.log(0.3), 0.6))
                                    ll_g = L(b99[d99][1][j], 20000, 0.5)
                                    i = int(np.argmax(ll_o))
                                    satir.append(dict(c=c, s_beta=s_beta, theta_ho=th_ho, theta_ac=th_ac, theta_g=tg, beta_g=bg, mu=mu, lam=LAM[i],
                                                      d99=d99, d23=d23, cift=cf, **{f"{k}_olu": float(v[i]) for k, v in olu.items()},
                                                      i99_agir_ustu=i99[0]["agir_ustu"], m23_agir_ustu_kisi=R23[0]["agir_ustu_kisi"],
                                                      b99_goc_bina=float(b99[d99][1][j]), ll=ll_h + ll_o[i] + ll_g))
            print(f"c={c} s_beta={s_beta} tamam ({time.time() - t0:.0f} sn)", flush=True)
    k = pd.DataFrame(satir)
    k["agirlik"] = np.exp(k.ll - k.ll.max()); k["agirlik"] /= k.agirlik.sum()
    k.to_parquet(HS / "kalibrasyon_v3.parquet", index=False)
    w = k.agirlik
    oz = {p: float((k[p] * w).sum()) for p in ("c", "s_beta", "theta_ho", "theta_ac", "theta_g", "beta_g", "mu", "lam", "d99", "d23")}
    oz["tahmin_vs_gozlem"] = {o: [float((k[f"{o}_olu"] * w).sum()), g] for o, g in (("s25", 0), ("i99", 454), ("b99", 16142), ("m23", 53537))}
    for p in ("d23", "mu", "c", "theta_g", "s_beta"):
        oz[f"marjinal_{p}"] = {str(a): round(float(b), 3) for a, b in k.groupby(p).agirlik.sum().items()}
    (HS / "kalibrasyon_v3.json").write_text(json.dumps(oz, ensure_ascii=False, indent=1))
    pd.set_option("display.width", 250)
    cols = ["c", "s_beta", "theta_ho", "theta_ac", "theta_g", "beta_g", "mu", "lam", "d99", "d23", "cift", "s25_olu", "i99_olu", "b99_olu", "m23_olu", "ll", "agirlik"]
    print(k.sort_values("ll", ascending=False)[cols].head(12).round(3).to_string(index=False))
    print(json.dumps(oz, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
