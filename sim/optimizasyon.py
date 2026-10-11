"""Eşitlik kısıtlı arama-kurtarma tahsisi: zaman genişletilmiş doğrusal program (HiGHS).

Değişken r_iτ: mahalle i'den τ döneminde canlı kurtarılan ağır sıkışmış kişi sayısı.
  Sağ kalma (doğrusal): τ döneminde canlı kurtarılan bir kişi, başlangıçtaki 1/S(t_τ) kurbanı temsil eder
                       ⇒ Σ_{τ' ≤ τ} r_iτ' / S(t_τ') ≤ H_i
  Ekip kapasitesi    : Σ_i r_iτ · süre ≤ (dönemde mevcut ekip-saat) · (1 − yol payı)
  Eş zamanlılık      : r_iτ · süre ≤ (çöken bina sayısı) · dönem uzunluğu      (bir binada sınırlı ekip çalışabilir)
  Ulaşılabilirlik    : dönem başında hiçbir üsten ulaşılamıyorsa r_iτ = 0
  Eşitlik (z)        : Σ_τ r_iτ ≥ z · H_i · Smax_i     (Smax_i: o mahalle için ulaşılabilir ilk dönemdeki sağ kalma; ulaşılabilir
                       olmayan mahalle kısıttan muaf). z = 0 verimlilik çözümü, z arttıkça adaletin bedeli (Bertsimas vd. 2011).
Çıktı: plan[i, τ] = o dönemde mahallede bulunması hedeflenen ortalama ekip sayısı (simülatörde "koordineli" politika izler).
"""
from __future__ import annotations

import numpy as np
from ag_hasar import DONEM
from parametreler import Parametre, sag_kalma
from scipy.optimize import linprog
from scipy.sparse import lil_matrix

SINIR = np.array([0, 3, 6, 12, 24, 48, 72.0])
YOL_PAYI = 0.25


def ekip_saat(par: Parametre) -> np.ndarray:
    """Dönem başına beklenen ekip-saat (takvimden, uniform gelişler analitik)."""
    out = np.zeros(len(SINIR) - 1)
    for k, (a, b) in enumerate(zip(SINIR[:-1], SINIR[1:])):
        sure = lambda bas: np.clip(b - np.maximum(a, bas), 0, b - a)
        out[k] = par.n_ibb_ilk * sure(0.0) + par.n_ibb_cagri * sure(3.0)
        u = np.linspace(6, 24, 200); out[k] += par.n_ulusal * sure(u).mean()
        u = np.linspace(24, 48, 200); out[k] += par.n_uluslararasi * sure(u).mean()
    return out * (1 - YOL_PAYI)


def plan_coz(H: np.ndarray, kapasite: np.ndarray, ulasilir: np.ndarray, par: Parametre, z: float = 0.0,
             agirlik: np.ndarray | None = None) -> dict:
    """H: mahalle başına ağır sıkışmış canlı (t=0). ulasilir: (N, dönem) bool. Dönüş: plan, amaç, durum."""
    I = np.where(H > 0.5)[0]; n, T = len(I), len(SINIR) - 1
    orta = (SINIR[:-1] + SINIR[1:]) / 2
    S = sag_kalma(orta, par.weibull_olcek)
    L = np.diff(SINIR); tr = par.kurtarma_sure_sa
    v = lambda i, t: i * T + t
    w = np.ones(n) if agirlik is None else agirlik[I]
    c = -np.repeat(w, T)
    ub = np.zeros(n * T)
    for a, i in enumerate(I):
        for t in range(T):
            ub[v(a, t)] = (kapasite[i] * L[t] / tr) if ulasilir[i, t] else 0.0
    A = lil_matrix((n * T + T + n, n * T)); b = np.zeros(n * T + T + n); r = 0
    for a, i in enumerate(I):                       # sağ kalma kümülatif
        for t in range(T):
            for t2 in range(t + 1):
                A[r, v(a, t2)] = 1 / S[t2]
            b[r] = H[i]; r += 1
    he = ekip_saat(par)
    for t in range(T):                              # ekip kapasitesi
        for a in range(n):
            A[r, v(a, t)] = tr
        b[r] = he[t]; r += 1
    smax = np.array([S[np.argmax(ulasilir[i])] if ulasilir[i].any() else 0.0 for i in I])
    for a, i in enumerate(I):                       # eşitlik: −Σ r ≤ −z·H·Smax
        if smax[a] > 0 and z > 0:
            for t in range(T):
                A[r, v(a, t)] = -1
            b[r] = -z * H[i] * smax[a]
        r += 1
    res = linprog(c, A_ub=A.tocsr()[:r], b_ub=b[:r], bounds=list(zip(np.zeros(n * T), ub)), method="highs")
    plan = np.zeros((len(H), T))
    if res.status == 0:
        x = res.x.reshape(n, T)
        plan[I] = x * tr / L[None, :]
        oran = np.where(smax > 0, x.sum(1) / (H[I] * np.maximum(smax, 1e-9)), np.nan)
        return dict(durum="optimal", plan=plan, kurtarilan=float(x.sum()), min_oran=float(np.nanmin(oran)), z=z)
    return dict(durum="olurlu_degil", plan=plan, kurtarilan=np.nan, min_oran=np.nan, z=z)


def ulasilabilirlik(mats: list[dict], us_ix: np.ndarray) -> np.ndarray:
    """(N, LP dönemi) – herhangi bir üsten sonlu süreyle ulaşılabilir mi (o LP döneminin başındaki yol dönemine göre)."""
    out = []
    for a in SINIR[:-1]:
        d = int(np.searchsorted(DONEM, a, side="right") - 1)
        out.append(np.isfinite(mats[d]["us_mah"][us_ix]).any(0))
    return np.stack(out, 1)
