# Calibration

A clip-on lens has no fixed magnification. The µm-per-pixel scale depends on the phone's camera module, the zoom setting, and the exact position of the lens on the camera window. PhytoSense therefore stores named calibration profiles, one per phone, lens and zoom combination.

## Stage micrometer (recommended)

1. Clip the lens on as it will be used for leaves, with the same zoom setting.
2. Photograph a stage micrometer with 10 µm divisions under the same illumination mode. Keep the ruling in focus across as much of the field as possible.
3. Run:

   ```bash
   phytosense calibrate-micrometer micrometer.jpg --spacing-um 10 \
       --name pixel7-apexel200-1x --phone "Pixel 7" --lens "APEXEL 200X" --zoom 1x
   ```

The ruling's period is found from the strongest peak of the 2-D Fourier spectrum, so the micrometer can be at any angle. If the photo contains printed numbers, the slide edge or long index marks that dominate the spectrum, crop to the fine ruling with `--crop x0,y0,x1,y1`.

Check the result: the field of view in µm (image width × µm/px) should be plausible for the lens, and a second photo of the micrometer at another position in the field should give the same value within about 1 %.

## Two points

If the automatic method fails, open the micrometer photo in Fiji, read the pixel coordinates of two marks far apart (e.g. 0 and 50 divisions = 500 µm), and run:

```bash
phytosense calibrate-points --p1 412,388 --p2 1630,402 --distance-um 500 --name pixel7-apexel200-1x
```

## Lens distortion

Small clip-on lenses can have barrel or pincushion distortion and field curvature, so the scale may differ between the centre and the edge of the field. To check, photograph the micrometer with the ruling at the centre and at the edge and compare µm/px. If the difference is more than a few percent, restrict analysis to the central region (a smaller field mask) until a distortion correction is added.

## Resolution

Magnification and resolution are different properties. Record the finest micrometer spacing in which the lines are still separated, and note it in the profile (`--notes`). If 10 µm lines are not clearly resolved, guard cell boundaries will not be either, and only counting (not size or aperture) should be attempted with that setup.
