import {createRequire} from 'node:module';
import {describe, expect, it} from 'vitest';
const require = createRequire(import.meta.url);
const {engineCommand} = require('../electron/engine-path.cjs');

describe('engine sidecar path', () => {
  it('uses the Windows executable extension only for packaged Windows builds', () => {
    expect(engineCommand({isPackaged:true, resourcesPath:'C:\\app\\resources', dirname:'ignored', platform:'win32'}))
      .toEqual({executable:'C:\\app\\resources\\engine\\pixelmend-engine.exe', args:[]});
    expect(engineCommand({isPackaged:true, resourcesPath:'/app/resources', dirname:'ignored', platform:'darwin'}))
      .toEqual({executable:'/app/resources/engine/pixelmend-engine', args:[]});
    expect(engineCommand({isPackaged:true, resourcesPath:'/app/resources', dirname:'ignored', platform:'linux'}))
      .toEqual({executable:'/app/resources/engine/pixelmend-engine', args:[]});
  });
});
