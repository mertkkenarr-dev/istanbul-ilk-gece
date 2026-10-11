"""USGS ShakeMap ızgarası okuma ve yer hareketi bileşeni dönüşümü.

ShakeMap v4 genlikleri iki yatay bileşenin büyüğüdür (GREATER_OF_TWO); bizim GMPE'lerimiz RotD50 verir. Aynı ölçekte
olmaları için ShakeMap değerleri Boore & Kishida (2017) büyük/RotD50 oranlarıyla bölünür (VARSAYIM: oranlar bölge bağımsız).
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from scipy.interpolate import RegularGridInterpolator

BUYUK_ROTD50 = {"PGA": 1.10, "PSA03": 1.11, "PSA06": 1.12, "PSA10": 1.13, "PGV": 1.11}
AD = {"PGA": "pga", "PSA03": "sa03", "PSA06": "sa06", "PSA10": "sa10", "PGV": "pgv", "SVEL": "vs30", "MMI": "mmi"}


def oku(yol: Path) -> dict:
    txt = yol.read_text()
    spec = dict(re.findall(r'(\w+)="([^"]+)"', re.search(r"<grid_specification([^>]*)/>", txt).group(1)))
    alan = {n: int(i) - 1 for i, n in re.findall(r'<grid_field index="(\d+)" name="(\w+)"', txt)}
    v = np.loadtxt(txt.split("<grid_data>")[1].split("</grid_data>")[0].strip().splitlines(), dtype=np.float32)
    nlon, nlat = int(spec["nlon"]), int(spec["nlat"])
    lon = v[:nlon, alan["LON"]]; lat = v[::nlon, alan["LAT"]][::-1]
    return {"lon": lon, "lat": lat, **{k: v[:, alan[k]].reshape(nlat, nlon)[::-1] for k in AD}}


def ornekle(g: dict, lon: np.ndarray, lat: np.ndarray) -> dict:
    """ln(g) RotD50 (PGV: ln cm/s) ve Vs30; ızgara dışı nokta NaN."""
    out = {}
    for k, ad in AD.items():
        f = RegularGridInterpolator((g["lat"], g["lon"]), g[k], bounds_error=False, fill_value=np.nan)
        x = f(np.c_[lat, lon])
        if k in ("SVEL", "MMI"):
            out[ad] = x
        else:
            birim = 100.0 if k != "PGV" else 1.0
            out[f"ln_{ad}"] = np.log(np.maximum(x / birim / BUYUK_ROTD50[k], 1e-6))
    return out
