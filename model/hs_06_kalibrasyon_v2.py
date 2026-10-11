"""Kalibrasyon v2: dört gerçek deprem, ayrı göçme eğrisi, sarsıntı süresi ve göçmede ölümcüllük.

Neden v2 (bkz. docs/YONTEM_2_HASAR.md §6): v1, İstanbul 1999 ile fay bölgesi 1999 arasındaki kişi başı ölüm farkını (gözlem ~×130)
hiçbir parametreyle üretemiyordu (en fazla ~×25) ve 6 Şubat 2023'ü 24 kat düşük tahmin etti. Sebep yapısal: HAZUS-TR, "çok ağır ama
çökmemiş" binada içindekilerin %4'ünü öldürür (zayıf sarsıntıda yapay ölüm) ve çöken binada ölümcüllüğü %10'da sabit tutar (güçlü
sarsıntıda eksik ölüm). Gözlem ve literatür (Ceferino vd. 2025, çöküş hacmi) ölümün neredeyse yalnızca göçmede olduğunu ve
göçmenin şiddetle birlikte büyüdüğünü söyler.

Model
  hasar      KOERI kırılganlığı, s_β (eğim) ve θ_ho / θ_ac (eşik ölçekleri) — v1 ile aynı
  süre       talep Sd·(Ds/20 sn)^c; c önseli N(0,16; 0,08) (Chandramohan vd. 2015/16: uzun sürede göçme kapasitesi %17–29 düşük)
  göçme      P(göçme) = P(DS4) · Φ(ln(Sd / (θ_g · Sd_DS4)) / β_g)   (çok ağır hasar içinde göçme payı şiddetle artar)
  ölüm       λ · P(göçme) · kişi  +  0,001 · P(DS4, göçmeyen) · kişi;  λ ∈ [0,05; 0,8], önsel ln λ ~ N(ln 0,3; 0,6)
Gözlemler
  2025 Silivri   orta ~200 (σ_ln 1,0), ağır+ 2 (Poisson), ölü 0 (Poisson)
  1999 İstanbul  ağır+ 3.300 (0,45), hafif+ 7.000 (0,6), ölü 454 (0,35)
  1999 bölge     göçen bina >20.000 (Sezen vd. 2003; 0,5), ölü 16.142 (0,4)
  2023 (11 il)   ölü 53.537 (AFAD; 0,3), ağır+ binada yaşayan ~2,0 M kişi (518.009 konut × 3,9; 0,4)
Çıktı: data/processed/hasar/kalibrasyon_v2.parquet, kalibrasyon_v2.json
"""
from __future__ import annotations

import json
import sys
import time

import numpy as np
import pandas as pd
from hasar_motoru import KOK, a_katsayi, hasar_olasilik, kap, kir, performans_sd, sa_periyot
from scipy.special import ndtr
from scipy.stats import norm, poisson

YH = KOK / "data/processed/yer_hareketi"; HS = KOK / "data/processed/hasar"
sys.path.insert(0, str(KOK / "sinama"))
rng = np.random.default_rng(2023)
DS_REF = np.log(20.0)
E_IST, E_BOLGE, E_2023 = 200, 150, 24
NC_OLUM = 0.001


def siniflar(e: pd.DataFrame, birimler: np.ndarray) -> tuple[list, np.ndarray, np.ndarray]:
    s = list(e.groupby(["sinif", "tip", "kat"]).groups)
    pos = pd.Series(np.arange(len(birimler)), index=birimler)
    B = np.zeros((len(s), len(birimler))); K = np.zeros_like(B)
    for c, (a, t, k) in enumerate(s):
        g = e[(e.sinif == a) & (e.tip == t) & (e.kat == k)]
        B[c, pos[g.uavt].values] = g.bina.values; K[c, pos[g.uavt].values] = g.kisi.values
    return s, B, K


def alan(ad: str, E: int) -> tuple[np.ndarray, np.ndarray]:
    z = np.load(YH / f"gecmis_{ad}.npz")
    imts = list(z["imts"]); sa = [i for i in imts if i != "PGA"]
    ln = z["ln_sa"][:E][:, [imts.index(i) for i in sa], :].transpose(0, 2, 1)
    return ln, np.array([float(i[3:-1]) for i in sa])


def olaylar() -> dict:
    env = pd.read_parquet(HS / "envanter.parquet")
    uavt = pd.read_parquet(KOK / "data/processed/mahalle.parquet", columns=["uavt"]).uavt.values
    saha = pd.read_parquet(YH / "sahalar.parquet"); saha = saha[saha.tip == "mahalle"]
    a_ist = a_katsayi(saha.set_index(saha.kaynak_id.astype(int)).vs30.reindex(uavt).values)
    sure = np.load(YH / "sure_ds595.npz")
    O = {}
    s, B, K = siniflar(env, uavt)
    O["s25"] = dict(sinif=s, B=B, K=K, a=a_ist, alan=alan("silivri2025", E_IST), lnds=sure["silivri2025"])
    e99 = env[env.yas != "2000-"].copy(); e99["kisi"] *= 10_018_735 / e99.kisi.sum()
    s, B, K = siniflar(e99, uavt)
    O["i99"] = dict(sinif=s, B=B, K=K, a=a_ist, alan=alan("izmit1999", E_IST), lnds=sure["izmit1999"])
    h = pd.read_parquet(HS / "bolge1999_hucre.parquet")
    ob = e99.groupby(["sinif", "tip", "kat"]).bina.sum() / e99.kisi.sum(); ok = e99.groupby(["sinif", "tip", "kat"]).kisi.sum() / e99.kisi.sum()
    O["b99"] = dict(sinif=list(ob.index), B=ob.values[:, None] * h.nufus.values[None], K=ok.values[:, None] * h.nufus.values[None],
                    a=a_katsayi(h.vs30.values), alan=alan("bolge1999", E_BOLGE), lnds=sure["bolge1999"])
    import s02_maras2023_tahmin as s02
    d = pd.read_parquet(KOK / "data/processed/sinama/maras2023_dugum.parquet")
    lnds = sure["maras2023"]
    m = d.il.isin(s02.IL11).values & (d.ln_pga.values > np.log(0.05))
    d = d[m].reset_index(drop=True); lnds = lnds[m]
    lr, _ = s02.yas_eslemesi()
    kos, W = s02.stok(d, lr, alcak=False)
    K = (d.nufus.values[:, None] * W).T
    kisi_bina = kos.kat.map(s02.KISI).values
    olcek = 7.0 / np.average(kisi_bina, weights=K.sum(1))           # bölgede ~7 kişi/bina (≈16 M nüfus / 2,3 M yapı)
    B = K / (kisi_bina * olcek)[:, None]
    ln0 = d[["ln_sa03", "ln_sa06", "ln_sa10"]].values
    eps = rng.normal(0, 0.45, (E_2023, len(d), 1))                  # ShakeMap koşullu belirsizliği (istasyon arası, tipik σ)
    O["m23"] = dict(sinif=[(r.sinif, r.tip, r.kat) for r in kos.itertuples()], B=B, K=K, a=a_katsayi(d.vs30.values),
                    alan=(ln0[None] + eps, np.array([0.3, 0.6, 1.0])), lnds=lnds)
    for k, o in O.items():
        print(f"{k}: {len(o['sinif'])} sınıf × {o['B'].shape[1]:,} birim, kişi {o['K'].sum():,.0f}, E = {o['alan'][0].shape[0]}", flush=True)
    return O


def sd_onbellek(O: dict) -> dict:
    """c'den bağımsız Sd talebi, sınıf başına (E, N)."""
    S = {}
    for k, o in O.items():
        ln, per = o["alan"]
        S[k] = [performans_sd(sa_periyot(ln, per, kap.at[s, "T_s"]), s, o["a"][None, :]) for s, _, _ in o["sinif"]]
    return S


def ozet(o: dict, sdl: list, f: np.ndarray, s_beta: float, theta: tuple, GOC: list) -> tuple[dict, np.ndarray, np.ndarray]:
    """Hasar toplamları ve her (θ_g, β_g) için göçen bina / göçmede kalan kişi / göçmeyen-DS4 kişi."""
    r = dict(hafif_ustu=0.0, orta=0.0, agir_ustu=0.0, agir_ustu_kisi=0.0)
    gb = np.zeros(len(GOC)); gk = np.zeros(len(GOC)); nk = np.zeros(len(GOC))
    for c, (s, _, _) in enumerate(o["sinif"]):
        if o["K"][c].sum() == 0:
            continue
        sd = sdl[c] * f
        p = hasar_olasilik(sd, s, s_beta, theta)
        pm = p.mean(0)
        r["hafif_ustu"] += (pm[:, 1:].sum(1) * o["B"][c]).sum(); r["orta"] += (pm[:, 2] * o["B"][c]).sum()
        r["agir_ustu"] += (pm[:, 3:].sum(1) * o["B"][c]).sum(); r["agir_ustu_kisi"] += (pm[:, 3:].sum(1) * o["K"][c]).sum()
        sd4 = theta[3] * kir.at[s, "sd_cokagir_cm"]
        lsd = np.log(np.maximum(sd, 1e-9) / sd4)
        for j, (tg, bg) in enumerate(GOC):
            pg = (p[..., 4] * ndtr((lsd - np.log(tg)) / bg)).mean(0)
            gb[j] += (pg * o["B"][c]).sum(); gk[j] += (pg * o["K"][c]).sum(); nk[j] += ((pm[:, 4] - pg) * o["K"][c]).sum()
    return r, gb, gk, nk


def main() -> None:
    O = olaylar()
    t0 = time.time(); S = sd_onbellek(O); print(f"Sd önbelleği {time.time() - t0:.0f} sn", flush=True)
    L = lambda x, m, s: norm.logpdf(np.log(np.maximum(x, 1e-9)), np.log(m), s)
    LAM = np.exp(np.linspace(np.log(0.05), np.log(0.8), 60))
    GOC = [(tg, bg) for tg in (1.0, 1.25, 1.6, 2.0, 2.6) for bg in (0.15, 0.3, 0.45)]
    satir = []
    for c in (0.0, 0.15, 0.3):
        F = {k: np.exp(c * (np.nan_to_num(o["lnds"], nan=DS_REF) - DS_REF))[None, :] for k, o in O.items()}
        for s_beta in (0.25, 0.4, 0.55, 0.7):
            for th_ho in (1.5, 2.5, 3.5):
                for th_ac in (0.8, 1.0, 1.3, 1.6, 2.0, 2.5, 3.0):
                    th = (th_ho, th_ho, th_ac, th_ac)
                    R = {k: ozet(o, S[k], F[k], s_beta, th, GOC) for k, o in O.items()}
                    s25, i99, b99, m23 = (R[k][0] for k in ("s25", "i99", "b99", "m23"))
                    ll_h = (L(s25["orta"], 200, 1.0) + poisson.logpmf(2, max(s25["agir_ustu"], 1e-6))
                            + L(i99["agir_ustu"], 3300, 0.45) + L(i99["hafif_ustu"], 7000, 0.6)
                            + L(m23["agir_ustu_kisi"], 2.0e6, 0.4) + norm.logpdf(c, 0.16, 0.08))
                    for j, (tg, bg) in enumerate(GOC):
                        olu = {k: LAM * R[k][2][j] + NC_OLUM * R[k][3][j] for k in R}
                        ll_o = (poisson.logpmf(0, np.maximum(olu["s25"], 1e-9)) + L(olu["i99"], 454, 0.35) + L(olu["b99"], 16142, 0.4)
                                + L(olu["m23"], 53537, 0.3) + norm.logpdf(np.log(LAM), np.log(0.3), 0.6))
                        ll_g = L(R["b99"][1][j], 20000, 0.5)
                        i = int(np.argmax(ll_o))
                        satir.append(dict(c=c, s_beta=s_beta, theta_ho=th_ho, theta_ac=th_ac, theta_g=tg, beta_g=bg, lam=LAM[i],
                                          **{f"{k}_olu": float(olu[k][i]) for k in olu}, **{f"{k}_goc_bina": float(R[k][1][j]) for k in R},
                                          s25_orta=s25["orta"], s25_agir_ustu=s25["agir_ustu"], i99_agir_ustu=i99["agir_ustu"],
                                          i99_hafif_ustu=i99["hafif_ustu"], m23_agir_ustu_kisi=m23["agir_ustu_kisi"],
                                          ll_hasar=ll_h, ll_olu=ll_o[i], ll_goc=ll_g, ll=ll_h + ll_o[i] + ll_g))
            print(f"c={c} s_beta={s_beta} tamam ({time.time() - t0:.0f} sn)", flush=True)
    k = pd.DataFrame(satir)
    k["agirlik"] = np.exp(k.ll - k.ll.max()); k["agirlik"] /= k.agirlik.sum()
    k.to_parquet(HS / "kalibrasyon_v2.parquet", index=False)
    w = k.agirlik
    ozet_ = {p: float((k[p] * w).sum()) for p in ("c", "s_beta", "theta_ho", "theta_ac", "theta_g", "beta_g", "lam")}
    ozet_["tahmin_vs_gozlem"] = {o: [float((k[f"{o}_olu"] * w).sum()), g] for o, g in (("s25", 0), ("i99", 454), ("b99", 16142), ("m23", 53537))}
    (HS / "kalibrasyon_v2.json").write_text(json.dumps(ozet_, ensure_ascii=False, indent=1))
    pd.set_option("display.width", 250)
    cols = ["c", "s_beta", "theta_ho", "theta_ac", "theta_g", "beta_g", "lam", "s25_olu", "i99_olu", "b99_olu", "m23_olu", "b99_goc_bina",
            "i99_agir_ustu", "m23_agir_ustu_kisi", "ll", "agirlik"]
    print(k.sort_values("ll", ascending=False)[cols].head(12).round(3).to_string(index=False))
    print(json.dumps(ozet_, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
