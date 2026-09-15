export type ModelAction = 'install'|'cancel'|'retry'|'probe'|'delete';
export type ModelView = {
  id:string;name:string;state:string;published:boolean;size_bytes:number|null;
  downloaded_bytes:number;revision:string|null;sha256:string|null;license_id:string|null;license_url:string|null;
  error:{code:string;message:string}|null;
  probe:{status:'unmeasured'|'running'|'passed'|'failed';selected_provider:string|null;providers:string[];measured_at:string|null}|null;
  in_use:boolean;
};
export type Capabilities = {
  host_ram_total_bytes:number|null;host_ram_available_bytes:number|null;cpu_count:number|null;
  execution_providers:string[];
  accelerator:{identity:string|null;memory_kind:string;device_budget_bytes:number|null;device_headroom_bytes:number|null};
  policy:{max_output_pixels:number;max_result_bytes?:number;max_ai_intermediate_pixels?:number};
};
export type ModelSnapshot = {models:ModelView[]};
export type UpscaleMethod = 'ai'|'lanczos';
// Availability is determined by an actual model probe, never by host RAM or provider presence.
export const aiReady = (model:ModelView|undefined) => model?.state === 'ready' && model.probe?.status === 'passed';
export function allowedActions(model:ModelView):ModelAction[] {
  if (!model.published || model.in_use) return [];
  if (['downloading','verifying','installing'].includes(model.state)) return ['cancel'];
  if (model.state === 'probing' || model.probe?.status === 'running') return [];
  if (model.state === 'ready') return ['probe','delete'];
  if (['failed','error','cancelled','corrupt'].includes(model.state)) return ['retry','delete'];
  if (model.state === 'installed') return ['probe','delete'];
  return ['install'];
}
export function formatBytes(value:number|null|undefined) {
  return value == null ? 'Ölçülmedi' : `${(value/1024/1024).toFixed(1)} MiB`;
}
