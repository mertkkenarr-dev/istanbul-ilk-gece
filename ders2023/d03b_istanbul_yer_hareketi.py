"""OpenQuake ortamında (.venv-oq): Mw 7,5 senaryosunun blok sahalarında mantık ağacı ağırlıklı ln medyanı (ε = 0).

Senaryo ve ağırlıklar model/yh_03 ile birebir aynı; tek fark IMT seti ShakeMap'in verdiği periyotlara (PGA, 0,3, 0,6, 1,0 s)
eşitlenir, çünkü vekil 2023'te bu IMT'lerle eğitildi.
Çıktı: data/processed/ders2023/istanbul_saha_medyan.parquet
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "model"))
from yh_ortak import CIKTI as YH  # noqa: E402
from yh_ortak import GMPE, kirilma, medyan_sigma, sahalar  # noqa: E402

IMT = ["PGA", "SA(0.3)", "SA(0.6)", "SA(1.0)"]
s = pd.read_parquet(KOK / "data/processed/ders2023/istanbul_saha.parquet")
iz = json.loads((KOK / "data/raw/external/gem_marmara_faults.geojson").read_text())["features"][1]
rup = kirilma([tuple(c) for c in iz["geometry"]["coordinates"]], 7.5, 0.0, 15.0)
kisa = list(GMPE)
w = pd.Series(json.loads((YH / "mantik_agaci.json").read_text())["agirlik"])[kisa].values
parca = []
for i in range(0, len(s), 20000):
    d = s.iloc[i:i + 20000]
    mu, _, _, _, ctx = medyan_sigma(kisa, rup, sahalar(d.lon, d.lat, d.vs30), IMT)
    lm = (w[:, None, None] * mu).sum(0)
    parca.append(pd.DataFrame({"blok": d.blok.values, "rjb_km": ctx.rjb, **{f"ln_{k}": lm[j] for j, k in enumerate(["pga", "sa03", "sa06", "sa10"])}}))
o = pd.concat(parca, ignore_index=True)
o.to_parquet(KOK / "data/processed/ders2023/istanbul_saha_medyan.parquet", index=False)
print(f"{len(o)} blok; medyan PGA {np.exp(o.ln_pga).median():.3f} g (%5–95: {np.exp(o.ln_pga.quantile(.05)):.3f}–{np.exp(o.ln_pga.quantile(.95)):.3f})")
