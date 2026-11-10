---
name: hata-ayikla
description: Bir hatayı, çökmeyi, yanlış çalışan kodu veya başarısız testi sistemli şekilde bul ve düzelt. Kullanıcı hata var, çalışmıyor, bozuldu, çöküyor, hata veriyor, düzelt, neden olmuyor ya da İngilizce bug, error, debug, fix, broken dediğinde kullan.
argument-hint: "[hata mesajı veya sorunun tarifi]"
---

# Hata Ayıkla

Kullanıcıyla her zaman Türkçe konuş. Sorun: $ARGUMENTS

Tahminle değil kanıtla ilerle:

1. **Yeniden üret.** Hatayı kendin tetikleyen en kısa komutu bul ve çalıştır. Tam hata mesajını ve yığın izini (stack trace) oku. Üretemiyorsan nedenini söyle ve ne denediğini anlat.
2. **Daralt.** Hata mesajındaki dosya/satıra git. Son değişikliklere bak (`git log -p -5`, `git diff`). Gerekirse geçici log/print ekle, giriş verisini küçült, `git bisect` kullan.
3. **Kök nedeni bul.** "Belirtiyi susturmak" (try/except ile yutmak, testi kapatmak) düzeltme değildir. Neden olduğunu bir cümleyle söyleyebilene kadar devam et.
4. **En küçük doğru düzeltmeyi yap.** Sorunla ilgisiz yerlere dokunma.
5. **Doğrula.** 1. adımdaki komutu tekrar çalıştır, hata gitmiş olmalı. İlgili testleri çalıştır. Mümkünse bu hatayı yakalayan bir test ekle.
6. **Geçici log'ları temizle.**
7. Kullanıcıya Türkçe ve sade anlat: sorun neydi, neden oluyordu, ne değiştirdin, nasıl doğruladın. Test başarısızsa bunu açıkça, çıktısıyla söyle.
