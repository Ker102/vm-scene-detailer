"""Scale-robustness probe from the BUILT library (build/stage/VM_Assets.blend):
odd-sized houses dressed with every part on (gable, porch, balcony, whole
damage, vines, yard), each part measured in WORLD space.
  blender -b --factory-startup --python .claude/skills/vm-new-building-part/scripts/scale_probe.py -- [render] [rebuild] [samples:N]
Per case and pool: count, floating (origin > 12 cm from the evaluated house),
world scale range (min / max axis scale and anisotropy), yard props inside the
footprint or further out than Yard Width + 0.6. With `render`, one corner shot
per case -> build/scale_probe_<case>.png. With `rebuild`,
the node groups come from the working copy of build_engine.py (minutes, no full build)."""
import bpy, bmesh, sys, os, math, time, importlib.util, mathutils
import builtins, functools
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
builtins.print = functools.partial(builtins.print, flush=True)
HERE = r"C:\Users\krist\Desktop\main-projects\Projects\vm-scene-detailer"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
RENDER = "render" in ARGS
SAMPLES = next((int(a[8:]) for a in ARGS if a.startswith("samples:")), 16)
T0 = time.time()
spec = importlib.util.spec_from_file_location("VM_Tools_Addon", os.path.join(HERE, "VM_Tools_Addon.py"))
vmt = importlib.util.module_from_spec(spec); sys.modules["VM_Tools_Addon"] = vmt; spec.loader.exec_module(vmt)
bpy.ops.wm.read_factory_settings(use_empty=True)
vmt.register(); vmt.LIBRARY_PATH_OVERRIDE = os.path.join(HERE, "build", "stage", "VM_Assets.blend")
vmt.import_engine(vmt.LIBRARY_PATH_OVERRIDE, [])
if "rebuild" in ARGS:       # the node groups rebuilt from the working copy of build_engine.py
    sys.path.insert(0, HERE)
    import build_engine as be
    for nm_, fn_ in (("VM_SceneDetailer", be.build_node_group), ("VM_RoofCap", be.build_roofcap_group)):
        old_ = bpy.data.node_groups[nm_]; new_ = fn_()
        old_.user_remap(new_); bpy.data.node_groups.remove(old_); new_.name = nm_
    print(f"GROUPS REBUILT {time.time() - T0:.0f}s")
sc = bpy.context.scene
W = "VM_SceneDetailer_Windows"
YARD_W = 1.2


def setv(ob, mod, name, val):
    m = ob.modifiers[mod]; it = vmt.find_input(m.node_group, name)
    if it is None:
        raise KeyError(f"{mod}: no socket {name!r}")
    getattr(m.properties.inputs, it.identifier).value = val


# (name, mesh size x/y/h, unapplied object scale)
CASES = [("tiny", (3.6, 2.8, 2.5), (1, 1, 1)),
         ("big", (16, 10, 6.5), (1, 1, 1)),
         ("tower", (4.2, 4.2, 9.0), (1, 1, 1)),
         ("objscale", (5, 4, 2.4), (1.6, 1.0, 1.3))]
POOLS = {}
for c in bpy.data.collections:
    if c.name.startswith(("VM_Tiles_", "VM_Yard_")) or c.name in ("VM_Windows", "VM_Doors"):
        for o in c.all_objects:
            POOLS.setdefault(o.name, c.name)
built = []
for k, (name, size, oscale) in enumerate(CASES):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.LocRotScale((0, 0, size[2] / 2), None, size))
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    ob.location = (k * 80.0, 0, 0); ob.scale = oscale
    bpy.context.view_layer.update()
    vmt.dress_object(ob, [])
    setv(ob, "VM_RoofCap", "Style", "Gable"); setv(ob, "VM_RoofCap", "Pitch", math.radians(45))
    setv(ob, "VM_RoofCap", "Porch", True); setv(ob, "VM_RoofCap", "Balcony", True)
    for mn in ("VM_SceneDetailer_Planks", "VM_SceneDetailer_Shingles", W):
        setv(ob, mn, "Damage", True); setv(ob, mn, "Damage Radius", 0.0); setv(ob, mn, "Damage Amount", 0.42)
    for sk, mat in (("Stem Material", "VM_VineStem"), ("Leaf Material", "VM_VineLeaf")):
        if bpy.data.materials.get(mat):
            setv(ob, W, sk, bpy.data.materials[mat])
    setv(ob, W, "Vines", True); setv(ob, W, "Yard", True)
    built.append((name, ob, size, oscale))
print("BUILT", f"{time.time() - T0:.0f}s")

dg = bpy.context.evaluated_depsgraph_get(); dg.update()
for name, ob, size, oscale in built:
    t1 = time.time()
    ev = ob.evaluated_get(dg)
    mw = ob.matrix_world
    mwi = mw.inverted()
    bvh = BVHTree.FromObject(ev, dg)                # in object space
    hx, hy = size[0] * oscale[0] / 2, size[1] * oscale[1] / 2
    cx, cy = ob.location.x, ob.location.y
    stats = {}
    for inst in dg.object_instances:
        if not (inst.is_instance and inst.parent is not None and inst.parent.original == ob):
            continue
        nm = inst.object.name
        pool = POOLS.get(nm, "other:" + nm.split("_")[0])
        m = inst.matrix_world
        p = m.translation
        sx = [m.col[i].xyz.length for i in range(3)]
        hit = bvh.find_nearest(mwi @ p)
        dist = (mw @ hit[0] - p).length if hit[0] is not None else 99.0
        s = stats.setdefault(pool, dict(n=0, fl=0, smin=9e9, smax=0.0, an=1.0, inside=0, far=0, dmax=0.0))
        s["n"] += 1
        s["smin"] = min(s["smin"], min(sx)); s["smax"] = max(s["smax"], max(sx))
        s["an"] = max(s["an"], max(sx) / max(min(sx), 1e-6))
        if pool.startswith("VM_Yard_"):
            ox, oy = abs(p.x - cx) - hx, abs(p.y - cy) - hy
            out_ = max(ox, oy)
            if out_ < -0.02:
                s["inside"] += 1
            if out_ > YARD_W + 0.6 and not (ox > 0 and oy > 0 and math.hypot(ox, oy) < YARD_W + 0.9):
                s["far"] += 1
            s["dmax"] = max(s["dmax"], out_)
        elif dist > 0.12:
            s["fl"] += 1
            s["dmax"] = max(s["dmax"], dist)
    print(f"CASE {name} size {size} objscale {oscale} ({time.time() - t1:.0f}s)")
    for pool in sorted(stats):
        s = stats[pool]
        extra = (f"inside {s['inside']} far {s['far']} max out {s['dmax']:.2f}" if pool.startswith("VM_Yard_")
                 else f"floating {s['fl']} (max {s['dmax']:.2f} m)")
        print(f"  {pool:28s} n {s['n']:5d}  scale {s['smin']:.2f}..{s['smax']:.2f} aniso {s['an']:.2f}  {extra}")

if RENDER:
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN")); sc.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(52), 0, math.radians(-35)); sun.data.energy = 3.5
    sc.world = bpy.data.worlds.new("W"); sc.world.use_nodes = True
    sc.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.5, 0.58, 0.7, 1)
    gnd = bpy.data.meshes.new("Ground"); bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=600.0); bm.to_mesh(gnd); bm.free()
    g_ob = bpy.data.objects.new("Ground", gnd); sc.collection.objects.link(g_ob)
    gm = bpy.data.materials.new("Ground"); gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.12, 0.1, 0.07, 1)
    gnd.materials.append(gm)
    sc.render.engine = "CYCLES"; sc.cycles.samples = SAMPLES; sc.cycles.device = "CPU"
    sc.cycles.use_denoising = True
    sc.render.resolution_x = 900; sc.render.resolution_y = 600
    sc.view_settings.view_transform = "AgX"
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.lens = 30
    for name, ob, size, oscale in built:
        for _n, o2, _s, _o in built:
            o2.hide_render = o2 is not ob
        d = max(size[0] * oscale[0], size[1] * oscale[1], size[2] * oscale[2] * 0.8)
        r = d * 1.4 + 3.0
        a = math.radians(-50.0)
        tgt = ob.location + Vector((0.0, 0.0, size[2] * oscale[2] * 0.55))
        cam.location = tgt + Vector((r * math.cos(a), r * math.sin(a), 2.4))
        cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(HERE, "build", f"scale_probe_{name}.png")
        bpy.ops.render.render(write_still=True)
        print("SHOT", sc.render.filepath)
print("PROBE DONE", f"{time.time() - T0:.0f}s")
