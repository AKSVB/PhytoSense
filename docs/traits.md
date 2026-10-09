# Trait definitions

All lengths are converted from pixels with the calibration profile. The analysed area is the field-of-view mask (illuminated and inside the clip-on lens's circular image, minus a margin).

## Density

`density = n / A`, where `n` is the number of stomata whose centre lies inside the mask and `A` is the mask area in mm². Counting centres (rather than whole stomata) gives an unbiased density estimate regardless of stomata cut by the field edge.

## Stomatal index

`SI = n_stomata / (n_stomata + n_pavement_cells)`, counted in the same area. Requires a pavement cell count.

## Size

Length and width of the stomatal complex (guard cell pair). The blob detector estimates them from intensity moments and gives only approximate values. A trained detector with oriented boxes gives better values; guard cell and pore dimensions require segmentation and adequate resolution (see [calibration.md](calibration.md)).

## Nearest-neighbour distance

Distance from each stoma to the closest other stoma, centre to centre.

## Clark-Evans aggregation index

`R = mean_NND / E[NND]`, with the expected value under complete spatial randomness corrected for edge effects after Donnelly (1978):

`E[NND] = 0.5 * sqrt(A/n) + (0.0514 + 0.041/sqrt(n)) * P/n`

`SE = sqrt(0.0703 * A/n² + 0.037 * P * sqrt(A/n⁵))`

where `A` and `P` are the field area and perimeter. `z = (mean_NND - E[NND]) / SE` gives a two-sided p-value. Normal stomatal patterning usually gives R > 1 (regular spacing).

## Ripley's L function

`L(r) - r`, with `L(r) = sqrt(K(r)/π)` and `K(r)` estimated with border correction (only stomata at least `r` from the field edge are used as centres). Values below the CSR envelope at short distances indicate inhibition; values above indicate clustering. `spatial.csr_envelope` simulates random patterns in the same field for comparison.

## Clusters

Stomata whose centres are closer than a contact distance (default: the median complex width) are linked; groups of two or more are reported as clusters. This approximates stomata in direct contact, i.e. violations of the one-cell spacing rule.

## Orientation

Axial mean direction (0 to 180°) and mean resultant length `r` of doubled angles; `r` near 1 means stomata are aligned, near 0 means random orientation.
