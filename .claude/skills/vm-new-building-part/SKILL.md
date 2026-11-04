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
| Wall siding, roof shakes and their damage pools | `vm-asset-cladding` | mature (v2.4 world-space checks, v2.28 damage) |
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
