---
name: komut-yardim
description: Terminal/komut satırı komutlarını (bash, PowerShell, git, npm, pip, docker vb.) açıkla, istenen iş için doğru komutu yaz ve riskini söyle. Kullanıcı hangi komut, komutu yaz, terminalde nasıl yapılır, bu komut ne yapar, cmd, powershell ya da İngilizce command, terminal, shell dediğinde kullan.
argument-hint: "[yapılmak istenen iş veya açıklanacak komut]"
---

# Komut Yardımı

Kullanıcıyla her zaman Türkçe konuş. İstek: $ARGUMENTS

1. Kullanıcının işletim sistemini bağlamdan çıkar (Windows → PowerShell, Mac/Linux → bash). Belirsizse ikisini de ver.
2. Komutu kendi kod bloğunda ver (bash için ```bash). Peş peşe çalıştırılacak komutların her biri ayrı blokta olsun; başına `$` koyma.
3. Altına sade Türkçeyle: ne yapar, her parça ne anlama gelir.
4. **Risk uyarısı:** silme (`rm -rf`, `del`), üzerine yazma, `sudo`/yönetici, `--force`, internetten betik indirip çalıştırma gibi durumlarda açıkça uyar ve daha güvenli alternatif öner.
5. Bir komutu açıklaman istendiyse çalıştırmadan önce açıkla; tehlikeliyse çalıştırma.
