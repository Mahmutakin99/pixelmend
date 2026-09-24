# PowerPaint v2-1 — aday incelemesi (2026-09-24)

PowerPaint v2-1, SDXL'nin başarısız nesne silme kalite denemesinden sonra ilk adaydır. [Resmî model kartı](https://huggingface.co/JunhaoZhuang/PowerPaint-v2-1) nesne kaldırmayı kullanım amacı olarak gösterir ve üst düzey depoyu Apache-2.0 olarak işaretler. [Dosya ağacı](https://huggingface.co/JunhaoZhuang/PowerPaint-v2-1/tree/main) yaklaşık 9,52 GB gösterir; `PowerPaint_Brushnet` ile `realisticVisionV60B1_v51VAE` ayrı bileşenlerdir.

Bu inceleme **kurulum veya ürün kabulü değildir**. Bileşenlerin her birinin sabit commit kimliği, dosya boyutu, SHA-256 değeri ve kendi ağırlık lisansı henüz doğrulanmadı. Üst düzey Apache-2.0 etiketi, alt bileşenlerin dağıtım iznini tek başına kanıtlamaz. M4/16 GB bellek, maske çevresi çıktı kalitesi, Windows/Linux CPU yolu ve paketli çalışma da ölçülmedi. Bu kapılar geçilene kadar model kataloğunda kurulabilir görünmemelidir.

Kabul denemesinde önce yalnız maskenin çevresindeki ROI işlenecek; sonuçta maske dışı RGB ve alfa kaynakla birebir karşılaştırılacak. Düz yüzey, doku, yapı çizgisi, kenar ve geniş seçim görselleri LaMa/OpenCV ile görsel olarak karşılaştırılacak. Bu aday kaynak veya kalite kapısından geçmezse ZITS++ 512 aynı yöntemle incelenecek.
