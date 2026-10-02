# PixelMend Windows ve Linux test yönergesi

Bu metni test edecek kişiye olduğu gibi gönderin. Ayrıntılı, test-kit içine de
kopyalanan sürüm: [`tools/diagnostics/README.md`](../tools/diagnostics/README.md).
Kişisel fotoğraf kullanmayın; uygulama kendi örnek görselleriyle test yapar.

## Gönderilecek dosyalar

Her testçiye iki şey gönderin:

1. İşletim sistemine uygun PixelMend kurulum paketi.
2. Aynı sürümün, işletim sistemine uygun `test-kit` klasörü. Windows kitinde yalnız
   `PixelMend-Test.cmd`; Linux kitinde yalnız `PixelMend-Test.sh` bulunur.

Model dosyalarını ayrıca göndermeyin. Test ekranındaki **Eksik modelleri indir**
seçeneği, kullanılabilir modelleri resmi kaynaktan indirir ve doğrular.

## Windows

1. `PixelMend-...-Setup.exe` dosyasını kurun.
2. `test-kit` klasöründeki `PixelMend-Test.cmd` dosyasına çift tıklayın.
3. Açılan PixelMend test penceresinde **Eksik modelleri indir** kutusunu işaretleyin.
4. Önce **Standart testi başlat** seçeneğine basın ve bitmesini bekleyin. Bu hızlı kontroldür.
5. Bilgisayar boşta iken test penceresini yeniden açıp **Kapsamlı test**i de başlatın. Bu, 12 lisanslı fotoğrafla 1×/2×/4× ve büyük görsel işleri çalıştırır; saatler sürebilir.
6. Test bitince not alanına bilgisayarın ekran kartını ve görülen sorunu yazın.
7. **Notları rapora ekle** düğmesine basın.
8. Masaüstündeki her iki yeni `PixelMend-Test-....zip` dosyasını bana gönderin. Kapsamlı rapordaki karşılaştırma görselleri ayrıca insan gözüyle incelenir.

## Linux

AppImage gönderildiyse terminal açın ve dosyaların bulunduğu klasörde şunları çalıştırın:

```sh
chmod +x PixelMend-*.AppImage test-kit/PixelMend-Test.sh
sh test-kit/PixelMend-Test.sh
```

Betik tek AppImage'ı bulur; birden fazlası varsa tam yolu tek argüman olarak
verin. Sonra önce standart, bilgisayar boşta iken de kapsamlı koşuyu ayrı
çalıştırın. Her iki `PixelMend-Test-....zip` raporunu gönderin; kapsamlı
görsellerin insan incelemesi Linux kalite kabulü için zorunludur.

`.deb` gönderildiyse önce paketi dağıtımın yazılım yükleyicisiyle kurun; sonra:

```sh
sh test-kit/PixelMend-Test.sh
```

Uygulama bulunamazsa betik PixelMend çalıştırılabilir dosyasının tam yolunu ister.
DEB için de önce standart, sonra bilgisayar boşta iken kapsamlı koşuyu ayrı
çalıştırın; her iki ZIP'i ve kapsamlı görsel inceleme sonucunu gönderin.

## Bana ne gönderecekler?

- Önce yalnız `PixelMend-Test-....zip` raporu.
- ZIP oluşmadıysa, aynı tarih-saatli `PixelMend-Test-...` klasörünü ve
  `PixelMend-Test-Baslangic-....txt` dosyasını birlikte göndersinler.
- Ayrıca kısa mesaj olarak: işletim sistemi sürümü, RAM miktarı, varsa ekran
  kartı adı ve gördükleri hata ekranının görüntüsü.

ZIP raporu kişisel fotoğrafları veya tam dosya yollarını içermez. Test başarısız
olursa raporu yine gönderin; başarısızlık nedeni orada bulunur.
