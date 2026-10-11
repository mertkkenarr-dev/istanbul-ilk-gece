"""Boştaki bir ekibin hangi mahalleye gideceği: sevk politikaları.

Hepsi aynı kısıtları paylaşır: ulaşılabilir (sonlu süre), hâlâ canlı sıkışmış kişi var, eş zamanlı ekip sayısı mahalledeki çöken
bina sayısını geçmez (bir binada sınırsız ekip çalışamaz).
  yakin    : en kısa yol süresi. Gerçek hayattaki varsayılan refleks; en yakın enkaza koş.
  fayda    : beklenen kurtarma hızı = kalan canlı / (atanan + 1) / (yol + işlem süresi). Toplam kurtarılanı büyütmeye çalışır.
  esitlik  : fayda × (1 + 2·[henüz ekip görmemiş]) × (1 + yoksunluk). Önce her mahalleye ilk ekibi ulaştırma (max-min kapsama),
             sonra fayda; yoksunluk = sosyal yardım oranı (0–1 ölçekli). Verimlilik–eşitlik ödünleşimini ölçmek için.
  koordineli: merkezi LP planını (optimizasyon.py) izler: o dönemde planlanan ekip sayısının en çok gerisinde kalan
             mahalle (açık / (1 + yol saati)); planlanmış açık kalmadıysa fayda kuralına düşer.
"""
from __future__ import annotations

import numpy as np


def sec(politika: str, sure_sa: np.ndarray, kalan: np.ndarray, atanan: np.ndarray, kapasite: np.ndarray,
        gorulmus: np.ndarray, yoksunluk: np.ndarray, islem_sa: float, hedef: np.ndarray | None = None) -> int:
    """Seçilen mahalle indeksi; uygun mahalle yoksa −1."""
    aday = np.isfinite(sure_sa) & (kalan > 0.5) & (atanan < kapasite)
    if not aday.any():
        return -1
    if politika == "koordineli" and hedef is not None:
        acik = np.where(aday, hedef - atanan, 0.0)
        if (acik > 0.5).any():
            return int(np.argmax(np.where(acik > 0.5, acik / (1.0 + sure_sa), -np.inf)))
        politika = "fayda"
    if politika == "yakin":
        skor = -sure_sa
    else:
        skor = kalan / (atanan + 1.0) / (sure_sa + islem_sa)
        if politika == "esitlik":
            skor = skor * (1.0 + 2.0 * (~gorulmus)) * (1.0 + yoksunluk)
    skor = np.where(aday, skor, -np.inf)
    return int(np.argmax(skor))
