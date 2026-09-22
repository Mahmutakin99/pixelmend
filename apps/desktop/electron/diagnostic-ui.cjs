// Exercise the shipped renderer through real controls. Native file panels are
// redirected only inside this isolated self-test session to owned temporary files.
const {dialog, nativeTheme} = require('electron');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const {setTimeout:delay} = require('node:timers/promises');
const {runCases} = require('./diagnostic-runner.cjs');

async function runEditorChecks({window,api,report,signal,onProgress}) {
  const temp=fs.mkdtempSync(path.join(os.tmpdir(),'pixelmend-ui-test-'));
  const originalOpen=dialog.showOpenDialog, originalSave=dialog.showSaveDialog, originalTheme=nativeTheme.themeSource;
  const imagePath=path.join(temp,'örnek görsel.png'), pngPath=path.join(temp,'sonuç.png'), projectPath=path.join(temp,'proje.pixelmend');
  let projectOpen=false, broken=false;
  const errors=[];
  const crashed=()=>errors.push('Renderer process exited');
  window.webContents.on('render-process-gone',crashed);
  const js=source=>window.webContents.executeJavaScript(source);
  const wait=async expression=>{
    const until=Date.now()+15000;
    while(Date.now()<until){signal.throwIfAborted();if(await js(expression))return;await delay(100);}
    throw new Error('Arayüz beklenen duruma geçmedi.');
  };
  const button=name=>`[...document.querySelectorAll('button')].find(b=>(b.getAttribute('aria-label')||b.textContent.trim())===${JSON.stringify(name)} && b.getBoundingClientRect().width>0 && !b.disabled)`;
  const click=async name=>{await wait(`!!(${button(name)})`);await js(`(${button(name)}).click()`);await delay(150);};
  const screenshot=async id=>{await delay(200);report.artifact(`gorseller/ui-${id}.png`,(await window.webContents.capturePage()).toPNG());};
  const stroke=async()=>{
    const point=await js(`(()=>{const r=document.querySelector('canvas.mask').getBoundingClientRect();return {x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)}})()`);
    window.webContents.sendInputEvent({type:'mouseMove',...point});
    window.webContents.sendInputEvent({type:'mouseDown',button:'left',clickCount:1,...point});
    window.webContents.sendInputEvent({type:'mouseMove',x:point.x+5,y:point.y+3});
    await delay(80);await screenshot('brush-drag');
    window.webContents.sendInputEvent({type:'mouseUp',button:'left',clickCount:1,x:point.x+5,y:point.y+3});
    await delay(200);
  };
  try {
    const fixture=await (await api('/diagnostics/fixture?fixture_id=rocket&width=1600',{method:'POST'})).json();
    fs.writeFileSync(imagePath,Buffer.from(await (await api(`/assets/${fixture.asset_id}/export?format=PNG`)).arrayBuffer()));
    await api(`/assets/${fixture.asset_id}`,{method:'DELETE'});
    dialog.showOpenDialog=async()=>({canceled:false,filePaths:[projectOpen?projectPath:imagePath]});
    dialog.showSaveDialog=async(_window,options)=>({canceled:false,filePath:options?.defaultPath?.endsWith('.pixelmend')?projectPath:pngPath});
    window.webContents.setBackgroundThrottling(false);
    const cases=[
      {id:'ui-home',name:'Başlangıç · küçük ve geniş pencere · açık/koyu tema',run:async()=>{
        await wait(`!!(${button('Görsel Aç')})`);
        for(const theme of ['light','dark']){nativeTheme.themeSource=theme;for(const [w,h] of [[800,600],[1440,900]]){window.setSize(w,h);await screenshot(`home-${theme}-${w}`);}}
      }},
      {id:'ui-settings',name:'Ayarlar · tüm bölümler · Escape ile dönüş',run:async()=>{
        for(const theme of ['light','dark']){
          nativeTheme.themeSource=theme;await click('Ayarlar');
          for(const section of ['Genel','Tuval ve araçlar','AI modelleri','Performans','Hakkında']){
            await click(section);await wait(`document.querySelector('.settings-nav [aria-current="page"]')?.textContent===${JSON.stringify(section)}`);
            await screenshot(`settings-${theme}-${['Genel','Tuval ve araçlar','AI modelleri','Performans','Hakkında'].indexOf(section)}`);
          }
          window.webContents.sendInputEvent({type:'keyDown',keyCode:'Escape'});window.webContents.sendInputEvent({type:'keyUp',keyCode:'Escape'});
          await wait(`!document.querySelector('.settings-page')`);
        }
      }},
      {id:'ui-paint',name:'Görsel açma · çizim · geri al/yinele',run:async()=>{
        await click('Görsel Aç');await wait(`document.querySelector('.canvas img')?.complete`);
        await stroke();await wait(`!(${button('Geri al')})?.disabled && !!(${button('Geri al')})`);
        await click('Geri al');await click('Yinele');
        const count=await js(`(()=>{const c=document.querySelector('canvas.paint');return c.getContext('2d').getImageData(0,0,c.width,c.height).data.some((v,i)=>i%4===3&&v>0)})()`);
        if(!count)throw new Error('Çizim geri alma/yinelemeden sonra görünmüyor.');
        await screenshot('paint');
      }},
      {id:'ui-save',name:'PNG kaydı · Başlangıç’ta gereksiz ikinci uyarı yok',run:async()=>{
        await click('Kaydet');await click('Görsel olarak kaydet (PNG)');
        await wait(`document.querySelector('[role="status"]')?.textContent.includes('kaydedildi')`);
        if(!fs.existsSync(pngPath)||fs.statSync(pngPath).size<50)throw new Error('PNG dosyası yazılmadı.');
        await click('Başlangıç');await wait(`!!(${button('Görsel Aç')})`);await screenshot('saved-home');
      }},
      {id:'ui-project',name:'Proje kaydı · yeniden açma',run:async()=>{
        await click('Görsel Aç');await wait(`document.querySelector('.canvas img')?.complete`);
        await click('Kaydet');await click('Projeyi kaydet (.pixelmend)');
        await wait(`document.querySelector('[role="status"]')?.textContent.includes('Proje kaydedildi')`);
        const saved=JSON.parse(fs.readFileSync(projectPath,'utf8'));
        if(saved.format!=='pixelmend'||!Object.keys(saved.blobs).length)throw new Error('Proje dosyası geçersiz.');
        await click('Başlangıç');projectOpen=true;await click('Proje Aç');await wait(`document.querySelector('.canvas img')?.complete`);projectOpen=false;
      }},
      {id:'ui-remove',name:'Seçim · işlem önizleme · vazgeç/uygula',run:async()=>{
        await click('Nesne silme');await stroke();
        await js(`(()=>{const input=[...document.querySelectorAll('label')].find(l=>l.textContent.includes('OpenCV'))?.querySelector('input');if(!input)throw new Error('Klasik silme seçeneği bulunamadı');input.click()})()`);
        await click('Nesneyi Sil');await wait(`!!(${button('Uygula')})`);await screenshot('preview');await click('Vazgeç');
        await click('Nesneyi Sil');await wait(`!!(${button('Uygula')})`);await click('Uygula');await screenshot('applied');
      }},
    ];
    await runCases(cases.map(({run,...value})=>value),{signal,report,onProgress,execute:async c=>{
      if(broken)return {status:'incomplete',detail:'Önceki arayüz adımı başarısız; bağımlı senaryo çalıştırılmadı.'};
      try{await cases.find(item=>item.id===c.id).run();if(errors.length)throw new Error(errors.join('\n'));return {detail:'Gerçek renderer kontrolleri çalıştırıldı. Ekran görüntülerinin görsel incelemesi ayrıca gerekir.'};}
      catch(error){broken=true;await screenshot('failure').catch(()=>{});throw error;}
    }});
  }finally{
    dialog.showOpenDialog=originalOpen;dialog.showSaveDialog=originalSave;nativeTheme.themeSource=originalTheme;
    window.webContents.off('render-process-gone',crashed);
    fs.rmSync(temp,{recursive:true,force:true});
  }
}
module.exports={runEditorChecks};
