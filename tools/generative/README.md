# Mac alpha packaging

The generative runtime is a separate, locked Python project. Build it using
`engine/generative-runtime/README.md` before packaging. Models are installed
separately; neither source weights nor evaluation reports enter the application.

From `apps/desktop`, `corepack pnpm package:mac:generative` prepares
`1.1.0-alpha.1` in an isolated local output directory. It requires an installed
Developer ID Application identity in `CSC_NAME` and an existing notarytool
Keychain profile in `PIXELMEND_NOTARY_PROFILE`. Keep credentials in Keychain;
the command does not accept passwords or API keys on the command line.
The signed app is notarized and stapled before the final ZIP and DMG are made;
the DMG is then notarized and stapled separately. Invalid notarization responses
stop packaging. Checksums cover the final artifacts, and the build manifest
hashes the runtime executable inside the packaged app after signing.

For local development review, run
`node ../../tools/generative/package-mac.mjs --unsigned`. This produces local
artifacts and checksums. It does not establish Developer ID, notarization,
Gatekeeper, human quality, or profile acceptance.

Packaging never publishes, uploads model assets, replaces installed apps, or
changes existing RC artifacts. A successful build is not hardware acceptance.
Use the explicit native Electron flow `corepack pnpm test:e2e:generative` after
models and a profile have passed acceptance. It uses real local models and
requires source fixture photos; native file dialogs alone are automated.

Klein's pinned VAE opts out of implicit tiling because separate GroupNorm
statistics can offset tile colours. The runtime releases the text encoder and
transformer through MFLUX's one-seed memory callbacks, retains a 1 GiB MLX cache
limit, and uses the original VAE. No system wired-memory limits are changed.
