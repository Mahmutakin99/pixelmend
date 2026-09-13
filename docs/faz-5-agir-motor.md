# Faz 5 — Ağır Motor (Opsiyonel PyTorch Eklentisi)

Amaç: İsteyen ve donanımı doğrulanan kullanıcı için prompt destekli üretken doldurma; istemeyen kullanıcı PyTorch veya SD ağırlıklarını indirmez.

## Görevler

- [ ] Ayrı, isteğe bağlı ağır motor dağıtımı: `torch`, `diffusers`, `transformers`. Ana sidecar paketine gömülmez; kurulum ve sürüm durumu `capabilities.py` içinde ayrı, doğrulanmış alanlardır.
  - Kurulum biçimi, paket bütünlüğü, rollback, kaldırma ve platform başına boyut yayın tasarımından önce belgelenir; çalışma anında denetimsiz `pip install` yapılmaz.
- [ ] `models/sd_inpaint.py`: SD inpainting adapter'ı; seçili ve gerçekten probe edilmiş `mps | cuda | cpu` backend'i kullanır. Host RAM, device budget ve latency kapılarının tümü ayrı değerlendirilir.
- [ ] Kanonik model kimlikleri:
  - SD 1.5 Inpainting: `stable-diffusion-v1-5/stable-diffusion-inpainting` — kaldırılan RunwayML deposunun RunwayML ile bağlantısız topluluk aynası; “resmî RunwayML aynası” denmez.
  - SDXL Inpainting 0.1: `diffusers/stable-diffusion-xl-1.0-inpainting-0.1`.
  - Üretim manifesti repo kimliği yanında immutable revision/commit, dosya listesi, byte boyutu, SHA-256 ve lisans kaydını sabitler; repo taşınması ilgili faz başında yeniden doğrulanır.
- [ ] Prompt UI yalnız ağır motor kurulu ve model uygun olduğunda görünür. Serbest metin, seçili maske ve model ayarlarının sonucu nasıl etkilediği kısa ve açık anlatılır; varsayılan yol nesne silme olarak kalır.
- [ ] Ağır motor/model kurulu değilken algoritmalar “kurulu değil” olarak görünür; yükleme açık kullanıcı eylemi ister, boyut/lisans/backend gereksinimi indirme öncesi gösterilir. UI'ın geri kalanı bundan etkilenmez.
- [ ] Open RAIL lisans kapısı:
  - SD 1.5 için CreativeML Open RAIL-M, SDXL için CreativeML Open RAIL++-M linki ve anlaşılır özet gösterilir.
  - Genel ticari kullanım yasağı varmış veya koşulsuz serbestmiş gibi anlatılmaz. Attachment A kullanım yasakları ve model/ağırlık yeniden dağıtım yükümlülükleri ürün/release kontrol listesine girer.
  - Model kartlarının intended-use/limitations bölümleri ayrıca ürün politikası ve kullanıcı bilgilendirmesi açısından değerlendirilir.
- [ ] `engine/bench/` ağır motor vakalarıyla genişletilir:
  - Lisansı açık sabit görsel+maske+prompt; seed, scheduler, step sayısı, precision, backend ve model revision kayıtlıdır.
  - Fixed seed bit düzeyinde platformlar arası eşitlik vaadi değildir. Çıktı hash'i fingerprint; kalite değişikliği toleranslı metrik + görsel onayla değerlendirilir.
  - Session/model load, cold inference, warm median/p95, host/device peak ve disk boyutu ayrı ölçülür.

## Doğrulama

- Ağır motor kurulu değilken uygulama normal çalışır; ilgili algoritmalar yalnız “kurulu değil” durumundadır, crash veya gizli download yoktur.
- Kurulum/download yarıda kesilip tekrar denendiğinde bozuk ortam/model etkinleşmez; kaldırma sonrası hafif motor etkilenmez.
- SD 1.5 M4'te gerçek sonuç üretir; model load, cold ve warm süreleri ayrı kaydedilir. “Saniyeler” gibi peşin vaat yerine ölçüm sonucu kullanılır.
- SDXL 16GB M4'te denenir; başarılı/başarısız sonuç, OOM davranışı ve gerçek süre/bellek `DURUM.md` ile benchmark JSON'una dürüstçe yazılır.
- Lisans linki/özeti indirme öncesi erişilebilir; kullanılan model revision'ı ve SHA release manifestinden izlenebilir.

Bitince: `DURUM.md` ve model/lisans manifesti güncellenir; commit yalnız kullanıcı onayıyla atılır.
