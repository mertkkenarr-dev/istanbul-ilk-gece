"""Veri hattını baştan sona çalıştırır: python scripts/hat.py [--temiz]

--temiz: data/interim ve data/processed silinir; her şey ham veriden yeniden üretilir (tekrar üretilebilirlik testi).
Bir adım hata verirse hat durur; kalite kontrolünde KALDI çıkan adım hattı durdurmaz ama sonda listelenir.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
ADIMLAR = ["00_indir", "01_istanbul_kirp", "02_mahalle_tablosu", "03_mahalle_sinirlari", "04_tesisler", "05_yol_agi",
           "06_zemin_bina", "07_yer_hareketi_gozlem", "08_birlestir", "09_yayinla"]

if "--temiz" in sys.argv:
    for d in ("data/interim", "data/processed"):
        shutil.rmtree(KOK / d, ignore_errors=True)

t0 = time.time()
for a in ADIMLAR:
    t = time.time()
    r = subprocess.run([sys.executable, "-W", "ignore", str(KOK / "scripts" / f"{a}.py")], cwd=KOK)
    if r.returncode:
        sys.exit(f"HATA: {a} (kod {r.returncode})")
    print(f"  [{time.time() - t:5.0f} sn] {a}\n")

qc = [json.loads(s) for s in (KOK / "data/interim/kalite_kontrol.jsonl").read_text(encoding="utf-8").splitlines() if s]
kalan = [q for q in qc if q["sonuc"] != "GEÇTİ"]
print(f"Hat bitti: {time.time() - t0:.0f} sn, {len(qc)} kontrol, {len(kalan)} KALDI")
for q in kalan:
    print(f"  KALDI  {q['adim']}: {q['kontrol']} ({q['detay']})")
