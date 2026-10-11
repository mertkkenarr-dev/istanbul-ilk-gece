"""Spektral yerdeğiştirme tabanlı bina hasarı ve can kaybı (KOERI 2010 parametreleri, ASCE 41-06 katsayı yöntemi).

Performans noktası: Sd = C1 · C2 · Sde(T), Sde = Sa(T)·g·T²/(4π²). Akma ivmesi Ay = Cs·γ/α1 (HAZUS kapasite eğrisi tanımı),
R = Sa/Ay. C1 = 1 + (R−1)/(a·T²) (T<0,2 s'de T=0,2; T≥1 s'de 1), C2 = 1 + ((R−1)/T)²/800 (T<0,7 s; aksi 1),
a: NEHRP B 130, C 90, D/E 60. KOERI'nin dört analitik yönteminden biri (CM) budur; kapalı form, yinelemesiz, vektörel.
Hasar: P(DS ≥ k | Sd) = Φ(ln(Sd/Sd,k)/β_k), KOERI Tablo 4.3.6.
Can kaybı: KOERI Tablo 4.4.8–4.4.9 (HAZUS oranlarının Kocaeli 1999 deneyimiyle ~5 kat artırılmış hali); çok ağır hasarda
çökmeyen/çöken ayrımı HAZUS-MH çökme oranlarıyla (betonarme 13/10/5 %, yığma 15 %, çelik 8/5/3 %).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import ndtr

KOK = Path(__file__).resolve().parent.parent
L = KOK / "data/raw/literatur"
DS = ["hafif", "orta", "agir", "cokagir"]

kap = pd.read_csv(L / "koeri2010_tablo431_kapasite.csv").set_index("kod")
kir = pd.read_csv(L / "koeri2010_tablo436_kirilganlik.csv").set_index("kod")
for eksik, vekil in (("B231", "B221"), ("B232", "B222"), ("B233", "B223")):  # 0–1 binalık yığma 9+ sınıfları
    kap.loc[eksik] = kap.loc[vekil]; kir.loc[eksik] = kir.loc[vekil]
kap["Ay_g"] = kap.Cs * kap.gamma / kap.alfa1

# yaralanma oranları (%), satır: derece 1..4 (4 = ölüm); sütun: hafif, orta, ağır, çok ağır-çökmeyen, çok ağır-çöken
YARA = {
    "betonarme": np.array([[0.05, 0.2, 1, 10, 50], [0.005, 0.02, 0.5, 8, 15], [0, 0, 0.01, 4, 10], [0, 0, 0.01, 4, 10]]) / 100,
    "yigma": np.array([[0.05, 0.4, 2, 10, 50], [0.005, 0.05, 0.5, 8, 15], [0, 0, 0.002, 5, 10], [0, 0, 0.002, 5, 10]]) / 100,
}
COKME = {("2", "1-4"): .15, ("2", "5-8"): .15, ("2", "9-"): .15, ("4", "1-4"): .08, ("4", "5-8"): .05, ("4", "9-"): .03}


def cokme_orani(tip: str, kat: str) -> float:
    return COKME.get((tip, kat), {"1-4": .13, "5-8": .10, "9-": .05}[kat])


def a_katsayi(vs30: np.ndarray) -> np.ndarray:
    return np.where(vs30 >= 760, 130.0, np.where(vs30 >= 360, 90.0, 60.0))


def sa_periyot(ln_sa: np.ndarray, periyotlar: np.ndarray, T: float) -> np.ndarray:
    """ln Sa'yı log-periyotta doğrusal enterpole eder. ln_sa: (..., P) periyot ekseni sonda."""
    lp = np.log(periyotlar)
    if T <= periyotlar[0]:
        return np.exp(ln_sa[..., 0])
    if T >= periyotlar[-1]:
        return np.exp(ln_sa[..., -1])
    j = np.searchsorted(periyotlar, T) - 1
    w = (np.log(T) - lp[j]) / (lp[j + 1] - lp[j])
    return np.exp((1 - w) * ln_sa[..., j] + w * ln_sa[..., j + 1])


def performans_sd(sa_g: np.ndarray, sinif: str, a: np.ndarray) -> np.ndarray:
    """Spektral yerdeğiştirme talebi (cm)."""
    T = kap.at[sinif, "T_s"]; ay = kap.at[sinif, "Ay_g"]
    sde = sa_g * 981.0 * T**2 / (4 * np.pi**2)
    R = np.maximum(sa_g / ay, 1.0)
    c1 = 1.0 if T >= 1.0 else 1 + (R - 1) / (a * max(T, 0.2) ** 2)
    c2 = 1 + ((R - 1) / T) ** 2 / 800 if T < 0.7 else 1.0
    return c1 * c2 * sde


def hasar_olasilik(sd_cm: np.ndarray, sinif: str, s_beta: float = 1.0, theta: float = 1.0) -> np.ndarray:
    """P(DS = k), k ∈ {yok, hafif, orta, ağır, çok ağır}; son eksen 5.

    s_beta: KOERI β çarpanı (β' = s_beta·β, alt sınır 0,15). KOERI β'sı yer hareketi belirsizliğini de içerdiğinden GMPE σ
    örneklenirken β küçülmelidir; ayrıca gözlemler eğrinin KOERI'den dik olduğunu gösteriyor (hs_03). theta: medyan eşik ölçeği,
    tek sayı ya da dört hasar düzeyi için ayrı (hafif, orta, ağır, çok ağır).
    """
    r = kir.loc[sinif]
    b = {d: max(s_beta * r[f"b_{d}"], 0.15) for d in DS}
    th = dict(zip(DS, theta)) if np.ndim(theta) else dict.fromkeys(DS, theta)
    asim = np.stack([ndtr(np.log(np.maximum(sd_cm, 1e-9) / (th[d] * r[f"sd_{d}_cm"])) / b[d]) for d in DS], -1)
    asim = np.minimum.accumulate(asim, axis=-1)  # olasılıklar azalan sırada kalsın (β farklıyken eğriler kesişebilir)
    return np.concatenate([1 - asim[..., :1], asim[..., :-1] - asim[..., 1:], asim[..., -1:]], -1)


def yaralanma(p_ds: np.ndarray, kisi: np.ndarray, tip: str, kat: str) -> tuple[np.ndarray, np.ndarray]:
    """Dönüş: (derece 1..4 beklenen kişi, son eksen 4), çökmüş binadaki kişi. p_ds son eksen 5 (yok + 4 DS)."""
    c = cokme_orani(tip, kat)
    oran = YARA["yigma" if tip == "2" else "betonarme"]
    dagilim = np.stack([p_ds[..., 1], p_ds[..., 2], p_ds[..., 3], p_ds[..., 4] * (1 - c), p_ds[..., 4] * c], -1)  # (..., 5)
    yara = np.einsum("...s,ds->...d", dagilim, oran) * kisi[..., None]
    return yara, p_ds[..., 4] * c * kisi
