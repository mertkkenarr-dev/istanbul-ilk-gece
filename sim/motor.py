"""72 saat müdahale simülatörü: akışkan kurban havuzları + ajan tabanlı arama-kurtarma ekipleri + hastane kapasitesi.

Adım 15 dk, 288 adım. Kurbanlar mahalle başına sürekli (beklenen değer) havuzlar; ekipler kesikli ajanlar.
Ekip durumları: BEKLIYOR (henüz gelmedi) → YOLDA (hedefe) → SAHADA (çalışıyor) → mahalle bitince yeniden sevk; uygun mahalle
yoksa BOSTA kalır, her saat yeniden dener. `atanan[j]`: j'ye giden + j'de çalışan ekip sayısı.
Rastlantısallık deprem gerçekleşmesinden (yer hareketi, hasar, köprü/enkaz) ve parametre örneklemesinden gelir; politikalar
aynı gerçekleşme ve aynı tohumla karşılaştırılır (ortak rastgele sayılar, varyans azaltma).
"""
from __future__ import annotations

import numpy as np
from ag_hasar import DONEM
from parametreler import Parametre, sag_kalma
from politika import sec
from scipy.stats import lognorm

PLAN_SINIR = np.array([0, 3, 6, 12, 24, 48, 72.0])  # optimizasyon.SINIR ile aynı

DT = 0.25
ADIM = int(72 / DT)
TRAFIK = [(6, 2.5), (24, 1.8), (1e9, 1.3)]
AGIR_PAY = {"H": 0.5, "L": 0.15}       # kurtarılan ağır/hafif sıkışmışlardan ağır yaralı payı
ORTA_PAY = {"H": 0.4, "L": 0.45}       # hastanede tedavi gerektiren (ağır olmayan) pay
_G = lognorm(0.8, scale=2.0)            # enkaz dışı yaralıların hastaneye kendi gelişi: medyan 2 sa
GELIS = np.diff(_G.cdf(np.arange(ADIM + 1) * DT))
BEKLIYOR, YOLDA, SAHADA, BOSTA = 0, 1, 2, 3


def trafik(t: float, par: Parametre) -> float:
    for ust, c in TRAFIK:
        if t < ust:
            return 1 + (c - 1) * par.trafik_carpan
    return 1.0


def ekip_takvimi(par: Parametre, us_pro: np.ndarray, giris: np.ndarray, rng: np.random.Generator):
    """(geliş saati, üs indeksi) – İBB istasyonlardan; ulusal ekipler doğu/batı kapısından; uluslararası havalimanlarından."""
    t = [(0.0, rng.choice(us_pro)) for _ in range(par.n_ibb_ilk)] + [(3.0, rng.choice(us_pro)) for _ in range(par.n_ibb_cagri)]
    t += [(rng.uniform(6, 24), giris[2 + i % 2]) for i in range(par.n_ulusal)]
    t += [(rng.uniform(24, 48), giris[i % 2]) for i in range(par.n_uluslararasi)]
    t.sort()
    return np.array([a for a, _ in t]), np.array([b for _, b in t], int)


def calistir(g: dict, mats: list[dict], sen, par: Parametre, rng: np.random.Generator, plan: np.ndarray | None = None,
             ek_hastane: dict | None = None, kayit: bool = False) -> dict:
    """ek_hastane: {"kap": (K,) yatak, "acilis_sa": float} – sahra hastaneleri; süreler mats[d]["mah_ek"].
    kayit: web animasyonu için saatlik mahalle durumu ve ekip hareketleri (yola çıkış, varış, kaynak, hedef) döner."""
    N = len(g["cokmus_kisi"])
    if "sikisan_canli" in g:                 # hasar v3: anında ölüm ve enkaz altında canlı kalanlar hasar modelinden
        olu_cokme, A0 = g["olu_aninda"], g["sikisan_canli"]
        T0 = olu_cokme + A0
    else:
        T0 = par.p_sikisma * g["cokmus_kisi"]
        olu_cokme = par.p_aninda * T0
        A0 = T0 - olu_cokme
    L, H = par.p_hafif_sikisma * A0, (1 - par.p_hafif_sikisma) * A0
    tahrip = np.clip(3.0 * g["cokagir"] / np.maximum(sen.mah.bina_toplam.values, 1), 0, 1)
    toplum_h = par.toplum_hiz * (1 - tahrip)
    kapasite = np.maximum(np.ceil(g["cokmus_bina"]), 1)
    gelis, us = ekip_takvimi(par, sen.us_pro, sen.us_giris, rng)
    E = len(gelis)
    durum = np.full(E, BEKLIYOR); konum = np.full(E, -1); hedef = np.full(E, -1); zaman = gelis.copy()
    atanan = np.zeros(N); gorulmus = np.zeros(N, bool); ilk_varis = np.full(N, np.inf)
    kap0 = sen.has_yatak * par.bos_yatak_payi * par.tahliye_carpan * g["has_islev"]
    kap = kap0.copy()
    K_ek = 0 if ek_hastane is None else len(ek_hastane["kap"])
    kap_ek = np.zeros(K_ek); ek_acik = False
    agir_b = np.zeros(N); orta_b = np.zeros(N)
    s_onceki = 1.0
    sira_onbellek: dict = {}  # dönem → mahalle başına en yakın 8 hastane (trafik çarpanı sırayı değiştirmez)
    seri = {k: np.zeros(ADIM, np.float32) for k in ("enkaz_canli", "kurtarilan_toplum", "kurtarilan_pro", "olu_enkaz", "olu_bekleme",
                                                    "olu_tedavi", "ekip_sahada", "yatak_dolu")}
    kum = {k: np.zeros(N) for k in ("kt", "kp", "oe", "ob", "ot")}
    hareket: list[tuple] = []                      # (ekip, çıkış sa, varış sa, kaynak türü 0=üs 1=mahalle, kaynak, hedef)
    saatlik = {k: [] for k in ("canli", "kurtarilan", "olu_enkaz", "olu_bekleme", "sahada")} if kayit else None

    def sevk(i: int, t: float, M: dict, tc: float) -> None:
        sure = (M["mah_mah"][konum[i]] if konum[i] >= 0 else M["us_mah"][us[i]]) / 3600 * tc
        plan_k = None if plan is None else plan[:, min(int(np.searchsorted(PLAN_SINIR, t, side="right") - 1), plan.shape[1] - 1)]
        j = sec(par.politika, sure, L + H, atanan, kapasite, gorulmus, sen.yoksunluk, par.kurtarma_sure_sa, plan_k)
        if j < 0:
            durum[i] = BOSTA; zaman[i] = t + 1.0
        else:
            if kayit:
                hareket.append((i, t, t + float(sure[j]), int(konum[i] >= 0), int(konum[i] if konum[i] >= 0 else us[i]), j))
            durum[i] = YOLDA; hedef[i] = j; zaman[i] = t + sure[j]; atanan[j] += 1

    for s in range(ADIM):
        t = s * DT
        M = mats[int(np.searchsorted(DONEM, t, side="right") - 1)]; tc = trafik(t, par)
        # --- 1) ekip olayları ---
        for i in np.where((durum == YOLDA) & (zaman <= t))[0]:
            durum[i] = SAHADA; konum[i] = hedef[i]; hedef[i] = -1
            ilk_varis[konum[i]] = min(ilk_varis[konum[i]], t); gorulmus[konum[i]] = True
        bitti = (durum == SAHADA) & ((L + H)[np.maximum(konum, 0)] <= 0.5)
        for i in np.where(bitti)[0]:
            atanan[konum[i]] -= 1
        for i in np.where(((durum == BEKLIYOR) | (durum == BOSTA)) & (zaman <= t) | bitti)[0]:
            sevk(i, t, M, tc)
        sahada = np.bincount(konum[durum == SAHADA], minlength=N).astype(float)
        # --- 2) kurtarma: ekip önce ağır sıkışmışları, artan kapasiteyle hafifleri; komşular yalnızca hafifleri ---
        oran = sahada * DT / par.kurtarma_sure_sa
        pro_h = np.minimum(H, oran)
        pro_l = np.minimum(L, np.maximum(2 * oran - 2 * pro_h, 0))
        top = np.minimum((L - pro_l) * (1 - np.exp(-toplum_h * DT)), L - pro_l)
        H -= pro_h; L -= pro_l + top
        # --- 3) enkaz altında ölüm: Weibull sağ kalma (herkes t=0'da sıkıştı, koşullu hazard) ---
        s_yeni = float(sag_kalma(t + DT, par.weibull_olcek)); p_ol = 1 - s_yeni / s_onceki; s_onceki = s_yeni
        olu = (H + L) * p_ol; H *= 1 - p_ol; L *= 1 - p_ol
        # --- 4) hastane ---
        agir_b += AGIR_PAY["H"] * pro_h + AGIR_PAY["L"] * (pro_l + top) + g["yarali_agir_diger"] * GELIS[s]
        orta_b += ORTA_PAY["H"] * pro_h + ORTA_PAY["L"] * (pro_l + top) + g["yarali_hastane_diger"] * GELIS[s]
        if K_ek and not ek_acik and t >= ek_hastane["acilis_sa"]:
            kap_ek[:] = ek_hastane["kap"]; ek_acik = True
        if s % 4 == 0:
            MH = np.c_[M["mah_has"], M["mah_ek"]] if K_ek else M["mah_has"]
            anahtar = (id(M), K_ek)
            if anahtar not in sira_onbellek:
                srt = np.argsort(MH, axis=1)[:, :8]
                sira_onbellek[anahtar] = (srt, np.take_along_axis(MH, srt, 1))
            srt, sure8 = sira_onbellek[anahtar]
            if K_ek:
                kk = np.r_[kap, kap_ek]
                kum["ot"] += _hastane_ata(agir_b, orta_b, kk, srt, sure8, tc, par)
                kap[:] = kk[:len(kap)]; kap_ek[:] = kk[len(kap):]
            else:
                kum["ot"] += _hastane_ata(agir_b, orta_b, kap, srt, sure8, tc, par)
        ob = agir_b * (1 - np.exp(-par.agir_bekleme_hazard * DT)); agir_b -= ob
        kum["kt"] += top; kum["kp"] += pro_h + pro_l; kum["oe"] += olu; kum["ob"] += ob
        if kayit and s % 4 == 3:
            for k, v in (("canli", H + L), ("kurtarilan", kum["kt"] + kum["kp"]), ("olu_enkaz", kum["oe"]), ("olu_bekleme", kum["ob"]),
                         ("sahada", sahada)):
                saatlik[k].append(v.astype(np.float32).copy())
        for k, v in (("enkaz_canli", (H + L).sum()), ("kurtarilan_toplum", kum["kt"].sum()), ("kurtarilan_pro", kum["kp"].sum()),
                     ("olu_enkaz", kum["oe"].sum()), ("olu_bekleme", kum["ob"].sum()), ("olu_tedavi", kum["ot"].sum()),
                     ("ekip_sahada", sahada.sum()), ("yatak_dolu", (kap0 - kap).sum() + (ek_hastane["kap"].sum() - kap_ek.sum() if ek_acik else 0))):
            seri[k][s] = v
    olu_aninda = olu_cokme + g["can_kaybi_diger"]
    mah = dict(sikisan=T0, canli_sikisan=A0, olu_aninda=olu_aninda, kurtarilan_toplum=kum["kt"], kurtarilan_pro=kum["kp"],
               olu_enkaz=kum["oe"], olu_bekleme=kum["ob"], olu_tedavi=kum["ot"], kalan_72=H + L, ilk_varis_sa=ilk_varis,
               agir_bekleyen_72=agir_b)
    etk = A0 > 1
    ozet = dict(olu_toplam=float(olu_aninda.sum() + kum["oe"].sum() + kum["ob"].sum() + kum["ot"].sum()),
                olu_aninda=float(olu_aninda.sum()), olu_enkaz=float(kum["oe"].sum()), olu_bekleme=float(kum["ob"].sum()),
                olu_tedavi=float(kum["ot"].sum()), canli_sikisan=float(A0.sum()), kurtarilan=float(kum["kt"].sum() + kum["kp"].sum()),
                kurtarilan_pro=float(kum["kp"].sum()), etkilenen_mahalle=int(etk.sum()), ekipsiz_mahalle=int((etk & ~gorulmus).sum()),
                ilk_varis_medyan_sa=float(np.median(ilk_varis[etk])) if etk.any() else 0.0, ekip=E)
    out = dict(seri=seri, mahalle=mah, ozet=ozet)
    if kayit:
        out["saatlik"] = {k: np.stack(v) for k, v in saatlik.items()}
        out["hareket"] = np.array(hareket, dtype=float) if hareket else np.zeros((0, 6))
        out["kap0"], out["kap_son"] = kap0, kap
    return out


def _hastane_ata(agir: np.ndarray, orta: np.ndarray, kap: np.ndarray, srt: np.ndarray, sure8: np.ndarray, tc: float,
                 par: Parametre) -> np.ndarray:
    """Saatlik atama (yerinde günceller): bekleyenler 2 saatlik yol içindeki en yakın kapasiteli hastaneye, önce ağırlar.
    srt/sure8: mahalle başına en yakın 8 hastane ve süreleri (sn). Dönüş: tedavi edilen ağırlar arasındaki beklenen ölüm."""
    olu = np.zeros(len(agir))
    for yuk, agir_mi in ((agir, True), (orta, False)):
        for i in np.argsort(-yuk):
            if yuk[i] <= 0.01:
                break
            for h, sure in zip(srt[i], sure8[i] / 3600 * tc):
                if sure > 2.0 or yuk[i] <= 0.01:
                    break
                al = min(yuk[i], kap[h]); kap[h] -= al; yuk[i] -= al
                if agir_mi:
                    olu[i] += al * par.agir_tedavili_olum
    return olu
