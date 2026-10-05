import {describe, expect, it} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {Settings, ModelCard} from './Settings';
import {aiReady, allowedActions, selectableModels, type ModelView} from './models';

const model:ModelView={id:'realesrgan-x4plus',name:'RealESRGAN x4plus',state:'unavailable',published:false,size_bytes:null,downloaded_bytes:0,revision:null,sha256:null,license_id:null,license_url:null,error:null,probe:null,in_use:false,stored_bytes:0,active_revision:null,last_used_at:null,stale_revisions:[]};
describe('model availability and performance facts',()=>{
  it('describes installed generative packages without requiring an ONNX provider',()=>{
    const packageModel={...model,id:'flux2-klein-4b-mlx-q4',runtime:'mlx' as const,
      source:'local' as const,verified_manifest:true,state:'installed',name:'Klein'};
    const html=renderToStaticMarkup(<ModelCard model={packageModel} refresh={()=>{}}/>);
    expect(html).toContain('Kurulu');
    expect(html).toContain('Modeli kontrol et');
    expect(html).not.toContain('Yerel ONNX');
    const absent=renderToStaticMarkup(<ModelCard model={{...packageModel,state:'absent'}} refresh={()=>{}}/>);
    expect(absent).toContain('Yerel paket klasörü seç');
  });
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
  it('never offers install or delete while cached discovery is queued',()=>{
    expect(allowedActions({...model,published:true,state:'waiting'})).toEqual([]);
  });
  it('offers only fast and balanced models while advanced candidates are coming soon',()=>{
    const advanced = {...model, id:'sdxl-inpainting', tier:'advanced' as const};
    const balanced = {...model, id:'lama', tier:'balanced' as const};
    expect(selectableModels([advanced, balanced])).toEqual([balanced]);
  });
  it('keeps technical capability data out of the default settings page',()=>{
    const html=renderToStaticMarkup(<Settings value={{language:'tr',theme:'system'}} close={()=>{}} set={()=>{}} models={[model]} capabilities={undefined} refresh={()=>{}} error=""/>);
    expect(html).toContain('Performans');
    expect(html).toContain('AI modelleri');
    expect(html).toContain('settings-page');
    expect(html).not.toContain('Ölçülmedi');
  });
  it('uses an Apple-style section navigation instead of a technical modal',()=>{
    const html=renderToStaticMarkup(<Settings value={{language:'tr',theme:'system'}} close={()=>{}} set={()=>{}} models={[model]} capabilities={undefined} refresh={()=>{}} error=""/>);
    expect(html).not.toContain('value="en"');
    expect(html).toContain('Genel');
    expect(html).toContain('Performans');
    expect(html).toContain('Tuval ve araçlar');
    expect(html).toContain('settings-nav');
    expect(html).toContain('settings-content');
    expect(html).toContain('Bitti');
  });
});

it('published packages offer download first and local installation second',()=>{
 const packageModel={...model,runtime:'mlx' as const,source:'published' as const,verified_manifest:true,published:true,state:'absent'};
 const html=renderToStaticMarkup(<ModelCard model={packageModel} refresh={()=>{}}/>);
 expect(html).toContain('Modeli indir');expect(html).toContain('Yerel paket klasörü seç');
 expect(html.indexOf('Modeli indir')).toBeLessThan(html.indexOf('Yerel paket klasörü seç'));
 const installed=renderToStaticMarkup(<ModelCard model={{...packageModel,state:'installed',last_check:{status:'deferred',code:'memory_insufficient',message:'Bellek yetersiz.'}}} refresh={()=>{}}/>);
 expect(installed).toContain('Kurulu');expect(installed).toContain('Kontrol ertelendi — şu an bellek yetersiz');
 expect(installed).not.toContain('Başarısız');expect(installed).not.toContain('Yeniden kurun');
});
