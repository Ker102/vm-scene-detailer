"""Look shots from the BUILT library (build/stage/VM_Assets.blend - no
group rebuild): four abandoned houses made with the add-on's Dress Object,
each rendered from a few metres further off than the close-ups, two angles.
  blender -b --factory-startup --python .claude/skills/vm-new-building-part/scripts/look_shots.py -- [samples:N]
Writes build/look_shot_<case>_<view>.png and build/look_shots_sheet.png."""
import bpy, bmesh, sys, os, math, time, importlib.util, mathutils
import builtins, functools
from mathutils import Vector
builtins.print = functools.partial(builtins.print, flush=True)
HERE = r"C:\Users\krist\Desktop\main-projects\Projects\vm-scene-detailer"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SAMPLES = next((int(a[8:]) for a in ARGS if a.startswith("samples:")), 48)
T0 = time.time()
spec = importlib.util.spec_from_file_location("VM_Tools_Addon", os.path.join(HERE, "VM_Tools_Addon.py"))
vmt = importlib.util.module_from_spec(spec); sys.modules["VM_Tools_Addon"] = vmt; spec.loader.exec_module(vmt)
bpy.ops.wm.read_factory_settings(use_empty=True)
vmt.register(); vmt.LIBRARY_PATH_OVERRIDE = os.path.join(HERE, "build", "stage", "VM_Assets.blend")
vmt.import_engine(vmt.LIBRARY_PATH_OVERRIDE, [])
_EX = vmt.example_library_path()   # build/stage holds the CORE library (v2.36 split): add the examples
if _EX and vmt.examples_missing(_EX):
    print("examples:", vmt.import_examples(_EX, []))
sc = bpy.context.scene
W = "VM_SceneDetailer_Windows"


def setv(ob, mod, name, val):
    m = ob.modifiers[mod]; it = vmt.find_input(m.node_group, name)
    if it is None:
        raise KeyError(f"{mod}: no socket {name!r}")
    getattr(m.properties.inputs, it.identifier).value = val


# (name, size x/y/h, pitch, porch, balcony, damage (none / zone / whole), vines)
CASES = [("porch", (8, 6, 3), 45, True, False, "zone", True),
         ("wreck", (9, 6.5, 3.2), 55, True, True, "whole", True),
         ("cottage", (7, 5, 2.8), 40, False, False, "zone", False),
         ("kept", (8, 6, 3), 45, True, False, "none", False)]
built = []
for k, (name, size, pitch, porch, balc, dmg, vines) in enumerate(CASES):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.LocRotScale((0, 0, size[2] / 2), None, size))
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    ob.location = (k * 60.0, 0, 0)
    vmt.dress_object(ob, [])
    setv(ob, "VM_RoofCap", "Style", "Gable"); setv(ob, "VM_RoofCap", "Pitch", math.radians(pitch))
    setv(ob, "VM_RoofCap", "Porch", porch)
    if balc:
        setv(ob, "VM_RoofCap", "Balcony", True)
    setv(ob, W, "Yard Seed", 3 + k)
    if dmg != "none":
        for mn in ("VM_SceneDetailer_Planks", "VM_SceneDetailer_Shingles", W):
            setv(ob, mn, "Damage", True); setv(ob, mn, "Damage Seed", 11 + k)
            if dmg == "whole":
                setv(ob, mn, "Damage Radius", 0.0); setv(ob, mn, "Damage Amount", 0.42)
        setv(ob, "VM_SceneDetailer_Planks", "Missing Share", 0.3)
        setv(ob, "VM_SceneDetailer_Planks", "Broken Share", 0.35)
        if dmg == "zone":
            vmt.add_damage_zone(ob, ob.location + Vector((0.8, -size[1] / 2, 1.4)), sc.collection, radius=2.4,
                                amount=0.85)
    if vines:
        m_ = ob.modifiers[W]
        for sk, mat in (("Stem Material", "VM_VineStem"), ("Leaf Material", "VM_VineLeaf")):
            if bpy.data.materials.get(mat):
                setv(ob, W, sk, bpy.data.materials[mat])
        setv(ob, W, "Vines", True); setv(ob, W, "Vine Count", 18); setv(ob, W, "Vine Branches", 12)
        setv(ob, W, "Vine Height", 5.0)
    built.append((name, ob, size))
print("BUILT", f"{time.time() - T0:.0f}s")

sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN")); sc.collection.objects.link(sun)
sun.rotation_euler = (math.radians(52), 0, math.radians(-35)); sun.data.energy = 3.5; sun.data.angle = math.radians(3)
sc.world = bpy.data.worlds.new("W"); sc.world.use_nodes = True
sc.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.5, 0.58, 0.7, 1)
sc.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.9
gnd = bpy.data.meshes.new("Ground"); bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=400.0); bm.to_mesh(gnd); bm.free()
g_ob = bpy.data.objects.new("Ground", gnd); sc.collection.objects.link(g_ob)
gm = bpy.data.materials.new("Ground"); gm.use_nodes = True
bsdf = gm.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.12, 0.1, 0.07, 1); bsdf.inputs["Roughness"].default_value = 0.95
gnd.materials.append(gm)
sc.render.engine = "CYCLES"; sc.cycles.samples = SAMPLES; sc.cycles.device = "CPU"
sc.cycles.use_denoising = True
sc.render.resolution_x = 1200; sc.render.resolution_y = 800
sc.view_settings.view_transform = "AgX"
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 32
shots = []
for name, ob, size in built:
    for _n, o2, _s in built:
        o2.hide_render = o2 is not ob
    d = max(size[0], size[1])
    for tag, ang, el in (("front", -28.0, 1.4), ("corner", 40.0, 2.4)):
        r = d * 1.45 + 3.0
        a = math.radians(-90.0 + ang)
        tgt = ob.location + Vector((0.0, 0.0, size[2] * 0.55))
        cam.location = tgt + Vector((r * math.cos(a), r * math.sin(a), el))
        cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
        fp = os.path.join(HERE, "build", f"look_shot_{name}_{tag}.png")
        sc.render.filepath = fp
        t1 = time.time()
        bpy.ops.render.render(write_still=True)
        shots.append(fp)
        print("SHOT", fp, f"{time.time() - t1:.0f}s")
import numpy as np
cols, w_, h_ = 2, 600, 400
rows = (len(shots) + cols - 1) // cols
sheet = np.ones((rows * h_, cols * w_, 4), dtype=np.float32)
for k, fp in enumerate(shots):
    im = bpy.data.images.load(fp)
    im.scale(w_, h_)
    px = np.array(im.pixels[:], dtype=np.float32).reshape(h_, w_, 4)
    r_, c_ = rows - 1 - k // cols, k % cols
    sheet[r_ * h_:(r_ + 1) * h_, c_ * w_:(c_ + 1) * w_] = px
out = bpy.data.images.new("look_shots_sheet", cols * w_, rows * h_, alpha=True)
out.pixels = sheet.ravel()
out.filepath_raw = os.path.join(HERE, "build", "look_shots_sheet.png"); out.file_format = "PNG"; out.save()
print("SHOTS DONE", f"{time.time() - T0:.0f}s")
