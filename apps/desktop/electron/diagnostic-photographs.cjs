const {runDiagnostics} = require('./diagnostic-runner.cjs');

async function runPhotographs({api,report,models,signal,onProgress}) {
  const photos=await (await api('/diagnostics/photographs')).json();
  if(photos.length!==12 || new Set(photos.map(p=>p.id)).size!==12)throw new Error('12 fotoğraflık doğrulanmış test seti eksik.');
  report.metadata({photographs:photos,photographTiming:'First measured run plus three repeats; engine startup probing is separate, so the first run is not guaranteed cold.'});
  const inputs=photos.map(p=>({id:p.id,width:0})).concat([{id:'rocket',width:1600},{id:'rocket',width:2400}]);
  for(const input of inputs){
    const prefix=`photo-${input.id}-${input.width || 'thumbnail'}`;
    if(signal.aborted){report.record({id:prefix,name:prefix,status:'cancelled'});continue;}
    const fixture=await (await api(`/diagnostics/fixture?fixture_id=${input.id}&width=${input.width}`,{method:'POST'})).json();
    report.record({id:`${prefix}-source`,name:`${input.id} · ${fixture.width} × ${fixture.height} · kaynak bütünlüğü`,status:'passed',fixture});
    const cases=[];
    const variants=[{id:'lanczos',name:'Lanczos',algorithm:'lanczos',operation:'upscale'},
      {id:'opencv',name:'OpenCV',algorithm:'opencv_telea',operation:'remove'},
      ...models.filter(m=>m.state==='ready'&&['lama','realesrgan-x4plus','realesrgan-general-x4v3'].includes(m.id))
        .map(m=>({...m,algorithm:m.id==='lama'?'lama':m.id==='realesrgan-x4plus'?'realesrgan_x4plus':'realesrgan_general_x4v3'}))];
    for(const model of variants){
      for(const scale of model.operation==='upscale'?[1,2,4]:[1]){
        for(let repeat=0;repeat<4;repeat++)cases.push({
          id:`${prefix}-${model.id}-${scale}-${repeat}`,name:`${input.id} · ${fixture.width} × ${fixture.height} · ${model.name} · ${scale}× · ölçüm ${repeat+1}`,
          modelId:model.id,algorithm:model.algorithm,scale,provider:'automatic',repeat,
        });
      }
    }
    await runDiagnostics({api,report,models,signal,onProgress,fixture,cases,fixtureName:prefix});
  }
}
module.exports={runPhotographs};
