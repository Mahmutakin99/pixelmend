# AI upscale implementation

Approved scope: reproducible RealESRGAN_x4plus ONNX export, immutable Hugging Face model delivery, authenticated model lifecycle, tiled local inference, 200 MP policy, full Performance settings, and measured M4 acceptance. Public publication needs the user's repository access; never fabricate artifact hashes or a published revision.

## Shared contracts

- Algorithm `realesrgan_x4plus`; model id `realesrgan-x4plus`. Keep `lama` and `lanczos` compatible.
- `GET /models` -> `{models: ModelView[]}`; `GET /models/events` -> SSE event `models`, data is the same snapshot. Mutations: `POST /models/{id}/install|cancel|retry|probe`, `DELETE /models/{id}`; return snapshot or model view, never paths.
- ModelView: `id, name, state, published, size_bytes, downloaded_bytes, revision, sha256, license_id, license_url, error: {code,message}|null, probe: {status, selected_provider, providers, measured_at}|null, in_use`. Unpublished model state is `unavailable`, metadata unknown fields are null, installation is disabled. Probe statuses `unmeasured|running|passed|failed`.
- Inference integration: `ModelManager.lease(model_id)` context yields verified model Path and prevents mutation while queued/running; `manager.selected_provider(model_id)` yields provider string; `manager.list_models()` returns safe snapshot; `await manager.close()` cancels/drains work. Model API uses injected auth dependency.
- Narrow desktop bridge: `models()`, `modelAction(id, 'install'|'cancel'|'retry'|'probe'|'delete')`, `onModels(callback)`; `capabilities()` returns policy plus host observations. `startJob` adds `upscaleMethod: 'ai'|'lanczos'`.
- Policy default output/AI natural intermediate limit 200,000,000 pixels, results 1 GiB; local operator configuration may change policy, browser cannot. Expose policy through capabilities. Image import/reopen/continue must support allowed generated outputs consistently.

## Work units

1. Model manager/API: cancellable bounded transport, SHA/size, file locks, lifecycle/probe state, safe deletion, missing/unpublished behavior, tests.
2. Desktop: narrow authenticated IPC/SSE proxy; AI/default choice; Performance settings; reusable contracts and behavior tests.
3. Export/benchmark: isolated development-only dependencies, pinned provenance, parity gate, fixture manifest and runner. No public upload or invented baseline.
4. Integration: policy, tiled adapter and probes, queue progress/cancel/resources, app lifecycle, meaningful regression tests, real inference and package checks.

## Acceptance

Tests cover auth, corrupt/partial files, cancellation/races, disk and memory admission, provider correctness, alpha, arbitrary dimensions, seam blending, cleanup and existing editor workflows. Real model and licensed fixtures must produce evidence before claiming AI release or M4 stress acceptance. Record unfinished external requirements explicitly.

## Progress

- Started from clean commit 899b8a3 on branch feat/ai-upscale.
- Publishing target is chosen but credentials/ownership have not been established; implement and verify all local work first.
- Local implementation is complete through model/UI/engine integration. Verification on 2026-09-15: engine non-sidecar suite `107 passed, 1 skipped, 1 deselected`; desktop Vitest `16 passed`; desktop production build passed. The public artifact and M4 benchmark acceptance remain external gates, not completion claims.
