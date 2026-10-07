import type {EditorDocument, Stroke} from './document';
import type {Capabilities, ModelAction, ModelSnapshot, ModelView, UpscaleMethod} from './models';
import type {PixelMendPreferences} from './preferences';
export type AssetView = {asset_id:string;preview:string;width:number;height:number};
export type GenerationInfo = {operation:'text_edit'|'text_to_image';model_id:string;model_revision:string;seed:number;profile:'low-resource'|'balanced';original_prompt:string;used_prompt:string;translated_prompt:string};
export type JobSnapshot = {job_id:string;status:string;seed?:number;result_ids:string[];result_details?:Array<{algorithm:string;model_revision:string|null;provider:string|null;fallback_reason?:string|null}&Partial<GenerationInfo>>;error?:{code:string;message:string};progress?:{completed:number;total:number;phase:string}};
type GenerativeCommon = {prompt:string;promptLanguage:'tr'|'en';englishOverride?:string;profile:'low-resource'|'balanced';seed?:number};
export type GenerativeRequest = GenerativeCommon & ({operation:'text_edit';assetId:string;selectionStrokes:Stroke[];paintStrokes:Stroke[]}|{operation:'text_to_image';aspect:'square'|'landscape'|'portrait'});
export type GenerativePreflight = {ready:boolean;reason?:{code:string;message:string};seed:number;width:number;height:number;profile:string;available_memory_bytes?:number;required_available_memory_bytes?:number;execution_mode?:'fast'|'adaptive';memory_pressure?:'normal'|'warning'|'critical'|'unknown';waiting_for_memory?:boolean};
export type Preferences = Pick<PixelMendPreferences, 'language' | 'theme'> & Partial<PixelMendPreferences>;
export interface DesktopBridge {
  generativeMemory(request:GenerativeRequest):Promise<GenerativePreflight>;
  generativePreflight(request:GenerativeRequest):Promise<GenerativePreflight>;
  startGenerativeJob(request:GenerativeRequest):Promise<JobSnapshot>;
  disposeAsset(id:string):Promise<void>;
  disposeGenerativeJob(id:string):Promise<void>;
  confirmClose():Promise<void>;
  models():Promise<ModelSnapshot>;
  modelAction(id:string,action:ModelAction):Promise<ModelSnapshot|ModelView>;
  onModels(callback:(snapshot:ModelSnapshot)=>void):()=>void;
  capabilities():Promise<Capabilities>;
  startJob(payload:{assetId:string;operation:'remove'|'upscale';modelId?:string;intent?:'resize'|'preserve_size';removeMethod?:'lama'|'opencv';selectionStrokes?:Stroke[];targetWidth?:number;targetHeight?:number;upscaleMethod?:UpscaleMethod}):Promise<JobSnapshot>;
  job(id:string):Promise<JobSnapshot>;cancel(id:string):Promise<unknown>;
  openImage():Promise<AssetView|null>;continueResult(job:string,result:string):Promise<AssetView>;
  settings():Promise<Preferences>;setSettings(value:Preferences):Promise<void>;
  onAction(callback:(action:string)=>void):()=>void;
  exportSource(id:string):Promise<string>;saveImage(payload:{assetId:string}):Promise<boolean>;
  renderAsset(payload:{assetId:string;paintStrokes:Stroke[]}):Promise<AssetView>;
  saveProject(document:EditorDocument|undefined,saveAs:boolean):Promise<boolean>;openProject():Promise<EditorDocument|null>;
}
declare global {interface Window {pixelmend:DesktopBridge}}
