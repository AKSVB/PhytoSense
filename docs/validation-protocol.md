# Validation protocol

The question is how well traits measured with a phone and clip-on lens agree with the same traits measured on laboratory microscopes, for each species and preparation method. This protocol is written for a lab with several species and several microscope types available.

## 1. Setup characterisation

For each phone, lens and zoom combination:

| Test | Procedure | Output |
|---|---|---|
| Scale | micrometer photo, `calibrate-micrometer` | µm/px |
| Re-mount repeatability | remove and re-mount the clip 10 times, calibrate each time | CV of µm/px |
| Phone-to-phone | same lens on 3 or more phone models | µm/px and field area per phone |
| Distortion | micrometer at centre vs. edge of field | % scale difference |
| Resolution | finest resolved micrometer spacing or a resolution target | µm |
| Field area | `field_area_mm2` from analysis output | mm² |

## 2. Paired imaging

Use epidermal impressions so the same field can be imaged on every instrument.

1. Make an impression and mark a reference dot on the slide next to the region to image.
2. Image the field with the phone setup (transmitted light).
3. Image the same field on each reference instrument:
   - Brightfield or DIC light microscope, 10× and 20× objectives: reference for counts and complex size.
   - Digital microscope: a second low-cost reference.
   - Confocal microscope on stained tissue (e.g. propidium iodide for cell outlines) where pavement cells are needed for stomatal index. This uses the leaf itself, not the impression, so pair it at leaf level rather than field level.
4. Separately, image leaves directly (no impression) with the phone in reflected light, to measure what is lost without the impression step.

## 3. Species and sampling

Start with species that differ in stomatal size, density and epidermis type, for example Arabidopsis thaliana, tomato, Citrus and hemp, then extend. For each species:

- both leaf sides where both carry stomata,
- at least 3 leaf positions or ages,
- enough leaves to span the natural range of density (a few dozen per species is a reasonable start; adjust after the first agreement analysis).

Include treatments or genotypes with known differences in density or patterning (e.g. stomatal development mutants in Arabidopsis) so the method is tested on the effect sizes it is meant to detect.

## 4. Reference annotation

Count stomata on the reference images in Fiji (multi-point tool) or with a reference pipeline. Have a subset counted by two people to measure inter-operator agreement; the phone method does not need to agree with the reference better than two operators agree with each other.

## 5. Analysis

Object level, on fields imaged on both systems after registering the images (or annotating both by hand):

```bash
phytosense match phone_points.csv reference_points.csv --tol-px 10
```

Report precision, recall and F1 per species and preparation.

Sample level, one row per field or leaf (template: [templates/paired_validation.csv](templates/paired_validation.csv)):

```bash
phytosense agree paired.csv --test-col density_phone --ref-col density_ref --group-col species
```

Report the bias, Bland-Altman 95 % limits of agreement, Lin's concordance correlation coefficient, and regression slope and intercept. Plot Bland-Altman diagrams per species.

Decide acceptance criteria before collecting data, for example: density bias within 5 % and limits of agreement within 15 % of the mean for a given species and preparation. Report the species and preparations that pass and fail separately rather than pooling them.

## 6. Training data

Every reference-annotated phone image is also training data for the detector (see [../training/README.md](../training/README.md)). Keep a held-out set of plants that is never used for training, so reported agreement is not inflated.
