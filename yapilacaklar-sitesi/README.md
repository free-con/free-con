# Yapılacaklar Sitesi

Basit bir yapılacaklar listesi. Görev ekle, bitti olarak işaretle, sil, filtrele. Görevler tarayıcıda saklanır, sayfa yenilense de kaybolmaz. Kurulum gerektirmez.

## Çalıştırma

Bu klasörde:

```bash
python3 -m http.server 8000
```

Sonra tarayıcıda `http://localhost:8000` adresini aç.

## Testler

```bash
npm test
```

## Dosyalar

- `index.html` — sayfa
- `stil.css` — görünüm (açık ve koyu tema)
- `liste.js` — görev mantığı (ekle, sil, işaretle, filtrele)
- `app.js` — sayfayla bağlantı ve kaydetme
- `test/liste.test.js` — testler
