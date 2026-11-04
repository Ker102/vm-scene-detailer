# Scale probe status per part

`scripts/scale_probe.py` dresses four houses from the built library with every
part on (Gable 45°, porch, balcony, whole-building damage 0.42, vines, yard):

| Case | Mesh (m) | Unapplied object scale |
|---|---|---|
| tiny | 3.6 × 2.8 × 2.5 | 1 |
| big | 16 × 10 × 6.5 | 1 |
| tower | 4.2 × 4.2 × 9 | 1 |
| objscale | 5 × 4 × 2.4 | (1.6, 1.0, 1.3) |

For every pool it reports the count, the world scale range, the **aniso** (largest
over smallest axis scale of an instance, which shows stretching), and either
"floating" (origin more than 12 cm from the evaluated house) or, for the yard,
inside / too far out.

How to read it:
- Cladding aniso is large **by design**: tiles are trimmed to outlines, so a
  2 cm sliver at a gable has a tiny X scale. Compare the objscale case with the
  unscaled ones, not with 1.0.
- "Floating" studs, sheathing and worn boards sit in **cut wall holes**: their
  origin is over the hole, so the nearest wall face is far away. That is
  expected. The real tests are the build checks `v2.29(sheathing)` (all on the
  wall plane, none in an opening) and `v2.30(world-space)`.
- One "floating" window in the tiny case is a loose window tilted off the wall
  by the damage (by design; you can see it in the render).

## v2.29 (2026-11-04, before the fix)
| Pool | tiny | big | tower | objscale |
|---|---|---|---|---|
| Doors / Windows aniso | 1.00 | 1.00 | 1.00 | 1.01 ✔ |
| Shingles aniso | 1.78 | 3.65 | 3.45 | 1.80 ✔ |
| Yard, all sets: inside / far | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 ✔ |
| **Yard aniso** | 1.00 | 1.00 | 1.00 | **1.60 ✘** |
| **Sheathing aniso** | 1.00 | 1.00 | 1.00 | **1.50 ✘** |
| **Studs aniso** | 1.00 | 1.00 | 1.00 | **1.60 ✘** |

The v2.29 parts were stretched by the unapplied object scale, and their lattice was
laid in local units. Fixed in v2.30: `world_shape()` plus the lattice in world metres.

## v2.30 (2026-11-04, `scale_probe.py -- rebuild`)
| Pool | tiny | big | tower | objscale |
|---|---|---|---|---|
| Doors / Windows aniso | 1.00 | 1.00 | 1.00 | 1.01 ✔ |
| Shingles aniso | 1.78 | 3.65 | 3.45 | 1.80 ✔ |
| Yard: inside / far | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 ✔ |
| Yard aniso | 1.00 | 1.00 | 1.00 | **1.00 ✔** |
| Sheathing aniso (n) | 1.00 (43) | 1.00 (1031) | 1.00 (442) | **1.00 (178)** ✔ |
| Studs aniso (n) | 1.00 (195) | 1.00 (2137) | 1.00 (945) | **1.00 (430)** ✔ |

The unscaled cases match v2.29 exactly (same counts). On objscale the lattice now
runs in world metres: there are more studs (377 → 430) because the 1.6× wall really is
1.6× longer. The `v2.30(world-space)` build check pins this.

**Still approximate under a non-uniform scale:** the yard's distance band from the
wall uses the volume-mean factor `geo_f`. On the objscale house, props on the
walls facing X sit up to about 25 % further out than on the walls facing Y (max out
0.56 m vs 0.41 m). It is harmless at today's 1.2 m Yard Width. Use `ws["eff_of"]`
of the wall normal if it ever shows.

Update this file after every probe run.
