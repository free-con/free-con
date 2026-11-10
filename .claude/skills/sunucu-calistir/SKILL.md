---
name: sunucu-calistir
description: Projeyi çalıştır (geliştirme sunucusu, uygulama, betik), hazır olduğunu doğrula, gerekirse ekran görüntüsü al. Kullanıcı çalıştır, başlat, aç, siteyi göster, uygulamayı çalıştır, önizleme ya da İngilizce run, start, serve, preview dediğinde kullan.
argument-hint: "[isteğe bağlı: hangi uygulama/komut]"
---

# Çalıştır

Kullanıcıyla her zaman Türkçe konuş.

1. Çalıştırma yolunu bul: README, `package.json` scriptleri (`dev`, `start`), `Makefile`, `docker-compose.yml`, `manage.py`, `main.py`. Bağımlılıklar kurulu değilse kur.
2. Sunucuyu arka planda başlat (Bash `run_in_background: true`), çıktıyı bir log dosyasına yaz.
3. Hazır olmasını kendiliğinden biten bir döngüyle bekle (port cevap verene veya süreç ölene kadar). Gerçek portu çıktıdan oku; dolu port yüzünden başka porta geçmiş olabilir.
4. Web arayüzüyse portu bildir (`report_preview_port`) ve istenirse Playwright ile ekran görüntüsü al.
5. Hata olursa log'u oku, `hata-ayikla` adımlarıyla düzelt.
6. Kullanıcıya: nasıl çalıştırıldığı, adres/port, nasıl durdurulacağı.
