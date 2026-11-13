---
name: vm-asset-cladding
description: Make a new ASSET SET for the VM engine's cladding - wall siding boards (VM_Tiles_Plank) and roof shakes/shingles (VM_Tiles_Shingle) plus their damage pools (PlankBroken / PlankWorn / ShingleBroken / ShingleWorn) - so a house can wear different wood, board sizes or roof coverings (cedar shakes, wide clapboard, slate, board-and-batten...). Use when the user wants a different siding or roof look, a new plank or shingle style, or more damage variety on them.
---

# Cladding asset sets (siding and roof shakes)

Shared rules and the build/test loop are in `../vm-new-building-part/WORKFLOW.md`.

**Status (v2.36): the most mature part.** World-space course formula and
unapplied-scale checks (`world-space:` and `reflow:`) pass, and the damage
pools have been tuned through v2.13, v2.28 and v2.29. v2.32 added the first
non-wood covering (asphalt shingles) and the roof frame under holes. v2.33
reworked the roof damage after the user's "muddy, intact shapes, not much
variation": torn outlines (`_tall_damage`), a torn hole rim, damage in the
visible part, more variants. v2.34 (the user's "the damage faces the
undamaged roof" and "tiles stuffed into each other, like plasticine"): tall
tiles are damaged on the side that faces the damage (head-torn pieces and
worn-from-above sets), every lift stays in the visible part (`_expo`), and
crisp splintered wood tears (`_wood_tear`). v2.35 (the user's "damage in
every direction around the hole" and "broken asphalt is not a straight
cut"): side-broken worn sets for the tiles beside a hole, and every asphalt
break a brittle fracture (`_fracture_outline`, `_edge_crack`, a granule-loss
band). v2.36 (the user's "unbroken tabs lying in the hole" and "blobby
dark patches"): the lone-tile pass (`tall_iso`) clears whole tiles and
broken pieces left alone in a hole, the roof is cut under them, and asphalt
granule loss is speckle in the material, not a thresholded blob in the mesh;
after the user marked a render, the tiles along a hole's left / right edges
break off facing the hole (side sets) instead of at the butt.
Scale probe: see the bottom.

## Sets in the library
| Set | Pools | Material | Preset |
|---|---|---|---|
| Siding planks | `VM_Tiles_Plank` / `PlankBroken` / `PlankWorn` | `VM_Siding` (texture) | Dress default |
| Cedar shakes | `VM_Tiles_Shingle` / `ShingleBroken` / `ShingleWorn` | `VM_Shake` (texture) | Dress default |
| Asphalt shingles (v2.32) | `VM_Tiles_Shingle_Asphalt` / `_AsphaltBroken` / `_AsphaltWorn` | `VM_Asphalt` (procedural) | `Base - Asphalt roof`, `Base - Weathered asphalt` |

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

  **A set with other sizes needs a preset with matching numbers.** For a tile
  `w` wide and `L` long laid with exposure `e` (the visible course):
  - Row Height = `e`;
  - Row Overlap = `1 - e / L` (so the lapped tile is L);
  - Slot Width = `w / (1 - Row Overlap)` (so the slot pitch is exactly `w`;
    with Trim To Face the widest variant is scaled to that pitch);
  - Stagger 0.5 for joints that line up every other course (three-tab look).
  Asphalt: `w` 0.25, `L` 0.33, `e` 0.13 -> Overlap 0.606, Slot Width 0.635
  (`ASPHALT_OVERLAP` in build_engine.py).
- **Tall or long decides the damage.** The engine treats a tile that is
  longer in X than in Z (`d_long`) like siding: broken pieces run along the
  course in `_L` / `_R` pairs. A roof tile must be **taller than wide** in its
  mesh (asphalt tab 0.25 x 0.33) or it gets the siding damage on the roof.

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
    - **A worn TALL tile must not keep its outline** (v2.33, the user's "the
      shape of the tiles remains perfectly intact"). Use
      `_tall_damage(rng, w, L, sev, tear_max, exposed)`: with severity, the
      butt torn off ragged and slanting, a big broken corner, gaping splits,
      side bites, all inside the exposed bottom part. Both the shakes and the
      asphalt tabs use it. Vary the width per variant like the intact set.
  - **v2.34 TALL-tile pool layout (shakes, asphalt tabs) - the engine depends on it:**
    - Broken: groups of FOUR per variant, sorted `_NN_L`, `_NN_R` (torn at
      the butt: nailed head at the origin, 1 m down -Z) and `_NN_UL`, `_NN_UR`
      (torn at the HEAD: the butt at the origin, 1 m UP +Z, for the tile just
      below a hole). The engine places a `_U` piece at the tile's bottom edge.
    - Worn (v2.35): FOUR sets of the same size, in name order `_01.._NN`
      damaged at the butt (tiles above the damage), `_L01.._LNN` / `_R01..
      _RNN` broken off on their -X / +X side (`_side_damage`: tiles beside a
      hole - vm_dsid 3/4 - or in the Wear band with the damage to their side -
      vm_dsid 1/2; wood splits along the grain, asphalt in brittle facets, up
      to about the covered line), then `_U01.._UNN` damaged from above
      (`_tall_damage_head`) for tiles whose nearest damage is above them. The
      engine picks set `wo_set * floor(n / 4)` + severity.
    - Boards (`d_long`) keep `_L` / `_R` pairs and one worn set.
  - **No lift under the course above** (v2.34): the courses share one plane
    and a butt is only ~6 mm (shake) / ~2.4 mm (tab) thicker than the tile
    under it, so any curl, cup or warp there pushes through the course
    above. Scale every lift by `_expo(z, L, exposed)` (0 from the covered
    line up). The `v2.34(no push-through)` check measures it (<= 2.5 mm).
  - **A piece made 1 m and scaled down** (broken pools) lays its weathering
    and UVs out in REAL metres: `_weathering(..., zs=<shown m per unit>)`
    and `_rough_tile(..., uvs=zs)`, step along the grain `real / zs`.
    Otherwise the grain, gouges and texture are squashed 3-6x into blobs.
    v2.35: draw such a piece's OUTLINE in real metres too (the tear, chips,
    cracks), then divide z by the drawn length - a tear drawn on the 1 m
    piece is squashed flat into a near-straight line.
  - **Asphalt (and any material read in texture space)**: give the mesh
    real-metre UVs (`_uv_metres(me, zs)`); the asphalt material reads UVs, not
    object space (object space follows the instance scale - squashed granules).
  - **Brittle breaks** (asphalt, slate, tile): run the outline through
    `_fracture_outline(rng, ol, _is_orig(w, (z lines)))` - every edge that is
    not an original cut edge becomes angled facets rough at every scale,
    calmer below 3 cm - plus `_edge_crack` (cracks running on from a break,
    `pick=` for splits from the butt) and `_asphalt_wear(..., brk_d=
    _break_field(ol, orig))` for the granule-loss band. Wood keeps
    `_wood_tear` / grain splits. The `v2.35(brittle asphalt)` check measures
    the straight share of the breaks.
  - **Asphalt granule loss** (v2.36): `vm_wear` on an asphalt piece is a
    smooth CHANCE of granule loss (broad patches + streaks down the roof,
    capped at 0.8 away from breaks), and `make_asphalt_material` drops each
    1-2 mm granule (Voronoi cell, its own random) under that chance,
    clustered by a 55/m noise. Never threshold noise into the mesh value:
    at ~9 mm vertex spacing it renders as soft black blobs. Solid black
    (vm_wear 1) only in the break band.
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
   - `make_board_material` is **wood only** (one board of a plank texture per
     tile, the wear bleaches, the cut shows raw wood). A non-wood covering
     (asphalt, slate, metal, tar paper) needs its own material that still
     reads the two attributes: copy `make_asphalt_material`. It uses Object
     coordinates plus Object Info Random (per-tile offset and tone), a fine
     Voronoi for the grain, `vm_wear` -> what shows when the surface wears
     off, `vm_cut` -> the core at a tear, and a bump from the grain.
   - Poly Haven has no asphalt shingle texture (searched v2.32); look there
     first, but expect to go procedural for man-made coverings.
   - Write the damage noise for the material, not for wood: `_asphalt_wear`
     (granule-loss patches, hairline cracks, a torn felt edge) replaces
     `_weathering` (grain, knots) as the `disp` passed to `_rough_tile`.
     Keep wear patches small and sparse: large dark patches read as
     camouflage (v2.32 first look).
4. **Pools:** in the library section of `main()` (search `VM_Tiles_PlankBroken`),
   create the sibling collections under the same `tile_parent`:
   `VM_Tiles_Plank_<Style>`, `..._<Style>Broken` and `..._<Style>Worn`.
   Use 6+ intact, 10-12+ broken and 20 worn (v2.33: the user saw "not much
   variation" with 6 torn asphalt and 12 worn shakes).
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
   - **A roof set also sets the Windows layer:** the frame under a hole and
     the shards come from there (`Batten Props`, `Batten Spacing`, `Roof
     Debris Props`, see below). Asphalt uses a board deck
     (`VM_Tiles_RoofDeck`, spacing 0.15) and `VM_Tiles_AsphaltShard`.
6. **Checks:** copy an existing cladding check onto a fresh house with the new preset:
   - counts follow the course formula;
   - no tile floats more than 5 mm off the wall;
   - every variant appears;
   - broken pieces sit next to an intact board.
7. **Test:** first the assets alone: `scripts/lineup.py` (every pool in a row,
   fronts up) and, for any colour artefact, `scripts/attr_profile.py`. Then
   the fast house test with flat pool colours (`build/v232_test.py --
   poolcolors closeonly`: grey intact, red broken, yellow worn) to see which
   pool sits where, then real materials. Then the scale probe (tiny, big,
   tower, objscale) and look shots of a house with the new preset, close-up
   and from a few metres back. Check the laps, the shadow lines and that no
   texture repeats. **At a hole's rim nearly every tile must be torn**
   (the `v2.33(torn rim)` check).

## The roof frame under a hole (v2.32)
A damage zone on the roof cuts holes (Shingles layer markers, Windows layer
boolean). Under them the Windows layer lays the frame from three pools:
- **Battens** (`VM_Tiles_Batten`, or `VM_Tiles_RoofDeck` for a deck):
  `make_battens(col, name, n, mat, width, thick, length=ROOF_RAFTER)`. X along
  the eaves (one rafter bay, 0.6 m), Z across, top at y=0. `A_NN` whole,
  `B_NN` snapped (nailed end at -X, splintered free end). The engine keeps
  whole ones, snapped stubs from either rafter and hanging stubs by Frame
  Breakage, and lays them every Batten Spacing (world m).
- **Rafters** (`VM_Tiles_Rafter`): `make_rafters`, Z along, 0.5 m segments
  (scaled to the course pitch), under the battens.
- **Shards** (`VM_Tiles_ShakeShard`, `VM_Tiles_AsphaltShard`):
  `make_roof_shards(..., asphalt=)`, flat, back at y=0, raw rim. Laid mostly
  below the hole, never over it.
- Material: `VM_RoofFrame` (darker, little bleach) for the frame.
- Checks: `v2.32(roof damage)`, `v2.32(asphalt)`, `v2.32(world-space)`;
  the frame pieces carry `vm_fpc` (1 whole, 2 stub, 3 hanging, 4 rafter).

## Lessons (append; newest last)
- v2.27: all intact tiles showed variant 0 until the No-Repeat pick got a
  random offset per course. Check that every variant shows.
- v2.28: "perfectly smooth" damaged planks read as fake. They need real ragged
  geometry (`_rough_tile` with grain, gouges, knot holes, splits, warp) and the
  bleach / raw-wood attributes, graded light to heavy towards the damage.
- v2.26: steep gable and hip roofs only got shakes once the roof cap's pitched
  faces counted as roof at any pitch above the wall band (Roof Slope Min/Max).
- v2.32 (asphalt, the first set made from this skill): the frame, naming,
  pools and preset steps worked first time. What was missing then is now
  above: the course formula for a new size, the tall-vs-long damage rule,
  a non-wood material, and the Windows-layer pools a roof set needs.
- v2.32: give a thin covering a taper (butt 5 mm, tip -1 mm) even when the
  real one is flat; flat lapped tiles z-fight with the course below.
- v2.33 ("muddy / not realistic" roof): `_weathering`'s gouges were sized
  for 2 m planks. On a 42 cm shake they came out ROUND and their raw-wood
  `vm_cut` showed as pale beige blobs, like paint spots. Gouges on a short
  tile run along the grain (3-6x longer than wide, at the edge), and an old
  roof's gouges are weathered grey: only a little `vm_cut` in the deep
  middle. Fresh raw wood belongs at a fresh break only.
- v2.33: **a lineup render must show the FRONT.** Lay tiles with
  `rotation_euler = (90 deg, 0, 180 deg)` (+Y up, Z up the roof -> +Y).
  The v2.32 lineup used -90 deg and showed the flat backs. The back is the
  outline alone, triangulated, so it smears the edge vertices' `vm_cut` over
  big triangles: fake brown halves and bands, a whole round of wrong fixes.
- v2.33: to find what makes a colour artefact, print the attributes per
  height band (`scripts/attr_profile.py` in this skill) before you touch the
  material. A full-width band of `vm_cut` is a gouge; a crisp line is a
  `z <` condition.
- v2.33: every procedural noise in a non-wood material reads each tile's
  OWN offset coordinates (Object + Random x a vector). The v2.32 asphalt
  mottling used plain Object coordinates, so every tab had the same stains.
  Stretch stains along Z: they run down the roof.
- v2.33 (engine): the tiles that frame a hole were "worn" (category 4) or
  loose (3, which shows the worn pool too) and kept their whole outline.
  Now an intact, worn or loose tall tile next to a missing one breaks
  (category 2, `d_rim` in the Shingles layer): the tile under its butt (one
  course pitch `d_pitch` down, at +-0.5 of the half-width) or its neighbour
  in the course (+-1.6 half-widths) is missing; radius 0.3 pitch, because
  tiles lap three deep and the centres near a butt belong to two courses.
  Intact-only did nothing: the Wear band has made every tile round the
  damage worn already. Result: whole outlines over the hole went from 28 /
  20 broken to 2 / 31 (shakes) and 20 / 20 to 4 / 24 (asphalt).
- v2.33 (engine): **damage must land in the VISIBLE part of a tile.** A
  broken tall tile kept 70-95 % of its length (the siding rule), but only
  the bottom `1 - Row Overlap` (31 % of a shake, 39 % of a tab) shows: a
  "broken" tile lost 2 cm and looked whole. Tall tiles now lose 30-90 % of
  the exposed part (`d_frac`). Same rule in the assets: `_tall_damage`
  damages only the `exposed` bottom of the outline.
- v2.33: intact shakes from `_rough_tile` with full edge rounding read as
  pillows / cobblestones from a few metres. Split wood has crisp edges:
  `_weathering(..., edge=0.3)` for the intact set, 0.4 worn, 0.5 broken.
  The same soft rounding plus soft-walled gouges made the worn shakes look
  like MELTED RUBBER in a close crop: on a short tile a lost chunk needs
  steep walls (the gouge ramp 0.1 instead of 0.35) and deeper grain ridges
  (x1.8). Crop the render at 2x before you call a surface done.
- v2.33 (engine): a roof-hole box cut to each shake's own width left thin
  pillars of roof between two narrower missing shakes (grey slabs in the
  hole, joined to the roof so the island cleanup can't take them). The box
  is 1.3x the tile width; the overlap hides under the neighbours.

- v2.34 (engine + assets): **damage faces the damage.** The tiles at a
  hole's LOWER edge were broken pieces nailed at the head: their straight
  head framed the hole and the tear pointed down the roof, away from it
  ("the damage faces the undamaged part"). A tall tile whose course-above
  neighbour (+1 pitch at the two stagger points) is missing is now torn at
  the head (`vm_dhead` 2, a `_U` piece placed at the butt, 22-60 % kept); a
  worn tile whose nearest damage (Proximity to the gap cloud) is above it
  gets the `_U` worn set. Check `v2.34(damage faces the hole)`.
- v2.34: **"plasticine" was interpenetration, not texture.** Worn shakes
  curled from the head (`b_^2`), intact ones cupped down to the nail line
  and loose ones turned about their top edge: the hidden part rose up to
  8.5 mm through the course above, so the courses looked merged and
  morphed. Lifts only in the visible part (`_expo`), loose tall tiles pivot
  at the covered line (`Row Overlap` along the bounds). Measure it on the
  assets (the push-through check) - it never shows in a lineup.
- v2.34: **scaled pieces need real-metre weathering.** The broken shakes are
  made 1 m long and scaled to ~0.1-0.38 m. The v2.28 weathering in asset
  units became squashed blobs, and once converted to real metres the
  42 cm shake's gouges covered a whole 17 cm piece, stacked deeper than
  the wood (the front collapsed into flaps). Scale gouge count and length
  with the real span, take the deepest gouge (not the sum), and skip
  gouges on short crisp pieces - render ONE piece large in plain grey
  (`scripts/one_tile.py -- out.png make_broken_shakes:B_01_UL:0.17 grey`) to see
  shading artefacts the texture hides.
- v2.34: **wood tears along the grain.** A random zigzag (`_jag`), worn
  round, read as torn clay. `_wood_tear`: fibre bundles 6-28 mm wide break
  at different lengths with slanted or pointed ends (square steps read as
  battlements) and the odd long splinter; `crisp=True` keeps tears sharp
  (no extra rounding at an end or a break, fray x0.4).
- v2.35 (engine): **the sides too.** After "below" was fixed the user saw
  the tiles beside a hole: broken short at the butt, a straight side framing
  the hole. Every direction round a hole needs its own piece facing it -
  above (butt torn), below (head torn), beside (side broken). The engine
  keeps the per-side rim tests separately (`side_t`) and stores `vm_dsid`.
- v2.35: **a fracture is not noise on a line.** Midpoint displacement at
  full roughness on every scale reads as torn paper / a saw; a brittle
  break is a few straight-ish facets at angles with fine roughness (calm the
  displacement below ~3 cm). Measure, don't eyeball: the share of the break
  length in straight runs >= 2 cm went 0.80-0.86 -> 0.03-0.05.
- v2.35: **validate only what you changed.** `_poly_ok(..., only=(i0, i1))`
  tests just the new edges, so one tight spot already in an outline (a slit)
  cannot veto every later fracture. Crack holes the fracture brings near the
  outline are dropped. When MEASURING outlines from a built mesh, trace them
  from the side-wall quads (front and back vertex at the same x, z: the warp
  lifts the back too, so "lowest y" misses parts) and break runs at jumps -
  a broken trace closed into one long fake edge and looked like a 20 cm
  straight cut.
- v2.36 (engine): **clean the hole on the FINAL categories.** A lone-tile
  pass on the first damage pattern is undone by the rules after it (the
  torn rim, head and side tears turn the neighbours of a whole tile into
  broken pieces). `tall_iso` runs on `vm_dcat0` (so the rim sees the
  cleared tiles) AND on the final `vm_dcat` (whole tiles: >= 2 holding
  neighbours; broken pieces: >= 1). Holding = intact or worn - a loose
  tile slides and holds nothing.
- v2.36: **removing a tile must cut the roof under it.** The roof face is
  only cut under missing tiles deep in the damage (`rf_sel`); everywhere
  else the lapped tiles hide it. Clear a tile, or tear the head off the one
  below a missing tile, and the flat grey roof face shows. `vm_diso` (tiles
  the FIRST pass cleared) and `rf_unc` (a tile missing before the final
  pass whose course below is missing / head-torn) add those boxes. Never
  cut under a tile the FINAL pass cleared: the tears round it are already
  decided, and the new hole opened over tiles torn at the butt (the
  `v2.34(damage faces the hole)` check caught it; re-deciding the tears
  afterwards broke three other checks).
- v2.36: **a check must fail on the old code.** The first `v2.36(no lone
  tiles)` passed on v2.35 too: the culprits were broken pieces in the
  middle of the hole, not intact tiles, and the stagger put the probe on
  the joint between the two tiles above (test both halves). Run the new
  check without `rebuild` (old nodes) before trusting it: v2.35 11 / 13
  lone, v2.36 0 / 0.
- v2.36 (engine): **the stagger hides a side edge from a butt test.**
  Along a hole's left / right edge every other tile has the hole under ONE
  stagger half of its butt; the rim rule "a missing tile under the butt ->
  torn at the butt" fired there, so the whole side edge showed damage
  pointing down the roof. Test the two halves separately (`blw_`): both ->
  butt tear (top edge), one -> side-broken on that side (`sd_l` / `sd_r`),
  including tiles the damage had already broken. The user found it only
  by drawing arrows on a render - a per-direction check (`v2.36(sides face
  the hole)`) has to classify each tile by WHERE the hole is relative to it.

## Scale probe (v2.29)
See the `scale_probe` results in `../vm-new-building-part/SCALE_STATUS.md`.
