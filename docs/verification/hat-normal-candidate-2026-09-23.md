# Real HAT GAN x4 — yerel aday doğrulaması

Tarih: 23 Eylül 2026  
Durum: **Uygulamada etkin değil — dağıtım koşulu bekleniyor**

## Kaynak ve bütünlük

- Resmî kaynak depo: `XPixelGroup/HAT`, commit
  `1638a9a822581657811867bf670717f8371fc3e5`.
- Varyant: README’de sadakat için önerilen normal `Real_HAT_GAN_SRx4.pth`;
  "sharper" varyant kullanılmadı.
- Resmî Google Drive dosya kimliği: `1Ma12vCWT27P9M99-s2RXnynKN-OQsBrv`.
- Ağırlık: 170.277.017 bayt;
  SHA-256 `f5b1e3bbbb05147ca2beefcc715279cb647d7976cbda67d62ea7e6e20d5ffcc7`.
- Kaynak kod lisansı: Apache-2.0; sabit lisans metni SHA-256
  `a91d57ebad8955a1757be7891ca2da8e07493e662f0e34e1e1926571e05f37fc`.

Resmî Google Drive ağırlık indirmesinde ağırlıkların yeniden dağıtımı veya
ticari kullanımı için ayrı ve açık bir izin bulunamadı. Kaynak kodun
Apache-2.0 olması bu ayrı dosya için otomatik dağıtım izni sayılmaz. Bu nedenle
PixelMend ağırlığı yayımlamaz, indirtmez ve modeli seçilebilir hale getirmez.

## Yerel teknik denetim

Resmî mimari dosyası `hat/archs/hat_arch.py` aynı committen alındı (SHA-256
`81d8cecf491975246c9ebb20480898c656f59de020f38b05daa68741e426117f`).
Mimari, resmî `params_ema` durum sözlüğünü strict biçimde yükledi: 20.772.507
parametre.

Yerel ONNX adayının sözleşmesi FP32, NCHW, RGB, 0..1 giriş aralığı, doğal 4×
çıktı ve 16 piksel pencere katlarıdır. Üretilen ONNX:

- Boyut: 161.871.750 bayt
- SHA-256: `bafb132e0338502b77ca311baf5097575ead5def859b659888fec287af75c36b`
- PyTorch/ONNX CPU eşdeğerliği: 64×64, 80×64 ve 64×80 girdilerde geçti;
  en büyük mutlak hata sırasıyla `1.1623e-05`, `1.0848e-05` ve `3.6955e-06`.

`HATGANUpscale` adaptörü pencere dışı kenar karolarını 16’nın katına yansıma
ile doldurur ve bu sentetik alanı birleştirmeden önce kırpar. Bu davranış
birim testiyle sabitlenmiştir.

Bu rapor kalite kabulü veya M4 performans kabulü değildir. Lisans açıklığa
kavuşmadan model manifesti, uygulama kurulumu, yayın ve kullanıcı seçimi
eklenmeyecektir.
