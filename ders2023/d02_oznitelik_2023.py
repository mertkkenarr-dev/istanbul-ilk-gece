"""Etiketli 2023 binalarına sarsıntı (iki ana şokun hücre başına büyüğü), zemin ve GHSL öznitelikleri.

İki ana şok (Pazarcık Mw 7,8 ve Elbistan Mw 7,5) aynı gün oldu ve uydu görüntüleri ikisinden sonra alındı: hasar ikisinin
birleşik etkisidir. Hücre başına her IMT'de iki ShakeMap'in büyüğü alınır (birikimli hasarın ilk yaklaşımı; VARSAYIM).
Kapsam kontrolü: AOI'deki etiketli bina sayısı / GHSL yapılı alanı. Copernicus bazı AOI'lerde yalnızca bir kısmı
sınıflandırmış; bu oran diğerlerinin çok altındaysa AOI kısmi sayılır ve dışlanır (log).
Çıktı: data/processed/ders2023/egitim.parquet
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import sarsinti
from ghsl import katmanlar, ornekle
from ortak_ders import CIKTI, HAM, log, qc

ADIM = "d02_oznitelik_2023"
e = pd.read_parquet(CIKTI / "etiket.parquet")
g1 = sarsinti.oku(HAM / "usgs_2023/jllz_grid.xml"); g2 = sarsinti.oku(HAM / "usgs_2023/jlqa_grid.xml")
a, b = sarsinti.ornekle(g1, e.lon.values, e.lat.values), sarsinti.ornekle(g2, e.lon.values, e.lat.values)
for k in a:
    e[k] = a[k] if k == "vs30" else np.fmax(a[k], b[k])
e["baskin_sok"] = np.where(a["ln_pga"] >= np.nan_to_num(b["ln_pga"], nan=-99), "Pazarcik", "Elbistan")

kat = katmanlar((35.6, 35.9, 40.0, 38.5), "R6_C22")
f = ornekle(kat, e.lon.values, e.lat.values)
for k, v in f.items():
    e[k] = v
bos = e.yapili_2020 <= 0
log(ADIM, "GHSL", "Bazı etiketli binalar GHSL'de yapılı görünmeyen hücreye düşüyor (yeni yapı / sınır / konum kayması)", int(bos.sum()),
    "Yapılaşma öznitelikleri NaN bırakıldı (LightGBM eksik değeri ayrı dal olarak işler), satır silinmedi",
    "Silmek yalnızca kırsal/çevre binaları sistematik olarak dışlardı")

# kapsam: etiket yoğunluğu (bina / ha yapılı alan) AOI başına
hucre = e.groupby(["aoi", "hucre"]).agg(n=("yikik", "size"), yapili=("yapili_2020", "first")).reset_index()
kap = hucre.groupby("aoi").apply(lambda d: d.n.sum() / max(d.yapili.sum() * 0.66, 1e-9), include_groups=False).rename("bina_per_ha")
med = kap.median()
kismi = kap[kap < med / 4].index.tolist()
print(kap.round(1).sort_values().to_string())
log(ADIM, "Copernicus EMSR648", f"Etiket yoğunluğu medyanın 1/4'ünden düşük AOI'ler kısmi sınıflandırılmış: {', '.join(kismi) or 'yok'}",
    int(e.aoi.isin(kismi).sum()), "Kısmi AOI'ler eğitimden çıkarıldı",
    "Kısmi sınıflandırmada hasarlı binalar öncelikle işaretlendiğinden yıkım oranı yukarı yanlıdır")
e = e[~e.aoi.isin(kismi)].reset_index(drop=True)
qc(ADIM, "Tüm etiketler en az bir ShakeMap ızgarasının içinde", bool(e.ln_pga.notna().all()), f"PGA {np.exp(e.ln_pga).min():.2f}–{np.exp(e.ln_pga).max():.2f} g")
qc(ADIM, "GHSL ile eşleşen bina oranı ≥ %90", (e.yapili_2020 > 0).mean() >= 0.9, f"%{100 * (e.yapili_2020 > 0).mean():.1f}")
e.to_parquet(CIKTI / "egitim.parquet", index=False)
print(e.groupby("aoi").agg(n=("yikik", "size"), yikik=("yikik", "mean"), pga=("ln_pga", lambda x: np.exp(x).median()),
                           yil=("yapilasma_yili", "median"), h=("yukseklik_m", "median"), sok=("baskin_sok", lambda x: x.mode()[0])).round(3).to_string())
