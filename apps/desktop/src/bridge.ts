import type {EditorDocument, Stroke} from './document';
import type {Capabilities, ModelAction, ModelSnapshot, ModelView, UpscaleMethod} from './models';
import type {PixelMendPreferences} from './preferences';
export type AssetView = {asset_id:string;preview:string;width:number;height:number};
export type JobSnapshot = {job_id:string;status:string;result_ids:string[];result_details?:{algorithm:string;model_revision:string|null;provider:string|null;fallback_reason?:string|null}[];error?:{code:string;message:string};progress?:{completed:number;total:number;phase:string}};
export type Preferences = Pick<PixelMendPreferences, 'language' | 'theme'> & Partial<PixelMendPreferences>;
export interface DesktopBridge {
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
