"""Variation shots + manual-test scene from the BUILT library (build/stage/VM_Assets.blend).
Eight houses that differ in shape, size, unapplied object scale, roof style,
porch / balcony, damage and yard, each dressed the way a user would (Dress
Object + a library preset + a few sockets), rendered one by one.
  blender -b --factory-startup --python .claude/skills/vm-new-building-part/scripts/variations.py -- [samples:N] [cpu] [only:a,b] [render:a,b] [save:PATH] [lib:PATH] [norender]
lib:PATH uses that VM_Assets.blend instead of build/stage (e.g. the delivered one, so the
saved file's assets point at the library the add-on updates from). A core library gets the
example doors / windows / yard added (VM_ExampleAssets.blend found by the add-on, or examples:PATH).
Writes build/var_<case>.png + build/var_sheet.png; save:PATH also saves the
dressed scene (camera per case as markers) for manual testing."""
import bpy, bmesh, sys, os, math, time, importlib.util, mathutils
import builtins, functools
from mathutils import Vector
builtins.print = functools.partial(builtins.print, flush=True)
HERE = r"C:\Users\krist\Desktop\main-projects\Projects\vm-scene-detailer"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SAMPLES = next((int(a[8:]) for a in ARGS if a.startswith("samples:")), 64)
ONLY = next((a[5:].split(",") for a in ARGS if a.startswith("only:")), None)
SAVE = next((a[5:] for a in ARGS if a.startswith("save:")), None)
RENDER = next((a[7:].split(",") for a in ARGS if a.startswith("render:")), None)   # render only these (all dressed)
T0 = time.time()
spec = importlib.util.spec_from_file_location("VM_Tools_Addon", os.path.join(HERE, "VM_Tools_Addon.py"))
vmt = importlib.util.module_from_spec(spec); sys.modules["VM_Tools_Addon"] = vmt; spec.loader.exec_module(vmt)
bpy.ops.wm.read_factory_settings(use_empty=True)
LIB = next((a[4:] for a in ARGS if a.startswith("lib:")), os.path.join(HERE, "build", "stage", "VM_Assets.blend"))
vmt.register(); vmt.LIBRARY_PATH_OVERRIDE = LIB
vmt.import_engine(vmt.LIBRARY_PATH_OVERRIDE, [])
# a CORE library (v2.36 split) has empty door / window / yard collections: add the example set
# (VM_ExampleAssets.blend next to it, or examples:PATH) so the kit looks like the demo builds
_EX = next((a[9:] for a in ARGS if a.startswith("examples:")), "") or vmt.example_library_path()
if _EX and vmt.examples_missing(_EX):
    print("examples:", vmt.import_examples(_EX, []))
sc = bpy.context.scene
W, P, S, R = "VM_SceneDetailer_Windows", "VM_SceneDetailer_Planks", "VM_SceneDetailer_Shingles", "VM_RoofCap"


def setv(ob, mod, name, val):
    m = ob.modifiers[mod]; it = vmt.find_input(m.node_group, name)
    if it is None:
        raise KeyError(f"{mod}: no socket {name!r}")
    getattr(m.properties.inputs, it.identifier).value = val


# name: boxes [(cx, cy, z0, sx, sy, sz)], object scale, preset, roof overrides,
#       damage (None | "light" | "zone" | "whole"), yard, vines, extra sockets {(mod, socket): v}
CASES = [
    ("porch_cottage", [(0, 0, 0, 8, 6, 3)], (1, 1, 1), "Base - Porch house", {},
     "zone", True, 18, {}),
    ("balcony_wreck", [(0, 0, 0, 9, 6.5, 3.2)], (1, 1, 1), "Base - Balcony house", {},
     "whole", True, 40, {}),
    ("l_shape_hip", [(0, 0, 0, 10, 5, 3), (3.0, 4.0, 0, 4, 5, 3)], (1, 1, 1), "Base - Hip roof", {},
     "light", True, 0, {}),
    ("scaled_unapplied", [(0, 0, 0, 5, 4, 2.4)], (1.6, 1.0, 1.3), "Base - Weathered gable", {},
     "light", True, 0, {(W, "Half Broken"): 1.0}),
    ("two_storey", [(0, 0, 0, 7, 5, 6)], (1, 1, 1), "Base - Gable roof", {"Pitch": 52},
     "zone", True, 30, {}),
    ("tower", [(0, 0, 0, 4, 4, 9)], (1, 1, 1), "Base - Weathered gable", {"Pitch": 55},
     "light", True, 0, {}),
    ("tiny_shed", [(0, 0, 0, 3, 2.5, 2.2)], (1, 1, 1), "Base - Weathered gable", {},
     "light", True, 0, {}),
    ("big_barn", [(0, 0, 0, 14, 9, 4)], (1, 1, 1), "Base - Gable roof", {"Pitch": 40},
     "whole", True, 25, {}),
    ("kept_flat", [(0, 0, 0, 8, 6, 3)], (1, 1, 1), "Base - Flat roof", {},
     None, False, 0, {}),
    # v2.32-v2.36 roof damage: a torn hole in the asphalt roof (sides facing the hole,
    # shards on the roof below, granule loss); the zone sits ON the roof (raycast after evaluation)
    ("asphalt_hole", [(0, 0, 0, 8, 6, 3)], (1, 1, 1), "Base - Weathered asphalt", {},
     "roofhole", False, 0, {}),
]
if ONLY:
    CASES = [c for c in CASES if c[0] in ONLY]

built = []
roof_zones = []          # "roofhole" cases: zone added once the roof exists
for k, (name, boxes, oscale, preset, roof, dmg, yard, vines, extra) in enumerate(CASES):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    for cx, cy, z0, sx, sy, sz in boxes:
        bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.LocRotScale(
            (cx, cy, z0 + sz / 2), None, (sx, sy, sz)))
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    ob.location = (k * 70.0, 0, 0); ob.scale = oscale
    bpy.context.view_layer.update()
    vmt.dress_object(ob, [])
    for o_ in bpy.context.selected_objects:
        o_.select_set(False)
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.vm.apply_preset(preset="lib:" + preset)
    for sk, v in roof.items():
        setv(ob, R, sk, math.radians(v) if sk == "Pitch" else v)
    setv(ob, W, "Yard", yard); setv(ob, W, "Yard Seed", 5 + k)
    if dmg:
        for mn in (P, S, W):
            setv(ob, mn, "Damage", True); setv(ob, mn, "Damage Seed", 7 if dmg == "roofhole" else 21 + k)
            if dmg == "whole":
                setv(ob, mn, "Damage Radius", 0.0); setv(ob, mn, "Damage Amount", 0.42)
        if dmg == "roofhole":
            setv(ob, S, "Roof Holes", 1.0)
            roof_zones.append(ob)
        elif dmg != "light":
            setv(ob, P, "Missing Share", 0.3); setv(ob, P, "Broken Share", 0.35)
        if dmg == "zone":
            sy_ = boxes[0][4] * oscale[1]
            vmt.add_damage_zone(ob, ob.location + Vector((0.8, -sy_ / 2, 1.4)), sc.collection,
                                radius=2.4, amount=0.85)
    if vines:
        for sk, mat in (("Stem Material", "VM_VineStem"), ("Leaf Material", "VM_VineLeaf")):
            if bpy.data.materials.get(mat):
                setv(ob, W, sk, bpy.data.materials[mat])
        setv(ob, W, "Vines", True); setv(ob, W, "Vine Count", vines); setv(ob, W, "Vine Branches", 12)
        setv(ob, W, "Vine Height", 6.0)
    for (mn, sk), v in extra.items():
        setv(ob, mn, sk, v)
    ob.update_tag()
    xs = [b[0] + s * b[3] / 2 for b in boxes for s in (-1, 1)]
    ys = [b[1] + s * b[4] / 2 for b in boxes for s in (-1, 1)]
    zs = [b[2] + b[5] for b in boxes]
    ext = Vector(((max(xs) - min(xs)) * oscale[0], (max(ys) - min(ys)) * oscale[1], max(zs) * oscale[2]))
    pitch_ = roof.get("Pitch", {"Base - Porch house": 45, "Base - Balcony house": 55}.get(preset, 35))
    if "Flat" not in preset:                         # frame the roof too: ridge = half the short side x tan(pitch)
        ext.z += min(ext.x, ext.y) / 2 * math.tan(math.radians(pitch_))
    ctr = ob.location + Vector(((max(xs) + min(xs)) / 2 * oscale[0], (max(ys) + min(ys)) / 2 * oscale[1], 0))
    built.append((name, ob, ext, ctr))
    print("DRESSED", name, preset, dmg, f"{time.time() - T0:.0f}s")

t_ev = time.time()
dg = bpy.context.evaluated_depsgraph_get(); dg.update()
counts = {}
for inst in dg.object_instances:
    if inst.is_instance and inst.parent is not None:
        n_ = inst.parent.original.name
        counts[n_] = counts.get(n_, 0) + 1
print("EVALUATED", f"{time.time() - t_ev:.0f}s", counts)
close_cams = []
for ob in roof_zones:
    hit, loc, *_r = sc.ray_cast(dg, ob.location + Vector((0.5, -1.5, 40.0)), Vector((0, 0, -1)))
    if not hit:
        print("ROOF NOT HIT", ob.name); continue
    vmt.add_damage_zone(ob, loc, sc.collection, radius=2.2, amount=0.9)
    cd_ = bpy.data.cameras.new("CamClose"); cd_.lens = 35
    cc = bpy.data.objects.new("Cam_" + ob.name + "_close", cd_); sc.collection.objects.link(cc)
    cc.location = loc + Vector((0.0, -4.2, 3.4))
    cc.rotation_euler = (loc - cc.location).to_track_quat("-Z", "Y").to_euler()
    close_cams.append((ob.name + "_close", cc))
    print("ROOF ZONE", ob.name, tuple(round(c, 2) for c in loc))
if roof_zones:
    dg.update()

sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN")); sc.collection.objects.link(sun)
sun.rotation_euler = (math.radians(52), 0, math.radians(-35)); sun.data.energy = 3.5; sun.data.angle = math.radians(3)
sc.world = bpy.data.worlds.new("W"); sc.world.use_nodes = True
sc.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.5, 0.58, 0.7, 1)
sc.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.9
gnd = bpy.data.meshes.new("Ground"); bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=800.0); bm.to_mesh(gnd); bm.free()
g_ob = bpy.data.objects.new("Ground", gnd); sc.collection.objects.link(g_ob)
gm = bpy.data.materials.new("Ground"); gm.use_nodes = True
bsdf = gm.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.12, 0.1, 0.07, 1); bsdf.inputs["Roughness"].default_value = 0.95
gnd.materials.append(gm)
sc.render.engine = "CYCLES"; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
DEV = "CPU"
if "cpu" not in ARGS:
    try:
        cp = bpy.context.preferences.addons["cycles"].preferences
        for typ in ("OPTIX", "CUDA"):
            try:
                cp.compute_device_type = typ
            except TypeError:
                continue
            cp.get_devices()
            gpus = [d for d in cp.devices if d.type == typ]
            if gpus:
                for d in cp.devices:
                    d.use = d.type == typ
                sc.cycles.device = "GPU"; DEV = typ
                break
    except Exception as e:
        print("GPU setup failed, CPU:", e)
print("RENDER DEVICE", DEV)
sc.render.resolution_x = 1400; sc.render.resolution_y = 900
sc.view_settings.view_transform = "AgX"
cam_data = bpy.data.cameras.new("Cam"); cam_data.lens = 30
shots, cams = [], []
for k, (name, ob, ext, ctr) in enumerate(built):
    d = max(ext.x, ext.y, ext.z * 0.8)
    r = d * 1.45 + 4.0
    a = math.radians(-90.0 + 38.0)
    tgt = ctr + Vector((0.0, 0.0, ext.z * 0.5))
    c_k = bpy.data.objects.new("Cam_" + name, cam_data); sc.collection.objects.link(c_k)
    c_k.location = tgt + Vector((r * math.cos(a), r * math.sin(a), 1.8 + ext.z * 0.25))
    c_k.rotation_euler = (tgt - c_k.location).to_track_quat("-Z", "Y").to_euler()
    cams.append(c_k)
    if "norender" in ARGS or (RENDER and name not in RENDER):
        continue
    sc.camera = c_k
    for _n, o2, _e, _c in built:
        o2.hide_render = o2 is not ob
    fp = os.path.join(HERE, "build", f"var_{name}.png")
    sc.render.filepath = fp
    t1 = time.time()
    bpy.ops.render.render(write_still=True)
    shots.append(fp)
    print("SHOT", fp, f"{time.time() - t1:.0f}s")
for _n, o2, _e, _c in built:
    o2.hide_render = False
for k, c_k in enumerate(cams):        # manual test: frame k+1 = this case's camera (bound AFTER the renders)
    mk = sc.timeline_markers.new(built[k][0], frame=k + 1); mk.camera = c_k
for j, (n_, c_k) in enumerate(close_cams):   # close-ups of the roof holes after the case frames
    mk = sc.timeline_markers.new(n_, frame=len(cams) + j + 1); mk.camera = c_k
sc.camera = cams[0]
sc.frame_start, sc.frame_end = 1, len(cams) + len(close_cams)

if shots:
    import numpy as np
    cols, w_, h_ = 3, 700, 450
    rows = (len(shots) + cols - 1) // cols
    sheet = np.ones((rows * h_, cols * w_, 4), dtype=np.float32)
    for k, fp in enumerate(shots):
        im = bpy.data.images.load(fp)
        im.scale(w_, h_)
        px = np.array(im.pixels[:], dtype=np.float32).reshape(h_, w_, 4)
        r_, c_ = rows - 1 - k // cols, k % cols
        sheet[r_ * h_:(r_ + 1) * h_, c_ * w_:(c_ + 1) * w_] = px
        bpy.data.images.remove(im)
    out = bpy.data.images.new("var_sheet", cols * w_, rows * h_, alpha=True)
    out.pixels = sheet.ravel()
    out.filepath_raw = os.path.join(HERE, "build", "var_sheet.png"); out.file_format = "PNG"; out.save()
    bpy.data.images.remove(out)
if SAVE:
    sc.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=SAVE, compress=True)
    print("SAVED", SAVE)
print("VARIATIONS DONE", f"{time.time() - T0:.0f}s")
