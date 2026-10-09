# Imaging protocol

## Sample preparation

### Direct imaging (non-destructive)

1. Use a fully expanded leaf at a defined position (record node or leaf number).
2. Image the abaxial surface unless the study concerns the adaxial side. Record which side.
3. Avoid the midrib and major veins; image intercostal areas at a defined position (e.g. middle of the lamina, halfway between midrib and margin).
4. Hold the leaf flat against a dark, matte background or a slide. The clip-on lens has a very shallow depth of field, so curvature puts parts of the field out of focus.

### Epidermal impressions

1. Paint a thin layer of clear nail polish on the leaf surface (about 1 cm²) and let it dry completely.
2. Press clear tape on the dried polish, peel it off, and stick it on a labelled glass slide.
3. Image with transmitted light (see [hardware.md](hardware.md)).

Impressions allow the same field to be imaged later on a lab microscope, which the validation protocol requires. Mark a reference point on the slide (a dot with a fine marker) to find the same field.

## Camera settings

- Main camera, fixed zoom, maximum resolution.
- Lock focus and exposure on the leaf (long-press on most phones) before taking the picture.
- Turn off HDR, beauty filters and scene enhancement if the camera app allows it. They add sharpening and local contrast changes that alter stoma edges. A manual ("Pro") mode or an app that saves RAW is preferable.
- Use the self-timer or a Bluetooth shutter to avoid shake.
- Take at least three non-overlapping fields per leaf. More fields give a better density estimate, because stomatal density varies across a leaf.

## File naming and metadata

Name files so each image can be linked to the plant, leaf, side and field, for example:

```
<species>_<genotype>_<plant>_<leaf>_<side>_<field>.jpg
arabidopsis_col0_P03_L07_abx_F2.jpg
```

Keep a sample sheet with one row per image. A template is in [templates/samples.csv](templates/samples.csv).

## Before analysis

Run `phytosense analyze` and check the `quality_flags` column. Re-take images flagged `blurred` or `overexposed`. Focus thresholds depend on the species and setup; set them from a few images you have judged sharp and blurred by eye.
