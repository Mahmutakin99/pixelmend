export type ModelAction = 'install-local'|'install'|'cancel'|'retry'|'probe'|'delete';
export type ModelView = {
  source?:'local'|'published';verified_manifest?:boolean;id:string;name:string;state:string;published:boolean;size_bytes:number|null;
  downloaded_bytes:number;revision:string|null;sha256:string|null;license_id:string|null;license_url:string|null;
  error:{code:string;message:string}|null;
  probe:{status:'unmeasured'|'running'|'passed'|'failed';selected_provider:string|null;providers:string[];measured_at:string|null}|null;
  in_use:boolean|number;
  stored_bytes:number;active_revision:string|null;last_used_at:string|null;stale_revisions:string[];
  operation?:'remove'|'upscale'|'generative';tier?:'fast'|'balanced'|'advanced';description?:string;
  runtime?:'mlx'|'torch-cpu';operations?:string[];loaded?:boolean;package_revision?:string;source_revision?:string;
  accepted_profiles?:Array<{profile:'low-resource'|'balanced'}>;
  minimum_memory_bytes?:number|null;recommended_memory_bytes?:number|null;
};
export type Capabilities = {
  generative?:{platform_supported:boolean;runtime_installed:boolean;minimum_ram_bytes:number;
    minimum_macos_major:number;runtime:'mlx';translation_runtime:'torch-cpu';accepted_profiles:string[]};
  host_ram_total_bytes:number|null;host_ram_available_bytes:number|null;cpu_count:number|null;
  execution_providers:string[];
  accelerator:{identity:string|null;memory_kind:string;device_budget_bytes:number|null;device_headroom_bytes:number|null};
  policy:{max_output_pixels:number;max_result_bytes?:number;max_ai_intermediate_pixels?:number};
};
export type ModelSnapshot = {models:ModelView[]};
export type UpscaleMethod = 'ai'|'lanczos';
export const selectableModels = (models: ModelView[]) => models.filter(model => model.tier !== 'advanced');
// Availability is determined by an actual model probe, never by host RAM or provider presence.
export const aiReady = (model:ModelView|undefined) => model?.state === 'ready' && model.probe?.status === 'passed';
export const isModelPreparing = (model:ModelView|undefined) => !!model && ['waiting','verifying','probing'].includes(model.state);
export const modelAvailability = (model:ModelView|undefined) => isModelPreparing(model) ? 'hazırlanıyor' : aiReady(model) ? 'hazır' : 'kurulum/sınama gerekli';
export function allowedActions(model:ModelView):ModelAction[] {
  if (!(model.verified_manifest ?? model.published) || model.in_use) return [];
  if (['waiting','cancelling','deleting'].includes(model.state)) return [];
  if (['downloading','verifying','installing'].includes(model.state)) return ['cancel'];
  if (model.state === 'probing' || model.probe?.status === 'running') return [];
  if (model.state === 'ready') return ['probe','delete'];
  if (['failed','error','cancelled','corrupt'].includes(model.state)) return [model.source === 'local' ? 'install-local' : 'retry','delete'];
  if (model.state === 'installed') return ['probe','delete'];
  return [model.source === 'local' ? 'install-local' : 'install'];
}
export function formatBytes(value:number|null|undefined) {
  return value == null ? 'Ölçülmedi' : `${(value/1024/1024).toFixed(1)} MiB`;
}
