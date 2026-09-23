export type AiOperation = 'upscale' | 'remove';
export type AiMethod = 'ai' | 'lanczos' | 'lama' | 'opencv';

export function showsAiControls(operation: AiOperation, method: AiMethod): boolean {
  return operation === 'upscale' ? method === 'ai' : method === 'lama';
}
