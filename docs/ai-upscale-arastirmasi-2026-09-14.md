# AI kalite artırma araştırması — 2026-09-14

## Karar özeti

PixelMend'in ilk **AI kalite artırma** sürümü için önerilen model ailesi **Real-ESRGAN**, varsayılan fotoğraf modeli olarak **RealESRGAN_x4plus**'tır. Kullanıcı 2×, 4× veya özel hedef ölçü seçer; model önce doğal 4× kalite artırma yapar, istenen kesin ölçü gerekiyorsa uygulama son aşamada Lanczos ile hedef ölçüye getirir. Bu, modelin desteklediği ölçek ile kullanıcı hedefinin birbirine karıştırılmasını önler.

Bu karar "her koşulda en yüksek algısal kalite" iddiası değildir. İmzalı ürün için en dengeli ilk seçenek; açık lisans, olgun ve yerel çıkarım araçları, genel fotoğraflardaki dayanıklılık, alfa/tile desteği ve sonraki Windows/Linux paketleme hedefi açısından en uygulanabilir seçenektir.

## Kaynaklara dayalı değerlendirme

| Aday | Güçlü taraf | PixelMend v1 kararı |
| --- | --- | --- |
| **RealESRGAN_x4plus** | Gerçek dünya fotoğraf restorasyonu için tasarlanmış; tile, alfa, gri/16-bit giriş ve isteğe bağlı çıktı ölçeği desteği belgelenmiş. Kod deposu BSD-3-Clause. | **Seçildi: genel fotoğraf AI kalite varsayılanı.** |
| realesr-general-x4v3 | Daha küçük genel-sahne modeli; denoise gücü ayarlanabilir. | V1 sonrasındaki “Hızlı AI” profili için benchmark adayı. |
| SwinIR | Apache-2.0; SR yanında denoise ve JPEG artefakt azaltma görevleri var. | Deterministik “gürültü/JPEG onarımı” modu için ikinci aday; ilk paket değil. |
| HAT | Apache-2.0 transformer; yüksek kalite araştırma seçeneği. | Apple M4 16 GB ve Windows/Linux paket boyutu/latency benchmarkı olmadan eklenmeyecek. |
| SUPIR / diffusion tabanlı restorasyon | Çok güçlü foto-gerçekçi sonuçlar üretebilir. | V1 dışı: büyük SDXL/LLaVA bağımlılıkları, ağır bellek ihtiyacı ve ticari kullanım için ayrı lisans gerektiriyor. |

Birincil kaynaklar:

- [Real-ESRGAN resmi deposu](https://github.com/xinntao/Real-ESRGAN): genel restorasyon amacı, `RealESRGAN_x4plus`, küçük `realesr-general-x4v3`, tile/alfa/16-bit ve arbitrary outscale davranışı.
- [Real-ESRGAN BSD-3-Clause lisansı](https://github.com/xinntao/Real-ESRGAN/blob/master/LICENSE).
- [SwinIR resmi deposu](https://github.com/JingyunLiang/SwinIR): SR, denoise ve JPEG artefakt azaltma kapsamı; Apache-2.0.
- [XPixelGroup HAT kaydı](https://github.com/orgs/XPixelGroup/repositories): HAT için Apache-2.0 ve araştırma konumu.
- [SUPIR lisansı](https://github.com/Fanghua-Yu/SUPIR/blob/master/LICENSE): ticari kullanım ve proprietary neural-network bileşenleri için ayrı lisans gereksinimi.

## Çalışma zamanı ve platform kararı

AI model ağırlıkları uygulama paketine veya git'e girmeyecek. Model yöneticisi immutable revision, SHA-256, boyut ve lisans manifestiyle indirme/doğrulama/kaldırma yapacak.

İlk teknik aday ONNX Runtime'dır:

- macOS Apple Silicon: CoreML Execution Provider denenir; ONNX Runtime'ın resmi macOS paketleri CoreML EP ile yayımlanır ve CPU/GPU/Neural Engine seçenekleri sunar ([resmi belge](https://onnxruntime.ai/docs/execution-providers/CoreML-ExecutionProvider.html)).
- Windows x64: DirectML sağlayıcısı, yoksa CPU fallback ile platforma özgü sidecar içinde paketlenir.
- Linux x64: CPU fallback ilk garantili yol olur; Vulkan/NCNN ikinci platform optimizasyonu olarak benchmark sonrası değerlendirilir.

Real-ESRGAN'ın NCNN/Vulkan taşınabilir ikilileri Windows/Linux/macOS için yayımlanıyor; bu, sonraki platform paketleme fazında karşılaştırma referansıdır ([resmi depo](https://github.com/xinntao/Real-ESRGAN), [NCNN RealSR örneği](https://github.com/nihui/realsr-ncnn-vulkan)). macOS performansının Metal/CoreML ve NCNN/MoltenVK arasında gerçek M4 ölçümüyle seçilmesi gerekir; varsayım yapılmayacak.

## Uygulama öncesi kabul ölçümü

1. `RealESRGAN_x4plus` için immutable kaynak/revision, SHA-256, byte boyutu ve ağırlık lisansı ayrı manifestte doğrulanır.
2. 12 izinli fotoğraflık sabit test setinde M4 16 GB için 2×/4× kalite, süre, peak RAM ve tile-seam ölçülür.
3. Aynı set ve hedef ölçülerde Lanczos, RealESRGAN_x4plus ve `realesr-general-x4v3` karşılaştırılır. Varsayılan model, görsel inceleme ve başarısızlık/bellek oranıyla seçilir; bu not gerektiğinde güncellenir.
4. AI işlemde ilerleme, iptal, model eksik/bozuk, disk yetersiz ve bellek yetersiz durumları kullanıcıya anlaşılır gösterilir. Başarısız backend "hazır" olarak sunulmaz.

## Sıralı ürün kuyruğu

1. **Sonraki iş:** Real-ESRGAN model yöneticisi, AI kalite modu, benchmark ve macOS Apple Silicon doğrulaması.
2. **Ardından:** Windows x64 ve Linux x64 sidecar derleme/paketleme, her platformda gerçek açılış ve inference testi, ZIP/kurulum çıktıları.
3. **Ardından:** SD 1.5 / SDXL tabanlı isteğe bağlı üretken doldurma; lisans onayı, cihaz/bellek kontrolü ve iptal ile ayrı ağır runtime.
4. **Sonraki değerlendirme:** SwinIR (deterministik JPEG/denoise) ve HAT (yüksek kalite) benchmarkı; SUPIR yalnız uygun ticari lisans ve ayrı ağır-runtime kararıyla değerlendirilir.
