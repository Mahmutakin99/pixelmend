export function validBlob(value: unknown): boolean;
export function validStroke(value: unknown,width?:number,height?:number): boolean;
export function validGeneration(value: unknown): boolean;
export function validDocument(value: unknown): boolean;
export function photosOf(value: import('../src/document').EditorDocument): import('../src/document').BlobRef[];
