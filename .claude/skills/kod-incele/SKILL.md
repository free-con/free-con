---
name: kod-incele
description: Değişiklikleri veya bir dosyayı hatalar, güvenlik açıkları ve kalite sorunları için incele, bulguları Türkçe raporla. Kullanıcı kodu incele, kontrol et, gözden geçir, review yap, hata var mı bak ya da İngilizce review dediğinde kullan.
argument-hint: "[dosya, dal veya PR; boşsa mevcut değişiklikler]"
---

# Kod İnceleme

Kullanıcıyla her zaman Türkçe konuş. Hedef: $ARGUMENTS (boşsa `git diff` ve `git diff --staged`; o da boşsa ana dala göre fark).

1. Değişen her dosyayı ve gerekirse çevresindeki kodu oku.
2. Öncelik sırasıyla ara:
   - **Doğruluk:** mantık hataları, sınır durumları, null/boş değerler, yarış durumları, hatalı hata yönetimi.
   - **Güvenlik:** enjeksiyon (SQL, komut, XSS), koda gömülü şifre/anahtar, eksik yetki kontrolü, güvensiz girdi.
   - **Veri kaybı/geri dönüşsüzlük:** silme, üzerine yazma, migration riskleri.
   - **Performans:** gereksiz döngüler, N+1 sorgular, bellek sızıntıları.
   - **Okunabilirlik:** sadece gerçekten önemliyse.
3. Her bulgu için emin ol: hangi girdide, ne yanlış oluyor? Kanıtlayamadığını "olası" diye işaretle.
4. Rapor biçimi (en ciddiden en hafife):
   - `dosya:satır` — **sorun** — neden önemli — önerilen düzeltme
5. Bulgu yoksa bunu açıkça söyle. Kullanıcı isterse düzeltmeleri uygula.
