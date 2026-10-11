"""Hattın tüm adımlarının paylaştığı yollar, ad normalleştirme ve karar günlüğü.

Karar günlüğü (temizleme_logu) her adımda JSONL'a eklenir ve 09_yayinla.py'de veritabanına yazılır;
böylece hangi kararın hangi betikte, kaç kaydı etkileyerek alındığı tek tabloda izlenebilir.
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
RAW = KOK / "data" / "raw"
IBB = RAW / "ibb"
EXT = RAW / "external"
BUYUK = RAW / "buyuk"
USGS = RAW / "usgs_silivri_2025"
INTERIM = KOK / "data" / "interim"
PROCESSED = KOK / "data" / "processed"
DOCS = KOK / "docs"
for _d in (INTERIM, PROCESSED, DOCS):
    _d.mkdir(parents=True, exist_ok=True)

LOG_DOSYA = INTERIM / "temizleme_logu.jsonl"
QC_DOSYA = INTERIM / "kalite_kontrol.jsonl"

# Metrik projeksiyon: İstanbul UTM 35N içinde kalır, mesafe/alan hesapları burada yapılır.
CRS_METRIK = 32635
CRS_GEO = 4326

_TR = str.maketrans({"İ": "i", "I": "i", "ı": "i", "Ş": "s", "ş": "s", "Ğ": "g", "ğ": "g",
                     "Ü": "u", "ü": "u", "Ö": "o", "ö": "o", "Ç": "c", "ç": "c", "Â": "a", "â": "a"})
# Ek yalnızca ayrı bir kelimeyse atılır: "Yenimahalle" adın kendisidir, "Yeni Mahalle Mahallesi" -> "yeni".
_EKLER = re.compile(r"\s+(mahallesi|mahalesi|mahalle|mah|mh|koyu|beldesi)$")


def katla(s: object) -> str:
    """Türkçe adları karşılaştırılabilir anahtara indirger: büyük/küçük harf, aksan, boşluk ve 'Mah.' eki farkı yok sayılır."""
    if s is None:
        return ""
    t = str(s).strip().translate(_TR).lower()
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"\(.*?\)", "", t)
    t = re.sub(r"[^a-z0-9 ]+", " ", t).strip()
    while (yeni := _EKLER.sub("", t).strip()) != t:
        t = yeni
    return re.sub(r"\s+", "", t)


ILCE_ESANLAM = {"eyup": "eyupsultan"}

# (ilçe, eski/farklı ad) -> İBB senaryo tablosundaki ad. Her satır kanıtıyla temizleme_logu'na yazılır.
MAHALLE_ESANLAM = {
    ("bagcilar", "15temmuz"): "evren",          # Evren Mah. 2016'da 15 Temmuz adını aldı
    ("buyukcekmece", "mimarsinan"): "mimarsinanmerkez",
    ("bayrampasa", "orta"): "ortamahalle",       # İBB 2017 'ORTAMAHALLE', diğer kaynaklar 'ORTA'
}

_AYLAR = ["OCAK", "ŞUBAT", "MART", "NİSAN", "MAYIS", "HAZİRAN", "TEMMUZ", "AĞUSTOS", "EYLÜL", "EKİM", "KASIM", "ARALIK"]
_AY_EN = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}


def excel_tarih_onar(v: object) -> tuple[object, bool]:
    """Excel'in '19 MAYIS' gibi adları tarihe çevirmesini geri alır ('19.May', datetime 2026-05-19 -> '19 MAYIS')."""
    if hasattr(v, "day") and hasattr(v, "month"):
        return f"{v.day} {_AYLAR[v.month - 1]}", True
    m = re.fullmatch(r"(\d{1,2})[.\- ]([A-Za-z]{3})", str(v).strip())
    if m and m.group(2).lower() in _AY_EN:
        return f"{int(m.group(1))} {_AYLAR[_AY_EN[m.group(2).lower()] - 1]}", True
    return v, False


def mahalle_anahtar(ilce_k: str, ad: object) -> str:
    k = katla(ad)
    return MAHALLE_ESANLAM.get((ilce_k, k), k)


def ilce_katla(s: object) -> str:
    k = katla(s)
    return ILCE_ESANLAM.get(k, k)


def log(adim: str, katman: str, sorun: str, etkilenen: int, karar: str, gerekce: str) -> None:
    kayit = dict(zaman=datetime.now().isoformat(timespec="seconds"), adim=adim, katman=katman, sorun=sorun,
                 etkilenen=int(etkilenen), karar=karar, gerekce=gerekce)
    with LOG_DOSYA.open("a", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")


def qc(adim: str, kontrol: str, gecti: bool, detay: str) -> None:
    kayit = dict(adim=adim, kontrol=kontrol, sonuc="GEÇTİ" if gecti else "KALDI", detay=detay)
    with QC_DOSYA.open("a", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
    print(f"  [{'OK' if gecti else '!!'}] {kontrol}: {detay}")


def adim_temizle(adim: str) -> None:
    """Bir adım yeniden çalıştırılınca eski log/QC satırlarını siler; günlük her zaman son çalıştırmayı yansıtır."""
    for dosya in (LOG_DOSYA, QC_DOSYA):
        if not dosya.exists():
            continue
        satirlar = [s for s in dosya.read_text(encoding="utf-8").splitlines() if s and json.loads(s)["adim"] != adim]
        dosya.write_text("".join(s + "\n" for s in satirlar), encoding="utf-8")
