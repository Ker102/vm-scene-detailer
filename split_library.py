"""Split the full built library into the CORE library and the optional EXAMPLE assets.
  blender -b --factory-startup <full VM_Assets.blend> --python split_library.py -- <out_dir>
(build_engine.py runs it at delivery on build/stage/VM_Assets.blend -> build/split.)
Writes <out_dir>/VM_Assets.blend (core) and <out_dir>/VM_ExampleAssets.blend (examples).

CORE = the engine's own assets: node groups, presets, the procedural / CC0-textured tile and
debris pools. The example collections stay in it as EMPTY placeholders with the same names
(VM_Doors, VM_DoorHandles, VM_Windows, VM_Yard + VM_Yard_*), so every preset and modifier
socket still resolves; a core-only house has closed walls and an empty yard until the user
drops their own objects in (bring your own doors / windows / yard).
EXAMPLES = the objects of those collections (Sketchfab CC-BY doors and windows, Poly Haven
CC0 yard), under an 'AssetLibrary' root of the same layout, every object tagged
ob['vm_example'] = 1, plus a 'VM_ExampleInfo' text (engine_version, credits, collections and a
content 'fingerprint': publish_release.py re-uploads the previous release's example file while
the fingerprint is unchanged, so the updater does not offer the same 140 MB again).
The add-on's 'Add Example Assets' appends that root and merges it into the core placeholders.
Left out of both: the pack-ingest working collections (*_WALLFLAT / _TILE / _PROP /
_Quarantine), the unused legacy tile pools and VM_Props_Primary / VM_Props_Library (unused by
the engine; the lamps and books are BlenderKit assets, which may not be redistributed)."""
import bpy, os, sys, json, hashlib
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(ARGS[0] if ARGS else os.path.join(os.path.dirname(bpy.data.filepath), "split"))
os.makedirs(OUT, exist_ok=True)
CORE_PATH = os.path.join(OUT, "VM_Assets.blend")
EX_PATH = os.path.join(OUT, "VM_ExampleAssets.blend")
if os.path.normcase(CORE_PATH) == os.path.normcase(bpy.data.filepath):
    raise SystemExit("split_library: <out_dir> must not be the folder of the full library")

ROOT = "AssetLibrary"
EXAMPLE_COLS = ["VM_Doors", "VM_DoorHandles", "VM_Windows", "VM_Yard",
                "VM_Yard_Wall", "VM_Yard_Clutter", "VM_Yard_Plants", "VM_Yard_Shrubs"]
EXAMPLE_TOP = ["VM_Doors", "VM_DoorHandles", "VM_Windows", "VM_Yard"]     # children of the root
DROP_COLS = ["VM_Props_Primary", "VM_Props_Library", "VM_Tiles_PlankLegacy", "VM_Tiles_ShingleLegacy"]
INGEST_SUFFIXES = ("_WALLFLAT", "_TILE", "_PROP", "_Quarantine")
CREDITS = [
    dict(asset="Doors and door handles (VM_Doors, VM_DoorHandles)",
         title="Low-Poly PSX Style Worn Wooden Doors Pack", author="vanillao03",
         url="https://sketchfab.com/3d-models/low-poly-psx-style-worn-wooden-doors-pack-16dd7631d2e145ffacfc374961d71cf1",
         license="CC-BY-4.0"),
    dict(asset="Windows (VM_Windows: Window_01, Window_02)",
         title="Weathered Wooden Window | GameReady", author="Mark Peters",
         url="https://sketchfab.com/3d-models/weathered-wooden-window-gameready-c4256c1d2a0b49edb6a5aefcfe12593a",
         license="CC-BY-4.0"),
    dict(asset="Windows (VM_Windows: Window_03)",
         title="Broken Window 01", author="Game Ready Art",
         url="https://sketchfab.com/3d-models/broken-window-01-52ca73d422bc4c9e9dbfe9b1ce7e60f2",
         license="CC-BY-4.0"),
    dict(asset="Yard props and plants (VM_Yard_*)", title="Poly Haven models", author="Poly Haven",
         url="https://polyhaven.com/models", license="CC0-1.0"),
]

cols = bpy.data.collections
root = cols[ROOT]
missing = [c for c in EXAMPLE_COLS if c not in cols]
if missing:
    raise SystemExit(f"split_library: the library has no {missing}")
engine_version = json.loads(bpy.data.texts["VM_Presets"].as_string()).get("engine_version", "")
ex_objs = sorted({o for c in EXAMPLE_COLS for o in cols[c].all_objects}, key=lambda o: o.name)
for o in ex_objs:
    o["vm_example"] = 1
print(f"SPLIT {engine_version}: {len(ex_objs)} example objects")

# ---- 1. the example file: a second 'AssetLibrary' root holding the example collections,
#         written with libraries.write (the IDs + everything they use, packed images included)
root.name = ROOT + "_full"
ex_root = cols.new(ROOT)
for n in EXAMPLE_TOP:
    ex_root.children.link(cols[n])


def _fingerprint(objs):
    rows = []
    for o in objs:
        me = o.data
        mats = sorted(s.material.name for s in o.material_slots if s.material)
        imgs = sorted({(n.image.name, tuple(n.image.size)) for s in o.material_slots if s.material
                       and s.material.node_tree for n in s.material.node_tree.nodes
                       if n.type == "TEX_IMAGE" and n.image})
        rows.append([o.name, len(me.vertices) if me else 0, len(me.polygons) if me else 0,
                     [round(v, 4) for v in o.dimensions], mats, imgs,
                     sorted(c.name for c in o.users_collection if c.name in EXAMPLE_COLS)])
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()[:16]


info = dict(engine_version=engine_version, kind="VM example assets", fingerprint=_fingerprint(ex_objs),
            collections={n: sorted(o.name for o in cols[n].objects) for n in EXAMPLE_COLS},
            credits=CREDITS,
            note="Optional example doors, windows and yard for the VM engine. Add them with the "
                 "add-on's 'Add Example Assets' button. Credit the CC-BY authors wherever you share "
                 "work that shows them.")
txt = bpy.data.texts.new("VM_ExampleInfo")
txt.write(json.dumps(info, indent=1))
bpy.data.libraries.write(EX_PATH, {ex_root, txt}, fake_user=True, compress=True)
bpy.data.batch_remove([ex_root, txt])
root.name = ROOT
print("SPLIT wrote", EX_PATH, "%.1f MB" % (os.path.getsize(EX_PATH) / 1e6))

# ---- 2. the core file: empty the example collections, drop the rest, purge, save
drop = [c for c in cols if c.name in DROP_COLS or c.name.endswith(INGEST_SUFFIXES)]
gone = {o for c in drop for o in c.all_objects} | set(ex_objs)
gone = [o for o in gone if not any(c.name not in DROP_COLS and not c.name.endswith(INGEST_SUFFIXES)
                                   and c.name not in EXAMPLE_COLS for c in o.users_collection)]
KINDS = ("node_groups", "materials", "texts", "collections", "objects", "meshes", "images")
snap = {k: {i.name for i in getattr(bpy.data, k)} for k in KINDS}
print("SPLIT core drops", len(drop), "collections:", sorted(c.name for c in drop))
bpy.data.batch_remove(drop + gone)


def purge():
    for _ in range(3):
        bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)


purge()
# the BlenderKit lamp / book blends brought their materials with a fake user, so after the
# purge only that fake user holds them: drop every non-engine material kept by nothing else
stray = [m for m in bpy.data.materials if m.use_fake_user and m.users == 1 and not m.name.startswith("VM_")]
for m in stray:
    m.use_fake_user = False
print("SPLIT core drops fake-user leftovers", sorted(m.name for m in stray))
purge()
for k in KINDS:
    lost = sorted(snap[k] - {i.name for i in getattr(bpy.data, k)})
    print(f"SPLIT core removed {len(lost):4d} {k}", lost[:12] if k in ("node_groups", "materials", "texts", "collections") else "")
lost_ng = snap["node_groups"] - {i.name for i in bpy.data.node_groups}
assert not any(n.startswith(("VM_", ".VM_")) for n in lost_ng), sorted(lost_ng)
assert "VM_Presets" in bpy.data.texts
umap = bpy.data.user_map(subset=list(bpy.data.images))
foreign = sorted(i.name for i in bpy.data.images
                 if not any(isinstance(u, bpy.types.Material) and u.name.startswith(("VM_", "Debris_"))
                            for u in umap[i]))
print("SPLIT core images", len(bpy.data.images), sorted({i.name.rsplit("_", 1)[0] for i in bpy.data.images}))
assert not foreign, f"images the engine's materials do not use: {foreign}"
left = {c: len(cols[c].all_objects) for c in EXAMPLE_COLS}
assert not any(left.values()), left
bpy.ops.wm.save_as_mainfile(filepath=CORE_PATH, compress=True)
print("SPLIT wrote", CORE_PATH, "%.1f MB" % (os.path.getsize(CORE_PATH) / 1e6))
print("SPLIT core collections", [c.name for c in cols[ROOT].children])
print("SPLIT OK")
