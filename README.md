# PixelMend

Fotoğraflarınızda istemediğiniz bir alanı fırçayla işaretleyip silin — çevresindeki piksellerden yola çıkarak doldurulsun. Aynı uygulamada düşük çözünürlüklü fotoğrafları da büyütün. Birden fazla algoritma sonucu yan yana karşılaştırın, en beğendiğinizi seçin.

- **Tamamen yerel çalışır** — görselleriniz cihazınızdan çıkmaz, hiçbir üçüncü parti API'ye gönderilmez.
- **Çapraz platform** — v1 hedefi macOS Apple Silicon, Windows x64 ve Linux x64.
- **Doğrulanmış kapasiteye göre uyarlanır** — cihazda gerçekten çalışan backend ve modeller ölçülür; uygun olmayan ağır yöntemler varsayılan kapalı kalır.

> **Durum:** Planlama aşaması. Henüz uygulama kodu veya kullanılabilir bir sürüm yok. Güncel kararları `DURUM.md`'den takip edebilirsiniz.

## Bu ne işe yarar

1. **Nesne/leke silme (inpainting):** Bir fotoğrafta istenmeyen bir nesneyi, yazıyı veya lekeyi fırçayla işaretleyin; uygulama o alanı çevredeki dokuya uygun şekilde doldurur.
2. **Büyütme (upscale):** Düşük çözünürlüklü bir fotoğrafı detay kaybetmeden büyütün.
3. **Karşılaştırma:** Her iki iş için de birden fazla algoritma çalıştırılır, sonuçlar yan yana gösterilir — en iyi sonucu siz seçersiniz.

## Cihazınıza göre önerilen mod

Tier yalnız toplam RAM'e bakılarak seçilmeyecek. Uygulama; host belleğini, gerçekten seçilmiş accelerator/adapter'ın bellek bütçesini, modelin ilgili execution provider'da açılıp açılmadığını ve kısa kalibrasyon ölçümünü ayrı ayrı değerlendirecek.

| Doğrulanmış cihaz profili | Önerilen tier | Varsayılan kapsam |
|---|---|---|
| Hızlandırıcı yok, doğrulanamadı veya model probe'u başarısız | **Hafif** | OpenCV inpainting ve klasik Lanczos büyütme |
| LaMa, seçili backend'de doğruluk ve süre bütçesini geçti | **Orta** | + LaMa ile gelişmiş nesne silme |
| Real-ESRGAN bellek ve büyük görsel benchmark'ını geçti | **Yüksek** | + model tabanlı büyütme |
| Opsiyonel ağır motor ve seçilen SD modeli kendi host/device bellek kapılarını geçti | **Maksimum** (ayrıca indirilir) | + prompt destekli üretken doldurma |

8/16/24/32GB değerleri ancak ölçümler tamamlandığında yaklaşık örnekler olarak yayınlanacak; ayrık GPU'da VRAM, host RAM'in yerine geçmez. Ölçülemeyen kapasite `unknown` kalır ve uygulama temkinli öneri verir. Kullanıcı öneriyi **Ayarlar → Performans**'tan değiştirebilir. Ağır modlar varsayılan kapalıdır, yalnız kullanıcı açtığında ilgili model indirilir.

## Neden bu yaklaşım

Tek bir algoritmayı "doğru cevap" olarak dayatmak yerine, her iş için birkaç farklı yöntemin sonucunu üretip karşılaştırma imkanı sunuyoruz — hangi algoritma sizin fotoğrafınızda daha iyi sonuç verir, önceden bilinemez. Aynı zamanda düşük donanımlı bir cihazda da uygulamanın kullanılabilir kalması için ağır algoritmalar isteğe bağlı tutuluyor.

## Kullanılan modeller ve lisanslar

Bkz. [`docs/modeller-ve-lisanslar.md`](docs/modeller-ve-lisanslar.md).

## Geliştirme

Proje durumu, alınan kararlar ve sıradaki adımlar için: [`DURUM.md`](DURUM.md).
Mimari detay: [`docs/mimari.md`](docs/mimari.md).
Kurulum adımları: [`docs/faz-0-kurulum.md`](docs/faz-0-kurulum.md).

## Lisans

Belirlenecek (öneri: MIT veya Apache-2.0) — üçüncü parti model lisansları ayrıdır, bkz. [`docs/modeller-ve-lisanslar.md`](docs/modeller-ve-lisanslar.md).
