# VM Scene Detailer

Procedural architecture engine for Blender (Geometry Nodes). One node-group stack
that dresses any base mesh with cladding courses, fitted parts (doors/windows),
and per-zone surface materials — plus `VM_RoofCap`, a procedural pitched-roof
generator. Built to be **pack-agnostic**: any glTF asset pack goes through
`pack_ingest.py` and comes out engine-ready, no per-style code.

## Contents

| file | what |
|---|---|
| `build_engine.py` | deterministic generator — builds both node groups, demo scenes, runs the verification suite, renders previews |
| `pack_ingest.py` | generic pack adapter: classifies (flat slab / tile / prop), normalizes origins+scale, quarantines ajar/multi-part meshes, emits ready collections + JSON report |
| `VM_Tools_Addon.py` | one-click "Toggle All Modifiers" (clean-view button for the modifier tab) |
| `USAGE.txt` | GUI run-book (panels, sockets, asset prep rules, reference numbers) |
| `verification_v2.json` | numeric proof log (45 checks) |
| `preview_*.png` | rendered proofs |

Blends (`VM_SceneDetailer.blend`, `VM_Starter.blend`, `VM_RoofCap.blend`) are NOT
in the repo (100MB+ build outputs, textures packed in). Rebuild them with:

```
blender -b --python build_engine.py
```

A prebuilt copy lives at `C:\Users\krist\Downloads\blender-engine\` (deliverable
mirror; sources here are canonical).

## Conventions

- Deterministic: fixed seeds, same output every run.
- All textures packed into delivered blends (Windows-safe).
- Asset packs: one object per variant, real-world scale, transforms applied —
  or just run `pack_ingest.py` and let it enforce that.
- Verification is mandatory and two-sided: numeric checks AND rendered previews
  inspected visually (numbers alone miss float/gap defects).

## Versioning

Every version bump = a git tag + a GitHub release on this repo. Current:
**v2.6** (openings fit any wall height, Flat roof style with subtle incline,
manual painted placement + Exact Count. v2.5 = slot placement math; v2.4 =
shape robustness; v2.3 = pack adapter; v2.2 = engine v2 base).

## Roadmap

- v2.2 (in flight): pack adapter, ajar-door quarantine, windows layer on the starter.
- Native "disable all modifiers" control inside the engine UI (single point of
  control at the top of the stack).
