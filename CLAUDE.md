# PhytoSense: context for Claude sessions

## Project

Low-cost stomatal phenotyping: smartphone + clip-on 200x lens (APEXEL 200X) for imaging, a Python package `phytosense` for calibration, QC, detection and trait statistics. The owner works at BIAM (CEA Cadarache) and has access to many species (Arabidopsis, Citrus, tomato, hemp and others) and to light, digital, confocal and other microscopes for validation.

## Current state (v0.1)

- `src/phytosense/`: calibration (stage micrometer FFT, two-point, named profiles), field-of-view mask for vignetted clip-on images, QC (focus, exposure), blob detector, YOLO wrapper, ImageJ point CSV import, density, size, NND, Clark-Evans (Donnelly correction), Ripley's L, contact clusters, orientation, validation statistics (point matching, Bland-Altman, Lin's CCC), CLI `phytosense`.
- `pytest`: 15 tests on synthetic images, all passing. Nothing has been run on real clip-on photos yet.
- `docs/`: hardware, imaging protocol, calibration, traits, validation protocol, roadmap. `training/`: annotation and YOLO notes.

## Decisions so far

- Python core first; mobile app later (on-device model via TFLite/ONNX).
- Validation uses nail-polish impressions so the same field can be imaged on the phone and on reference microscopes.
- No licence chosen yet. IP ownership must be checked with CEA's technology transfer office before publishing or commercialising (work done with CEA resources).
- Patent US 11988509 B2 (Inari Agriculture) claims multi-focal-distance image capture + composite image + trainable detector for stomata count/density. Do not add focus stacking without a freedom-to-operate check.

## Competitor: MIAtecs (miatecs.com)

Marseille, founded early 2024 by Fabien Miart. Products: STOMmini (portable smartphone microscope, 75 g, 200X, USB 3.0; claims 200 leaves/hour), PHENOM (digital microscope), STOM (AI analysis platform). Services: stomata, trichomes, leaf veins, roots, root hairs. No public pricing or independent validation found. The site could not be opened from the cloud session; a local session with the built-in browser should review it in full (product pages, AI analysis page, services) and record a feature gap list in `docs/product-plan.md`.

## Product ideas agreed as direction

- Leaf clamp (3D printed) holding the leaf flat at fixed distance, with a calibration scale built into the field of view so every image self-calibrates; transmitted and oblique LED light.
- Mobile app: offline detection, live QC, tap-to-correct (feeds training), QR/barcode sample tracking, guided protocols.
- Traits: add anatomical maximum stomatal conductance (gs,max), open/closed and aperture where resolution allows, trichomes, pavement cells, veins, leaf area.
- Import from lab microscopes, cloud dashboard, CSV/R/BrAPI export, audit trail.
- Business: kit sales, software tiers (free academic tier), analysis service, education kits. Publish a multi-species, multi-microscope validation paper.

## Next steps

1. Done: MIAtecs review and gap list in `docs/product-plan.md` (2026-10-09).
2. First real images: 8 Citrus photos (2026-10-09) in Training_data/ (git-ignored). Added PaleSpotDetector (`--detector pale --stoma-length-px N`), which works on them; zoom varied between photos, so stoma size was set per photo. Still needed: micrometer photo at a fixed zoom, a blur reject rule (photo 141653 is mostly out of focus), start YOLO annotation using pale detections as pre-annotations.
3. Design the leaf clamp with built-in calibration scale.

## Conventions

- Writing style: plain, direct prose; no em dashes; no promotional wording.
- Run `pytest` before committing.
