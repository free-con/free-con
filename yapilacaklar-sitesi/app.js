import { ekle, degistir, sil, bitenleriTemizle, suz, kalanSayisi } from './liste.js';

const ANAHTAR = 'yapilacaklar-v1';
let liste = [];
let filtre = 'hepsi';
try { liste = JSON.parse(localStorage.getItem(ANAHTAR)) || []; } catch { liste = []; }

const $ = s => document.querySelector(s);
const form = $('#form'), girdi = $('#girdi'), ul = $('#liste'), sayac = $('#sayac');

function kaydet() { try { localStorage.setItem(ANAHTAR, JSON.stringify(liste)); } catch {} }
function guncelle(yeni) { liste = yeni; kaydet(); ciz(); }

function ciz() {
  ul.replaceChildren(...suz(liste, filtre).map(g => {
    const li = document.createElement('li');
    li.className = g.bitti ? 'bitti' : '';
    const kutu = Object.assign(document.createElement('input'), { type: 'checkbox', checked: g.bitti });
    kutu.setAttribute('aria-label', 'Bitti olarak işaretle');
    kutu.addEventListener('change', () => guncelle(degistir(liste, g.id)));
    const yazi = Object.assign(document.createElement('span'), { textContent: g.metin });
    const btn = Object.assign(document.createElement('button'), { textContent: '✕', className: 'sil', title: 'Sil' });
    btn.addEventListener('click', () => guncelle(sil(liste, g.id)));
    li.append(kutu, yazi, btn);
    return li;
  }));
  const k = kalanSayisi(liste);
  sayac.textContent = liste.length ? `${k} görev kaldı` : 'Henüz görev yok';
  document.querySelectorAll('[data-filtre]').forEach(b => b.classList.toggle('secili', b.dataset.filtre === filtre));
}

form.addEventListener('submit', e => { e.preventDefault(); guncelle(ekle(liste, girdi.value)); girdi.value = ''; girdi.focus(); });
document.querySelectorAll('[data-filtre]').forEach(b => b.addEventListener('click', () => { filtre = b.dataset.filtre; ciz(); }));
$('#temizle').addEventListener('click', () => guncelle(bitenleriTemizle(liste)));
ciz();
