"""Simülasyon parametreleri: varsayılan değer, belirsizlik aralığı ve kaynak. Duyarlılık ve ML vekil modeli bu aralıkları örnekler.

Tutarlılık kuralı: hasar modeli (hs_02) çöken binadaki kişilerin ~%10'unun öldüğünü varsayar ve κ≈1 ile 1999 İstanbul'a
kalibredir. Simülatör bu %10'u "anında ölüm + kurtarılamadan ölüm" olarak zamana yayar; 1999'a benzer yavaş müdahalede
toplam ~%10–12'ye çıkacak şekilde sıkışma payı seçildi (p_sikisma × (p_aninda + (1−p_aninda)·~0,45) ≈ 0,11).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields

import numpy as np
from scipy.optimize import curve_fit

# Coburn vd. (1992) / Coburn & Spence (2002): kurtarılanlar içinde canlı çıkanların payı, kurtarma gününe göre.
# İlk 30 dk %91 ⇒ anında ölüm ~%9 kabul edilip canlı sıkışanların sağ kalma eğrisi S(t)/0,91 olarak uydurulur.
COBURN_SAAT = np.array([0.5, 12, 36, 60, 84, 108])
COBURN_CANLI = np.array([0.91, 0.81, 0.36, 0.33, 0.19, 0.07])


def _weibull(t, lam, k):
    return np.exp(-(t / lam) ** k)


WEIBULL_LAM, WEIBULL_K = curve_fit(_weibull, COBURN_SAAT, COBURN_CANLI / 0.91, p0=(40, 1.2), bounds=([5, 0.3], [300, 4]))[0]


@dataclass
class Parametre:
    # --- enkaz ve kurbanlar ---
    p_sikisma: float = 0.20        # çöken binadaki kişilerin enkaz altında kalan payı [0,12–0,30]; yukarıdaki tutarlılık kuralı
    p_aninda: float = 0.20         # sıkışanlardan çökme anında ölen [0,10–0,35]; Coburn M4 (BA %40 üst sınır)
    p_hafif_sikisma: float = 0.50  # sıkışanlardan komşuların elle çıkarabileceği [0,30–0,70]; Noji (1997), Macintyre (2006)
    weibull_olcek: float = 1.0     # sağ kalma eğrisi zaman ölçeği çarpanı [0,75–1,25]
    # --- toplum kurtarması ---
    toplum_hiz: float = 0.15       # hafif sıkışmış başına saatlik kurtarma hazardı (hasarsız mahallede) [0,05–0,30]
    # --- profesyonel ekipler (İBB İtfaiye 2025: 5.082 personel, 173 kurtarma aracı; gece vardiyası ~1/3) ---
    n_ibb_ilk: int = 120           # t=0'da çıkabilen İBB kurtarma ekibi [80–170]
    n_ibb_cagri: int = 60          # izinli personelin çağrılmasıyla t≈3 sa'te eklenen [0–120]
    n_ulusal: int = 300            # AFAD + diğer iller, 6–24 sa arası doğu/batı kapısından [100–600]
    n_uluslararasi: int = 80       # INSARAG ekipleri, 24–48 sa, havalimanlarından [0–200]
    kurtarma_sure_sa: float = 3.0  # ağır sıkışmış bir kişiyi çıkarma süresi (ekip-saat) [2–6]
    # --- yol ağı ---
    enkaz_a: float = 0.04          # kapanma olasılığı 1−exp(−a·yoğunluk), yoğunluk = ağır+ bina / mahalle yol km [0,02–0,10]
    temizleme_sa: float = 24.0     # enkazla kapanan kenarın ortalama açılma süresi [12–48]; İBB 1. derece acil yollar ×1/3
    p_eski_kopru: float = 0.3      # köprülerin HAZUS HWB5 (eski, basit mesnetli) payı, kalanı HWB10 [0,1–0,5]; otoyol yapılarının çoğu 1990 sonrası
    trafik_carpan: float = 1.0     # sıkışıklık çarpanı ölçeği (0–6 sa ×2,5; 6–24 sa ×1,8; sonrası ×1,3) [0,7–1,5]
    # --- hastane ---
    bos_yatak_payi: float = 0.30   # gece boş yatak payı [0,20–0,40] (doluluk ~%70)
    tahliye_carpan: float = 1.5    # taburcu + koridor ile genişleme [1,2–2,0]
    agir_bekleme_hazard: float = 0.010  # tedavi edilemeyen ağır yaralının saatlik ölüm hazardı [0,005–0,02]
    agir_tedavili_olum: float = 0.05    # tedavi edilen ağır yaralıda ölüm payı [0,02–0,10]
    # --- politika ---
    politika: str = "fayda"        # yakin | fayda | esitlik | koordineli

    def sozluk(self) -> dict:
        return asdict(self)


ARALIK = {
    "p_sikisma": (0.12, 0.30), "p_aninda": (0.10, 0.35), "p_hafif_sikisma": (0.30, 0.70), "weibull_olcek": (0.75, 1.25),
    "toplum_hiz": (0.05, 0.30), "n_ibb_ilk": (80, 170), "n_ibb_cagri": (0, 120), "n_ulusal": (100, 600), "n_uluslararasi": (0, 200),
    "kurtarma_sure_sa": (2.0, 6.0), "enkaz_a": (0.02, 0.10), "temizleme_sa": (12.0, 48.0), "p_eski_kopru": (0.1, 0.5),
    "trafik_carpan": (0.7, 1.5), "bos_yatak_payi": (0.20, 0.40), "tahliye_carpan": (1.2, 2.0), "agir_bekleme_hazard": (0.005, 0.02),
    "agir_tedavili_olum": (0.02, 0.10),
}
TAMSAYI = {f.name for f in fields(Parametre) if f.type in ("int", int)}
# Karar kolları: müdahale tasarımıyla değiştirilebilenler. Geri kalanlar fiziksel/bilgi belirsizliğidir ve hep örneklenir.
KOL = ("n_ibb_ilk", "n_ibb_cagri", "n_ulusal", "n_uluslararasi", "temizleme_sa", "tahliye_carpan")
AG_PARAM = ("enkaz_a", "p_eski_kopru", "temizleme_sa")  # değişirse yol matrisleri yeniden hesaplanır


def orneklem(n: int, rng: np.random.Generator, sabit: dict | None = None, adlar=None) -> list[Parametre]:
    """Latin hiperküp örneklemesi: her parametre aralığı n eşit dilime bölünür, her dilimden bir değer (McKay vd. 1979).
    adlar verilirse yalnızca onlar örneklenir, diğerleri varsayılan kalır."""
    out = [dict() for _ in range(n)]
    for ad, (lo, hi) in ARALIK.items():
        if adlar is not None and ad not in adlar:
            continue
        u = (rng.permutation(n) + rng.random(n)) / n
        for i in range(n):
            v = lo + u[i] * (hi - lo)
            out[i][ad] = int(round(v)) if ad in TAMSAYI else float(v)
    return [Parametre(**{**o, **(sabit or {})}) for o in out]


def sag_kalma(t_sa: np.ndarray, olcek: float = 1.0) -> np.ndarray:
    return _weibull(np.asarray(t_sa, float), WEIBULL_LAM * olcek, WEIBULL_K)


if __name__ == "__main__":
    print(f"Weibull uyumu (canlı sıkışanlar): λ = {WEIBULL_LAM:.1f} sa, k = {WEIBULL_K:.2f}")
    for t, c in zip(COBURN_SAAT, COBURN_CANLI / 0.91):
        print(f"  {t:5.1f} sa: veri {c:.2f}, model {sag_kalma(t):.2f}")
    print("  72 sa:", round(float(sag_kalma(72)), 3))
