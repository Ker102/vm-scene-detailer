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
| `VM_Tools_Addon.py` | the Blender add-on: Import / Update Engine, Dress Object, presets, Copy / Paste Setup, Add Damage Zone, Add Example Assets, Check for Updates |
| `split_library.py` | splits the built library into the core `VM_Assets.blend` and the optional `VM_ExampleAssets.blend` |
| `USAGE.txt` | GUI run-book (panels, sockets, asset prep rules, reference numbers) |
| `CREDITS.md` | credits and licences of the example assets |

## Install

From the [latest release](https://github.com/Ker102/vm-scene-detailer/releases/latest):

1. `VM_Tools_Addon.py`: Blender > Edit > Preferences > Add-ons > Install from Disk.
2. `VM_Assets.blend`: the engine library. Set its path in the add-on preferences
   (or let **Check for Updates** in the VM panel download it).
3. Optional: `VM_ExampleAssets.blend`, see below.

Then in any file: VM panel (3D Viewport > N > VM) > **Import Engine**, select a mesh,
**Dress Object**.

## Example assets (optional)

The engine ships no doors, windows or yard props of its own. In `VM_Assets.blend` the
collections `VM_Doors`, `VM_DoorHandles`, `VM_Windows` and `VM_Yard_*` are empty: put
your own objects in them (or ingest a pack with `pack_ingest.py`). Until you do, walls
stay closed and the yard stays empty.

The doors, windows and yard of the demo builds are in `VM_ExampleAssets.blend`. Put it
next to `VM_Assets.blend` (or tick **Include example assets** so Check for Updates
downloads it), then click **Add Example Assets** in the VM panel. They are third-party
assets under CC-BY 4.0 and CC0: see [CREDITS.md](CREDITS.md) and credit the CC-BY authors
when you share work that shows them.

## Building

The blends are NOT in the repo (build outputs, textures packed in). Rebuild them with:

```
blender -b --python build_engine.py
```

The build reads its source assets from `VM_ASSET_SRC` (default `~/Documents/ViperMeshAssets`),
writes to `build/` and copies the deliverables to `VM_DELIVER` (default
`~/Downloads/blender-engine`).

## Conventions

- Deterministic: fixed seeds, same output every run.
- All textures packed into delivered blends (Windows-safe).
- Asset packs: one object per variant, real-world scale, transforms applied —
  or just run `pack_ingest.py` and let it enforce that.
- Verification is mandatory and two-sided: numeric checks AND rendered previews
  inspected visually (numbers alone miss float/gap defects).

## Versioning

Every version bump = a git tag + a GitHub release on this repo carrying the add-on,
the core library and the example assets (the add-on's Check for Updates reads it).
Current: **v2.36** (roof holes, asphalt roofs, sheathing and studs behind damaged
siding, yard, the add-on's update path; see the version notes at the top of
`USAGE.txt`). Roadmap tickets live in GitHub Issues.

## Roadmap

- v2.2 (in flight): pack adapter, ajar-door quarantine, windows layer on the starter.
- Native "disable all modifiers" control inside the engine UI (single point of
  control at the top of the stack).
