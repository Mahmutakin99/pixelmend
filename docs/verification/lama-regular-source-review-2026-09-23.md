# LaMa Regular — kaynak incelemesi

Tarih: 23 Eylül 2026  
Durum: **Uygulamada etkin değil — doğrulanabilir ağırlık kaynağı bekleniyor**

## Bulgular

Resmî `advimman/lama` kaynağında `lama-regular` ayrı bir Places modeli olarak
tanımlanır. Makaledeki LaMa-Regular 45M parametrelidir; bu, PixelMend’deki
208 MB ONNX Dengeli LaMa ağırlığından ayrı bir mimari/hedeftir.

Ancak güncel resmî README yalnızca `big-lama.zip` indirmesini açıkça sunuyor.
Arşivdeki bütün eski Places/CelebA modelleri için yönlendirme yapılan resmî
Drive klasöründe şu an yalnız `big-lama.zip` görünür. `lama-places/lama-regular`
ağırlığını taşıyan üçüncü taraf Hugging Face aynası da ayrı lisans veya dağıtım
izni beyan etmiyor.

Bu nedenle üçüncü taraf ağırlığı uygulamaya indirmek, ONNX’e dönüştürmek veya
modeli “Hızlı” diye etkinleştirmek mümkün değildir. Aynı ağırlığı farklı adla
sunmak da kabul edilmez.

## Gerekli kanıt

Bu kart ancak aşağıdakilerden biri sağlanırsa açılabilir:

1. LaMa yazarlarının sabit sürüm, dosya bütünlüğü ve ağırlık dağıtım koşulunu
   açıkça yayımladığı resmî kaynak; veya
2. Ağırlık hak sahibinden yazılı yeniden dağıtım izni.

Sonrasında özgün ağırlık için SHA-256, kaynak/lisans kaydı, ONNX eşdeğerliği,
M4 hız/bellek ölçümü ve maskesiz piksel koruma kabulü tekrar yapılacaktır.
