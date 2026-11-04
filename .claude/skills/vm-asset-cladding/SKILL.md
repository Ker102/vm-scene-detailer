---
name: vm-asset-cladding
description: Make a new ASSET SET for the VM engine's cladding - wall siding boards (VM_Tiles_Plank) and roof shakes/shingles (VM_Tiles_Shingle) plus their damage pools (PlankBroken / PlankWorn / ShingleBroken / ShingleWorn) - so a house can wear different wood, board sizes or roof coverings (cedar shakes, wide clapboard, slate, board-and-batten...). Use when the user wants a different siding or roof look, a new plank or shingle style, or more damage variety on them.
---

# Cladding asset sets (siding and roof shakes)

Shared rules and the build/test loop are in `../vm-new-building-part/WORKFLOW.md`.

**Status (v2.29): the most mature part.** World-space course formula and
unapplied-scale checks (`world-space:` and `reflow:`) pass, and the damage
pools have been tuned through v2.13, v2.28 and v2.29. Scale probe: see the bottom.

## How the engine uses a set
- Layers `VM_SceneDetailer_Planks` (walls) and `VM_SceneDetailer_Shingles` (roof)
  lay **courses** of instances. Each course is Row Height high, the slots are
  `Slot Width * (1 - Row Overlap)` apart, and Stagger shifts every other row. The
  variant per slot comes from the No-Repeat pick (column plus a random offset per
  course), so every variant shows.
- The sockets are wired by `AUTO_COLLECTIONS` in `VM_Tools_Addon.py`:

  | Socket | Planks | Shingles |
  |---|---|---|
  | Primary Props | `VM_Tiles_Plank` | `VM_Tiles_Shingle` |
  | Broken Props (Damage) | `VM_Tiles_PlankBroken` | `VM_Tiles_ShingleBroken` |
  | Worn Props (Wear band) | `VM_Tiles_PlankWorn` | `VM_Tiles_ShingleWorn` |
- **Each tile is scaled to its course.**
  - Height is Row Height / (1 - Row Overlap): the lapped tile.
  - Length is the slot (Slot Width), clipped to the wall or roof outline when
    Trim To Face is on.
  - The engine reads the nominal size from the Primary Props bounds. **All variants
    in a set share one nominal size** (width jitter only inside that bbox). The
    mesh's real size matters for the thickness and grain; X and Z get stretched to
    the course.
  - Keep the set's proportions close to the course, or the grain and bevels stretch.
- Dress values (`dress_stack()` in the add-on) that go with today's tiles:
  - planks: Row Height 0.17, Overlap 0.19 (a 21 cm board), Stagger 0.37,
    Slot Width 2.4, Edge Boards on;
  - shakes: Row Height 0.13, Overlap 0.69 (42 cm, three layers deep), Stagger 0.5,
    Slot Width 0.8, ridge Edge Boards.

  **A set with other sizes needs a preset with matching numbers.**

## The asset contract (every variant)
- One mesh object, transforms applied, named `<Set>_01 .. _NN`. Collection Info
  sorts the variants alphabetically, so the numbering is the pick order.
- **Frame:** X runs along the course (planks) or across the roof (shakes), Z goes up
  the face, and +Y points out of the surface.
  - Origin at the tile centre in X and Z.
  - Flat back plane at y = -0.006 (planks) or -0.004 (shakes), sitting on the wall.
  - The front tapers from the thick butt at the bottom edge to the thin top, so the
    course above laps over it.
- **Size = real metres**: planks 2.0 × 0.2 m (butt 22 mm, top 6 mm); shakes
  0.165–0.235 × 0.42 m (butt 24 mm, tip 4 mm). Width variation inside a set
  is fine (the gaps read as real). The course pitch comes from the preset,
  not from the mesh. The demo stage's flat test tiles in `main()` (Row 0.22 / 0.11)
  are pinned by old checks; don't copy their numbers.
- **UVs:** U = metres along the grain (X for planks, Z for shakes) and V = 0..1
  across. `make_board_material(name, tex_dir, tex, n_boards, phase, tex_w, lo, hi, darken)`
  maps each instance onto one whole board of a plank texture at a random offset,
  so no seam crosses a tile. `n_boards` and `phase` are measured from the texture's
  normal map.
- **Damage pools** use the same frame and the same width:
  - **Broken** (`_rough_tile`): 1 m long, the nailed end square at the origin, and
    a jagged free end with a splinter. Planks come in `_L` / `_R` mirrored pairs:
    `_L` runs along +X, `_R` is its mirror. Shakes keep the nailed top edge at the
    origin and run 1 m down -Z.
  - **Worn:** full-size, ordered light (`_01`) to heavy (`_NN`). The engine picks
    heavier ones nearer the damage.
  - Both carry mesh attributes `vm_wear` (weathered, bleached) and `vm_cut` (raw
    wood at a gouge or break), which the board material reads. Get them from
    `_weathering(...)` and `_rough_tile(...)`.

## Making a new set
1. **Reference:** ask the user for an image of the siding or roof they want, unless
   they already sent one. Read off the board width, exposure (Row Height),
   lap, profile, colour and weathering.
2. **Generator** (preferred: procedural and deterministic): copy
   `make_siding_variants` / `make_shake_variants` (and the broken and worn makers) into
   `make_<style>_variants(col, name, n, mat, ..., seed=)`. Change the profile in
   `_tile_mesh(...)` or the `shape(v)` deform. Keep the frame, the back plane and the UV rule.
   - A downloaded scan or tile works too, but normalise it to this frame and
     size, apply transforms and rebuild the UVs to the U-along-grain rule.
3. **Material:** texture into `~/Documents/ViperMeshAssets/materials/walls/<id>/`
   (Poly Haven CC0, with `SOURCE.txt`), then `make_board_material(...)` in the
   library section's `lib_mats`.
4. **Pools:** in the library section of `main()` (search `VM_Tiles_PlankBroken`),
   create the sibling collections under the same `tile_parent`:
   `VM_Tiles_Plank_<Style>`, `..._<Style>Broken` and `..._<Style>Worn`.
   Use 6+ intact, 12+ broken and 16+ worn.
5. **Wire it:** add a **library preset**, a new tuple in the `lib_presets` loop
   (search `"Base - Balcony house"`). The loop dresses a probe cube, then
   `set_params(...)` changes it, then `vmt.snapshot_object(probe)` records it. In
   your branch, set Primary, Broken and Worn Props on the Planks or Shingles
   modifier to `bpy.data.collections["VM_Tiles_Plank_<Style>"]` (and the others),
   plus the matching Row Height, Slot Width, Overlap and Stagger.
   - The snapshot stores collections by name as `["id", "NodeSocketCollection", name]`.
     `apply_snapshot` writes them back as they are.
   - Dress alone wires only the defaults in `AUTO_COLLECTIONS`. Make the new set the
     default only when the user asks, by changing `AUTO_COLLECTIONS`.
   - The user can also swap the collection in the modifier panel and save it with
     VM: Save Preset.
6. **Checks:** copy an existing cladding check onto a fresh house with the new preset:
   - counts follow the course formula;
   - no tile floats more than 5 mm off the wall;
   - every variant appears;
   - broken pieces sit next to an intact board.
7. **Test:** scale probe (tiny, big, tower, objscale), then look shots of a house with
   the new preset, close-up and from a few metres back. Check the laps, the shadow
   lines and that no texture repeats.

## Lessons (append; newest last)
- v2.27: all intact tiles showed variant 0 until the No-Repeat pick got a
  random offset per course. Check that every variant shows.
- v2.28: "perfectly smooth" damaged planks read as fake. They need real ragged
  geometry (`_rough_tile` with grain, gouges, knot holes, splits, warp) and the
  bleach / raw-wood attributes, graded light to heavy towards the damage.
- v2.26: steep gable and hip roofs only got shakes once the roof cap's pitched
  faces counted as roof at any pitch above the wall band (Roof Slope Min/Max).

## Scale probe (v2.29)
See the `scale_probe` results in `../vm-new-building-part/SCALE_STATUS.md`.
