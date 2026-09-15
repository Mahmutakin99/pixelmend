import type {EditorDocument, Stroke} from './document';
import type {Capabilities, ModelAction, ModelSnapshot, ModelView, UpscaleMethod} from './models';
export type AssetView = {asset_id:string;preview:string;width:number;height:number};
export type JobSnapshot = {job_id:string;status:string;result_ids:string[];error?:{code:string;message:string};progress?:{completed:number;total:number;phase:string}};
export type Preferences = {language:string;theme:string};
export interface DesktopBridge {
  models():Promise<ModelSnapshot>;
  modelAction(id:string,action:ModelAction):Promise<ModelSnapshot|ModelView>;
  onModels(callback:(snapshot:ModelSnapshot)=>void):()=>void;
  capabilities():Promise<Capabilities>;
  startJob(payload:{assetId:string;operation:'remove'|'upscale';selectionStrokes?:Stroke[];targetWidth?:number;targetHeight?:number;upscaleMethod?:UpscaleMethod}):Promise<JobSnapshot>;
  job(id:string):Promise<JobSnapshot>;cancel(id:string):Promise<unknown>;
  openImage():Promise<AssetView|null>;continueResult(job:string,result:string):Promise<AssetView>;
  settings():Promise<Preferences>;setSettings(value:Preferences):Promise<void>;
  onAction(callback:(action:string)=>void):()=>void;
  exportSource(id:string):Promise<string>;saveImage(payload:{assetId:string}):Promise<boolean>;
  renderAsset(payload:{assetId:string;paintStrokes:Stroke[]}):Promise<AssetView>;
  saveProject(document:EditorDocument|undefined,saveAs:boolean):Promise<boolean>;openProject():Promise<EditorDocument|null>;
}
declare global {interface Window {pixelmend:DesktopBridge}}
