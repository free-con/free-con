// Saf mantık: tarayıcıdan ve depolamadan bağımsız, böylece test edilebilir.
export function ekle(liste, metin, id = Date.now().toString(36) + Math.random().toString(36).slice(2, 6)) {
  const temiz = String(metin ?? '').trim();
  if (!temiz) return liste;
  return [...liste, { id, metin: temiz, bitti: false }];
}
export function degistir(liste, id) {
  return liste.map(g => (g.id === id ? { ...g, bitti: !g.bitti } : g));
}
export function sil(liste, id) {
  return liste.filter(g => g.id !== id);
}
export function bitenleriTemizle(liste) {
  return liste.filter(g => !g.bitti);
}
export function suz(liste, filtre) {
  if (filtre === 'aktif') return liste.filter(g => !g.bitti);
  if (filtre === 'biten') return liste.filter(g => g.bitti);
  return liste;
}
export function kalanSayisi(liste) {
  return liste.filter(g => !g.bitti).length;
}
