"""GHSL R2023A (JRC) 3 yay-saniyelik katmanlarından iki bölgede birebir aynı tanımla hücre öznitelikleri.

Neden GHSL: bina yaşı ve kat sayısı ne Hatay'da ne İstanbul'da bina bazında açık veri olarak var. GHSL, Landsat/Sentinel
arşivinden 1975–2020 arası her 5 yılda bir hücredeki yapılı alanı ve 2018 ortalama bina yüksekliğini verir; iki bölge için
aynı algoritmayla üretildiği için "6 Şubat'ta öğren, İstanbul'a uygula" aktarımının ortak dili budur.
Öznitelikler (hepsi TÜRETİLMİŞ):
  yapili_2020        hücrede yapılı alan oranı (0–1)
  pay_1975…pay_2010  2020 yapılı alanının o yıl zaten var olan payı (yapılaşma dönemi; 1975 = "1975 ve öncesi")
  yapilasma_yili     yapılı alanın yarısına ulaşılan dönem (medyan yapılaşma yılı)
  yukseklik_m        ortalama bina yüksekliği (AGBH 2018)
  k_*                aynı büyüklüklerin ~450 m (5×5 hücre) komşuluk ortalaması: blok/mahalle dokusu
"""
from __future__ import annotations

import glob

import numpy as np
import rasterio
from ortak_ders import BUYUK
from rasterio.windows import from_bounds
from scipy.ndimage import uniform_filter

DONEM = [1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020]
PAY = [1975, 1990, 2000, 2010]


def _dosya(desen: str, tile: str) -> str:
    f = glob.glob(str(BUYUK / f"ghsl/{desen}*{tile}*.tif"))
    assert len(f) == 1, (desen, tile, f)
    return f[0]


def katmanlar(bbox: tuple[float, float, float, float], tile: str) -> dict:
    """bbox (lon0, lat0, lon1, lat1) penceresi için öznitelik ızgaraları + ızgaranın dönüşümü."""
    out, s = {}, {}
    for e in DONEM:
        with rasterio.open(_dosya(f"GHS_BUILT_S_E{e}_", tile)) as r:
            w = from_bounds(*bbox, r.transform).round_offsets().round_lengths()
            s[e] = r.read(1, window=w).astype(np.float32)
            tr = r.window_transform(w)
    with rasterio.open(_dosya("GHS_BUILT_H_AGBH", tile)) as r:
        h = r.read(1, window=from_bounds(*bbox, r.transform).round_offsets().round_lengths()).astype(np.float32)
    lat = tr.f + tr.e * (np.arange(s[2020].shape[0]) + 0.5)
    hucre_m2 = (abs(tr.e) * 111_320) * (tr.a * 111_320 * np.cos(np.radians(lat)))[:, None]
    s20 = np.maximum(s[2020], 1e-6)
    out["yapili_2020"] = np.clip(s[2020] / hucre_m2, 0, 1)
    for e in PAY:
        out[f"pay_{e}"] = np.where(s[2020] > 0, np.minimum(s[e] / s20, 1), np.nan)
    yari = np.full(s20.shape, np.nan, np.float32)
    for e in reversed(DONEM):
        yari = np.where((s[2020] > 0) & (s[e] >= 0.5 * s[2020]), e, yari)
    out["yapilasma_yili"] = yari
    out["yukseklik_m"] = np.where(s[2020] > 0, h, np.nan)
    for k in ("yapili_2020", "pay_1990", "pay_2000", "yukseklik_m"):
        a = out[k]; m = np.isfinite(a)
        pay = uniform_filter(np.where(m, a, 0) * (out["yapili_2020"] if k != "yapili_2020" else 1), 5)
        payda = uniform_filter(m * (out["yapili_2020"] if k != "yapili_2020" else 1.0), 5)
        out[f"k_{k}"] = (pay / np.maximum(payda, 1e-9)) if k != "yapili_2020" else pay
    out["_tr"] = tr
    return out


def ornekle(kat: dict, lon: np.ndarray, lat: np.ndarray) -> dict:
    tr = kat["_tr"]
    c = np.floor((np.asarray(lon) - tr.c) / tr.a).astype(int)
    r = np.floor((np.asarray(lat) - tr.f) / tr.e).astype(int)
    n, m = kat["yapili_2020"].shape
    assert (c >= 0).all() and (c < m).all() and (r >= 0).all() and (r < n).all(), "nokta pencere dışında"
    return {k: v[r, c] for k, v in kat.items() if not k.startswith("_")} | {"hucre": r * m + c}
