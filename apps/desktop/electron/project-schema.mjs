// Shared disk/editor contract. No filesystem access; usable in the renderer.
export const validBlob=v=>!!v&&typeof v.id==='string'&&v.id.length>0&&typeof v.uri==='string'&&v.uri.startsWith('pixelmend://')&&Number.isInteger(v.width)&&v.width>0&&Number.isInteger(v.height)&&v.height>0;
export function validStroke(v,width=Infinity,height=Infinity){
 return !!v&&typeof v.id==='string'&&['draw','erase'].includes(v.mode)&&Array.isArray(v.points)&&v.points.length>0&&v.points.length<=8192&&v.points.every(p=>Number.isFinite(p?.x)&&Number.isFinite(p?.y)&&p.x>=0&&p.y>=0&&p.x<width&&p.y<height)&&/^#[a-f0-9]{6}$/i.test(v.color)&&Number.isFinite(v.opacity)&&v.opacity>0&&v.opacity<=1&&Number.isFinite(v.size)&&v.size>0&&Number.isFinite(v.hardness)&&v.hardness>=0&&v.hardness<=1;
}
export function validGeneration(v){
 return !!v&&['text_edit','text_to_image'].includes(v.operation)&&typeof v.model_id==='string'&&/^[a-f0-9]{40}$/.test(v.model_revision)&&Number.isInteger(v.seed)&&v.seed>=0&&v.seed<2**32&&['low-resource','balanced'].includes(v.profile)&&[v.original_prompt,v.used_prompt,v.translated_prompt].every(p=>typeof p==='string'&&p.trim().length>0&&[...p].length<=16384);
}
export function validDocument(doc){
 if(!doc||doc.version!==1||!validBlob(doc.original)||!doc.history||!Array.isArray(doc.history.past)||!Array.isArray(doc.history.future))return false;
 return [...doc.history.past,doc.history.present,...doc.history.future].every(s=>!!s&&validBlob(s.photo)&&typeof s.label==='string'&&(s.generation===undefined||validGeneration(s.generation))&&['paint','selection'].every(k=>Array.isArray(s[k])&&s[k].length<=2048&&s[k].every(v=>validStroke(v,s.photo.width,s.photo.height))&&s[k].reduce((n,v)=>n+v.points.length,0)<=250000));
}
export function photosOf(doc){return [doc.original,...[...doc.history.past,doc.history.present,...doc.history.future].map(s=>s.photo)];}
