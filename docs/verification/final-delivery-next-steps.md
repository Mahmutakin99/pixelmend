# Nihai teslim — sıradaki işler

Bu belge, PixelMend'in nihai teslim sırasını korur. Kullanıcı “sıradaki adıma
devam et” dediğinde, engel yoksa ilk tamamlanmamış maddeden başlanır.

2026-09-23 itibarıyla kalan kapsam iki uygulanabilir plana ayrıldı:

1. [`Model ve kalite planı`](../superpowers/plans/2026-09-23-pixelmend-models-and-quality.md): üç eksik model, ortak çalışma yolu ve altı modelin M4 kabulü.
2. [`Platform ve son teslim planı`](../superpowers/plans/2026-09-23-pixelmend-release-and-platforms.md): paketli üç platform, test kiti, UI kabulü ve Mac'e son kurulum.

Birinci planın kaynak ve çalışma yolu incelendi. İkinci planın tanı kiti ve
paketleme hazırlıkları ilk plan sürerken ilerleyebilir; nihai kurulum ve “altı
model tamam” kararı ilk planın kabul kapısına bağlıdır.

## Tamamlanan temel kilometre taşları

- RealESRGAN General x4v3 ve x4plus, lisans/provenance/SHA-256 kayıtlarıyla
  yayımlandı ve uygulama manifestlerine bağlandı.
- Her iki model, temiz geçici depoya indirilip M4 üzerinde Core ML ile gerçek
  işlem sınamasından geçti.
- Taşınabilir tanı kiti; HTML, JSON, ZIP rapor, macOS/Windows/Linux başlatıcıları
  ve standart uygulama içi test akışı eklendi.
- Kayıt durumu, fırça imleci, ayarlar sayfası, CPU geri dönüşü ve temel UI akışları
  için regresyonlar eklendi.

## Model planı — güncel kapılar

- Real HAT GAN x4: resmî normal ağırlık, mimari ve ONNX eşdeğerliği yerelde
  doğrulandı. Ağırlık için açık yeniden dağıtım/ticari kullanım izni olmadığı
  için uygulamada etkin değil. Kanıt:
  [`hat-normal-candidate-2026-09-23.md`](hat-normal-candidate-2026-09-23.md).
- LaMa Regular: resmî kaynak ayrı modeli tanımlıyor ancak indirtilebilir,
  lisanslı resmî ağırlık sunmuyor. Üçüncü taraf aynası da izin beyan etmiyor;
  kart etkin değil. Kanıt:
  [`lama-regular-source-review-2026-09-23.md`](lama-regular-source-review-2026-09-23.md).
- SDXL Inpainting: sabit paket ve Open RAIL++ koşulları incelendi. Son kullanıcı
  lisans akışı ile M4/16 GB üzerinde temsilî MPS kabulü eksik; kart etkin değil.
  Kanıt:
  [`sdxl-inpainting-source-review-2026-09-23.md`](sdxl-inpainting-source-review-2026-09-23.md).
- Düşük kaynak modu artık gerçek karo ve CPU iş parçacığı ayarını seçer;
  provider profilinin kalıcı önbelleği hâlâ açık iştir.

## Ardışık kalan işler

1. HAT ve LaMa Regular ağırlıkları için yazılı/ayrıntılı dağıtım izni al veya
   açık lisanslı, farklı ve ölçülebilir alternatifleri seç.
2. SDXL için Open RAIL++ koşullarını kullanıcıya ileten ve kabul ettiren lisans
   akışını tasarla; sonra yerel MPS worker, maskesiz piksel koruması ve kaynak
   kabulünü tamamla.
3. Bu üç kapı açıldıktan sonra altı modelin 12 fotoğraflık kalite/performance
   kabulünü tamamla.
4. Otomatik CPU/GPU sisteminde profil önbelleğini ekle ve arayüzde CPU geri
   dönüş açıklamasını gerçek ölçümden besle.
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
