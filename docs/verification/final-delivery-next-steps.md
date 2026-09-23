# Nihai teslim — sıradaki işler

Bu belge, PixelMend'in nihai teslim sırasını korur. Kullanıcı “sıradaki adıma
devam et” dediğinde, engel yoksa ilk tamamlanmamış maddeden başlanır.

2026-09-23 itibarıyla kalan kapsam iki uygulanabilir plana ayrıldı:

1. [`Model ve kalite planı`](../superpowers/plans/2026-09-23-pixelmend-models-and-quality.md): üç eksik model, ortak çalışma yolu ve altı modelin M4 kabulü.
2. [`Platform ve son teslim planı`](../superpowers/plans/2026-09-23-pixelmend-release-and-platforms.md): paketli üç platform, test kiti, UI kabulü ve Mac'e son kurulum.

Başlangıç noktası birinci planın Real HAT GAN x4 görevidir. İkinci planın
tanı kiti ve paketleme hazırlıkları ilk plan sürerken ilerleyebilir; nihai
kurulum ve “altı model tamam” kararı ilk planın kabul kapısına bağlıdır.

## Tamamlanan temel kilometre taşları

- RealESRGAN General x4v3 ve x4plus, lisans/provenance/SHA-256 kayıtlarıyla
  yayımlandı ve uygulama manifestlerine bağlandı.
- Her iki model, temiz geçici depoya indirilip M4 üzerinde Core ML ile gerçek
  işlem sınamasından geçti.
- Taşınabilir tanı kiti; HTML, JSON, ZIP rapor, macOS/Windows/Linux başlatıcıları
  ve standart uygulama içi test akışı eklendi.
- Kayıt durumu, fırça imleci, ayarlar sayfası, CPU geri dönüşü ve temel UI akışları
  için regresyonlar eklendi.

## Sıradaki iş: gelişmiş büyütme modeli

1. Real HAT GAN x4 için resmî ağırlığı, lisansı ve ticari kullanım koşulunu
   doğrula.
2. Sabit SHA-256, boyut, kaynak revision'ı ve ONNX giriş/çıkış sözleşmesini
   kaydet.
3. PyTorch ile ONNX çıktısını birden çok örnekte karşılaştır; farklılık kabulünü
   belgele.
4. Atomik kurulum, model probe, M4/Core ML ve CPU çalıştırma yollarını ekle.
5. Gerçek fotoğraflarda 1× netleştirme, 2×, 4×; karo, alfa, bellek ve süre
   ölçümlerini yap. Kabulü geçmeden modeli “Hazır” olarak gösterme.

## Ardışık kalan işler

1. LaMa Regular'ı ayrı, doğrulanmış hızlı nesne silme modeli olarak entegre et.
2. SDXL Inpainting için yerel MPS/CPU worker, çok dosyalı atomik model paketi,
   maske dışı piksel koruması ve kaynak kabulünü tamamla.
3. Altı modelin 12 fotoğraflık kalite/performance kabulünü tamamla.
4. Otomatik CPU/GPU sisteminde düşük kaynak modunu gerçek karo/iş parçacığı
   ayarlarına bağla; profil önbelleği ve arayüzde CPU geri dönüş açıklamasını
   tamamla.
5. Windows NVIDIA/CUDA, Windows DirectML ve Linux CUDA/CPU paket yollarını
   hazırla; gerçek cihaz kabulünü dış test raporlarıyla kaydet.
6. Paketli macOS, Windows ve Linux uygulamalarını tanı kitiyle çalıştır; açık/koyu
   tema, ekran görüntüsü, klavye ve erişilebilirlik kabulünü tamamla.
7. macOS paketini `/Applications/PixelMend.app` içine güvenli biçimde güncelle;
   temiz profil ve mevcut model deposu ile yeniden doğrula.
8. Son raporları, test ZIP örneklerini, model karşılaştırmalarını, durum belgesini
   ve temiz çalışma ağacını teslim et.

## Doğruluk kuralı

Kurulmamış, yalnızca sağlayıcısı görünen, kaynak yetersiz kalan veya gerçek kalite
kabulünü geçmeyen model/sağlayıcı doğrulanmış ya da hazır olarak gösterilmez.
Windows ve Linux GPU desteği, gerçek cihaz raporu gelmeden doğrulanmış sayılmaz.
