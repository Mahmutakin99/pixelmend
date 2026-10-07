# PixelMend 1.1.0-alpha.4

Apple Silicon için deneysel Mac ön sürümü. [İndirme dosyaları](https://github.com/Mahmutakin99/pixelmend/releases/tag/v1.1.0-alpha.4).

## Değişiklikler

- Rahat çalışma için önerilen bellek miktarının altında görsel üretimi başlatılabilir.
- Kritik bellek baskısında yeni model aşaması bekler; bellek rahatladığında otomatik devam eder. Bekleme iptal edilebilir.
- Bellek ayırma hatasında yalnız başarısız görsel aşaması yeniden denenir. Görsele dönüştürme aşaması başarısız olduğunda tamamlanmış denoise verisi korunur.
- Gerçek ilerleme süren üretim beş dakika sınırıyla kesilmez. On dakika boyunca gerçek ilerleme görülmeyen model süreci durdurulur.
- Model, hassasiyet, çalışma çözünürlüğü ve mevcut derlenmiş MLX işlemleri korunur.

## Kurulum

DMG'yi açıp PixelMend'i Applications klasörüne sürükleyin veya ZIP'i açın.
Alternatif olarak:

```sh
brew install --cask Mahmutakin99/pixelmend/pixelmend
```

Homebrew tanımı [ayrı tap deposundadır](https://github.com/Mahmutakin99/homebrew-pixelmend).
Mevcut PixelMend elle kurulmuşsa Homebrew yönetimine geçmeden önce uygulamayı
kapatıp yalnız eski `PixelMend.app` kopyasını kaldırın. Model ve proje dizinlerini
silmeyin. Tap'ın yönettiği kurulumlar sonraki sürümlerde şu komutla güncellenebilir:

```sh
brew upgrade --cask Mahmutakin99/pixelmend/pixelmend
```

Apple Silicon ve macOS 15+ gerekir. Üretken AI özellikleri en az 16 GB fiziksel
RAM ve kabul edilmiş cihaz/profil eşleşmesi gerektirir. Modeller uygulama
arşivlerine dahil değildir; ilk kurulum Ayarlar → AI modelleri üzerinden yapılır.
İşleme model kurulumu sonrasında yereldir. Mevcut modeller yeniden indirilmez.

## İmza

Bu paket yerel ad-hoc imzalıdır; **Developer ID imzası ve Apple notarizasyonu
yoktur**. İndirilen uygulama başka Mac'lerde Gatekeeper tarafından engellenebilir.
Yalnız güvendiğiniz kaynaktan indirilen uygulamalar için
[Apple'ın uygulama açma yönergelerini](https://support.apple.com/en-us/102445)
izleyin. Homebrew SHA-256 doğrulaması Apple notarizasyonunun yerini tutmaz.
Genel dağıtımda sorunsuz ilk açılış için Developer ID Application imzası,
notarizasyon ve pakete eklenmiş notarizasyon bileti gerekir.

## Doğrulama ve sınırlar

20 gerçek kaynak/stres/paketli model karşılaştırmasında Alpha3 referanslarıyla
çıktılar piksel düzeyinde aynı kaldı. İki profil ve üç yeni görsel en-boy oranı
karşılaştırıldı. Önceki Dengeli profil düzenleme kalite kaydı değişmedi.

113 hedefli motor testi, 12 arayüz testi, 6 Electron IPC testi ve TypeScript
kontrolü geçti. Çalışma paketi testlerinde 23 vaka vardı; dört gerçek model kabul
vakası açıkça atlandı ve ayrı gerçek model karşılaştırmaları yapıldı.

Paketli motor yaklaşık 4.3 GiB kullanılabilir bellekle iki profili de kabul etti.
Üç kontrollü stres denemesinde bellek işlem sırasında 1.96 GiB'ye kadar düştü;
bu denemeler 4.9–5.3 GiB civarında başladı. Bu sonuçlar her Mac'te veya başlangıçta
4.2 GiB bellekle her işin tamamlanacağı garantisi değildir. Süre diğer uygulamalara,
bellek baskısına ve takas belleğine bağlıdır.

Release ekleri ZIP, DMG, her arşivin SHA-256 dosyası, derleme bilgisi, imza durumu
ve doğrulama raporudur. Derleme mevcut kaynak değişiklikleri commit edilmeden
tamamlanmıştır; `release-provenance.json` yayımlanan kaynak commit'ini ve paketlerin
sağlama toplamlarını ilişkilendirir.
