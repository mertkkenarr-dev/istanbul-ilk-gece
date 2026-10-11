/**
 * "Nasıl yaptık" sayfası. Metin tek kaynaktan, docs/web_metin/NASIL_YAPTIK.md'den derleme anında okunur:
 * site ile belge ayrı ayrı düzenlenip birbirinden kaymasın diye. Taslak başlığı ve editör notu (ilk blockquote) okura gösterilmez.
 */
import './stil.css'
import './nasil.css'
import { marked } from 'marked'
import hamTr from '../../docs/web_metin/NASIL_YAPTIK.md?raw'
import hamEn from '../../docs/web_metin/HOW_WE_DID_IT.md?raw'
import { ARAYUZ, dilAdresi, dilSec } from './dil'

const DIL = dilSec()
const A = ARAYUZ[DIL]
const obur = DIL === 'tr' ? 'en' : 'tr'
document.title = A.baslikNasil
document.getElementById('ust-bar')!.innerHTML = `<a href="./?lang=${DIL}" class="marka geri">${A.hikayeyeDon}</a><nav class="ust-baglar"><a href="${dilAdresi(obur)}" class="dil" hreflang="${obur}" aria-label="${A.oburDilAd}">${A.oburDil}</a><span class="bag etkin" aria-current="page">${A.nasilYaptik}</span></nav>`
document.getElementById('icindekiler-baslik')!.textContent = A.icindekiler
document.querySelector('.icindekiler')!.setAttribute('aria-label', A.icindekiler)
const ham = DIL === 'tr' ? hamTr : hamEn

const kok = document.getElementById('nasil')!
const liste = document.getElementById('icindekiler')!

const govde = ham.replace(/^# .*\n+/, '').replace(/^(>.*\n)+/m, '')
kok.innerHTML = `<p class="ust">${A.yontem}</p><h1>${A.nasilYaptik}</h1>
  <p class="spot">${A.spot}</p>
  ${marked.parse(govde, { async: false })}`

// tablolar dar ekranda yatay kaysın, sayfa taşmasın
kok.querySelectorAll('table').forEach((t) => {
  const sar = document.createElement('div'); sar.className = 'tablo'; sar.tabIndex = 0
  t.replaceWith(sar); sar.appendChild(t)
})

const kimlik = (s: string) => s.toLocaleLowerCase('tr').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/ı/g, 'i').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
const basliklar = [...kok.querySelectorAll('h2')]
basliklar.forEach((h) => { h.id = kimlik(h.textContent ?? '') })
liste.innerHTML = basliklar.map((h) => `<li><a href="#${h.id}">${h.textContent}</a></li>`).join('')

// okunan bölüm içindekilerde işaretlenir
const io = new IntersectionObserver((g) => {
  for (const e of g) if (e.isIntersecting) liste.querySelectorAll('a').forEach((a) => a.classList.toggle('aktif', a.getAttribute('href') === `#${e.target.id}`))
}, { rootMargin: '0px 0px -70% 0px' })
basliklar.forEach((h) => io.observe(h))

// geniş ekranda içindekiler hep açık yan sütun; dar ekranda başlıkta katlanmış durur ve bir bağlantıya basınca kapanır
const kutu = document.getElementById('icindekiler-kutu') as HTMLDetailsElement
const genis = window.matchMedia('(min-width: 60.01rem)')
const ayarla = () => { kutu.open = genis.matches }
ayarla(); genis.addEventListener('change', ayarla)
liste.addEventListener('click', (e) => { if (!genis.matches && (e.target as HTMLElement).tagName === 'A') kutu.open = false })
