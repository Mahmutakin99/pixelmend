import {createRequire} from 'node:module';
import {describe, expect, it} from 'vitest';
const require = createRequire(import.meta.url);

describe('desktop model and job boundary', () => {
  it('routes the fast model explicitly and rejects models belonging to another tool', () => {
    const {jobForm}=require('../electron/model-ipc.cjs');
    const payload={assetId:'a'.repeat(32),operation:'upscale',upscaleMethod:'ai',targetWidth:100,targetHeight:80,modelId:'realesrgan-general-x4v3',intent:'preserve_size'};
    expect(jobForm(payload).get('algorithms')).toBe('["realesrgan_general_x4v3"]');
    expect(jobForm(payload).get('model_id')).toBe('realesrgan-general-x4v3');
    expect(jobForm(payload).get('intent')).toBe('preserve_size');
    expect(()=>jobForm({...payload,modelId:'lama'})).toThrow();
  });
  it('allowlists model routes and refuses renderer URLs, paths and actions', async () => {
    const {modelRoute} = require('../electron/model-ipc.cjs');
    expect(modelRoute('realesrgan-x4plus', 'install')).toEqual({route:'/models/realesrgan-x4plus/install',method:'POST'});
    expect(modelRoute('lama', 'delete')).toEqual({route:'/models/lama',method:'DELETE'});
    for (const id of ['../lama','https://example.com/model','lama/install']) expect(()=>modelRoute(id,'install')).toThrow();
    expect(()=>modelRoute('lama','download')).toThrow();
  });
  it('uses trusted policy and explicit algorithms, with legacy Lanczos compatibility', () => {
    const {jobForm} = require('../electron/model-ipc.cjs');
    const payload = {assetId:'a'.repeat(32),operation:'upscale',targetWidth:20000,targetHeight:10000};
    expect(jobForm(payload,{max_output_pixels:200000000}).get('algorithms')).toBe('["lanczos"]');
    expect(jobForm({...payload,upscaleMethod:'ai'},{max_output_pixels:200000000}).get('algorithms')).toBe('["realesrgan_x4plus"]');
    expect(()=>jobForm(payload,{max_output_pixels:50000000})).toThrow();
    expect(()=>jobForm({...payload,upscaleMethod:'bogus'},{})).toThrow();
    expect(()=>jobForm({...payload,targetWidth:20001},{})).toThrow();
    expect(()=>jobForm({...payload,assetId:'../../etc/passwd'},{})).toThrow();
  });
  it('defaults to LaMa and only uses OpenCV when explicitly selected', () => {
    const {jobForm} = require('../electron/model-ipc.cjs');
    const form = jobForm({
      assetId: 'a'.repeat(32),
      operation: 'remove',
      selectionStrokes: [{mode:'draw', points:[{x:4,y:4}], color:'#ff3b6b', opacity:1, size:20, hardness:1}],
    });
    expect(form.get('algorithms')).toBe('["lama"]');
    const payload = {assetId:'a'.repeat(32), operation:'remove', selectionStrokes:[]};
    expect(jobForm({...payload,removeMethod:'opencv'}).get('algorithms')).toBe('["opencv_telea"]');
    expect(()=>jobForm({...payload,removeMethod:'unknown'})).toThrow();
  });
  it('routes the fast MI-GAN removal model explicitly', () => {
    const {jobForm} = require('../electron/model-ipc.cjs');
    const form = jobForm({assetId:'a'.repeat(32),operation:'remove',removeMethod:'lama',modelId:'migan-512-places2',selectionStrokes:[]});
    expect(form.get('algorithms')).toBe('["migan_512_places2"]');
    expect(form.get('model_id')).toBe('migan-512-places2');
  });
  it('shares one SSE stream, handles split events and aborts after last subscriber', async () => {
    const {createModelEvents} = require('../electron/model-ipc.cjs');
    let controller: ReadableStreamDefaultController<Uint8Array>;
    let signal: AbortSignal;
    let requests=0;
    const events = createModelEvents(async (_route:string, options:{signal:AbortSignal}) => {
      requests++;signal=options.signal;
      return new Response(new ReadableStream({start(c){controller=c;}}));
    });
    const received:unknown[]=[];
    const sender={id:1,isDestroyed:()=>false,send:(_channel:string,data:unknown)=>received.push(data),once:()=>{}};
    events.subscribe(sender);events.subscribe(sender);
    await new Promise(resolve=>setTimeout(resolve,0));
    controller!.enqueue(new TextEncoder().encode('event: models\r\ndata: {"mod'));
    controller!.enqueue(new TextEncoder().encode('els":[]}\r\n\r\n'));
    await new Promise(resolve=>setTimeout(resolve,0));
    expect(requests).toBe(1);expect(received).toEqual([{models:[]}]);
    events.unsubscribe(sender);expect(signal!.aborted).toBe(true);
    controller!.close();events.close();
  });
});
