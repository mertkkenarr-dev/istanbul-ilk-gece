"""Sitenin kullandığı veri dosyalarını data/processed/web_tiles'tan web/public/veri'ye kopyalar.
Üretim ile yayın ayrı: hat istediği kadar ara dosya üretir, site yalnızca bu listedekileri sunar (sembolik bağ değil gerçek kopya,
çünkü statik barındırma bağları izlemez).
"""
from __future__ import annotations

import shutil
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
T = KOK / "data/processed/web_tiles"; OUT = KOK / "web/public/veri"
DOSYA = {  # yayındaki ad: üretimdeki ad
    "altlik.pmtiles": "istanbul_altlik.pmtiles", "binalar.pmtiles": "binalar.pmtiles", "toplanma_akis.json": "toplanma_akis.json",
    "ilce_cikis.json": "ilce_cikis.json", "istanbul_yersiz.json": "istanbul_yersiz.json", "maket.json": "maket.json",
}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for ad, kaynak in DOSYA.items():
        shutil.copyfile(T / kaynak, OUT / ad)
        print(f"{ad:24s} {(OUT / ad).stat().st_size / 1e6:7.2f} MB")
