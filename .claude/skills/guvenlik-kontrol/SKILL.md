---
name: guvenlik-kontrol
description: Projeyi güvenlik açıkları, sızmış şifre/anahtar ve eski/güvensiz bağımlılıklar için tara, Türkçe raporla. Kullanıcı güvenlik kontrolü, güvenli mi, açık var mı, şifre sızmış mı, bağımlılıkları kontrol et ya da İngilizce security, audit, vulnerability dediğinde kullan.
argument-hint: "[isteğe bağlı klasör veya dosya]"
---

# Güvenlik Kontrolü

Kullanıcıyla her zaman Türkçe konuş. Bu bir savunma amaçlı kontroldür; sadece kullanıcının kendi projesinde çalış.

1. **Sızmış sırlar:** Kodda ve git geçmişinde API anahtarı, şifre, token, özel anahtar ara (ör. `grep -rniE "api[_-]?key|secret|password|token|BEGIN .*PRIVATE KEY"`, `.env` dosyalarının commit'lenip commit'lenmediği: `git log --all --oneline -- .env`). Bulduğun değeri rapora **yazma**, sadece yerini söyle; anahtarın iptal edilip yenilenmesi gerektiğini belirt.
2. **Bağımlılıklar:** Dile göre denetim aracı çalıştır: `npm audit`, `pip-audit`, `cargo audit`, `govulncheck` (yoksa kur). Ciddi olanları listele.
3. **Kod:** SQL/komut enjeksiyonu, XSS, güvensiz dosya yolu birleştirme, `eval`, kapalı TLS doğrulaması, eksik yetki kontrolü, güvensiz CORS, hata mesajlarında hassas bilgi.
4. **Ayarlar:** `.gitignore`'da `.env` var mı, debug modu açık mı, varsayılan şifreler var mı.
5. Rapor: ciddiyet (Kritik/Yüksek/Orta/Düşük) — `dosya:satır` — sorun — düzeltme. Kullanıcı isterse düzeltmeleri uygula.
