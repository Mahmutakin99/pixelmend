/** Stable renderer-local marker for the last successfully saved state. */
export function documentFingerprint(document: unknown) {
  return JSON.stringify(document);
}

export function isDocumentDirty(document: unknown, savedFingerprint: string | null) {
  return savedFingerprint === null || documentFingerprint(document) !== savedFingerprint;
}
