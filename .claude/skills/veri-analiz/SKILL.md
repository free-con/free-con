---
name: veri-analiz
description: CSV, Excel, JSON veya veritabanı verisini incele, temizle, hesapla ve grafikle; sonuçları Türkçe açıkla. Kullanıcı veriyi analiz et, tabloya bak, grafik çiz, ortalama/toplam hesapla, Excel'i incele, rapor çıkar ya da İngilizce analyze data, chart, csv, excel dediğinde kullan.
argument-hint: "[dosya yolu ve soru]"
---

# Veri Analizi

Kullanıcıyla her zaman Türkçe konuş. Veri ve soru: $ARGUMENTS

1. Python ve pandas kullan (yoksa `pip install pandas openpyxl matplotlib` ile kur). Dosyayı oku; satır/sütun sayısını, sütun türlerini, boş değerleri ve ilk birkaç satırı göster.
2. Veri sorunlarını bildir: boş değerler, tekrar eden satırlar, tutarsız biçimler (tarih, ondalık ayırıcı virgül/nokta), aykırı değerler. Orijinal dosyayı değiştirme; temizlenmiş hâli yeni bir dosyaya yaz.
3. Soruyu cevaplayan hesaplamaları yap. Kullandığın kodu kısa tut ve sonucu tablo olarak göster.
4. Grafik işe yarıyorsa çiz (`dataviz` skill'indeki kurallara uy), PNG olarak kaydet ve kullanıcıya gönder.
5. Sonucu sade Türkçeyle yorumla: ne bulundu, ne kadar güvenilir, hangi varsayımlar yapıldı. Korelasyonu nedensellik gibi anlatma.
6. Excel çıktısı istenirse `xlsx` skill'ini kullan.
