---
name: vm-asset-yard
description: Make a new ASSET SET for the VM engine's Yard - the props and growth hugging an (abandoned) house - VM_Yard_Wall (barrels, crates, ladders stood against the walls), VM_Yard_Clutter (tyres, logs, branches dropped at the foot), VM_Yard_Plants (weeds, nettles, ferns, rank grass) and VM_Yard_Shrubs (bushes). Use when the user wants other yard objects or plants (a farm yard, a desert shack, a snowy cabin, a junk yard), more variety, or Poly Haven / Sketchfab props brought into the yard.
---

# Yard asset sets (props and growth round the house)

Shared rules and the build/test loop are in `../vm-new-building-part/WORKFLOW.md`.

**Status (v2.30): verified, scale-safe** (v2.30 `world_shape`: props never stretched by an unapplied object scale). The `v2.29(yard)` check passes: none inside the
building, on a door's path, or on or under the porch; Yard off places none. The probe
results at four scales are in `../vm-new-building-part/SCALE_STATUS.md`. The user's
look target: "nature that has started to grow around the house since its abandoned,
slowly absorbing it", with old wooden barrels and boxes **touching the house**. No trees,
lawn or rocks.

## How the engine uses a set
- Panel **Yard** on `VM_SceneDetailer_Windows`.
  - Sockets: `Yard` (bool), `Yard Seed`, `Yard Width` 1.2, `Clutter Amount`,
    `Plant Amount`, and the four collection sockets
    `Yard Wall / Clutter / Plant / Shrub Props`.
  - The collection sockets are wired in `AUTO_COLLECTIONS` to `VM_Yard_Wall` / `_Clutter` /
    `_Plants` / `_Shrubs`.
  - v2.36: in the shipped core library these four are EMPTY (yard on, nothing
    placed). The Poly Haven CC0 set is the EXAMPLE yard in the optional
    `VM_ExampleAssets.blend`. A new yard set: CC0 / own models only, recorded in
    `SOURCE.txt` per asset; add it to `split_library.py` (`EXAMPLE_COLS`,
    `CREDITS`) and `CREDITS.md`, or ship it as the user's own collections.
- Points come from the footprint: the boundary edges of the bottom faces. One
  `yd_set(...)` call per set, **in this order** (what goes first claims the room):
  Wall, then Clutter, then Shrubs, then Plants (close band), then Plants (outer band).
  - Arguments: spacing, the distance band from the wall (d_lo..d_hi), share,
    the amount socket, clearance round each one, the scale range, sink, whether it
    faces along the wall, the seed offset, `far_pow`, `plant_`, `crowd_` and
    `cluster_`.
  - `cluster_` sets (Wall, Clutter) only appear where a shared noise (scale 0.55,
    Fac > 0.53) is high, so barrels gather in the same spots.
- Exclusions:
  - trims and porch: plants keep 0.12 m from them, everything else 0.35 m;
  - under the porch or balcony: raycasts 1.2 m up from ground + 2 cm, plus one 30 cm
    further out;
  - door lanes: doors are `vm_openmark`, tall, and their bottom is within 0.3 m of the
    ground; the lane is |along| < 3.5 and lateral < 1.25 + clear/2;
  - earlier sets: plants keep 0.4 × their clearance, `crowd_` sets keep crowd × their
    clearance, everything else the full clearance.
- **Sizes are world metres.** The variant's real size is what shows, scaled by the
  per-set scale range (about 0.9–1.8).

## The asset contract (every variant)
- One mesh object `Yard_<assetid>[_<tag>][_NN]`, transforms applied, **centred
  on X/Y, ground at z = 0 as authored**. Roots and buried parts may go below 0.
  - "flat" mode lays a prop on its side and sets it on the ground.
  - Real-world size, after the per-asset scale in `YARD_SETS`. Scans of seedlings
    get scaled up: nettle ×2, weed ×2.2.
- No preview spheres, no exact duplicates, no slivers (under 25 % of the asset's
  biggest piece), and the lowest LOD only.
- Textures go through `_shrink_images`: colour maps ≤ 2k and the others 1k, as JPEG
  (PNG only for alpha or mask maps). The library grew from 128 to 243 MB with
  today's sets. **Watch the size.**
- Alpha-cut plants (grass cards) need the material's alpha kept: PNG plus blend
  or alpha-clip.

## Making a new set
1. **Reference:** ask the user what kind of yard (an image if possible). Agree
   the list: which objects stand against the walls, which lie at their foot, and
   what grows.
2. **Find assets.** Poly Haven first (CC0, real scans; use the `.blend` download).
   - For each asset: `~/Documents/ViperMeshAssets/props/yard/<id>/` with
     `SOURCE.txt` (URL, CC0, date). Each download goes in its own new, empty
     directory.
   - Sketchfab and other sites that need a login: give the user the links and let
     them download.
   - Check the licence (CC0 or CC-BY with credit in `SOURCE.txt`).
3. **Declare** it in a new `YARD_SETS`-style tuple. Each entry is
   `(asset id, object-name regex filter, mode merge|each|flat, scale)`.
   - For a themed variant, add new collection names (`VM_Yard_Wall_<Theme>`, …)
     and let `make_yard_props` build them. Generalise it to take the sets tuple as
     an argument if needed. Call it next to the existing `make_yard_props(yard_parent, ...)`.
   - Use `_join_yard` for merging. A plain `bpy.ops.object.join` fails with
     "not in View Layer".
4. **Wire** it through a library preset that sets the four Yard collection sockets
   (see the `vm-asset-cladding` step 5) plus Yard on.
5. **Check** in the probe and a render:
   - counts per set > 0 on each side;
   - none inside the footprint;
   - none further out than Yard Width + 0.6 m;
   - none on the porch;
   - variants actually used (all of them, over a few seeds).

   Run `build/yard_count_probe.py` for per-set counts and sides with the porch off
   and on.
6. **Look:** render from a few metres back (the user asked for "slightly further
   away" shots). The props should touch the walls and the growth should crowd the
   foundation, the corners and the porch posts.

## Lessons (append; newest last)
- Plants kept a whole prop's clearance and the yard looked sparse. The `plant_`
  and `crowd_` shares fixed that.
- Bushes placed first crowded out the barrels. Wall props go first now.
- Props spread evenly looked fake. Clusters fixed that.
- Ground-floor windows were taken for doors until the door test required a
  bottom within 0.3 m of the ground.
- The porch check never found the deck: `vm_trim` is a POINT attribute, so average
  it per face. Plants under the deck needed the up-raycasts. The deck boards stop
  12 cm short of the wall, hence the second ray 30 cm further out.
