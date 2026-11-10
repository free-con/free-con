# Claude Skill Paketi (Türkçe)

Claude Code için 19 Türkçe skill. Hepsi bu depoda açılan oturumlarda otomatik çalışır; kendi bilgisayarına kurmak için aşağıya bak.

| Skill | Ne yapar |
|---|---|
| `watch` | PR, test, sunucu, log, deploy izler; bitince haber verir |
| `kaydet` | Değişiklikleri commit'ler ve gönderir (push) |
| `pr-ac` | GitHub'da pull request açar |
| `hata-ayikla` | Hatayı yeniden üretir, kök nedenini bulur, düzeltir |
| `test-yaz` | Otomatik testler yazar ve çalıştırır |
| `kod-acikla` | Kodu sade Türkçeyle açıklar |
| `kod-incele` | Kodu hata ve güvenlik açısından inceler |
| `duzenle` | Kodu davranışı bozmadan temizler (refactor) |
| `guvenlik-kontrol` | Sızmış şifre, açık ve eski bağımlılık tarar |
| `yeni-proje` | Sıfırdan çalışır bir proje kurar |
| `sunucu-calistir` | Projeyi çalıştırır, hazır olduğunu doğrular |
| `komut-yardim` | Terminal komutlarını yazar, açıklar, riskini söyler |
| `readme-yaz` | Türkçe README / belge yazar |
| `veri-analiz` | CSV/Excel verisini analiz eder, grafik çizer |
| `arastir` | İnternetten kaynaklı araştırma yapar |
| `ozetle` | Metin, PDF, sayfa, log özetler |
| `cevir` | Diller arası çeviri yapar |
| `e-posta-yaz` | E-posta, mesaj, dilekçe taslağı hazırlar |
| `yapilacaklar` | İşi adımlara böler, yapılacaklar listesi tutar |

## Bilgisayara kurulum

`kurulum.zip`'i indir, aç ve:

- **Windows:** `kur-windows.bat` dosyasına çift tıkla.
- **Mac / Linux:** terminalde çalıştır:

```bash
bash kur-mac-linux.sh
```

Kurulum tüm skill'leri `~/.claude/skills/` altına yazar ve `~/.claude/CLAUDE.md` dosyasına "her zaman Türkçe konuş" ayarını ekler (bir kez). Sonra Claude Code'u yeniden aç.

## Claude ayarlarına yükleme (claude.ai)

`skill-zipleri/` klasöründeki her `.zip` tek bir skill'dir. Claude ayarlarında Skills bölümünden istediklerini tek tek yükle.

## Skill ekleme / değiştirme

`.claude/skills/<ad>/SKILL.md` dosyasını düzenle, sonra kurulum dosyalarını yeniden üret:

```bash
python3 kurulum/olustur.py
```
