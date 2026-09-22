export type ResultDetail = {
  algorithm: string;
  provider: string | null;
  fallback_reason?: string | null;
};

export function resultNotice(detail: ResultDetail | undefined, width: number, height: number) {
  const algorithm = detail?.algorithm ?? '';
  const provider = detail?.provider ?? 'CPU';
  const fallback = detail?.fallback_reason === 'accelerator_execution_failed'
    ? ' Hızlandırıcı işlemi tamamlayamadığı için aynı model CPU’da tamamlandı.'
    : '';
  return `Sonuç hazır: ${width} × ${height} · ${algorithm} · ${provider}.${fallback} Uygula veya Vazgeç.`;
}
