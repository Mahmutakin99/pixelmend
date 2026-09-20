export type ErrorContext = 'save' | 'render' | 'upscale' | 'remove' | 'cancel';
export type UserError = {title: string; message: string};

/** Keep internal HTTP/IPC/engine details out of the product UI. */
export function userError(context: ErrorContext, error: unknown): UserError {
  const detail = error instanceof Error ? error.message : String(error ?? '');
  if (['not_ready', 'changed_model', 'missing_model', 'in_use'].some(code => detail.includes(code))) return {title: 'Model hazır değil', message: 'Ayarlar → Modeller bölümünden modeli kurun veya yeniden sınayın. Çalışan işlem varsa bitmesini bekleyin.'};
  if (detail.includes('selection_required')) return {title: 'Seçim gerekli', message: 'Nesneyi silmeden önce Nesne Seçici ile silinecek alanı işaretleyin.'};
  if (detail.includes('target_invalid')) return {title: 'Geçersiz ölçü', message: 'Genişlik ve yükseklik pozitif tam sayılar olmalı ve çıktı sınırını aşmamalıdır.'};
  if (detail.includes('stroke point is outside image bounds')) return {title: 'Çizim kaydedilemedi', message: 'Çizim görsel sınırına ulaştı. Düzenlemeyi geri alıp tekrar deneyin.'};
  if (detail.includes('model') && detail.includes('hazır değil')) return {title: 'AI kalite hazır değil', message: 'Performans ayarlarından modeli indirip doğruladıktan sonra tekrar deneyin.'};
  if (detail.includes('memory') || detail.includes('bellek')) return {title: 'Yetersiz bellek', message: 'Bu işlem için yeterli bellek yok. Daha küçük bir görsel veya hedef ölçü deneyin.'};
  if (context === 'save' || context === 'render') return {title: 'Görsel kaydedilemedi', message: 'Dosya yazılırken veya düzenlemeler hazırlanırken bir sorun oluştu. Konumu, disk alanını ve görseli kontrol edip tekrar deneyin.'};
  if (context === 'cancel') return {title: 'İptal isteği gönderilemedi', message: 'İşlem hâlâ çalışıyor olabilir. Birkaç saniye bekleyip tekrar deneyin.'};
  return {title: context === 'remove' ? 'Nesne silinemedi' : 'Görsel büyütülemedi', message: 'İşlem tamamlanamadı. Görseli ve seçilen ayarları kontrol edip tekrar deneyin.'};
}
