# Faz 3 — Çoklu Algoritma + Karşılaştırma

Amaç: Kullanıcı aynı **iş türündeki** 3–4 algoritmanın sonuçlarını geldikçe karşılaştırabilsin. Inpainting ile upscale tek fan-out içinde karıştırılmaz; her job tek bir görev ve ortak çıktı ölçüsü sözleşmesine sahiptir.

## Görevler

- [ ] `registry.py` algoritma manifestlerini genişletir: tür (`inpaint | upscale`), model repo+revision+SHA, minimum host RAM, opsiyonel device budget, doğrulanmış backend'ler, cold/warm latency ve ölçülmüş bellek alanları.
- [ ] Klasik upscale baseline'ı eklenir (ör. Lanczos). Böylece model tabanlı büyütme “hiçbir şey” ile değil, hızlı ve düşük maliyetli bir baseline ile karşılaştırılır.
- [ ] `models/realesrgan_onnx.py`: seçilen Real-ESRGAN varyantı; upstream/model revision ve SHA sabitlenir.
  - Model, Faz 1'de kurulan manifest/hash/atomik etkinleştirme çekirdeğiyle edinilir; Faz 4 model yöneticisinin gelmesi beklenmez.
  - Büyük görselde karo (tile) + overlap + ağırlıklı birleştirme; görünür sınır ve peak bellek benchmark ile doğrulanır.
  - Tile boyutu ve overlap sabit sihirli sayı değil, model/cihaz manifest parametresidir; güvenli varsayılan ve fallback tanımlanır.
- [ ] Fan-out:
  - `/jobs` yalnız aynı `type` ve uyumlu scale/output sözleşmesine sahip algoritmaları kabul eder; karışık tür açık `422` döner.
  - Seçim sırası UI'da korunur; çalışma sırası “ilk yararlı sonucu erken gösterme” amacıyla doğrulanmış warm latency'ye göre hızlıdan yavaşa planlanabilir. Çalışma sırası API event'inde açıktır ve aynı girdide deterministiktir.
  - Tek inference worker korunur; her algoritma bitince şemalı result event'i akar. Event loop, health/heartbeat/cancel akışını bloklamaz.
- [ ] React sonuç grid'i:
  - SSE'yi main üzerinden dinler; her algoritma için yer tutucu/status kartı baştan görünür, sonuç geldiğinde bulunduğu kartta güncellenir. Böylece grid sonuç geldikçe zıplamaz.
  - Kartta algoritma adı, gerçek süre, warning ve ölçülebilmişse bellek bilgisi; tahmin ile gerçek değer ayrı etiketlenir.
  - Before/after karşılaştırma slider'ı pointer'a 1:1 bağlı, kesintisiz ve geri çevrilebilir; klavye okları, görünür odak ve erişilebilir değer metni vardır. Reduced motion'da gesture dışı geçişler sadeleşir.
  - Sonuç gelmesi ve bütün job'ın bitmesi ayrı durumlar olarak ekran okuyucuya duyurulur; ilk sonuç geldiğinde diğerleri iptal edilmeden kullanıcı inceleyebilir.
- [ ] “Bunu kaydet”: seçilen opaque `result_id` main üzerinden native diyaloğa yazılır. Diğer sonuçlar job yaşam döngüsünde kalır.
- [ ] Temizlik/disk bütçesi:
  - İş ekranı aktif job sürerken kapanırsa önce idempotent cancel çağrılır ve terminal durum beklenir; ardından veya kullanıcı terminal sonuçlar için açıkça “sonuçları temizle” dediğinde `DELETE /jobs/{id}` uygulanır.
  - Sidecar session TTL/başlangıç temizliği crash kalıntılarını ele alır; sonuç deposuna toplam kota ve “disk dolu” hata durumu eklenir.
  - Temizlik Faz 4'e ertelenmez; Faz 4 yalnız model deposunu yönetir.
- [ ] `engine/bench/` genişletilir:
  - 4000×3000 upscale stress fixture'ı ve lisans manifesti.
  - Karo birleşim sınırı için toleranslı kalite metriği/görsel golden; cold/warm süre ile host/device peak ayrı alanlar.
  - Faz 1'deki ham sonuç/baseline ayrımı korunur.

## GFPGAN kararı — v1 kapsamı dışında fizibilite kapısı

GFPGAN bu fazın veya v1'in teslimatı değildir; aşağıdaki kapılar ayrı bir gelecekteki fizibilite çalışmasında kapanmadan ürün kapsamına alınmaz:

- Resmî ve desteklenen hazır uçtan uca ONNX pipeline bulunmadığından, core ONNX artefaktının tekrarlanabilir export tarifi, upstream commit'i, model sürümü, SHA-256'sı ve kaynağı tanımlanır.
- Pipeline tek `session.run()` değildir: RetinaFace/landmark tespiti, beş noktalı hizalama, 512×512 affine warp, yüz başına çıkarım, ters affine dönüşüm, ParseNet/soft-mask paste-back ve çoklu yüz döngüsü belgelenir/test edilir.
- Real-ESRGAN arka plan iyileştirmesi opsiyoneldir; kapalı ve açık davranış ayrı ölçülür.
- CoreML, DirectML/Windows backend'i, CUDA ve CPU uyumluluğu ile end-to-end süre/bellek ölçülür.
- GFPGAN deposundaki “Apache-2.0 except third-party components”, StyleGAN2/DFDNet/ParseNet/facexlib ve seçilen tüm ağırlık/graph kaynakları dosya bazlı lisans manifestinde onaylanır.
- NC/SA kısıtı veya provenance belirsizliği çözülmezse modül ürün kapsamına alınmaz. Modeli lazy-download etmek bu lisans kapısını ortadan kaldırmaz.

Bu fizibilite çalışması Faz 4'e geçişi bloklamaz.

## Doğrulama

- Tek inpainting isteğinde `opencv_telea`, `opencv_ns`, `lama`; ayrı upscale isteğinde klasik baseline ve Real-ESRGAN seçilir. Karışık inpaint+upscale isteği reddedilir.
- Yer tutucular baştan görünür; en hızlı algoritmanın sonucu, yavaş sonuca göre belirgin erken kullanılabilir olur ve UI'ın geri kalanı responsive kalır.
- Sonuç kartlarının seçimi, before/after slider ve kaydetme pointer ile ve klavyeyle çalışır.
- 4000×3000 görsel Real-ESRGAN ile bellek hatası almadan tamamlanır; tile sınırı golden/tolerans kontrolünü geçer.
- Job silindikten sonra sonuç endpoint'leri erişilemez ve yalnız o job'ın temp dizini temizlenir; başka job/session dosyası etkilenmez.

Bitince: `DURUM.md` ölçüm ve doğrulama kanıtlarıyla güncellenir; commit yalnız kullanıcı onayıyla atılır.
