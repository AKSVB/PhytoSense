# Product plan and MIAtecs comparison

Reviewed 2026-10-09 from the public pages of miatecs.com (home, STOMmini, STOM, PHENOM, Climate-aware breeding, Ploidy, Biostimulants, Beyond Stomata, Insights). Everything below about MIAtecs is what the site claims; none of it has been tested.

## What MIAtecs offers

**Business model.** MIAtecs is a service company, not a tool vendor. The STOMmini kit is "always loaned, never sold" as part of an engagement. Most projects start with a paid Phase 1 proof of concept. MIAtecs trains a separate model for each species (under 48 hours after about 3 hours of training images) and also runs on-site measurement campaigns in Europe, Africa and Latin America. There is no public pricing, no self-service tier and no downloadable software.

**STOMmini (capture).** A smartphone, an Apexel clip-on lens (the same brand as our hardware), a calibration slide and a rugged case. A guided capture app enforces the acquisition protocol, and operators are trained by MIAtecs. The site claims validation across 27 species and shows 8 crops (wheat, maize, rice, apricot, tomato, rapeseed, grapevine, coffee).

**STOM (cloud analysis).**
- Per-species models giving density per mm², guard cell length and width, aperture, orientation, clusters and spatial distribution.
- Quality check pipeline: each image gets a status. Blurred stomata are excluded, and an image with more than 30% blur is rejected for recapture.
- Reviewable detection overlays on every image.
- Project structure covering experiments, plants, genotypes, treatments, dates and metadata.
- Climate context: VPD, growing degree days and rainfall pulled automatically for each site and date.
- Export to CSV or Excel keyed to plot and genotype IDs.
- STOM Mobile app for projects, acquisition progress and field capture.
- Accepts images from other sources (Field-Dino, ProScope, leaf imprints).
- A species compatibility table covering density and size, clustering, open/closed dynamics, trichome density and clustering, venation pattern and areole size.
- Optional written report with QC, trait distributions, rankings and interpretation.

**PHENOM (lab).** A bench-top microscope for live imaging of intact leaves: up to 20 stomata tracked over a time lapse of up to 24 hours, open/closed status in real time, chemical treatments in vivo, first image within 15 minutes.

**Beyond stomata.** Trichome density, length, morphology, adaxial/abaxial distribution and clustering. Venation: vein length density, branching order, areole size, and a vein to stomata coordination ratio. Both are sold as add-ons to stomatal projects.

**Applications.** Climate-adaptive breeding (water-conserving vs responsive stomatal strategies), ploidy pre-screening ahead of flow cytometry (page marked "coming soon"), and biostimulant mode-of-action evidence for EU Regulation 2019/1009 dossiers (also "coming soon").

**Claims to treat with caution.** The home page counters render as 0 without JavaScript, so the actual figures for species, stomata counted and accuracy target could not be read. The site mentions an "accuracy target on protocol-compliant images" rather than a measured accuracy. Listed users include AAFC, CIRAD, INRAE, IJPB, Eurofins and Cérience. No validation paper or method description was found on the site.

## Where PhytoSense stands (v0.1)

| Capability | MIAtecs | PhytoSense v0.1 |
|---|---|---|
| Clip-on phone capture | Yes, loaned kit with guided app | Protocol documented, no app |
| Calibration | Calibration slide | Micrometer FFT, two-point, named profiles |
| Image QC | Blur rule, per-image status | Focus and exposure metrics, field-of-view mask |
| Detection | Trained model per species | Blob detector; YOLO wrapper, no trained model yet |
| Density, size | Yes | Density yes; size from blob scale only |
| Aperture, open/closed | Yes | No |
| Orientation | Yes | Yes |
| Spatial pattern | Clusters, "spatial distribution" | NND, Clark-Evans with Donnelly correction, Ripley's L, contact clusters |
| Stomatal index, pavement cells | Not listed | No (planned) |
| gs,max | Not listed | No (planned) |
| Trichomes, venation | Yes, add-on | No |
| Manual / ImageJ input | Not listed | ImageJ point CSV import |
| Validation statistics | Not published | Point matching, Bland-Altman, Lin's CCC |
| Project and metadata model | Yes | No |
| Climate data | VPD, GDD, rainfall | No |
| Export | CSV, Excel | CSV |
| Mobile app | STOM Mobile | No |
| Time lapse / live imaging | PHENOM | No |
| Open method, user owns pipeline | No | Yes |
| Price | Engagement only | Free core |

## Gap list

Ordered by priority. "Catch up" closes a gap with MIAtecs; "Differentiate" is something they do not offer.

### Priority 1: needed before anyone can use it on real leaves

1. **Trained detector on real images** (catch up). Annotate APEXEL images from several BIAM species and train the YOLO oriented-box model. MIAtecs' strongest point is that their detection works per species; ours has only been tested on synthetic images.
2. **Guard cell length, width and aperture** (catch up). Take size from the oriented box, and aperture from pore segmentation only where the measured resolution allows it. Report "not resolvable" rather than a number when it does not.
3. **Per-image QC status with a reject rule** (catch up). Turn the existing focus and exposure metrics into pass/warn/reject, plus a per-detection blur flag that excludes stomata, like their 30% rule.
4. **Overlay images for review** (catch up). Save an annotated image for every analysed image, with detections and excluded regions.
5. **Batch run with a metadata sheet** (catch up). Read a CSV of image to sample, genotype, treatment, plot and date, and write one trait table keyed to those IDs. Add Excel export.

### Priority 2: features MIAtecs does not offer

6. **Published validation** (differentiate). Run the multi-species, multi-microscope validation in `validation-protocol.md` and publish it. MIAtecs shows no independent accuracy figures, so this is the clearest advantage available to us.
7. **Self-service, open pipeline** (differentiate). Anyone can run it on their own images without an engagement or a per-species contract. A free academic tier and documented methods suit researchers who need to report how numbers were produced.
8. **Physiological traits** (differentiate). Stomatal index (needs pavement cell segmentation), anatomical gs,max, and the spatial statistics we already have (Clark-Evans, Ripley's L), reported with confidence intervals.
9. **Self-calibrating leaf clamp** (differentiate). A clamp with a scale inside the field of view removes the separate calibration step and keeps the working distance fixed. Their kit uses a separate slide.
10. **Tap-to-correct in the app** (differentiate). Users fix detections on the phone, and the corrections become training data. MIAtecs does all annotation in-house.
11. **ImageJ/Fiji integration** (differentiate). We already import ImageJ point CSVs. A Fiji macro or plugin that sends images to PhytoSense and loads the detections back as ROIs would let labs keep their existing ImageJ workflow.

### Priority 3: extend coverage

12. **Mobile app** (catch up). Guided capture with focus and exposure locked, live QC, on-device detection, QR sample tracking. See the roadmap, Phase 3.
13. **Trichomes** (catch up). Density, length and clustering, using the same detector framework with a new class.
14. **Venation and areoles** (catch up). Vein length density and areole size. This probably needs lower magnification or cleared leaves, so first check what the clip-on lens can resolve.
15. **Climate context** (catch up). Pull VPD, GDD and rainfall for the site and date from a public weather API (for example Open-Meteo) and join them to the trait table.
16. **Ploidy pre-screen** (catch up, and they have not launched it). Guard cell length vs ploidy calibration curves per species, checked against flow cytometry. BIAM's species collection makes this a realistic early target.
17. **Time series on one leaf** (partial catch up with PHENOM). Track the same stomata across a phone time lapse in the clamp. This will not match a bench microscope's resolution, but it may be enough for open/closed status.
18. **BrAPI export and audit trail** (differentiate). Useful for breeding programs that already run a BrAPI database.

## Out of scope for now

- A bench-top live imaging microscope like PHENOM. It needs different hardware; existing lab microscopes plus the import path cover research use.
- On-site measurement campaigns as a service. Possible later as a business line, but not a software task.
- Focus stacking or multi-focal capture. Do not add it without a freedom-to-operate check against US 11988509 B2 (Inari).

## Open questions

- IP ownership and licence: check with CEA's technology transfer office before publishing code or a paper.
- The clip-on lens resolution limit for aperture and venation: measure it on a micrometer and on nail polish impressions before promising those traits.
- Whether MIAtecs' Apexel-based kit and our hardware are close enough that their claims set user expectations for us.
