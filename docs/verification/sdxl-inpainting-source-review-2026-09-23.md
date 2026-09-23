# SDXL Inpainting 0.1 — kaynak ve cihaz kabul incelemesi

Tarih: 23 Eylül 2026  
Durum: **Uygulamada etkin değil — lisans akışı ve gerçek cihaz kabulü bekleniyor**

## Sabit resmî paket

- Depo: `diffusers/stable-diffusion-xl-1.0-inpainting-0.1`
- Revision: `115134f363124c53c7d878647567d04daf26e41e`
- Lisans: CreativeML Open RAIL++-M (model kartındaki `openrail++`)
- FP16 ağırlık toplamı: 6.938.041.649 bayt

Paket; UNet, VAE, iki metin kodlayıcı, iki tokenizer, scheduler ve yapılandırma
dosyalarından oluşur. Büyük fp16 dosyalarının sabit SHA-256 değerleri resmî
Hugging Face LFS manifestinden alınmıştır:

| Dosya | Bayt | SHA-256 |
| --- | ---: | --- |
| `unet/diffusion_pytorch_model.fp16.safetensors` | 5.135.178.560 | `6470840731e98cc16713ddf3ac7ee458c9fdbcb881a98c6727cd4a938f227d3f` |
| `text_encoder_2/model.fp16.safetensors` | 1.389.382.884 | `a8622bd41f8d359df484fdf9de091edb9337a2fd747f0a5c9c320a62e24d1fd3` |
| `text_encoder/model.fp16.safetensors` | 246.144.867 | `fc83cf401d930147807e7c44021c164bcc5508c9d4cc0ff35f4e354685ca9cd0` |
| `vae/diffusion_pytorch_model.fp16.safetensors` | 167.335.338 | `4ad62825e5c8b31eefb77355ba6693785619bf7d669d9b1a6fd9f19dec6d65b3` |

23 Eylül'de resmî revision'dan küçük dosyalar da indirilip SHA-256 ile
doğrulandı. `sdxl_package.py` içindeki manifest, dört ağırlığa ek olarak
`model_index.json`, scheduler, iki text-encoder yapılandırması, iki tokenizer
seti, UNet ve VAE yapılandırmalarını kapsar: toplam **18 dosya** ve
**6.941.218.469 bayt**. Böylece bir tokenizer veya yapılandırma eksikken yalnız
ağırlıkların bulunması modelin hazır sayılması için yeterli değildir.

`model_package.py` bu tür çok dosyalı paketleri her dosya doğrulandıktan sonra
tek atomik revision dizini olarak etkinleştirmek için eklendi. Eksik, bozuk veya
bağlantı içeren bir paket hazır sayılamaz.

## Lisans ve cihaz kapısı

Open RAIL++-M yeniden dağıtıma izin verir, ancak uygulama dağıtımında kullanıcı
için lisansın kullanım kısıtları uygulanabilir bir sözleşme olarak bulunmalı ve
sonraki kullanıcılara lisans iletilmelidir. PixelMend’de bu kabul/iletişim akışı
henüz yoktur; bu yüzden model kartı indirme veya hazır durumu gösteremez.

Bu Mac: Apple M4, 16 GB birleşik bellek ve doğrulama anında 77 GiB boş disk.
Sadece fp16 dosyaları 6,46 GiB olsa da çalışma sırasında ağırlıklar, etkinlikler,
VAE ve görüntü bağlamı ek bellek ister. Bu nedenle yalnız dosya boyutuna bakıp
MPS kabulü ilan edilmemiştir. Gerçek temsilî MPS işi, bellek zirvesi, iptal,
maskesiz piksel/alpha korunumu ve görsel inceleme tamamlanmadan SDXL bu cihazda
“çalışır” sayılmayacaktır.

Model kartı ayrıca yüzlerin ve metnin zor olabileceğini, VAE’nin kayıplı olduğunu
belirtiyor. Sonuç, yalnız maskeli RGB bölgesine birleştirilip kaynak alfa ve
maskesiz pikseller birebir korunmadan sunulamaz.

`models/sdxl_worker.py` bu sözleşmeyi uygular: doğrulanmış paketi kontrol eder,
seçim çevresindeki en fazla 1024 px bağlamı kare biçimde 512 px çalıştırma
girdisine dönüştürür, seed/arka-plan tamamlama bilgisini döndürür ve sonucu
yeniden yalnız seçili RGB piksellerine birleştirir. Diffusers/Torch runtime'ı
henüz paketlenmediğinden worker şu an açık, güvenli `SDXL çalışma bileşeni bu
uygulama paketinde kurulu değil` hatası verir; model kartı etkinleşmez.
