"""Test the add-on's Import / Update Engine on a real dressed file (never saves it).
  blender -b <dressed.blend> --python .claude/skills/vm-new-building-part/scripts/update_test.py -- lib:<VM_Assets.blend> [relabel]
Pass expect:<json file of {house: instances}> to compare with the same houses dressed fresh.
Without `relabel` the file should hold an OLDER engine (e.g. the v2.30 manual-test backup):
the update must finish in minutes, keep every modifier value it had, bring the new pools
(one AssetLibrary root, no '.001' copies beyond the library's own names), keep a user
object added to VM_Doors, fill only the NEW default slots, and a second import is a no-op.
With `relabel` the file holds the CURRENT engine, relabelled as old: every asset is
swapped for the library's copy and each house must evaluate to exactly the same
instance count and every datablock name must come back (the swap changes nothing).
v2.36 lesson: per-ID remove() and remapping one AssetLibrary root onto the other hung
the update for 14 h on the v2.30 test file; the merge is now one remap per pair + one batch_remove."""
import bpy, os, sys, re, time, importlib.util, collections
HERE = r"C:\Users\krist\Desktop\main-projects\Projects\vm-scene-detailer"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
LIB = next((a[4:] for a in ARGS if a.startswith("lib:")),
           os.path.expanduser(os.path.join("~", "Downloads", "blender-engine", "VM_Assets.blend")))
spec = importlib.util.spec_from_file_location("VM_Tools_Addon", os.path.join(HERE, "VM_Tools_Addon.py"))
vmt = importlib.util.module_from_spec(spec); sys.modules["VM_Tools_Addon"] = vmt; spec.loader.exec_module(vmt)
vmt.register(); vmt.LIBRARY_PATH_OVERRIDE = LIB
FAILS = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name, detail, flush=True)
    if not ok:
        FAILS.append(name)


def counts():
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    return dict(collections.Counter(i.parent.original.name for i in dg.object_instances
                                    if i.is_instance and i.parent is not None))


def names():
    return {k: sorted(d.name for d in getattr(bpy.data, k)) for k in vmt.DEDUPE_KINDS}


def lib_names():
    out = set()
    with bpy.data.libraries.load(LIB, link=False) as (src, _dst):
        for k in vmt.DEDUPE_KINDS:
            out |= set(getattr(src, k))
    return out


houses = [o for o in bpy.context.scene.objects if vmt.vm_modifiers(o)]
pre = {d.name for k in vmt.DEDUPE_KINDS for d in getattr(bpy.data, k)}    # the file's own names
snap0 = {o.name: vmt.snapshot_object(o) for o in houses}
if "relabel" in ARGS:
    c0, n0 = counts(), names()
    for g in vmt.VM_GROUPS:
        vmt.find_input(vmt.resolve_group(g), "Engine Version").default_value = "v0.0"
        vmt.sync_version_labels(vmt.resolve_group(g))
else:
    door = bpy.data.objects.new("MyOwnDoor", bpy.data.meshes.new("MyOwnDoorMesh"))
    bpy.data.collections["VM_Doors"].objects.link(door)
old_v = vmt.file_engine_version()
t = time.time(); rep = vmt.import_engine(LIB, []); dt = time.time() - t
print("REPORT", rep, flush=True)
check("update finishes in minutes", dt < 900, f"{old_v} -> {vmt.file_engine_version()} in {dt:.0f}s")
check("engine is the library's", vmt.file_engine_version() == vmt.library_info(LIB).get("engine_version"))
kept = all(v == {x["name"]: x for x in vmt.snapshot_object(bpy.data.objects[ob])}[m["name"]]["values"].get(k)
           for ob, mods in snap0.items() for m in mods for k, v in m["values"].items()
           if v[0] not in ("Engine Version", "Usage Hint"))
check("every modifier keeps the values it had", kept)
roots = [c.name for c in bpy.data.collections if c.name.startswith(vmt.LIBRARY_COLLECTION)]
check("one AssetLibrary root, in the scene", roots == [vmt.LIBRARY_COLLECTION]
      and bpy.context.scene.collection.children.get(vmt.LIBRARY_COLLECTION) is not None, roots)
ln = lib_names()
extra = [d.name for k in vmt.DEDUPE_KINDS for d in getattr(bpy.data, k)
         if re.search(r"\.\d{3}$", d.name) and d.name not in ln and d.name not in pre
         and not d.name.startswith("Cube")]
check("no new '.001' copies (beyond the library's and the file's own names)", not extra, extra[:8])
if not "relabel" in ARGS:     # v2.37: the core library has no examples - the file's own must stay
    ex = {c: len(bpy.data.collections[c].all_objects) for c in ("VM_Doors", "VM_Windows", "VM_Yard")
          if bpy.data.collections.get(c) is not None}
    check("the file's doors / windows / yard stay after the update", all(ex.values()) and len(ex) == 3, ex)
if "relabel" in ARGS:
    c1, n1 = counts(), names()
    check("swap changes nothing: same instances per house", c0 == c1,
          {k: (c0.get(k), c1.get(k)) for k in set(c0) | set(c1) if c0.get(k) != c1.get(k)})
    check("swap changes nothing: same datablock names", n0 == n1)
else:
    check("the user's own object in VM_Doors survives", door.name in bpy.data.collections["VM_Doors"].objects)
    empty_new = [(o.name, m.name) for o in houses for m in vmt.vm_modifiers(o) if m.name == "VM_SceneDetailer_Windows"
                 and getattr(m.properties.inputs, vmt.find_input(m.node_group, "Batten Props").identifier).value is None]
    check("new default slots filled (Batten Props)", not empty_new, empty_new[:3])
    bpy.data.collections["VM_Doors"].objects.unlink(door)     # it would change the door pool
    c_ = counts()
    print("COUNTS", c_, flush=True)
    exp = next((a[7:] for a in ARGS if a.startswith("expect:")), None)    # expect:<json of counts>
    if exp:
        import json
        want = json.loads(open(exp).read())
        check("each house = the same house dressed fresh on the new engine",
              all(c_.get(k) == v for k, v in want.items()),
              {k: (c_.get(k), v) for k, v in want.items() if c_.get(k) != v})
t = time.time(); rep2 = vmt.import_engine(LIB, [])
check("a second import is a no-op", rep2 == [] and time.time() - t < 30, rep2)
print("UPDATE TEST", "OK" if not FAILS else f"{len(FAILS)} FAILED", flush=True)
os._exit(0)
