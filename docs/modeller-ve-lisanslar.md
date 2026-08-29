# Modeller, Codec'ler ve Lisans Kapıları

GitHub'da açık kaynak paylaşılacağı ve uygulama binary dağıtacağı için yalnız repo üst lisansı yeterli değildir. Kullanılan kod, dönüştürülmüş graph, ağırlık, yardımcı model ve binary codec dosyaları ayrı ayrı izlenir.

**Son kaynak doğrulaması:** 2026-08-28. Model ekosistemi hareketlidir; her ilgili faz başında repo/revision/dosya yeniden doğrulanır.

## Model tablosu

| Model/bileşen | İş | Lisans durumu | Kanonik kaynak / ürün durumu | Tier |
|---|---|---|---|---|
| OpenCV inpaint (Telea / Navier-Stokes) | Küçük alan inpainting | OpenCV Apache-2.0 | OpenCV yerleşik; dependency sürümü lock edilir | Hafif |
| LaMa ONNX | Büyük alan inpainting | Model kartı Apache-2.0 | [`Carve/LaMa-ONNX/lama_fp32.onnx`](https://huggingface.co/Carve/LaMa-ONNX); opset 17, fixed 512×512, SHA-256 `1faef5301d78db7dda502fe59966957ec4b79dd64e16f03ed96913c7a4eb68d6` | Orta |
| Klasik resize (Lanczos vb.) | Upscale baseline | Kullanılan Pillow/OpenCV lisansına bağlı | Model ağırlığı yok; Faz 3 baseline'ı | Hafif |
| Real-ESRGAN | Model tabanlı upscale | Resmî kod repo BSD-3-Clause; seçilecek ONNX graph/ağırlık ayrıca manifestlenmeli | [`xinntao/Real-ESRGAN`](https://github.com/xinntao/Real-ESRGAN); kanonik ONNX artefakt/revision Faz 3 kapısı | Yüksek adayı |
| SwinIR | Alternatif upscale | Resmî repo Apache-2.0; seçilecek ağırlık/export ayrıca doğrulanmalı | [`JingyunLiang/SwinIR`](https://github.com/JingyunLiang/SwinIR); v1 taahhüdü değil | Gelecek aday |
| GFPGAN | Yüz iyileştirme | **Açık lisans/provenance kapısı; v1 için onaylı değil** | [`TencentARC/GFPGAN`](https://github.com/TencentARC/GFPGAN): “Apache-2.0 except third-party components”; resmî desteklenen uçtan uca ONNX artefakt yok | v1 dışında |
| Stable Diffusion 1.5 Inpainting | Prompt'lu üretken doldurma | CreativeML Open RAIL-M ⚠️ kullanım ve dağıtım koşullu | [`stable-diffusion-v1-5/stable-diffusion-inpainting`](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-inpainting); kaldırılan RunwayML deposunun RunwayML ile bağlantısız topluluk aynası | Maksimum |
| SDXL Inpainting 0.1 | Daha yüksek kaliteli üretken doldurma | CreativeML Open RAIL++-M ⚠️ kullanım ve dağıtım koşullu | [`diffusers/stable-diffusion-xl-1.0-inpainting-0.1`](https://huggingface.co/diffusers/stable-diffusion-xl-1.0-inpainting-0.1) | Maksimum |

## GFPGAN lisans ve pipeline kapısı

GFPGAN deposunun üst seviye Apache-2.0 beyanı third-party bileşenleri hariç tutar. Resmî LICENSE içinde StyleGAN2 türevi parçalar için NVIDIA Source Code License-NC, DFDNet türevleri için CC BY-NC-SA ve başka bileşen lisansları ayrıca listelenir. Resmî pipeline facexlib ile RetinaFace ve ParseNet gibi yardımcı modeller de kullanır; bu modellerin kendi provenance/lisansları ayrıca incelenmelidir.

Bu not, her dönüştürülmüş ağırlığın otomatik olarak bütün bu lisanslara tabi olduğuna dair hukuki hüküm değildir. Ürün kapısı şudur: seçilecek kaynak dosyalar, export tarifi, ONNX graph, GFPGAN ağırlığı, yüz tespit modeli ve parsing modeli tek tek kaynağa/lisansa bağlanmadan modül indirilemez, dağıtılamaz veya ticari kullanıma uygun sayılmaz. Lazy download bu yükümlülüğü kaldırmaz. Ayrıntılı teknik kapı `docs/faz-3-coklu-algoritma.md` içindedir.

## SD / SDXL Open RAIL notu

Open RAIL lisanslarında genel bir ticari kullanım yasağı yoktur; ancak Attachment A'daki kullanım yasakları bağlayıcıdır. Model/ağırlık dağıtılırsa lisans kopyası, gerekli bildirimler ve kullanım kısıtları sonraki kullanıcılara aktarılmalıdır. Model kartındaki intended-use ve limitations bölümleri ayrıca ürün politikası olarak değerlendirilir.

Faz 5'te kullanıcı model indirmeden önce doğru lisans linkini ve anlaşılır özeti görür. Ürün “koşulsuz serbest” veya yalnızca “ticari kullanılabilir” gibi eksik bir ifadeyle yetinmez.

## HEIF/HEIC codec kararı

HEIF/HEIC, 2026-08-29 tarihli ADR 13 ile v1 kapsamından çıkarılmıştır. v1 giriş formatları JPEG, PNG, WebP ve TIFF'tir; pakete HEIF decoder eklenmez.

Gelecekte destek yeniden değerlendirilirse aşağıdaki riskler yeni bir codec/provenance kapısında çözülmelidir:

- `pillow-heif` kaynak kodu BSD-3-Clause olsa da 2026-08-28 tarihli `LICENSES_bundled.txt`, yayımlanan binary wheel'in `x265` nedeniyle GPLv2 ve ayrıca LGPL bileşenler içerdiğini belirtir.
- Decoder-only, daha izinli `pi-heif` paketi 1.4.0 ile sonlandırılmıştır; yeni bir projede bakım riski değerlendirilmeden seçilmez.
- Seçenekler: dağıtıma uygun sürdürülen decoder, platform-native decode katmanı veya lisansı uygun biçimde kurulmuş libheif decoder build'i. Seçilen yol macOS/Windows/Linux paketlerinde gerçek codec ve notice dosyalarıyla doğrulanır.

`pillow-heif` veya başka bir HEIF codec'i ayrı ADR olmadan dependency lock'a giremez. HEVC patent/dağıtım koşulları için gerekiyorsa yayın öncesi hukuk incelemesi alınır.

## Model manifesti ve indirme prensibi

Hiçbir ağırlık dosyası git'e veya varsayılan uygulama paketine commit edilmez. Her indirilebilir model manifesti şunları içerir:

- repo kimliği ve immutable revision/commit;
- kesin filename'ler ve beklenen byte boyutu;
- her dosyanın SHA-256 değeri;
- kod, graph, ağırlık ve yardımcı modellerin lisans kimliği/linki;
- doğrulanmış backend/platform bilgisi.

İndirme geçici dosyaya yapılır; boyut ve hash doğrulanmadan etkinleşmez. Üretim hareketli `main` dalına bağlanmaz. Repo taşınır veya lisans/model kartı değişirse yeni revision ayrı inceleme olmadan otomatik kabul edilmez.

## Referans, fork edilmeyen proje

- **IOPaint** (eski adı lama-cleaner) — Apache-2.0, [`Sanster/IOPaint`](https://github.com/Sanster/IOPaint), arşivlenmiş. Maske harmanlama ve tiling stratejisi için referans; kodu fork/taşıma yok. Bkz. `docs/karar-gunlugu.md` madde 3.
