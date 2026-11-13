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

## v2.32 (2026-11-06, from the built library; v2.30 re-probed as reference)
| Pool | tiny | big | tower | objscale |
|---|---|---|---|---|
| Every wall / yard / ivy / intact-shingle count vs v2.30 | = | = | = | = ✔ |
| ShakeShard n (aniso, floating) | 9 (1.00, 0) | 126 (1.00, 0) | 12 (1.00, 0) | 48 (1.00, 0) ✔ |
| ShingleBroken v2.30 -> v2.32 | 56 -> 53 | 798 -> 665 | 141 -> 128 | 288 -> 248 |
| ShingleWorn v2.30 -> v2.32 | 433 -> 425 | 4681 -> 4545 | 921 -> 907 | 1459 -> 1424 |

The only changes are the roof holes': shards, and tiles over a hole with
nothing left to hold them now fall. The roof frame is realized geometry (not
in the probe); the `v2.32(world-space)` check pins it (rafters every 0.6 world m).
The first v2.32 probe showed ivy 704 -> 294 on objscale: the v2.31 Join
Geometry order bug (see the Lessons in SKILL.md), fixed before delivery.

## v2.33 (2026-11-06, from the built library; v2.32 as reference)
| Pool | tiny | big | tower | objscale |
|---|---|---|---|---|
| ShingleBroken v2.32 -> v2.33 (floating) | 53 -> 86 | 665 -> 1149 (5 -> 10) | 128 -> 188 (2 -> 3) | 248 -> 385 (1 -> 2) |
| ShingleWorn v2.32 -> v2.33 | 425 -> 392 | 4545 -> 4066 | 907 -> 846 | 1424 -> 1288 |
| ShakeShard n (aniso 1.00, floating 0) | 9 -> 8 | 126 -> 117 | 48 -> 44 | ✔ |
| Stud / Sheathing / PlankBroken (cut-wall pools) | = | Stud 478 -> 499, Sheathing floating 111 -> 114 | PlankBroken floating 1 -> 4 | other floating 23 -> 33 |

Broken shingles up and worn down: the torn rim (tiles whose butts hang over a
hole break short instead of staying whole) and the wider worn pools. The
small floating rises are on the cut-wall pools that SCALE_STATUS already notes
as hanging into holes by design (torn pieces at the hole edge); aniso is 1.00
everywhere, so no stretching.

## v2.34 (2026-11-06, from the built library; v2.33 as reference)
| Pool | tiny | big | tower | objscale |
|---|---|---|---|---|
| ShingleBroken v2.33 -> v2.34 (floating) | 86 -> 103 | 1149 -> 1377 (10 -> 14) | 188 -> 223 (3 -> 1) | 385 -> 461 (2 -> 2) |
| ShingleWorn v2.33 -> v2.34 | 392 -> 381 | 4066 -> 3985 | 846 -> 827 | 1288 -> 1258 |
| Shingle (intact) scale | 0.58..1.16 -> 0.53..1.06 | same ratio | same ratio | same ratio |
| Everything else | = | Stud floating 499 -> 500 | = | = |

ShingleBroken min scale 0.07..0.10 and aniso up to 16: the new head-torn
`_UL/_UR` pieces are 1 m pieces placed at z-scale ~0.17 by design (the
`zs`/`uvs` rule in vm-asset-cladding), not stretching. The intact Shingle
range moved by the same 0.91 at both ends because the new corner-chip draw
reshuffled the six random widths (0.169..0.228 m, inside the 0.165..0.235
design range). No floating intact or worn tiles; broken floating stays the
few torn pieces hanging into the hole.

## v2.35 (2026-11-06, from the built library; v2.34 as reference)
| Pool | tiny | big | tower | objscale |
|---|---|---|---|---|
| ShingleBroken v2.34 -> v2.35 (floating) | 103 -> 89 | 1377 -> 1168 (14 -> 13) | 223 -> 197 (1 -> 1) | 461 -> 402 (2 -> 2) |
| ShingleWorn v2.34 -> v2.35 | 381 -> 395 | 3985 -> 4194 | 827 -> 853 | 1258 -> 1317 |
| Everything else | = | = | = | = |

The tiles beside a hole moved from the broken pool (torn short at the butt)
to the worn pool's new side sets (_L / _RNN, full length): broken + worn is
the same total in every case. Scale ranges and anisotropy unchanged, no new
floating tiles.

## v2.36 (2026-11-08, from the built library; v2.35 as reference)
| Pool | tiny | big | tower | objscale |
|---|---|---|---|---|
| Shingle (intact) v2.35 -> v2.36 | 117 -> 102 | 1492 -> 1255 | 323 -> 277 | 498 -> 422 |
| ShingleWorn | 395 -> 352 | 4194 -> 3441 | 853 -> 728 | 1317 -> 1086 |
| ShingleBroken (floating) | 89 -> 49 (0) | 1168 -> 708 (13 -> 3) | 197 -> 139 (1 -> 1) | 402 -> 251 (2 -> 0) |
| ShakeShard (floating) | 8 -> 25 | 117 -> 376 (0 -> 1) | 12 -> 60 | 44 -> 111 |
| Walls, sheathing, studs, yard | = | = (Stud +18) | = | = |

Two v2.36 changes move these. The lone-tile pass (`tall_iso`) clears tall
tiles in the damage with fewer than two whole neighbours (and broken pieces
with none), so on these probe houses (whole-building damage 0.42 - most of
the roof is in the damage) the holes grow and the shards placed round them
triple. And the tiles along a hole's side edges move from the broken pool
(butt-torn) to the worn pool's side sets. Scale ranges and anisotropy
unchanged, no intact or worn tile floats. (A first v2.36 round, before the
side-edge fix, lost far more worn tiles: big 4194 -> 2751.) If heavy-damage
roofs read as too open, gate the pass to the hole itself (roof cut /
`rf_sel`) rather than the whole damage mask.

Update this file after every probe run.
