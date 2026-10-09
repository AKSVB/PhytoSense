# Roadmap

## Phase 1: analysis core (this release)

Calibration profiles, field-of-view masking, quality control, blob detector, manual point import, density and pattern statistics, validation statistics, command-line interface.

## Phase 2: trained models

- Annotate phone images (oriented boxes, classes `stoma_open` and `stoma_closed`) and train a YOLO oriented-box detector. See [../training/README.md](../training/README.md).
- Pavement cell segmentation (e.g. Cellpose) for stomatal index and pavement cell shape.
- Pore segmentation for aperture, only on setups whose measured resolution allows it.
- Per-species detection thresholds and expected sizes stored with the model.

## Phase 3: mobile app

- Camera screen that locks focus, exposure and zoom and refuses images that fail QC.
- Calibration wizard using the micrometer photo.
- On-device detection (model exported to TFLite or ONNX) for offline field use.
- Sample metadata entry, results table, export to CSV.
- Optional sync to a lab server for the full analysis and storage.

## Phase 4: further traits

- Trichome density.
- Leaf-level traits from an ordinary phone photo (area, shape) linked to the microscope fields of the same leaf.
- Time series of aperture on the same leaf.
- Lens distortion correction.
