# 🤖 Jarvis: Kişisel Sesli Asistanınız

Jarvis, beyni **Claude** olan, Türkçe konuşan kişisel bir asistandır. "Jarvis" diye seslenirsiniz;
sizi dinler, bilgisayarınızda iş yapar ve sesli cevap verir. İsterseniz klavyeden yazarak da konuşabilirsiniz.

## Neler yapabilir?

| Ne söylersiniz | Ne yapar |
|---|---|
| "Jarvis, Spotify'ı aç" / "Chrome'u kapat" | Uygulama açar/kapatır (oyunlar ve Mağaza uygulamaları dahil) |
| "Jarvis, Tarkan çal" / "sonraki şarkı" / "sesi yüzde 30 yap" | YouTube/Spotify'da müzik açar, medya ve ses kontrolü yapar |
| "Jarvis, 10 dakika sonra çayı hatırlat" / "her gün 9'da ilacımı hatırlat" | Hatırlatıcı, alarm, zamanlayıcı kurar (tekrarlı da olabilir) |
| "Jarvis, yarın hava nasıl, şemsiye alayım mı?" | Hava durumuna bakar |
| "Jarvis, dolar kaç TL?" / "bugünün önemli haberleri neler?" | İnternette arar, sayfaları okur |
| "Jarvis, ekranımda ne var?" / "bu hata ne demek?" | Ekran görüntüsü alıp ekrana bakar ve yorumlar |
| "Jarvis, bilgisayar neden yavaş?" / "şarj ne durumda?" | İşlemci, bellek, disk, pil durumunu söyler |
| "Jarvis, masaüstündeki fatura dosyasını aç" | Dosya arar ve açar |
| "Jarvis, benim adım Ali, kahvemi şekersiz içerim, unutma" | Sizi hatırlar (kalıcı hafıza) |
| "Jarvis, not al: süt, ekmek, yumurta" | Not tutar |
| "Jarvis, bilgisayarı kilitle" / "1 saat sonra kapat" / "iptal et" | Kilitler, uyutur, kapatır (kapatma her zaman gecikmeli, iptal edilebilir) |
| "Jarvis, salonun ışığını kapat" | Akıllı ev kontrolü (Home Assistant varsa) |

Bir cevaptan sonra 8 saniye boyunca "Jarvis" demeden devam edebilirsiniz ("peki ya yarın?").

---

## Kurulum

### 1) Dosyaları indirin
[Bu bağlantıdan ZIP olarak indirin](https://github.com/free-con/free-con/archive/refs/heads/claude/claude-capabilities-2inii2.zip),
çıkartın ve içindeki **`jarvis`** klasörünü istediğiniz bir yere (örneğin Belgeler) taşıyın.

### 2) Claude API anahtarı alın
1. <https://console.anthropic.com> adresinde hesap açın.
2. **Billing** bölümünden kredi yükleyin (kullandıkça ödenir; 5 dolar ile yüzlerce komut verebilirsiniz).
3. **Settings → API Keys → Create Key** ile anahtar oluşturun ve kopyalayın (`sk-ant-...` ile başlar).

> claude.ai aboneliği (Pro/Max) API kredisi içermez; API ayrı ücretlendirilir.

### 3) Kurulumu çalıştırın
- **Windows:** `jarvis\kurulum\kur-windows.bat` dosyasına çift tıklayın.
  Python yoksa otomatik kurmayı dener. Sonunda API anahtarınızı sorar ve masaüstüne **Jarvis** kısayolu ekler.
- **Mac / Linux:** Terminalde `bash jarvis/kurulum/kur-mac-linux.sh` çalıştırın.
  Mac'te masaüstüne `Jarvis.command` eklenir; ilk açılışta mikrofon iznine **İzin Ver** deyin.

### 4) Başlatın
- Masaüstündeki **Jarvis** kısayolu → sesli mod
- **Jarvis (Yazı)** kısayolu (Windows) → klavyeden yazarak
- Elle: `jarvis-baslat.bat` (Windows) veya `./jarvis-baslat.sh` (Mac/Linux)

```
python jarvis.py                 # sesli mod
python jarvis.py --yazi          # yazarak konuşma
python jarvis.py --yazi --konus  # yazarak sorun, sesli cevap alın
python jarvis.py --ses-testi     # hoparlör ve mikrofon testi
python jarvis.py --mikrofonlar   # bağlı mikrofonları listele
python jarvis.py --model claude-haiku-5-5   # bu seferlik başka modelle
```

Yazı modunda kullanabileceğiniz komutlar: `/yeni` (yeni konuşma), `/hafiza`, `/maliyet`, `/yardim`, `/cikis`.
Sesli modda kapatmak için **"Jarvis, kendini kapat"** deyin ya da `Ctrl+C`'ye basın.

---

## Maliyet

Varsayılan model **Claude Opus 5.5** (en akıllısı), hızlı cevap için düşük düşünme seviyesinde (`JARVIS_EFFORT=low`).
Sıradan bir komut tahminen **1-3 sent** civarı tutar; internette arama yapınca biraz artar. Aynı konuşma içindeki
tekrarlanan kısımlar önbelleğe alındığı için ucuzlar. Harcamanızı her an `/maliyet` ile görebilirsiniz.

Daha ucuz/hızlı isterseniz `.env` dosyasında modeli değiştirin:

| Model | Özellik | Fiyat (milyon token, girdi / çıktı) |
|---|---|---|
| `claude-opus-5-5` | En akıllı (varsayılan) | $4 / $20 |
| `claude-sonnet-5-5` | Hızlı ve dengeli | $2 / $10 |
| `claude-haiku-5-5` | En hızlı, en ucuz | $0.10 / $0.50 |

> Opus ve Sonnet'te "yedek model" (fallback) açıktır: Claude'un güvenlik filtresi zararsız bir isteği
> yanlışlıkla reddederse istek otomatik olarak uygun bir modelle yeniden denenir. Kapatmak için `JARVIS_FALLBACKS=hayır`.

---

## Ayarlar (`.env` dosyası)

Kurulum `.env` dosyasını sizin için oluşturur. Not Defteri ile açıp değiştirebilirsiniz:

| Ayar | Açıklama | Varsayılan |
|---|---|---|
| `ANTHROPIC_API_KEY` | Claude API anahtarınız | (zorunlu) |
| `JARVIS_MODEL` | Claude modeli | `claude-opus-5-5` |
| `JARVIS_EFFORT` | Düşünme derinliği: `low`, `medium`, `high` | `low` |
| `JARVIS_USER_NAME` | Size nasıl hitap etsin | (boş = "efendim") |
| `JARVIS_NAME`, `JARVIS_WAKE_WORDS` | Asistanın adı ve uyanma kelimeleri | `Jarvis` |
| `JARVIS_CITY` | Hava durumu ve aramalar için şehir | `İstanbul` |
| `JARVIS_VOICE` | `tr-TR-AhmetNeural` (erkek) veya `tr-TR-EmelNeural` (kadın) | Ahmet |
| `JARVIS_VOICE_RATE` | Konuşma hızı (`+0%`, `+15%`...) | `+8%` |
| `JARVIS_STT` | Konuşma tanıma: `google` veya `whisper` (internetsiz) | `google` |
| `JARVIS_MIC` | Mikrofon numarası/adı (`--mikrofonlar` ile görün) | varsayılan mikrofon |
| `JARVIS_FOLLOW_UP_SECONDS` | Cevaptan sonra "Jarvis" demeden devam süresi | `8` |
| `JARVIS_DATA_DIR` | Hafıza/not/hatırlatıcı klasörü | `~/Jarvis` |
| `HA_URL`, `HA_TOKEN` | Home Assistant bağlantısı | (boş = kapalı) |

Asistanın adını değiştirmek isterseniz (örn. "Cuma"), `JARVIS_NAME=Cuma` ve `JARVIS_WAKE_WORDS=cuma` yazmanız yeterli.

### Akıllı ev (isteğe bağlı)
[Home Assistant](https://www.home-assistant.io/) kullanıyorsanız: Home Assistant'ta **Profil → Güvenlik → Uzun ömürlü erişim anahtarları**
bölümünden bir anahtar oluşturun ve `.env` dosyasına ekleyin:
```
HA_URL=http://homeassistant.local:8123
HA_TOKEN=buraya-anahtar
```
Güvenlik için kapı kilidi ve alarm cihazları Jarvis'e kapalıdır.

### İnternetsiz konuşma tanıma
Sesinizin Google'a gitmesini istemiyorsanız: `.venv\Scripts\python -m pip install faster-whisper` (Mac/Linux: `.venv/bin/python -m pip install faster-whisper`) çalıştırın ve `.env` içinde `JARVIS_STT=whisper` yapın.
İlk kullanımda model indirilir (~500 MB). Bilgisayarınızda çalışır; daha yavaş olabilir.

---

## Gizlilik ve güvenlik

- **Nereye ne gider:** Sesli modda Jarvis, "Jarvis" dendiğini anlayabilmek için mikrofonun duyduğu her cümleyi yazıya çevirir.
  `google` modunda bu cümleler Google'ın konuşma tanıma servisine gider (`whisper` modunda bilgisayarınızdan çıkmaz).
  Claude'a (Anthropic) ise sadece **"Jarvis" diye başlayan** komutlar ve cevaptan hemen sonraki kısa sürede söyledikleriniz gönderilir.
  Jarvis'in cevapları seslendirilmek için Microsoft'un ses servisine gider.
- **Yerel veriler:** Hafıza, notlar, hatırlatıcılar ve ekran görüntüleri sizin bilgisayarınızda `~/Jarvis` klasöründe durur.
- **API anahtarınızı** kimseyle paylaşmayın; `.env` dosyası sadece sizin bilgisayarınızdadır.
- **Kısıtlar:** Jarvis program dosyalarını (`.exe`, `.bat` vb.) dosya olarak açmaz, kritik sistem süreçlerini kapatmaz,
  bilgisayarı her zaman en az 10 saniye gecikmeyle kapatır ("iptal et" diyebilirsiniz) ve şifre gibi bilgileri hafızaya kaydetmez.
  Web sayfalarındaki talimatlara uymaz, onları sadece bilgi olarak kullanır.

---

## Sorun giderme

| Sorun | Çözüm |
|---|---|
| "API anahtarı bulunamadı" | `.env` dosyasında `ANTHROPIC_API_KEY=sk-ant-...` satırı olmalı |
| "API bakiyeniz bitmiş" | console.anthropic.com → Billing'den kredi yükleyin |
| Jarvis beni duymuyor | `--ses-testi` çalıştırın; yanlış mikrofon seçiliyse `--mikrofonlar` ile bakıp `JARVIS_MIC` ayarlayın |
| "Jarvis" dediğimi anlamıyor | Ekranda "(duyuldu: ...)" satırına bakın; Google'ın nasıl yazdığını `JARVIS_WAKE_WORDS` listesine ekleyin |
| Ses çıkmıyor | İnternet bağlantınızı kontrol edin (doğal ses internet ister); yedek ses için `pip install pyttsx3` |
| Linux'ta "PortAudio library not found" | `sudo apt install libportaudio2` |
| Mac'te mikrofon çalışmıyor | Sistem Ayarları → Gizlilik ve Güvenlik → Mikrofon → Terminal'e izin verin |

---

## Geliştiriciler için

```
jarvis/
├── jarvis.py               # giriş noktası
├── jarvis_core/
│   ├── app.py              # yazı ve ses döngüleri
│   ├── brain.py            # Claude ile konuşma ve araç döngüsü
│   ├── prompts.py          # Jarvis'in kişiliği ve kuralları
│   ├── voice.py            # mikrofon, uyanma kelimesi, konuşma
│   ├── memory.py           # kalıcı hafıza ve notlar
│   ├── reminders.py        # hatırlatıcılar
│   ├── config.py           # .env ayarları
│   └── tools/              # Jarvis'in yapabildiği işler
│       ├── computer.py     # uygulama, dosya, ekran, sistem, güç
│       ├── media.py        # müzik ve ses
│       ├── info.py         # hava durumu
│       ├── personal.py     # hafıza, not, hatırlatıcı araçları
│       └── smarthome.py    # Home Assistant
├── kurulum/                # tek tıkla kurulum betikleri
└── tests/                  # python -m pytest tests
```

**Yeni bir yetenek eklemek** için `jarvis_core/tools/` altındaki bir dosyada `registry.add(...)` ile isim,
açıklama, parametreler ve bir Python fonksiyonu tanımlamanız yeterli. Claude açıklamayı okuyup aracı ne zaman
kullanacağına kendisi karar verir.

Testler gerçek API çağrısı yapmaz: `pip install pytest` ve `python -m pytest tests`.
