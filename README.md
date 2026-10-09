# PhytoSense

Stomatal phenotyping from images taken with a smartphone and a low-cost clip-on microscope lens. PhytoSense calibrates each phone and lens combination, finds the usable field of view, detects stomata, and reports density, size, orientation and spatial pattern. The same statistics can be run on manual counts from ImageJ/Fiji, and a validation module compares the phone results with reference microscopes.

Status: research prototype (v0.1). The geometry, calibration and statistics are tested on synthetic images with known ground truth. Detection on real clip-on images has not been validated yet; that is the purpose of the protocol in [docs/validation-protocol.md](docs/validation-protocol.md).

## What it measures

| Trait | Source | Notes |
|---|---|---|
| Stomatal density (stomata/mm²) | count / calibrated field area | field is the in-focus, illuminated region only |
| Stomatal index | stomata / (stomata + pavement cells) | needs a pavement cell count (manual or segmentation) |
| Complex length and width (µm) | detector | approximate with the blob detector; use a trained model for size work |
| Nearest-neighbour distance (µm) | positions | |
| Clark-Evans R with Donnelly edge correction | positions | R > 1 regular, R < 1 clustered |
| Ripley's L(r) - r with CSR envelope | positions | pattern across distance scales |
| Clustering (stomata in contact) | positions | one-cell spacing rule violations |
| Orientation and alignment | detector | relevant for monocots and elongated leaves |
| Open fraction | trained model with open/closed classes | |
| Image quality flags | QC | blur, over/under-exposure, small field |

Definitions and formulas are in [docs/traits.md](docs/traits.md).

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"          # core + tests
pip install -e ".[yolo]"         # optional: trained YOLO detector
pytest
```

Python 3.10 or newer. Core dependencies are numpy, scipy, scikit-image and Pillow.

## Quick start

Run the pipeline on a synthetic image to check the installation:

```bash
phytosense demo --out demo
```

Calibrate a phone and lens combination from a photo of a stage micrometer (10 µm divisions):

```bash
phytosense calibrate-micrometer micrometer.jpg --spacing-um 10 \
    --name pixel7-apexel200-1x --phone "Pixel 7" --lens "APEXEL 200X" --zoom 1x
```

This writes the profile to `calibrations.json`. If automatic detection of the ruling fails, give two points a known distance apart instead:

```bash
phytosense calibrate-points --p1 412,388 --p2 1630,402 --distance-um 500 --name pixel7-apexel200-1x
```

Analyse leaf images with the blob detector:

```bash
phytosense analyze images/*.jpg --profile pixel7-apexel200-1x \
    --stoma-length-um 25 --polarity dark --out results
```

Or use manual counts made in Fiji (multi-point tool, Analyze > Measure, save as `<image-name>.csv`):

```bash
phytosense analyze images/*.jpg --profile pixel7-apexel200-1x \
    --points-dir counts/ --contact-dist-um 15 --out results_manual
```

Each run writes `summary.csv` (one row per image), `results.json` (full detail), and per-image overlays and stomata tables.

Compare against reference data:

```bash
# Object level: same field annotated twice
phytosense match results/leaf1_stomata.csv reference/leaf1.csv --tol-px 10

# Sample level: one row per leaf with phone and microscope values
phytosense agree paired.csv --test-col density_phone --ref-col density_lm --group-col species
```

## Hardware

The reference setup is a 200× clip-on lens with an LED ring (for example the APEXEL 200X), a phone stand, and a stage micrometer for calibration. Total cost is roughly that of the lens plus a few euros for the micrometer and nail polish. See [docs/hardware.md](docs/hardware.md) and [docs/imaging-protocol.md](docs/imaging-protocol.md).

The "200×" figure is a marketing number. What matters is the calibrated µm per pixel and the optical resolution, both of which PhytoSense records and the validation protocol measures.

## Repository layout

```
src/phytosense/
  calibration.py   µm/px from a stage micrometer (FFT) or two points; named profiles
  quality.py       field-of-view mask for vignetted clip-on images; focus and exposure QC
  preprocess.py    flat-field correction, CLAHE
  detect.py        blob detector, YOLO wrapper, ImageJ point import
  spatial.py       NND, Clark-Evans, Ripley's L, contact clusters, orientation
  analysis.py      per-image traits
  validation.py    point matching (P/R/F1), Bland-Altman, Lin's CCC
  synthetic.py     test images with known ground truth
  report.py        overlays, CSV and JSON output
  cli.py           command-line interface
docs/              hardware, imaging, calibration, validation, traits, roadmap
training/          annotation and YOLO training notes
tests/             pytest suite
```

## Related work

- StomataCounter: deep-learning stomata counting on microscope images ([Fetter et al., bioRxiv preprint](https://www.biorxiv.org/content/10.1101/677450v1.full.pdf+html)).
- StomaAI: pore and density measurement with deep computer vision, University of Adelaide ([announcement](https://www.adelaide.edu.au/aiml/news/list/2023/04/14/ai-fast-track-for-development-of-water-saving-plants)).
- A smartphone method for stomatal aperture using MSER ([Flinders University](https://researchnow.flinders.edu.au/en/publications/a-fast-method-to-measure-stomatal-aperture-by-mser-on-smart-mobil/)).

## Licence

Not yet chosen. Check institutional requirements before publishing the code.
