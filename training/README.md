# Training a stoma detector

The blob detector in `phytosense.detect` needs no training but is sensitive to contrast and background texture. For routine use, train a detector on annotated images from the actual phone setup.

## Annotation

- Tool: CVAT or Label Studio; both can export YOLO formats.
- Draw an oriented box around each stomatal complex (guard cell pair). Oriented boxes give length, width and angle directly.
- Classes: `stoma_open`, `stoma_closed`. If open/closed cannot be judged at the setup's resolution, use a single class `stoma`.
- Annotate every stoma in the image, including partial ones at the field edge; PhytoSense excludes them later by centre position.

## Data split

Split by plant (or at least by leaf), never by image. Fields from the same leaf are correlated, and splitting them across training and test sets inflates the test score. Keep separate test sets per species, preparation (direct or impression) and phone model.

## Training

With Ultralytics installed (`pip install -e ".[yolo]"`) and a dataset YAML in YOLO OBB format:

```bash
yolo obb train data=stomata.yaml model=yolo11n-obb.pt imgsz=1280 epochs=150
```

Use a large `imgsz` because stomata are small relative to the frame. Then analyse with:

```bash
phytosense analyze images/*.jpg --profile pixel7-apexel200-1x --yolo runs/obb/train/weights/best.pt
```

Evaluate on the held-out plants with `phytosense match` and `phytosense agree`, as described in [../docs/validation-protocol.md](../docs/validation-protocol.md).
