<p align="center"><img src="assets/icon.png" width="96" alt="PixelMend application icon"></p>

<h1 align="center">PixelMend</h1>
<p align="center">Repair, enlarge and edit your photos. On your own computer.</p>
<p align="center"><strong>macOS Apple Silicon · Windows x64 · Local image processing · RC</strong></p>
<p align="center"><a href="https://github.com/Mahmutakin99/pixelmend-showcase/releases/tag/v1.0.0-rc.2">Download · 1.0.0-rc.2</a></p>
<p align="center"><a href="README.md">Türkçe</a> · English</p>

![PixelMend photo editor](assets/02-editor.png)

PixelMend is a desktop application for selecting and removing unwanted areas, enlarging images and editing with brush tools. Photo processing runs in a local engine; photos are not sent to external services for editing. Model installation can require a separate download.

This repository is the public product showcase and feedback space. Application source code is not published here.

## From a photo to your next step

| Task | In PixelMend |
| --- | --- |
| Object removal | Brush selection; AI processing when its model is ready, or a separate Fast / OpenCV option |
| Enlargement | Standard / Lanczos and model-dependent AI enhancement; 2×, 4× or custom dimensions |
| Editing | Drawing, eraser, selection tools, undo / redo and zoom |
| Reviewing a result | Apply or discard a preview; continue editing from an accepted result |
| Saving work | PNG export and `.pixelmend` project files |
| Workspace | Turkish interface, light / dark / system themes and model status |

AI results depend on the photo and selection. Review the preview before saving; AI enlargement may reinterpret original details.

## Inside the application

These screenshots were captured from the running macOS application, rather than design mockups. The sample is a public-domain NASA photograph of Eileen Collins. [Capture and version record](docs/SCREENSHOTS.md).

| Start screen | Enlargement |
| --- | --- |
| ![PixelMend start screen](assets/01-workspace.png) | ![Enlargement controls](assets/03-upscale.png) |

![PixelMend settings](assets/04-settings.png)

## Availability

PixelMend is in development. The installed application shown here is **1.0.0-rc.2**, captured on **2 October 2026**. Windows operation was confirmed by the developer on that date; no additional Windows device test was performed while preparing this publication. Advanced model acceptance and the final stable release remain ongoing.

| Platform | Status |
| --- | --- |
| macOS / Apple Silicon | RC.2 · [DMG](https://github.com/Mahmutakin99/pixelmend-showcase/releases/download/v1.0.0-rc.2/PixelMend-1.0.0-rc.2-macOS-arm64.dmg) / [ZIP](https://github.com/Mahmutakin99/pixelmend-showcase/releases/download/v1.0.0-rc.2/PixelMend-1.0.0-rc.2-macOS-arm64.zip) |
| Windows x64 | RC.2 · [EXE](https://github.com/Mahmutakin99/pixelmend-showcase/releases/download/v1.0.0-rc.2/PixelMend-1.0.0-rc.2-Windows-x64-Setup.exe) / [ZIP + test launcher](https://github.com/Mahmutakin99/pixelmend-showcase/releases/download/v1.0.0-rc.2/PixelMend-1.0.0-rc.2-Windows-x64.zip); not a portable build |
| Linux | Support is incomplete; no Linux package is published |

[Release notes, SHA-256 checksums and optional test kit](https://github.com/Mahmutakin99/pixelmend-showcase/releases/tag/v1.0.0-rc.2). The `.sh`, `.command` and `.cmd` launchers open installed-app diagnostics; they are not installers. macOS packages wrap the existing installed application and are not notarized. Windows may show SmartScreen warnings; verified Authenticode signing is not claimed. Do not disable system-wide security protections.

The Git source repository remains private, but JavaScript can be extracted from public Electron packages; private repository visibility cannot guarantee secrecy of distributed application code.

The screenshots document the interface only. This repository does not present a new quality comparison, speed benchmark, evidence of GPU acceleration or a claim that every model is ready.

## Feedback

Submit a [bug report](https://github.com/Mahmutakin99/pixelmend-showcase/issues/new?template=bug-report.yml) or [feature request](https://github.com/Mahmutakin99/pixelmend-showcase/issues/new?template=feature-request.yml). Include the version, operating system, expected behavior and reproduction steps. Avoid posting private photos, personal file paths or sensitive diagnostic data in public issues.

Mahmut AKIN · [GitHub](https://github.com/Mahmutakin99)

## Rights and third-party materials

Original showcase text is covered by the [rights notice](RIGHTS.md). The source project's Apache-2.0 license, rights in inherited assets and third-party photo / model licenses remain separate and unchanged. Application packages are hosted in Releases, not as source in the Git tree. Model weights are downloaded separately.
