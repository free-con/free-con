import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ekle, degistir, sil, bitenleriTemizle, suz, kalanSayisi } from '../liste.js';

test('ekle: görev ekler ve boşlukları kırpar', () => {
  const l = ekle([], '  süt al  ', 'a');
  assert.deepEqual(l, [{ id: 'a', metin: 'süt al', bitti: false }]);
});
test('ekle: boş veya sadece boşluk olan metni eklemez', () => {
  assert.deepEqual(ekle([], '   '), []);
  assert.deepEqual(ekle([], ''), []);
  assert.deepEqual(ekle([], undefined), []);
});
test('ekle: orijinal listeyi değiştirmez', () => {
  const l = [];
  ekle(l, 'x', 'a');
  assert.equal(l.length, 0);
});
test('degistir: bitti durumunu açıp kapatır', () => {
  let l = ekle([], 'x', 'a');
  l = degistir(l, 'a');
  assert.equal(l[0].bitti, true);
  l = degistir(l, 'a');
  assert.equal(l[0].bitti, false);
});
test('sil: sadece verilen görevi siler', () => {
  let l = ekle(ekle([], 'x', 'a'), 'y', 'b');
  assert.deepEqual(sil(l, 'a').map(g => g.id), ['b']);
  assert.equal(sil(l, 'yok').length, 2);
});
test('suz, kalanSayisi, bitenleriTemizle', () => {
  let l = ekle(ekle(ekle([], 'x', 'a'), 'y', 'b'), 'z', 'c');
  l = degistir(l, 'b');
  assert.deepEqual(suz(l, 'aktif').map(g => g.id), ['a', 'c']);
  assert.deepEqual(suz(l, 'biten').map(g => g.id), ['b']);
  assert.equal(suz(l, 'hepsi').length, 3);
  assert.equal(kalanSayisi(l), 2);
  assert.deepEqual(bitenleriTemizle(l).map(g => g.id), ['a', 'c']);
});
