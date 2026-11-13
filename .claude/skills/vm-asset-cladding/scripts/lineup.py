"""Render a LINEUP of tile pools, FRONTS up, one row per pool - the first look
at a new or changed asset set, before any house test.
  blender -b --factory-startup --python lineup.py -- <out.png> <maker>:<n>[:<material>] ...
  e.g. -- C:/tmp/lineup.png make_shake_variants:10:shake make_worn_shakes:20:shake
          make_broken_shakes:6:shake make_worn_asphalt:20:asphalt make_torn_asphalt:8:asphalt
Materials: shake (VM_Shake), siding (VM_Siding), frame (VM_RoofFrame), asphalt.
Each tile lies with +Y (its front) up and Z (up the roof / face) pointing up
the image: rotation (90 deg, 0, 180 deg). (v2.33: a -90 deg lineup shows the
flat BACKS, whose big triangles smear the edge attributes - fake bands.)"""
import bpy, sys, os, math
sys.path.insert(0, r"C:\Users\krist\Desktop\main-projects\Projects\vm-scene-detailer")
import build_engine as be
args = sys.argv[sys.argv.index("--") + 1:]
out, specs = args[0], args[1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
walls = os.path.join(be.ASSET_SRC, "materials", "walls")
MATS = dict(
    shake=lambda: be.make_board_material("VM_Shake", os.path.join(walls, "dark_planks"), "dark_planks",
                                         8, 0.10, 2.0, 0.65, 1.1, 0.6),
    siding=lambda: be.make_board_material("VM_Siding", os.path.join(walls, "brown_planks_09"), "brown_planks_09",
                                          7, 0.08, 0.95, 0.55, 0.9),
    frame=lambda: be.make_board_material("VM_RoofFrame", os.path.join(walls, "brown_planks_09"), "brown_planks_09",
                                         7, 0.08, 0.95, 0.45, 0.7),
    asphalt=lambda: be.make_asphalt_material("VM_Asphalt"))
made = {}
rows = []
for spec in specs:
    fn, n, *m = spec.split(":")
    m = m[0] if m else "shake"
    if m not in made:
        made[m] = MATS[m]()
    col = bpy.data.collections.new(fn); sc.collection.children.link(col)
    getattr(be, fn)(col, fn, int(n), made[m])
    rows.append(sorted(col.objects, key=lambda o: o.name))
y, w_max = 0.0, 0.0
for obs in rows:
    x = 0.0
    for ob in obs:
        d = ob.dimensions
        ob.rotation_euler = (math.radians(90), 0, math.radians(180))
        ob.location = (x + d.x / 2, y, 0.0)
        x += d.x + 0.05
    w_max = max(w_max, x)
    y -= max(max(o.dimensions.z for o in obs), 0.12) + 0.12
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN")); sc.collection.objects.link(sun)
sun.rotation_euler = (math.radians(40), 0, math.radians(30)); sun.data.energy = 4.0
sc.world = bpy.data.worlds.new("W"); sc.world.use_nodes = True
sc.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.6, 0.7, 1)
cd = bpy.data.cameras.new("C"); cd.type = "ORTHO"; cd.ortho_scale = max(w_max, -y) + 0.2
cam = bpy.data.objects.new("C", cd); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (w_max / 2, y / 2, 6.0)
sc.render.engine = "CYCLES"; sc.cycles.samples = 24; sc.cycles.device = "CPU"; sc.cycles.use_denoising = True
sc.render.resolution_x = sc.render.resolution_y = 1500
sc.view_settings.view_transform = "AgX"
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print("WROTE", out)
