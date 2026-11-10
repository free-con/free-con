---
name: test-yaz
description: Kod için otomatik testler yaz ve çalıştır. Kullanıcı test yaz, test ekle, bunu test et, birim testi, testleri çalıştır ya da İngilizce write tests, unit test, add tests dediğinde kullan.
argument-hint: "[test edilecek dosya veya fonksiyon]"
---

# Test Yaz

Kullanıcıyla her zaman Türkçe konuş. Hedef: $ARGUMENTS

1. Projenin test altyapısını bul: `package.json` scriptleri, `pytest.ini`/`pyproject.toml`, `go test`, `cargo test`, mevcut test klasörleri. Var olan testlerin stilini, adlandırmasını ve konumunu taklit et. Altyapı yoksa dilin en yaygın aracını öner ve kur (JS/TS: vitest veya jest, Python: pytest).
2. Test edilecek kodu oku; girdileri, çıktıları ve yan etkileri anla.
3. Şunları kapsayan testler yaz: normal kullanım, sınır değerleri (boş, sıfır, çok büyük, negatif), hatalı girdi ve beklenen hatalar. Her test tek bir şeyi denesin ve adı ne denediğini söylesin.
4. Dış servisleri (ağ, veritabanı, saat) gerektiğinde taklit et (mock), ama mantığın kendisini taklit etme.
5. Testleri çalıştır. Başarısız olan varsa: test mi yanlış, kod mu? Kodda gerçek bir hata bulduysan kullanıcıya söyle; testi geçsin diye beklentiyi bozma.
6. Kullanıcıya özetle: kaç test, neyi kapsıyor, sonuç ne (çıktıyla).
