import {describe, expect, it} from 'vitest';
import {resultNotice} from './job-result';

describe('result notice', () => {
  it('explains when the selected accelerator retried on CPU', () => {
    expect(resultNotice({algorithm: 'realesrgan_x4plus', provider: 'CPUExecutionProvider', fallback_reason: 'accelerator_execution_failed'}, 1600, 900))
      .toContain('CPU’da tamamlandı');
  });
});
