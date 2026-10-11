"""Uzamsal + periyotlar arası korelasyonlu olay içi rezidü alanları (doğrusal korejyonalizasyon modeli, LMC).

Hedef: aynı sahada periyotlar arası korelasyon Baker & Jayaram (2008); her periyodun uzamsal korelasyonu Jayaram & Baker (2009).
OpenQuake olay içi rezidüleri periyotlar arasında bağımsız üretir; bu, bir mahallenin hem kısa hem uzun periyotta aynı anda
"şanslı" ya da "şanssız" olmasını engeller ve toplam kayıp dağılımını olduğundan dar gösterir.

Kurulum: C0 = V Λ Vᵀ (BJ08 matrisinin özayrışımı). Her bileşen j bağımsız bir uzamsal alan, menzili b_j = Σ_m V_mj² b_m
(bileşenin yük taşıdığı periyotların JB09 menzillerinin ağırlıklı ortalaması). Kovaryans C(h) = Σ_j λ_j v_j v_jᵀ ρ_j(h):
pozitif yarı tanımlı matrislerin pozitif ağırlıklı toplamı olduğundan her h için geçerli; h=0'da tam olarak C0'a eşit.
Yaklaşım: her periyodun marjinal uzamsal korelasyonu tek üstel değil üstel karışımıdır (testte sapma raporlanır).
"""
from __future__ import annotations

import numpy as np

BJ_T_MIN = 0.01  # PGA, BJ08'de T=0,01 s ile temsil edilir


def periyot(imt: str) -> float:
    return BJ_T_MIN if imt == "PGA" else float(imt[3:-1])


def bj08(t1: float, t2: float) -> float:
    """Baker & Jayaram (2008) periyotlar arası korelasyon (GMRotI50)."""
    if abs(t1 - t2) < 1e-10:
        return 1.0
    tmin, tmax = min(t1, t2), max(t1, t2)
    c1 = 1 - np.cos(np.pi / 2 - 0.366 * np.log(tmax / max(tmin, 0.109)))
    c2 = 1 - 0.105 * (1 - 1 / (1 + np.exp(100 * tmax - 5))) * (tmax - tmin) / (tmax - 0.0099) if tmax < 0.2 else 0.0
    c3 = c2 if tmax < 0.109 else c1
    c4 = c1 + 0.5 * (np.sqrt(c3) - c3) * (1 + np.cos(np.pi * tmin / 0.109))
    if tmax < 0.109:
        return c2
    if tmin > 0.109:
        return c1
    return min(c2, c4) if tmax < 0.2 else c4


def jb09_menzil(t: float, vs30_kumelenmesi: bool = True) -> float:
    """Jayaram & Baker (2009) eş. 17–19: korelasyon menzili b (km); ρ(h) = exp(−3h/b)."""
    if t >= 1:
        return 22.0 + 3.7 * t
    return 40.7 - 15.0 * t if vs30_kumelenmesi else 8.5 + 17.2 * t


def mesafe_km(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    """Haversine uzaklık matrisi (km)."""
    la, lo = np.radians(lat), np.radians(lon)
    dla = la[:, None] - la[None, :]; dlo = lo[:, None] - lo[None, :]
    a = np.sin(dla / 2) ** 2 + np.cos(la[:, None]) * np.cos(la[None, :]) * np.sin(dlo / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


class LMC:
    def __init__(self, imts: list[str], lon, lat, vs30_kumelenmesi: bool = True, nugget: float = 1e-6):
        self.imts = imts
        T = [periyot(i) for i in imts]
        self.C0 = np.array([[bj08(a, b) for b in T] for a in T])
        lam, V = np.linalg.eigh(self.C0)
        lam = np.clip(lam, 0, None)
        self.lam, self.V = lam, V
        b_imt = np.array([jb09_menzil(t, vs30_kumelenmesi) for t in T])
        self.b_bilesen = (V**2).T @ b_imt
        h = mesafe_km(np.asarray(lon, float), np.asarray(lat, float))
        self.L = []
        for b in self.b_bilesen:
            R = np.exp(-3.0 * h / b)
            R[np.diag_indices_from(R)] += nugget
            self.L.append(np.linalg.cholesky(R))
        self.h = h

    def ornekle(self, n_olay: int, rng: np.random.Generator) -> np.ndarray:
        """Standart normal, korelasyonlu olay içi alan: (n_olay, M, N)."""
        M, N = len(self.imts), self.L[0].shape[0]
        out = np.zeros((n_olay, M, N), np.float32)
        for j in range(M):
            if self.lam[j] < 1e-10:
                continue
            z = (self.L[j] @ rng.standard_normal((N, n_olay))).T  # (E, N)
            out += (np.sqrt(self.lam[j]) * self.V[:, j])[None, :, None] * z[:, None, :]
        return out

    def hedef_korelasyon(self, m: int, h: np.ndarray) -> np.ndarray:
        """Modelin m. periyot için verdiği marjinal uzamsal korelasyon (üstel karışım)."""
        w = self.lam * self.V[m] ** 2
        return (w[None, :] * np.exp(-3.0 * h[:, None] / self.b_bilesen[None, :])).sum(1) / w.sum()
