"""Render ONE tile variant large - the close look a lineup is too small for
(v2.34: shading artefacts - flaps, dark slits, stacked gouges - only showed
on a single piece rendered big, in plain grey).
  blender -b --factory-startup --python one_tile.py -- <out.png> <maker>:<object name>[:<scale z>] [grey]
  e.g. -- C:/tmp/one.png make_broken_shakes:B_01_UL:0.17 grey
The maker is called with n=2 into a collection named 'B', 'W'... (its first
letter of the object name prefix); pass the object name it makes. <scale z>
shows a 1 m broken piece at a real length (0.17 for a head-torn shake)."""
import bpy, sys, os, math
sys.path.insert(0, r"C:\Users\krist\Desktop\main-projects\Projects\vm-scene-detailer")
import build_engine as be
args = sys.argv[sys.argv.index("--") + 1:]
out, spec = args[0], args[1]
fn, obname, *sz = spec.split(":")
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
walls = os.path.join(be.ASSET_SRC, "materials", "walls")
if "grey" in args[2:]:
    mat = bpy.data.materials.new("Grey"); mat.use_nodes = True
elif "asphalt" in fn:
    mat = be.make_asphalt_material("VM_Asphalt")
else:
    mat = be.make_board_material("VM_Shake", os.path.join(walls, "dark_planks"), "dark_planks", 8, 0.10, 2.0, 0.65,
                                 1.1, 0.6)
col = bpy.data.collections.new("c"); sc.collection.children.link(col)
getattr(be, fn)(col, obname.split("_")[0], 2, mat)
ob = bpy.data.objects[obname]
for o in list(col.objects):
    if o is not ob:
        bpy.data.objects.remove(o)
if sz:
    ob.scale.z = float(sz[0])
ob.rotation_euler = (math.radians(90), 0, math.radians(180))     # front up, Z up the image
bpy.context.view_layer.update()
d = ob.dimensions
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN")); sc.collection.objects.link(sun)
sun.rotation_euler = (math.radians(40), 0, math.radians(30)); sun.data.energy = 4.0
sc.world = bpy.data.worlds.new("W"); sc.world.use_nodes = True
cd = bpy.data.cameras.new("C"); cd.type = "ORTHO"; cd.ortho_scale = max(d.x, d.y) * 1.25
cam = bpy.data.objects.new("C", cd); sc.collection.objects.link(cam); sc.camera = cam
bb = [ob.matrix_world @ __import__("mathutils").Vector(c) for c in ob.bound_box]
cam.location = (sum(v.x for v in bb) / 8, sum(v.y for v in bb) / 8, 1.0)
sc.render.engine = "CYCLES"; sc.cycles.samples = 16; sc.cycles.device = "CPU"
sc.render.resolution_x = sc.render.resolution_y = 900
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print("WROTE", out, "verts", len(ob.data.vertices))
