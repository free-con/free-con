---
name: pr-ac
description: Mevcut dal için GitHub'da pull request (PR) aç. Kullanıcı PR aç, pull request oluştur, birleştirme isteği aç ya da İngilizce open PR, create pull request dediğinde kullan.
argument-hint: "[isteğe bağlı başlık veya hedef dal]"
---

# PR Aç

Kullanıcıyla her zaman Türkçe konuş.

1. Değişikliklerin commit'lenip gönderildiğinden emin ol (değilse önce `kaydet` adımlarını uygula).
2. Hedef dalı bul (genelde `main`). `git log <hedef>..HEAD --oneline` ve `git diff <hedef>...HEAD --stat` ile PR'ın kapsamını çıkar.
3. Depoda PR şablonu var mı bak: `.github/pull_request_template.md`, `.github/PULL_REQUEST_TEMPLATE.md`, `PULL_REQUEST_TEMPLATE.md`, `docs/PULL_REQUEST_TEMPLATE.md`. Varsa başlıklarını kullan.
4. Başlık: kısa ve ne yapıldığını söyleyen. Açıklama: **Ne değişti**, **Neden**, **Nasıl test edildi** bölümleri; maddeler halinde, sade.
5. PR'ı GitHub araçlarıyla (`mcp__github__create_pull_request` vb.) veya `gh pr create` ile aç.
6. Kullanıcıya PR bağlantısını tam URL olarak ver ve PR'ı izlemek isteyip istemediğini sor (review ve CI için `watch` skill'i).
