import {describe, expect, it} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {Settings} from './Settings';
import {aiReady, allowedActions, type ModelView} from './models';

const model:ModelView={id:'realesrgan-x4plus',name:'RealESRGAN x4plus',state:'unavailable',published:false,size_bytes:null,downloaded_bytes:0,revision:null,sha256:null,license_id:null,license_url:null,error:null,probe:null,in_use:false,stored_bytes:0,active_revision:null,last_used_at:null,stale_revisions:[]};
describe('model availability and performance facts',()=>{
  it('requires installed weights and a successful provider probe to enable AI',()=>{
    expect(aiReady(model)).toBe(false);
    expect(aiReady({...model,state:'ready',published:true})).toBe(false);
    expect(aiReady({...model,state:'ready',published:true,probe:{status:'passed',selected_provider:'CPUExecutionProvider',providers:['CPUExecutionProvider'],measured_at:'2026-09-15'}})).toBe(true);
  });
  it('disables unpublished and in-use mutations but allows cancellation during download',()=>{
    expect(allowedActions(model)).toEqual([]);
    expect(allowedActions({...model,published:true,state:'downloading'})).toEqual(['cancel']);
    expect(allowedActions({...model,published:true,state:'installed'})).toEqual(['probe','delete']);
    expect(allowedActions({...model,published:true,state:'ready',in_use:true})).toEqual([]);
    expect(allowedActions({...model,published:true,state:'failed'})).toContain('retry');
  });
  it('shows unknown hardware honestly and keeps unpublished installation disabled',()=>{
    const html=renderToStaticMarkup(<Settings value={{language:'tr',theme:'system'}} close={()=>{}} set={()=>{}} models={[model]} capabilities={undefined} refresh={()=>{}} error=""/>);
    expect(html).toContain('Performans');expect(html).toContain('Ölçülmedi');
    expect(html).toContain('settings-body');expect(html).toContain('performance-facts');
    expect(html).toContain('Henüz yayınlanmadı');
    expect(html).toMatch(/disabled=""[^>]*>İndir/);
  });
});
