# Faz 6 — Çapraz Platform Paketleme & Yayın

Amaç: v1 hedefleri için izlenebilir, kurulabilir ve gerçek artefakt üzerinde test edilmiş paketler: macOS Apple Silicon, Windows x64 ve Linux x64.

## Destek matrisi

| Platform | v1 mimari | Paket |
|---|---|---|
| macOS | arm64 / Apple Silicon | DMG veya ZIP; Developer ID imzalı, notarized ve stapled genel sürüm |
| Windows | x64 | NSIS installer; dağıtım/imzalama kanalı açık karara bağlı |
| Linux | x64 | AppImage + `.deb` |

macOS Intel v1 kapsamında değildir. 2026-08-28 itibarıyla GitHub'da `macos-26-intel` runner vardır; engel runner yokluğu değil, güncel ONNX Runtime'ın macOS x86_64 wheel yayımlamamasıdır. İleride desteklenirse ayrı native x64 dependency/build/test hattı gerekir; arm64 artefaktı sonradan `lipo` ile güvenilir biçimde Intel pakete dönüştürülmez.

## Görevler

- [ ] `electron-builder` kimlik ve hedefleri:
  - Kararlaştırılmış reverse-DNS `appId`, `productName: PixelMend`, paket adı `pixelmend` ve platform kimlikleri sabitlenir.
  - İkonların yayın formatları tamamlanır; app/update kimliği ilk imzalı betadan sonra keyfî değiştirilmez.
  - PyInstaller sidecar ve tüm native provider kütüphaneleri `extraResources` içine platforma/mimariye göre açıkça alınır.
- [ ] PyInstaller her OS/arch üzerinde native build edilir; Faz 2'deki `onedir` smoke tarifi CI'da gerçek paketli sidecar'a uygulanır.
  - Önce mevcut hook'lar; yalnız kanıtlanmış eksik için dar custom hook. `--collect-all` varsayılan çözüm değildir.
  - PyInstaller doğrudan OS'ler arası cross-build yapmaz. macOS multi-arch ancak tüm native dependency slice'ları mevcut ve ayrı doğrulanmışsa düşünülebilir; v1 buna dayanmaz.
- [ ] GitHub Actions matrisi hareketli `latest` varsayımlarına bırakılmaz; faz başında güncelliği doğrulanan açık label'lar kullanılır. 2026-08-28 planı:
  - macOS arm64: `macos-26`
  - Windows x64: `windows-2025`
  - Linux x64: `ubuntu-24.04`
  - Her job başlangıçta gerçek OS ve architecture'ı assert eder; yanlış runner sessizce paket üretmez.
- [ ] CI artefakt sözleşmesi:
  - `actions/upload-artifact@v4` ile sabit ve benzersiz ad: `pixelmend-<version>-<os>-<arch>-<package>`.
  - Paket, SHA-256 dosyası, build manifesti, dependency lock özeti, model manifesti ve smoke-test raporu birlikte yayınlanır; ham benchmark sonucu gerekiyorsa ayrı artefakttır.
  - PR build'leri imzasız/test amaçlı ve sınırlı retention'lıdır. İmzalama/notarization sırları yalnız korumalı tag/manual release job'ında bulunur; fork PR koduna açılmaz.
  - İndirilen CI artefaktı üzerinde yeniden smoke test yapılır; yalnız build workspace içindeki dosyanın çalışması yeterli sayılmaz.
- [ ] Platform inference paket stratejisi gerçek ölçümle kilitlenir:
  - macOS: `onnxruntime` + ölçümle seçilmiş CoreML/CPU davranışı.
  - Windows: DirectML'in sürdürülen durumu ve alternatif Windows ML değerlendirmesi Faz 4 ADR'sine göre paketlenir; eski varsayım körlemesine taşınmaz.
  - Linux: CPU varsayılanının yanında CUDA desteğinin dağıtım boyutu, driver uyumu ve ayrı paket gereksinimi karara bağlanır; `onnxruntime-gpu` herkese otomatik kurulmaz.
- [ ] macOS genel dağıtım:
  - Apple Developer Program/Developer ID kararı kapatılır; app ile gömülü PyInstaller sidecar/native binary'ler aynı güven zincirinde imzalanır.
  - Hardened runtime ve gerekli en dar entitlement'lar; nested binary imza doğrulaması; notarization ve staple.
  - CI artefaktından temiz kullanıcı profilinde Gatekeeper doğrulaması yapılır.
- [ ] Windows genel dağıtım:
  - Microsoft Store, Artifact Signing veya CA tabanlı OV/EV yolu açık kararla seçilir; sabit “sertifika $X/yıl” varsayımı plana yazılmaz.
  - İmza her sürümde tutarlı publisher identity sağlar fakat yeni uygulamada SmartScreen uyarısını ilk günden kesin kaldırmaz; release iletişimi bunu dürüstçe açıklar.
  - Installer, app executable, sidecar ve gerekiyorsa diğer PE dosyalarının imza kapsamı test edilir.
- [ ] Lisans ve tedarik zinciri:
  - Proje `LICENSE`; `THIRD_PARTY_NOTICES`; Python/Node/native binary lisansları; model lisans/link/revision manifesti paketle uyumlu tutulur.
  - GFPGAN v1'e girmez. HEIF decoder seçildiyse binary wheel/codec lisansı ve notice yükümlülüğü release gate'te doğrulanır.
  - Build'ler lock dosyalarından yapılır; model indirmeleri immutable revision + SHA kullanır. Paket/checksum ve mümkünse SBOM/provenance yayımlanır.
- [ ] README destek matrisi ve tier tablosu gerçek Faz 1/3/5 benchmark sonuçlarıyla güncellenir; “macOS” tek başına Intel desteği ima etmez.
- [ ] Sürüm numaralama, release notes ve `CHANGELOG.md` politikası yayın öncesi kilitlenir; tag yalnız kullanıcı onayıyla atılır.

## CI smoke kriterleri

Her platform artefaktı en az şunları geçer:

1. Temiz, modelsiz profil ile install/start.
2. Authenticated sidecar startup ve `/health`/`capabilities` main proxy akışı.
3. Küçük OpenCV işi.
4. LaMa model manifest doğrulaması, kontrollü download veya önceden hazırlanmış test cache'i ve bir gerçek ONNX session.
5. Opaque `result_id` ile preview/read/save.
6. Cancel, job delete, temp cleanup ve kontrollü app shutdown; zombi process yok.
7. Package signature/checksum/architecture doğrulaması.

## Yayın doğrulaması

- Matris üç hedefte yeşil olur ve indirilen artefakt smoke testini geçer.
- macOS paketi temiz Apple Silicon kullanıcı profilinde indirilip Gatekeeper üzerinden açılır; model cache boşken hafif akış çalışır.
- Windows ve Linux paketleri en az birer gerçek hedefte veya donanım hızlandırma iddiası yoksa temsilî VM'de kurulur. GPU/backend iddiası yalnız ilgili gerçek donanımda doğrulanır.
- Güncelleme/yeniden kurma kullanıcı ayarlarını ve özel model deposunu beklenmedik biçimde silmez; uninstall davranışı belgelenir.
- Release artefaktlarının SHA, imza, notice ve build manifesti yayımlanan dosyayla birebir eşleşir.

Bitince: `DURUM.md` gerçek artefakt linkleri ve smoke kanıtlarıyla güncellenir; sürüm etiketi ve commit yalnız kullanıcı onayıyla atılır.
