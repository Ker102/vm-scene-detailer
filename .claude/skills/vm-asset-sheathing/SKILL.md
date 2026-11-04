---
name: vm-asset-sheathing
description: Make a new ASSET SET for what the VM engine shows behind damaged siding - the diagonal sheathing boards (VM_Tiles_Sheathing) and the studs (VM_Tiles_Stud) - e.g. horizontal shiplap sheathing, plywood sheets, OSB, brick infill, log or stone walls behind the cladding. Use when the user wants a different "what is under the siding" look or the wall holes to show other structure.
---

# Sheathing and stud asset sets (behind the damage)

Shared rules and the build/test loop are in `../vm-new-building-part/WORKFLOW.md`.

**Status (v2.30): verified, scale-safe.** `v2.29(sheathing)` check: 168 pieces, none off the wall,
none in a cut opening, 1.7 mm proud. v2.30 made it safe under an unapplied non-uniform object scale (`world_shape`, lattice in world metres). Probe numbers:
`../vm-new-building-part/SCALE_STATUS.md`. It shows wood three ways: siding
horizontal, sheathing diagonal, studs vertical.

## How the engine uses a set
- Panel **Wall Holes** on `VM_SceneDetailer_Windows` (the layer that cuts the
  openings). Sockets:
  - `Sheathing` 0.85 (share of the damage area covered);
  - `Sheathing Props` → `VM_Tiles_Sheathing`;
  - `Stud Props` → `VM_Tiles_Stud`.

  They are wired in `AUTO_COLLECTIONS`.
- Sheathing pieces lie on a **45° lattice**. Each piece spans two studs
  (`SHEATH_STUD` = 0.4 m), with joints on every second stud, a pitch of
  `SHEATH_PITCH` = 0.14 across the boards and a board width of `SHEATH_WIDTH` = 0.132.
- A piece is kept only where `sh_onwall` is true: within 4 mm of the host wall, and
  not within 6 cm of an `open_cut_at` cut or an `o_real` cutter box.
  `A` (whole) pieces go where all of it is on the wall; `B` (broken) pieces go at
  the hole and outline edges.
- Studs are stacked from `STUD_CELL` = 0.25 m lengths at every
  `j * SHEATH_STUD` along the wall, merged at 1 cm, only in cells where a hole
  opens the wall (`st_hole`: more than 1.5 cm from the `c_open` faces). They are
  tagged `vm_sheath`.
- **The constants are part of the contract.** A new set with another stud
  spacing or board pitch must change the constants, or better, add sockets
  after the existing ones and default them to today's values.

## The asset contract
- **Sheathing** `<Name>A_NN` (whole) and `<Name>B_NN` (broken), the same count of each:
  - Frame: X along the board, Z across it, +Y out of the wall.
  - Front at y = +0.0015 (just proud of the wall face, behind the siding's back
    plane at -0.006). Back at y = -0.0155.
  - A whole piece is a parallelogram with **plumb-cut ends** (it spans 2 studs
    at 45°): half-length `L = stud·√2 - 0.001`, half-width `h = width/2`.
  - A broken piece keeps the nailed plumb end at -X and breaks off 30–85 % of the way
    along in a jagged, splintered line.
  - The grain may groove in but never stand proud (`capped`). Use the
    `_rough_tile` + `_weathering` attributes `vm_wear` / `vm_cut`, with less bleach
    (0.5): it was out of the weather.
- **Studs** `<Name>_NN` (4 lengths):
  - 38 × 70 mm, STUD_CELL long, Z up and centred, X along the wall (±19 mm).
  - Face at y = -0.0158 (just behind the sheathing), back at -0.0858.
  - Grain along Z.
- **Material:** `make_board_material(...)` (today it is `VM_SheathBoard`, brown_planks_09,
  7 boards, phase 0.08). The bare wall face behind them is `VM_Sheathing`
  (darken 0.1) and reads as the dark cavity.

## Making a new set
1. Ask the user for a reference of the structure they want behind the
   siding (an old barn, plywood, brick nogging…).
2. Copy `make_sheathing_boards` / `make_studs` into `make_<style>_sheathing(...)`.
   - Horizontal boards: rotate the lattice by adding an angle socket (default 45°).
     Don't fake it in the mesh.
   - Sheet goods (plywood, OSB): one large `A` piece per stud bay.
3. Put the pools in sibling collections `VM_Tiles_Sheathing_<Style>` /
   `VM_Tiles_Stud_<Style>` (library section, next to the `VM_Tiles_Sheathing`
   line), and wire them through a library preset (see the `vm-asset-cladding` step 5).
4. Checks: extend `v2.29(sheathing)`, which runs on a fresh house with Weathered gable and
   Half Broken 1. It asserts:
   - pieces > 0, all within 4 mm of the wall;
   - none inside a **cut** opening (one with no wall face at its centre; inset 0.1);
   - none more than 2 mm proud;
   - studs only where the wall is open.
5. Probe and look: the scale probe's `VM_Tiles_Sheathing` / `VM_Tiles_Stud` rows
   must show no floating pieces, then a close-up render of a hole.

## Lessons (append; newest last)
- Boards across a hole with nothing behind them float. Studs fixed that, but
  only once the stud cells tested the hole against the actual `c_open` faces
  (Proximity > 1.5 cm) instead of the gap markers.
- The bbox casing margin made a window look "inside" sheathing. Use inset 0.1,
  and test against the real cutter boxes (`o_real`, SampleNearestSurface
  position and normal), not bounding boxes.
