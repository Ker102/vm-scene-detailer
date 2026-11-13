---
name: vm-new-building-part
description: Add a NEW building part, variable, node, socket or modifier layer to the VM_SceneDetailer / VM_RoofCap Geometry Nodes engine (a new object such as shutters, chimneys, gutters, steps or fences, or a new behaviour of an existing part). Use when the user asks for something the house does not have yet, sends a reference image of a part, or asks to make a part "look like this". It covers reference-first design, where the part plugs in, the builder idiom, checks, the scale probe, the look pass and delivery. For a new ASSET SET for a part that already exists, use the matching vm-asset-* skill instead.
---

# Adding a new building part

Read `WORKFLOW.md` (next to this file) first. It holds the user's standing
rules, the edit, test and build loop, and delivery. This skill is the order of
work that kept the last parts (v2.11–v2.29) from needing repeated fix rounds.

## The parts and their skills
| Part | Skill | Maturity |
|---|---|---|
| Wall siding, roof shakes / asphalt and their damage pools | `vm-asset-cladding` | mature (v2.4 world-space checks, v2.28 damage, v2.32 asphalt) |
| The roof frame under a hole (battens / deck, rafters, shards) | `vm-asset-cladding` (section "roof frame") | new in v2.32, world-space checked |
| Doors and windows (ingest, fit, cut, glass) | `vm-asset-openings` | mature (v2.6–v2.18) |
| Sheathing and studs behind the damage | `vm-asset-sheathing` | new, scale-safe since v2.30 |
| Yard props and growth | `vm-asset-yard` | new, scale-safe since v2.30 |
| Ivy / vines (procedural, `VM_VineLeaf` material) | none yet | works; no asset set (leaf cards are generated) |
| Porch, balcony, railings, dormers (procedural, `VM_RoofCap`) | none yet | works; the railings are one box kit (RAIL_STYLES) |

Before you write a skill for a part that has none, run the scale probe on it
(`scripts/scale_probe.py`) and fix what it finds. The user's bar: "when scaling
the building there is no bugs with it in different cases". `SCALE_STATUS.md`
holds the latest probe numbers per part.

## 0. Reference first: ask, don't guess
Before any code, make sure you know **what it looks like and where it goes**:
- If the user sent an image, describe back what you see in it: the part, its
  scale in metres, where it attaches, how it repeats, how it weathers, and
  what is *not* wanted. Confirm that with them.
- If there is no image, or it is ambiguous (where on the wall, how many, which
  style), **ask the user for a reference image** or a quick sketch or screenshot.
  They have said they will clarify with images, and one image saves a build round.
- Write the outcome down as a short spec: shape, size range, placement rule,
  counts, the cases it must survive (tiny, large, tower, unapplied scale,
  porch or balcony on, damage on), and what it must never do (float, sit
  in an opening, stand on the porch, block a door).

## 1. Decide where it lives
| The part is… | Put it in | Pattern to copy |
|---|---|---|
| A repeated tile on a surface (cladding, sheathing, roof covering) | `VM_SceneDetailer` course layout and a new tile pool | `vm-asset-cladding`, `vm-asset-sheathing` |
| One fitted object per wall slot (opening, shutter, lamp) | Fit layout on a `VM_SceneDetailer_*` layer | `vm-asset-openings` |
| Something generated *from the massing* (roof, porch, balcony, dormer, chimney) | `build_roofcap_group()` (`add_porch`, `add_dormers`) | the porch and balcony code |
| Something round the building (props, growth, fences) | the Yard section of the Windows layer | `vm-asset-yard` |
| A look-only change (weathering, colour) | the materials / `make_board_material` | n/a |

Prefer extending an existing layer and panel over adding a modifier. The add-on's
`dress_stack()` and the presets must know about every new modifier.

## 2. Assets before nodes
Define the asset **contract** first: local frame, origin, real-world size,
naming `_01.._NN`, material and UVs, and mesh attributes. Then build or ingest
2–3 variants and look at them on their own. Write the contract into a new
`vm-asset-<part>` skill (copy the structure of `vm-asset-cladding`).
- Asset generators are plain functions `make_<part>(col, name, n, mat, ..., seed=)`
  next to the others in `build_engine.py`. They are deterministic (seeded `random.Random`),
  give world-metre sizes, and use the frame **X along, Z up, +Y out of the
  surface**, with the back plane at a fixed small negative y.
- Downloaded assets go through a normaliser (`pack_ingest.py` for wall-flat
  parts, `make_yard_props` for free-standing props). Never place raw imports.

## 3. Nodes
- Sockets go **after** the existing ones, in a panel named for the part, with
  a `desc=` that says what it does in the user's words. Collection sockets get
  wired in the add-on's `AUTO_COLLECTIONS`, materials in `AUTO_MATERIALS`.
- Every distance is world metres. Sample in object space with `em("DIVIDE", d, geo_f)`.
- Exclusion zones learnt the hard way. Test all of them for anything placed near the walls:
  openings (`open_cut_at`, the `o_real` cutter boxes, `c_open`), the porch and
  balcony (`c_trims`, with raycasts up from the ground and one 30 cm further out),
  door lanes, eaves (keep upward rays short, ~1.2 m), corners, and the damage
  pattern (`gap_at`).
- Default it OFF (bool socket) unless the user asked for it in every house. Add it
  to the right preset in the library section (`lib_presets`) and to the add-on's
  `dress_stack()` defaults if it belongs in Dress.

## 4. Checks (in `main()` of `build_engine.py`)
Add `check("vX.YY(<part>): <claim in words>", cond, detail)` cases that measure
the *failure modes from step 0*, in world space, on a fresh dressed house
(the add-on path), not on the demo stage. The detail string prints the
numbers you'd want when it fails. Count your new checks into the USAGE header.

## 5. Probe, look, iterate
1. Fast in-file test (WORKFLOW §Tests 1). Iterate on numbers.
   **Dry-run new checks before the full build:**
   `scripts/check_dryrun.py -- "from:<your block's first comment>" rebuild`
   runs just that block of `main()` against `build/VM_Assets.blend` (the last
   full build's library) in ~6 min. In v2.32 it caught two real bugs and one
   check bug that would each have cost a 50-min build.
2. Full build, then `scripts/scale_probe.py` and `scripts/look_shots.py` from the
   built library. Extend the probe's per-pool report if your part needs a
   new measure (copy the yard block).
3. Look at the renders. Compare them with the reference image and list what
   still differs, then fix it. Send the user the contact sheet and say what is
   still off.

## 6. Ship and record
Deliver (WORKFLOW), commit locally, ask before pushing. Then **update the
skills**: the new part's `vm-asset-*` skill (its contract and status) and the
"Lessons" list below if you learnt something general.

## Lessons (append; newest last)
- Courses and slots must come from world-space formulas. A 1.6× unapplied
  object scale stretched tiles until v2.4; the `world-space:` checks guard it.
- A check that never finds its subject passes silently. The v2.29 yard check
  did not see the porch because `vm_trim` is a POINT attribute. Make every check
  assert that its subject exists (count > 0) before it asserts the rule.
- "Not in an opening" needs the opening really *cut*. A window on closed wall
  hides nothing. Count only openings with no wall face at their centre.
- Spreading props evenly reads as fake. Cluster them (a shared noise mask) and
  let growth crowd the objects placed before it (the `crowd_` share).
- The order of placement matters: what goes first claims the room. Barrels go
  before bushes, and plants go last.
- Ground-floor windows look like doors to a "tall opening" test. A door's bottom is
  within 0.3 m of the ground.
- Background builds: `run_in_background`, never `&` inside a foreground call.
- v2.30: dividing an instance's scale by `geo_f` only works for a *uniform*
  object scale. The v2.29 yard, sheathing and studs were 1.6× stretched on a
  (1.6, 1, 1.3) house. **Make every new instance at its world size (scale 1 ×
  its own random scale) and pass the instances through `world_shape(geo)`**
  (T(p)·S⁻¹·T(-p)·M, exactly the identity unscaled). Lay any lattice or spacing
  in world metres along the surface (`ws["eff_of"](direction)`) and convert the
  offsets back to local units.
- Run `scripts/scale_probe.py -- rebuild` (about 30 min) before the 50-min full build.
  It caught the v2.30 bug that 275 green checks did not.
- v2.32: **store Index-based randoms before a Delete Geometry.** Fields keyed
  on Index are evaluated again after the delete, on shifted indices: the
  shards were tested at one spot and placed at another (13 of 30 floated).
  Store the random values and the position as attributes, delete, then read
  the stored ones.
- v2.32: `gap_at` (nearest damage marker's footprint) misses gaps between
  markers. To ask "is there a hole here?" raycast the actually cut surface
  (`c_bool`) instead.
- v2.32: a test that probes "below the top edge" must stop at the piece's
  own end: short broken stubs were held up by roof past their end. And a
  "taller than wide" filter for roof tiles drops the stubs - filter out
  ridge boards by width (< 0.5 m) instead.
- v2.32: `from x import y` inside `main()` makes `y` local to all of main;
  nested functions defined earlier that use the module's `y` then crash.
  Never re-import inside main().
- v2.32: **a "same graph" proof must include the link ORDER into multi-input
  sockets.** v2.31's chunked build matched the flat graph as a set of links
  but joined three Join Geometry nodes in another order (Blender's sort id for a
  new link = the links on the socket now, so removes + re-adds leave ties).
  That moved Index-keyed randoms: 58 % fewer ivy leaves on one probe house,
  a few planks and shakes. 279 green checks did not see it; the scale probe's
  per-pool counts did. After touching NGBuilder, run
  `scripts/flat_vs_chunk.py -- <a flat-built library> <source dir>` and compare
  `scale_probe` counts with the previous release's numbers.
- v2.32: realized geometry hides what a check needs to count. Tag the pieces
  with a small attribute before Realize (`vm_fpc`), it carries through.
- v2.33: **a boolean cut can strand scraps.** Where cut boxes ring a spot
  that got no box itself, a small island of the host stays standing inside
  the hole (a grey slab in a roof hole). After the cut, Mesh Island plus two
  Accumulate Field (Group ID = island): face area, and the faces from a hole
  box (`vm_cutter` 2). Delete islands that are small (< 0.3 m2 world: area x
  geo_f^2) AND were cut by a hole box. An island no box touched (a porch
  post) is a real part and stays.
- v2.33: **look at the asset before you blame the engine.** Render a pool
  lineup of fronts and print the attribute profile (`vm-asset-cladding`'s
  `scripts/attr_profile.py`), and colour the pools flat in the house shot
  (`poolcolors` in the fast test). The v2.32 "muddy roof" was three things:
  round gouge blobs on the asset, worn (whole-outline) tiles framing the
  hole, and a lineup that showed the tiles' backs.
- v2.33: **after an ENGINE_VERSION bump, in-file tests run the OLD nodes**
  unless the rebuilt groups carry the library's version label. The add-on's
  `import_engine` (called by Dress and Apply Preset) swaps any group whose
  version differs from the library's back to the library copy, silently.
  Three rounds of v2.33 node changes "did nothing" until a forced control
  (every tile broken) also did nothing. `check_dryrun.py` and the fast tests
  now set `be.ENGINE_VERSION` to the library's version before rebuilding.
  **When a change shows no effect, force it to an extreme first**: if the
  extreme does nothing too, the test isn't running your code.
- v2.34: **when the user says "merged / morphed / plasticine", look for
  interpenetration before texture.** Parts laid in one plane that overlap
  (roof courses, lap siding) hide each other only while every lift stays in
  the visible part; a curl under the covering course pushed through it.
  Measure it on the assets (max lift over the nominal surface where covered)
  and turn the number into a check - a render only shows "something soft".
- v2.34: **damage has a direction.** A broken or worn piece shows its damage
  on one side; pick that side from where the damage is (the neighbour that is
  missing, Proximity to the gap cloud), not a fixed side of the asset. Ship
  the asset in both orientations rather than flipping instances (a flip
  breaks a tapered or one-sided part).
- v2.35: **every direction, not just the one the user named.** "The damage
  faces the wrong way below the hole" was fixed for below; the next round
  was "and beside it". When a fix is directional, do all four sides (above,
  below, -X, +X) in the same release and make the check count each side.
- v2.35: **brittle vs fibrous breaks are different generators.** Wood tears
  in fibre bundles (`_wood_tear`) and splits along the grain; asphalt, slate,
  tile and glass break in a few angled facets with fine roughness
  (`_fracture_outline`). Turn "it looks like a straight cut" into a number
  (the share of the break length in straight runs) before tuning.
- v2.35: `scripts/check_dryrun.py -- "from:<block>" rebuild pools:all` runs a
  check block against node groups AND tile pools rebuilt from the working
  copy - asset changes no longer need a 47-min full build to test a check.
- v2.36: **a new check must FAIL on the old code first.** Run the dry run
  without `rebuild` (the library's old nodes) and with it: if both pass,
  the check measures the wrong thing. The v2.36 lone-tile check passed on
  v2.35 until it counted the broken pieces the user had actually seen.
- v2.36: **look at what you removed.** Clearing geometry exposes what was
  under it (the uncut roof face); render the close-up after every removal
  rule, not only the checks.
- v2.36: Import / Update Engine hung 14 h on the v2.30 manual-test scene: an old
  file lacking a newer pack collection made the import append a second
  AssetLibrary, and remapping one scene-linked root onto the other never returns.
  It also kept the OLD pools and left new sockets (Batten Props...) empty. Now
  `_merge_appended` keeps the library's assets on an update (one remap per pair,
  ONE `batch_remove`, roots never remapped) and `fill_new_slots` fills only the
  sockets the update added. After any add-on change to the import path run
  `scripts/update_test.py` on the v2.30 backup (with `expect:` counts of a fresh
  kit) and with `relabel` on a current dressed file - both must print UPDATE TEST OK.
  The build's addon(update) check never caught it: its file had every collection.
- Regenerate the manual-test scene with `scripts/variations.py -- norender
  lib:<delivered VM_Assets.blend> save:<path>` (back up the old file first).
  Rendering a file with camera markers: `frame_set(<marker frame>)`, not `sc.camera`.
- v2.36: releases reach users through the add-on's 'Check for Updates' (GitHub
  Releases of `UPDATE_REPO` = the public Ker102/vm-scene-detailer, assets `VM_Tools_Addon.py` + `VM_Assets.blend`
  + the optional `VM_ExampleAssets.blend`,
  tag = engine version). On every version bump set `ADDON_VERSION` and
  `bl_info["version"]` in the add-on to `ENGINE_VERSION`; `scripts/publish_release.py`
  refuses to publish when the four disagree (a stale ADDON_VERSION makes every
  user's Blender offer the same update forever). Publishing is public: only on
  the user's ask. Test the updater with `scripts/updater_test.py` (fake release
  server on 127.0.0.1, never GitHub); the threaded download and the panel only
  run in a real UI session - headless Blender runs no timers. An automatic
  check must never touch a status the user's own click set (it flipped a
  running download back to 'available' once).
- v2.36: the doors, windows and yard we build and test with are EXAMPLE assets,
  not the engine (the user's call: core ships no door / window models - bring
  your own; the examples are an opt-in, off by default). `split_library.py`
  (repo root, run by the build's delivery) makes the CORE `VM_Assets.blend` -
  same collection names, door / window / yard ones EMPTY so presets and sockets
  still resolve - and `VM_ExampleAssets.blend` (an `AssetLibrary` root of the
  same layout, objects tagged `vm_example`, a `VM_ExampleInfo` text with the
  credits and a content fingerprint). The add-on's 'Add Example Assets'
  appends that root and `_merge_appended(prefer_new=False)` pours it into the
  placeholders. Rules that came out of it:
  - a NEW part's own assets go in the core (engine-made or CC0 we may ship);
    a third-party model set is an example, never a core dependency, and the
    part must still work - visibly degrade, not break - with its collection
    empty (test: `scripts/examples_test.py`, full vs core vs core+examples
    must give identical instance counts per collection).
  - check every licence before anything ships: BlenderKit assets (the lamps and
    books in VM_Props_Library) may NOT be redistributed, so they are in
    neither file. Credits live in `CREDITS.md`, `VM_ExampleInfo` and the
    release notes (`publish_release.py` writes them).
  - imported .blends bring their materials with a FAKE USER: deleting the
    objects leaves the materials and their packed textures behind. The split
    drops non-`VM_` fake-user-only materials after a purge and asserts that
    every remaining image belongs to a `VM_` / `Debris_` material.
  - `build/stage` holds the CORE library now: the probes (`scale_probe.py`,
    `look_shots.py`, `variations.py`) add the examples next to it; the build's
    own checks still run on the full `build/VM_Assets.blend`.
  - a release re-uploads the previous example file while its fingerprint is
    unchanged (asset label `[<fp>]`), so the updater, which compares the sha256
    it recorded at install, does not offer the same 140 MB again.
