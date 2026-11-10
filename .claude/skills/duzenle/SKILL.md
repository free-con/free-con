---
name: duzenle
description: Çalışan kodu davranışını değiştirmeden daha temiz, okunur ve sade hale getir (refactor). Kullanıcı kodu düzenle, temizle, sadeleştir, toparla, refactor et, daha iyi yaz ya da İngilizce refactor, clean up, simplify dediğinde kullan.
argument-hint: "[dosya veya klasör]"
---

# Düzenle (Refactor)

Kullanıcıyla her zaman Türkçe konuş. Hedef: $ARGUMENTS

1. Önce testleri çalıştır ve mevcut durumu kaydet. Test yoksa ve kod önemliyse, düzenlemeden önce davranışı sabitleyen birkaç basit test ekle.
2. Neyi düzelteceğine karar ver: tekrarlanan kod, çok uzun fonksiyonlar, anlamsız isimler, ölü kod, gereksiz karmaşıklık, iç içe if'ler.
3. Küçük adımlarla ilerle; her adımdan sonra testleri çalıştır.
4. Davranışı değiştirme. Düzenleme sırasında bir hata fark edersen ayrıca söyle; düzenlemenin içine sessizce karıştırma.
5. Projenin mevcut stiline uy; yeni kütüphane ekleme.
6. Kullanıcıya özetle: neyi neden değiştirdin, testler ne diyor.
