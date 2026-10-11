"""ders2023 adımlarının ortak yolları; günlük ve QC ana hattın (scripts/ortak.py) dosyalarına yazılır."""
from __future__ import annotations

import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "scripts"))
from ortak import log, qc  # noqa: E402

HAM = KOK / "data/raw/external"
BUYUK = KOK / "data/raw/buyuk"
CIKTI = KOK / "data/processed/ders2023"
CIKTI.mkdir(parents=True, exist_ok=True)
__all__ = ["KOK", "HAM", "BUYUK", "CIKTI", "log", "qc"]
