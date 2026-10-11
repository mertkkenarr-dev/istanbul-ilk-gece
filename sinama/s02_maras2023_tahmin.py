"""6 Şubat 2023 sınaması, adım 2: İstanbul hasar ve can kaybı modelimiz 6 Şubat'ın gerçek sarsıntısıyla çalıştırılsaydı ne derdi?

Gözlem (yalnız Türkiye): 53.537 ölü (AFAD, Şubat 2024); 518.009 acil yıkılacak + ağır hasarlı + yıkık konut (ÇŞİDB, 6 Mart 2023,
SBB raporu Tablo 20). Kıyas 11 ilde; Diyarbakır kentinin çoğu GHSL R6_C22 karosu dışında kalır (≈400 ölü) → alt sınır kıyası.

Yapı stoku düğüm başına: yaş payları GHSL'den, İstanbul'da İBB 2017 sayımına uydurulan eşlemeyle düzeltilir (GHSL yerinde yeniden
yapımı göremez, eski payı abartır); kat ve yapı tipi yaşa koşullu olarak İstanbul envanterinden (VARSAYIM; bölge stoku daha alçaktır,
"alçak stok" duyarlılığıyla sınanır). Kişi ağırlıkları hs_01 ile aynı (1–4 kat: 6, 5–8: 24, 9+: 60).
Model katmanları: KOERI (s_β = θ = κ = 1, İBB'nin yöntemi) ve kalibrasyon posteriorunun 144 noktası (hs_03 ağırlıklarıyla).
Çıktı: data/processed/sinama/maras2023_sonuc.json, maras2023_il.parquet
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "model"))
from hasar_motoru import a_katsayi, hasar_olasilik, kap, performans_sd, sa_periyot, yaralanma  # noqa: E402

CIKTI = KOK / "data/processed/sinama"
IL11 = ["Adana", "Adıyaman", "Diyarbakır", "Elazığ", "Gaziantep", "Hatay", "Kahramanmaraş", "Kilis", "Malatya", "Osmaniye", "Şanlıurfa"]
GOZLEM = dict(olu=53537, agir_ustu_konut=518009)
KISI = {"1-4": 6.0, "5-8": 24.0, "9-": 60.0}
YAS = ["-1979", "1980-2000", "2000-"]


def yas_eslemesi() -> tuple[LinearRegression, list[str]]:
    """GHSL (pay_80, pay_00) → İBB yaş payları (1980 öncesi, 2000 sonrası); İstanbul'un 959 mahallesinde, bina ağırlıklı."""
    h = pd.read_parquet(KOK / "data/processed/ders2023/istanbul_hucre.parquet")
    d = pd.read_parquet(CIKTI / "istanbul_ghsl_yas.parquet")
    m = pd.read_parquet(KOK / "data/processed/mahalle.parquet").set_index("uavt")
    X = d.reindex(m.index)[["pay_80", "pay_00"]].values
    Y = np.c_[m.bina_1980_oncesi / m.bina_toplam, m.bina_2000_sonrasi / m.bina_toplam]
    ok = np.isfinite(X).all(1) & np.isfinite(Y).all(1)
    lr = LinearRegression().fit(X[ok], Y[ok], sample_weight=m.bina_toplam.values[ok])
    print(f"yaş eşlemesi R² = {lr.score(X[ok], Y[ok], sample_weight=m.bina_toplam.values[ok]):.2f} ({ok.sum()} mahalle); hücre sayısı {len(h):,}")
    return lr, ["pay_80", "pay_00"]


def stok(p: pd.DataFrame, lr: LinearRegression, alcak: bool) -> tuple[pd.DataFrame, np.ndarray]:
    env = pd.read_parquet(KOK / "data/processed/hasar/envanter.parquet")
    kos = env.groupby(["yas", "sinif", "tip", "kat"]).bina.sum().reset_index()
    if alcak:
        kos.loc[kos.kat != "1-4", "bina"] *= 0.5
    kos["p"] = kos.bina / kos.groupby("yas").bina.transform("sum")
    y = np.clip(lr.predict(p[["pay_80", "pay_00"]].values), 0, 1)
    y80, y00 = y[:, 0], y[:, 1]
    s = y80 + y00
    y80, y00 = np.where(s > 1, y80 / s, y80), np.where(s > 1, y00 / s, y00)
    yas_pay = {"-1979": y80, "1980-2000": 1 - y80 - y00, "2000-": y00}
    W = np.stack([yas_pay[r.yas] * r.p * KISI[r.kat] for r in kos.itertuples()], 1)  # (N, sınıf) kişi ağırlığı
    return kos, W / W.sum(1, keepdims=True)


def calistir(p: pd.DataFrame, kos: pd.DataFrame, W: np.ndarray, noktalar: pd.DataFrame) -> pd.DataFrame:
    per = np.array([0.3, 0.6, 1.0]); ln = p[["ln_sa03", "ln_sa06", "ln_sa10"]].values
    a = a_katsayi(p.vs30.values)
    nuf = p.nufus.values
    out = []
    sd = {r.sinif: performans_sd(sa_periyot(ln, per, kap.at[r.sinif, "T_s"]), r.sinif, a) for r in kos.drop_duplicates("sinif").itertuples()}
    for q in noktalar.itertuples():
        olu = np.zeros(len(p)); agir = np.zeros(len(p))
        for j, r in enumerate(kos.itertuples()):
            pr = hasar_olasilik(sd[r.sinif], r.sinif, q.s_beta, (q.theta_ho, q.theta_ho, q.theta_ac, q.theta_ac))
            kisi = nuf * W[:, j]
            olu += q.kappa * yaralanma(pr, kisi, r.tip, r.kat)[0][:, 3]
            agir += (pr[:, 3] + pr[:, 4]) * kisi
        out.append((olu, agir))
    return out


if __name__ == "__main__":
    p = pd.read_parquet(CIKTI / "maras2023_dugum.parquet")
    p = p[p.il.isin(IL11)].reset_index(drop=True)
    lr, _ = yas_eslemesi()
    kal = pd.read_parquet(KOK / "data/processed/hasar/kalibrasyon.parquet")
    koeri = pd.DataFrame([dict(s_beta=1.0, theta_ho=1.0, theta_ac=1.0, kappa=1.0, agirlik=1.0)])
    sonuc, il_satir = {}, []
    for alcak in (False, True):
        kos, W = stok(p, lr, alcak)
        etiket = "alcak_stok" if alcak else "temel"
        for ad, nok in (("koeri", koeri), ("posterior", kal)):
            r = calistir(p, kos, W, nok)
            olu = np.array([x[0].sum() for x in r]); agir = np.array([x[1].sum() for x in r])
            w = nok.agirlik.values / nok.agirlik.sum()
            sira = np.argsort(olu); cw = np.cumsum(w[sira])
            q = lambda v, s=sira, c=cw: float(v[s][np.searchsorted(c, 0.5)])
            sonuc[f"{etiket}/{ad}"] = dict(olu_ort=float((w * olu).sum()), olu_medyan=q(olu), olu_min=float(olu.min()), olu_maks=float(olu.max()),
                                          agir_ustu_kisi_ort=float((w * agir).sum()))
            enb = int(np.argmax(w))
            il_satir.append(pd.DataFrame({"il": p.il, "olu": r[enb][0], "agir_kisi": r[enb][1], "nufus": p.nufus}).groupby("il").sum()
                            .assign(katman=f"{etiket}/{ad}").reset_index())
            print(etiket, ad, json.dumps(sonuc[f"{etiket}/{ad}"], default=lambda x: round(x)))
    sonuc["gozlem"] = GOZLEM
    (CIKTI / "maras2023_sonuc.json").write_text(json.dumps(sonuc, indent=1))
    pd.concat(il_satir).to_parquet(CIKTI / "maras2023_il.parquet", index=False)
