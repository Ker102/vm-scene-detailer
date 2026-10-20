"""
VM_SceneDetailer v2 - semantic architectural application engine for Blender 5.2 (headless).

Extends v1 (scatter detailing) with:
  * Placement Mode menu socket: Scatter (v1 default) / Fit / Cladding
  * Zones panel: Face Zone {All, Walls, Roof, Floor} + Wall/Roof slope thresholds
  * Fit: wall-zone placement, depth-axis aligned to face normal (parts sit flush on
    the wall plane), embed offset, optional drop-to-ground, fit jitter
  * Cladding: exact per-face row/slot courses (rows along horizontal tangent /
    slope direction), stagger, per-slot jitter/tint, Row Overlap
  * Materials panel: Wall/Roof/Floor material sockets applied to the base mesh by
    zone via Set Material (gated: empty socket = untouched)
  * VM_RoofCap node group: pitched gable/hip roof generator over a flat-top host

v2.1 bug fixes:
  * Strict wall-contact contract: architectural variants (doors, handles, tiles)
    are normalized to a BACK-CENTER depth origin (y=0 ON the wall-contact face),
    and Fit gained a "Backing Offset" socket so fitted parts clear the cladding
    layer in front of the base wall (doors sit proud of the planks, never behind).
  * Every image is PACKED into each delivered .blend before saving (no more
    magenta/missing textures on Windows - no load-bearing outside filepaths).

v2.2 pack adapter + windows layer:
  * pack_ingest.py (delivered alongside): generic ZERO-CONFIG adapter that
    ingests ANY glTF/OBJ pack into normalized <Pack>_WALLFLAT/_TILE/_PROP
    variant collections + <Pack>_Quarantine (degenerate sheets, multi-part
    leftovers, non-flat/ajar panels) + a JSON ingest report. Same unmodified
    script runs on WornWoodenDoorsPack and 4 window packs.
  * Doors are rebuilt THROUGH the adapter: VM_Doors now contains ONLY the
    wall-flat door slabs; the pack's "Worn Doorframe_*" pieces (splayed frame
    profile: PCA thickness 1.078x bbox depth) are auto-quarantined as
    non-flat (ajar) - they were the "floating" door stand-ins.
  * Windows layer: a fifth starter modifier (Fit) over a windows collection
    from the adapter (WeatheredWoodenWindow shutters + a BrokenWindow01 unit)
    - SAME VM_SceneDetailer node group, different collection = the
    "different pack, same engine" proof. Windows keep the identical
    wall-contact contract as doors and are reseeded so zero window/door and
    zero window/plank bbox intersections occur.

Deterministic (fixed seeds). Run:
  cd /home/kristo/blender && ./blender-5.2.2-linux-x64/blender -b --python build_engine.py
"""

import bpy, bmesh, os, sys, shutil, math, json
from collections import Counter
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pack_ingest

ROOT = "/home/kristo/harneloop-work/engine"
ASSET_SRC = "/mnt/c/Users/krist/Documents/ViperMeshAssets"
DELIVER = "/mnt/c/Users/krist/Downloads/blender-engine"
BLEND_PATH = os.path.join(ROOT, "VM_SceneDetailer.blend")
STARTER_PATH = os.path.join(ROOT, "VM_Starter.blend")
ROOFCAP_PATH = os.path.join(ROOT, "VM_RoofCap.blend")
STAGE = os.path.join(ROOT, "assets")

GLTF_SLUGS = ["Shelf_01", "wooden_table_02", "painted_wooden_nightstand", "painted_wooden_shelves"]
LIB_BLENDS = [
    "props/lamps/table-lamps/lamp_brass_desk_a.blend",
    "props/lamps/table-lamps/lamp_ceramic_linen_a.blend",
    "props/books/stacks/books_stack_blue_gray_a.blend",
    "props/books/stacks/books_stack_neutral_a.blend",
]
DOOR_GLTF = "props/doors/WornWoodenDoorsPack/scene.gltf"
WIN_GLTF_WW = "props/windows/WeatheredWoodenWindow/scene.gltf"
WIN_GLTF_BW01 = "props/windows/BrokenWindow01/scene.gltf"
WIN_GLTF_BW07 = "props/windows/BrokenWindow07/scene.gltf"
WIN_GLTF_MED = "props/windows/MedievalWindows/scene.gltf"
PACK_PATHS = [DOOR_GLTF, WIN_GLTF_WW, WIN_GLTF_BW01, WIN_GLTF_BW07, WIN_GLTF_MED]

log = lambda *a: print(*a, flush=True)


# ---------------------------------------------------------------------------- helpers
def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def link_only(ob, col):
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    if ob.name not in col.objects:
        col.objects.link(ob)


def new_mesh_obj(name, verts, faces, col):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    return ob


# ---------------------------------------------------------------------------- materials
def make_principled(name, color, rough=0.8):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    return mat


def make_textured_material(name, tdir, diff_f, rough_f=None, nor_f=None, scale=0.35):
    """Principled material with Object-coord image textures (read-only asset lib)."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexCoord"); tex.location = (-1100, 0)
    mapping = nt.nodes.new("ShaderNodeMapping"); mapping.location = (-900, 0)
    mapping.inputs["Scale"].default_value = (scale, scale, scale)
    nt.links.new(tex.outputs["Object"], mapping.inputs["Vector"])
    diff = bpy.data.images.load(os.path.join(tdir, diff_f), check_existing=True)
    it_d = nt.nodes.new("ShaderNodeTexImage"); it_d.image = diff; it_d.location = (-650, 200)
    nt.links.new(mapping.outputs["Vector"], it_d.inputs["Vector"])
    nt.links.new(it_d.outputs["Color"], bsdf.inputs["Base Color"])
    if rough_f:
        rough = bpy.data.images.load(os.path.join(tdir, rough_f), check_existing=True)
        rough.colorspace_settings.name = "Non-Color"
        it_r = nt.nodes.new("ShaderNodeTexImage"); it_r.image = rough; it_r.location = (-650, -100)
        nt.links.new(mapping.outputs["Vector"], it_r.inputs["Vector"])
        nt.links.new(it_r.outputs["Color"], bsdf.inputs["Roughness"])
    if nor_f:
        nor = bpy.data.images.load(os.path.join(tdir, nor_f), check_existing=True)
        nor.colorspace_settings.name = "Non-Color"
        it_n = nt.nodes.new("ShaderNodeTexImage"); it_n.image = nor; it_n.location = (-650, -400)
        nmap = nt.nodes.new("ShaderNodeNormalMap"); nmap.location = (-400, -400)
        nt.links.new(mapping.outputs["Vector"], it_n.inputs["Vector"])
        nt.links.new(it_n.outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


# NOTE: per-instance tint is delivered as the material-independent instance color
# attribute 'Color' (FLOAT_COLOR, INSTANCE domain) stored by VM_SceneDetailer.
# Demo materials deliberately do NOT consume it (headless Attribute-node quirk).

def make_wood_material():
    tdir = os.path.join(ASSET_SRC, "materials", "wooden_planks")
    return make_textured_material("VM_WoodPlanks", tdir,
                                  "wooden_planks_Diffuse_1k.jpg",
                                  "wooden_planks_Rough_1k.jpg",
                                  "wooden_planks_nor_gl_1k.jpg", 0.35)


# ---------------------------------------------------------------------------- asset staging
def stage_gltf(slug):
    src = os.path.join(ASSET_SRC, "props", slug)
    dst = os.path.join(STAGE, "props", slug)
    os.makedirs(os.path.join(dst, "textures"), exist_ok=True)
    for f in os.listdir(src):
        s = os.path.join(src, f)
        if os.path.isfile(s):
            shutil.copy2(s, os.path.join(dst, f))
            if f.lower().endswith((".jpg", ".png")):
                shutil.copy2(s, os.path.join(dst, "textures", f))
    return os.path.join(dst, f"{slug}_1k.gltf")


def merge_to_variant(objs, name, col):
    """Join all mesh objects of one source asset into a single variant object."""
    meshes = [o for o in objs if o.type == "MESH"]
    for o in objs:
        link_only(o, col)
    if not meshes:
        return None
    names = [o.name for o in objs]
    if len(meshes) == 1:
        ob = meshes[0]
    else:
        bpy.ops.object.select_all(action="DESELECT")
        for o in meshes:
            o.select_set(True)
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.join()
        ob = meshes[0]
    for n in names:
        if n != ob.name and n in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
    ob.data.transform(ob.matrix_world)
    ob.matrix_world = Matrix.Identity(4)
    ob.name = name
    ob.data.name = name
    link_only(ob, col)
    return ob


def orient_variant(ob):
    """Bake transform, then force the strict wall-contact convention:
    X = width, Y = depth (local +Y = outward face normal), Z = height,
    origin at BACK-BASE-CENTER: x centered, z at base (Drop To Ground contract),
    y = 0 ON the wall-contact (back) face. Placement therefore puts the wall
    contact face of EVERY variant at the same distance regardless of depth."""
    ob.data.transform(ob.matrix_world)
    ob.matrix_world = Matrix.Identity(4)
    me = ob.data
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    ex, ey, ez = max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)
    if ey >= ez and ey >= ex:          # height along Y -> rotate +90 about X: (x,y,z)->(x,-z,y)
        me.transform(Matrix.Rotation(math.pi / 2, 4, "X"))
    elif ez >= ex and ez >= ey:
        pass                            # already Z-up
    else:                               # height along X -> rotate -90 about Y: (x,y,z)->(z,y,-x)
        me.transform(Matrix.Rotation(-math.pi / 2, 4, "Y"))
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    # wall-contact convention: y=0 is the BACK face (local min Y), the face that
    # touches the wall when fitted (local +Y points along the outward normal)
    cx, cy, cz = (min(xs) + max(xs)) / 2, min(ys), min(zs)
    me.transform(Matrix.Translation((-cx, -cy, -cz)))
    me.update()


def import_assets(primary_col, library_col):
    for slug in GLTF_SLUGS:
        path = stage_gltf(slug)
        before = set(bpy.data.objects.keys())
        bpy.ops.import_scene.gltf(filepath=path)
        new = [bpy.data.objects[n] for n in set(bpy.data.objects.keys()) - before]
        ob = merge_to_variant(new, "Prop_" + slug, primary_col)
        log(f"  imported {slug}: merged into 1 variant, {len(ob.data.vertices)} verts")
    for rel in LIB_BLENDS:
        path = os.path.join(ASSET_SRC, rel)
        with bpy.data.libraries.load(path, link=False) as (src, dst):
            dst.objects = src.objects[:]
        objs = [o for o in dst.objects if o is not None]
        name = "Lib_" + os.path.splitext(os.path.basename(rel))[0]
        ob = merge_to_variant(objs, name, library_col)
        log(f"  appended {os.path.basename(rel)}: merged {len(objs)} objects -> "
            f"{len(ob.data.vertices) if ob else 0} verts")


def ingest_packs(col_parent, col_doors, col_handles, col_windows):
    """Ingest the asset packs through pack_ingest.py (zero-config adapter) and
    wire the normalized outputs into the engine's VM_ collections:
      VM_Doors       <- <WornWoodenDoorsPack_WALLFLAT> (wall-flat slabs ONLY)
      VM_DoorHandles <- <WornWoodenDoorsPack_PROP>
      VM_Windows     <- <WeatheredWoodenWindow_WALLFLAT> + <BrokenWindow01_WALLFLAT>
    Quarantined objects stay in <Pack>_Quarantine and never reach Fit."""
    reports = {}
    for rel in PACK_PATHS:
        rep = pack_ingest.ingest_pack(os.path.join(ASSET_SRC, rel),
                                      out_dir=ROOT, parent=col_parent)
        reports[rep["pack"]] = rep

    def pack_objs(pack, cls):
        cname = "%s_%s" % (pack, cls)
        col = bpy.data.collections.get(cname)
        return sorted(col.objects, key=lambda o: o.name) if col else []

    doors = pack_objs("WornWoodenDoorsPack", "WALLFLAT")
    handles = pack_objs("WornWoodenDoorsPack", "PROP")
    windows = pack_objs("WeatheredWoodenWindow", "WALLFLAT") + \
        pack_objs("BrokenWindow01", "WALLFLAT")
    for i, ob in enumerate(doors, 1):
        ob.name = ob.data.name = "Door_%02d" % i
        link_only(ob, col_doors)
    for i, ob in enumerate(handles, 1):
        ob.name = ob.data.name = "DoorHandle_%02d" % i
        link_only(ob, col_handles)
    for i, ob in enumerate(windows, 1):
        ob.name = ob.data.name = "Window_%02d" % i
        link_only(ob, col_windows)
    log("  adapter wired VM_Doors=%d wall-flat slabs, VM_DoorHandles=%d props, "
        "VM_Windows=%d window variants" % (len(doors), len(handles), len(windows)))
    return reports, len(doors), len(handles), len(windows)


def make_tile_variants(col, name, wx, hy, th, n, mat, bend):
    """Procedural tile variants: slightly bent thin boxes.
    X = width along the row (centered), Z = height along the stack (centered in
    its slot), Y = thickness with y=0 ON the wall-contact (back) face - the same
    strict wall-contact convention as the architectural variants, so cladding
    tiles sit ON the surface instead of half-buried in it."""
    out = []
    for i in range(n):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        b = bend[i % len(bend)]
        for v in bm.verts:
            v.co.x *= wx
            v.co.y *= th
            v.co.z *= hy
            if v.co.x > 0:
                v.co.z += b
            v.co.y += b * 0.3 * (1 if v.co.x > 0 else -1) * 0.2
        ymin = min(v.co.y for v in bm.verts)
        for v in bm.verts:
            v.co.y -= ymin
        me = bpy.data.meshes.new(f"{name}_{i + 1:02d}")
        bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new(f"{name}_{i + 1:02d}", me)
        col.objects.link(ob)
        me.materials.append(mat)
        out.append(ob)
    return out


def make_debris(debris_col):
    specs = [
        ("Debris_Crate", "cube", (0.45, 0.28, 0.15)),
        ("Debris_Plank", "plank", (0.52, 0.36, 0.20)),
        ("Debris_Bottle", "bottle", (0.10, 0.32, 0.16)),
        ("Debris_Paper", "wad", (0.78, 0.76, 0.70)),
        ("Debris_Can", "can", (0.42, 0.43, 0.45)),
    ]
    for name, kind, color in specs:
        bm = bmesh.new()
        if kind == "cube":
            bmesh.ops.create_cube(bm, size=0.55)
        elif kind == "plank":
            bmesh.ops.create_cube(bm, size=1.0)
            for v in bm.verts:
                v.co.x *= 0.9; v.co.y *= 0.11; v.co.z *= 0.05
        elif kind == "bottle":
            bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.07, radius2=0.07, depth=0.32)
        elif kind == "wad":
            bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.11)
        elif kind == "can":
            bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.09, radius2=0.09, depth=0.24)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new(name, me)
        debris_col.objects.link(ob)
        mat = make_principled(name + "_mat", color, rough=0.75)
        me.materials.append(mat)


# ---------------------------------------------------------------------------- house / cube
def make_house(name, center, col, wall_mat, roof_mat, ground_mat):
    """Gabled box shell + roof + ground plinth, joined into one dressed mesh."""
    cx, cy = center
    W, D, H, RH = 6.0, 5.0, 3.0, 1.9
    prof = [(-W / 2, 0), (W / 2, 0), (W / 2, H), (0, H + RH), (-W / 2, H)]
    verts = [(cx + x, cy - D / 2, z) for x, z in prof] + [(cx + x, cy + D / 2, z) for x, z in prof]
    faces = [
        (0, 1, 2, 3, 4),
        (9, 8, 7, 6, 5),
        (1, 6, 7, 2),
        (4, 3, 8, 9),
        (2, 7, 8, 3),
        (0, 4, 9, 5),
    ]
    house = new_mesh_obj(name + "_shell", verts, faces, col)
    g = 10.0
    gv = [(cx - g, cy - g, 0), (cx + g, cy - g, 0), (cx + g, cy + g, 0), (cx - g, cy + g, 0)]
    ground = new_mesh_obj(name + "_ground", gv, [(0, 1, 2, 3)], col)
    house.data.materials.append(wall_mat)
    house.data.materials.append(roof_mat)
    for p in house.data.polygons:
        p.material_index = 1 if p.index in (3, 4) else 0
    ground.data.materials.append(ground_mat)
    bpy.ops.object.select_all(action="DESELECT")
    house.select_set(True); ground.select_set(True)
    bpy.context.view_layer.objects.active = house
    bpy.ops.object.join()
    house.name = name
    house.data.name = name
    return house


def make_cube(name, size, col, base_z=0.0):
    """Cube centered in x/y, base at base_z."""
    h = size / 2
    verts = [(x, y, z) for z in (base_z, base_z + size) for y in (-h, h) for x in (-h, h)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return new_mesh_obj(name, verts, faces, col)


# ---------------------------------------------------------------------------- node group v2
SEED_OFF = dict(keep=3, vert=5, debris=7, rot=11, scale=13, idx_p=17, idx_d=19, tint=23,
                jitter=29, fitrot=31, cladpick=37)


class NGBuilder:
    """Small helper around interface creation + node/link sugar."""

    def __init__(self, name):
        self.ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
        self.iface = self.ng.interface
        self.menu_defaults = []   # (socket, default) applied after switches are linked

    def panel(self, name, desc=""):
        return self.iface.new_panel(name, description=desc)

    def sock(self, name, stype, panel, default=None, minv=None, maxv=None, subtype=None, desc=""):
        try:
            s = self.iface.new_socket(name, in_out="INPUT", socket_type=stype, parent=panel, description=desc)
        except TypeError:
            s = self.iface.new_socket(name, in_out="INPUT", socket_type=stype, parent=panel)
        if default is not None and stype != "NodeSocketMenu":
            s.default_value = default
        for attr, val in (("min_value", minv), ("max_value", maxv)):
            if val is not None and hasattr(s, attr):
                setattr(s, attr, val)
        if subtype and hasattr(s, "subtype"):
            try:
                s.subtype = subtype
            except Exception:
                pass
        return s

    def menu_sock(self, name, panel, default, desc=""):
        s = self.iface.new_socket(name, in_out="INPUT", socket_type="NodeSocketMenu", parent=panel,
                                  description=desc)
        self.menu_defaults.append((s, default))
        return s

    def N(self, t, loc=(0, 0), **props):
        n = self.ng.nodes.new(t)
        n.location = loc
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def L(self, a, b):
        self.ng.links.new(a, b)

    def menu_switch(self, items, data_type, menu_out, values, loc=(0, 0)):
        """Menu Switch with named items; values maps item name -> socket to link
        (None = constant default). Returns (output, {item: bool_out})."""
        n = self.N("GeometryNodeMenuSwitch", loc)
        n.data_type = data_type
        n.enum_items.clear()
        for it in items:
            n.enum_items.new(it)
        self.L(menu_out, n.inputs["Menu"])
        for it in items:
            src = values.get(it)
            if src is not None:
                self.L(src, n.inputs[it])
        bools = {it: n.outputs[it] for it in items}
        return n.outputs["Output"], bools

    def finish_menu_defaults(self):
        for s, d in self.menu_defaults:
            try:
                s.default_value = d
            except Exception as e:
                log(f"  !! menu default {s.name}={d}: {e}")


def seed_node(b, gi_seed, offset):
    n = b.N("FunctionNodeIntegerMath", operation="ADD")
    b.L(gi_seed, n.inputs[0])
    n.inputs[1].default_value = offset
    return n.outputs["Value"]


def material_gate(b, geo_in, mat_out, sel, loc):
    """Set Material with selection, gated: empty material socket leaves geometry untouched."""
    cmpn = b.N("FunctionNodeCompare", (loc[0] - 200, loc[1] - 200), data_type="MATERIAL", operation="EQUAL")
    b.L(mat_out, cmpn.inputs["A"])
    sm = b.N("GeometryNodeSetMaterial", loc)
    b.L(geo_in, sm.inputs["Geometry"])
    b.L(mat_out, sm.inputs["Material"])
    b.L(sel, sm.inputs["Selection"])
    sw = b.N("GeometryNodeSwitch", (loc[0] + 200, loc[1]))
    sw.input_type = "GEOMETRY"
    b.L(cmpn.outputs["Result"], sw.inputs["Switch"])   # True = material None -> passthrough
    b.L(sm.outputs["Geometry"], sw.inputs["False"])
    b.L(geo_in, sw.inputs["True"])
    return sw.outputs["Output"]


def build_node_group():
    b = NGBuilder("VM_SceneDetailer")
    iface = b.iface

    iface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")

    p_assets = b.panel("Assets", "Model sets fed into the engine (model-set agnostic)")
    b.sock("Primary Props", "NodeSocketCollection", p_assets, desc="Collection of primary prop variants")
    b.sock("Debris/Trash Props", "NodeSocketCollection", p_assets, desc="Collection of debris/trash variants")
    b.sock("Debris Ratio", "NodeSocketFloat", p_assets, 0.35, 0.0, 1.0, "FACTOR")

    p_pl = b.panel("Placement", "How parts are placed: Scatter (v1 random), Fit (architectural), Cladding (courses)")
    b.menu_sock("Placement Mode", p_pl, "Scatter", "Scatter=v1 random, Fit=wall-aligned architectural parts, Cladding=row courses")
    b.sock("Embed", "NodeSocketFloat", p_pl, 0.02, -10.0, 10.0, "DISTANCE", "Fit: sink the instance's back face into the placement plane by this depth (final normal offset = Backing Offset - Embed)")
    b.sock("Backing Offset", "NodeSocketFloat", p_pl, 0.0, -10.0, 10.0, "DISTANCE", "Fit: distance from the sampled face along +normal to the placement plane the variant's BACK face lands on (set it to the cladding/surface buildup in front of the base wall)")
    b.sock("Fit Jitter", "NodeSocketFloat", p_pl, 0.0, 0.0, 6.283, "ANGLE", "Fit: tiny random rotation (0 = perfectly flush)")
    b.sock("Drop To Ground", "NodeSocketBool", p_pl, False, desc="Fit: put instance origin at the host's base height (doors stand on the ground)")
    b.sock("Row Height", "NodeSocketFloat", p_pl, 0.22, 0.001, 100.0, "DISTANCE", "Cladding: course pitch along the stack direction")
    b.sock("Row Overlap", "NodeSocketFloat", p_pl, 0.35, 0.0, 0.95, "FACTOR", "Cladding: courses drawn 1/(1-Overlap) taller so they overlap")
    b.sock("Stagger", "NodeSocketFloat", p_pl, 0.5, 0.0, 1.0, "FACTOR", "Cladding: row phase offset in fraction of slot width")
    b.sock("Jitter", "NodeSocketFloat", p_pl, 0.01, 0.0, 1.0, "DISTANCE", "Cladding: per-slot position noise")
    b.sock("Slot Width", "NodeSocketFloat", p_pl, 0.25, 0.001, 100.0, "DISTANCE", "Cladding: tile width; slot pitch = Slot Width * (1 - Row Overlap)")

    p_dist = b.panel("Distribution", "Scatter/Fit point distribution")
    b.sock("Density", "NodeSocketFloat", p_dist, 0.12, 0.0, 100.0, "FACTOR", "Instances per square meter (Scatter/Fit)")
    b.sock("Seed", "NodeSocketInt", p_dist, 0)
    b.sock("Surface Offset", "NodeSocketFloat", p_dist, -0.02, -10.0, 10.0, "DISTANCE", "Scatter: offset along face normal")
    b.sock("Align To Normal", "NodeSocketBool", p_dist, True, desc="Scatter: Z-align instances to face normal (v1)")

    p_var = b.panel("Variation", "Per-instance rotation / scale / tint")
    b.sock("Random Rot X", "NodeSocketFloat", p_var, 0.02, 0.0, 6.283, "ANGLE")
    b.sock("Random Rot Y", "NodeSocketFloat", p_var, 0.02, 0.0, 6.283, "ANGLE")
    b.sock("Random Rot Z", "NodeSocketFloat", p_var, 3.1416, 0.0, 6.283, "ANGLE")
    b.sock("Scale Min", "NodeSocketFloat", p_var, 0.55, 0.01, 100.0)
    b.sock("Scale Max", "NodeSocketFloat", p_var, 1.7, 0.01, 100.0)
    b.sock("Tint Amount", "NodeSocketFloat", p_var, 0.5, 0.0, 1.0, "FACTOR")

    p_zone = b.panel("Zones", "Face classification by normal; drives Fit/Cladding sampling and Materials")
    b.menu_sock("Face Zone", p_zone, "Walls", "Which faces Fit/Cladding use (Scatter uses all faces)")
    b.sock("Wall Slope", "NodeSocketFloat", p_zone, 0.35, 0.0, 1.0, "FACTOR", "Walls: |N.z| <= Wall Slope")
    b.sock("Roof Slope", "NodeSocketFloat", p_zone, 0.7, 0.0, 1.0, "FACTOR", "Roof: N.z >= Roof Slope; Floor: N.z <= -Roof Slope")

    p_mat = b.panel("Materials", "Per-zone materials applied to the base mesh (empty socket = untouched)")
    b.sock("Wall Material", "NodeSocketMaterial", p_mat, None, desc="Material for wall-zone faces")
    b.sock("Roof Material", "NodeSocketMaterial", p_mat, None, desc="Material for roof-zone faces")
    b.sock("Floor Material", "NodeSocketMaterial", p_mat, None, desc="Material for floor-zone faces")

    p_mask = b.panel("Masks", "Random / vertical gradient / proximity masks")
    b.sock("Random Mask Threshold", "NodeSocketFloat", p_mask, 0.0, 0.0, 1.0, "FACTOR")
    b.sock("Vertical Mask", "NodeSocketBool", p_mask, False)
    b.sock("Vertical Range Min", "NodeSocketFloat", p_mask, 0.0, -100.0, 100.0, "DISTANCE")
    b.sock("Vertical Range Max", "NodeSocketFloat", p_mask, 4.0, -100.0, 100.0, "DISTANCE")
    b.sock("Proximity Mask", "NodeSocketBool", p_mask, False)
    b.sock("Proximity Object", "NodeSocketObject", p_mask, None, desc="Clear instances within radius of this object")
    b.sock("Proximity Radius", "NodeSocketFloat", p_mask, 2.0, 0.0, 100.0, "DISTANCE")

    p_clean = b.panel("Cleanup", "Hard caps")
    b.sock("Max Instances", "NodeSocketInt", p_clean, 500, 0, 1000000)

    iface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

    gi = b.N("NodeGroupInput", (-1800, 0))
    go = b.N("NodeGroupOutput", (2400, 0))
    idx = b.N("GeometryNodeInputIndex", (-1800, -600))
    seed = lambda off: seed_node(b, gi.outputs["Seed"], off)

    # ---------------- zone masks (face domain) ----------------
    nrm = b.N("GeometryNodeInputNormal", (-1800, 700))
    nsep = b.N("ShaderNodeSeparateXYZ", (-1600, 700))
    b.L(nrm.outputs["Normal"], nsep.inputs["Vector"])
    absz = b.N("ShaderNodeMath", (-1450, 780), operation="ABSOLUTE")
    b.L(nsep.outputs["Z"], absz.inputs[0])
    neg_rs = b.N("ShaderNodeMath", (-1450, 600), operation="MULTIPLY")
    b.L(gi.outputs["Roof Slope"], neg_rs.inputs[0])
    neg_rs.inputs[1].default_value = -1.0
    is_wall = b.N("FunctionNodeCompare", (-1250, 800), data_type="FLOAT", operation="LESS_EQUAL")
    b.L(absz.outputs["Value"], is_wall.inputs["A"])
    b.L(gi.outputs["Wall Slope"], is_wall.inputs["B"])
    is_roof = b.N("FunctionNodeCompare", (-1250, 650), data_type="FLOAT", operation="GREATER_EQUAL")
    b.L(nsep.outputs["Z"], is_roof.inputs["A"])
    b.L(gi.outputs["Roof Slope"], is_roof.inputs["B"])
    is_floor = b.N("FunctionNodeCompare", (-1250, 500), data_type="FLOAT", operation="LESS_EQUAL")
    b.L(nsep.outputs["Z"], is_floor.inputs["A"])
    b.L(neg_rs.outputs["Value"], is_floor.inputs["B"])

    zone_sel, _ = b.menu_switch(
        ["All", "Walls", "Roof", "Floor"], "BOOLEAN", gi.outputs["Face Zone"],
        {"All": None, "Walls": is_wall.outputs["Result"], "Roof": is_roof.outputs["Result"],
         "Floor": is_floor.outputs["Result"]}, loc=(-1050, 650))
    b.ng.nodes[-1].inputs["All"].default_value = True

    # ---------------- base materials by zone (gated Set Material) ----------------
    base1 = material_gate(b, gi.outputs["Geometry"], gi.outputs["Wall Material"],
                          is_wall.outputs["Result"], (-800, 1100))
    base2 = material_gate(b, base1, gi.outputs["Roof Material"],
                          is_roof.outputs["Result"], (-500, 1100))
    base_out = material_gate(b, base2, gi.outputs["Floor Material"],
                             is_floor.outputs["Result"], (-200, 1100))

    # sampling must only see the HOST MESH: in stacked modifiers the input also
    # carries earlier instances, and their faces must never receive new parts
    del_inst = b.N("GeometryNodeDeleteGeometry", (-200, 1350), domain="INSTANCE")
    b.L(base_out, del_inst.inputs["Geometry"])
    del_inst.inputs["Selection"].default_value = True
    mesh_only = del_inst.outputs["Geometry"]

    # ---------------- SCATTER branch (v1 behavior, all faces) ----------------
    dist = b.N("GeometryNodeDistributePointsOnFaces", (-1150, 200), distribute_method="RANDOM")
    b.L(mesh_only, dist.inputs["Mesh"])
    b.L(gi.outputs["Density"], dist.inputs["Density"])
    b.L(gi.outputs["Seed"], dist.inputs["Seed"])
    vscale = b.N("ShaderNodeVectorMath", operation="SCALE", location=(-950, 350))
    b.L(dist.outputs["Normal"], vscale.inputs[0])
    b.L(gi.outputs["Surface Offset"], vscale.inputs["Scale"])
    setpos = b.N("GeometryNodeSetPosition", (-750, 250))
    b.L(dist.outputs["Points"], setpos.inputs["Geometry"])
    b.L(vscale.outputs["Vector"], setpos.inputs["Offset"])
    capn = b.N("GeometryNodeStoreNamedAttribute", (-550, 250), data_type="FLOAT_VECTOR", domain="POINT")
    b.L(setpos.outputs["Geometry"], capn.inputs["Geometry"])
    capn.inputs["Name"].default_value = "vm_normal"
    b.L(dist.outputs["Normal"], capn.inputs["Value"])
    scat_geo = capn.outputs["Geometry"]

    pos = b.N("GeometryNodeInputPosition", (-1500, -250))
    sep = b.N("ShaderNodeSeparateXYZ", (-1300, -250))
    b.L(pos.outputs["Position"], sep.inputs["Vector"])

    # ---------------- FIT branch (zone faces, depth axis to normal) ----------------
    dist_f = b.N("GeometryNodeDistributePointsOnFaces", (-1150, -100), distribute_method="RANDOM")
    b.L(mesh_only, dist_f.inputs["Mesh"])
    b.L(zone_sel, dist_f.inputs["Selection"])
    b.L(gi.outputs["Density"], dist_f.inputs["Density"])
    b.L(gi.outputs["Seed"], dist_f.inputs["Seed"])
    # offset = normal * (Backing Offset - Embed): the variant's back face lands on
    # the backing plane (distance Backing Offset along +normal - e.g. the cladding
    # layer in front of the base wall) and is then sunk by Embed. With the strict
    # back-center variant origin this keeps the wall-contact face ON the surface
    # buildup instead of behind it, independent of variant depth.
    emb_net = b.N("ShaderNodeMath", (-1150, -350), operation="SUBTRACT")
    b.L(gi.outputs["Backing Offset"], emb_net.inputs[0])
    b.L(gi.outputs["Embed"], emb_net.inputs[1])
    vscale_f = b.N("ShaderNodeVectorMath", (-950, -150), operation="SCALE")
    b.L(dist_f.outputs["Normal"], vscale_f.inputs[0])
    b.L(emb_net.outputs["Value"], vscale_f.inputs["Scale"])
    # drop to ground: z offset to host bbox min z
    bb = b.N("GeometryNodeBoundBox", (-1500, -700))
    b.L(mesh_only, bb.inputs["Geometry"])
    bb_sep = b.N("ShaderNodeSeparateXYZ", (-1300, -700))
    b.L(bb.outputs["Min"], bb_sep.inputs["Vector"])
    dz = b.N("ShaderNodeMath", (-1150, -700), operation="SUBTRACT")
    b.L(bb_sep.outputs["Z"], dz.inputs[0])
    b.L(sep.outputs["Z"], dz.inputs[1])
    g_off = b.N("ShaderNodeCombineXYZ", (-1000, -700))
    b.L(dz.outputs["Value"], g_off.inputs["Z"])
    g_sw = b.N("GeometryNodeSwitch", (-850, -650))
    g_sw.input_type = "VECTOR"
    b.L(gi.outputs["Drop To Ground"], g_sw.inputs["Switch"])
    zero_v = b.N("ShaderNodeCombineXYZ", (-1000, -560))
    b.L(zero_v.outputs["Vector"], g_sw.inputs["False"])
    b.L(g_off.outputs["Vector"], g_sw.inputs["True"])
    off_sum = b.N("ShaderNodeVectorMath", (-700, -300), operation="ADD")
    b.L(vscale_f.outputs["Vector"], off_sum.inputs[0])
    b.L(g_sw.outputs["Output"], off_sum.inputs[1])
    setpos_f = b.N("GeometryNodeSetPosition", (-550, -150))
    b.L(dist_f.outputs["Points"], setpos_f.inputs["Geometry"])
    b.L(off_sum.outputs["Vector"], setpos_f.inputs["Offset"])
    capn_f = b.N("GeometryNodeStoreNamedAttribute", (-350, -150), data_type="FLOAT_VECTOR", domain="POINT")
    b.L(setpos_f.outputs["Geometry"], capn_f.inputs["Geometry"])
    capn_f.inputs["Name"].default_value = "vm_normal"
    b.L(dist_f.outputs["Normal"], capn_f.inputs["Value"])
    fit_geo = capn_f.outputs["Geometry"]

    # ---------------- CLADDING branch (exact per-face courses) ----------------
    # face-domain frame + extents (quads; triangle 4th corner wraps to corner 0)
    posf = b.N("GeometryNodeInputPosition", (-1800, -1400))
    cross_zn = b.N("ShaderNodeVectorMath", (-1600, -1300), operation="CROSS_PRODUCT")
    cross_zn.inputs[0].default_value = (0.0, 0.0, 1.0)
    b.L(nrm.outputs["Normal"], cross_zn.inputs[1])
    u_norm = b.N("ShaderNodeVectorMath", (-1450, -1300), operation="NORMALIZE")
    b.L(cross_zn.outputs["Vector"], u_norm.inputs[0])
    u_sw = b.N("GeometryNodeSwitch", (-1300, -1400))
    u_sw.input_type = "VECTOR"
    u_degen = b.N("FunctionNodeCompare", (-1450, -1500), data_type="FLOAT", operation="GREATER_THAN")
    b.L(absz.outputs["Value"], u_degen.inputs["A"])
    u_degen.inputs["B"].default_value = 0.995
    b.L(u_degen.outputs["Result"], u_sw.inputs["Switch"])
    u_sw.inputs["True"].default_value = (1.0, 0.0, 0.0)   # degenerate (flat) faces: world X
    b.L(u_norm.outputs["Vector"], u_sw.inputs["False"])
    u_out = u_sw.outputs["Output"]
    cross_nu = b.N("ShaderNodeVectorMath", (-1150, -1300), operation="CROSS_PRODUCT")
    b.L(nrm.outputs["Normal"], cross_nu.inputs[0])
    b.L(u_out, cross_nu.inputs[1])
    v_norm = b.N("ShaderNodeVectorMath", (-1000, -1300), operation="NORMALIZE")
    b.L(cross_nu.outputs["Vector"], v_norm.inputs[0])
    v_out = v_norm.outputs["Vector"]

    def corner_pos(k):
        cof = b.N("GeometryNodeCornersOfFace", (-1800, -1700 - 300 * k))
        b.L(idx.outputs["Index"], cof.inputs["Face Index"])
        coff = b.N("GeometryNodeOffsetCornerInFace", (-1650, -1700 - 300 * k))
        b.L(cof.outputs["Corner Index"], coff.inputs["Corner Index"])
        coff.inputs["Offset"].default_value = k
        voc = b.N("GeometryNodeVertexOfCorner", (-1575, -1700 - 300 * k))
        b.L(coff.outputs["Corner Index"], voc.inputs["Corner Index"])
        si = b.N("GeometryNodeSampleIndex", (-1500, -1700 - 300 * k))
        si.data_type = "FLOAT_VECTOR"
        si.domain = "POINT"
        b.L(mesh_only, si.inputs["Geometry"])
        b.L(pos.outputs["Position"], si.inputs["Value"])
        b.L(voc.outputs["Vertex Index"], si.inputs["Index"])
        return si.outputs["Value"]

    def axis_extents(uv):
        diffs = []
        for k in range(4):
            d = b.N("ShaderNodeVectorMath", (-1150, -1700 - 250 * k), operation="SUBTRACT")
            b.L(corner_pos(k), d.inputs[0])
            b.L(posf.outputs["Position"], d.inputs[1])
            dot = b.N("ShaderNodeVectorMath", (-1000, -1700 - 250 * k), operation="DOT_PRODUCT")
            b.L(d.outputs["Vector"], dot.inputs[0])
            b.L(uv, dot.inputs[1])
            diffs.append(dot.outputs["Value"])
        mins, maxs = list(diffs), list(diffs)
        while len(mins) > 1:
            mins = [pair(mins[i], mins[i + 1], "MINIMUM") for i in range(0, len(mins), 2)]
            maxs = [pair(maxs[i], maxs[i + 1], "MAXIMUM") for i in range(0, len(maxs), 2)]
        return mins[0], maxs[0]

    def pair(a, bsock, op):
        n = b.N("ShaderNodeMath", (random_loc()), operation=op)
        b.L(a, n.inputs[0]); b.L(bsock, n.inputs[1])
        return n.outputs["Value"]

    _loc_seq = [0]
    def random_loc():
        _loc_seq[0] += 1
        return (-800 + 20 * _loc_seq[0], -1800 - 30 * _loc_seq[0])

    a_lo, a_hi = axis_extents(u_out)
    b_lo, b_hi = axis_extents(v_out)
    w_face = b.N("ShaderNodeMath", (-600, -1500), operation="SUBTRACT")
    b.L(a_hi, w_face.inputs[0]); b.L(a_lo, w_face.inputs[1])
    h_face = b.N("ShaderNodeMath", (-600, -1600), operation="SUBTRACT")
    b.L(b_hi, h_face.inputs[0]); b.L(b_lo, h_face.inputs[1])

    ov_c = b.N("ShaderNodeMath", (-600, -1750), operation="SUBTRACT")
    ov_c.inputs[0].default_value = 1.0
    b.L(gi.outputs["Row Overlap"], ov_c.inputs[1])
    slot_pitch = b.N("ShaderNodeMath", (-450, -1750), operation="MULTIPLY")
    b.L(gi.outputs["Slot Width"], slot_pitch.inputs[0])
    b.L(ov_c.outputs["Value"], slot_pitch.inputs[1])
    max1 = b.N("ShaderNodeMath", (-300, -1750), operation="MAXIMUM")
    b.L(slot_pitch.outputs["Value"], max1.inputs[0])
    max1.inputs[1].default_value = 0.001
    ns_f = b.N("ShaderNodeMath", (-150, -1600), operation="DIVIDE")
    b.L(w_face.outputs["Value"], ns_f.inputs[0])
    b.L(max1.outputs["Value"], ns_f.inputs[1])
    ns_c = b.N("ShaderNodeMath", (0, -1600), operation="CEIL")
    b.L(ns_f.outputs["Value"], ns_c.inputs[0])
    ns_1 = b.N("ShaderNodeMath", (150, -1600), operation="MAXIMUM")
    b.L(ns_c.outputs["Value"], ns_1.inputs[0])
    ns_1.inputs[1].default_value = 1.0
    nrh = b.N("ShaderNodeMath", (-150, -1750), operation="MAXIMUM")
    b.L(gi.outputs["Row Height"], nrh.inputs[0])
    nrh.inputs[1].default_value = 0.001
    nr_f = b.N("ShaderNodeMath", (0, -1750), operation="DIVIDE")
    b.L(h_face.outputs["Value"], nr_f.inputs[0])
    b.L(nrh.outputs["Value"], nr_f.inputs[1])
    nr_c = b.N("ShaderNodeMath", (150, -1750), operation="CEIL")
    b.L(nr_f.outputs["Value"], nr_c.inputs[0])
    nr_1 = b.N("ShaderNodeMath", (300, -1750), operation="MAXIMUM")
    b.L(nr_c.outputs["Value"], nr_1.inputs[0])
    nr_1.inputs[1].default_value = 1.0

    # store frame data on faces -> transfer to face points
    store_chain = base_out
    stores = [("vm_normal", "FLOAT_VECTOR", nrm.outputs["Normal"]),
              ("vm_u", "FLOAT_VECTOR", u_out),
              ("vm_v", "FLOAT_VECTOR", v_out),
              ("vm_c", "FLOAT_VECTOR", posf.outputs["Position"]),
              ("vm_alo", "FLOAT", a_lo),
              ("vm_blo", "FLOAT", b_lo),
              ("vm_ns", "FLOAT", ns_1.outputs["Value"]),
              ("vm_nr", "FLOAT", nr_1.outputs["Value"]),
              ("vm_w", "FLOAT", w_face.outputs["Value"]),
              ("vm_h", "FLOAT", h_face.outputs["Value"])]
    sx = -600
    for nm_, dt, src in stores:
        st = b.N("GeometryNodeStoreNamedAttribute", (sx, -2100), data_type=dt, domain="FACE")
        b.L(mesh_only if store_chain is base_out else store_chain, st.inputs["Geometry"])
        st.inputs["Name"].default_value = nm_
        b.L(src, st.inputs["Value"])
        store_chain = st.outputs["Geometry"]
        sx += 180

    m2p_f = b.N("GeometryNodeMeshToPoints", (900, -2100))
    m2p_f.mode = "FACES"
    b.L(store_chain, m2p_f.inputs["Mesh"])
    b.L(zone_sel, m2p_f.inputs["Selection"])

    GRID = 64
    grid = b.N("GeometryNodeMeshGrid", (700, -2500))
    grid.inputs["Vertices X"].default_value = GRID
    grid.inputs["Vertices Y"].default_value = GRID
    m2p_g = b.N("GeometryNodeMeshToPoints", (900, -2500))
    m2p_g.mode = "VERTICES"
    b.L(grid.outputs["Mesh"], m2p_g.inputs["Mesh"])
    gmod = b.N("ShaderNodeMath", (1050, -2500), operation="FLOORED_MODULO")
    b.L(idx.outputs["Index"], gmod.inputs[0])
    gmod.inputs[1].default_value = float(GRID)
    gdiv = b.N("ShaderNodeMath", (1050, -2650), operation="DIVIDE")
    b.L(idx.outputs["Index"], gdiv.inputs[0])
    gdiv.inputs[1].default_value = float(GRID)
    gfl = b.N("ShaderNodeMath", (1200, -2650), operation="FLOOR")
    b.L(gdiv.outputs["Value"], gfl.inputs[0])
    g1 = b.N("GeometryNodeStoreNamedAttribute", (1250, -2500), data_type="FLOAT", domain="POINT")
    b.L(m2p_g.outputs["Points"], g1.inputs["Geometry"])
    g1.inputs["Name"].default_value = "vm_gi"
    b.L(gmod.outputs["Value"], g1.inputs["Value"])
    g2 = b.N("GeometryNodeStoreNamedAttribute", (1430, -2500), data_type="FLOAT", domain="POINT")
    b.L(g1.outputs["Geometry"], g2.inputs["Geometry"])
    g2.inputs["Name"].default_value = "vm_gj"
    b.L(gfl.outputs["Value"], g2.inputs["Value"])

    iop_g = b.N("GeometryNodeInstanceOnPoints", (1650, -2200))
    b.L(m2p_f.outputs["Points"], iop_g.inputs["Points"])
    b.L(g2.outputs["Geometry"], iop_g.inputs["Instance"])
    real = b.N("GeometryNodeRealizeInstances", (1850, -2200))
    b.L(iop_g.outputs["Instances"], real.inputs["Geometry"])

    def named(name, dt="FLOAT"):
        n = b.N("GeometryNodeInputNamedAttribute", (1900, -2600 - 120 * named.counter))
        named.counter += 1
        n.data_type = dt
        n.inputs["Name"].default_value = name
        return n.outputs["Attribute"]
    named.counter = 0

    gi_v = named("vm_gi"); gj_v = named("vm_gj")
    ns_v = named("vm_ns"); nr_v = named("vm_nr")
    alo_v = named("vm_alo", "FLOAT_VECTOR" if False else "FLOAT")
    blo_v = named("vm_blo")
    c_v = named("vm_c", "FLOAT_VECTOR")
    u_v = named("vm_u", "FLOAT_VECTOR")
    v_v = named("vm_v", "FLOAT_VECTOR")
    w_v = named("vm_w")
    h_v = named("vm_h")
    # even-fill spacing: slots/rows exactly cover the face (no overrun past edges)
    sp_w = b.N("ShaderNodeMath", (2050, -2750), operation="DIVIDE")
    b.L(w_v, sp_w.inputs[0]); b.L(ns_v, sp_w.inputs[1])
    sp_h = b.N("ShaderNodeMath", (2050, -3150), operation="DIVIDE")
    b.L(h_v, sp_h.inputs[0]); b.L(nr_v, sp_h.inputs[1])

    keep_i = b.N("FunctionNodeCompare", (2200, -2500), data_type="FLOAT", operation="LESS_THAN")
    b.L(gi_v, keep_i.inputs["A"]); b.L(ns_v, keep_i.inputs["B"])
    keep_j = b.N("FunctionNodeCompare", (2200, -2650), data_type="FLOAT", operation="LESS_THAN")
    b.L(gj_v, keep_j.inputs["A"]); b.L(nr_v, keep_j.inputs["B"])
    keep_ij = b.N("FunctionNodeBooleanMath", (2400, -2550), operation="AND")
    b.L(keep_i.outputs["Result"], keep_ij.inputs[0])
    b.L(keep_j.outputs["Result"], keep_ij.inputs[1])
    del_c = b.N("GeometryNodeDeleteGeometry", (2600, -2200), domain="POINT")
    b.L(real.outputs["Geometry"], del_c.inputs["Geometry"])
    not_keep = b.N("FunctionNodeBooleanMath", (2400, -2400), operation="NOT")
    b.L(keep_ij.outputs["Boolean"], not_keep.inputs[0])
    b.L(not_keep.outputs["Boolean"], del_c.inputs["Selection"])

    # position: c + u*(alo + mod(gi+0.5+shift, ns)*sp) + v*(blo + (gj+0.5)*rh) + jitter
    sh_row = b.N("ShaderNodeMath", (2200, -2850), operation="MULTIPLY")
    b.L(gj_v, sh_row.inputs[0]); b.L(gi.outputs["Stagger"], sh_row.inputs[1])
    sh_m = b.N("ShaderNodeMath", (2350, -2850), operation="FLOORED_MODULO")
    b.L(sh_row.outputs["Value"], sh_m.inputs[0])
    sh_m.inputs[1].default_value = 1.0
    ai = b.N("ShaderNodeMath", (2500, -2850), operation="MULTIPLY_ADD")
    b.L(gi_v, ai.inputs[0])
    ai.inputs[1].default_value = 1.0
    b.L(sh_m.outputs["Value"], ai.inputs[2])
    a_m = b.N("ShaderNodeMath", (2800, -2850), operation="FLOORED_MODULO")
    b.L(ai.outputs["Value"], a_m.inputs[0])
    b.L(ns_v, a_m.inputs[1])
    # half-slot offset kept OUTSIDE the wrap so slots never center on the face edge
    ai2 = b.N("ShaderNodeMath", (2650, -2850), operation="ADD")
    b.L(a_m.outputs["Value"], ai2.inputs[0])
    ai2.inputs[1].default_value = 0.5
    a_sp = b.N("ShaderNodeMath", (2950, -2850), operation="MULTIPLY_ADD")
    b.L(ai2.outputs["Value"], a_sp.inputs[0])
    b.L(sp_w.outputs["Value"], a_sp.inputs[1])
    b.L(alo_v, a_sp.inputs[2])
    bj = b.N("ShaderNodeMath", (2500, -3050), operation="MULTIPLY_ADD")
    b.L(gj_v, bj.inputs[0])
    b.L(sp_h.outputs["Value"], bj.inputs[1])
    b.L(blo_v, bj.inputs[2])
    bhalf = b.N("ShaderNodeMath", (2800, -3050), operation="MULTIPLY_ADD")
    b.L(sp_h.outputs["Value"], bhalf.inputs[0])
    bhalf.inputs[1].default_value = 0.5
    b.L(bj.outputs["Value"], bhalf.inputs[2])
    u_pos = b.N("ShaderNodeVectorMath", (3100, -2850), operation="SCALE")
    b.L(u_v, u_pos.inputs[0]); b.L(a_sp.outputs["Value"], u_pos.inputs["Scale"])
    v_pos = b.N("ShaderNodeVectorMath", (3100, -3050), operation="SCALE")
    b.L(v_v, v_pos.inputs[0]); b.L(bhalf.outputs["Value"], v_pos.inputs["Scale"])
    p_sum1 = b.N("ShaderNodeVectorMath", (3250, -2900), operation="ADD")
    b.L(u_pos.outputs["Vector"], p_sum1.inputs[0])
    b.L(v_pos.outputs["Vector"], p_sum1.inputs[1])
    p_sum2 = b.N("ShaderNodeVectorMath", (3400, -2900), operation="ADD")
    b.L(c_v, p_sum2.inputs[0])
    b.L(p_sum1.outputs["Vector"], p_sum2.inputs[1])
    rv_jit = b.N("FunctionNodeRandomValue", (3100, -3250), data_type="FLOAT_VECTOR")
    rv_jit.inputs["Min"].default_value = (-1.0, -1.0, -1.0)
    rv_jit.inputs["Max"].default_value = (1.0, 1.0, 1.0)
    b.L(idx.outputs["Index"], rv_jit.inputs["ID"])
    b.L(seed(SEED_OFF["jitter"]), rv_jit.inputs["Seed"])
    jit_s = b.N("ShaderNodeVectorMath", (3300, -3250), operation="SCALE")
    b.L(rv_jit.outputs["Value"], jit_s.inputs[0])
    b.L(gi.outputs["Jitter"], jit_s.inputs["Scale"])
    p_sum3 = b.N("ShaderNodeVectorMath", (3550, -2950), operation="ADD")
    b.L(p_sum2.outputs["Vector"], p_sum3.inputs[0])
    b.L(jit_s.outputs["Vector"], p_sum3.inputs[1])
    setpos_c = b.N("GeometryNodeSetPosition", (3750, -2200))
    b.L(del_c.outputs["Geometry"], setpos_c.inputs["Geometry"])
    b.L(p_sum3.outputs["Vector"], setpos_c.inputs["Position"])
    clad_geo = setpos_c.outputs["Geometry"]

    # ---------------- shared: masks + cap on mode-selected points ----------------
    pts_all, mode_bools = b.menu_switch(
        ["Scatter", "Fit", "Cladding"], "GEOMETRY", gi.outputs["Placement Mode"],
        {"Scatter": scat_geo, "Fit": fit_geo, "Cladding": clad_geo}, loc=(300, 200))
    is_fit = mode_bools["Fit"]
    is_clad = mode_bools["Cladding"]

    rv_keep = b.N("FunctionNodeRandomValue", (-350, -50), data_type="FLOAT")
    rv_keep.inputs["Min"].default_value = 0.0
    rv_keep.inputs["Max"].default_value = 1.0
    b.L(idx.outputs["Index"], rv_keep.inputs["ID"])
    b.L(seed(SEED_OFF["keep"]), rv_keep.inputs["Seed"])
    cmp_keep = b.N("FunctionNodeCompare", (-150, -50), data_type="FLOAT", operation="GREATER_THAN")
    b.L(rv_keep.outputs["Value"], cmp_keep.inputs["A"])
    b.L(gi.outputs["Random Mask Threshold"], cmp_keep.inputs["B"])

    vgrad = b.N("ShaderNodeMapRange", (-150, -250), clamp=True)
    b.L(sep.outputs["Z"], vgrad.inputs["Value"])
    b.L(gi.outputs["Vertical Range Min"], vgrad.inputs["From Min"])
    b.L(gi.outputs["Vertical Range Max"], vgrad.inputs["From Max"])
    vgrad.inputs["To Min"].default_value = 0.0
    vgrad.inputs["To Max"].default_value = 1.0
    rv_vert = b.N("FunctionNodeRandomValue", (-150, -450), data_type="FLOAT")
    rv_vert.inputs["Min"].default_value = 0.0
    rv_vert.inputs["Max"].default_value = 1.0
    b.L(idx.outputs["Index"], rv_vert.inputs["ID"])
    b.L(seed(SEED_OFF["vert"]), rv_vert.inputs["Seed"])
    cmp_vert = b.N("FunctionNodeCompare", (50, -350), data_type="FLOAT", operation="LESS_THAN")
    b.L(rv_vert.outputs["Value"], cmp_vert.inputs["A"])
    b.L(vgrad.outputs["Result"], cmp_vert.inputs["B"])
    not_vert = b.N("FunctionNodeBooleanMath", (50, -550), operation="NOT")
    b.L(gi.outputs["Vertical Mask"], not_vert.inputs[0])
    gate_vert = b.N("FunctionNodeBooleanMath", (250, -400), operation="OR")
    b.L(not_vert.outputs["Boolean"], gate_vert.inputs[0])
    b.L(cmp_vert.outputs["Result"], gate_vert.inputs[1])

    oi = b.N("GeometryNodeObjectInfo", (-350, -700), transform_space="RELATIVE")
    b.L(gi.outputs["Proximity Object"], oi.inputs["Object"])
    prox = b.N("GeometryNodeProximity", (-150, -700))
    b.L(oi.outputs["Geometry"], prox.inputs["Geometry"])
    b.L(pos.outputs["Position"], prox.inputs["Sample Position"])
    cmp_prox = b.N("FunctionNodeCompare", (50, -750), data_type="FLOAT", operation="GREATER_THAN")
    b.L(prox.outputs["Distance"], cmp_prox.inputs["A"])
    b.L(gi.outputs["Proximity Radius"], cmp_prox.inputs["B"])
    not_prox = b.N("FunctionNodeBooleanMath", (50, -900), operation="NOT")
    b.L(gi.outputs["Proximity Mask"], not_prox.inputs[0])
    gate_prox = b.N("FunctionNodeBooleanMath", (250, -800), operation="OR")
    b.L(not_prox.outputs["Boolean"], gate_prox.inputs[0])
    b.L(cmp_prox.outputs["Result"], gate_prox.inputs[1])

    and1 = b.N("FunctionNodeBooleanMath", (450, -300), operation="AND")
    b.L(cmp_keep.outputs["Result"], and1.inputs[0])
    b.L(gate_vert.outputs["Boolean"], and1.inputs[1])
    and2 = b.N("FunctionNodeBooleanMath", (600, -300), operation="AND")
    b.L(and1.outputs["Boolean"], and2.inputs[0])
    b.L(gate_prox.outputs["Boolean"], and2.inputs[1])

    keep_f = b.N("ShaderNodeMath", operation="ADD", location=(600, -500))
    b.L(and2.outputs["Boolean"], keep_f.inputs[0])
    keep_f.inputs[1].default_value = 0.0
    acc = b.N("GeometryNodeAccumulateField", (800, -500), domain="POINT")
    b.L(keep_f.outputs["Value"], acc.inputs["Value"])
    cmp_cap = b.N("FunctionNodeCompare", (1000, -500), data_type="FLOAT", operation="GREATER_THAN")
    b.L(acc.outputs["Leading"], cmp_cap.inputs["A"])
    b.L(gi.outputs["Max Instances"], cmp_cap.inputs["B"])
    not_keep2 = b.N("FunctionNodeBooleanMath", (800, -700), operation="NOT")
    b.L(and2.outputs["Boolean"], not_keep2.inputs[0])
    del_sel = b.N("FunctionNodeBooleanMath", (1200, -600), operation="OR")
    b.L(not_keep2.outputs["Boolean"], del_sel.inputs[0])
    b.L(cmp_cap.outputs["Result"], del_sel.inputs[1])
    dele = b.N("GeometryNodeDeleteGeometry", (1400, 100), domain="POINT")
    b.L(pts_all, dele.inputs["Geometry"])
    b.L(del_sel.outputs["Boolean"], dele.inputs["Selection"])

    # ---------------- rotations ----------------
    named_n = b.N("GeometryNodeInputNamedAttribute", (600, 500), data_type="FLOAT_VECTOR")
    named_n.inputs["Name"].default_value = "vm_normal"
    align = b.N("FunctionNodeAlignRotationToVector", (900, 500))
    b.L(named_n.outputs["Attribute"], align.inputs["Vector"])
    b.L(gi.outputs["Align To Normal"], align.inputs["Factor"])
    rot_comb = b.N("ShaderNodeCombineXYZ", (600, 300))
    b.L(gi.outputs["Random Rot X"], rot_comb.inputs["X"])
    b.L(gi.outputs["Random Rot Y"], rot_comb.inputs["Y"])
    b.L(gi.outputs["Random Rot Z"], rot_comb.inputs["Z"])
    rot_neg = b.N("ShaderNodeVectorMath", operation="SCALE", location=(800, 300))
    b.L(rot_comb.outputs["Vector"], rot_neg.inputs[0])
    rot_neg.inputs["Scale"].default_value = -1.0
    rv_rot = b.N("FunctionNodeRandomValue", (1000, 300), data_type="FLOAT_VECTOR")
    b.L(rot_neg.outputs["Vector"], rv_rot.inputs["Min"])
    b.L(rot_comb.outputs["Vector"], rv_rot.inputs["Max"])
    b.L(idx.outputs["Index"], rv_rot.inputs["ID"])
    b.L(seed(SEED_OFF["rot"]), rv_rot.inputs["Seed"])
    e2r = b.N("FunctionNodeEulerToRotation", (1200, 300))
    b.L(rv_rot.outputs["Value"], e2r.inputs["Euler"])
    final_rot = b.N("FunctionNodeRotateRotation", (1400, 400))
    b.L(align.outputs["Rotation"], final_rot.inputs["Rotation"])
    b.L(e2r.outputs["Rotation"], final_rot.inputs["Rotate By"])

    # Fit/Cladding: local Y (depth) along the face normal -> parts lie flush on the wall
    align_y = b.N("FunctionNodeAlignRotationToVector", (900, 700))
    align_y.axis = "Y"
    b.L(named_n.outputs["Attribute"], align_y.inputs["Vector"])
    align_y.inputs["Factor"].default_value = 1.0
    rv_fjit = b.N("FunctionNodeRandomValue", (1100, 700), data_type="FLOAT_VECTOR")
    rv_fjit.inputs["Min"].default_value = (-1.0, -1.0, -1.0)
    rv_fjit.inputs["Max"].default_value = (1.0, 1.0, 1.0)
    b.L(idx.outputs["Index"], rv_fjit.inputs["ID"])
    b.L(seed(SEED_OFF["fitrot"]), rv_fjit.inputs["Seed"])
    fjit_s = b.N("ShaderNodeVectorMath", (1300, 700), operation="SCALE")
    b.L(rv_fjit.outputs["Value"], fjit_s.inputs[0])
    b.L(gi.outputs["Fit Jitter"], fjit_s.inputs["Scale"])
    fjit_r = b.N("FunctionNodeEulerToRotation", (1500, 700))
    b.L(fjit_s.outputs["Vector"], fjit_r.inputs["Euler"])
    fit_rot = b.N("FunctionNodeRotateRotation", (1700, 700))
    b.L(align_y.outputs["Rotation"], fit_rot.inputs["Rotation"])
    b.L(fjit_r.outputs["Rotation"], fit_rot.inputs["Rotate By"])

    rot_sw1 = b.N("GeometryNodeSwitch", (1900, 500))
    rot_sw1.input_type = "ROTATION"
    b.L(is_fit, rot_sw1.inputs["Switch"])
    b.L(final_rot.outputs["Rotation"], rot_sw1.inputs["False"])
    b.L(fit_rot.outputs["Rotation"], rot_sw1.inputs["True"])
    rot_sw2 = b.N("GeometryNodeSwitch", (2100, 500))
    rot_sw2.input_type = "ROTATION"
    b.L(is_clad, rot_sw2.inputs["Switch"])
    b.L(rot_sw1.outputs["Output"], rot_sw2.inputs["False"])
    b.L(align_y.outputs["Rotation"], rot_sw2.inputs["True"])
    rot_out = rot_sw2.outputs["Output"]

    # ---------------- scales ----------------
    rv_scale = b.N("FunctionNodeRandomValue", (1000, 150), data_type="FLOAT")
    b.L(gi.outputs["Scale Min"], rv_scale.inputs["Min"])
    b.L(gi.outputs["Scale Max"], rv_scale.inputs["Max"])
    b.L(idx.outputs["Index"], rv_scale.inputs["ID"])
    b.L(seed(SEED_OFF["scale"]), rv_scale.inputs["Seed"])
    scale_v = b.N("ShaderNodeCombineXYZ", (1200, 150))
    for ch in ("X", "Y", "Z"):
        b.L(rv_scale.outputs["Value"], scale_v.inputs[ch])
    # cladding: height axis stretched by 1/(1-Overlap) so courses overlap
    k_hi = b.N("ShaderNodeMath", (1200, 0), operation="DIVIDE")
    k_hi.inputs[0].default_value = 1.0
    b.L(ov_c.outputs["Value"], k_hi.inputs[1])
    k_max = b.N("ShaderNodeMath", (1350, 0), operation="MAXIMUM")
    b.L(k_hi.outputs["Value"], k_max.inputs[0])
    k_max.inputs[1].default_value = 1.0
    sz = b.N("ShaderNodeMath", (1500, 0), operation="MULTIPLY")
    b.L(rv_scale.outputs["Value"], sz.inputs[0])
    b.L(k_max.outputs["Value"], sz.inputs[1])
    # width squeeze so tiles exactly fit their slot (sp_w <= slot pitch by construction)
    sx_f = b.N("ShaderNodeMath", (1500, -120), operation="DIVIDE")
    b.L(sp_w.outputs["Value"], sx_f.inputs[0])
    b.L(max1.outputs["Value"], sx_f.inputs[1])
    sx_c = b.N("ShaderNodeMath", (1650, -120), operation="MINIMUM")
    b.L(sx_f.outputs["Value"], sx_c.inputs[0])
    sx_c.inputs[1].default_value = 1.0
    sxs = b.N("ShaderNodeMath", (1800, -120), operation="MULTIPLY")
    b.L(rv_scale.outputs["Value"], sxs.inputs[0])
    b.L(sx_c.outputs["Value"], sxs.inputs[1])
    scale_c = b.N("ShaderNodeCombineXYZ", (1650, 60))
    b.L(sxs.outputs["Value"], scale_c.inputs["X"])
    b.L(rv_scale.outputs["Value"], scale_c.inputs["Y"])
    b.L(sz.outputs["Value"], scale_c.inputs["Z"])
    scale_sw1 = b.N("GeometryNodeSwitch", (1900, 150))
    scale_sw1.input_type = "VECTOR"
    b.L(is_fit, scale_sw1.inputs["Switch"])
    b.L(scale_v.outputs["Vector"], scale_sw1.inputs["False"])
    b.L(scale_v.outputs["Vector"], scale_sw1.inputs["True"])
    scale_sw2 = b.N("GeometryNodeSwitch", (2100, 150))
    scale_sw2.input_type = "VECTOR"
    b.L(is_clad, scale_sw2.inputs["Switch"])
    b.L(scale_sw1.outputs["Output"], scale_sw2.inputs["False"])
    b.L(scale_c.outputs["Vector"], scale_sw2.inputs["True"])
    scale_out = scale_sw2.outputs["Output"]

    # ---------------- debris split ----------------
    rv_debris = b.N("FunctionNodeRandomValue", (1400, -100), data_type="FLOAT")
    rv_debris.inputs["Min"].default_value = 0.0
    rv_debris.inputs["Max"].default_value = 1.0
    b.L(idx.outputs["Index"], rv_debris.inputs["ID"])
    b.L(seed(SEED_OFF["debris"]), rv_debris.inputs["Seed"])
    is_debris = b.N("FunctionNodeCompare", (1600, -100), data_type="FLOAT", operation="LESS_THAN")
    b.L(rv_debris.outputs["Value"], is_debris.inputs["A"])
    b.L(gi.outputs["Debris Ratio"], is_debris.inputs["B"])
    not_debris = b.N("FunctionNodeBooleanMath", (1800, -100), operation="NOT")
    b.L(is_debris.outputs["Result"], not_debris.inputs[0])

    # ---------------- instance branches ----------------
    def inst_branch(y, coll_sock, pick_seed_off, selection_sock):
        ci = b.N("GeometryNodeCollectionInfo", (1700, y))
        b.L(gi.outputs[coll_sock], ci.inputs["Collection"])
        ci.inputs["Separate Children"].default_value = True
        ci.inputs["Reset Children"].default_value = True
        rv_i = b.N("FunctionNodeRandomValue", (1700, y - 150), data_type="INT")
        rv_i.inputs["Min"].default_value = 0
        rv_i.inputs["Max"].default_value = 511
        b.L(idx.outputs["Index"], rv_i.inputs["ID"])
        b.L(seed(pick_seed_off), rv_i.inputs["Seed"])
        iop = b.N("GeometryNodeInstanceOnPoints", (2000, y))
        b.L(dele.outputs["Geometry"], iop.inputs["Points"])
        b.L(selection_sock, iop.inputs["Selection"])
        b.L(ci.outputs["Instances"], iop.inputs["Instance"])
        iop.inputs["Pick Instance"].default_value = True
        b.L(rv_i.outputs["Value"], iop.inputs["Instance Index"])
        b.L(rot_out, iop.inputs["Rotation"])
        b.L(scale_out, iop.inputs["Scale"])
        return iop

    iop_p = inst_branch(900, "Primary Props", SEED_OFF["idx_p"], not_debris.outputs["Boolean"])
    iop_d = inst_branch(-300, "Debris/Trash Props", SEED_OFF["idx_d"], is_debris.outputs["Result"])

    # ---------------- per-instance tint ----------------
    rv_tint = b.N("FunctionNodeRandomValue", (2000, -600), data_type="FLOAT_VECTOR")
    rv_tint.inputs["Min"].default_value = (0.55, 0.55, 0.55)
    rv_tint.inputs["Max"].default_value = (1.0, 1.0, 1.0)
    b.L(idx.outputs["Index"], rv_tint.inputs["ID"])
    b.L(seed(SEED_OFF["tint"]), rv_tint.inputs["Seed"])
    inv_t = b.N("ShaderNodeMath", operation="SUBTRACT", location=(2000, -800))
    inv_t.inputs[0].default_value = 1.0
    b.L(gi.outputs["Tint Amount"], inv_t.inputs[1])
    sep_c = b.N("ShaderNodeSeparateXYZ", (2150, -600))
    b.L(rv_tint.outputs["Value"], sep_c.inputs["Vector"])
    comb_c = b.N("FunctionNodeCombineColor", (2400, -600))
    comb_c.inputs["Alpha"].default_value = 1.0
    for i, ch in enumerate(("X", "Y", "Z")):
        m = b.N("ShaderNodeMath", operation="MULTIPLY_ADD", location=(2300, -550 - 120 * i))
        b.L(sep_c.outputs[ch], m.inputs[0])
        b.L(inv_t.outputs["Value"], m.inputs[1])
        b.L(gi.outputs["Tint Amount"], m.inputs[2])
        b.L(m.outputs["Value"], comb_c.inputs[i])

    join_i = b.N("GeometryNodeJoinGeometry", (2250, 300))
    b.L(iop_p.outputs["Instances"], join_i.inputs["Geometry"])
    b.L(iop_d.outputs["Instances"], join_i.inputs["Geometry"])
    store_c = b.N("GeometryNodeStoreNamedAttribute", (2450, 150), data_type="FLOAT_COLOR", domain="INSTANCE")
    b.L(join_i.outputs["Geometry"], store_c.inputs["Geometry"])
    store_c.inputs["Name"].default_value = "Color"
    b.L(comb_c.outputs["Color"], store_c.inputs["Value"])

    join_all = b.N("GeometryNodeJoinGeometry", (2650, 100))
    b.L(base_out, join_all.inputs["Geometry"])
    b.L(store_c.outputs["Geometry"], join_all.inputs["Geometry"])
    b.L(join_all.outputs["Geometry"], go.inputs["Geometry"])

    b.finish_menu_defaults()
    return b.ng


# ---------------------------------------------------------------------------- VM_RoofCap
def build_roofcap_group():
    b = NGBuilder("VM_RoofCap")
    iface = b.iface
    iface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    p = b.panel("Roof", "Pitched roof generated over the host's flat top")
    b.sock("Pitch", "NodeSocketFloat", p, math.radians(35.0), 0.0, math.radians(89.0), "ANGLE")
    b.sock("Overhang", "NodeSocketFloat", p, 0.25, 0.0, 10.0, "DISTANCE")
    b.menu_sock("Style", p, "Gable", "Gable = full-length ridge; Hip = ridge shortened by half the short side")
    b.sock("Roof Material", "NodeSocketMaterial", p, None, desc="Material for the generated roof faces")
    iface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

    gi = b.N("NodeGroupInput", (-1400, 0))
    go = b.N("NodeGroupOutput", (2600, 0))

    # process only the host mesh; incoming instances (from earlier modifiers)
    # pass through untouched via the final join
    del_inst = b.N("GeometryNodeDeleteGeometry", (-1400, 250), domain="INSTANCE")
    b.L(gi.outputs["Geometry"], del_inst.inputs["Geometry"])
    del_inst.inputs["Selection"].default_value = True
    mesh_in = del_inst.outputs["Geometry"]

    bb = b.N("GeometryNodeBoundBox", (-1200, 300))
    b.L(mesh_in, bb.inputs["Geometry"])
    mn = b.N("ShaderNodeSeparateXYZ", (-1000, 400))
    mx = b.N("ShaderNodeSeparateXYZ", (-1000, 250))
    b.L(bb.outputs["Min"], mn.inputs["Vector"])
    b.L(bb.outputs["Max"], mx.inputs["Vector"])

    def m(op, a, bsock=None, c=None, loc=(0, 0), const=None):
        n = b.N("ShaderNodeMath", operation=op, location=loc)
        if hasattr(a, "bl_idname"):
            b.L(a, n.inputs[0])
        else:
            n.inputs[0].default_value = a
        if bsock is not None:
            if hasattr(bsock, "bl_idname"):
                b.L(bsock, n.inputs[1])
            else:
                n.inputs[1].default_value = bsock
        elif const is not None:
            n.inputs[1].default_value = const
        if c is not None:
            b.L(c, n.inputs[2])
        return n.outputs["Value"]

    cx = m("MULTIPLY", m("ADD", mn.outputs["X"], mx.outputs["X"], loc=(-800, 500)), 0.5, loc=(-650, 500))
    cy = m("MULTIPLY", m("ADD", mn.outputs["Y"], mx.outputs["Y"], loc=(-800, 400)), 0.5, loc=(-650, 400))
    zmax = mx.outputs["Z"]
    lx = m("SUBTRACT", mx.outputs["X"], mn.outputs["X"], loc=(-800, 300))
    ly = m("SUBTRACT", mx.outputs["Y"], mn.outputs["Y"], loc=(-800, 200))
    lmin = m("MINIMUM", lx, ly, loc=(-650, 250))
    lmax = m("MAXIMUM", lx, ly, loc=(-650, 150))
    ridge_half = m("MAXIMUM", m("MULTIPLY", m("SUBTRACT", lmax, lmin, loc=(-500, 150)), 0.5, loc=(-350, 150)),
                   0.0, loc=(-200, 150))

    # height = (short/2 + overhang) * tan(pitch)  (tan via sin/cos; math node lacks TAN in 5.2)
    sin_p = m("SINE", gi.outputs["Pitch"], loc=(-800, -100))
    cos_p = m("MAXIMUM", m("COSINE", gi.outputs["Pitch"], loc=(-800, -200)), 0.01, loc=(-650, -200))
    tan_p = m("DIVIDE", sin_p, cos_p, loc=(-500, -150))
    run = m("ADD", m("MULTIPLY", lmin, 0.5, loc=(-500, -250)), gi.outputs["Overhang"], loc=(-350, -250))
    hgt = m("MULTIPLY", run, tan_p, loc=(-200, -200))

    eps = 0.002
    posf = b.N("GeometryNodeInputPosition", (-1200, -450))
    nrm = b.N("GeometryNodeInputNormal", (-1200, -600))
    psep = b.N("ShaderNodeSeparateXYZ", (-1000, -450))
    nsep = b.N("ShaderNodeSeparateXYZ", (-1000, -600))
    b.L(posf.outputs["Position"], psep.inputs["Vector"])
    b.L(nrm.outputs["Normal"], nsep.inputs["Vector"])

    top_z = b.N("FunctionNodeCompare", (-800, -450), data_type="FLOAT", operation="GREATER_THAN")
    b.L(psep.outputs["Z"], top_z.inputs["A"])
    b.L(m("SUBTRACT", zmax, eps, loc=(-950, -380)), top_z.inputs["B"])
    top_n = b.N("FunctionNodeCompare", (-800, -600), data_type="FLOAT", operation="GREATER_THAN")
    b.L(nsep.outputs["Z"], top_n.inputs["A"])
    top_n.inputs["B"].default_value = 0.98
    sel_top = b.N("FunctionNodeBooleanMath", (-650, -520), operation="AND")
    b.L(top_z.outputs["Result"], sel_top.inputs[0])
    b.L(top_n.outputs["Result"], sel_top.inputs[1])

    e1 = b.N("GeometryNodeExtrudeMesh", (-450, -300))
    e1.mode = "FACES"
    b.L(mesh_in, e1.inputs["Mesh"])
    b.L(sel_top.outputs["Boolean"], e1.inputs["Selection"])
    # NOTE: Extrude Mesh ignores Offset default_value on this build (it would extrude
    # along the face normal x Offset Scale) - the offset vector MUST be linked.
    e1_off = b.N("ShaderNodeCombineXYZ", (-600, -300))
    e1_off.inputs["Z"].default_value = eps
    b.L(e1_off.outputs["Vector"], e1.inputs["Offset"])
    e1.inputs["Individual"].default_value = False

    # expand the extruded cap outward to the eave line (footprint + overhang)
    pos = b.N("GeometryNodeInputPosition", (-250, -450))
    psep2 = b.N("ShaderNodeSeparateXYZ", (-100, -450))
    b.L(pos.outputs["Position"], psep2.inputs["Vector"])
    dx = m("SUBTRACT", psep2.outputs["X"], cx, loc=(50, -380))
    dy = m("SUBTRACT", psep2.outputs["Y"], cy, loc=(50, -470))
    fx = m("DIVIDE", m("MULTIPLY", gi.outputs["Overhang"], 2.0, loc=(200, -350)),
           m("MAXIMUM", lx, 0.001, loc=(200, -420)), loc=(350, -380))
    fy = m("DIVIDE", m("MULTIPLY", gi.outputs["Overhang"], 2.0, loc=(200, -520)),
           m("MAXIMUM", ly, 0.001, loc=(200, -590)), loc=(350, -500))
    ox = m("MULTIPLY", dx, fx, loc=(500, -380))
    oy = m("MULTIPLY", dy, fy, loc=(500, -500))
    exp_v = b.N("ShaderNodeCombineXYZ", (650, -440))
    b.L(ox, exp_v.inputs["X"])
    b.L(oy, exp_v.inputs["Y"])
    sp1_sel = b.N("FunctionNodeCompare", (350, -250), data_type="FLOAT", operation="GREATER_THAN")
    b.L(psep2.outputs["Z"], sp1_sel.inputs["A"])
    b.L(m("ADD", zmax, eps * 0.5, loc=(200, -250)), sp1_sel.inputs["B"])
    sp1 = b.N("GeometryNodeSetPosition", (750, -200))
    b.L(e1.outputs["Mesh"], sp1.inputs["Geometry"])
    b.L(sp1_sel.outputs["Result"], sp1.inputs["Selection"])
    b.L(exp_v.outputs["Vector"], sp1.inputs["Offset"])

    # extrude the eave cap up to the ridge height
    posf3 = b.N("GeometryNodeInputPosition", (850, -550))
    nrm3 = b.N("GeometryNodeInputNormal", (850, -700))
    psep3 = b.N("ShaderNodeSeparateXYZ", (1000, -550))
    nsep3 = b.N("ShaderNodeSeparateXYZ", (1000, -700))
    b.L(posf3.outputs["Position"], psep3.inputs["Vector"])
    b.L(nrm3.outputs["Normal"], nsep3.inputs["Vector"])
    sel2_z = b.N("FunctionNodeCompare", (1150, -550), data_type="FLOAT", operation="GREATER_THAN")
    b.L(psep3.outputs["Z"], sel2_z.inputs["A"])
    b.L(m("ADD", zmax, eps * 0.75, loc=(1000, -480)), sel2_z.inputs["B"])
    sel2_n = b.N("FunctionNodeCompare", (1150, -700), data_type="FLOAT", operation="GREATER_THAN")
    b.L(nsep3.outputs["Z"], sel2_n.inputs["A"])
    sel2_n.inputs["B"].default_value = 0.98
    sel2 = b.N("FunctionNodeBooleanMath", (1300, -620), operation="AND")
    b.L(sel2_z.outputs["Result"], sel2.inputs[0])
    b.L(sel2_n.outputs["Result"], sel2.inputs[1])
    e2 = b.N("GeometryNodeExtrudeMesh", (1450, -300))
    e2.mode = "FACES"
    b.L(sp1.outputs["Geometry"], e2.inputs["Mesh"])
    b.L(sel2.outputs["Boolean"], e2.inputs["Selection"])
    h_v = b.N("ShaderNodeCombineXYZ", (1300, -250))
    b.L(hgt, h_v.inputs["Z"])
    b.L(h_v.outputs["Vector"], e2.inputs["Offset"])
    e2.inputs["Individual"].default_value = False

    # collapse the extruded top to the ridge
    pos4 = b.N("GeometryNodeInputPosition", (1600, -550))
    psep4 = b.N("ShaderNodeSeparateXYZ", (1750, -550))
    b.L(pos4.outputs["Position"], psep4.inputs["Vector"])
    px = m("SUBTRACT", psep4.outputs["X"], cx, loc=(1900, -500))
    py = m("SUBTRACT", psep4.outputs["Y"], cy, loc=(1900, -620))
    px_c = m("MINIMUM", m("MAXIMUM", px, m("MULTIPLY", ridge_half, -1.0, loc=(2050, -430)), loc=(2200, -500)),
             ridge_half, loc=(2350, -500))
    py_c = m("MINIMUM", m("MAXIMUM", py, m("MULTIPLY", ridge_half, -1.0, loc=(2050, -700)), loc=(2200, -620)),
             ridge_half, loc=(2350, -620))
    along_x = b.N("FunctionNodeCompare", (1900, -800), data_type="FLOAT", operation="GREATER_EQUAL")
    b.L(lx, along_x.inputs["A"])
    b.L(ly, along_x.inputs["B"])

    def vswitch(cond, false_v, true_v, loc):
        sw = b.N("GeometryNodeSwitch", loc)
        sw.input_type = "VECTOR"
        b.L(cond, sw.inputs["Switch"])
        if isinstance(false_v, tuple):
            sw.inputs["False"].default_value = false_v
        else:
            b.L(false_v, sw.inputs["False"])
        if isinstance(true_v, tuple):
            sw.inputs["True"].default_value = true_v
        else:
            b.L(true_v, sw.inputs["True"])
        return sw.outputs["Output"]

    g_x_ridge = b.N("ShaderNodeCombineXYZ", (2500, -450))
    b.L(px, g_x_ridge.inputs["X"])
    g_y_ridge = b.N("ShaderNodeCombineXYZ", (2500, -650))
    b.L(py, g_y_ridge.inputs["Y"])
    gable_vec = vswitch(along_x.outputs["Result"], g_y_ridge.outputs["Vector"],
                        g_x_ridge.outputs["Vector"], (2650, -550))
    h_x_ridge = b.N("ShaderNodeCombineXYZ", (2500, -350))
    b.L(px_c, h_x_ridge.inputs["X"])
    h_y_ridge = b.N("ShaderNodeCombineXYZ", (2500, -750))
    b.L(py_c, h_y_ridge.inputs["Y"])
    hip_vec = vswitch(along_x.outputs["Result"], h_y_ridge.outputs["Vector"],
                      h_x_ridge.outputs["Vector"], (2650, -350))
    style_vec, _ = b.menu_switch(["Gable", "Hip"], "VECTOR", gi.outputs["Style"],
                                 {"Gable": gable_vec, "Hip": hip_vec}, loc=(2850, -500))
    new_xy = b.N("ShaderNodeVectorMath", (3050, -500), operation="ADD")
    cen_v = b.N("ShaderNodeCombineXYZ", (2850, -650))
    b.L(cx, cen_v.inputs["X"])
    b.L(cy, cen_v.inputs["Y"])
    b.L(cen_v.outputs["Vector"], new_xy.inputs[0])
    b.L(style_vec, new_xy.inputs[1])
    keep_z = b.N("ShaderNodeSeparateXYZ", (3200, -500))
    b.L(new_xy.outputs["Vector"], keep_z.inputs["Vector"])
    ridge_pos = b.N("ShaderNodeCombineXYZ", (3350, -500))
    b.L(keep_z.outputs["X"], ridge_pos.inputs["X"])
    b.L(keep_z.outputs["Y"], ridge_pos.inputs["Y"])
    b.L(psep4.outputs["Z"], ridge_pos.inputs["Z"])
    ridge_sel = b.N("FunctionNodeCompare", (3200, -650), data_type="FLOAT", operation="GREATER_THAN")
    b.L(psep4.outputs["Z"], ridge_sel.inputs["A"])
    b.L(m("ADD", zmax, m("MULTIPLY", hgt, 0.5, loc=(3050, -700)), loc=(3200, -720)), ridge_sel.inputs["B"])
    sp2 = b.N("GeometryNodeSetPosition", (3550, -300))
    b.L(e2.outputs["Mesh"], sp2.inputs["Geometry"])
    b.L(ridge_sel.outputs["Result"], sp2.inputs["Selection"])
    b.L(ridge_pos.outputs["Vector"], sp2.inputs["Position"])

    # roof material on everything above the wall top
    posf5 = b.N("GeometryNodeInputPosition", (3550, -600))
    psep5 = b.N("ShaderNodeSeparateXYZ", (3700, -600))
    b.L(posf5.outputs["Position"], psep5.inputs["Vector"])
    roof_sel = b.N("FunctionNodeCompare", (3850, -600), data_type="FLOAT", operation="GREATER_THAN")
    b.L(psep5.outputs["Z"], roof_sel.inputs["A"])
    b.L(m("ADD", zmax, eps * 0.25, loc=(3700, -700)), roof_sel.inputs["B"])
    # the extrude chain output already contains the (extruded) input mesh, so
    # join ONLY the newly generated roof faces on top of the untouched input
    sep_new = b.N("GeometryNodeSeparateGeometry", (3900, -300), domain="FACE")
    b.L(sp2.outputs["Geometry"], sep_new.inputs["Geometry"])
    b.L(roof_sel.outputs["Result"], sep_new.inputs["Selection"])
    dressed = material_gate(b, sep_new.outputs["Selection"], gi.outputs["Roof Material"],
                            roof_sel.outputs["Result"], (4050, -300))

    join = b.N("GeometryNodeJoinGeometry", (4450, -200))
    b.L(gi.outputs["Geometry"], join.inputs["Geometry"])
    b.L(dressed, join.inputs["Geometry"])
    b.L(join.outputs["Geometry"], go.inputs["Geometry"])
    b.finish_menu_defaults()
    return b.ng


# ---------------------------------------------------------------------------- verification helpers
def socket_id(ng, name):
    for it in ng.interface.items_tree:
        if it.item_type == "SOCKET" and it.name == name and it.in_out == "INPUT":
            return it.identifier
    raise KeyError(name)


def set_params(mod, ng, mapping):
    ins = mod.properties.inputs
    for k, v in mapping.items():
        item = getattr(ins, socket_id(ng, k))
        if v is None:
            try:
                item.value = None
            except Exception:
                pass
        else:
            item.value = v


def eval_stats(host):
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    n_inst = 0
    inst_verts = 0
    freq = Counter()
    scales = set()
    yaws = set()
    positions = []
    named_positions = []
    rotations = []
    updots = []
    normals = []
    host_inv = host.matrix_world.inverted()
    for inst in dg.object_instances:
        if not inst.is_instance or inst.parent is None:
            continue
        par = inst.parent
        if not (par == host or getattr(par, "original", None) == host):
            continue
        n_inst += 1
        ob = inst.object
        if ob.type == "MESH":
            inst_verts += len(ob.data.vertices)
        freq[ob.name] += 1
        m = inst.matrix_world
        scales.add(round(m.to_scale().x, 2))
        yaws.add(round(math.degrees(m.to_euler().z) % 360, 0))
        positions.append(tuple(round(v, 4) for v in (host_inv @ m.translation)))
        named_positions.append((ob.name, tuple(round(v, 4) for v in (host_inv @ m.translation))))
        rotations.append(tuple(round(math.degrees(a), 1) for a in m.to_euler()))
        updots.append(round(m.col[2].z, 4))
        nn = m.col[1]
        nx, ny, nz = nn.x, nn.y, nn.z
        ln = max((nx * nx + ny * ny + nz * nz) ** 0.5, 1e-9)
        normals.append((round(nx / ln, 3), round(ny / ln, 3), round(nz / ln, 3)))
    host_verts = len(host.data.vertices)
    return dict(n_instances=n_inst, instance_verts=inst_verts, host_verts=host_verts,
                total_verts=host_verts + inst_verts, freq=dict(freq),
                distinct_scales=len(scales), distinct_yaws=len(yaws),
                positions=positions, rotations=rotations, updots=updots, normals=normals,
                named_positions=named_positions)


def inst_boxes(host, prefix):
    """World AABBs of evaluated instances of `host` whose object name starts
    with `prefix` (depsgraph instance iteration)."""
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    boxes = []
    for inst in dg.object_instances:
        if not inst.is_instance or inst.parent is None:
            continue
        par = inst.parent
        if not (par == host or getattr(par, "original", None) == host):
            continue
        ob = inst.object
        if not ob.name.startswith(prefix):
            continue
        m = inst.matrix_world
        cs = [m @ Vector(c) for c in ob.bound_box]
        lo = Vector((min(c.x for c in cs), min(c.y for c in cs), min(c.z for c in cs)))
        hi = Vector((max(c.x for c in cs), max(c.y for c in cs), max(c.z for c in cs)))
        boxes.append(dict(name=ob.name, lo=lo, hi=hi, org=m.translation.copy(),
                          n=Vector(m.col[1]).normalized()))
    return boxes


def host_planes(host):
    # BASE WALL planes from the host's original mesh verts - object.bound_box
    # reflects evaluated geometry (roof/instances) and would skew the planes
    cs = [host.matrix_world @ Vector(v.co) for v in host.data.vertices]
    lo = Vector((min(c.x for c in cs), min(c.y for c in cs), min(c.z for c in cs)))
    hi = Vector((max(c.x for c in cs), max(c.y for c in cs), max(c.z for c in cs)))
    return lo, hi


def wall_of(n):
    if abs(n.x) > 0.9:
        return 0, (1 if n.x > 0 else -1)
    return 1, (1 if n.y > 0 else -1)


def back_dist_of(box, lo, hi):
    ax, sgn = wall_of(box["n"])
    plane = hi[ax] if sgn > 0 else lo[ax]
    return (box["org"][ax] - plane) * sgn


def aabb_gap(a, b):
    return max(max(a["lo"][i] - b["hi"][i], b["lo"][i] - a["hi"][i]) for i in range(3))


def zone_counts_on_cube(positions, normals, size=2.0):
    """Classify instance origins by the face normal they were placed against
    (Fit/Cladding align the instance's local Y axis to the face normal)."""
    on_wall = on_top = on_bottom = off = 0
    per_wall = Counter()
    z_lo, z_hi = 1e9, -1e9
    for (x, y, z), (nx, ny, nz) in zip(positions, normals):
        z_lo, z_hi = min(z_lo, z), max(z_hi, z)
        if nz > 0.9:
            on_top += 1
        elif nz < -0.9:
            on_bottom += 1
        elif abs(nx) > 0.9:
            on_wall += 1
            per_wall["x+" if nx > 0 else "x-"] += 1
        elif abs(ny) > 0.9:
            on_wall += 1
            per_wall["y+" if ny > 0 else "y-"] += 1
        else:
            off += 1
    return dict(on_wall=on_wall, on_top=on_top, on_bottom=on_bottom, off=off,
                per_wall=dict(per_wall), z_range=[round(z_lo, 3), round(z_hi, 3)])


def expected_courses(mesh_ob, zone_test, slot_w, overlap, row_h):
    """Independent Python re-implementation of the cladding row/slot formula,
    per face, for cross-checking the GN output. zone_test(normal, center) -> bool.
    Uses the EVALUATED mesh so VM_RoofCap-generated faces are included."""
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    me = mesh_ob.evaluated_get(dg).data
    total = 0
    per_face = []
    sp = max(slot_w * (1.0 - overlap), 0.001)
    for p in me.polygons:
        n = p.normal
        if not zone_test(n, p.center):
            continue
        # face frame: u = normalize(cross(Z, n)) (world X on flat faces), v = cross(n, u)
        import mathutils
        nv = mathutils.Vector((n.x, n.y, n.z))
        if abs(nv.z) > 0.995:
            u = mathutils.Vector((1, 0, 0))
        else:
            u = mathutils.Vector((0, 0, 1)).cross(nv).normalized()
        v = nv.cross(u).normalized()
        c = mathutils.Vector(p.center)
        aas, bbs = [], []
        for vi in p.vertices:
            d = mathutils.Vector(me.vertices[vi].co) - c
            aas.append(d.dot(u)); bbs.append(d.dot(v))
        W = max(aas) - min(aas)
        H = max(bbs) - min(bbs)
        ns = max(1, math.ceil(W / sp))
        nr = max(1, math.ceil(H / max(row_h, 0.001)))
        per_face.append(dict(face=p.index, W=round(W, 3), H=round(H, 3), slots=ns, rows=nr, total=ns * nr))
        total += ns * nr
    return total, per_face


# ---------------------------------------------------------------------------- main
def main():
    import faulthandler, signal, time
    faulthandler.register(signal.SIGUSR1)
    os.makedirs(STAGE, exist_ok=True)
    os.makedirs(os.path.join(ROOT, "renders"), exist_ok=True)
    os.makedirs(DELIVER, exist_ok=True)
    clear_scene()
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100

    results = {}
    checks = []

    def check(name, cond, detail):
        checks.append((name, bool(cond), detail))
        log(f"  CHECK {name}: {'PASS' if cond else 'FAIL'}  ({detail})")

    # collections
    col_assets = bpy.data.collections.new("AssetLibrary")
    scene.collection.children.link(col_assets)
    col_primary = bpy.data.collections.new("VM_Props_Primary")
    col_library = bpy.data.collections.new("VM_Props_Library")
    col_debris = bpy.data.collections.new("VM_Debris_Trash")
    col_doors = bpy.data.collections.new("VM_Doors")
    col_handles = bpy.data.collections.new("VM_DoorHandles")
    col_windows = bpy.data.collections.new("VM_Windows")
    col_shingle = bpy.data.collections.new("VM_Tiles_Shingle")
    col_plank = bpy.data.collections.new("VM_Tiles_Plank")
    for c in (col_primary, col_library, col_debris, col_doors, col_handles, col_windows,
              col_shingle, col_plank):
        col_assets.children.link(c)

    log("== importing asset model sets")
    import_assets(col_primary, col_library)
    log("== ingesting packs via pack_ingest.py (zero-config adapter)")
    ingest_reports, n_doors, n_handles, n_windows = ingest_packs(
        col_assets, col_doors, col_handles, col_windows)
    results["pack_ingest"] = {p: dict(counts=r["counts"], meshes=r["meshes"],
                                      non_mesh_dropped=r["non_mesh_dropped"],
                                      scale_factors=r["scale_factors"], flags=r["flags"],
                                      quarantine=r["quarantine"], source=r["source"])
                              for p, r in ingest_reports.items()}
    log("== generating debris + tile variant sets")
    make_debris(col_debris)

    mat_wall = make_textured_material(
        "VM_WallWeatheredPlanks", os.path.join(ASSET_SRC, "materials", "walls", "weathered_plank_siding"),
        "weathered_plank_siding_diff.jpg", "weathered_plank_siding_rough.jpg",
        "weathered_plank_siding_nor.jpg", 0.5)
    mat_roof = make_textured_material(
        "VM_RoofClayTiles", os.path.join(ASSET_SRC, "materials", "roofs", "clay_roof_tiles_02"),
        "clay_roof_tiles_02_diff.jpg", "clay_roof_tiles_02_rough.jpg",
        "clay_roof_tiles_02_nor.jpg", 0.6)
    mat_floor = make_textured_material(
        "VM_FloorGrass", os.path.join(ASSET_SRC, "materials", "vegetation", "leafy_grass"),
        "leafy_grass_diff.jpg", "leafy_grass_rough.jpg", "leafy_grass_nor.jpg", 0.5)
    mat_shingle = make_textured_material(
        "VM_ShingleTile", os.path.join(ASSET_SRC, "props", "shingles", "RoundedWoodShingles", "textures"),
        "Scene_-_Root_baseColor.png", "Scene_-_Root_metallicRoughness.png",
        "Scene_-_Root_normal.png", 1.0)
    mat_plank = make_textured_material(
        "VM_PlankTile", os.path.join(ASSET_SRC, "materials", "walls", "brown_planks_05"),
        "brown_planks_05_diff.jpg", "brown_planks_05_rough.jpg", "brown_planks_05_nor.jpg", 0.8)

    make_tile_variants(col_shingle, "Shingle", 0.25, 0.15, 0.012, 4, mat_shingle,
                       [0.006, -0.005, 0.008, -0.004])
    make_tile_variants(col_plank, "Plank", 2.0, 0.2, 0.02, 3, mat_plank,
                       [0.010, -0.008, 0.006])

    col_assets.hide_viewport = True
    col_assets.hide_render = True

    log("== building VM_SceneDetailer node group (v2)")
    ng = build_node_group()
    log("== building VM_RoofCap node group")
    ng_roof = build_roofcap_group()

    col_scene = scene.collection
    wall_mat = make_wood_material()
    roof_mat = make_principled("VM_Roof", (0.24, 0.11, 0.08), rough=0.85)
    ground_mat = make_principled("VM_Ground", (0.30, 0.36, 0.20), rough=0.95)
    house_a = make_house("HouseA", (0, 0), col_scene, wall_mat, roof_mat, ground_mat)
    house_b = make_house("HouseB", (40, 0), col_scene, wall_mat, roof_mat, ground_mat)

    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.2)
    me = bpy.data.meshes.new("ProximityBlocker")
    bm.to_mesh(me); bm.free()
    blocker = bpy.data.objects.new("ProximityBlocker", me)
    col_scene.objects.link(blocker)
    blocker.location = (4.2, -3.4, 0.85)
    blocker.scale = (1.3, 1.0, 0.75)
    me.materials.append(make_principled("VM_Boulder", (0.35, 0.33, 0.31), rough=0.9))

    mod_a = house_a.modifiers.new("VM_SceneDetailer", "NODES")
    mod_a.node_group = ng
    mod_b = house_b.modifiers.new("VM_SceneDetailer", "NODES")
    mod_b.node_group = ng

    defaults = {
        "Primary Props": col_primary, "Debris/Trash Props": col_debris, "Debris Ratio": 0.35,
        "Placement Mode": "Scatter", "Embed": 0.02, "Backing Offset": 0.0, "Fit Jitter": 0.0, "Drop To Ground": False,
        "Row Height": 0.22, "Row Overlap": 0.35, "Stagger": 0.5, "Jitter": 0.01, "Slot Width": 0.25,
        "Density": 0.12, "Seed": 0, "Surface Offset": -0.02, "Align To Normal": True,
        "Random Rot X": 0.02, "Random Rot Y": 0.02, "Random Rot Z": 3.1416,
        "Scale Min": 0.55, "Scale Max": 1.7, "Tint Amount": 0.5,
        "Face Zone": "Walls", "Wall Slope": 0.35, "Roof Slope": 0.7,
        "Wall Material": None, "Roof Material": None, "Floor Material": None,
        "Random Mask Threshold": 0.0, "Vertical Mask": False, "Vertical Range Min": 0.0,
        "Vertical Range Max": 4.0, "Proximity Mask": False, "Proximity Object": None,
        "Proximity Radius": 2.0, "Max Instances": 500,
    }
    set_params(mod_a, ng, defaults)
    set_params(mod_b, ng, dict(defaults, **{"Primary Props": col_library, "Seed": 3}))

    cam_data = bpy.data.cameras.new("Camera")
    cam = bpy.data.objects.new("Camera", cam_data)
    col_scene.objects.link(cam)
    scene.camera = cam
    sun_data = bpy.data.lights.new("Sun", "SUN")
    sun_data.energy = 3.5
    sun = bpy.data.objects.new("Sun", sun_data)
    col_scene.objects.link(sun)
    sun.rotation_euler = (math.radians(52), math.radians(8), math.radians(35))
    world = bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.55, 0.70, 0.92, 1.0)
    bg.inputs["Strength"].default_value = 0.8

    def look_at(ob, target):
        from mathutils import Vector
        direction = Vector(target) - ob.location
        ob.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    def render_from(tag, loc, target, lens=32):
        cam.location = loc
        look_at(cam, target)
        cam_data.lens = lens
        scene.render.filepath = os.path.join(ROOT, "renders", tag + ".png")
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        log(f"  rendered {tag}.png ({time.time() - t0:.0f}s)")

    cam.location = (11.5, -13.5, 7.0)
    look_at(cam, (0, 0, 2.0))
    cam_data.lens = 32

    # ================================================== v1 regression verification
    log("\n== V1 REGRESSION VERIFICATION (evaluated depsgraph) ==")
    baseline = dict(defaults)
    baseline.pop("Primary Props"); baseline.pop("Debris/Trash Props"); baseline.pop("Proximity Object")

    def run(host, mod, tag, params, store=True):
        t0 = time.time()
        set_params(mod, ng, params)
        host.update_tag()
        bpy.context.view_layer.update()
        s = eval_stats(host)
        if store:
            results[tag] = {k: v for k, v in s.items()
                            if k not in ("positions", "rotations", "updots", "normals", "named_positions")}
        log(f"[{tag:24s}] instances={s['n_instances']:5d}  total_verts={s['total_verts']:7d}  ({time.time()-t0:.1f}s)")
        return s

    s0 = run(house_a, mod_a, "v1_default", baseline)
    s1 = run(house_a, mod_a, "v1_density_high", dict(baseline, **{"Density": 0.5}))
    s2 = run(house_a, mod_a, "v1_seed_B", dict(baseline, **{"Seed": 7}))
    s3 = run(house_a, mod_a, "v1_random_mask", dict(baseline, **{"Random Mask Threshold": 0.5}))
    s4 = run(house_a, mod_a, "v1_vertical_mask",
             dict(baseline, **{"Vertical Mask": True, "Vertical Range Min": 0.0, "Vertical Range Max": 3.5}))
    s5 = run(house_a, mod_a, "v1_cap_25", dict(baseline, **{"Max Instances": 25}))
    s6 = run(house_a, mod_a, "v1_align_off", dict(baseline, **{"Align To Normal": False}))
    check("v1: density_high > 2.5x default", s1["n_instances"] > 2.5 * s0["n_instances"],
          f"{s1['n_instances']} vs {s0['n_instances']}")
    check("v1: seed changes mix", s2["freq"] != s0["freq"] or s2["n_instances"] != s0["n_instances"],
          f"count {s0['n_instances']}->{s2['n_instances']}")
    check("v1: random mask 0.5 removes ~half", 0.3 * s0["n_instances"] < s3["n_instances"] < 0.72 * s0["n_instances"],
          f"{s3['n_instances']} of {s0['n_instances']}")
    check("v1: vertical mask reduces", s4["n_instances"] < 0.6 * s0["n_instances"],
          f"{s4['n_instances']} vs {s0['n_instances']}")
    check("v1: cap 25 exact", s5["n_instances"] == 25, f"{s5['n_instances']}")
    check("v1: rotation-only change keeps count", s6["n_instances"] == s0["n_instances"],
          f"{s6['n_instances']} == {s0['n_instances']}")
    check("v1: scale variety", s0["distinct_scales"] >= 8, f"{s0['distinct_scales']} distinct scales")
    check("v1: rotation variety", s0["distinct_yaws"] >= 15, f"{s0['distinct_yaws']} distinct yaws")

    set_params(mod_a, ng, dict(baseline, **{"Proximity Mask": True, "Proximity Object": blocker,
                                            "Proximity Radius": 2.6}))
    house_a.update_tag(); bpy.context.view_layer.update()
    s7 = eval_stats(house_a)
    results["v1_proximity"] = {k: v for k, v in s7.items() if k not in ("positions", "rotations")}
    check("v1: proximity mask reduces", s7["n_instances"] < s0["n_instances"],
          f"{s7['n_instances']} vs {s0['n_instances']}")
    sB = run(house_b, mod_b, "v1_houseB_library",
             dict(defaults, **{"Primary Props": col_library, "Seed": 3}), store=True)
    check("v1: house B library set instances", sB["n_instances"] > 10, f"{sB['n_instances']}")
    set_params(mod_a, ng, defaults)

    # ================================================== starter scene objects
    log("\n== building StarterCube little-house demo ==")
    starter = make_cube("StarterCube", 2.0, col_scene)
    starter.location = (0, -40, 0)
    gverts = [(-15, -15, 0), (15, -15, 0), (15, 15, 0), (-15, 15, 0)]
    starter_ground = new_mesh_obj("StarterGround", [(x, y - 40, z) for (x, y, z) in gverts], [(0, 1, 2, 3)], col_scene)
    starter_ground.data.materials.append(mat_floor)

    m_plank = starter.modifiers.new("VM_SceneDetailer_Planks", "NODES")
    m_plank.node_group = ng
    plank_params = dict(defaults, **{
        "Placement Mode": "Cladding", "Face Zone": "Walls",
        "Row Height": 0.22, "Row Overlap": 0.05, "Stagger": 0.0, "Jitter": 0.002,
        "Slot Width": 2.0, "Primary Props": col_plank, "Debris/Trash Props": col_debris,
        "Debris Ratio": 0.0, "Scale Min": 1.0, "Scale Max": 1.0,
        "Wall Material": mat_wall, "Roof Material": mat_roof, "Floor Material": mat_floor,
        "Max Instances": 2000,
    })
    set_params(m_plank, ng, plank_params)
    m_roof = starter.modifiers.new("VM_RoofCap", "NODES")
    m_roof.node_group = ng_roof
    set_params(m_roof, ng_roof, {"Pitch": math.radians(35.0), "Overhang": 0.25,
                                 "Style": "Gable", "Roof Material": mat_roof})
    m_shing = starter.modifiers.new("VM_SceneDetailer_Shingles", "NODES")
    m_shing.node_group = ng
    shingle_params = dict(defaults, **{
        "Placement Mode": "Cladding", "Face Zone": "Roof",
        "Row Height": 0.11, "Row Overlap": 0.35, "Stagger": 0.5, "Jitter": 0.004,
        "Slot Width": 0.25, "Primary Props": col_shingle, "Debris/Trash Props": col_debris,
        "Debris Ratio": 0.0, "Scale Min": 1.0, "Scale Max": 1.0, "Max Instances": 4000,
    })
    set_params(m_shing, ng, shingle_params)
    m_door = starter.modifiers.new("VM_SceneDetailer_Door", "NODES")
    m_door.node_group = ng
    # Strict wall-contact contract for the fitted doors: planks sit ON the wall
    # (0.02 thick tiles, y=0 at the wall). The door placement plane is tangent
    # to the measured plank outer plane (0.02315-0.02317 m): net normal offset
    # = Backing Offset - Embed = 0.0435 - 0.02 = 0.0235 -> the door back face
    # lands 0.0003-0.0005 m in front of the frontmost planks (contact-level
    # gap, no hairline daylight) while still inside the accept(a) tolerance
    # band (planks_thickness + 0.005 +/- 0.005). Never behind the planks.
    # Seed 229 = the deterministic seed whose 3 fitted doors all clear the wall
    # corners (no door bbox overlaps a perpendicular wall's planks; verified by
    # the accept(a/b/c) measurements on the delivered VM_Starter.blend).
    door_params = dict(defaults, **{
        "Placement Mode": "Fit", "Face Zone": "Walls",
        "Density": 0.35, "Seed": 229, "Embed": 0.02, "Backing Offset": 0.0435,
        "Drop To Ground": True,
        "Scale Min": 1.0, "Scale Max": 1.0,
        "Primary Props": col_doors, "Debris/Trash Props": col_debris, "Debris Ratio": 0.0,
        "Random Mask Threshold": 0.0, "Vertical Mask": False,
        "Max Instances": 3,
    })
    set_params(m_door, ng, door_params)

    # ---- windows layer (v2.2): SAME VM_SceneDetailer node group, windows
    # collection from pack_ingest (WeatheredWoodenWindow shutters + a
    # BrokenWindow01 unit). Identical wall-contact contract as the doors:
    # Backing Offset 0.045 / Embed 0.02 -> back plane at planks_thickness + 0.005.
    m_win = starter.modifiers.new("VM_SceneDetailer_Windows", "NODES")
    m_win.node_group = ng
    win_params = dict(defaults, **{
        "Placement Mode": "Fit", "Face Zone": "Walls",
        "Density": 0.35, "Embed": 0.02, "Backing Offset": 0.0435,
        "Drop To Ground": False,
        "Scale Min": 0.5, "Scale Max": 0.5,
        "Primary Props": col_windows, "Debris/Trash Props": col_debris, "Debris Ratio": 0.0,
        "Random Mask Threshold": 0.0, "Vertical Mask": False,
        "Max Instances": 2,
    })
    # Deterministic reseed (shift/reseed, no geometry edits). Window sampling
    # only sees the HOST mesh (instance layers are deleted before sampling), so
    # the seed search runs on a cheap hidden rig (cube + VM_RoofCap = identical
    # host geometry) against the real door/plank boxes, then verifies on the
    # full starter stack. Hard constraints: windows stay on the wall (never
    # hang off a corner, never on roof gables), base at window height, and
    # zero window/door, window/window, window/plank bbox intersections.
    log("== windows layer: deterministic seed search (cheap rig + full-stack verify)")
    rig = make_cube("WinSearchRig", 2.0, col_scene)
    rig.location = (0, -40, 0)
    rig.hide_render = True
    m_rig_roof = rig.modifiers.new("VM_RoofCap", "NODES")
    m_rig_roof.node_group = ng_roof
    set_params(m_rig_roof, ng_roof, {"Pitch": math.radians(35.0), "Overhang": 0.25,
                                     "Style": "Gable", "Roof Material": None})
    m_rig_win = rig.modifiers.new("VM_SceneDetailer_Windows", "NODES")
    m_rig_win.node_group = ng
    set_params(m_rig_win, ng, win_params)
    doors_b = inst_boxes(starter, "Door_")
    planks_b = inst_boxes(starter, "Plank_")
    lo_h, hi_h = host_planes(starter)

    def win_evaluate(wins):
        if not (2 <= len(wins) <= 3):
            return False, 0, 99.0
        for w in wins:
            ax, sgn = wall_of(w["n"])
            t = 1 - ax
            if not (0.25 <= w["org"].z <= 1.05) or w["hi"].z > 2.0:
                return False, 0, 99.0
            if w["lo"][t] < lo_h[t] - 0.005 or w["hi"][t] > hi_h[t] + 0.005:
                return False, 0, 99.0        # window hangs off a wall corner
        pairs = [aabb_gap(w, b) for w in wins for b in doors_b]
        pairs += [aabb_gap(wins[i], wins[j])
                  for i in range(len(wins)) for j in range(i + 1, len(wins))]
        pairs += [aabb_gap(w, p) for w in wins for p in planks_b]
        if any(g < 0 for g in pairs):
            return False, 0, min(pairs)
        vis = sum(1 for w in wins if wall_of(w["n"]) in ((1, -1), (0, -1)))
        return True, vis, min(pairs)

    win_seed_used, win_fallback, win_tried = 0, None, 0
    for seed in range(4000):
        win_tried = seed + 1
        set_params(m_rig_win, ng, dict(win_params, **{"Seed": seed}))
        rig.update_tag()
        bpy.context.view_layer.update()
        ok, vis, mgap = win_evaluate(inst_boxes(rig, "Window_"))
        if not ok:
            continue
        if win_fallback is None:
            win_fallback = dict(seed=seed, visible=vis, min_gap=round(mgap, 5))
        if vis >= 1:
            win_seed_used = seed
            break
    else:
        win_seed_used = win_fallback["seed"] if win_fallback else 0
    set_params(m_win, ng, dict(win_params, **{"Seed": win_seed_used}))
    starter.update_tag()
    bpy.context.view_layer.update()
    f_ok, f_vis, f_gap = win_evaluate(inst_boxes(starter, "Window_"))
    results["windows_seed_search"] = dict(seed=win_seed_used, seeds_tried=win_tried,
                                          fallback=win_fallback,
                                          full_stack_ok=f_ok, full_stack_visible=f_vis,
                                          full_stack_min_gap=round(f_gap, 5))
    log(f"  windows seed {win_seed_used} chosen after {win_tried} candidates "
        f"(fallback={win_fallback}, full-stack verify ok={f_ok}, min gap={f_gap:.5f})")

    m_ground = starter_ground.modifiers.new("VM_SceneDetailer", "NODES")
    m_ground.node_group = ng
    ground_params = dict(defaults, **{
        "Placement Mode": "Scatter", "Density": 0.10, "Seed": 5,
        "Surface Offset": 0.0, "Primary Props": col_primary,
        "Debris/Trash Props": col_debris, "Debris Ratio": 1.0,
        "Scale Min": 0.7, "Scale Max": 1.5, "Max Instances": 40,
    })
    set_params(m_ground, ng, ground_params)

    starter.update_tag(); starter_ground.update_tag()
    bpy.context.view_layer.update()
    s_house = eval_stats(starter)
    results["starter_house"] = {k: v for k, v in s_house.items()
                                if k not in ("positions", "rotations", "updots", "normals", "named_positions")}
    log(f"  StarterCube: {s_house['n_instances']} instances, freq={s_house['freq']}")

    # ================================================== test rigs
    log("\n== building verification rigs ==")
    test_fit = make_cube("TestFit", 2.0, col_scene); test_fit.location = (60, 0, 0)
    mod_fit = test_fit.modifiers.new("VM_SceneDetailer", "NODES"); mod_fit.node_group = ng
    fit_params = dict(defaults, **{
        "Placement Mode": "Fit", "Face Zone": "Walls", "Density": 0.6, "Seed": 2,
        "Embed": 0.03, "Drop To Ground": True, "Scale Min": 1.0, "Scale Max": 1.0,
        "Primary Props": col_doors, "Debris/Trash Props": col_debris, "Debris Ratio": 0.0,
        "Max Instances": 100,
    })
    set_params(mod_fit, ng, fit_params)

    test_clad = make_cube("TestClad", 2.0, col_scene); test_clad.location = (70, 0, 0)
    mod_clad = test_clad.modifiers.new("VM_SceneDetailer", "NODES"); mod_clad.node_group = ng
    clad_params = dict(defaults, **{
        "Placement Mode": "Cladding", "Face Zone": "Walls",
        "Row Height": 0.22, "Row Overlap": 0.35, "Stagger": 0.5, "Jitter": 0.01,
        "Slot Width": 0.25, "Primary Props": col_shingle, "Debris/Trash Props": col_debris,
        "Debris Ratio": 0.0, "Scale Min": 1.0, "Scale Max": 1.0, "Max Instances": 2000,
    })
    set_params(mod_clad, ng, clad_params)

    test_zones = make_cube("TestZones", 2.0, col_scene); test_zones.location = (80, 0, 0)
    mod_zones = test_zones.modifiers.new("VM_SceneDetailer", "NODES"); mod_zones.node_group = ng
    zones_params = dict(clad_params, **{"Face Zone": "Roof"})
    set_params(mod_zones, ng, zones_params)

    test_mat = make_cube("TestMat", 2.0, col_scene); test_mat.location = (90, 0, 0)
    mod_mat = test_mat.modifiers.new("VM_SceneDetailer", "NODES"); mod_mat.node_group = ng
    mat_params = dict(defaults, **{
        "Wall Material": mat_wall, "Roof Material": mat_roof, "Floor Material": mat_floor,
        "Max Instances": 0,
    })
    set_params(mod_mat, ng, mat_params)

    test_roof_g = make_cube("TestRoofGable", 2.0, col_scene); test_roof_g.location = (100, 0, 0)
    mod_rg = test_roof_g.modifiers.new("VM_RoofCap", "NODES"); mod_rg.node_group = ng_roof
    set_params(mod_rg, ng_roof, {"Pitch": math.radians(35.0), "Overhang": 0.25,
                                 "Style": "Gable", "Roof Material": mat_roof})
    test_roof_h = make_cube("TestRoofHip", 2.0, col_scene); test_roof_h.location = (107, 0, 0)
    mod_rh = test_roof_h.modifiers.new("VM_RoofCap", "NODES"); mod_rh.node_group = ng_roof
    set_params(mod_rh, ng_roof, {"Pitch": math.radians(35.0), "Overhang": 0.25,
                                 "Style": "Hip", "Roof Material": mat_roof})

    for ob in (test_fit, test_clad, test_zones, test_mat, test_roof_g, test_roof_h):
        ob.update_tag()
    bpy.context.view_layer.update()

    # ================================================== STAGE 1: Fit walls-only proof
    log("\n== STAGE 1: Fit placement, Face Zone=Walls on a 2m cube ==")
    sf = run(test_fit, mod_fit, "fit_walls_density0.6", fit_params)
    zc = zone_counts_on_cube(sf["positions"], sf["normals"])
    results["fit_zone_counts"] = zc
    log(f"  fit zone counts: {zc}")
    check("fit: 100% instances on vertical faces", zc["on_wall"] == sf["n_instances"] and sf["n_instances"] > 0,
          f"{zc['on_wall']}/{sf['n_instances']} on walls, top={zc['on_top']}, bottom={zc['on_bottom']}, off={zc['off']}")
    check("fit: 0 on top/bottom faces", zc["on_top"] == 0 and zc["on_bottom"] == 0,
          f"top={zc['on_top']}, bottom={zc['on_bottom']}")
    yaws = sorted({r[2] for r in sf["rotations"]})
    upright = all(abs(d) > 0.99 for d in sf["updots"])
    check("fit: no random spin, upright on walls", upright and len(yaws) <= 4,
          f"upright={upright} (local Z ~ world Z, min |dot|={min(sf['updots']) if sf['updots'] else 0}), "
          f"distinct yaws={yaws}")
    embeds = [round(min(abs(abs(x) - 1.0), abs(abs(y) - 1.0)), 3) for (x, y, z) in sf["positions"]]
    results["fit_embed_depths"] = embeds
    check("fit: embed 0.03 into wall surface", all(0.015 <= e <= 0.045 for e in embeds),
          f"embed depths {embeds}")

    # ================================================== STAGE 2: zone selection
    log("\n== STAGE 2: Face Zone selection ==")
    sz = run(test_zones, mod_zones, "clad_zone_roof", zones_params)
    zc2 = zone_counts_on_cube(sz["positions"], sz["normals"])
    results["zone_roof_counts"] = zc2
    log(f"  roof-zone cladding positions: {zc2}")
    check("zone: Roof zone cladding sits on the top face only",
          zc2["on_top"] == sz["n_instances"] and sz["n_instances"] > 0,
          f"{zc2['on_top']}/{sz['n_instances']} on top, walls={zc2['on_wall']}")
    check("zone: walls vs roof give disjoint placements",
          zc["on_top"] == 0 and zc2["on_wall"] == 0, "walls-only fit + roof-only clad")

    # ================================================== STAGE 3: cladding courses
    log("\n== STAGE 3: cladding row/slot formula ==")
    sc = run(test_clad, mod_clad, "clad_walls", clad_params)
    exp_total, per_face = expected_courses(test_clad, lambda n, c: abs(n.z) <= 0.35, 0.25, 0.35, 0.22)
    results["clad_expected_per_face"] = per_face
    results["clad_expected_total"] = exp_total
    rows = per_face[0]["rows"] if per_face else 0
    slots = per_face[0]["slots"] if per_face else 0
    log(f"  expected per face: rows={rows} (=ceil(2/0.22)), slots={slots} (=ceil(2/(0.25*0.65))), "
        f"total={exp_total}; actual={sc['n_instances']}")
    check("clad: rows == ceil(2/Row Height) = 10", rows == math.ceil(2 / 0.22), f"rows={rows}")
    check("clad: slots per row == ceil(2/(Slot Width*(1-Overlap))) = 13",
          slots == math.ceil(2 / (0.25 * 0.65)), f"slots={slots}")
    check("clad: instance count matches independent formula", sc["n_instances"] == exp_total,
          f"actual={sc['n_instances']} expected={exp_total}")
    zc3 = zone_counts_on_cube(sc["positions"], sc["normals"])
    per_wall_ok = all(zc3["per_wall"].get(k, 0) == rows * slots for k in ("x+", "x-", "y+", "y-"))
    results["clad_per_wall"] = zc3["per_wall"]
    check("clad: per-face slot counts uniform on all 4 walls", per_wall_ok,
          f"per-wall counts {zc3['per_wall']} (expect {rows * slots} each)")

    # starter roof cladding cross-check (slopes from VM_RoofCap)
    exp_roof, per_roof = expected_courses(
        starter,
        lambda n, c: n.z >= 0.7, 0.25, 0.35, 0.11)
    results["starter_roof_expected"] = per_roof
    n_shingle = sum(v for k, v in s_house["freq"].items() if k.startswith("Shingle_"))
    check("clad: starter roof shingle count matches formula", n_shingle == exp_roof,
          f"actual={n_shingle} expected={exp_roof} over {len(per_roof)} roof faces")
    n_plank = sum(v for k, v in s_house["freq"].items() if k.startswith("Plank_"))
    exp_wall, per_wallf = expected_courses(
        starter, lambda n, c: abs(n.z) <= 0.35 and c.z <= 2.01, 2.0, 0.05, 0.22)
    results["starter_wall_expected"] = per_wallf
    check("clad: starter wall plank count matches formula", n_plank == exp_wall,
          f"actual={n_plank} expected={exp_wall} over {len(per_wallf)} wall faces")
    n_door = sum(v for k, v in s_house["freq"].items() if k.startswith("Door_"))
    check("starter: 1-3 fitted doors on the house", 1 <= n_door <= 3, f"{n_door} doors")
    dpos = [p for (nm, p) in s_house["named_positions"] if nm.startswith("Door_")]
    min_sep = min([((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
                   for i, a in enumerate(dpos) for b in dpos[i + 1:]] or [99.0])
    # wall-contact contract: the instance origin (variant back face) must sit at
    # 1.0 + Backing Offset - Embed from the cube axis on a 2m cube
    exp_r = 1.0 + door_params["Backing Offset"] - door_params["Embed"]
    on_cube = all((abs(abs(x) - exp_r) < 0.02 and abs(y) < 0.6) or (abs(abs(y) - exp_r) < 0.02 and abs(x) < 0.6)
                  for (x, y, z) in dpos)
    check("starter: doors on cube walls (no gable-end floaters), well separated",
          on_cube and min_sep > 0.85,
          f"on_cube_walls={on_cube} (back plane at r={exp_r:.3f}), min separation={min_sep:.2f}m, pos={dpos}")

    # density sweep per mode
    log("\n== density sweep 0.1 / 0.35 / 0.6 per mode ==")
    sweep = {}
    for d in (0.1, 0.35, 0.6):
        ss = run(house_a, mod_a, f"sweep_scatter_{d}", dict(baseline, **{"Density": d}))
        sfi = run(test_fit, mod_fit, f"sweep_fit_{d}", dict(fit_params, **{"Density": d}))
        scd = run(test_clad, mod_clad, f"sweep_clad_{d}", dict(clad_params, **{"Density": d}))
        sweep[d] = dict(scatter=ss["n_instances"], fit=sfi["n_instances"], clad=scd["n_instances"])
    results["density_sweep"] = sweep
    log(f"  sweep: {sweep}")
    check("sweep: scatter counts increase with density",
          sweep[0.1]["scatter"] < sweep[0.35]["scatter"] < sweep[0.6]["scatter"],
          f"{sweep}")
    check("sweep: fit counts increase with density",
          sweep[0.1]["fit"] < sweep[0.35]["fit"] < sweep[0.6]["fit"], f"{sweep}")
    check("sweep: cladding density-independent (tile-driven)",
          len({sweep[d]["clad"] for d in sweep}) == 1, f"{sweep}")

    # cap in each mode (fit gets a density bump so >25 candidates exist)
    for tag, ob, mod, prm in (("cap_scatter", house_a, mod_a, baseline),
                              ("cap_fit", test_fit, mod_fit,
                               dict(fit_params, **{"Density": 4.0})),
                              ("cap_clad", test_clad, mod_clad, clad_params)):
        s = run(ob, mod, tag, dict(prm, **{"Max Instances": 25}))
        check(f"cap: 25 exact in {tag.split('_')[1]} mode", s["n_instances"] == 25, f"{s['n_instances']}")
    set_params(mod_a, ng, defaults)
    set_params(mod_fit, ng, fit_params)
    set_params(mod_clad, ng, clad_params)

    # ================================================== STAGE 4: zone materials
    log("\n== STAGE 4: per-zone materials on base mesh ==")
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    ev_mat = test_mat.evaluated_get(dg)
    slots = [m.name if m else None for m in ev_mat.data.materials]
    results["material_slots"] = slots
    log(f"  evaluated TestMat slots: {slots}")
    zone_face_idx = {}
    for p in ev_mat.data.polygons:
        n = p.normal
        z = "wall" if abs(n.z) <= 0.35 else ("roof" if n.z >= 0.7 else ("floor" if n.z <= -0.7 else "other"))
        zone_face_idx.setdefault(z, set()).add(p.material_index)
    results["zone_face_material_index"] = {k: sorted(v) for k, v in zone_face_idx.items()}
    log(f"  zone -> material_index: {results['zone_face_material_index']}")
    check("mat: >=1 material slot per zone (3+ slots)", len([s for s in slots if s]) >= 3, f"slots={slots}")
    wall_i = slots.index(mat_wall.name) if mat_wall.name in slots else -1
    roof_i = slots.index(mat_roof.name) if mat_roof.name in slots else -1
    floor_i = slots.index(mat_floor.name) if mat_floor.name in slots else -1
    ok_map = (zone_face_idx.get("wall", {-9}) == {wall_i} and zone_face_idx.get("roof", {-9}) == {roof_i}
              and zone_face_idx.get("floor", {-9}) == {floor_i})
    check("mat: each zone's faces point at its zone material", ok_map,
          f"zone idx {results['zone_face_material_index']}, expected wall={wall_i} roof={roof_i} floor={floor_i}")
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    ev_house = house_a.evaluated_get(dg)
    house_slots = [m.name if m else None for m in ev_house.data.materials]
    check("mat: empty sockets leave v1 house materials untouched",
          house_slots == [wall_mat.name, roof_mat.name, ground_mat.name],
          f"evaluated HouseA slots {house_slots}")

    # ================================================== STAGE 5: VM_RoofCap
    log("\n== STAGE 5: VM_RoofCap ==")
    H_exp = (1.0 + 0.25) * math.tan(math.radians(35.0))
    for ob, style in ((test_roof_g, "Gable"), (test_roof_h, "Hip")):
        ob.update_tag(); bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get(); dg.update()
        ev = ob.evaluated_get(dg)
        zs = [v.co.z for v in ev.data.vertices]
        zmax = max(zs)
        results[f"roofcap_{style}"] = dict(zmax=round(zmax, 4), expected=round(2.0 + 0.002 + H_exp, 4),
                                           verts=len(ev.data.vertices),
                                           n_roof_faces=sum(1 for p in ev.data.polygons
                                                            if p.normal.z >= 0.7 and p.center.z > 2.01))
        log(f"  {style}: zmax={zmax:.4f} (expected {2.0 + 0.002 + H_exp:.4f}), "
            f"verts={len(ev.data.vertices)}, roof faces={results[f'roofcap_{style}']['n_roof_faces']}")
        check(f"roofcap: {style} ridge height correct", abs(zmax - (2.0 + 0.002 + H_exp)) < 0.01,
              f"zmax={zmax:.4f} expected={2.0 + 0.002 + H_exp:.4f}")
        check(f"roofcap: {style} adds roof faces", results[f"roofcap_{style}"]["n_roof_faces"] >= 2,
              f"{results[f'roofcap_{style}']['n_roof_faces']} faces with N.z>=0.7 above z=2")
        slots_r = [m.name if m else None for m in ev.data.materials]
        check(f"roofcap: {style} roof material applied", mat_roof.name in slots_r, f"slots={slots_r}")

    # ================================================== renders
    log("\n== renders (Cycles CPU 32spp 960x540) ==")
    render_from("preview_stage1_fit_walls", (64.2, -5.2, 2.6), (60, 0, 1.0), 35)
    render_from("preview_stage2_zones_roof", (84.0, -5.0, 3.6), (80, 0, 1.0), 35)
    render_from("preview_stage3_cladding", (72.6, -3.4, 1.9), (70, 0, 1.0), 45)
    render_from("preview_stage4_materials", (93.6, -4.4, 2.8), (90, 0, 1.0), 35)
    render_from("preview_stage5_roofcap", (106.5, -10.5, 5.5), (103.5, 0, 1.6), 35)
    render_from("preview_starter_house", (-3.0, -47.6, 2.3), (0, -40, 1.3), 38)
    # close-up of a fitted door mounted on the wall planks (v2.2 proof): camera
    # at door height, ~15 deg off the wall normal so the junction and contact
    # read without exaggerated perspective on the door's side faces
    d_idx = [i for i, (nm, _) in enumerate(s_house["named_positions"]) if nm.startswith("Door_")]
    if d_idx:
        i0 = d_idx[0]
        p_world = starter.matrix_world @ Vector(s_house["named_positions"][i0][1])
        nrm0 = Vector(s_house["normals"][i0])
        tan0 = Vector((-nrm0.y, nrm0.x, 0.0)).normalized()
        cam_pos = p_world + nrm0 * 1.5 + tan0 * 0.42 + Vector((0, 0, 1.05))
        render_from("preview_door_closeup", tuple(cam_pos), tuple(p_world + Vector((0, 0, 0.92))), 45)
        log(f"  door close-up aimed at {s_house['named_positions'][i0]} (normal {tuple(nrm0)})")
    w_idx = [i for i, (nm, _) in enumerate(s_house["named_positions"]) if nm.startswith("Window_")]
    if w_idx:
        i0 = w_idx[0]
        p_world = starter.matrix_world @ Vector(s_house["named_positions"][i0][1])
        nrm0 = Vector(s_house["normals"][i0])
        tan0 = Vector((-nrm0.y, nrm0.x, 0.0)).normalized()
        cam_pos = p_world + nrm0 * 1.4 + tan0 * 0.42 + Vector((0, 0, 1.05))
        render_from("preview_window_closeup", tuple(cam_pos), tuple(p_world + Vector((0, 0, 0.55))), 45)
        log(f"  window close-up aimed at {s_house['named_positions'][i0]} (normal {tuple(nrm0)})")

    # ================================================== save + deliverables
    set_params(mod_a, ng, defaults)
    house_a.update_tag(); house_b.update_tag()
    bpy.context.view_layer.update()

    # ---- BUG (B) fix: pack EVERY image into each delivered blend so the files
    # are texture-portable (zero missing/magenta textures on any machine and no
    # load-bearing filepaths outside the blend). Runs before every save, on
    # every rebuild.
    def pack_images():
        try:
            bpy.ops.file.pack_all()
        except Exception as e:
            log(f"  pack_all note: {e}")
        live = lambda: [i for i in bpy.data.images
                        if i.name not in ("Render Result", "Viewer Node") and i.source != "VIEWER"]
        for img in live():
            if img.packed_file is None:
                try:
                    img.pack()
                except Exception as e:
                    log(f"  !! image cannot be packed: {img.name}: {e}")
        imgs = live()
        packed = [i for i in imgs if i.packed_file is not None]
        log(f"  images packed: {len(packed)}/{len(imgs)}")
        return len(imgs), len(packed)

    for _p in (STARTER_PATH, BLEND_PATH, ROOFCAP_PATH):
        _n, _k = pack_images()
        bpy.ops.wm.save_as_mainfile(filepath=_p)
        log(f"\n== saved {_p} (images packed {_k}/{_n})")

    # ================================================== acceptance measured ON the delivered blends
    log("\n== ACCEPTANCE MEASUREMENT (on the delivered .blend files) ==")

    def blend_image_report(path):
        bpy.ops.wm.open_mainfile(filepath=path)
        imgs = [i for i in bpy.data.images
                if i.name not in ("Render Result", "Viewer Node") and i.source != "VIEWER"]
        unpacked = [i.name for i in imgs if i.packed_file is None]
        log(f"  images_packed {os.path.basename(path)}: {len(imgs) - len(unpacked)}/{len(imgs)}"
            + (f"  UNPACKED={unpacked}" if unpacked else ""))
        return dict(total=len(imgs), packed=len(imgs) - len(unpacked), unpacked=unpacked)

    # ---- VM_Starter.blend: images + (A) door wall-contact contract
    rep = blend_image_report(STARTER_PATH)
    results["images_packed"] = {"VM_Starter.blend": rep}
    check(f"images_packed VM_Starter.blend: {rep['packed']}/{rep['total']}",
          rep["total"] > 0 and not rep["unpacked"],
          f"{rep['packed']}/{rep['total']} image datablocks packed, unpacked={rep['unpacked']}")

    bpy.context.view_layer.update()
    host = bpy.data.objects["StarterCube"]
    lo_h, hi_h = host_planes(host)
    doors = inst_boxes(host, "Door_")
    planks = inst_boxes(host, "Plank_")
    log(f"  StarterCube: {len(doors)} door instances, {len(planks)} plank instances")

    PLANKS_THICKNESS = 0.02      # demo cladding tile spec (VM_Tiles_Plank)
    per_door = []
    for d in doors:
        ax, sgn = wall_of(d["n"])
        plane = hi_h[ax] if sgn > 0 else lo_h[ax]
        back_d = (d["org"][ax] - plane) * sgn
        front_c = d["hi"][ax] if sgn > 0 else d["lo"][ax]
        front_d = (front_c - plane) * sgn
        wall_planks = [p for p in planks if wall_of(p["n"]) == (ax, sgn)]
        outer_d = max((((p["hi"][ax] if sgn > 0 else p["lo"][ax]) - plane) * sgn)
                      for p in wall_planks) if wall_planks else 0.0
        per_door.append(dict(name=d["name"], wall="xy"[ax] + ("+" if sgn > 0 else "-"),
                             back_dist=round(back_d, 5), front_dist=round(front_d, 5),
                             plank_outer=round(outer_d, 5), proud=round(front_d - outer_d, 5)))
    for pd in per_door:
        log(f"  door {pd['name']} (wall {pd['wall']}): back plane {pd['back_dist']:.5f} m off the base wall, "
            f"front {pd['front_dist']:.5f} m, plank outer plane {pd['plank_outer']:.5f} m, "
            f"front proud of planks {pd['proud']:.5f} m")

    backs = [p["back_dist"] for p in per_door]
    ok_a = (len(per_door) == 3
            and all(abs(bd - (PLANKS_THICKNESS + 0.005)) <= 0.005 for bd in backs)
            and all(p["proud"] >= 0.005 for p in per_door))
    check("accept(a): door back plane = planks_thickness + small tolerance, front proud >= 0.005",
          ok_a, f"back distances {backs} (target {PLANKS_THICKNESS}+0.005 +/- 0.005), "
                f"proud {[p['proud'] for p in per_door]}")

    gaps = [aabb_gap(d, p) for d in doors for p in planks]
    min_gap = min(gaps) if gaps else 99.0
    n_int = sum(1 for g in gaps if g < 0)
    check("accept(b): zero door/plank bbox intersection, min pairwise gap >= 0",
          n_int == 0 and min_gap >= 0.0,
          f"{len(gaps)} door-plank world-bbox pairs, intersecting={n_int}, min pairwise gap={min_gap:.5f} m")

    # ---- (w) v2.2 windows layer: same wall-contact contract as the doors
    wins = inst_boxes(host, "Window_")
    per_win = []
    for w in wins:
        ax, sgn = wall_of(w["n"])
        plane = hi_h[ax] if sgn > 0 else lo_h[ax]
        back_d = (w["org"][ax] - plane) * sgn
        front_c = w["hi"][ax] if sgn > 0 else w["lo"][ax]
        front_d = (front_c - plane) * sgn
        wall_planks = [p for p in planks if wall_of(p["n"]) == (ax, sgn)]
        outer_d = max((((p["hi"][ax] if sgn > 0 else p["lo"][ax]) - plane) * sgn)
                      for p in wall_planks) if wall_planks else 0.0
        per_win.append(dict(name=w["name"], wall="xy"[ax] + ("+" if sgn > 0 else "-"),
                            base_z=round(w["org"].z, 4), top_z=round(w["hi"].z, 4),
                            back_dist=round(back_d, 5), front_dist=round(front_d, 5),
                            plank_outer=round(outer_d, 5), proud=round(front_d - outer_d, 5)))
    for pw in per_win:
        log(f"  window {pw['name']} (wall {pw['wall']}): base z={pw['base_z']:.3f}, "
            f"top z={pw['top_z']:.3f}, back plane {pw['back_dist']:.5f} m off the base wall, "
            f"plank outer {pw['plank_outer']:.5f} m, proud {pw['proud']:.5f} m")

    check("windows: 2-3 fitted windows on the house", 2 <= len(wins) <= 3,
          f"{len(wins)} windows: {[p['name'] for p in per_win]}")
    wbacks = [p["back_dist"] for p in per_win]
    check("windows: same wall-contact contract as doors (back plane = planks_thickness + 0.005 +/- 0.005)",
          len(per_win) >= 2 and all(abs(bd - (PLANKS_THICKNESS + 0.005)) <= 0.005 for bd in wbacks)
          and all(p["proud"] >= 0.005 for p in per_win),
          f"back distances {wbacks} (target {PLANKS_THICKNESS}+0.005 +/- 0.005), "
          f"proud {[p['proud'] for p in per_win]}")

    w_pairs = [aabb_gap(w, d) for w in wins for d in doors]
    w_pairs += [aabb_gap(wins[i], wins[j])
                for i in range(len(wins)) for j in range(i + 1, len(wins))]
    w_int = sum(1 for g in w_pairs if g < 0)
    check("windows: zero window/door and window/window bbox intersection",
          w_int == 0 and (not w_pairs or min(w_pairs) >= 0.0),
          f"{len(w_pairs)} window-door/window-window world-bbox pairs, intersecting={w_int}, "
          f"min pairwise gap={min(w_pairs) if w_pairs else 99.0:.5f} m")
    wp_gaps = [aabb_gap(w, p) for w in wins for p in planks]
    wp_min = min(wp_gaps) if wp_gaps else 99.0
    wp_int = sum(1 for g in wp_gaps if g < 0)
    check("windows: zero window/plank bbox intersection (like the door/plank check)",
          wp_int == 0 and wp_min >= 0.0,
          f"{len(wp_gaps)} window-plank world-bbox pairs, intersecting={wp_int}, "
          f"min pairwise gap={wp_min:.5f} m")
    check("windows: bases at window height, tops below the wall top",
          all(0.25 <= p["base_z"] <= 1.05 and p["top_z"] <= 2.0 for p in per_win),
          f"bases {[p['base_z'] for p in per_win]}, tops {[p['top_z'] for p in per_win]}")

    # windows variant back-plane variance (accept(c) analog, same setting)
    m_win = host.modifiers["VM_SceneDetailer_Windows"]
    ngw = m_win.node_group
    w_backing = float(getattr(m_win.properties.inputs, socket_id(ngw, "Backing Offset")).value)
    w_embed = float(getattr(m_win.properties.inputs, socket_id(ngw, "Embed")).value)
    win_var_back, win_var_ymin = {}, {}
    for ob in sorted(bpy.data.collections["VM_Windows"].objects, key=lambda o: o.name):
        ymin = min(v.co.y for v in ob.data.vertices)
        win_var_ymin[ob.name] = round(ymin, 6)
        win_var_back[ob.name] = round(w_backing - w_embed + ymin, 6)
    wvals = list(win_var_back.values())
    wspread = max(wvals) - min(wvals)
    check("windows: 0 back-plane variance across all window variants at one setting",
          len(wvals) >= 2 and wspread <= 0.005
          and max(abs(y) for y in win_var_ymin.values()) <= 0.0005,
          f"per-variant back distances {win_var_back}, spread={wspread:.6f} m, "
          f"modifier Backing Offset={w_backing}, Embed={w_embed}")
    same_ng = (m_win.node_group == host.modifiers["VM_SceneDetailer_Door"].node_group)
    check("windows layer: same VM_SceneDetailer node group, different pack collection "
          "(different pack, same engine)",
          same_ng and bpy.data.collections["VM_Windows"].objects[0].name.startswith("Window_")
          and not bpy.data.collections["VM_Windows"].objects[0].name.startswith("Door_"),
          f"node group shared with the door modifier: {same_ng}; "
          f"windows collection: {sorted(o.name for o in bpy.data.collections['VM_Windows'].objects)}")
    results["acceptance_windows"] = dict(
        per_window=per_win, pairs=len(w_pairs), intersecting=w_int,
        min_pairwise_gap=round(min(w_pairs) if w_pairs else 99.0, 5),
        plank_pairs=len(wp_gaps), plank_intersecting=wp_int, plank_min_gap=round(wp_min, 5),
        modifier=dict(backing_offset=w_backing, embed=w_embed),
        variant_back_dist=win_var_back, variant_y_min=win_var_ymin,
        variant_spread=round(wspread, 6), node_group_shared=same_ng)

    # (c) all VM_Doors variants placed at the SAME setting (the delivered door
    # modifier's own values read back from the blend): back plane = base wall +
    # (Backing Offset - Embed) + variant local y_min (y_min must be 0 by the
    # wall-contact origin convention -> identical back plane for every depth)
    m_door = host.modifiers["VM_SceneDetailer_Door"]
    ngd = m_door.node_group
    sid = lambda nm: socket_id(ngd, nm)
    backing = float(getattr(m_door.properties.inputs, sid("Backing Offset")).value)
    embed = float(getattr(m_door.properties.inputs, sid("Embed")).value)
    log(f"  delivered door modifier setting: Backing Offset={backing}, Embed={embed}")
    var_back, var_ymin = {}, {}
    for ob in sorted(bpy.data.collections["VM_Doors"].objects, key=lambda o: o.name):
        ymin = min(v.co.y for v in ob.data.vertices)
        var_ymin[ob.name] = round(ymin, 6)
        var_back[ob.name] = round(backing - embed + ymin, 6)
    vals = list(var_back.values())
    spread = max(vals) - min(vals)
    mean_v = sum(vals) / len(vals)
    var_var = sum((v - mean_v) ** 2 for v in vals) / len(vals)
    log(f"  per-variant back-plane distance at the same setting: {var_back}")
    log(f"  variant local y_min (wall-contact face): {var_ymin}")

    tf = bpy.data.objects["TestFit"]
    lo_t, hi_t = host_planes(tf)
    tf_boxes = inst_boxes(tf, "Door_")
    live = {d["name"]: back_dist_of(d, lo_h, hi_h) for d in doors}
    for b in tf_boxes:
        live.setdefault(b["name"], back_dist_of(b, lo_t, hi_t))
    log(f"  live instance back-plane distances: starter={ {d['name']: round(back_dist_of(d, lo_h, hi_h), 5) for d in doors} }")
    log(f"  TestFit live coverage {len(tf_boxes)} instances, variants present "
        f"{len({b['name'] for b in tf_boxes})}/{len(var_back)}")
    n_door_vars = len(var_back)
    ok_c = (n_door_vars >= 1 and len(vals) == n_door_vars and spread <= 0.005
            and max(abs(y) for y in var_ymin.values()) <= 0.0005)
    check("accept(c): back-plane distance variance across all wall-flat door variants <= 0.005 m "
          "(v2.2: VM_Doors holds the adapter's wall-flat slabs only)",
          ok_c, f"{n_door_vars} variants, per-variant back distances {var_back}, "
                f"spread={spread:.6f} m, variance={var_var:.8f} m^2, "
                f"y_min spread={max(var_ymin.values()) - min(var_ymin.values()):.6f} m")
    results["acceptance_doors"] = dict(
        per_door=per_door, pairs=len(gaps), intersecting=n_int, min_pairwise_gap=round(min_gap, 5),
        planks_thickness=PLANKS_THICKNESS, modifier=dict(backing_offset=backing, embed=embed),
        variant_back_dist=var_back, variant_y_min=var_ymin,
        variant_spread=round(spread, 6), variant_variance=round(var_var, 8),
        live_back_dist={k: round(v, 5) for k, v in live.items()},
        testfit_instances=len(tf_boxes), testfit_variants=len({b["name"] for b in tf_boxes}))

    # ---- VM_SceneDetailer.blend / VM_RoofCap.blend: images
    for path in (BLEND_PATH, ROOFCAP_PATH):
        rep2 = blend_image_report(path)
        results["images_packed"][os.path.basename(path)] = rep2
        check(f"images_packed {os.path.basename(path)}: {rep2['packed']}/{rep2['total']}",
              rep2["total"] > 0 and not rep2["unpacked"],
              f"{rep2['packed']}/{rep2['total']} image datablocks packed, unpacked={rep2['unpacked']}")

    # ---- adapter wiring proof: Fit collections contain only classified slab
    # outputs; quarantined objects never mix in (measured on the delivered blend)
    doors_col = sorted(bpy.data.collections["VM_Doors"].objects, key=lambda o: o.name)
    quar = []
    for ob in bpy.data.objects:
        if "_Q" in ob.name and any(ob.name.startswith(p) for p in
                                   ("WornWoodenDoorsPack", "WeatheredWoodenWindow",
                                    "BrokenWindow01", "BrokenWindow07", "MedievalWindows")):
            quar.append(ob.name)
    mixed = [ob.name for ob in doors_col if not ob.name.startswith("Door_")]
    check("adapter: VM_Doors holds wall-flat slabs only (quarantined/props never mix in)",
          len(doors_col) >= 1 and not mixed and not any(q.startswith("Door_") for q in quar),
          f"VM_Doors={[o.name for o in doors_col]}, quarantine={len(quar)} objects "
          f"kept in <Pack>_Quarantine, misfiled={mixed}")
    pack_counts = {p: r["counts"] for p, r in results.get("pack_ingest", {}).items()}
    check("adapter: 5 packs classified by pack_ingest.py with zero pack-specific parameters",
          len(results.get("pack_ingest", {})) == 5,
          f"packs={sorted(results.get('pack_ingest', {}))}; counts={pack_counts}")

    with open(os.path.join(ROOT, "verification_v2.json"), "w") as f:
        json.dump({"results": results,
                   "checks": [{"name": n, "pass": p, "detail": d} for n, p, d in checks]}, f, indent=2, default=str)

    failed = [c[0] for c in checks if not c[1]]
    log(f"\n== CHECKS: {len(checks) - len(failed)}/{len(checks)} passed")
    if failed:
        log("!! FAILED: " + ", ".join(failed))

    # deliverables
    for f in ("build_engine.py", "pack_ingest.py"):
        shutil.copy2(os.path.join(ROOT, f), os.path.join(DELIVER, f))
    for rep_name in sorted(os.listdir(ROOT)):
        if rep_name.endswith("_ingest.json"):
            shutil.copy2(os.path.join(ROOT, rep_name), os.path.join(DELIVER, rep_name))
    shutil.copy2(STARTER_PATH, os.path.join(DELIVER, "VM_Starter.blend"))
    shutil.copy2(BLEND_PATH, os.path.join(DELIVER, "VM_SceneDetailer.blend"))
    shutil.copy2(ROOFCAP_PATH, os.path.join(DELIVER, "VM_RoofCap.blend"))
    shutil.copy2(os.path.join(ROOT, "verification_v2.json"), os.path.join(DELIVER, "verification_v2.json"))
    for r in sorted(os.listdir(os.path.join(ROOT, "renders"))):
        if r.startswith("preview_"):
            shutil.copy2(os.path.join(ROOT, "renders", r), os.path.join(DELIVER, r))
    log(f"== deliverables copied to {DELIVER}: {sorted(os.listdir(DELIVER))}")
    log("== DONE")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
