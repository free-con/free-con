---
name: yeni-proje
description: Sıfırdan yeni bir proje kur (web sitesi, API, betik, bot, mobil/masaüstü uygulama vb.), klasör yapısını, bağımlılıkları ve çalışır bir başlangıç kodunu oluştur. Kullanıcı yeni proje, proje başlat, sıfırdan yap, uygulama kur, site yap ya da İngilizce new project, scaffold, bootstrap dediğinde kullan.
argument-hint: "[ne tür proje, ör. 'react sitesi', 'python telegram botu']"
---

# Yeni Proje

Kullanıcıyla her zaman Türkçe konuş. İstek: $ARGUMENTS

1. Proje türünü istekten çıkar. Belirsizse en yaygın, en az kurulum gerektiren seçeneği seç ve neyi seçtiğini söyle (kullanıcıya uzun soru listesi sorma):
   - Web sitesi/arayüz: Vite + React (TypeScript) veya basit HTML/CSS/JS
   - API/sunucu: Node (Express/Fastify) veya Python (FastAPI)
   - Betik/otomasyon/bot: Python
2. Resmi oluşturucu araçları kullan (`npm create vite@latest`, `uv init`/`python -m venv` vb.); elle yüzlerce dosya yazma.
3. Şunları ekle: `.gitignore`, Türkçe `README.md` (ne olduğu, nasıl kurulur, nasıl çalıştırılır), örnek bir test, varsa `.env.example` (gerçek şifre olmadan).
4. Bağımlılıkları kur ve projeyi gerçekten çalıştırıp çalıştığını doğrula (sunucuysa isteğe cevap verdiğini gör, testleri çalıştır).
5. `git init` yoksa yap, ilk commit'i at.
6. Kullanıcıya özetle: ne kuruldu, nasıl çalıştırılır (komutları ayrı kod bloklarında ver), sırada ne yapılabilir.
