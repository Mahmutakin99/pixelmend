# Mac local AI delivery — 2026-09-20

Intent: implement the user-provided Mac-only final delivery plan. Public model publication, other OS releases and generative fill are out of scope.

Tasks: (1) explicit LaMa/OpenCV routing and model leases/metadata; (2) pinned local RealESRGAN acquisition and CPU probes; (3) editor/settings audit; (4) real photographic model acceptance and packaging; (5) inventory, reversible cleanup, installation and local commits.

Pre-flight: renderer removal method must survive IPC mapping and use the same verified path as the manager probe. Local manifest must preserve hash/size verification while separating publication from availability. Runtime discovery must probe installed models on restart.

Ruling: work on a dedicated local branch in the existing clean checkout, preserving its installed dependencies; sandbox initially denied Git mutation, authorized escalation created feat/mac-local-ai. No shared-state concurrent implementation.

Baseline: desktop 26 tests passed. Engine 116 passed, 1 skipped; loopback subprocess failed under sandbox (empty startup output), rerun with loopback permission required. Existing real test opt-in is not final acceptance.

Tasks 1–3: implementation complete. RealESRGAN export parity passed and fixed local manifest added. CPU discovery/probe and local copy survive source removal. Explicit LaMa routing uses leased model path; job results/events report algorithm/revision/provider. Real default temporary disk path fixed after packaged AI returned HTTP 500. Model admission errors preserve public codes.
Task 4: engine 126 passed, 0 skipped with real models; desktop 26 + CI tools 3 passed; 12-photo 2x/4x benchmark and four LaMa comparisons visually reviewed. Packaged editor and fresh-store/restart/AI/cancel passed. Native quit guard added after audit found unsaved loss; final close-preview regression pending.
Review: independent code reviewer found generic model errors (fixed) and preview-save-close loss (fix in progress).
Task 5: hidden tree inventory complete (40296 files). Applications instance was open; user asked to continue, subsequent process check confirms it closed. Install authorized; waiting only for final package gate.

All tasks complete for Mac delivery. Native close and pending-preview guards verified in packaged E2E. /Applications installation and post-install editor/fresh-store/models/cancel/project/smoke tests passed. Duplicate export/build/package artifacts moved to Trash; real persisted models continued working. 58.99 MP Lanczos output verified; large AI throughput remains explicitly unclaimed. Branch retained locally as authorized by user plan; no push/merge/publication.
