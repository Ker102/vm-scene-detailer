"""Test the core / example split (split_library.py) through the add-on.
  blender -b --factory-startup --python examples_test.py -- <split_dir> <full VM_Assets.blend> <out.json>
Three fresh files, each with the same houses dressed (weathered gable + yard, an asphalt
roof): FULL = the full built library; CORE = the core library alone; CORE+EX = the core
library + 'Add Example Assets'. Checks: CORE dresses with no errors, closed walls (no
door / window / yard instances) but every engine pool still there; CORE+EX gives the same
instance counts per collection as FULL; a second 'Add Example Assets' is a no-op; the
example objects carry ob['vm_example']; the core file has no example datablocks.
Prints PASS / FAIL lines and EXAMPLES TEST OK."""
import bpy, os, sys, json, importlib.util, collections, bmesh, mathutils
HERE = r"C:\Users\krist\Desktop\main-projects\Projects\vm-scene-detailer"
ARGS = sys.argv[sys.argv.index("--") + 1:]
SPLIT, FULL, OUT = ARGS[0], ARGS[1], ARGS[2]
CORE, EX = os.path.join(SPLIT, "VM_Assets.blend"), os.path.join(SPLIT, "VM_ExampleAssets.blend")
spec = importlib.util.spec_from_file_location("VM_Tools_Addon", os.path.join(HERE, "VM_Tools_Addon.py"))
vmt = importlib.util.module_from_spec(spec); sys.modules["VM_Tools_Addon"] = vmt; spec.loader.exec_module(vmt)
os.environ["VM_EXAMPLES"] = EX
EXAMPLE_COLS = {"VM_Doors", "VM_DoorHandles", "VM_Windows", "VM_Yard_Wall", "VM_Yard_Clutter",
                "VM_Yard_Plants", "VM_Yard_Shrubs"}
FAILS = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name, detail, flush=True)
    if not ok:
        FAILS.append(name)


def house(name, x, preset, yard):
    sc = bpy.context.scene
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.LocRotScale((0, 0, 1.5), None, (8, 6, 3)))
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob); ob.location = (x, 0, 0)
    warn = []
    vmt.dress_object(ob, warn)
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    r = bpy.ops.vm.apply_preset(preset=preset)
    if yard:
        W = ob.modifiers["VM_SceneDetailer_Windows"]
        getattr(W.properties.inputs, vmt.find_input(W.node_group, "Yard").identifier).value = True
    return ob, warn, r


def counts():
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    out = collections.defaultdict(collections.Counter)
    for i in dg.object_instances:
        if i.is_instance and i.parent is not None:
            cols = i.object.original.users_collection
            out[i.parent.original.name][cols[0].name if cols else "?"] += 1
    return {k: dict(v) for k, v in out.items()}


def run(mode):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    vmt.register()
    vmt.LIBRARY_PATH_OVERRIDE = FULL if mode == "full" else CORE
    rep = vmt.import_engine(vmt.LIBRARY_PATH_OVERRIDE, [])
    print("IMPORT", mode, rep, flush=True)
    if mode == "core+ex":
        miss = vmt.examples_missing(EX)
        check("core file: every example object is missing before the import", len(miss) > 50, len(miss))
        r = bpy.ops.vm.import_examples()
        check("Add Example Assets runs", r == {'FINISHED'}, r)
        check("... and nothing is missing after it", vmt.examples_missing(EX) == [], vmt.examples_missing(EX)[:5])
        tagged = [o.name for o in bpy.data.objects if o.get("vm_example")]
        check("example objects carry vm_example", len(tagged) == 88, len(tagged))
        roots = [c.name for c in bpy.data.collections if c.name.startswith(vmt.LIBRARY_COLLECTION)]
        dup = [c.name for c in bpy.data.collections if c.name[-4:-3] == "." and c.name[-3:].isdigit()]
        check("one AssetLibrary root and no '.001' collections", roots == [vmt.LIBRARY_COLLECTION] and not dup, (roots, dup))
        n = len(bpy.data.objects)
        r2 = bpy.ops.vm.import_examples()
        check("a second Add Example Assets is a no-op", len(bpy.data.objects) == n, (r2, len(bpy.data.objects), n))
    if mode == "core":
        ex_objs = [o.name for c in EXAMPLE_COLS if bpy.data.collections.get(c)
                   for o in bpy.data.collections[c].all_objects]
        check("core: example collections exist but are empty",
              all(bpy.data.collections.get(c) is not None for c in EXAMPLE_COLS) and not ex_objs, ex_objs[:5])
        check("core: no BlenderKit / pack leftovers",
              not any(c.name.startswith(("VM_Props_", "WornWooden", "BrokenWindow", "Medieval", "Weathered"))
                      for c in bpy.data.collections))
    a, wa, ra = house("gable_yard", 0, "lib:Base - Weathered gable", True)
    b, wb, rb = house("asphalt", 30, "lib:Base - Weathered gable", False)
    check(f"{mode}: dress + preset run without warnings", ra == rb == {'FINISHED'} and not (wa or wb), (ra, rb, wa, wb))
    c = counts()
    ev = a.evaluated_get(bpy.context.evaluated_depsgraph_get())
    print("COUNTS", mode, json.dumps(c), "faces", len(ev.data.polygons), flush=True)
    return c, len(ev.data.polygons)


res = {m: run(m) for m in ("full", "core", "core+ex")}
full, core, both = (res[m][0] for m in ("full", "core", "core+ex"))
for h in full:
    f_ex = {k: v for k, v in full[h].items() if k in EXAMPLE_COLS}
    c_ex = {k: v for k, v in core.get(h, {}).items() if k in EXAMPLE_COLS}
    rest_f = {k: v for k, v in full[h].items() if k not in EXAMPLE_COLS}
    rest_c = {k: v for k, v in core.get(h, {}).items() if k not in EXAMPLE_COLS}
    check(f"{h}: the full library places example assets", sum(f_ex.values()) > 0, f_ex)
    check(f"{h}: core places none of them", not c_ex, c_ex)
    check(f"{h}: core keeps the engine's own pools", sum(rest_c.values()) > 0.5 * sum(rest_f.values()),
          (sum(rest_c.values()), sum(rest_f.values())))
    check(f"{h}: core + examples == full, per collection", both.get(h) == full[h],
          {k: (full[h].get(k), both.get(h, {}).get(k)) for k in set(full[h]) | set(both.get(h, {}))
           if full[h].get(k) != both.get(h, {}).get(k)})
check("core + examples: same wall mesh as full (openings cut)", res["core+ex"][1] == res["full"][1],
      (res["core+ex"][1], res["full"][1], res["core"][1]))
json.dump({m: res[m][0] for m in res}, open(OUT, "w"), indent=1)
print("EXAMPLES TEST", "OK" if not FAILS else f"{len(FAILS)} FAILED", flush=True)
os._exit(0)
