"""Yer hareketi modelinin ortak parçaları: aday GMPE'ler, kırılma yüzeyi, OpenQuake bağlamları.

OpenQuake (GEM) yalnızca medyan ve sigma bileşenleri için kullanılır; alan simülasyonu yh_korelasyon.py'de kendi kodumuzdur.
Bu modül .venv-oq (Python 3.12) ortamında çalışır; OpenQuake 3.14 ile uyumlu değil.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from openquake.hazardlib import valid
from openquake.hazardlib.contexts import simple_cmaker
from openquake.hazardlib.geo import Line, Point
from openquake.hazardlib.geo.surface import SimpleFaultSurface
from openquake.hazardlib.site import SiteCollection
from openquake.hazardlib.source.rupture import BaseRupture

KOK = Path(__file__).resolve().parent.parent
CIKTI = KOK / "data" / "processed" / "yer_hareketi"
CIKTI.mkdir(parents=True, exist_ok=True)

# Aday modeller. AbrahamsonSilva2008: İBB/KOERI 2010–2019 kayıp çalışmasının kullandığı denklem (rapor §2.1).
GMPE = {
    "ASB14": "AkkarEtAlRjb2014",        # Avrupa–Orta Doğu, Türkiye kayıtları ağırlıklı
    "KAA15": "KaleEtAl2015Turkey",      # Türkiye'ye özgü
    "BSSA14": "BooreEtAl2014",          # NGA-West2
    "CY14": "ChiouYoungs2014",          # NGA-West2
    "ASK14": "AbrahamsonEtAl2014",      # NGA-West2
    "CB14": "CampbellBozorgnia2014",    # NGA-West2
    "CEA14": "CauzziEtAl2014",          # küresel, Japonya ağırlıklı
    "AS08": "AbrahamsonSilva2008",      # İBB senaryosunun denklemi (NGA-West1)
}
IMT_DOGRULAMA = ["PGA", "SA(0.3)", "SA(1.0)", "SA(3.0)"]
# Hasar modelinin ihtiyaç duyduğu periyotlar: KOERI kapasite tablosundaki bina periyotları (0,3–1,2 s) + PGA
IMT_SENARYO = ["PGA", "SA(0.3)", "SA(0.4)", "SA(0.55)", "SA(0.75)", "SA(0.9)", "SA(1.2)"]


def gsim(kisa: str):
    return valid.gsim(GMPE[kisa])


def z1pt0_cy14(vs30: np.ndarray) -> np.ndarray:
    """Chiou & Youngs (2014) Kaliforniya z1.0 – Vs30 bağıntısı (m). Havza derinliği verisi yok; vekil kullanılır."""
    return np.exp(-7.15 / 4 * np.log((vs30**4 + 571.0**4) / (1360.0**4 + 571.0**4)))


def z2pt5_cb14(vs30: np.ndarray) -> np.ndarray:
    """Campbell & Bozorgnia (2014) Kaliforniya z2.5 – Vs30 bağıntısı (km)."""
    return np.exp(7.089 - 1.144 * np.log(vs30))


def sahalar(lon, lat, vs30) -> SiteCollection:
    lon, lat, vs30 = map(np.asarray, (lon, lat, vs30))
    arr = np.zeros(len(lon), dtype=[("sids", np.uint32), ("lon", float), ("lat", float), ("depth", float), ("vs30", float),
                                     ("vs30measured", bool), ("z1pt0", float), ("z2pt5", float), ("backarc", bool)])
    arr["sids"] = np.arange(len(lon)); arr["lon"] = lon; arr["lat"] = lat; arr["vs30"] = vs30
    arr["z1pt0"] = z1pt0_cy14(vs30); arr["z2pt5"] = z2pt5_cb14(vs30)
    sc = object.__new__(SiteCollection)
    sc.array = arr; sc.complete = sc
    return sc


def kirilma(iz: list[tuple[float, float]], mw: float, ust_km: float, alt_km: float, egim: float = 90.0,
            rake: float = 180.0, hipo: tuple[float, float, float] | None = None) -> BaseRupture:
    """Fay izi boyunca düzlemsel kırılma. Varsayılan: düşey (90°), sağ yanal doğrultu atımlı (rake 180)."""
    yuzey = SimpleFaultSurface.from_fault_data(Line([Point(x, y) for x, y in iz]), ust_km, alt_km, egim, 1.0)
    if hipo is None:
        m = yuzey.mesh; i, j = m.shape[0] // 2, m.shape[1] // 2
        hipo = (float(m.lons[i, j]), float(m.lats[i, j]), (ust_km + alt_km) / 2)
    return BaseRupture(mw, rake, "Active Shallow Crust", Point(*hipo), yuzey)


def medyan_sigma(kisalar: list[str], rup: BaseRupture, sc: SiteCollection, imts: list[str]):
    """Tüm GMPE'ler tek bağlamla: dönüş (ln medyan, sigma, tau, phi) her biri (G, M, N) ve bağlam (saha sırasında)."""
    cm = simple_cmaker([gsim(k) for k in kisalar], imts, mags=[f"{rup.mag:.2f}"], truncation_level=99.0)
    ctx = list(cm.get_ctxs([rup], sc))[0]
    if len(ctx) != len(sc):
        raise ValueError(f"{len(sc) - len(ctx)} saha mesafe süzgecinde düştü")
    sira = np.argsort(ctx.sids)
    ms = cm.get_mean_stds([ctx[sira]])  # (4, G, M, N)
    return ms[0], ms[1], ms[2], ms[3], ctx[sira]


def iz_yonu(iz: np.ndarray, lon: float, lat: float) -> float:
    """İzin verilen noktaya en yakın parçasının doğrultusu (derece, kuzeyden saat yönü)."""
    d = np.hypot((iz[:, 0] - lon) * np.cos(np.radians(lat)), iz[:, 1] - lat)
    i = int(np.clip(np.argmin(d), 0, len(iz) - 2))
    dx = (iz[i + 1, 0] - iz[i, 0]) * np.cos(np.radians(lat)); dy = iz[i + 1, 1] - iz[i, 1]
    return float(np.degrees(np.arctan2(dx, dy)) % 360)
