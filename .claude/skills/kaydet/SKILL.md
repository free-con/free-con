---
name: kaydet
description: Yapılan değişiklikleri git ile kaydet (commit) ve uzak depoya gönder (push). Kullanıcı kaydet, commit at, gönder, push et, yükle, değişiklikleri kaydet ya da İngilizce commit, push, save dediğinde kullan.
argument-hint: "[isteğe bağlı commit mesajı]"
---

# Kaydet (commit + push)

Kullanıcıyla her zaman Türkçe konuş.

1. `git status` ve `git diff` (gerekirse `git diff --staged`) ile neyin değiştiğine bak.
2. Kaydedilmemesi gereken şeyleri ayıkla: `.env`, şifre/anahtar içeren dosyalar, `node_modules`, derleme çıktıları, büyük geçici dosyalar. Böyle bir şey görürsen kaydetme; `.gitignore`'a eklemeyi öner ve kullanıcıya söyle.
3. Dosyaları isimleriyle ekle (`git add <dosya>`), körlemesine `git add -A` yapma.
4. Commit mesajı: `$ARGUMENTS` verildiyse onu kullan. Verilmediyse değişikliği özetleyen kısa, net bir mesaj yaz (ilk satır en fazla ~70 karakter, ne yapıldığını ve neden yapıldığını söylesin). Depodaki eski commit'lerin dili ve biçimi neyse ona uy (`git log --oneline -10`).
5. Bulunduğun dal ana dal (`main`/`master`) ise ve kullanıcı açıkça istemediyse önce yeni bir dal aç.
6. `git push -u origin <dal>` ile gönder. Ağ hatası olursa birkaç kez bekleyip tekrar dene; yetki hatasında dur ve kullanıcıya açıkla.
7. Sonunda Türkçe kısa bir özet ver: hangi dosyalar, hangi mesajla, hangi dala gönderildi.

Asla `--force` ile gönderme, geçmişi yeniden yazma veya testleri atlamak için kancaları (`--no-verify`) kapatma — kullanıcı açıkça istemedikçe.
