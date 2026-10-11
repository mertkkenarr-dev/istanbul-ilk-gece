"""Kırılganlık kalibrasyonu: üç gerçek deneyim (düşük, orta, yüksek şiddet), üç parametre.

Parametreler
  s_beta : KOERI β çarpanı. KOERI β'sı (~0,9–1,1) yer hareketi belirsizliğini de içerir (rapor §4.3 D-b); GMPE σ ayrıca
           örneklendiğinde çift sayılır. s_beta < 1 eğriyi dikleştirir: düşük şiddette daha az, yüksek şiddette daha çok hasar.
  theta  : medyan hasar eşikleri ölçeği, iki ayrı değer: θ_ho (hafif, orta) ve θ_ac (ağır, çok ağır). Hipotez: Türk betonarme
           binalarında dolgu duvarlar düşük ötelemede dayanımı artırır (θ_ho büyük), göçme eşiğini pek değiştirmez (θ_ac ~ 1).
  kappa  : can kaybı oranı çarpanı (KOERI tablosunun kendisi çok ağır hasarda %4–10 aralığı verir); önsel ln κ ~ N(0, 0,7),
           her (s_beta, θ) için tek boyutlu en büyük olabilirlik.
Gözlemler
  2025 Silivri, İstanbul (PGA ~0,03–0,1 g): Bakanlık tespiti – 8.367 incelemede 437 "az hasarlı", orta/ağır ≈ 0, Silivri'de 1
        ağır hasarlı, Bakırköy'de 1 kısmi çökme, ölü 0. HAZUS "orta" (kolon/kirişlerde kılcal çatlak) Türk tespit pratiğinde
        "az hasar"dır ⇒ orta ~200 (σ_ln 1,0, yalnızca ihbar edilen binalar incelendi); ağır+ 2 ve ölü 0 Poisson.
  1999 İzmit, İstanbul (~0,1–0,2 g): 454 yerel ölü (σ_ln 0,35); 18.162 "oturulamaz" konut ⇒ ~3.300 ağır+ bina (σ_ln 0,45);
        ~41.000 hasarlı konut/işyeri ⇒ ~7.000 hafif+ bina (σ_ln 0,6). Stok: 2000 öncesi; nüfus 10,0 M bu stoğa dağıtılır.
  1999 İzmit, fay bölgesi Kocaeli+Sakarya+Yalova+Bolu(Düzce) (~0,3–0,4 g): 16.142 ölü (σ_ln 0,5: vekil envanter bölgenin
        daha kırılgan stoğunu ve Adapazarı yumuşak zeminini temsil edemez); ">20.000 betonarme çerçeve
        bina çöktü" (Sezen vd. 2003, resmî tahmin) ⇒ çok ağır ~22.000 (σ_ln 0,5). Envanter: WorldPop 2000 nüfusuna İstanbul
        2000 öncesi stoğunun kişi başı sınıf karışımı (vekil; bölge stoğu daha alçak katlı – sınırlılık).
Çıktı: data/processed/hasar/kalibrasyon.parquet, kalibrasyon.json
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from hasar_motoru import KOK, a_katsayi, cokme_orani, hasar_olasilik, kap, performans_sd, sa_periyot, yaralanma
from scipy.stats import norm, poisson

YH = KOK / "data/processed/yer_hareketi"; HS = KOK / "data/processed/hasar"
env = pd.read_parquet(HS / "envanter.parquet")
uavt = pd.read_parquet(KOK / "data/processed/mahalle.parquet", columns=["uavt"]).uavt.values
saha = pd.read_parquet(YH / "sahalar.parquet"); saha = saha[saha.tip == "mahalle"]
a_ist = a_katsayi(saha.set_index(saha.kaynak_id.astype(int)).vs30.reindex(uavt).values)
NUFUS_1999_IST = 10_018_735  # TÜİK 2000 sayımı, İstanbul


def sinif_matrisi(e: pd.DataFrame, birimler: np.ndarray) -> tuple[list, np.ndarray, np.ndarray]:
    """Sınıf listesi ve (C, N) bina / kişi matrisleri."""
    sinif = list(e.groupby(["sinif", "tip", "kat"]).groups)
    pos = pd.Series(np.arange(len(birimler)), index=birimler)
    B = np.zeros((len(sinif), len(birimler))); K = np.zeros_like(B)
    for c, (s, t, k) in enumerate(sinif):
        g = e[(e.sinif == s) & (e.tip == t) & (e.kat == k)]
        B[c, pos[g.uavt].values] = g.bina.values; K[c, pos[g.uavt].values] = g.kisi.values
    return sinif, B, K


# --- üç olayın maruziyeti ---
OLAY = {}
s_all, B, K = sinif_matrisi(env, uavt)
OLAY["silivri2025"] = (s_all, B, K, a_ist)
e99 = env[env.yas != "2000-"].copy(); e99["kisi"] *= NUFUS_1999_IST / e99.kisi.sum()
s99, B99, K99 = sinif_matrisi(e99, uavt)
OLAY["izmit1999"] = (s99, B99, K99, a_ist)
h = pd.read_parquet(HS / "bolge1999_hucre.parquet")
oran_b = e99.groupby(["sinif", "tip", "kat"]).bina.sum() / e99.kisi.sum()   # kişi başına bina, sınıf bazında
oran_k = e99.groupby(["sinif", "tip", "kat"]).kisi.sum() / e99.kisi.sum()
sb = list(oran_b.index)
OLAY["bolge1999"] = (sb, oran_b.values[:, None] * h.nufus.values[None], oran_k.values[:, None] * h.nufus.values[None], a_katsayi(h.vs30.values))

ALAN = {}
for ad in OLAY:
    z = np.load(YH / f"gecmis_{ad}.npz")
    imts = list(z["imts"]); sa = [i for i in imts if i != "PGA"]
    ALAN[ad] = (z["ln_sa"][:, [imts.index(i) for i in sa], :].transpose(0, 2, 1), np.array([float(i[3:-1]) for i in sa]))


def tahmin(ad: str, s_beta: float, theta: float) -> dict:
    sinif, B, K, a = OLAY[ad]; ln, per = ALAN[ad]
    o = dict(hafif_ustu=0.0, orta=0.0, agir_ustu=0.0, cokagir=0.0, cokmus=0.0, olu=0.0)
    for c, (s, t, k) in enumerate(sinif):
        if B[c].sum() == 0:
            continue
        p = hasar_olasilik(performans_sd(sa_periyot(ln, per, kap.at[s, "T_s"]), s, a[None, :]), s, s_beta, theta).mean(0)  # (N, 5)
        o["hafif_ustu"] += (p[:, 1:].sum(1) * B[c]).sum(); o["orta"] += (p[:, 2] * B[c]).sum()
        o["agir_ustu"] += (p[:, 3:].sum(1) * B[c]).sum(); o["cokagir"] += (p[:, 4] * B[c]).sum()
        o["cokmus"] += (p[:, 4] * cokme_orani(t, k) * B[c]).sum()
        o["olu"] += yaralanma(p, K[c], t, k)[0][:, 3].sum()
    return o


def main() -> None:
    KAPPA = np.exp(np.linspace(np.log(0.05), np.log(5.0), 160))
    L = lambda x, m, s: norm.logpdf(np.log(np.maximum(x, 1e-9)), np.log(m), s)
    satir = []
    for s_beta in (0.25, 0.4, 0.55, 0.7):
        for th_ho in (1.5, 2.0, 2.5, 3.0, 3.5, 4.0):
            for th_ac in (1.0, 1.5, 2.0, 2.5, 3.0, 3.5):
                theta = (th_ho, th_ho, th_ac, th_ac)
                s, i, b = (tahmin(x, s_beta, theta) for x in ("silivri2025", "izmit1999", "bolge1999"))
                ll_h = (L(s["orta"], 200, 1.0) + poisson.logpmf(2, max(s["agir_ustu"], 1e-6))
                        + L(i["agir_ustu"], 3300, 0.45) + L(i["hafif_ustu"], 7000, 0.6) + L(b["cokagir"], 22000, 0.5))
                ll_k = (poisson.logpmf(0, np.maximum(KAPPA * s["olu"], 1e-9)) + L(KAPPA * i["olu"], 454, 0.35) + L(KAPPA * b["olu"], 16142, 0.5)
                        + norm.logpdf(np.log(KAPPA), 0, 0.7))
                j = int(np.argmax(ll_k))
                satir.append(dict(s_beta=s_beta, theta_ho=th_ho, theta_ac=th_ac, kappa=KAPPA[j], **{f"s25_{k}": v for k, v in s.items()},
                                  **{f"i99_{k}": v for k, v in i.items()}, **{f"b99_{k}": v for k, v in b.items()},
                                  ll_hasar=ll_h, ll_olu=ll_k[j], ll=ll_h + ll_k[j]))
        print(f"s_beta={s_beta} tamam", flush=True)
    k = pd.DataFrame(satir)
    k["agirlik"] = np.exp(k.ll - k.ll.max()); k["agirlik"] /= k.agirlik.sum()
    for c in ("s25", "i99", "b99"):
        k[f"{c}_olu_k"] = k[f"{c}_olu"] * k.kappa
    k.to_parquet(HS / "kalibrasyon.parquet", index=False)
    en = k.loc[k.ll.idxmax()]
    ozet = dict(en_iyi=en.round(4).to_dict(),
                s_beta_ort=float((k.s_beta * k.agirlik).sum()), theta_ho_ort=float((k.theta_ho * k.agirlik).sum()),
                theta_ac_ort=float((k.theta_ac * k.agirlik).sum()),
                kappa_ort=float(np.exp((np.log(k.kappa) * k.agirlik).sum())))
    (HS / "kalibrasyon.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1))
    pd.set_option("display.width", 250)
    cols = ["s_beta", "theta_ho", "theta_ac", "kappa", "s25_orta", "s25_olu_k", "s25_agir_ustu", "i99_agir_ustu", "i99_olu_k", "b99_cokagir", "b99_olu_k", "ll_hasar", "ll_olu", "agirlik"]
    print(k.sort_values("ll", ascending=False)[cols].head(12).round(2).to_string(index=False))
    print(f"\nolabilirlik ağırlıklı: s_beta = {ozet['s_beta_ort']:.2f}, θ_ho = {ozet['theta_ho_ort']:.2f}, θ_ac = {ozet['theta_ac_ort']:.2f}, κ = {ozet['kappa_ort']:.2f}")
    print("\nθ_ac marjinal ağırlığı:", k.groupby("theta_ac").agirlik.sum().round(3).to_dict())
    print("θ_ho marjinal ağırlığı:", k.groupby("theta_ho").agirlik.sum().round(3).to_dict())


if __name__ == "__main__":
    main()
