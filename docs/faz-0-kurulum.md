# Faz 0 — M4 Mac Mini Kurulum Adımları

Bu dosya, `pixelmend/` klasörü M4 Mac Mini'ye taşındıktan sonra Faz 1'e başlamadan önce yapılması gerekenleri listeler. Her adımdan sonra çıktısını `DURUM.md` → `Ortam` bölümüne not düş.

## 1. Ön kontrol

```bash
sw_vers                          # macOS sürümü
sysctl -n hw.memsize | awk '{print $1/1073741824" GB RAM"}'
node --version                   # v20+ önerilir
python3 --version                # 3.9 yetersiz, 3.12 hedef
git --version
```

## 2. Python 3.12 + uv kurulumu

Proje `uv` ile yönetilecek (pip/venv yerine — hızlı, kilitli bağımlılık).

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.12
```

## 3. pnpm kurulumu (Node paket yöneticisi)

Node dağıtımında Corepack varsa onu kullan; bu M4'teki Node 25 kurulumunda Corepack bulunmadığı için Homebrew yolu kullanıldı:

```bash
brew install pnpm
pnpm --version
```

## 4. Homebrew bağımlılıkları (varsa eksikse)

```bash
brew install python@3.12   # uv zaten kendi Python'ını indirir, bu opsiyonel/yedek
```

## 5. Doğrulama

Aşağıdakilerin hepsi hatasız çalışmalı:

```bash
uv --version
uv python list          # 3.12 görünmeli
pnpm --version
node --version
```

## 6. Bir sonraki adım

Bu adımlar tamamlanınca `DURUM.md`'yi sürüm numaralarıyla güncelle. Faz 1'e geçmeden önce:

- `DURUM.md` içindeki proje lisansı ve HEIF/HEIC kararlarının kapalı olduğunu doğrula.
- Kullanıcıdan uygulama koduna geçme onayı al; 2026-08-29 tarihinde bu onay verildi.
- İlk commit öncesi `find . -name .DS_Store -print` ile macOS metadata dosyalarını listele. Silme hedeflerini doğruladıktan ve kullanıcı onayı aldıktan sonra bunları temizle; `.gitignore` yeni `.DS_Store` dosyalarını zaten dışlar.

**Not:** Bu dosya bu klasörü M4'e ilk taşıdığında bir kereliğine çalıştırılır; sonraki oturumlarda tekrar gerekmez, sadece `DURUM.md`'nin "Ortam" bölümüne bakılır.
