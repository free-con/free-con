---
name: yapilacaklar
description: Büyük bir işi adımlara böl, yapılacaklar listesi (TODO) oluştur, takip et ve sırayla bitir. Kullanıcı plan yap, adımlara böl, yapılacaklar listesi, ne yapmam lazım, nereden başlayayım, iş planı ya da İngilizce plan, todo, roadmap dediğinde kullan.
argument-hint: "[iş veya hedef]"
---

# Yapılacaklar / Plan

Kullanıcıyla her zaman Türkçe konuş. Hedef: $ARGUMENTS

1. Hedefi ve mevcut durumu anla (gerekirse projeye bak).
2. İşi 3–12 somut adıma böl. Her adım: ne yapılacak, nasıl anlaşılacak bittiği. Bağımlılık sırasına diz; en riskli veya belirsiz adımı öne al.
3. Listeyi görev araçlarıyla (TaskCreate/TaskUpdate) tut; kullanıcı kalıcı istiyorsa projeye `YAPILACAKLAR.md` olarak da yaz (`- [ ]` / `- [x]` biçiminde).
4. Kullanıcı "başla" dediyse ya da iş açıkça senden isteniyorsa adımları sırayla yap, her biri bitince işaretle.
5. Plan değişirse listeyi güncelle; biten, kalan ve engellenen adımları kısaca bildir.
