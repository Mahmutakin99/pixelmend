/** Stable renderer-local marker for the last successfully saved state. */
export function documentFingerprint(document: unknown) {
  const value = document as {version?:number;original?:unknown;history?:{present?:unknown}} | null;
  return JSON.stringify(value?.history ? {version:value.version,original:value.original,present:value.history.present} : value);
}

export function isDocumentDirty(document: unknown, savedFingerprint: string | null) {
  return savedFingerprint === null || documentFingerprint(document) !== savedFingerprint;
}
