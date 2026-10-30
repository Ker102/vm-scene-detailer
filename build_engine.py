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

v2.4 non-cube compound robustness (the user extrudes shapes FIRST, then the
engine dresses them):
  * PER-FACE ANCHORING: 'Drop To Ground' is now 'Stand On Face Base' - the
    instance base sits on ITS OWN placement face's lowest edge + Sill Height,
    never the host bbox. A door on a face whose bottom is at z=1.2 stands at
    z=1.2 (measured per instance on CompoundTest).
  * FACE FILTERS + SILL: Fit gains Min Face Width / Min Face Height (skip
    step-wall fragments), Sill Height (doors 0.0 / windows 0.9) and
    Ground Floor Only + Ground Tolerance (doors never climb steps). Fit also
    never anchors on VM_RoofCap-generated faces (vm_roofgen marker).
  * PER-REGION VM_RoofCap: every qualifying up-facing QUAD top (>= Min Roof
    Face Size) gets its own gable/hip along its local long axis; 'Largest Face
    Only' keeps just the biggest. Unresolvable regions (non-quad tops,
    undersized fragments) are SKIPPED CLEANLY and counted in the verification
    report - never garbage geometry. Honest limits: gables of different
    regions may intersect on compounds (valleys are out of scope).
  * ROOF ZONE = SLOPE BAND: 'Roof Slope' is replaced by 'Roof Slope Min/Max'
    (0.55-0.92); flat tops (N.z ~ 1) are NOT roof-clad (Floor zone covers
    flat decks/bottoms: N.z <= -Roof Slope Min OR N.z >= Roof Slope Max).
  * SHAPE-ROBUSTNESS MATRIX: CompoundTest (L-shaped stepped compound),
    CompoundScaled (non-uniform object scale x1.6, transforms left as-is),
    TowerWing (multi-height + 2 unresolved roof regions), Warehouse (wide
    low box) - each with the full stack, numeric acceptance + renders.
  * LIVE-EDIT SEMANTICS: ReflowTest is re-dressed after a base-mesh edit
    (non-uniform mesh scale + one more extrusion step): parts re-anchor on the
    new faces, cladding re-tiles, roofs regenerate.

v2.4.1 world-space sizing (object-scale no longer stretches parts):
  * WORLD-SPACE SIZING IS THE CONTRACT: every DISTANCE socket (Slot Width,
    Row Height, Jitter, Embed, Backing Offset, Sill Height, Min Face Width/
    Height, Ground Tolerance, Surface Offset, Vertical Range, Proximity Radius,
    VM_RoofCap Overhang / Min Roof Face Size / Pitch) is WORLD meters (Pitch a
    world angle), and every placed instance (cladding tiles, doors, windows,
    debris) keeps its WORLD size when the dressed object is scaled in OBJECT
    MODE with transforms left unapplied ('make the house bigger' workflow).
  * Mechanics: the node groups read the host's OWN transform (Blender 5.2
    Self Object -> Object Info) and divide local quantities by the
    world-meters-per-meter factor of their direction (|S . axis| per face-frame
    axis and per instance axis from the actual placement rotation). At object
    scale (1,1,1) every factor is GATED to exactly 1.0 so v2.4 scenes evaluate
    bit-identically (CompoundTest 145/888, ReflowTest-after 240/1236).
  * Density is a COUNT knob (instances per m^2 of the mesh as modeled) and
    keeps its v2.4 semantics on purpose - it is not a world-meter socket
    (rescaling it was built and tested: the first-N Max Instances cap then
    starves later faces and capped Fit layers can find no clean layout);
    Sill Height 0.9 = 0.9 world meters
    above the face base whatever the object scale. Verified against
    CompoundWorldRef (same compound scaled in edit mode = vertices moved):
    object-scale rig and vertex-scale rig dress identically in world space.

v2.5 HouseCraft opening placement math ('Slots') + user bug fixes:
  * SLOTS panel (Fit mode): deterministic per-face COLUMN SLOTS derived from
    wall width (Count Mode 'Per Width' = one opening per N meters of wall,
    'Explicit' = fixed Slot Count) with 'Min Gap X' / 'Opening Width' enforced
    gap math (column pitch >= Opening Width + Min Gap X + 2*Slot Jitter so
    neighbours can never touch or overlap), ONE row per face by default
    ('Slot Rows' x 'Row Spacing', Min Gap Z clamps the row pitch so nothing
    stacks), 'Column Select' {All, First Only, Skip First} so a door layer and
    a window layer split the SAME column grid (First Only = the door column,
    Skip First = the windows beside it - cross-layer collisions impossible by
    construction), 'No-Repeat' (adjacent columns cycle variants, never the
    same variant twice in a row), 'Slot Jitter' (small per-slot organic noise),
    'Sill Line' {Common Z, Face Base}: Common Z = ONE shared world-z sill line
    (host zmin + Sill Height) across every wall of the object - windows align
    exactly like the reference houses; Face Base = per-face sill (v2.4).
  * ROOF PROTECTION (the user's roof-door bug): 'Ground Floor Only' now
    DEFAULTS ON for doors and 'Max Base Height' (world m above host zmin) is a
    hard ceiling on placement-face bases in BOTH Fit layouts - a wall segment
    whose base sits on a roof surface (e.g. the tower face above a wing roof)
    can never receive openings. Explicit upper doors: Ground Floor Only OFF +
    raise Max Base Height. In Slots/Common Z mode a face whose base edge is
    above the sill line gets no slots at all (openings never stand on roofs).
  * BLACK-TRIANGLE fix: cladding tiles now STRADDLE the wall-contact plane
    (centered on it) instead of growing inward from it. Root cause: a wall
    fragment wound INWARD (extrusion/fill leftovers - the user's tower wall
    triangle) swallowed its tiles inside the wall and z-fought their coplanar
    backs, leaving a bare triangle that renders BLACK in the viewport.
    Straddling covers every wall face whatever its winding (verified on a
    tower+wing repro with a deliberately flipped triangle fill).
  * PACK-SWAP demo: one base model, two full looks - only the pack COLLECTION
    sockets on the existing layers are repointed (WornWoodenDoors + louvered
    shutters vs MedievalWindows), same camera, side-by-side renders.

v2.6 the user's custom-shape bug report (2026-10-22) + HouseCraft parity:
  * FIT-DEAD ROOT CAUSE on his blocky stepped massing (demo 'UserShape2',
    rebuilt at the exact proportions/scale of his screenshots: ~2.67 x 2.0 m,
    tallest wall 2.0 m): the ROW-FIT gate (row base + 'Opening Height' <= face
    top) rejected EVERY wall - his walls are shorter than the 2.1-2.2 m
    default/demo Opening Height (windows additionally lose their 0.25-0.9 m
    sill), and the v2.5 cross-layer windows split was emptied as well: the gap
    law clamps his <= 1.33 m walls to ONE column, so 'Column Select' 'Skip
    First' (the window layer of the First-Only/Skip-First split) keeps nothing.
    Evidence: 0 doors + 0 windows on all 20 wall faces with the exact v2.5
    stack (sockets read from his session's autosave), reproduced and measured.
  * FIX - 'Opening Fit' menu {Scale To Face (NEW DEFAULT), Drop (v2.5)} +
    'Min Fit Scale' (0.5): an opening that does not fit its face is SHRUNK to
    the available face height/width (instance auto-fit factor vm_fitk; the gap
    law still holds and the base stays on the sill line); rows that would drop
    past 'Min Fit Scale' are still rejected (not sensible). CONTRACT CHANGE:
    openings now appear on faces shorter than 'Opening Height' (scaled down)
    where v2.5 silently dropped them - documented, measured on UserShape2.
  * VM_RoofCap 'Flat' style + 'Incline' (default 2.5 deg) + 'Fascia' (0.12 m):
    a near-flat cap over every flat top - subtle incline along the region's
    long axis, thin vertical fascia skirt, NEVER invented gable triangles
    (the user's flat-topped design). COMPLETE COVERAGE (CONTRACT CHANGE):
    every up-facing top that cannot take a gable cleanly (non-quad tops,
    undersized fragments, Largest-Face-Only losers) is now FLAT-CAPPED instead
    of skipped-and-left-open - zero interior exposed through the top.
    vm_roofgen: 1 = gable faces, 2 = flat-cap faces.
  * HOUSECRAFT EXACT COUNTS: 'Count Mode' gains 'Exact N' + 'Exact Count' +
    'Exact Pick' {Spread (default), First} - EXACTLY N openings for the whole
    layer (deterministic candidate order: face order, then column/row; Spread
    spaces them evenly). Honest limit: strict largest-face-FIRST ordering is
    not expressible in geometry nodes (Blender 5.2 has no domain sort) -
    'Spread' is the even-coverage variant, 'First' is mesh order.
  * HOUSECRAFT MANUAL PLACEMENT: 'Manual Mask' + 'Manual Mask Group'
    (e.g. 'VM_Slots_Doors') + 'Manual Threshold' - openings are placed ONLY
    where the user weight-painted the named vertex group (Blender-native,
    mirrors HouseCraft ID-painting). The painted area can only REMOVE
    candidates (gap/sill/fit rules hold with precedence). The weight is
    sampled 3x (slot position +/- a quarter opening along the wall) so
    vertex-group interpolation bleed across shared corner verts cannot leak
    openings onto unpainted walls. Limit: mask resolution is vertex-group
    interpolation - sub-wall paint areas need wall subdivision.

v2.7 unambiguous behavior + zero-setup UX (2026-10-22, the user's confusion report):
  * GABLES ONLY ON REQUEST: VM_RoofCap 'Style' DEFAULT is now 'Flat' (was
    'Gable') - a freshly-added VM_RoofCap NEVER invents gable triangles on a
    flat top; 'Gable'/'Hip' are opt-in. The default incline stays 2.5 deg.
  * DESIGN-LANGUAGE DEFAULTS on a FRESHLY-ADDED VM_SceneDetailer: Placement
    Mode 'Fit', Slot Layout 'Slots' (openings on walls out of the box) with
    'Opening Fit: Scale To Face'; 'Primary Props' defaults to the VM_Doors
    collection so an untouched Add Modifier places doors. This is the
    acceptance 'untouched default path' (fresh scene + fresh cube + Add
    Modifier + ZERO socket tweaks -> openings + flat cap + 2.5 deg incline).
  * STARTER re-saved as the canonical CURRENT-DEFAULTS demo: StarterCube is
    flat-capped (Style 'Flat') with visible openings + 'Scale To Face'; a
    new 'GableShowcase' object shows the pitched look opt-in, side by side;
    a new 'StarterCompound' (a literal DUPLICATE of StarterCube edited into
    a tower + lower wing + annex compound - the user's exact action) proves
    the copied stack keeps openings on ground walls and ZERO gable triangles.
  * VERSION VISIBILITY: both node groups gain a top 'About' panel with an
    'Engine Version' string socket ('v2.7') + a one-line usage hint, and the
    version is embedded in the node-group DESCRIPTION (node-group selector
    tooltip). The About sockets are appended LAST and moved to the top, so
    every v2.5/v2.6 socket IDENTIFIER is unchanged (re-pointing an old
    modifier at the new group keeps its saved values). USAGE.txt gains
    'Which version am I running?' and 'Upgrading old stacks'.
  * VM_Tools_Addon.py (delivered + exercised headless): 'VM: Dress Object'
    (one click = the full default v2.7 stack; assigning variant collections
    is the only remaining step), 'VM: Copy/Paste Engine Setup' (full VM_*
    modifier stack incl. collection pointers, identifier-rename-safe) and
    'VM: Save/Load Preset <name>' (JSON presets that travel across .blend
    files; ID references re-matched BY NAME with missing names reported).
  * VM_Assets.blend: both node groups marked as BLENDER ASSETS for the Asset
    Browser (drag the engine onto any object in any file).

Deterministic (fixed seeds). Run (Windows or Linux, Blender 5.2.2):
  blender -b --python build_engine.py
Paths (env overrides): VM_ROOT = working dir (default ./build next to this
script), VM_ASSET_SRC = asset library (default ~/Documents/ViperMeshAssets),
VM_DELIVER = deliverable mirror (default ~/Downloads/blender-engine).
"""

import bpy, bmesh, os, sys, shutil, math, json
from collections import Counter
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pack_ingest

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("VM_ROOT", os.path.join(_HERE, "build"))
ASSET_SRC = os.environ.get("VM_ASSET_SRC", os.path.expanduser("~/Documents/ViperMeshAssets"))
DELIVER = os.environ.get("VM_DELIVER", os.path.expanduser("~/Downloads/blender-engine"))
os.makedirs(ROOT, exist_ok=True)
BLEND_PATH = os.path.join(ROOT, "VM_SceneDetailer.blend")
STARTER_PATH = os.path.join(ROOT, "VM_Starter.blend")
ROOFCAP_PATH = os.path.join(ROOT, "VM_RoofCap.blend")
ENGINE_VERSION = "v2.10"   # the ONE version label: About sockets, descriptions, checks, add-on
ASSETS_PATH = os.path.join(ROOT, "VM_Assets.blend")   # v2.7: asset-browser package
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


def new_mesh_obj(name, verts, faces, col, recalc=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    if recalc:
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


def make_tile_variants(col, name, wx, hy, th, n, mat, bend, straddle=True):
    """Procedural tile variants: slightly bent thin boxes.
    X = width along the row (centered), Z = height along the stack (centered in
    its slot), Y = thickness.

    v2.5 BLACK-TRIANGLE FIX: tiles STRADDLE the wall-contact plane (centered on
    y=0) instead of growing from it ([0, th]). A wall fragment wound INWARD
    (extrusion leftovers - triangle fills with flipped normals) used to swallow
    its tiles inside the wall and z-fight its coplanar tile backs, leaving a
    bare triangle that renders BLACK in the solid/material viewport - the
    user's black-triangle artifact. Straddling covers every wall face whatever
    its winding (half the tile thickness is buried either way; visually
    identical). straddle=False reproduces the legacy [0, th] convention for the
    before/after bug demo."""
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
        if not straddle:
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
                jitter=29, fitrot=31, cladpick=37, slotjit=41)
# v2.8 cladding containment tolerance (LOCAL units): slots whose anchor is not
# within this distance of a real face polygon are dropped (float noise only -
# the phantom-slab fix). Override on the module for debugging.
CLAD_EPS = 0.0005
# v2.8 internal gate switches (diagnostics only - all True in production):
V28_FLAGS = dict(contain=True, gate1=True, greedy=True, occ=True, rr=True)


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


def world_scale_block(b, normal_sock=None, absz_sock=None, loc=(-2700, 1900)):
    """v2.4.1 WORLD-SPACE SIZING contract (see USAGE.txt).

    GN placement math runs in the host's LOCAL space, so an unapplied object
    transform used to stretch everything the user sets in meters (cladding
    tiles, sills, fit offsets). This block reads the host's OWN transform
    (Self Object -> Object Info, 'Original' space) and returns per-direction
    "world meters per local meter" factors to divide local quantities by:

      sx/sy/sz      object-axis factors (vertical offsets, jitter components)
      eff_u/eff_v/eff_n   face-frame factors |S . d| for the frame axes the
                    detailer derives from the face normal (same formula)
      area          face AREA factor -> Density becomes instances per WORLD m^2
      geo           volume-mean factor (Proximity Radius approximation)

    When the object scale is exactly (1,1,1) EVERY factor is GATED to exactly
    1.0 so compensated expressions reduce to the v2.4 ones bit-for-bit
    (regression contract for un-scaled scenes)."""
    so = b.N("GeometryNodeSelfObject", loc)
    oi = b.N("GeometryNodeObjectInfo", (loc[0] + 150, loc[1]), transform_space="ORIGINAL")
    b.L(so.outputs["Self Object"], oi.inputs["Object"])
    self_scale = oi.outputs["Scale"]
    ssep = b.N("ShaderNodeSeparateXYZ", (loc[0] + 320, loc[1]))
    b.L(self_scale, ssep.inputs["Vector"])
    ident = b.N("FunctionNodeCompare", (loc[0] + 320, loc[1] - 180),
                data_type="VECTOR", operation="EQUAL")
    b.L(self_scale, ident.inputs["A"])
    ident.inputs["B"].default_value = (1.0, 1.0, 1.0)

    def gate(val, l, is_vec=False):
        sw = b.N("GeometryNodeSwitch", l)
        sw.input_type = "VECTOR" if is_vec else "FLOAT"
        b.L(ident.outputs["Result"], sw.inputs["Switch"])
        sw.inputs["True"].default_value = (1.0, 1.0, 1.0) if is_vec else 1.0
        b.L(val, sw.inputs["False"])
        return sw.outputs["Output"]

    def eps1(vout, l):
        n = b.N("ShaderNodeMath", l, operation="MAXIMUM")
        b.L(vout, n.inputs[0])
        n.inputs[1].default_value = 1e-5
        return n.outputs["Value"]

    sx = gate(eps1(ssep.outputs["X"], (loc[0] + 520, loc[1] + 60)), (loc[0] + 700, loc[1] + 60))
    sy = gate(eps1(ssep.outputs["Y"], (loc[0] + 520, loc[1])), (loc[0] + 700, loc[1]))
    sz = gate(eps1(ssep.outputs["Z"], (loc[0] + 520, loc[1] - 60)), (loc[0] + 700, loc[1] - 60))

    def vm(op, a, bsock=None, l=(0, 0)):
        n = b.N("ShaderNodeVectorMath", l, operation=op)
        if hasattr(a, "bl_idname"):
            b.L(a, n.inputs[0])
        else:
            n.inputs[0].default_value = a
        if bsock is not None:
            if hasattr(bsock, "bl_idname"):
                b.L(bsock, n.inputs[1])
            else:
                n.inputs[1].default_value = bsock
        return n

    def eff_of(dir_sock, l):
        mul = vm("MULTIPLY", dir_sock, self_scale, l=l)
        ln = b.N("ShaderNodeVectorMath", (l[0] + 170, l[1]), operation="LENGTH")
        b.L(mul.outputs["Vector"], ln.inputs[0])
        return gate(ln.outputs["Value"], (l[0] + 340, l[1]))

    out = dict(sx=sx, sy=sy, sz=sz, gate=gate, eff_of=eff_of)
    if normal_sock is not None:
        # per-face frame axes mirror the detailer's frame formula exactly
        u_raw = vm("CROSS_PRODUCT", (0.0, 0.0, 1.0), normal_sock,
                   l=(loc[0], loc[1] + 320))
        u_norm = b.N("ShaderNodeVectorMath", (loc[0] + 170, loc[1] + 320), operation="NORMALIZE")
        b.L(u_raw.outputs["Vector"], u_norm.inputs[0])
        u_deg = b.N("FunctionNodeCompare", (loc[0] + 170, loc[1] + 200),
                    data_type="FLOAT", operation="GREATER_THAN")
        b.L(absz_sock, u_deg.inputs["A"])
        u_deg.inputs["B"].default_value = 0.995
        u_sw = b.N("GeometryNodeSwitch", (loc[0] + 340, loc[1] + 320))
        u_sw.input_type = "VECTOR"
        b.L(u_deg.outputs["Result"], u_sw.inputs["Switch"])
        u_sw.inputs["True"].default_value = (1.0, 0.0, 0.0)
        b.L(u_norm.outputs["Vector"], u_sw.inputs["False"])
        v_raw = vm("CROSS_PRODUCT", normal_sock, u_sw.outputs["Output"],
                   l=(loc[0] + 520, loc[1] + 320))
        v_norm = b.N("ShaderNodeVectorMath", (loc[0] + 690, loc[1] + 320), operation="NORMALIZE")
        b.L(v_raw.outputs["Vector"], v_norm.inputs[0])
        out["eff_u"] = eff_of(u_sw.outputs["Output"], (loc[0] + 880, loc[1] + 380))
        out["eff_v"] = eff_of(v_norm.outputs["Vector"], (loc[0] + 880, loc[1] + 320))
        out["eff_n"] = eff_of(normal_sock, (loc[0] + 880, loc[1] + 260))
        # face area factor: |det S| * |S^-T n| (density per WORLD square meter)
        nsep_ws = b.N("ShaderNodeSeparateXYZ", (loc[0] + 880, loc[1] + 80))
        b.L(normal_sock, nsep_ws.inputs["Vector"])
        inv = b.N("ShaderNodeCombineXYZ", (loc[0] + 880, loc[1] + 140))
        for ch, g in (("X", sx), ("Y", sy), ("Z", sz)):
            d = b.N("ShaderNodeMath", (loc[0] + 700, loc[1] + 140 - 60 * "XYZ".index(ch)),
                    operation="DIVIDE")
            b.L(nsep_ws.outputs[ch], d.inputs[0])
            b.L(g, d.inputs[1])
            b.L(d.outputs["Value"], inv.inputs[ch])
        invn = b.N("ShaderNodeVectorMath", (loc[0] + 1050, loc[1] + 140), operation="LENGTH")
        b.L(inv.outputs["Vector"], invn.inputs[0])
        det = b.N("ShaderNodeMath", (loc[0] + 1050, loc[1] + 220), operation="MULTIPLY")
        b.L(sx, det.inputs[0])
        b.L(sy, det.inputs[1])
        det2 = b.N("ShaderNodeMath", (loc[0] + 1200, loc[1] + 220), operation="MULTIPLY")
        b.L(det.outputs["Value"], det2.inputs[0])
        b.L(sz, det2.inputs[1])
        area_r = b.N("ShaderNodeMath", (loc[0] + 1350, loc[1] + 180), operation="MULTIPLY")
        b.L(det2.outputs["Value"], area_r.inputs[0])
        b.L(invn.outputs["Value"], area_r.inputs[1])
        out["area"] = gate(area_r.outputs["Value"], (loc[0] + 1520, loc[1] + 180))
    gm = b.N("ShaderNodeMath", (loc[0] + 1050, loc[1] - 180), operation="MULTIPLY")
    b.L(sx, gm.inputs[0]); b.L(sy, gm.inputs[1])
    gm2 = b.N("ShaderNodeMath", (loc[0] + 1200, loc[1] - 180), operation="MULTIPLY")
    b.L(gm.outputs["Value"], gm2.inputs[0]); b.L(sz, gm2.inputs[1])
    groot = b.N("ShaderNodeMath", (loc[0] + 1350, loc[1] - 180), operation="POWER")
    b.L(gm2.outputs["Value"], groot.inputs[0])
    groot.inputs[1].default_value = 1.0 / 3.0
    out["geo"] = gate(groot.outputs["Value"], (loc[0] + 1520, loc[1] - 180))
    return out


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


def exterior_face_field(b, target, loc):
    """v2.9 face-domain field: False for faces buried INSIDE the host solid
    and for zero-area (collapsed) faces.

    Edit-mode modeling leaves hidden faces behind (an extruded top keeps its old
    cap as an internal floor, overlapping boxes in one mesh bury each other's
    tops/walls). Those faces are up-facing/vertical like real ones, so the zone
    tests alone roofed and clad them INSIDE the building (the user's 'roof on a
    floor' bug). Test: cast a ray from just off the face along its normal; when
    the FIRST hit is the BACK of another face (hit normal agrees with the ray)
    the face starts inside the solid. Open meshes / sky-facing tops never hit a
    back face, so they stay exterior; a ledge under an overhang hits the
    overhang's front (downward) face and stays exterior too."""
    x, y = loc
    pos = b.N("GeometryNodeInputPosition", (x, y))
    nrm = b.N("GeometryNodeInputNormal", (x, y - 120))
    off = b.N("ShaderNodeVectorMath", (x + 150, y - 60), operation="SCALE")
    b.L(nrm.outputs["Normal"], off.inputs[0])
    off.inputs["Scale"].default_value = 0.001
    src = b.N("ShaderNodeVectorMath", (x + 300, y), operation="ADD")
    b.L(pos.outputs["Position"], src.inputs[0])
    b.L(off.outputs["Vector"], src.inputs[1])
    rc = b.N("GeometryNodeRaycast", (x + 450, y))
    b.L(target, rc.inputs["Target Geometry"])
    b.L(src.outputs["Vector"], rc.inputs["Source Position"])
    b.L(nrm.outputs["Normal"], rc.inputs["Ray Direction"])
    rc.inputs["Ray Length"].default_value = 10000.0
    dot = b.N("ShaderNodeVectorMath", (x + 650, y - 120), operation="DOT_PRODUCT")
    b.L(rc.outputs["Hit Normal"], dot.inputs[0])
    b.L(nrm.outputs["Normal"], dot.inputs[1])
    back = b.N("FunctionNodeCompare", (x + 800, y - 120), data_type="FLOAT", operation="GREATER_THAN")
    b.L(dot.outputs["Value"], back.inputs["A"])
    back.inputs["B"].default_value = 1e-4
    inside = b.N("FunctionNodeBooleanMath", (x + 950, y), operation="AND")
    b.L(rc.outputs["Is Hit"], inside.inputs[0])
    b.L(back.outputs["Result"], inside.inputs[1])
    # generated roof caps are OPEN sheets: the host top under a cap hits the
    # cap's back and would read 'inside' - hits on vm_roofgen faces don't count
    rg = b.N("GeometryNodeInputNamedAttribute", (x + 300, y - 300))
    rg.data_type = "FLOAT"
    rg.inputs["Name"].default_value = "vm_roofgen"
    rc.data_type = "FLOAT"
    b.L(rg.outputs["Attribute"], rc.inputs["Attribute"])
    host_hit = b.N("FunctionNodeCompare", (x + 800, y - 300), data_type="FLOAT", operation="LESS_THAN")
    b.L(rc.outputs["Attribute"], host_hit.inputs["A"])
    host_hit.inputs["B"].default_value = 0.5
    inside2 = b.N("FunctionNodeBooleanMath", (x + 1000, y - 150), operation="AND")
    b.L(inside.outputs["Boolean"], inside2.inputs[0])
    b.L(host_hit.outputs["Result"], inside2.inputs[1])
    outside = b.N("FunctionNodeBooleanMath", (x + 1100, y), operation="NOT")
    b.L(inside2.outputs["Boolean"], outside.inputs[0])
    # zero-area faces (an extrude collapsed flat - the user's TestFit carries 12)
    # report an arbitrary +Z normal but still MEASURE metres along their edge
    # line: the flat-cap fallback turned one into a roof strip along a wall
    area = b.N("GeometryNodeInputMeshFaceArea", (x + 800, y + 150))
    real = b.N("FunctionNodeCompare", (x + 950, y + 150), data_type="FLOAT", operation="GREATER_THAN")
    b.L(area.outputs["Area"], real.inputs["A"])
    real.inputs["B"].default_value = 1e-6
    ext = b.N("FunctionNodeBooleanMath", (x + 1250, y), operation="AND")
    b.L(outside.outputs["Boolean"], ext.inputs[0])
    b.L(real.outputs["Result"], ext.inputs[1])
    return ext.outputs["Boolean"]


def store_exterior(b, geo, name, loc):
    """Materialize exterior_face_field as a FACE float attribute (evaluation-
    context contract: selections read it back as a plain named attribute).
    Returns (geometry_out, bool_field_reading_it_back).

    The store runs on the MESH component only: Store Named Attribute on the
    whole input also reaches into earlier modifiers' instances and turns their
    object references into anonymous geometry (every Plank/Door instance of a
    stacked dress lost its identity - measured in the v2.9 bring-up)."""
    sep = b.N("GeometryNodeSeparateComponents", (loc[0] - 200, loc[1]))
    b.L(geo, sep.inputs["Geometry"])
    mesh = sep.outputs["Mesh"]
    ext = exterior_face_field(b, mesh, loc)
    conv = b.N("ShaderNodeMath", (loc[0] + 1250, loc[1]), operation="ADD")
    b.L(ext, conv.inputs[0])
    conv.inputs[1].default_value = 0.0
    st = b.N("GeometryNodeStoreNamedAttribute", (loc[0] + 1400, loc[1]), data_type="FLOAT", domain="FACE")
    b.L(mesh, st.inputs["Geometry"])
    st.inputs["Name"].default_value = name
    b.L(conv.outputs["Value"], st.inputs["Value"])
    join = b.N("GeometryNodeJoinGeometry", (loc[0] + 1600, loc[1]))
    for out_name in ("Instances", "Curve", "Point Cloud"):
        b.L(sep.outputs[out_name], join.inputs["Geometry"])
    b.L(st.outputs["Geometry"], join.inputs["Geometry"])
    rd = b.N("GeometryNodeInputNamedAttribute", (loc[0] + 1400, loc[1] - 200))
    rd.data_type = "FLOAT"
    rd.inputs["Name"].default_value = name
    ok = b.N("FunctionNodeCompare", (loc[0] + 1550, loc[1] - 200), data_type="FLOAT", operation="GREATER_EQUAL")
    b.L(rd.outputs["Attribute"], ok.inputs["A"])
    ok.inputs["B"].default_value = 0.5
    return join.outputs["Geometry"], ok.outputs["Result"]


def region_frame(b, geo, loc):
    """v2.9.1 coplanar REGIONS for the flat cap: every connected patch of cap
    faces (Mesh Island - a top split into a grid, an L-shaped top modeled as
    several quads) gets ONE shared frame, written over the per-face vm_rc/ru/
    rv/rw/rh/rz attributes so the cap math downstream is unchanged:
      axes    = the patch's LARGEST face's in-plane axes (ties: highest index),
      extents = min/max of the patch's vertex projections on those axes,
      long    = the longer extent (vm_ru/vm_rw), centre = extents' midpoints,
      height  = mean face-centre z of the patch.
    Identical values on every face of a patch make face->point interpolation
    exact, so a non-individual extrusion yields ONE slab with ONE incline
    plane (was: one tilted slab per face, overlapping into dark triangles).
    Two-phase store (temp vm_g*/vm_t* names, then copy back) keeps every read
    of the ORIGINAL per-face attributes ahead of the overwrite (evaluation-
    context contract)."""
    x, y = loc

    def nattr(name, dt, dx, dy):
        n = b.N("GeometryNodeInputNamedAttribute", (x + dx, y + dy))
        n.data_type = dt
        n.inputs["Name"].default_value = name
        return n.outputs["Attribute"]

    def store(g, name, dt, src, dx):
        st = b.N("GeometryNodeStoreNamedAttribute", (x + dx, y), data_type=dt, domain="FACE")
        b.L(g, st.inputs["Geometry"])
        st.inputs["Name"].default_value = name
        b.L(src, st.inputs["Value"])
        return st.outputs["Geometry"]

    def vm(op, a, c=None, dx=0, dy=0):
        n = b.N("ShaderNodeVectorMath", (x + dx, y + dy), operation=op)
        b.L(a, n.inputs[0])
        if c is not None:
            b.L(c, n.inputs[1])
        return n

    def fm(op, a, c, dx, dy):
        n = b.N("ShaderNodeMath", (x + dx, y + dy), operation=op)
        for i, s in enumerate((a, c)):
            if hasattr(s, "bl_idname"):
                b.L(s, n.inputs[i])
            else:
                n.inputs[i].default_value = s
        return n.outputs["Value"]

    def field_minmax(val, dt, domain, dx, dy):
        n = b.N("GeometryNodeFieldMinAndMax", (x + dx, y + dy), data_type=dt, domain=domain)
        b.L(val, n.inputs["Value"])
        b.L(isl, n.inputs["Group ID"])
        return n

    isl = b.N("GeometryNodeInputMeshIsland", (x, y - 300)).outputs["Island Index"]
    # ---- phase 1a: the patch's representative (largest) face -> region axes
    area = b.N("GeometryNodeInputMeshFaceArea", (x, y - 450)).outputs["Area"]
    amax = field_minmax(area, "FLOAT", "FACE", 150, -450)
    is_rep = b.N("FunctionNodeCompare", (x + 300, y - 450), data_type="FLOAT", operation="GREATER_EQUAL")
    b.L(area, is_rep.inputs["A"])
    b.L(fm("SUBTRACT", amax.outputs["Max"], 1e-9, 300, -600), is_rep.inputs["B"])
    rep_idx = b.N("GeometryNodeSwitch", (x + 450, y - 450))
    rep_idx.input_type = "INT"
    b.L(is_rep.outputs["Result"], rep_idx.inputs["Switch"])
    rep_idx.inputs["False"].default_value = -1
    b.L(b.N("GeometryNodeInputIndex", (x + 300, y - 750)).outputs["Index"], rep_idx.inputs["True"])
    rmax = field_minmax(rep_idx.outputs["Output"], "INT", "FACE", 600, -450)
    g = geo
    for k, (tmp, src) in enumerate((("vm_ga", "vm_ru"), ("vm_gb", "vm_rv"))):
        fai = b.N("GeometryNodeFieldAtIndex", (x + 750, y - 450 - 150 * k), data_type="FLOAT_VECTOR", domain="FACE")
        b.L(rmax.outputs["Max"], fai.inputs["Index"])
        b.L(nattr(src, "FLOAT_VECTOR", 600, -650 - 150 * k), fai.inputs["Value"])
        g = store(g, tmp, "FLOAT_VECTOR", fai.outputs["Value"], 900 + 150 * k)
    # ---- phase 1b: patch extents along the region axes (vertex projections;
    # the face->point read of vm_ga/vm_gb is exact: one value per patch)
    pos = b.N("GeometryNodeInputPosition", (x + 1100, y - 300)).outputs["Position"]
    ext = []
    for k, ax in enumerate(("vm_ga", "vm_gb")):
        d = vm("DOT_PRODUCT", pos, nattr(ax, "FLOAT_VECTOR", 1100, -450 - 150 * k), 1250, -450 - 150 * k)
        ext.append(field_minmax(d.outputs["Value"], "FLOAT", "POINT", 1400, -450 - 150 * k))
    for k, (nm_, sock) in enumerate((("vm_gal", ext[0].outputs["Min"]), ("vm_gah", ext[0].outputs["Max"]),
                                     ("vm_gbl", ext[1].outputs["Min"]), ("vm_gbh", ext[1].outputs["Max"]))):
        g = store(g, nm_, "FLOAT", sock, 1550 + 150 * k)
    # ---- phase 1c: region frame from the stored extents -> temp names
    ga = nattr("vm_ga", "FLOAT_VECTOR", 2150, -300)
    gb = nattr("vm_gb", "FLOAT_VECTOR", 2150, -400)
    gal, gah = nattr("vm_gal", "FLOAT", 2150, -500), nattr("vm_gah", "FLOAT", 2150, -550)
    gbl, gbh = nattr("vm_gbl", "FLOAT", 2150, -600), nattr("vm_gbh", "FLOAT", 2150, -650)
    wa = fm("SUBTRACT", gah, gal, 2300, -500)
    hb = fm("SUBTRACT", gbh, gbl, 2300, -600)
    long_a = b.N("FunctionNodeCompare", (x + 2450, y - 500), data_type="FLOAT", operation="GREATER_EQUAL")
    b.L(wa, long_a.inputs["A"])
    b.L(hb, long_a.inputs["B"])
    gu = b.N("GeometryNodeSwitch", (x + 2600, y - 300))
    gu.input_type = "VECTOR"
    b.L(long_a.outputs["Result"], gu.inputs["Switch"])
    b.L(gb, gu.inputs["False"])
    b.L(ga, gu.inputs["True"])
    nrm = b.N("GeometryNodeInputNormal", (x + 2450, y - 750)).outputs["Normal"]
    gv = vm("NORMALIZE", vm("CROSS_PRODUCT", nrm, gu.outputs["Output"], 2600, -750).outputs["Vector"],
            dx=2750, dy=-750)
    mid_a = fm("MULTIPLY", fm("ADD", gal, gah, 2300, -850), 0.5, 2450, -850)
    mid_b = fm("MULTIPLY", fm("ADD", gbl, gbh, 2300, -950), 0.5, 2450, -950)
    ca = vm("SCALE", ga, dx=2600, dy=-850)
    b.L(mid_a, ca.inputs["Scale"])
    cb = vm("SCALE", gb, dx=2600, dy=-950)
    b.L(mid_b, cb.inputs["Scale"])
    gc = vm("ADD", ca.outputs["Vector"], cb.outputs["Vector"], 2750, -900)
    zavg = b.N("GeometryNodeFieldAverage", (x + 2600, y - 1100), data_type="FLOAT", domain="FACE")
    b.L(nattr("vm_rz", "FLOAT", 2450, -1100), zavg.inputs["Value"])
    b.L(isl, zavg.inputs["Group ID"])
    temps = (("vm_tu", "FLOAT_VECTOR", gu.outputs["Output"], "vm_ru"),
             ("vm_tv", "FLOAT_VECTOR", gv.outputs["Vector"], "vm_rv"),
             ("vm_tw", "FLOAT", fm("MAXIMUM", wa, hb, 2450, -1250), "vm_rw"),
             ("vm_th", "FLOAT", fm("MINIMUM", wa, hb, 2450, -1350), "vm_rh"),
             ("vm_tc", "FLOAT_VECTOR", gc.outputs["Vector"], "vm_rc"),
             ("vm_tz", "FLOAT", zavg.outputs["Mean"], "vm_rz"))
    for k, (tmp, dt, src, _dst) in enumerate(temps):
        g = store(g, tmp, dt, src, 2900 + 150 * k)
    # ---- phase 2: copy the region frame over the per-face attributes
    for k, (tmp, dt, _src, dst) in enumerate(temps):
        g = store(g, dst, dt, nattr(tmp, dt, 3800 + 150 * k, -300), 3800 + 150 * k)
    return g


def build_node_group():
    b = NGBuilder("VM_SceneDetailer")
    iface = b.iface

    iface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")

    p_assets = b.panel("Assets", "Model sets fed into the engine (model-set agnostic)")
    s_pp = b.sock("Primary Props", "NodeSocketCollection", p_assets, desc="Collection of primary prop variants")
    # v2.7 design-language default: a FRESHLY-ADDED VM_SceneDetailer (Fit+Slots)
    # places openings out of the box - the default layer shows doors. Cladding
    # layers point this at their tile collection (the Dress Object recipe does).
    if bpy.data.collections.get("VM_Doors") is not None:
        s_pp.default_value = bpy.data.collections["VM_Doors"]
    b.sock("Debris/Trash Props", "NodeSocketCollection", p_assets, desc="Collection of debris/trash variants")
    b.sock("Debris Ratio", "NodeSocketFloat", p_assets, 0.35, 0.0, 1.0, "FACTOR")

    p_pl = b.panel("Placement", "How parts are placed: Scatter (v1 random), Fit (architectural), Cladding (courses)")
    b.menu_sock("Placement Mode", p_pl, "Fit", "Fit (v2.7 default) = wall-aligned architectural parts/openings (doors, windows); Scatter = v1 random props; Cladding = row courses")
    b.sock("Embed", "NodeSocketFloat", p_pl, 0.02, -10.0, 10.0, "DISTANCE", "Fit: sink the instance's back face into the placement plane by this depth (final normal offset = Backing Offset - Embed)")
    b.sock("Backing Offset", "NodeSocketFloat", p_pl, 0.0, -10.0, 10.0, "DISTANCE", "Fit: distance from the sampled face along +normal to the placement plane the variant's BACK face lands on (set it to the cladding/surface buildup in front of the base wall)")
    b.sock("Fit Jitter", "NodeSocketFloat", p_pl, 0.0, 0.0, 6.283, "ANGLE", "Fit: tiny random rotation (0 = perfectly flush)")
    b.sock("Stand On Face Base", "NodeSocketBool", p_pl, False, desc="Fit per-face anchoring (v2.4, renamed from 'Drop To Ground'): the instance base sits on ITS OWN placement face's lowest edge + Sill Height - never the host bbox (a door on a face whose bottom is at z=1.2 stands at z=1.2)")
    b.sock("Sill Height", "NodeSocketFloat", p_pl, 0.0, -10.0, 10.0, "DISTANCE", "Fit: instance base = face base + Sill Height (doors 0.0, windows ~0.9); with Stand On Face Base off it is added to the sampled point height")
    b.sock("Min Face Width", "NodeSocketFloat", p_pl, 0.6, 0.0, 100.0, "DISTANCE", "Fit: skip placement faces narrower than this (step-wall fragments never receive parts)")
    b.sock("Min Face Height", "NodeSocketFloat", p_pl, 1.2, 0.0, 100.0, "DISTANCE", "Fit: skip placement faces shorter than this")
    b.sock("Ground Floor Only", "NodeSocketBool", p_pl, True, desc="Fit: only faces whose base sits within Ground Tolerance of the host's lowest point get parts (doors never climb steps or land on a roof-adjacent wall segment - v2.5 default ON)")
    b.sock("Ground Tolerance", "NodeSocketFloat", p_pl, 0.1, 0.0, 100.0, "DISTANCE", "Fit: Ground Floor Only acceptance band around the host z-min")
    b.sock("Max Base Height", "NodeSocketFloat", p_pl, 0.5, 0.0, 1000.0, "DISTANCE", "Fit (both layouts): hard ceiling on placement faces - a face whose base edge is higher than host zmin + Max Base Height NEVER receives openings (kills the roof-door case). Raise it for explicit upper doors/windows (with Ground Floor Only off)")
    b.sock("Row Height", "NodeSocketFloat", p_pl, 0.22, 0.001, 100.0, "DISTANCE", "Cladding: course pitch along the stack direction")
    b.sock("Row Overlap", "NodeSocketFloat", p_pl, 0.35, 0.0, 0.95, "FACTOR", "Cladding: courses drawn 1/(1-Overlap) taller so they overlap")
    b.sock("Stagger", "NodeSocketFloat", p_pl, 0.5, 0.0, 1.0, "FACTOR", "Cladding: row phase offset in fraction of slot width")
    b.sock("Jitter", "NodeSocketFloat", p_pl, 0.01, 0.0, 1.0, "DISTANCE", "Cladding: per-slot position noise")
    b.sock("Slot Width", "NodeSocketFloat", p_pl, 0.25, 0.001, 100.0, "DISTANCE", "Cladding: tile width; slot pitch = Slot Width * (1 - Row Overlap)")

    p_slot = b.panel("Slots", "HouseCraft-style opening placement math for Fit mode: per-face column slots derived from wall width, enforced gaps, one row, shared sill line, no duplicate neighbours")
    b.menu_sock("Slot Layout", p_slot, "Slots", "Slots (v2.7 default) = deterministic per-face column slots (HouseCraft opening math); Random = v2.5-pre density sampling")
    b.menu_sock("Count Mode", p_slot, "Per Width", "Slots: Per Width = one opening per Openings Per Width meters of wall (wall-length-derived counts); Explicit = fixed Slot Count per face; Exact N (v2.6) = EXACTLY 'Exact Count' openings for the whole layer (all faces combined, HouseCraft exact-number parity)")
    b.sock("Openings Per Width", "NodeSocketFloat", p_slot, 2.5, 0.1, 100.0, "DISTANCE", "Slots/Per Width: wall meters per opening (count = floor(face width / this), min 1)")
    b.sock("Slot Count", "NodeSocketInt", p_slot, 2, 0, 64, desc="Slots/Explicit: columns per face")
    b.sock("Opening Width", "NodeSocketFloat", p_slot, 1.4, 0.0, 100.0, "DISTANCE", "Slots: nominal opening width (world m); columns are spaced so bbox gap >= Min Gap X between neighbours as long as variants are no wider than this")
    b.sock("Opening Height", "NodeSocketFloat", p_slot, 2.1, 0.0, 100.0, "DISTANCE", "Slots: nominal opening height (world m); rows are spaced so bbox gap >= Min Gap Z between rows as long as variants are no taller than this")
    b.sock("Min Gap X", "NodeSocketFloat", p_slot, 0.4, 0.0, 100.0, "DISTANCE", "Slots: minimum gap between horizontally adjacent openings (world m); column pitch is clamped to Opening Width + Min Gap X + 2*Slot Jitter so neighbours never touch")
    b.sock("Min Gap Z", "NodeSocketFloat", p_slot, 0.3, 0.0, 100.0, "DISTANCE", "Slots: minimum gap between rows (world m) - prevents stacking, no opening on top of another; row pitch clamped to Opening Height + Min Gap Z")
    b.sock("Slot Rows", "NodeSocketInt", p_slot, 1, 1, 16, desc="Slots: opening rows per face (default 1 - a single row never stacks)")
    b.sock("Row Spacing", "NodeSocketFloat", p_slot, 2.4, 0.0, 100.0, "DISTANCE", "Slots: world distance between row base lines (clamped to at least Opening Height + Min Gap Z)")
    b.menu_sock("Column Select", p_slot, "All", "Slots: which columns this layer fills: All; First Only (door column); Skip First (windows beside the door column)")
    b.menu_sock("Sill Line", p_slot, "Common Z", "Slots: Common Z = one shared world-z sill line (host zmin + Sill Height) across ALL walls - aligned window rows like the reference houses (faces above the line get no slots); Face Base = per-face sill (v2.4)")
    b.sock("Slot Jitter", "NodeSocketFloat", p_slot, 0.02, 0.0, 10.0, "DISTANCE", "Slots: small per-slot random horizontal noise along the wall (world m) for an organic look - vertical jitter is deliberately zero so the shared sill line stays exactly aligned")
    b.sock("No-Repeat", "NodeSocketBool", p_slot, True, desc="Slots: adjacent columns never pick the same variant twice in a row (deterministic cycle per face)")
    # ---- v2.6: opening auto-fit + exact counts + manual (vertex-group) masks ----
    b.menu_sock("Opening Fit", p_slot, "Scale To Face",
                "Slots: what happens when the nominal opening does not fit its face: "
                "Scale To Face (v2.6 default) = shrink the instance uniformly to the "
                "available face height/width (gap law still holds; base stays on the sill); "
                "Drop (v2.5) = reject the row outright (nothing placed)")
    b.sock("Min Fit Scale", "NodeSocketFloat", p_slot, 0.5, 0.0, 1.0, "FACTOR",
           "Slots/Scale To Face: openings that would shrink below this fraction of the "
           "nominal size are dropped (a half-size door is not a sensible opening)")
    b.menu_sock("Exact Pick", p_slot, "Spread",
                "Slots/Exact N: how the exactly-N openings are drawn from the candidate "
                "list (deterministic order = face order, then column/row): Spread = evenly "
                "spaced across the whole layer (default); First = the first N candidates in "
                "mesh order. NOTE: strict largest-face-first ordering is NOT expressible in "
                "geometry nodes (no domain sort in Blender 5.2) - Spread gives the even "
                "coverage variant and is documented as the exact-count default")
    b.sock("Exact Count", "NodeSocketInt", p_slot, 2, 0, 4096,
           desc="Slots/Exact N: EXACTLY this many openings for the whole LAYER (all "
                "qualifying faces combined) - HouseCraft 'choose exactly the number' parity; "
                "fewer candidates than N = all candidates are placed")
    b.sock("Manual Mask", "NodeSocketBool", p_slot, False,
           desc="Slots: MANUAL placement gate - only slots whose position falls in the "
                "painted area of the named vertex group are kept (Blender-native weight "
                "painting, HouseCraft ID-paint parity). Painted area can only REMOVE "
                "candidates, never add: gap/sill/fit rules still hold (documented precedence)")
    b.sock("Manual Mask Group", "NodeSocketString", p_slot, "VM_Slots",
           desc="Slots/Manual Mask: vertex group name to sample (e.g. 'VM_Slots_Doors' / "
                "'VM_Slots_Windows' so each layer can be painted independently)")
    b.sock("Manual Threshold", "NodeSocketFloat", p_slot, 0.5, 0.0, 1.0, "FACTOR",
           "Slots/Manual Mask: minimum interpolated weight at the slot position for the "
           "opening to be placed (0.5 = the painted-area interior)")

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
    b.sock("Roof Slope Min", "NodeSocketFloat", p_zone, 0.55, 0.0, 1.0, "FACTOR", "Roof zone SLOPE BAND lower bound (v2.4): Roof = Roof Slope Min <= N.z < Roof Slope Max - pitched faces only; flat tops (N.z ~ 1) are NOT roof")
    b.sock("Roof Slope Max", "NodeSocketFloat", p_zone, 0.92, 0.0, 1.0, "FACTOR", "Roof band upper bound; Floor zone = N.z <= -Roof Slope Min OR N.z >= Roof Slope Max (flat decks and bottoms use Floor or stay bare)")

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
    # v2.4: Roof is a SLOPE BAND (pitched faces only); flat tops/bottoms are Floor
    nrm = b.N("GeometryNodeInputNormal", (-1800, 700))
    nsep = b.N("ShaderNodeSeparateXYZ", (-1600, 700))
    b.L(nrm.outputs["Normal"], nsep.inputs["Vector"])
    absz = b.N("ShaderNodeMath", (-1450, 780), operation="ABSOLUTE")
    b.L(nsep.outputs["Z"], absz.inputs[0])
    neg_rs = b.N("ShaderNodeMath", (-1450, 600), operation="MULTIPLY")
    b.L(gi.outputs["Roof Slope Min"], neg_rs.inputs[0])
    neg_rs.inputs[1].default_value = -1.0

    # ---------------- v2.4.1 world-space sizing factors ----------------------
    ws = world_scale_block(b, nrm.outputs["Normal"], absz.outputs["Value"], (-2800, 1900))
    sx_g, sy_g, sz_g = ws["sx"], ws["sy"], ws["sz"]
    eff_u, eff_v, eff_n = ws["eff_u"], ws["eff_v"], ws["eff_n"]
    dens_f, geo_f = ws["area"], ws["geo"]
    # v2.9: faces buried inside the solid belong to NO zone (no cladding,
    # openings or zone material on hidden internal floors/walls)
    host_geo, ext_ok = store_exterior(b, gi.outputs["Geometry"], "vm_ext", (-3400, 1300))

    def zone_and(sock, loc):
        n = b.N("FunctionNodeBooleanMath", loc, operation="AND")
        b.L(sock, n.inputs[0])
        b.L(ext_ok, n.inputs[1])
        return n
    is_wall_raw = b.N("FunctionNodeCompare", (-1250, 800), data_type="FLOAT", operation="LESS_EQUAL")
    b.L(absz.outputs["Value"], is_wall_raw.inputs["A"])
    b.L(gi.outputs["Wall Slope"], is_wall_raw.inputs["B"])
    is_wall = zone_and(is_wall_raw.outputs["Result"], (-1150, 860))
    roof_lo = b.N("FunctionNodeCompare", (-1250, 650), data_type="FLOAT", operation="GREATER_EQUAL")
    b.L(nsep.outputs["Z"], roof_lo.inputs["A"])
    b.L(gi.outputs["Roof Slope Min"], roof_lo.inputs["B"])
    roof_hi = b.N("FunctionNodeCompare", (-1250, 580), data_type="FLOAT", operation="LESS_THAN")
    b.L(nsep.outputs["Z"], roof_hi.inputs["A"])
    b.L(gi.outputs["Roof Slope Max"], roof_hi.inputs["B"])
    is_roof_raw = b.N("FunctionNodeBooleanMath", (-1080, 620), operation="AND")
    b.L(roof_lo.outputs["Result"], is_roof_raw.inputs[0])
    b.L(roof_hi.outputs["Result"], is_roof_raw.inputs[1])
    is_roof = zone_and(is_roof_raw.outputs["Boolean"], (-1000, 620))
    floor_lo = b.N("FunctionNodeCompare", (-1250, 500), data_type="FLOAT", operation="LESS_EQUAL")
    b.L(nsep.outputs["Z"], floor_lo.inputs["A"])
    b.L(neg_rs.outputs["Value"], floor_lo.inputs["B"])
    floor_hi = b.N("FunctionNodeCompare", (-1250, 430), data_type="FLOAT", operation="GREATER_EQUAL")
    b.L(nsep.outputs["Z"], floor_hi.inputs["A"])
    b.L(gi.outputs["Roof Slope Max"], floor_hi.inputs["B"])
    is_floor_raw = b.N("FunctionNodeBooleanMath", (-1080, 470), operation="OR")
    b.L(floor_lo.outputs["Result"], is_floor_raw.inputs[0])
    b.L(floor_hi.outputs["Result"], is_floor_raw.inputs[1])
    is_floor = zone_and(is_floor_raw.outputs["Boolean"], (-1000, 470))

    zone_sel, _ = b.menu_switch(
        ["All", "Walls", "Roof", "Floor"], "BOOLEAN", gi.outputs["Face Zone"],
        {"All": ext_ok, "Walls": is_wall.outputs["Boolean"], "Roof": is_roof.outputs["Boolean"],
         "Floor": is_floor.outputs["Boolean"]}, loc=(-1050, 650))

    # ---------------- base materials by zone (gated Set Material) ----------------
    base1 = material_gate(b, host_geo, gi.outputs["Wall Material"],
                          is_wall.outputs["Boolean"], (-800, 1100))
    base2 = material_gate(b, base1, gi.outputs["Roof Material"],
                          is_roof.outputs["Boolean"], (-500, 1100))
    base_out = material_gate(b, base2, gi.outputs["Floor Material"],
                             is_floor.outputs["Boolean"], (-200, 1100))

    # sampling must only see the HOST MESH: in stacked modifiers the input also
    # carries earlier instances, and their faces must never receive new parts
    del_inst = b.N("GeometryNodeDeleteGeometry", (-200, 1350), domain="INSTANCE")
    b.L(base_out, del_inst.inputs["Geometry"])
    del_inst.inputs["Selection"].default_value = True
    mesh_only = del_inst.outputs["Geometry"]

    # ---------------- SCATTER branch (v1 behavior, all faces) ----------------
    dist = b.N("GeometryNodeDistributePointsOnFaces", (-1150, 200), distribute_method="RANDOM")
    b.L(mesh_only, dist.inputs["Mesh"])
    # v2.4.1 NOTE: Density is a COUNT knob (instances per m^2 of the mesh as
    # modeled) and is deliberately kept at its v2.4 semantics - it is NOT one of
    # the world-meter sockets. Rescaling it with the object transform was built
    # and tested: the Max Instances cap keeps the FIRST N candidates in face
    # order, so world-m^2 density floods the early faces of a scaled building
    # and starves later ones until capped Fit layers cannot find any clean
    # door/window layout. All DISTANCE sockets and instance SIZES below are
    # world-space compensated regardless.
    b.L(gi.outputs["Density"], dist.inputs["Density"])
    b.L(gi.outputs["Seed"], dist.inputs["Seed"])
    vscale = b.N("ShaderNodeVectorMath", operation="SCALE", location=(-950, 350))
    b.L(dist.outputs["Normal"], vscale.inputs[0])
    # v2.4.1: Surface Offset is WORLD meters along the normal (eff from the
    # distribute's OWN Normal output - valid on points, unlike the Normal input)
    eff_n_sc = ws["eff_of"](dist.outputs["Normal"], (-1150, 420))
    soff_l = b.N("ShaderNodeMath", (-1150, 330), operation="DIVIDE")
    b.L(gi.outputs["Surface Offset"], soff_l.inputs[0])
    b.L(eff_n_sc, soff_l.inputs[1])
    b.L(soff_l.outputs["Value"], vscale.inputs["Scale"])
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

    # ---------------- shared per-face frame (face domain of mesh_only) ----------------
    # u/v in-plane axes + extents + the face's own base height (min corner z).
    # Used by Fit (per-face anchoring + face filters) and Cladding (course layout).
    posf = b.N("GeometryNodeInputPosition", (-1800, -1400))
    cross_zn = b.N("ShaderNodeVectorMath", (-1600, -1300), operation="CROSS_PRODUCT")
    cross_zn.inputs[0].default_value = (0.0, 0.0, 1.0)
    b.L(nrm.outputs["Normal"], cross_zn.inputs[1])
    u_norm = b.N("ShaderNodeVectorMath", (-1450, -1300), operation="NORMALIZE")
    b.L(cross_zn.outputs["Vector"], u_norm.inputs[0])
    # v2.8 CANONICAL TANGENT: cross(Z, n) flips sign with the normal, so two
    # coincident duplicate wall faces (opposite windings - the user's hand-built
    # massing has them) mirrored each other's u grids and their openings
    # interleaved/collided. Flip u into the +Y (or +X when horizontal) half
    # plane so every face on the same plane shares ONE grid.
    u_nsep = b.N("ShaderNodeSeparateXYZ", (-1600, -1150))
    b.L(u_norm.outputs["Vector"], u_nsep.inputs["Vector"])
    u_neg_y = b.N("FunctionNodeCompare", (-1450, -1150), data_type="FLOAT",
                  operation="LESS_THAN")
    b.L(u_nsep.outputs["Y"], u_neg_y.inputs["A"])
    u_neg_y.inputs["B"].default_value = -1e-6
    u_absy = b.N("ShaderNodeMath", (-1550, -1250), operation="ABSOLUTE")
    b.L(u_nsep.outputs["Y"], u_absy.inputs[0])
    u_zero_y = b.N("FunctionNodeCompare", (-1450, -1250), data_type="FLOAT",
                   operation="LESS_EQUAL")
    b.L(u_absy.outputs["Value"], u_zero_y.inputs["A"])
    u_zero_y.inputs["B"].default_value = 1e-6
    u_neg_x = b.N("FunctionNodeCompare", (-1300, -1250), data_type="FLOAT",
                  operation="LESS_THAN")
    b.L(u_nsep.outputs["X"], u_neg_x.inputs["A"])
    u_neg_x.inputs["B"].default_value = 0.0
    u_flip2 = b.N("FunctionNodeBooleanMath", (-1300, -1150), operation="AND")
    b.L(u_zero_y.outputs["Result"], u_flip2.inputs[0])
    b.L(u_neg_x.outputs["Result"], u_flip2.inputs[1])
    u_flip = b.N("FunctionNodeBooleanMath", (-1150, -1150), operation="OR")
    b.L(u_neg_y.outputs["Result"], u_flip.inputs[0])
    b.L(u_flip2.outputs["Boolean"], u_flip.inputs[1])
    u_negv = b.N("ShaderNodeVectorMath", (-1150, -1300), operation="SCALE")
    b.L(u_norm.outputs["Vector"], u_negv.inputs[0])
    u_negv.inputs["Scale"].default_value = -1.0
    u_can_sw = b.N("GeometryNodeSwitch", (-1000, -1250))
    u_can_sw.input_type = "VECTOR"
    b.L(u_flip.outputs["Boolean"], u_can_sw.inputs["Switch"])
    b.L(u_norm.outputs["Vector"], u_can_sw.inputs["False"])
    b.L(u_negv.outputs["Vector"], u_can_sw.inputs["True"])
    u_sw = b.N("GeometryNodeSwitch", (-1300, -1400))
    u_sw.input_type = "VECTOR"
    u_degen = b.N("FunctionNodeCompare", (-1450, -1500), data_type="FLOAT", operation="GREATER_THAN")
    b.L(absz.outputs["Value"], u_degen.inputs["A"])
    u_degen.inputs["B"].default_value = 0.995
    b.L(u_degen.outputs["Result"], u_sw.inputs["Switch"])
    u_sw.inputs["True"].default_value = (1.0, 0.0, 0.0)   # degenerate (flat) faces: world X
    b.L(u_can_sw.outputs["Output"], u_sw.inputs["False"])
    u_out = u_sw.outputs["Output"]
    cross_nu = b.N("ShaderNodeVectorMath", (-1150, -1300), operation="CROSS_PRODUCT")
    b.L(nrm.outputs["Normal"], cross_nu.inputs[0])
    b.L(u_out, cross_nu.inputs[1])
    v_norm = b.N("ShaderNodeVectorMath", (-1000, -1300), operation="NORMALIZE")
    b.L(cross_nu.outputs["Vector"], v_norm.inputs[0])
    v_out = v_norm.outputs["Vector"]

    _loc_seq = [0]

    def random_loc():
        _loc_seq[0] += 1
        return (-800 + 20 * _loc_seq[0], -1800 - 30 * _loc_seq[0])

    def pair(a, bsock, op):
        n = b.N("ShaderNodeMath", (random_loc()), operation=op)
        b.L(a, n.inputs[0]); b.L(bsock, n.inputs[1])
        return n.outputs["Value"]

    # NOTE: corner sampling nodes are deliberately NOT shared between consumers -
    # v2.4 testing showed the shared-corner field evaluated inconsistently between
    # the cladding store context and the Distribute-Points selection context.
    # Each consumer gets its own Sample Index chain (as v2.3 did).
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
            d = b.N("ShaderNodeVectorMath", (-1150, -2900 - 250 * k), operation="SUBTRACT")
            b.L(corner_pos(k), d.inputs[0])
            b.L(posf.outputs["Position"], d.inputs[1])
            dot = b.N("ShaderNodeVectorMath", (-1000, -2900 - 250 * k), operation="DOT_PRODUCT")
            b.L(d.outputs["Vector"], dot.inputs[0])
            b.L(uv, dot.inputs[1])
            diffs.append(dot.outputs["Value"])
        mins, maxs = list(diffs), list(diffs)
        while len(mins) > 1:
            mins = [pair(mins[i], mins[i + 1], "MINIMUM") for i in range(0, len(mins), 2)]
            maxs = [pair(maxs[i], maxs[i + 1], "MAXIMUM") for i in range(0, len(maxs), 2)]
        return mins[0], maxs[0]

    a_lo, a_hi = axis_extents(u_out)
    b_lo, b_hi = axis_extents(v_out)
    w_face = b.N("ShaderNodeMath", (-600, -1500), operation="SUBTRACT")
    b.L(a_hi, w_face.inputs[0]); b.L(a_lo, w_face.inputs[1])
    h_face = b.N("ShaderNodeMath", (-600, -1600), operation="SUBTRACT")
    b.L(b_hi, h_face.inputs[0]); b.L(b_lo, h_face.inputs[1])

    # face base z = lowest world-z corner of the face (per-face anchoring target)
    zc = []
    for k in range(4):
        s = b.N("ShaderNodeSeparateXYZ", (-1350, -2900 - 250 * k))
        b.L(corner_pos(k), s.inputs["Vector"])
        zc.append(s.outputs["Z"])
    face_min_z = pair(pair(zc[0], zc[1], "MINIMUM"), pair(zc[2], zc[3], "MINIMUM"), "MINIMUM")

    # ---- v2.4 evaluation-context contract ---------------------------------
    # Corner-sampled fields (Corners of Face chains) evaluate DIFFERENTLY in a
    # Distribute-Points Selection context than in a Store context (verified on
    # Blender 5.2.2: the same field gives the right value when stored and a
    # wrong one when used as a selection). So ALL frame data is materialized as
    # FACE ATTRIBUTES first (store context is correct), and every selection /
    # placement decision reads those attributes back as simple named-attribute
    # fields. The cladding course math (ns/nr) is computed inside the stores.
    ov_c = b.N("ShaderNodeMath", (-600, -1750), operation="SUBTRACT")
    ov_c.inputs[0].default_value = 1.0
    b.L(gi.outputs["Row Overlap"], ov_c.inputs[1])
    slot_pitch = b.N("ShaderNodeMath", (-450, -1750), operation="MULTIPLY")
    b.L(gi.outputs["Slot Width"], slot_pitch.inputs[0])
    b.L(ov_c.outputs["Value"], slot_pitch.inputs[1])
    # v2.4.1: Slot Width / Row Overlap pitch is WORLD meters -> local pitch
    pitch_l = b.N("ShaderNodeMath", (-375, -1750), operation="DIVIDE")
    b.L(slot_pitch.outputs["Value"], pitch_l.inputs[0])
    b.L(eff_u, pitch_l.inputs[1])
    max1 = b.N("ShaderNodeMath", (-300, -1750), operation="MAXIMUM")
    b.L(pitch_l.outputs["Value"], max1.inputs[0])
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
    # v2.4.1: Row Height is WORLD meters -> local row pitch
    nrh_l = b.N("ShaderNodeMath", (-75, -1750), operation="DIVIDE")
    b.L(nrh.outputs["Value"], nrh_l.inputs[0])
    b.L(eff_v, nrh_l.inputs[1])
    nr_f = b.N("ShaderNodeMath", (0, -1750), operation="DIVIDE")
    b.L(h_face.outputs["Value"], nr_f.inputs[0])
    b.L(nrh_l.outputs["Value"], nr_f.inputs[1])
    nr_c = b.N("ShaderNodeMath", (150, -1750), operation="CEIL")
    b.L(nr_f.outputs["Value"], nr_c.inputs[0])
    nr_1 = b.N("ShaderNodeMath", (300, -1750), operation="MAXIMUM")
    b.L(nr_c.outputs["Value"], nr_1.inputs[0])
    nr_1.inputs[1].default_value = 1.0

    # store frame data on faces -> transfer to face points / read for selection
    store_chain = mesh_only
    stores = [("vm_normal", "FLOAT_VECTOR", nrm.outputs["Normal"]),
              ("vm_u", "FLOAT_VECTOR", u_out),
              ("vm_v", "FLOAT_VECTOR", v_out),
              ("vm_c", "FLOAT_VECTOR", posf.outputs["Position"]),
              ("vm_alo", "FLOAT", a_lo),
              ("vm_blo", "FLOAT", b_lo),
              ("vm_ns", "FLOAT", ns_1.outputs["Value"]),
              ("vm_nr", "FLOAT", nr_1.outputs["Value"]),
              ("vm_w", "FLOAT", w_face.outputs["Value"]),
              ("vm_h", "FLOAT", h_face.outputs["Value"]),
              ("vm_fz", "FLOAT", face_min_z),
              # v2.5 Slots: the face index feeds the deterministic no-repeat
              # variant pick (adjacent columns of a face never share a variant)
              ("vm_fi", "FLOAT", idx.outputs["Index"]),
              # v2.4.1 world-space factors materialized here too: fields derived
              # from the Normal INPUT are only valid on the mesh domain (they
              # evaluate as garbage on POINT domains - the same class of problem
              # as the v2.4 corner-sampling contract), so point/selection
              # consumers read these back as simple named attributes.
              ("vm_eu", "FLOAT", eff_u),
              ("vm_ev", "FLOAT", eff_v),
              ("vm_en", "FLOAT", eff_n)]
    sx = -600
    for nm_, dt, src in stores:
        st = b.N("GeometryNodeStoreNamedAttribute", (sx, -2100), data_type=dt, domain="FACE")
        b.L(store_chain, st.inputs["Geometry"])
        st.inputs["Name"].default_value = nm_
        b.L(src, st.inputs["Value"])
        store_chain = st.outputs["Geometry"]
        sx += 180
    frame_chain = store_chain

    # named-attribute reads for the selection / anchoring fields (simple fields,
    # safe in any evaluation context)
    def named_face(name):
        n = b.N("GeometryNodeInputNamedAttribute", (-1050, -1050 - 120 * named_face.counter))
        named_face.counter += 1
        n.data_type = "FLOAT"
        n.inputs["Name"].default_value = name
        return n.outputs["Attribute"]
    named_face.counter = 0
    na_w = named_face("vm_w")
    na_h = named_face("vm_h")
    na_fz = named_face("vm_fz")

    # Fit never lands on VM_RoofCap-generated faces (gables are not walls):
    # generated faces carry the 'vm_roofgen' face attribute; missing attr = 0 = fine
    rg = b.N("GeometryNodeInputNamedAttribute", (-1250, -1050))
    rg.data_type = "FLOAT"
    rg.inputs["Name"].default_value = "vm_roofgen"
    not_rg = b.N("FunctionNodeCompare", (-1050, -1050), data_type="FLOAT", operation="LESS_THAN")
    b.L(rg.outputs["Attribute"], not_rg.inputs["A"])
    not_rg.inputs["B"].default_value = 0.5

    # ---------------- FIT branch (zone faces, depth axis to normal) ----------------
    # v2.4.1: Min Face Width/Height are WORLD-meter thresholds on the world face
    # extents (local extent >= threshold / eff); eff read back as STORED vm_eu/vm_ev
    na_eu = named_face("vm_eu")
    na_ev = named_face("vm_ev")
    mfw_l = b.N("ShaderNodeMath", (-975, -1150), operation="DIVIDE")
    b.L(gi.outputs["Min Face Width"], mfw_l.inputs[0])
    b.L(na_eu, mfw_l.inputs[1])
    sel_w = b.N("FunctionNodeCompare", (-850, -1150), data_type="FLOAT", operation="GREATER_EQUAL")
    b.L(na_w, sel_w.inputs["A"])
    b.L(mfw_l.outputs["Value"], sel_w.inputs["B"])
    mfh_l = b.N("ShaderNodeMath", (-975, -1250), operation="DIVIDE")
    b.L(gi.outputs["Min Face Height"], mfh_l.inputs[0])
    b.L(na_ev, mfh_l.inputs[1])
    sel_h = b.N("FunctionNodeCompare", (-850, -1250), data_type="FLOAT", operation="GREATER_EQUAL")
    b.L(na_h, sel_h.inputs["A"])
    b.L(mfh_l.outputs["Value"], sel_h.inputs["B"])
    sel_f1 = b.N("FunctionNodeBooleanMath", (-650, -1100), operation="AND")
    b.L(zone_sel, sel_f1.inputs[0])
    b.L(sel_w.outputs["Result"], sel_f1.inputs[1])
    sel_f2 = b.N("FunctionNodeBooleanMath", (-500, -1100), operation="AND")
    b.L(sel_f1.outputs["Boolean"], sel_f2.inputs[0])
    b.L(sel_h.outputs["Result"], sel_f2.inputs[1])
    sel_f3 = b.N("FunctionNodeBooleanMath", (-350, -1100), operation="AND")
    b.L(sel_f2.outputs["Boolean"], sel_f3.inputs[0])
    b.L(not_rg.outputs["Result"], sel_f3.inputs[1])
    # Ground Floor Only: face base within Ground Tolerance of the host z-min
    bb = b.N("GeometryNodeBoundBox", (-1500, -700))
    b.L(mesh_only, bb.inputs["Geometry"])
    bb_sep = b.N("ShaderNodeSeparateXYZ", (-1300, -700))
    b.L(bb.outputs["Min"], bb_sep.inputs["Vector"])
    gsub = b.N("ShaderNodeMath", (-1150, -850), operation="SUBTRACT")
    b.L(na_fz, gsub.inputs[0])
    b.L(bb_sep.outputs["Z"], gsub.inputs[1])
    gabs = b.N("ShaderNodeMath", (-1000, -850), operation="ABSOLUTE")
    b.L(gsub.outputs["Value"], gabs.inputs[0])
    on_ground = b.N("FunctionNodeCompare", (-850, -850), data_type="FLOAT", operation="LESS_EQUAL")
    b.L(gabs.outputs["Value"], on_ground.inputs["A"])
    # v2.4.1: Ground Tolerance is WORLD meters (local z band = tol / sz)
    gt_l = b.N("ShaderNodeMath", (-975, -950), operation="DIVIDE")
    b.L(gi.outputs["Ground Tolerance"], gt_l.inputs[0])
    b.L(sz_g, gt_l.inputs[1])
    b.L(gt_l.outputs["Value"], on_ground.inputs["B"])
    g_not = b.N("FunctionNodeBooleanMath", (-700, -950), operation="NOT")
    b.L(gi.outputs["Ground Floor Only"], g_not.inputs[0])
    g_ok = b.N("FunctionNodeBooleanMath", (-550, -900), operation="OR")
    b.L(g_not.outputs["Boolean"], g_ok.inputs[0])
    b.L(on_ground.outputs["Result"], g_ok.inputs[1])
    fit_sel = b.N("FunctionNodeBooleanMath", (-200, -1000), operation="AND")
    b.L(sel_f3.outputs["Boolean"], fit_sel.inputs[0])
    b.L(g_ok.outputs["Boolean"], fit_sel.inputs[1])

    # ---------------- v2.5 Slots layout menus + roof protection ----------------
    # Slot Layout: Random = v2.5-pre density sampling, Slots = HouseCraft
    # column-slot math. The per-item menu outputs are the item-selected bools.
    slot_sw, slot_bools = b.menu_switch(["Random", "Slots"], "BOOLEAN",
                                        gi.outputs["Slot Layout"], {}, loc=(-200, -1250))
    b.ng.nodes[-1].inputs["Slots"].default_value = True
    is_slots = slot_bools["Slots"]
    sill_sw, sill_bools = b.menu_switch(["Face Base", "Common Z"], "BOOLEAN",
                                        gi.outputs["Sill Line"], {}, loc=(-200, -1450))
    b.ng.nodes[-1].inputs["Common Z"].default_value = True
    common_z = sill_bools["Common Z"]
    cm_sw, cm_bools = b.menu_switch(["Per Width", "Explicit", "Exact N"], "BOOLEAN",
                                    gi.outputs["Count Mode"], {}, loc=(-200, -1650))
    b.ng.nodes[-1].inputs["Per Width"].default_value = True
    per_width_mode = cm_bools["Per Width"]
    exact_mode = cm_bools["Exact N"]
    ep_sw, ep_bools = b.menu_switch(["Spread", "First"], "BOOLEAN",
                                    gi.outputs["Exact Pick"], {}, loc=(-200, -1750))
    b.ng.nodes[-1].inputs["Spread"].default_value = True
    exact_spread = ep_bools["Spread"]
    of_sw, of_bools = b.menu_switch(["Drop", "Scale To Face"], "BOOLEAN",
                                    gi.outputs["Opening Fit"], {}, loc=(-200, -1850))
    b.ng.nodes[-1].inputs["Scale To Face"].default_value = True
    fit_scale_mode = of_bools["Scale To Face"]

    # Max Base Height (BOTH layouts): a face whose base edge sits higher than
    # host zmin + Max Base Height NEVER receives openings - the roof-adjacent
    # wall segment case (door standing on a wing roof) is impossible by default.
    # v2.4.1: Max Base Height is WORLD meters above the host z-min.
    mbh_l = b.N("ShaderNodeMath", (-50, -850), operation="DIVIDE")
    b.L(gi.outputs["Max Base Height"], mbh_l.inputs[0])
    b.L(sz_g, mbh_l.inputs[1])
    mbh_z = b.N("ShaderNodeMath", (100, -850), operation="ADD")
    b.L(bb_sep.outputs["Z"], mbh_z.inputs[0])
    b.L(mbh_l.outputs["Value"], mbh_z.inputs[1])
    mbh_ok = b.N("FunctionNodeCompare", (250, -850), data_type="FLOAT", operation="LESS_EQUAL")
    b.L(na_fz, mbh_ok.inputs["A"])
    b.L(mbh_z.outputs["Value"], mbh_ok.inputs["B"])
    fit_sel1 = b.N("FunctionNodeBooleanMath", (400, -1000), operation="AND")
    b.L(fit_sel.outputs["Boolean"], fit_sel1.inputs[0])
    b.L(mbh_ok.outputs["Result"], fit_sel1.inputs[1])

    # Slots/Common Z sill line: host zmin + Sill Height (world z, SAME for every
    # ground-storey wall). v2.10: a wall whose base edge is ABOVE the line (an
    # upper storey standing on a roof or on the storey below) is no longer
    # rejected - its rows start at its OWN base + Sill Height (targ switch
    # below). Doors stay off roofs through Ground Floor Only + Max Base Height,
    # which reject raised faces on their own.
    # v2.4.1: Sill Height is WORLD meters -> local = sill / sz (hoisted here so
    # the sill line and the v2.4 anchoring below share one divide)
    sill_l = b.N("ShaderNodeMath", (550, -550), operation="DIVIDE")
    b.L(gi.outputs["Sill Height"], sill_l.inputs[0])
    b.L(sz_g, sill_l.inputs[1])
    sill_line_z = b.N("ShaderNodeMath", (100, -1050), operation="ADD")
    b.L(bb_sep.outputs["Z"], sill_line_z.inputs[0])
    b.L(sill_l.outputs["Value"], sill_line_z.inputs[1])
    sill_eps = b.N("ShaderNodeMath", (250, -1050), operation="ADD")
    b.L(sill_line_z.outputs["Value"], sill_eps.inputs[0])
    sill_eps.inputs[1].default_value = 0.001
    fit_sel2 = fit_sel1

    # ---- v2.8 SPREAD: per-face ordinal among qualifying Fit faces + their total
    # (stored as face attrs; the Max Instances cap below becomes ROUND-ROBIN -
    # one opening per qualifying face before any face gets a second - instead of
    # first-N in point order which starved every face after the first wall).
    fit_ff = b.N("ShaderNodeMath", (1000, -1100), operation="ADD")
    b.L(fit_sel2.outputs["Boolean"], fit_ff.inputs[0])
    fit_ff.inputs[1].default_value = 0.0
    acc_ffo = b.N("GeometryNodeAccumulateField", (1150, -1100), domain="FACE")
    b.L(fit_ff.outputs["Value"], acc_ffo.inputs["Value"])
    st_ffo = b.N("GeometryNodeStoreNamedAttribute", (1300, -1100), data_type="FLOAT",
                 domain="FACE")
    b.L(frame_chain, st_ffo.inputs["Geometry"])
    st_ffo.inputs["Name"].default_value = "vm_ffo"
    b.L(acc_ffo.outputs["Leading"], st_ffo.inputs["Value"])
    st_ffn = b.N("GeometryNodeStoreNamedAttribute", (1480, -1100), data_type="FLOAT",
                 domain="FACE")
    b.L(st_ffo.outputs["Geometry"], st_ffn.inputs["Geometry"])
    st_ffn.inputs["Name"].default_value = "vm_ffn"
    b.L(acc_ffo.outputs["Total"], st_ffn.inputs["Value"])
    frame_chain = st_ffn.outputs["Geometry"]

    dist_f = b.N("GeometryNodeDistributePointsOnFaces", (250, -100), distribute_method="RANDOM")
    b.L(frame_chain, dist_f.inputs["Mesh"])
    b.L(fit_sel2.outputs["Boolean"], dist_f.inputs["Selection"])
    b.L(gi.outputs["Density"], dist_f.inputs["Density"])   # v2.4.1: count knob (see dist above)
    b.L(gi.outputs["Seed"], dist_f.inputs["Seed"])
    # offset = normal * (Backing Offset - Embed): the variant's back face lands on
    # the backing plane (distance Backing Offset along +normal - e.g. the cladding
    # layer in front of the base wall) and is then sunk by Embed. With the strict
    # back-center variant origin this keeps the wall-contact face ON the surface
    # buildup instead of behind it, independent of variant depth.
    emb_net = b.N("ShaderNodeMath", (250, -350), operation="SUBTRACT")
    b.L(gi.outputs["Backing Offset"], emb_net.inputs[0])
    b.L(gi.outputs["Embed"], emb_net.inputs[1])
    # v2.4.1: Backing Offset / Embed are WORLD meters along the face normal
    # (eff read back as STORED vm_en - point-domain fields from the Normal input
    # are garbage)
    na_en = named_face("vm_en")
    emb_l = b.N("ShaderNodeMath", (350, -350), operation="DIVIDE")
    b.L(emb_net.outputs["Value"], emb_l.inputs[0])
    b.L(na_en, emb_l.inputs[1])
    vscale_f = b.N("ShaderNodeVectorMath", (450, -150), operation="SCALE")
    b.L(dist_f.outputs["Normal"], vscale_f.inputs[0])
    b.L(emb_l.outputs["Value"], vscale_f.inputs["Scale"])
    # v2.4 per-face anchoring: base z = THE FACE'S OWN base edge + Sill Height
    na_fz = b.N("GeometryNodeInputNamedAttribute", (450, -500))
    na_fz.data_type = "FLOAT"
    na_fz.inputs["Name"].default_value = "vm_fz"
    # v2.4.1: Sill Height is WORLD meters above the face base (sill_l hoisted
    # above with the v2.5 sill-line gate - one divide shared by both)
    stand_base = b.N("ShaderNodeMath", (650, -450), operation="ADD")
    b.L(na_fz.outputs["Attribute"], stand_base.inputs[0])
    b.L(sill_l.outputs["Value"], stand_base.inputs[1])
    stand_z = b.N("ShaderNodeMath", (800, -450), operation="SUBTRACT")
    b.L(stand_base.outputs["Value"], stand_z.inputs[0])
    b.L(sep.outputs["Z"], stand_z.inputs[1])
    z_stand = b.N("ShaderNodeCombineXYZ", (950, -450))
    b.L(stand_z.outputs["Value"], z_stand.inputs["Z"])
    z_plain = b.N("ShaderNodeCombineXYZ", (950, -600))
    b.L(sill_l.outputs["Value"], z_plain.inputs["Z"])
    g_sw = b.N("GeometryNodeSwitch", (1100, -500))
    g_sw.input_type = "VECTOR"
    b.L(gi.outputs["Stand On Face Base"], g_sw.inputs["Switch"])
    b.L(z_plain.outputs["Vector"], g_sw.inputs["False"])
    b.L(z_stand.outputs["Vector"], g_sw.inputs["True"])

    # ---- v2.8 GAP LAW for Fit openings (the user's 'all openings cram onto one
    # wall' bug, part B): every Fit candidate snaps onto the wall's OPENING
    # GRID - one opening per (wall plane, column) strip, centered in its strip.
    # Strip pitch = Opening Width + Min Gap X + 2*Slot Jitter (world), so any
    # two kept neighbours are >= Opening Width + Min Gap X + 2*Slot Jitter apart
    # before jitter and keep >= Min Gap X of bbox gap after it - the Slots gap
    # law, now also for 'Random' layout (random which strips fill, never
    # overlapping). Strips whose nominal opening would cross the face edge are
    # dropped. Per-plane groups merge coincident duplicate faces (hand-built
    # meshes) so they share one grid instead of interleaving.
    def rnamed(name, dt="FLOAT", dy=0):
        n = b.N("GeometryNodeInputNamedAttribute", (250, -2600 - 110 * rnamed.counter - dy))
        rnamed.counter += 1
        n.data_type = dt
        n.inputs["Name"].default_value = name
        return n.outputs["Attribute"]
    rnamed.counter = 0
    r_c = rnamed("vm_c", "FLOAT_VECTOR"); r_u = rnamed("vm_u", "FLOAT_VECTOR")
    r_alo = rnamed("vm_alo"); r_w = rnamed("vm_w"); r_eu = rnamed("vm_eu")
    dpos = b.N("GeometryNodeInputPosition", (250, -3450))
    dsub = b.N("ShaderNodeVectorMath", (400, -3450), operation="SUBTRACT")
    b.L(dpos.outputs["Position"], dsub.inputs[0]); b.L(r_c, dsub.inputs[1])
    da_ = b.N("ShaderNodeVectorMath", (550, -3450), operation="DOT_PRODUCT")
    b.L(dsub.outputs["Vector"], da_.inputs[0]); b.L(r_u, da_.inputs[1])
    gx_s0 = b.N("ShaderNodeMath", (400, -3600), operation="ADD")
    b.L(gi.outputs["Opening Width"], gx_s0.inputs[0])
    b.L(gi.outputs["Min Gap X"], gx_s0.inputs[1])
    gx_s1 = b.N("ShaderNodeMath", (550, -3600), operation="MULTIPLY_ADD")
    b.L(gi.outputs["Slot Jitter"], gx_s1.inputs[0])
    gx_s1.inputs[1].default_value = 2.0
    b.L(gx_s0.outputs["Value"], gx_s1.inputs[2])     # Opening Width + Min Gap X + 2*Jitter
    gx_s2 = b.N("ShaderNodeMath", (700, -3600), operation="DIVIDE")
    b.L(gx_s1.outputs["Value"], gx_s2.inputs[0])
    b.L(r_eu, gx_s2.inputs[1])
    strip_pitch = b.N("ShaderNodeMath", (850, -3600), operation="MAXIMUM")
    b.L(gx_s2.outputs["Value"], strip_pitch.inputs[0])
    strip_pitch.inputs[1].default_value = 0.001
    # v2.8.2 EVEN-FILL STRIPS: the strip grid fills the face EVENLY (ns strips
    # centred at alo + (k+0.5)*w/ns) instead of a fixed pitch glued to the
    # face's left edge. The old alignment put a narrow face's single strip at
    # pitch/2 and the edge guard then rejected it outright (1.6 m tower wall:
    # centre 0.92 + half-opening 0.72 = 1.64 > 1.6 -> ZERO doors there).
    # Even fill satisfies the same gap law (spacing w/ns >= pitch) and every
    # centred opening fits inside its face by construction.
    ns_n1 = b.N("ShaderNodeMath", (550, -3300), operation="DIVIDE")
    b.L(r_w, ns_n1.inputs[0])
    b.L(strip_pitch.outputs["Value"], ns_n1.inputs[1])
    ns_n2 = b.N("ShaderNodeMath", (700, -3300), operation="FLOOR")
    b.L(ns_n1.outputs["Value"], ns_n2.inputs[0])
    ns_cnt = b.N("ShaderNodeMath", (850, -3300), operation="MAXIMUM")
    b.L(ns_n2.outputs["Value"], ns_cnt.inputs[0])
    ns_cnt.inputs[1].default_value = 1.0
    strip_eff = b.N("ShaderNodeMath", (1000, -3300), operation="DIVIDE")
    b.L(r_w, strip_eff.inputs[0])
    b.L(ns_cnt.outputs["Value"], strip_eff.inputs[1])
    s_r1 = b.N("ShaderNodeMath", (850, -3450), operation="SUBTRACT")
    b.L(da_.outputs["Value"], s_r1.inputs[0]); b.L(r_alo, s_r1.inputs[1])
    s_r2 = b.N("ShaderNodeMath", (1000, -3450), operation="DIVIDE")
    b.L(s_r1.outputs["Value"], s_r2.inputs[0])
    b.L(strip_eff.outputs["Value"], s_r2.inputs[1])
    s_r3 = b.N("ShaderNodeMath", (1150, -3450), operation="FLOOR")
    b.L(s_r2.outputs["Value"], s_r3.inputs[0])
    ns_m1 = b.N("ShaderNodeMath", (1150, -3250), operation="SUBTRACT")
    b.L(ns_cnt.outputs["Value"], ns_m1.inputs[0])
    ns_m1.inputs[1].default_value = 1.0
    s_r3b = b.N("ShaderNodeMath", (1300, -3350), operation="MINIMUM")
    b.L(s_r3.outputs["Value"], s_r3b.inputs[0])
    b.L(ns_m1.outputs["Value"], s_r3b.inputs[1])
    s_rand = b.N("ShaderNodeMath", (1300, -3450), operation="MAXIMUM")
    b.L(s_r3b.outputs["Value"], s_rand.inputs[0])
    s_rand.inputs[1].default_value = 0.0
    c_u1 = b.N("ShaderNodeMath", (1450, -3450), operation="MULTIPLY_ADD")
    b.L(s_rand.outputs["Value"], c_u1.inputs[0])
    b.L(strip_eff.outputs["Value"], c_u1.inputs[1])
    b.L(r_alo, c_u1.inputs[2])
    c_u2 = b.N("ShaderNodeMath", (1600, -3450), operation="MULTIPLY_ADD")
    c_u2.inputs[0].default_value = 0.5
    b.L(strip_eff.outputs["Value"], c_u2.inputs[1])
    b.L(c_u1.outputs["Value"], c_u2.inputs[2])
    half_s1 = b.N("ShaderNodeMath", (850, -3750), operation="MULTIPLY_ADD")
    half_s1.inputs[1].default_value = 0.5
    b.L(gi.outputs["Opening Width"], half_s1.inputs[0])
    b.L(gi.outputs["Slot Jitter"], half_s1.inputs[2])
    half_s2 = b.N("ShaderNodeMath", (1000, -3750), operation="DIVIDE")
    b.L(half_s1.outputs["Value"], half_s2.inputs[0])
    b.L(r_eu, half_s2.inputs[1])
    e_lo1 = b.N("ShaderNodeMath", (1300, -3750), operation="SUBTRACT")
    b.L(c_u2.outputs["Value"], e_lo1.inputs[0])
    b.L(half_s2.outputs["Value"], e_lo1.inputs[1])
    e_lo = b.N("FunctionNodeCompare", (1450, -3750), data_type="FLOAT",
               operation="GREATER_EQUAL")
    b.L(e_lo1.outputs["Value"], e_lo.inputs["A"]); b.L(r_alo, e_lo.inputs["B"])
    e_hi1 = b.N("ShaderNodeMath", (1300, -3900), operation="ADD")
    b.L(c_u2.outputs["Value"], e_hi1.inputs[0])
    b.L(half_s2.outputs["Value"], e_hi1.inputs[1])
    e_hi2 = b.N("ShaderNodeMath", (1450, -3900), operation="ADD")
    b.L(r_alo, e_hi2.inputs[0]); b.L(r_w, e_hi2.inputs[1])
    e_hi = b.N("FunctionNodeCompare", (1600, -3900), data_type="FLOAT",
               operation="LESS_EQUAL")
    b.L(e_hi1.outputs["Value"], e_hi.inputs["A"]); b.L(e_hi2.outputs["Value"], e_hi.inputs["B"])
    edge_ok = b.N("FunctionNodeBooleanMath", (1750, -3800), operation="AND")
    b.L(e_lo.outputs["Result"], edge_ok.inputs[0])
    b.L(e_hi.outputs["Result"], edge_ok.inputs[1])
    # snap: u := strip centre + slot jitter (world meters -> local via vm_eu)
    rv_rjit = b.N("FunctionNodeRandomValue", (1750, -3600), data_type="FLOAT")
    rv_rjit.inputs["Min"].default_value = -1.0
    rv_rjit.inputs["Max"].default_value = 1.0
    b.L(idx.outputs["Index"], rv_rjit.inputs["ID"])
    b.L(seed_node(b, gi.outputs["Seed"], SEED_OFF["slotjit"] + 2), rv_rjit.inputs["Seed"])
    rj_l = b.N("ShaderNodeMath", (1900, -3600), operation="DIVIDE")
    b.L(gi.outputs["Slot Jitter"], rj_l.inputs[0]); b.L(r_eu, rj_l.inputs[1])
    rj_m = b.N("ShaderNodeMath", (2050, -3600), operation="MULTIPLY")
    b.L(rv_rjit.outputs["Value"], rj_m.inputs[0])
    b.L(rj_l.outputs["Value"], rj_m.inputs[1])
    a_snap = b.N("ShaderNodeMath", (2200, -3500), operation="ADD")
    b.L(c_u2.outputs["Value"], a_snap.inputs[0])
    b.L(rj_m.outputs["Value"], a_snap.inputs[1])
    da_snap = b.N("ShaderNodeMath", (2350, -3500), operation="SUBTRACT")
    b.L(a_snap.outputs["Value"], da_snap.inputs[0])
    b.L(da_.outputs["Value"], da_snap.inputs[1])
    snap_vec = b.N("ShaderNodeVectorMath", (2500, -3500), operation="SCALE")
    b.L(r_u, snap_vec.inputs[0])
    b.L(da_snap.outputs["Value"], snap_vec.inputs["Scale"])

    off_sum = b.N("ShaderNodeVectorMath", (1250, -300), operation="ADD")
    b.L(vscale_f.outputs["Vector"], off_sum.inputs[0])
    b.L(g_sw.outputs["Output"], off_sum.inputs[1])
    off_sum2 = b.N("ShaderNodeVectorMath", (1450, -300), operation="ADD")
    b.L(off_sum.outputs["Vector"], off_sum2.inputs[0])
    b.L(snap_vec.outputs["Vector"], off_sum2.inputs[1])
    setpos_f = b.N("GeometryNodeSetPosition", (1600, -150))
    b.L(dist_f.outputs["Points"], setpos_f.inputs["Geometry"])
    b.L(off_sum2.outputs["Vector"], setpos_f.inputs["Offset"])
    capn_f = b.N("GeometryNodeStoreNamedAttribute", (1800, -150), data_type="FLOAT_VECTOR", domain="POINT")
    b.L(setpos_f.outputs["Geometry"], capn_f.inputs["Geometry"])
    capn_f.inputs["Name"].default_value = "vm_normal"
    b.L(dist_f.outputs["Normal"], capn_f.inputs["Value"])
    # v2.8: per-point strip column + row 0 + edge guard -> shared gap-law greedy
    rg1 = b.N("GeometryNodeStoreNamedAttribute", (2000, -150), data_type="FLOAT", domain="POINT")
    b.L(capn_f.outputs["Geometry"], rg1.inputs["Geometry"])
    rg1.inputs["Name"].default_value = "vm_gcol"
    b.L(s_rand.outputs["Value"], rg1.inputs["Value"])
    rg2 = b.N("GeometryNodeStoreNamedAttribute", (2200, -150), data_type="FLOAT", domain="POINT")
    b.L(rg1.outputs["Geometry"], rg2.inputs["Geometry"])
    rg2.inputs["Name"].default_value = "vm_grow"
    rg2.inputs["Value"].default_value = 0.0
    rg3 = b.N("GeometryNodeStoreNamedAttribute", (2400, -150), data_type="FLOAT", domain="POINT")
    b.L(rg2.outputs["Geometry"], rg3.inputs["Geometry"])
    rg3.inputs["Name"].default_value = "vm_gate1"
    eg_f = b.N("ShaderNodeMath", (2200, -4000), operation="ADD")
    b.L(edge_ok.outputs["Boolean"], eg_f.inputs[0])
    eg_f.inputs[1].default_value = 0.0
    b.L(eg_f.outputs["Value"], rg3.inputs["Value"])

    # ---------------- v2.5 SLOTS branch (HouseCraft opening placement math) ----
    # Per-face COLUMN SLOTS: one point per eligible face -> a 64x4 column/row
    # grid realized as slot points (the cladding trick), then kept/positioned by
    # the slot math. Every distance socket is WORLD meters converted to local
    # units through the STORED per-face factors (vm_eu / vm_ev - evaluation-
    # context contract). The slot point sits exactly ON its opening's base line:
    #  x = face u-range filled evenly: alo + (col + 0.5) * (face width / ns)
    #  z = sill line + row * row pitch  (Sill Line 'Common Z': host zmin + Sill
    #      Height, ONE shared world-z line across every wall; 'Face Base': the
    #      face's own base + Sill Height)
    # ns = floor(width / Openings Per Width) (min 1) or Slot Count (Explicit),
    # clamped so pitch >= Opening Width + Min Gap X + 2*Slot Jitter: neighbouring
    # columns can never touch or overlap; row pitch clamped by Opening Height +
    # Min Gap Z so nothing stacks on top of anything.
    m2p_s = b.N("GeometryNodeMeshToPoints", (1500, -750))
    m2p_s.mode = "FACES"
    b.L(frame_chain, m2p_s.inputs["Mesh"])
    b.L(fit_sel2.outputs["Boolean"], m2p_s.inputs["Selection"])
    grid_s = b.N("GeometryNodeMeshGrid", (1500, -950))
    grid_s.inputs["Vertices X"].default_value = 64
    grid_s.inputs["Vertices Y"].default_value = 4
    m2p_gs = b.N("GeometryNodeMeshToPoints", (1700, -950))
    m2p_gs.mode = "VERTICES"
    b.L(grid_s.outputs["Mesh"], m2p_gs.inputs["Mesh"])
    smod = b.N("ShaderNodeMath", (1850, -950), operation="FLOORED_MODULO")
    b.L(idx.outputs["Index"], smod.inputs[0])
    smod.inputs[1].default_value = 64.0
    sdiv = b.N("ShaderNodeMath", (1850, -1100), operation="DIVIDE")
    b.L(idx.outputs["Index"], sdiv.inputs[0])
    sdiv.inputs[1].default_value = 64.0
    sfl = b.N("ShaderNodeMath", (2000, -1100), operation="FLOOR")
    b.L(sdiv.outputs["Value"], sfl.inputs[0])
    sg1 = b.N("GeometryNodeStoreNamedAttribute", (2050, -950), data_type="FLOAT", domain="POINT")
    b.L(m2p_gs.outputs["Points"], sg1.inputs["Geometry"])
    sg1.inputs["Name"].default_value = "vm_sgi"
    b.L(smod.outputs["Value"], sg1.inputs["Value"])
    sg2 = b.N("GeometryNodeStoreNamedAttribute", (2230, -950), data_type="FLOAT", domain="POINT")
    b.L(sg1.outputs["Geometry"], sg2.inputs["Geometry"])
    sg2.inputs["Name"].default_value = "vm_sgj"
    b.L(sfl.outputs["Value"], sg2.inputs["Value"])
    iop_s = b.N("GeometryNodeInstanceOnPoints", (2450, -750))
    b.L(m2p_s.outputs["Points"], iop_s.inputs["Points"])
    b.L(sg2.outputs["Geometry"], iop_s.inputs["Instance"])
    real_s = b.N("GeometryNodeRealizeInstances", (2650, -750))
    b.L(iop_s.outputs["Instances"], real_s.inputs["Geometry"])

    def snamed(name, dt="FLOAT"):
        n = b.N("GeometryNodeInputNamedAttribute", (2700, -1100 - 110 * snamed.counter))
        snamed.counter += 1
        n.data_type = dt
        n.inputs["Name"].default_value = name
        return n.outputs["Attribute"]
    snamed.counter = 0
    sgi_v = snamed("vm_sgi"); sgj_v = snamed("vm_sgj")
    # v2.8: the Column Select filter reads ONE column index in both layouts -
    # the Slots grid column in 'Slots', the opening-grid strip in 'Random'
    gcol_v = snamed("vm_gcol")
    col_sw = b.N("GeometryNodeSwitch", (2700, -2200))
    col_sw.input_type = "FLOAT"
    b.L(is_slots, col_sw.inputs["Switch"])
    b.L(gcol_v, col_sw.inputs["False"])
    b.L(sgi_v, col_sw.inputs["True"])
    col_v = col_sw.outputs["Output"]
    sw_v = snamed("vm_w"); seu_v = snamed("vm_eu"); sev_v = snamed("vm_ev")
    sc_v = snamed("vm_c", "FLOAT_VECTOR"); su_v = snamed("vm_u", "FLOAT_VECTOR")
    sv_v = snamed("vm_v", "FLOAT_VECTOR"); sfz_v = snamed("vm_fz")
    salo_v = snamed("vm_alo"); sen_v = snamed("vm_en")
    sn_v = snamed("vm_normal", "FLOAT_VECTOR"); sfi_v = snamed("vm_fi")

    # column count: Per Width -> floor(w / Openings Per Width) (min 1), clamped
    # by the gap law (>= 1 column always - a lone opening has no neighbour)
    pw_l = b.N("ShaderNodeMath", (2900, -1050), operation="DIVIDE")
    b.L(gi.outputs["Openings Per Width"], pw_l.inputs[0])
    b.L(seu_v, pw_l.inputs[1])
    pw_max = b.N("ShaderNodeMath", (3050, -1050), operation="MAXIMUM")
    b.L(pw_l.outputs["Value"], pw_max.inputs[0])
    pw_max.inputs[1].default_value = 0.001
    ns_pw1 = b.N("ShaderNodeMath", (2900, -1200), operation="DIVIDE")
    b.L(sw_v, ns_pw1.inputs[0])
    b.L(pw_max.outputs["Value"], ns_pw1.inputs[1])
    ns_pw2 = b.N("ShaderNodeMath", (3050, -1200), operation="FLOOR")
    b.L(ns_pw1.outputs["Value"], ns_pw2.inputs[0])
    ns_pw = b.N("ShaderNodeMath", (3200, -1200), operation="MAXIMUM")
    b.L(ns_pw2.outputs["Value"], ns_pw.inputs[0])
    ns_pw.inputs[1].default_value = 1.0
    ns_exp = b.N("ShaderNodeMath", (2900, -1350), operation="ADD")
    b.L(gi.outputs["Slot Count"], ns_exp.inputs[0])
    ns_exp.inputs[1].default_value = 0.0
    ns_sw = b.N("GeometryNodeSwitch", (3350, -1250))
    ns_sw.input_type = "FLOAT"
    b.L(per_width_mode, ns_sw.inputs["Switch"])
    b.L(ns_pw.outputs["Value"], ns_sw.inputs["True"])
    b.L(ns_exp.outputs["Value"], ns_sw.inputs["False"])
    # gap law: pitch >= Opening Width + Min Gap X + 2*Slot Jitter (world) ->
    # ns <= width / (that / eu); min 1 column on narrow faces (no neighbour)
    gx1 = b.N("ShaderNodeMath", (2900, -1500), operation="ADD")
    b.L(gi.outputs["Opening Width"], gx1.inputs[0])
    b.L(gi.outputs["Min Gap X"], gx1.inputs[1])
    gx2 = b.N("ShaderNodeMath", (3050, -1500), operation="MULTIPLY_ADD")
    b.L(gi.outputs["Slot Jitter"], gx2.inputs[0])
    gx2.inputs[1].default_value = 2.0
    b.L(gx1.outputs["Value"], gx2.inputs[2])
    gx_l = b.N("ShaderNodeMath", (3200, -1500), operation="DIVIDE")
    b.L(gx2.outputs["Value"], gx_l.inputs[0])
    b.L(seu_v, gx_l.inputs[1])
    gx_max = b.N("ShaderNodeMath", (3350, -1500), operation="MAXIMUM")
    b.L(gx_l.outputs["Value"], gx_max.inputs[0])
    gx_max.inputs[1].default_value = 0.001
    ns_cap1 = b.N("ShaderNodeMath", (2900, -1650), operation="DIVIDE")
    b.L(sw_v, ns_cap1.inputs[0])
    b.L(gx_max.outputs["Value"], ns_cap1.inputs[1])
    ns_cap2 = b.N("ShaderNodeMath", (3050, -1650), operation="FLOOR")
    b.L(ns_cap1.outputs["Value"], ns_cap2.inputs[0])
    ns_cap = b.N("ShaderNodeMath", (3200, -1650), operation="MAXIMUM")
    b.L(ns_cap2.outputs["Value"], ns_cap.inputs[0])
    ns_cap.inputs[1].default_value = 1.0
    ns_m1 = b.N("ShaderNodeMath", (3500, -1350), operation="MINIMUM")
    b.L(ns_sw.outputs["Output"], ns_m1.inputs[0])
    b.L(ns_cap.outputs["Value"], ns_m1.inputs[1])
    ns_v = b.N("ShaderNodeMath", (3650, -1350), operation="MINIMUM")
    b.L(ns_m1.outputs["Value"], ns_v.inputs[0])
    ns_v.inputs[1].default_value = 64.0
    sp_sl = b.N("ShaderNodeMath", (3800, -1350), operation="DIVIDE")
    b.L(sw_v, sp_sl.inputs[0])
    b.L(ns_v.outputs["Value"], sp_sl.inputs[1])
    sp_max = b.N("ShaderNodeMath", (3950, -1350), operation="MAXIMUM")
    b.L(sp_sl.outputs["Value"], sp_max.inputs[0])
    sp_max.inputs[1].default_value = 0.0001

    # row pitch: max(Row Spacing, Opening Height + Min Gap Z, Min Gap Z) world m
    rz1 = b.N("ShaderNodeMath", (2900, -1800), operation="ADD")
    b.L(gi.outputs["Opening Height"], rz1.inputs[0])
    b.L(gi.outputs["Min Gap Z"], rz1.inputs[1])
    rz2 = b.N("ShaderNodeMath", (3050, -1800), operation="MAXIMUM")
    b.L(gi.outputs["Row Spacing"], rz2.inputs[0])
    b.L(rz1.outputs["Value"], rz2.inputs[1])
    rz3 = b.N("ShaderNodeMath", (3200, -1800), operation="MAXIMUM")
    b.L(rz2.outputs["Value"], rz3.inputs[0])
    b.L(gi.outputs["Min Gap Z"], rz3.inputs[1])
    rp_l = b.N("ShaderNodeMath", (3350, -1800), operation="DIVIDE")
    b.L(rz3.outputs["Value"], rp_l.inputs[0])
    b.L(sev_v, rp_l.inputs[1])
    rp_max = b.N("ShaderNodeMath", (3500, -1800), operation="MAXIMUM")
    b.L(rp_l.outputs["Value"], rp_max.inputs[0])
    rp_max.inputs[1].default_value = 0.0001

    # sill target z (LOCAL): Common Z = host zmin + sill; Face Base = face base + sill
    targ_face = b.N("ShaderNodeMath", (4000, -1550), operation="ADD")
    b.L(sfz_v, targ_face.inputs[0])
    b.L(sill_l.outputs["Value"], targ_face.inputs[1])
    targ_com = b.N("ShaderNodeMath", (4000, -1700), operation="ADD")
    b.L(bb_sep.outputs["Z"], targ_com.inputs[0])
    b.L(sill_l.outputs["Value"], targ_com.inputs[1])
    # v2.10: Common Z only for faces whose base is at/below the shared line;
    # a raised face (upper storey) measures its sill from its own base
    low_face = b.N("FunctionNodeCompare", (3850, -1750), data_type="FLOAT", operation="LESS_EQUAL")
    b.L(sfz_v, low_face.inputs["A"])
    b.L(sill_eps.outputs["Value"], low_face.inputs["B"])
    use_common = b.N("FunctionNodeBooleanMath", (4000, -1820), operation="AND")
    b.L(common_z, use_common.inputs[0])
    b.L(low_face.outputs["Result"], use_common.inputs[1])
    targ_sw = b.N("GeometryNodeSwitch", (4150, -1620))
    targ_sw.input_type = "FLOAT"
    b.L(use_common.outputs["Boolean"], targ_sw.inputs["Switch"])
    b.L(targ_com.outputs["Value"], targ_sw.inputs["True"])
    b.L(targ_face.outputs["Value"], targ_sw.inputs["False"])
    # row base z for row j (shared by the fit gate and the position below)
    z_row = b.N("ShaderNodeMath", (4300, -1620), operation="MULTIPLY_ADD")
    b.L(sgj_v, z_row.inputs[0])
    b.L(rp_max.outputs["Value"], z_row.inputs[1])
    b.L(targ_sw.outputs["Output"], z_row.inputs[2])
    # ROW FIT: a row is kept only if the opening FITS on its face
    # (row base + Opening Height <= face top) - no row ever floats above a wall
    sh_v = snamed("vm_h")
    oh_l = b.N("ShaderNodeMath", (4300, -1800), operation="DIVIDE")
    b.L(gi.outputs["Opening Height"], oh_l.inputs[0])
    b.L(sev_v, oh_l.inputs[1])
    row_top1 = b.N("ShaderNodeMath", (4450, -1800), operation="ADD")
    b.L(z_row.outputs["Value"], row_top1.inputs[0])
    b.L(oh_l.outputs["Value"], row_top1.inputs[1])
    face_top1 = b.N("ShaderNodeMath", (4600, -1800), operation="ADD")
    b.L(sfz_v, face_top1.inputs[0])
    b.L(sh_v, face_top1.inputs[1])
    row_fit = b.N("FunctionNodeCompare", (4750, -1800), data_type="FLOAT", operation="LESS_EQUAL")
    b.L(row_top1.outputs["Value"], row_fit.inputs["A"])
    b.L(face_top1.outputs["Value"], row_fit.inputs["B"])

    # ---- v2.6 Opening Fit 'Scale To Face' (CONTRACT CHANGE, default ON) ----
    # v2.5 'Drop' rejected the whole row when the nominal opening did not fit -
    # on the user's ~2 m-tall custom massing that killed EVERY wall (2.1-2.2 m
    # default/demo Opening Height). 'Scale To Face' keeps the row and shrinks
    # the INSTANCE to the available face height/width (fit factor below); rows
    # that would shrink past 'Min Fit Scale' are still dropped (not sensible).
    avail_h = b.N("ShaderNodeMath", (4450, -2050), operation="SUBTRACT")
    b.L(face_top1.outputs["Value"], avail_h.inputs[0])
    b.L(z_row.outputs["Value"], avail_h.inputs[1])
    kh1 = b.N("ShaderNodeMath", (4600, -2050), operation="DIVIDE")
    b.L(avail_h.outputs["Value"], kh1.inputs[0])
    b.L(oh_l.outputs["Value"], kh1.inputs[1])
    kh2 = b.N("ShaderNodeMath", (4750, -2050), operation="MINIMUM")
    b.L(kh1.outputs["Value"], kh2.inputs[0])
    kh2.inputs[1].default_value = 1.0
    kh = b.N("ShaderNodeMath", (4900, -2050), operation="MAXIMUM")
    b.L(kh2.outputs["Value"], kh.inputs[0])
    kh.inputs[1].default_value = 0.0
    # width: scaled neighbours must keep >= Min Gap X, so k <= (pitch - gap)/OpeningWidth
    sp_world = b.N("ShaderNodeMath", (4450, -2200), operation="MULTIPLY")
    b.L(sp_max.outputs["Value"], sp_world.inputs[0])
    b.L(seu_v, sp_world.inputs[1])
    kw1 = b.N("ShaderNodeMath", (4600, -2200), operation="SUBTRACT")
    b.L(sp_world.outputs["Value"], kw1.inputs[0])
    b.L(gi.outputs["Min Gap X"], kw1.inputs[1])
    kw2 = b.N("ShaderNodeMath", (4750, -2200), operation="DIVIDE")
    b.L(kw1.outputs["Value"], kw2.inputs[0])
    b.L(gi.outputs["Opening Width"], kw2.inputs[1])
    kw3 = b.N("ShaderNodeMath", (4900, -2200), operation="MINIMUM")
    b.L(kw2.outputs["Value"], kw3.inputs[0])
    kw3.inputs[1].default_value = 1.0
    kw = b.N("ShaderNodeMath", (5050, -2200), operation="MAXIMUM")
    b.L(kw3.outputs["Value"], kw.inputs[0])
    kw.inputs[1].default_value = 0.0
    fitk_raw = b.N("ShaderNodeMath", (5200, -2100), operation="MINIMUM")
    b.L(kh.outputs["Value"], fitk_raw.inputs[0])
    b.L(kw.outputs["Value"], fitk_raw.inputs[1])
    fit_ok = b.N("FunctionNodeCompare", (5350, -2100), data_type="FLOAT", operation="GREATER_EQUAL")
    b.L(fitk_raw.outputs["Value"], fit_ok.inputs["A"])
    b.L(gi.outputs["Min Fit Scale"], fit_ok.inputs["B"])
    row_in = b.N("FunctionNodeCompare", (5350, -2250), data_type="FLOAT", operation="LESS_EQUAL")
    b.L(z_row.outputs["Value"], row_in.inputs["A"])
    b.L(face_top1.outputs["Value"], row_in.inputs["B"])
    scale_row_ok = b.N("FunctionNodeBooleanMath", (5500, -2150), operation="AND")
    b.L(row_in.outputs["Result"], scale_row_ok.inputs[0])
    b.L(fit_ok.outputs["Result"], scale_row_ok.inputs[1])
    keep_row = b.N("GeometryNodeSwitch", (5650, -2050))
    keep_row.input_type = "BOOLEAN"
    b.L(fit_scale_mode, keep_row.inputs["Switch"])
    b.L(row_fit.outputs["Result"], keep_row.inputs["False"])
    b.L(scale_row_ok.outputs["Boolean"], keep_row.inputs["True"])

    # keep: column in range, row in range + fits on the face, Column Select filter
    keep_c1 = b.N("FunctionNodeCompare", (2900, -1950), data_type="FLOAT", operation="LESS_THAN")
    b.L(sgi_v, keep_c1.inputs["A"])
    b.L(ns_v.outputs["Value"], keep_c1.inputs["B"])
    keep_r1 = b.N("FunctionNodeCompare", (2900, -2080), data_type="FLOAT", operation="LESS_THAN")
    b.L(sgj_v, keep_r1.inputs["A"])
    b.L(gi.outputs["Slot Rows"], keep_r1.inputs["B"])
    sgi_zero = b.N("FunctionNodeCompare", (2900, -2210), data_type="FLOAT", operation="EQUAL")
    b.L(col_v, sgi_zero.inputs["A"])
    sgi_zero.inputs[1].default_value = 0.0
    sgi_pos = b.N("FunctionNodeCompare", (2900, -2340), data_type="FLOAT", operation="GREATER_THAN")
    b.L(col_v, sgi_pos.inputs["A"])
    sgi_pos.inputs[1].default_value = 0.0
    cs_sw, cs_bools = b.menu_switch(["All", "First Only", "Skip First"], "BOOLEAN",
                                    gi.outputs["Column Select"],
                                    {"First Only": sgi_zero.outputs["Result"],
                                     "Skip First": sgi_pos.outputs["Result"]}, loc=(3200, -2250))
    b.ng.nodes[-1].inputs["All"].default_value = True
    keep_k1 = b.N("FunctionNodeBooleanMath", (3500, -2000), operation="AND")
    b.L(keep_c1.outputs["Result"], keep_k1.inputs[0])
    b.L(keep_r1.outputs["Result"], keep_k1.inputs[1])
    keep_k1b = b.N("FunctionNodeBooleanMath", (3650, -1950), operation="AND")
    b.L(keep_k1.outputs["Boolean"], keep_k1b.inputs[0])
    b.L(keep_row.outputs["Output"], keep_k1b.inputs[1])
    keep_k2 = b.N("FunctionNodeBooleanMath", (3800, -2000), operation="AND")
    b.L(keep_k1b.outputs["Boolean"], keep_k2.inputs[0])
    b.L(cs_sw, keep_k2.inputs[1])

    # ---- v2.6 MANUAL mask (vertex-group painted placement) ----
    # Sample the painted weight at the slot's final wall position (the same
    # field the Set Position below uses, minus the tiny jitter). Painted area
    # can only REMOVE candidates - gap/sill/fit rules hold with precedence.
    mp_a = b.N("ShaderNodeMath", (4000, -2500), operation="ADD")
    b.L(sgi_v, mp_a.inputs[0])
    mp_a.inputs[1].default_value = 0.5
    mp_pos = b.N("ShaderNodeMath", (4150, -2500), operation="MULTIPLY_ADD")
    b.L(mp_a.outputs["Value"], mp_pos.inputs[0])
    b.L(sp_max.outputs["Value"], mp_pos.inputs[1])
    b.L(salo_v, mp_pos.inputs[2])
    mp_cz = b.N("ShaderNodeSeparateXYZ", (4000, -2650))
    b.L(sc_v, mp_cz.inputs["Vector"])
    mp_dz = b.N("ShaderNodeMath", (4150, -2650), operation="SUBTRACT")
    b.L(z_row.outputs["Value"], mp_dz.inputs[0])
    b.L(mp_cz.outputs["Z"], mp_dz.inputs[1])
    mp_u = b.N("ShaderNodeVectorMath", (4300, -2500), operation="SCALE")
    b.L(su_v, mp_u.inputs[0])
    b.L(mp_pos.outputs["Value"], mp_u.inputs["Scale"])
    mp_v = b.N("ShaderNodeCombineXYZ", (4300, -2650))
    # v2.8.2: probe offset along ABSOLUTE world-z (the frame's v can point -Z
    # after the canonical-u flip - see the sv_pos note)
    b.L(mp_dz.outputs["Value"], mp_v.inputs["Z"])
    mp_p1 = b.N("ShaderNodeVectorMath", (4450, -2550), operation="ADD")
    b.L(sc_v, mp_p1.inputs[0])
    b.L(mp_u.outputs["Vector"], mp_p1.inputs[1])
    mp_p2 = b.N("ShaderNodeVectorMath", (4600, -2550), operation="ADD")
    b.L(mp_p1.outputs["Vector"], mp_p2.inputs[0])
    b.L(mp_v.outputs["Vector"], mp_p2.inputs[1])
    mp_emb_l = b.N("ShaderNodeMath", (4600, -2800), operation="DIVIDE")
    b.L(emb_net.outputs["Value"], mp_emb_l.inputs[0])
    b.L(sen_v, mp_emb_l.inputs[1])
    mp_emb = b.N("ShaderNodeVectorMath", (4750, -2550), operation="SCALE")
    b.L(sn_v, mp_emb.inputs[0])
    b.L(mp_emb_l.outputs["Value"], mp_emb.inputs["Scale"])
    mp_p3 = b.N("ShaderNodeVectorMath", (4900, -2550), operation="ADD")
    b.L(mp_p2.outputs["Vector"], mp_p3.inputs[0])
    b.L(mp_emb.outputs["Vector"], mp_p3.inputs[1])
    mask_attr = b.N("GeometryNodeInputNamedAttribute", (4450, -2800))
    mask_attr.data_type = "FLOAT"
    b.L(gi.outputs["Manual Mask Group"], mask_attr.inputs["Name"])
    # v2.6: the painted weight is sampled at the slot position AND at +/- a
    # quarter-opening along the wall (3-point min): vertex-group interpolation
    # bleeds across shared corner verts into UNPAINTED neighbours - trimming a
    # quarter-opening margin keeps openings INSIDE the painted area (the exact
    # bleed case was measured on UserShape2: one door slipped onto the adjacent
    # wall at interpolated weight 0.505). Documented limit: mask resolution is
    # vertex-group interpolation - sub-wall paint areas need wall subdivision.
    mdel = b.N("ShaderNodeMath", (4300, -2800), operation="DIVIDE")
    b.L(gi.outputs["Opening Width"], mdel.inputs[0])
    b.L(seu_v, mdel.inputs[1])
    mdel2 = b.N("ShaderNodeMath", (4300, -2950), operation="MULTIPLY")
    b.L(mdel.outputs["Value"], mdel2.inputs[0])
    mdel2.inputs[1].default_value = 0.25
    mdu1 = b.N("ShaderNodeVectorMath", (4450, -2950), operation="SCALE")
    b.L(su_v, mdu1.inputs[0])
    b.L(mdel2.outputs["Value"], mdu1.inputs["Scale"])
    mpp_a = b.N("ShaderNodeVectorMath", (4600, -2750), operation="ADD")
    b.L(mp_p3.outputs["Vector"], mpp_a.inputs[0])
    b.L(mdu1.outputs["Vector"], mpp_a.inputs[1])
    mpp_b = b.N("ShaderNodeVectorMath", (4600, -2950), operation="SUBTRACT")
    b.L(mp_p3.outputs["Vector"], mpp_b.inputs[0])
    b.L(mdu1.outputs["Vector"], mpp_b.inputs[1])
    mask_samp = b.N("GeometryNodeSampleNearestSurface", (4750, -2800))
    b.L(mesh_only, mask_samp.inputs["Mesh"])
    b.L(mask_attr.outputs["Attribute"], mask_samp.inputs["Value"])
    b.L(mp_p3.outputs["Vector"], mask_samp.inputs["Sample Position"])
    mask_samp_a = b.N("GeometryNodeSampleNearestSurface", (4750, -3050))
    b.L(mesh_only, mask_samp_a.inputs["Mesh"])
    b.L(mask_attr.outputs["Attribute"], mask_samp_a.inputs["Value"])
    b.L(mpp_a.outputs["Vector"], mask_samp_a.inputs["Sample Position"])
    mask_samp_b = b.N("GeometryNodeSampleNearestSurface", (4750, -3300))
    b.L(mesh_only, mask_samp_b.inputs["Mesh"])
    b.L(mask_attr.outputs["Attribute"], mask_samp_b.inputs["Value"])
    b.L(mpp_b.outputs["Vector"], mask_samp_b.inputs["Sample Position"])
    mask_ok = b.N("FunctionNodeCompare", (5050, -2800), data_type="FLOAT", operation="GREATER_EQUAL")
    b.L(mask_samp.outputs["Value"], mask_ok.inputs["A"])
    b.L(gi.outputs["Manual Threshold"], mask_ok.inputs["B"])
    mask_ok_a = b.N("FunctionNodeCompare", (5050, -3050), data_type="FLOAT", operation="GREATER_EQUAL")
    b.L(mask_samp_a.outputs["Value"], mask_ok_a.inputs["A"])
    b.L(gi.outputs["Manual Threshold"], mask_ok_a.inputs["B"])
    mask_ok_b = b.N("FunctionNodeCompare", (5050, -3300), data_type="FLOAT", operation="GREATER_EQUAL")
    b.L(mask_samp_b.outputs["Value"], mask_ok_b.inputs["A"])
    b.L(gi.outputs["Manual Threshold"], mask_ok_b.inputs["B"])
    mask_ok_ab = b.N("FunctionNodeBooleanMath", (5250, -2950), operation="AND")
    b.L(mask_ok.outputs["Result"], mask_ok_ab.inputs[0])
    b.L(mask_ok_a.outputs["Result"], mask_ok_ab.inputs[1])
    mask_ok3 = b.N("FunctionNodeBooleanMath", (5400, -3050), operation="AND")
    b.L(mask_ok_ab.outputs["Boolean"], mask_ok3.inputs[0])
    b.L(mask_ok_b.outputs["Result"], mask_ok3.inputs[1])
    mask_not = b.N("FunctionNodeBooleanMath", (5050, -2950), operation="NOT")
    b.L(gi.outputs["Manual Mask"], mask_not.inputs[0])
    manual_gate = b.N("FunctionNodeBooleanMath", (5250, -2850), operation="OR")
    b.L(mask_not.outputs["Boolean"], manual_gate.inputs[0])
    b.L(mask_ok3.outputs["Boolean"], manual_gate.inputs[1])
    keep_k3 = b.N("FunctionNodeBooleanMath", (5450, -2500), operation="AND")
    b.L(keep_k2.outputs["Boolean"], keep_k3.inputs[0])
    b.L(manual_gate.outputs["Boolean"], keep_k3.inputs[1])
    # v2.9: cross-layer clearance BEFORE the Exact N rank (input 1 is linked
    # once the earlier-layer anchor cloud exists - see slot_occ below). Ranking
    # first and culling later let 'Exactly 1 window' pick a slot beside a door
    # and then lose it: the layer ended with 0.
    keep_k4 = b.N("FunctionNodeBooleanMath", (5550, -2500), operation="AND")
    b.L(keep_k3.outputs["Boolean"], keep_k4.inputs[0])

    # ---- v2.6 Count Mode 'Exact N': EXACTLY 'Exact Count' openings per LAYER ----
    # Candidate order is deterministic (face order, then grid column/row order);
    # rank = running count of kept candidates (Accumulate Field, POINT domain).
    keep_ff = b.N("ShaderNodeMath", (5650, -2500), operation="ADD")
    b.L(keep_k4.outputs["Boolean"], keep_ff.inputs[0])
    keep_ff.inputs[1].default_value = 0.0
    acc_s = b.N("GeometryNodeAccumulateField", (5850, -2500), domain="POINT")
    b.L(keep_ff.outputs["Value"], acc_s.inputs["Value"])
    n_f = b.N("ShaderNodeMath", (5850, -2700), operation="ADD")
    b.L(gi.outputs["Exact Count"], n_f.inputs[0])
    n_f.inputs[1].default_value = 0.0
    ex_first = b.N("FunctionNodeCompare", (6050, -2450), data_type="FLOAT", operation="LESS_THAN")
    b.L(acc_s.outputs["Leading"], ex_first.inputs["A"])
    b.L(n_f.outputs["Value"], ex_first.inputs["B"])
    tot_g = b.N("ShaderNodeMath", (6050, -2650), operation="MAXIMUM")
    b.L(acc_s.outputs["Total"], tot_g.inputs[0])
    tot_g.inputs[1].default_value = 1.0
    sp_a = b.N("ShaderNodeMath", (6200, -2650), operation="MULTIPLY")
    b.L(acc_s.outputs["Leading"], sp_a.inputs[0])
    b.L(n_f.outputs["Value"], sp_a.inputs[1])
    sp_b = b.N("ShaderNodeMath", (6350, -2650), operation="DIVIDE")
    b.L(sp_a.outputs["Value"], sp_b.inputs[0])
    b.L(tot_g.outputs["Value"], sp_b.inputs[1])
    sp_f1 = b.N("ShaderNodeMath", (6500, -2650), operation="FLOOR")
    b.L(sp_b.outputs["Value"], sp_f1.inputs[0])
    sp_r = b.N("ShaderNodeMath", (6200, -2800), operation="SUBTRACT")
    b.L(acc_s.outputs["Leading"], sp_r.inputs[0])
    sp_r.inputs[1].default_value = 1.0
    sp_c = b.N("ShaderNodeMath", (6350, -2800), operation="MULTIPLY")
    b.L(sp_r.outputs["Value"], sp_c.inputs[0])
    b.L(n_f.outputs["Value"], sp_c.inputs[1])
    sp_d = b.N("ShaderNodeMath", (6500, -2800), operation="DIVIDE")
    b.L(sp_c.outputs["Value"], sp_d.inputs[0])
    b.L(tot_g.outputs["Value"], sp_d.inputs[1])
    sp_f2 = b.N("ShaderNodeMath", (6650, -2800), operation="FLOOR")
    b.L(sp_d.outputs["Value"], sp_f2.inputs[0])
    ex_spread = b.N("FunctionNodeCompare", (6800, -2700), data_type="FLOAT", operation="GREATER_THAN")
    b.L(sp_f1.outputs["Value"], ex_spread.inputs["A"])
    b.L(sp_f2.outputs["Value"], ex_spread.inputs["B"])
    ex_pick = b.N("GeometryNodeSwitch", (7000, -2550))
    ex_pick.input_type = "BOOLEAN"
    b.L(exact_spread, ex_pick.inputs["Switch"])
    b.L(ex_first.outputs["Result"], ex_pick.inputs["False"])
    b.L(ex_spread.outputs["Result"], ex_pick.inputs["True"])
    ex_not = b.N("FunctionNodeBooleanMath", (7000, -2750), operation="NOT")
    b.L(exact_mode, ex_not.inputs[0])
    exact_gate = b.N("FunctionNodeBooleanMath", (7200, -2650), operation="OR")
    b.L(ex_not.outputs["Boolean"], exact_gate.inputs[0])
    b.L(ex_pick.outputs["Output"], exact_gate.inputs[1])
    keep_final = b.N("FunctionNodeBooleanMath", (7400, -2500), operation="AND")
    b.L(keep_k4.outputs["Boolean"], keep_final.inputs[0])
    b.L(exact_gate.outputs["Boolean"], keep_final.inputs[1])

    not_keep_s = b.N("FunctionNodeBooleanMath", (3950, -2000), operation="NOT")
    b.L(keep_final.outputs["Boolean"], not_keep_s.inputs[0])
    del_s = b.N("GeometryNodeDeleteGeometry", (3950, -750), domain="POINT")
    b.L(real_s.outputs["Geometry"], del_s.inputs["Geometry"])
    b.L(not_keep_s.outputs["Boolean"], del_s.inputs["Selection"])

    # position: c + u*(alo + (col+0.5)*pitch) + v*(sill_line + row*row_pitch - c.z)
    # NOTE: Math-node inputs default to 0.5 - every constant here is set EXPLICITLY
    a_half = b.N("ShaderNodeMath", (4000, -1350), operation="ADD")
    b.L(sgi_v, a_half.inputs[0])
    a_half.inputs[1].default_value = 0.5
    a_pos = b.N("ShaderNodeMath", (4300, -1350), operation="MULTIPLY_ADD")
    b.L(a_half.outputs["Value"], a_pos.inputs[0])
    b.L(sp_max.outputs["Value"], a_pos.inputs[1])
    b.L(salo_v, a_pos.inputs[2])
    csep_s = b.N("ShaderNodeSeparateXYZ", (4000, -1850))
    b.L(sc_v, csep_s.inputs["Vector"])
    b_abs_s = b.N("ShaderNodeMath", (4450, -1620), operation="SUBTRACT")
    b.L(z_row.outputs["Value"], b_abs_s.inputs[0])
    b.L(csep_s.outputs["Z"], b_abs_s.inputs[1])
    su_pos = b.N("ShaderNodeVectorMath", (4600, -1350), operation="SCALE")
    b.L(su_v, su_pos.inputs[0]); b.L(a_pos.outputs["Value"], su_pos.inputs["Scale"])
    # v2.8.2: the row offset is ABSOLUTE world-z, never the face frame's v axis -
    # the v2.8 canonical-u flip also flips v = cross(n, u) to -Z on some walls,
    # and a v-scaled z offset then MIRRORED openings about the face centre
    # (windows landed at 2*c.z - sill instead of sill).
    sv_pos = b.N("ShaderNodeCombineXYZ", (4600, -1620))
    b.L(b_abs_s.outputs["Value"], sv_pos.inputs["Z"])
    p1_s = b.N("ShaderNodeVectorMath", (4800, -1450), operation="ADD")
    b.L(sc_v, p1_s.inputs[0]); b.L(su_pos.outputs["Vector"], p1_s.inputs[1])
    p2_s = b.N("ShaderNodeVectorMath", (4950, -1450), operation="ADD")
    b.L(p1_s.outputs["Vector"], p2_s.inputs[0]); b.L(sv_pos.outputs["Vector"], p2_s.inputs[1])
    # Slot Jitter (world meters -> local via vm_eu): applied along the face's
    # horizontal u axis ONLY so the shared sill line stays EXACT (aligned window
    # rows) while the columns read organically
    rv_sj = b.N("FunctionNodeRandomValue", (4600, -1950), data_type="FLOAT")
    rv_sj.inputs["Min"].default_value = -1.0
    rv_sj.inputs["Max"].default_value = 1.0
    b.L(idx.outputs["Index"], rv_sj.inputs["ID"])
    b.L(seed_node(b, gi.outputs["Seed"], SEED_OFF["slotjit"]), rv_sj.inputs["Seed"])
    sjit_l = b.N("ShaderNodeMath", (4750, -1950), operation="DIVIDE")
    b.L(gi.outputs["Slot Jitter"], sjit_l.inputs[0])
    b.L(seu_v, sjit_l.inputs[1])
    sjit_m = b.N("ShaderNodeMath", (4900, -1950), operation="MULTIPLY")
    b.L(rv_sj.outputs["Value"], sjit_m.inputs[0])
    b.L(sjit_l.outputs["Value"], sjit_m.inputs[1])
    sjit_v = b.N("ShaderNodeVectorMath", (5050, -1950), operation="SCALE")
    b.L(su_v, sjit_v.inputs[0])
    b.L(sjit_m.outputs["Value"], sjit_v.inputs["Scale"])
    p3_s = b.N("ShaderNodeVectorMath", (5150, -1450), operation="ADD")
    b.L(p2_s.outputs["Vector"], p3_s.inputs[0]); b.L(sjit_v.outputs["Vector"], p3_s.inputs[1])
    # wall-contact contract: back face on the backing plane (Backing - Embed)
    emb_ls = b.N("ShaderNodeMath", (4600, -2350), operation="DIVIDE")
    b.L(emb_net.outputs["Value"], emb_ls.inputs[0])
    b.L(sen_v, emb_ls.inputs[1])
    noff_s = b.N("ShaderNodeVectorMath", (4800, -2350), operation="SCALE")
    b.L(sn_v, noff_s.inputs[0]); b.L(emb_ls.outputs["Value"], noff_s.inputs["Scale"])
    p4_s = b.N("ShaderNodeVectorMath", (5350, -1450), operation="ADD")
    b.L(p3_s.outputs["Vector"], p4_s.inputs[0]); b.L(noff_s.outputs["Vector"], p4_s.inputs[1])
    setpos_s = b.N("GeometryNodeSetPosition", (5550, -750))
    b.L(del_s.outputs["Geometry"], setpos_s.inputs["Geometry"])
    b.L(p4_s.outputs["Vector"], setpos_s.inputs["Position"])
    # No-Repeat variant pick: adjacent slots cycle (col + 17*row + 7*face + Seed)
    # so horizontal neighbours differ by 1 and vertical neighbours by 17 - two
    # touching slots can NEVER pick the same variant for any collection >= 2
    # (only a collection of exactly 17 variants could alias vertically).
    pick1_s = b.N("ShaderNodeMath", (5150, -2100), operation="MULTIPLY_ADD")
    b.L(sfi_v, pick1_s.inputs[0])
    pick1_s.inputs[1].default_value = 7.0
    b.L(sgi_v, pick1_s.inputs[2])
    pick1b_s = b.N("ShaderNodeMath", (5150, -2250), operation="MULTIPLY_ADD")
    b.L(sgj_v, pick1b_s.inputs[0])
    pick1b_s.inputs[1].default_value = 17.0
    b.L(pick1_s.outputs["Value"], pick1b_s.inputs[2])
    pick2_s = b.N("ShaderNodeMath", (5300, -2100), operation="ADD")
    b.L(pick1b_s.outputs["Value"], pick2_s.inputs[0])
    b.L(gi.outputs["Seed"], pick2_s.inputs[1])
    pick3_s = b.N("ShaderNodeMath", (5450, -2100), operation="FLOORED_MODULO")
    b.L(pick2_s.outputs["Value"], pick3_s.inputs[0])
    pick3_s.inputs[1].default_value = 251.0
    pick_store = b.N("GeometryNodeStoreNamedAttribute", (5750, -750), data_type="FLOAT", domain="POINT")
    b.L(setpos_s.outputs["Geometry"], pick_store.inputs["Geometry"])
    pick_store.inputs["Name"].default_value = "vm_pick"
    b.L(pick3_s.outputs["Value"], pick_store.inputs["Value"])
    # v2.6: per-slot auto-fit factor (Scale To Face) -> applied to the instance
    # scale below; 1.0 in Drop mode / other branches (bit-identical v2.5 scale)
    fitk_sw = b.N("GeometryNodeSwitch", (5750, -950))
    fitk_sw.input_type = "FLOAT"
    b.L(fit_scale_mode, fitk_sw.inputs["Switch"])
    fitk_sw.inputs["False"].default_value = 1.0
    b.L(fitk_raw.outputs["Value"], fitk_sw.inputs["True"])
    fitk_store = b.N("GeometryNodeStoreNamedAttribute", (5950, -750), data_type="FLOAT", domain="POINT")
    b.L(pick_store.outputs["Geometry"], fitk_store.inputs["Geometry"])
    fitk_store.inputs["Name"].default_value = "vm_fitk"
    b.L(fitk_sw.outputs["Output"], fitk_store.inputs["Value"])
    # v2.8: grid column/row on the slot points too (shared gap-law greedy)
    sg_a = b.N("GeometryNodeStoreNamedAttribute", (6150, -750), data_type="FLOAT", domain="POINT")
    b.L(fitk_store.outputs["Geometry"], sg_a.inputs["Geometry"])
    sg_a.inputs["Name"].default_value = "vm_gcol"
    b.L(sgi_v, sg_a.inputs["Value"])
    sg_b = b.N("GeometryNodeStoreNamedAttribute", (6350, -750), data_type="FLOAT", domain="POINT")
    b.L(sg_a.outputs["Geometry"], sg_b.inputs["Geometry"])
    sg_b.inputs["Name"].default_value = "vm_grow"
    # v2.10: the greedy row key is the row's HEIGHT (world z / 0.5 m, mod 17 to
    # fit the safe group-id budget), not its index on the face. Two coplanar
    # faces stacked on one wall plane (storeys of one mesh) both have a 'row 0';
    # keyed by index the upper storey lost every opening as a 'duplicate'.
    # Coincident duplicate faces still share a key (same height).
    grz_w = b.N("ShaderNodeMath", (6150, -950), operation="MULTIPLY")
    b.L(z_row.outputs["Value"], grz_w.inputs[0])
    b.L(sz_g, grz_w.inputs[1])
    grz_q = b.N("ShaderNodeMath", (6300, -950), operation="MULTIPLY")
    b.L(grz_w.outputs["Value"], grz_q.inputs[0])
    grz_q.inputs[1].default_value = 2.0
    grz_r = b.N("ShaderNodeMath", (6450, -950), operation="ROUND")
    b.L(grz_q.outputs["Value"], grz_r.inputs[0])
    grz_m = b.N("ShaderNodeMath", (6600, -950), operation="FLOORED_MODULO")
    b.L(grz_r.outputs["Value"], grz_m.inputs[0])
    grz_m.inputs[1].default_value = 17.0
    b.L(grz_m.outputs["Value"], sg_b.inputs["Value"])
    slot_geo = sg_b.outputs["Geometry"]

    # Fit points: Slots layout -> slot_geo, Random layout -> density sampling
    fit_geo_sw = b.N("GeometryNodeSwitch", (1800, -150))
    fit_geo_sw.input_type = "GEOMETRY"
    b.L(is_slots, fit_geo_sw.inputs["Switch"])
    b.L(rg3.outputs["Geometry"], fit_geo_sw.inputs["False"])
    b.L(slot_geo, fit_geo_sw.inputs["True"])
    fit_geo = fit_geo_sw.outputs["Output"]

    # ---------------- CLADDING branch (exact per-face courses) ----------------
    # face-domain frame + extents + course counts are materialized by the shared
    # store chain above (evaluation-context contract)
    m2p_f = b.N("GeometryNodeMeshToPoints", (900, -2100))
    m2p_f.mode = "FACES"
    b.L(frame_chain, m2p_f.inputs["Mesh"])
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
    # v2.4.1: the width squeeze runs on POINTS (Normal-derived fields are garbage
    # there) -> recompute the world->local slot pitch from the STORED vm_eu
    eu_pts = named("vm_eu")
    pitch_p = b.N("ShaderNodeMath", (1250, -2810), operation="DIVIDE")
    b.L(slot_pitch.outputs["Value"], pitch_p.inputs[0])
    b.L(eu_pts, pitch_p.inputs[1])
    max1_p = b.N("ShaderNodeMath", (1400, -2810), operation="MAXIMUM")
    b.L(pitch_p.outputs["Value"], max1_p.inputs[0])
    max1_p.inputs[1].default_value = 0.001

    keep_i = b.N("FunctionNodeCompare", (2200, -2500), data_type="FLOAT", operation="LESS_THAN")
    b.L(gi_v, keep_i.inputs["A"]); b.L(ns_v, keep_i.inputs["B"])
    keep_j = b.N("FunctionNodeCompare", (2200, -2650), data_type="FLOAT", operation="LESS_THAN")
    b.L(gj_v, keep_j.inputs["A"]); b.L(nr_v, keep_j.inputs["B"])
    keep_ij = b.N("FunctionNodeBooleanMath", (2400, -2550), operation="AND")
    b.L(keep_i.outputs["Result"], keep_ij.inputs[0])
    b.L(keep_j.outputs["Result"], keep_ij.inputs[1])

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
    # v2.8: jitter stays IN THE FACE PLANE (u/v components only) - the wall
    # contact contract (Embed/Backing Offset) owns the depth, and a normal
    # component would push the slot anchor off the face plane and outside the
    # containment test. Jitter is WORLD meters -> local via vm_eu / vm_ev.
    rv_jit = b.N("FunctionNodeRandomValue", (3100, -3250), data_type="FLOAT_VECTOR")
    rv_jit.inputs["Min"].default_value = (-1.0, -1.0, -1.0)
    rv_jit.inputs["Max"].default_value = (1.0, 1.0, 1.0)
    b.L(idx.outputs["Index"], rv_jit.inputs["ID"])
    b.L(seed(SEED_OFF["jitter"]), rv_jit.inputs["Seed"])
    jit_u1 = b.N("ShaderNodeMath", (3000, -3450), operation="DIVIDE")
    b.L(gi.outputs["Jitter"], jit_u1.inputs[0])
    b.L(eu_pts, jit_u1.inputs[1])
    ev_pts = named("vm_ev")
    jit_v1 = b.N("ShaderNodeMath", (3000, -3520), operation="DIVIDE")
    b.L(gi.outputs["Jitter"], jit_v1.inputs[0])
    b.L(ev_pts, jit_v1.inputs[1])
    jit_sep = b.N("ShaderNodeSeparateXYZ", (3150, -3320))
    b.L(rv_jit.outputs["Value"], jit_sep.inputs["Vector"])
    jit_ux2 = b.N("ShaderNodeMath", (3300, -3450), operation="MULTIPLY")
    b.L(jit_sep.outputs["X"], jit_ux2.inputs[0])
    b.L(jit_u1.outputs["Value"], jit_ux2.inputs[1])
    jit_vy2 = b.N("ShaderNodeMath", (3300, -3520), operation="MULTIPLY")
    b.L(jit_sep.outputs["Y"], jit_vy2.inputs[0])
    b.L(jit_v1.outputs["Value"], jit_vy2.inputs[1])
    # v2.8: clamp the jittered slot coordinates back inside the face bbox (0.1mm
    # margin) so no anchor can ever escape a face by jitter - the containment
    # contract is exact AND tile counts stay deterministic (the course formula
    # keeps matching). Staggered wrap columns land exactly on the face edge and
    # used to jitter outside it (randomly dropping edge tiles).
    CLM = 0.0001
    aj_1 = b.N("ShaderNodeMath", (3450, -3450), operation="ADD")
    b.L(a_sp.outputs["Value"], aj_1.inputs[0])
    b.L(jit_ux2.outputs["Value"], aj_1.inputs[1])
    alo_m = b.N("ShaderNodeMath", (3450, -3600), operation="ADD")
    b.L(alo_v, alo_m.inputs[0]); alo_m.inputs[1].default_value = CLM
    ahi_m = b.N("ShaderNodeMath", (3450, -3680), operation="MULTIPLY_ADD")
    b.L(w_v, ahi_m.inputs[0]); ahi_m.inputs[1].default_value = 1.0
    b.L(alo_v, ahi_m.inputs[2])
    ahi_m2 = b.N("ShaderNodeMath", (3600, -3680), operation="SUBTRACT")
    b.L(ahi_m.outputs["Value"], ahi_m2.inputs[0]); ahi_m2.inputs[1].default_value = CLM
    aj_2 = b.N("ShaderNodeMath", (3600, -3450), operation="MINIMUM")
    b.L(aj_1.outputs["Value"], aj_2.inputs[0])
    b.L(ahi_m2.outputs["Value"], aj_2.inputs[1])
    a_fin = b.N("ShaderNodeMath", (3750, -3450), operation="MAXIMUM")
    b.L(aj_2.outputs["Value"], a_fin.inputs[0])
    b.L(alo_m.outputs["Value"], a_fin.inputs[1])
    bj_1 = b.N("ShaderNodeMath", (3450, -3520), operation="ADD")
    b.L(bhalf.outputs["Value"], bj_1.inputs[0])
    b.L(jit_vy2.outputs["Value"], bj_1.inputs[1])
    blo_m = b.N("ShaderNodeMath", (3750, -3600), operation="ADD")
    b.L(blo_v, blo_m.inputs[0]); blo_m.inputs[1].default_value = CLM
    bhi_m = b.N("ShaderNodeMath", (3750, -3680), operation="MULTIPLY_ADD")
    b.L(h_v, bhi_m.inputs[0]); bhi_m.inputs[1].default_value = 1.0
    b.L(blo_v, bhi_m.inputs[2])
    bhi_m2 = b.N("ShaderNodeMath", (3900, -3680), operation="SUBTRACT")
    b.L(bhi_m.outputs["Value"], bhi_m2.inputs[0]); bhi_m2.inputs[1].default_value = CLM
    bj_2 = b.N("ShaderNodeMath", (3600, -3520), operation="MINIMUM")
    b.L(bj_1.outputs["Value"], bj_2.inputs[0])
    b.L(bhi_m2.outputs["Value"], bj_2.inputs[1])
    b_fin = b.N("ShaderNodeMath", (3750, -3520), operation="MAXIMUM")
    b.L(bj_2.outputs["Value"], b_fin.inputs[0])
    b.L(blo_m.outputs["Value"], b_fin.inputs[1])
    u_fin = b.N("ShaderNodeVectorMath", (3950, -3450), operation="SCALE")
    b.L(u_v, u_fin.inputs[0])
    b.L(a_fin.outputs["Value"], u_fin.inputs["Scale"])
    v_fin = b.N("ShaderNodeVectorMath", (3950, -3520), operation="SCALE")
    b.L(v_v, v_fin.inputs[0])
    b.L(b_fin.outputs["Value"], v_fin.inputs["Scale"])
    p_sum1 = b.N("ShaderNodeVectorMath", (4100, -3485), operation="ADD")
    b.L(u_fin.outputs["Vector"], p_sum1.inputs[0])
    b.L(v_fin.outputs["Vector"], p_sum1.inputs[1])
    p_sum3 = b.N("ShaderNodeVectorMath", (4250, -3485), operation="ADD")
    b.L(c_v, p_sum3.inputs[0])
    b.L(p_sum1.outputs["Vector"], p_sum3.inputs[1])
    setpos_c = b.N("GeometryNodeSetPosition", (3750, -2200))
    b.L(real.outputs["Geometry"], setpos_c.inputs["Geometry"])
    b.L(p_sum3.outputs["Vector"], setpos_c.inputs["Position"])
    # ---- v2.8 CONTAINMENT (the user's phantom-wall-slab bug): a cladding slot
    # is kept ONLY if its anchor lies inside a real face polygon of the host
    # mesh. The v2.2 course layout fills the face BOUNDING BOX, so non-rect
    # faces (his gable triangle, thin sliver fragments) used to flood tiles into
    # empty air outside the face. Proximity distance to the mesh is exactly 0
    # inside any face polygon and positive outside it - the slot-level
    # point-in-face test, run on the FINAL (post-jitter) positions after Set
    # Position so it evaluates in the plain point context. Tolerance 0.5 mm
    # local (float noise only; edge slots sit >= half a slot from any edge so
    # jitter can never trigger it).
    prox_c = b.N("GeometryNodeProximity", (3400, -3200))
    b.L(mesh_only, prox_c.inputs["Geometry"])
    pos_c = b.N("GeometryNodeInputPosition", (3250, -3350))
    b.L(pos_c.outputs["Position"], prox_c.inputs["Sample Position"])
    try:
        prox_c.inputs["Accuracy"].default_value = 0.0   # exact search (0.05 default is approximate)
    except Exception:
        pass
    # v2.4 evaluation-context contract: proximity fields read directly in a
    # DELETE SELECTION evaluate as garbage for most points (measured: only ~25%
    # of in-face anchors kept). Materialize the distance as a POINT ATTRIBUTE in
    # a STORE context first, then the selection reads it back - the exact
    # pattern the frame attributes use above.
    st_cd = b.N("GeometryNodeStoreNamedAttribute", (3400, -2500), data_type="FLOAT",
                domain="POINT")
    b.L(setpos_c.outputs["Geometry"], st_cd.inputs["Geometry"])
    st_cd.inputs["Name"].default_value = "vm_cd"
    b.L(prox_c.outputs["Distance"], st_cd.inputs["Value"])
    cd_rd = b.N("GeometryNodeInputNamedAttribute", (3550, -3350))
    cd_rd.data_type = "FLOAT"
    cd_rd.inputs["Name"].default_value = "vm_cd"
    in_face = b.N("FunctionNodeCompare", (3650, -3200), data_type="FLOAT",
                  operation="LESS_EQUAL")
    b.L(cd_rd.outputs["Attribute"], in_face.inputs["A"])
    in_face.inputs["B"].default_value = CLAD_EPS
    keep_c2 = b.N("FunctionNodeBooleanMath", (3850, -3100), operation="AND")
    b.L(keep_ij.outputs["Boolean"], keep_c2.inputs[0])
    if V28_FLAGS.get("contain", True):
        b.L(in_face.outputs["Result"], keep_c2.inputs[1])
    else:
        keep_c2.inputs[1].default_value = True
    not_keep = b.N("FunctionNodeBooleanMath", (4050, -3100), operation="NOT")
    b.L(keep_c2.outputs["Boolean"], not_keep.inputs[0])
    del_c = b.N("GeometryNodeDeleteGeometry", (4250, -2200), domain="POINT")
    b.L(st_cd.outputs["Geometry"], del_c.inputs["Geometry"])
    b.L(not_keep.outputs["Boolean"], del_c.inputs["Selection"])
    clad_geo = del_c.outputs["Geometry"]

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
    # v2.4.1: Vertical Range Min/Max are WORLD heights -> local z = world / sz
    vr_l = []
    for _i, _nm in enumerate(("Vertical Range Min", "Vertical Range Max")):
        _d = b.N("ShaderNodeMath", (-320, -220 - 60 * _i), operation="DIVIDE")
        b.L(gi.outputs[_nm], _d.inputs[0])
        b.L(sz_g, _d.inputs[1])
        vr_l.append(_d.outputs["Value"])
    b.L(vr_l[0], vgrad.inputs["From Min"])
    b.L(vr_l[1], vgrad.inputs["From Max"])
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
    # v2.4.1: Proximity Radius is WORLD meters (approx: volume-mean scale factor,
    # exact for uniform scale; non-uniform scale makes distance anisotropic)
    prox_l = b.N("ShaderNodeMath", (-70, -850), operation="DIVIDE")
    b.L(gi.outputs["Proximity Radius"], prox_l.inputs[0])
    b.L(geo_f, prox_l.inputs[1])
    b.L(prox_l.outputs["Value"], cmp_prox.inputs["B"])
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

    # ================= v2.8 GAP LAW + SPREAD (the user's two opening bugs) =====
    # (1) vm_gate1: the Random-layout strip edge guard (stored on Fit points).
    g1_a = b.N("GeometryNodeInputNamedAttribute", (600, -2200))
    g1_a.data_type = "FLOAT"
    g1_a.inputs["Name"].default_value = "vm_gate1"
    g1_sw = b.N("GeometryNodeSwitch", (800, -2200))
    g1_sw.input_type = "FLOAT"
    b.L(g1_a.outputs["Exists"], g1_sw.inputs["Switch"])
    g1_sw.inputs["False"].default_value = 1.0
    b.L(g1_a.outputs["Attribute"], g1_sw.inputs["True"])
    g1_ok = b.N("FunctionNodeCompare", (950, -2200), data_type="FLOAT",
                operation="GREATER_EQUAL")
    b.L(g1_sw.outputs["Output"], g1_ok.inputs["A"])
    g1_ok.inputs["B"].default_value = 0.5
    # (2) gap-law GREEDY: only the FIRST candidate per (wall plane, column, row)
    # survives - coincident duplicate faces (hand-built meshes) share ONE grid
    # instead of interleaving, and no two kept openings on a plane can collide.
    gcol_a = b.N("GeometryNodeInputNamedAttribute", (600, -2400))
    gcol_a.data_type = "FLOAT"
    gcol_a.inputs["Name"].default_value = "vm_gcol"
    grow_a = b.N("GeometryNodeInputNamedAttribute", (600, -2550))
    grow_a.data_type = "FLOAT"
    grow_a.inputs["Name"].default_value = "vm_grow"
    gn_a = b.N("GeometryNodeInputNamedAttribute", (600, -2700))
    gn_a.data_type = "FLOAT_VECTOR"
    gn_a.inputs["Name"].default_value = "vm_normal"
    gc_a = b.N("GeometryNodeInputNamedAttribute", (600, -2850))
    gc_a.data_type = "FLOAT_VECTOR"
    gc_a.inputs["Name"].default_value = "vm_c"
    # canonical plane hash (same sign convention as the canonical u tangent)
    gn_sep = b.N("ShaderNodeSeparateXYZ", (800, -2700))
    b.L(gn_a.outputs["Attribute"], gn_sep.inputs["Vector"])
    n_flipx = b.N("FunctionNodeCompare", (950, -2700), data_type="FLOAT",
                  operation="LESS_THAN")
    b.L(gn_sep.outputs["X"], n_flipx.inputs["A"])
    n_flipx.inputs["B"].default_value = -1e-6
    n_absx = b.N("ShaderNodeMath", (950, -2850), operation="ABSOLUTE")
    b.L(gn_sep.outputs["X"], n_absx.inputs[0])
    n_zerox = b.N("FunctionNodeCompare", (1100, -2850), data_type="FLOAT",
                  operation="LESS_EQUAL")
    b.L(n_absx.outputs["Value"], n_zerox.inputs["A"])
    n_zerox.inputs["B"].default_value = 1e-6
    n_posy = b.N("FunctionNodeCompare", (1100, -3000), data_type="FLOAT",
                 operation="GREATER_THAN")
    b.L(gn_sep.outputs["Y"], n_posy.inputs["A"])
    n_posy.inputs["B"].default_value = 1e-6
    n_fx2 = b.N("FunctionNodeBooleanMath", (1250, -2900), operation="AND")
    b.L(n_zerox.outputs["Result"], n_fx2.inputs[0])
    b.L(n_posy.outputs["Result"], n_fx2.inputs[1])
    n_flip = b.N("FunctionNodeBooleanMath", (1400, -2750), operation="OR")
    b.L(n_flipx.outputs["Result"], n_flip.inputs[0])
    b.L(n_fx2.outputs["Boolean"], n_flip.inputs[1])
    n_neg = b.N("ShaderNodeVectorMath", (1400, -2700), operation="SCALE")
    b.L(gn_a.outputs["Attribute"], n_neg.inputs[0])
    n_neg.inputs["Scale"].default_value = -1.0
    n_can_sw = b.N("GeometryNodeSwitch", (1550, -2750))
    n_can_sw.input_type = "VECTOR"
    b.L(n_flip.outputs["Boolean"], n_can_sw.inputs["Switch"])
    b.L(gn_a.outputs["Attribute"], n_can_sw.inputs["False"])
    b.L(n_neg.outputs["Vector"], n_can_sw.inputs["True"])
    d_pl = b.N("ShaderNodeVectorMath", (1700, -2850), operation="DOT_PRODUCT")
    b.L(gc_a.outputs["Attribute"], d_pl.inputs[0])
    b.L(n_can_sw.outputs["Output"], d_pl.inputs[1])
    # SAFE group id (v2.8.1): the id MUST stay < 2^24 = 16.7M - Blender's math
    # nodes run float32 and any larger id silently drops the low bits (the
    # column term!), collapsing every column of a wall into ONE greedy group.
    #   norm_code (0..26) * 420 + plane_d (0..400)   -> <= 11,320
    #   * 1024 + col_row (grow*64 + gcol, 0..1087)   -> <= 11,591,680  (safe)
    d_q1 = b.N("ShaderNodeMath", (1850, -2850), operation="MULTIPLY")
    b.L(d_pl.outputs["Value"], d_q1.inputs[0])
    d_q1.inputs[1].default_value = 20.0
    d_q = b.N("ShaderNodeMath", (2000, -2850), operation="ADD")
    b.L(d_q1.outputs["Value"], d_q.inputs[0])
    d_q.inputs[1].default_value = 200.0
    d_sh = b.N("ShaderNodeMath", (2150, -2850), operation="FLOORED_MODULO")
    b.L(d_q.outputs["Value"], d_sh.inputs[0])
    d_sh.inputs[1].default_value = 420.0
    nh_sep = b.N("ShaderNodeSeparateXYZ", (1700, -3050))
    b.L(n_can_sw.outputs["Output"], nh_sep.inputs["Vector"])
    nh_1 = b.N("ShaderNodeMath", (1850, -3050), operation="MULTIPLY_ADD")
    b.L(nh_sep.outputs["X"], nh_1.inputs[0])
    nh_1.inputs[1].default_value = 9.0
    nh_1.inputs[2].default_value = 9.0
    nh_2 = b.N("ShaderNodeMath", (2000, -3050), operation="MULTIPLY_ADD")
    b.L(nh_sep.outputs["Y"], nh_2.inputs[0])
    nh_2.inputs[1].default_value = 3.0
    nh_2.inputs[2].default_value = 3.0
    nh_3 = b.N("ShaderNodeMath", (2150, -3050), operation="ADD")
    b.L(nh_sep.outputs["Z"], nh_3.inputs[0])
    nh_3.inputs[1].default_value = 1.0
    nh_4 = b.N("ShaderNodeMath", (2300, -3050), operation="ADD")
    b.L(nh_1.outputs["Value"], nh_4.inputs[0])
    b.L(nh_2.outputs["Value"], nh_4.inputs[1])
    nh_r = b.N("ShaderNodeMath", (2300, -3150), operation="ADD")
    b.L(nh_4.outputs["Value"], nh_r.inputs[0])
    b.L(nh_3.outputs["Value"], nh_r.inputs[1])
    nh_m = b.N("ShaderNodeMath", (2450, -3050), operation="FLOORED_MODULO")
    b.L(nh_r.outputs["Value"], nh_m.inputs[0])
    nh_m.inputs[1].default_value = 27.0
    gid_1 = b.N("ShaderNodeMath", (2600, -2950), operation="MULTIPLY_ADD")
    b.L(nh_m.outputs["Value"], gid_1.inputs[0])
    gid_1.inputs[1].default_value = 420.0
    b.L(d_sh.outputs["Value"], gid_1.inputs[2])
    gid_2 = b.N("ShaderNodeMath", (2750, -2950), operation="FLOORED_MODULO")
    b.L(gid_1.outputs["Value"], gid_2.inputs[0])
    gid_2.inputs[1].default_value = 12000.0
    col_g = b.N("ShaderNodeMath", (2600, -3200), operation="MULTIPLY_ADD")
    b.L(grow_a.outputs["Attribute"], col_g.inputs[0])
    col_g.inputs[1].default_value = 64.0
    b.L(gcol_a.outputs["Attribute"], col_g.inputs[2])
    col_gm = b.N("ShaderNodeMath", (2750, -3200), operation="FLOORED_MODULO")
    b.L(col_g.outputs["Value"], col_gm.inputs[0])
    col_gm.inputs[1].default_value = 1088.0
    col_gz = b.N("ShaderNodeMath", (2900, -3200), operation="MAXIMUM")
    b.L(col_gm.outputs["Value"], col_gz.inputs[0])
    col_gz.inputs[1].default_value = 0.0
    gid_3 = b.N("ShaderNodeMath", (2900, -2950), operation="MULTIPLY_ADD")
    b.L(gid_2.outputs["Value"], gid_3.inputs[0])
    gid_3.inputs[1].default_value = 1088.0
    b.L(col_gz.outputs["Value"], gid_3.inputs[2])
    _gsrc = V28_FLAGS.get("gidsrc", "full")
    if _gsrc == "colonly":
        b.L(col_gz.outputs["Value"], gid_3.inputs[0])
        gid_3.inputs[1].default_value = 1.0
        gid_3.inputs[2].default_value = 0.0
    elif _gsrc == "planeonly":
        b.L(gid_2.outputs["Value"], gid_3.inputs[0])
        gid_3.inputs[1].default_value = 1.0
        gid_3.inputs[2].default_value = 0.0
    gid_i = b.N("ShaderNodeMath", (3050, -2950), operation="ROUND")
    b.L(gid_3.outputs["Value"], gid_i.inputs[0])
    acc_g = b.N("GeometryNodeAccumulateField", (3200, -2750), domain="POINT")
    acc_g.inputs["Value"].default_value = 1.0
    if V28_FLAGS.get("greedy") == "zerogroup":
        acc_g.inputs["Group ID"].default_value = 0
    else:
        b.L(gid_i.outputs["Value"], acc_g.inputs["Group ID"])
    first_ok = b.N("FunctionNodeCompare", (3350, -2750), data_type="FLOAT",
                   operation="LESS_THAN")
    b.L(acc_g.outputs["Leading"], first_ok.inputs["A"])
    # Blender 5.2 Accumulate Field 'Leading' counts the CURRENT element too
    # (the v2.7 cap's 'Leading > Max keeps exactly Max' semantics rely on it),
    # so the group's FIRST element has Leading == 1; < 1.5 is robust to either
    # convention.
    first_ok.inputs["B"].default_value = 1.5
    greedy_ok = b.N("FunctionNodeBooleanMath", (3500, -2600), operation="OR")
    gcol_not = b.N("FunctionNodeBooleanMath", (3350, -2600), operation="NOT")
    b.L(gcol_a.outputs["Exists"], gcol_not.inputs[0])
    b.L(gcol_not.outputs["Boolean"], greedy_ok.inputs[0])
    b.L(first_ok.outputs["Result"], greedy_ok.inputs[1])
    # (3) CROSS-LAYER gap law: openings placed by EARLIER modifiers (marked
    # instances) collapse to their anchors; any candidate whose anchor sits
    # within the clearance of a neighbour anchor is dropped - layers can never
    # overlap each other however they are configured.
    mark_a = b.N("GeometryNodeInputNamedAttribute", (600, -3300))
    mark_a.data_type = "FLOAT"
    mark_a.inputs["Name"].default_value = "vm_openmark"
    # v2.8.1: only REAL marks count - on a bare input mesh (no previous layer)
    # the attribute is missing and SeparateGeometry would happily treat the
    # mesh's own points as 'marked neighbours' (rejecting every candidate).
    mark_sw = b.N("GeometryNodeSwitch", (700, -3300))
    mark_sw.input_type = "FLOAT"
    b.L(mark_a.outputs["Exists"], mark_sw.inputs["Switch"])
    mark_sw.inputs["False"].default_value = 0.0
    b.L(mark_a.outputs["Attribute"], mark_sw.inputs["True"])
    mark_ok = b.N("FunctionNodeCompare", (800, -3300), data_type="FLOAT",
                  operation="GREATER_EQUAL")
    b.L(mark_sw.outputs["Output"], mark_ok.inputs["A"])
    mark_ok.inputs["B"].default_value = 0.5
    sep_mark = b.N("GeometryNodeSeparateGeometry", (950, -3300))
    sep_mark.domain = "INSTANCE"
    b.L(gi.outputs["Geometry"], sep_mark.inputs["Geometry"])
    b.L(mark_ok.outputs["Result"], sep_mark.inputs["Selection"])
    real_mark = b.N("GeometryNodeRealizeInstances", (1150, -3300))
    b.L(sep_mark.outputs["Selection"], real_mark.inputs["Geometry"])
    anc_a = b.N("GeometryNodeInputNamedAttribute", (1350, -3300))
    anc_a.data_type = "FLOAT_VECTOR"
    anc_a.inputs["Name"].default_value = "vm_anchor"
    # v2.8.1: unanchored points (attribute missing) get pushed to the far
    # sentinel position instead of the origin - a stray origin point would sit
    # within one opening-width of every candidate on the ground floor.
    anc_sw = b.N("GeometryNodeSwitch", (1450, -3300))
    anc_sw.input_type = "VECTOR"
    b.L(anc_a.outputs["Exists"], anc_sw.inputs["Switch"])
    anc_sw.inputs["False"].default_value = (1e6, 1e6, 1e6)
    b.L(anc_a.outputs["Attribute"], anc_sw.inputs["True"])
    set_mark = b.N("GeometryNodeSetPosition", (1550, -3300))
    b.L(real_mark.outputs["Geometry"], set_mark.inputs["Geometry"])
    b.L(anc_sw.outputs["Output"], set_mark.inputs["Position"])
    # NOTE: Proximity on an EMPTY target reports distance 0 (Is Valid stays
    # True in Blender 5.2!) which would reject every candidate on the first
    # layer of a stack - a far-away sentinel point keeps the target non-empty
    # and can never be the nearest neighbour.
    mark_sent = b.N("GeometryNodePoints", (1650, -3450))
    mark_sent.inputs["Count"].default_value = 1
    mark_sent.inputs["Position"].default_value = (1e6, 1e6, 1e6)
    mark_join = b.N("GeometryNodeJoinGeometry", (1700, -3300))
    b.L(set_mark.outputs["Geometry"], mark_join.inputs["Geometry"])
    b.L(mark_sent.outputs["Points"], mark_join.inputs["Geometry"])
    prox_o = b.N("GeometryNodeProximity", (1750, -3300))
    b.L(mark_join.outputs["Geometry"], prox_o.inputs["Geometry"])
    b.L(pos.outputs["Position"], prox_o.inputs["Sample Position"])
    # v2.8.2 CROSS-LAYER CLEARANCE: the neighbour's HORIZONTAL distance (the
    # world-XY plane - openings only ever sit on vertical walls) decides, not
    # the 3D anchor distance. A 3D threshold inflated by the vertical offset
    # either killed every window beside a door on a 2 m cube (v2.8.1: windows
    # 0 everywhere) or, smaller, let same-column overlaps through. Rule: an
    # opening keeps its slot only if it stands at least its OWN nominal Opening
    # Width (horizontally) from every earlier layer's opening anchor - then two
    # kept cross-layer openings can never share wall space.
    o_delta = b.N("ShaderNodeVectorMath", (1750, -3650), operation="SUBTRACT")
    b.L(prox_o.outputs["Position"], o_delta.inputs[0])
    b.L(pos.outputs["Position"], o_delta.inputs[1])
    o_dsep = b.N("ShaderNodeSeparateXYZ", (1900, -3650))
    b.L(o_delta.outputs["Vector"], o_dsep.inputs["Vector"])
    o_dxy = b.N("ShaderNodeCombineXYZ", (2050, -3650))
    b.L(o_dsep.outputs["X"], o_dxy.inputs["X"])
    b.L(o_dsep.outputs["Y"], o_dxy.inputs["Y"])
    o_len = b.N("ShaderNodeVectorMath", (2200, -3650), operation="LENGTH")
    b.L(o_dxy.outputs["Vector"], o_len.inputs[0])
    # v2.4 evaluation-context contract again: store the distance first (store
    # context), then the selection reads it back as a plain named attribute.
    st_od = b.N("GeometryNodeStoreNamedAttribute", (300, -3300), data_type="FLOAT",
                domain="POINT")
    b.L(pts_all, st_od.inputs["Geometry"])
    st_od.inputs["Name"].default_value = "vm_od"
    b.L(o_len.outputs["Value"], st_od.inputs["Value"])
    od_rd = b.N("GeometryNodeInputNamedAttribute", (2350, -3550))
    od_rd.data_type = "FLOAT"
    od_rd.inputs["Name"].default_value = "vm_od"
    occ_thr = b.N("ShaderNodeMath", (2050, -3500), operation="DIVIDE")
    b.L(gi.outputs["Opening Width"], occ_thr.inputs[0])
    b.L(geo_f, occ_thr.inputs[1])
    occ_far = b.N("FunctionNodeCompare", (2200, -3300), data_type="FLOAT",
                  operation="GREATER_EQUAL")
    b.L(od_rd.outputs["Attribute"], occ_far.inputs["A"])
    b.L(occ_thr.outputs["Value"], occ_far.inputs["B"])
    occ_ok = b.N("FunctionNodeBooleanMath", (2350, -3300), operation="OR")
    prox_inv = b.N("FunctionNodeBooleanMath", (2200, -3450), operation="NOT")
    b.L(prox_o.outputs["Is Valid"], prox_inv.inputs[0])
    b.L(prox_inv.outputs["Boolean"], occ_ok.inputs[0])
    b.L(occ_far.outputs["Result"], occ_ok.inputs[1])
    # ---- v2.8.3 OPENING CONTAINMENT (the floating-window leak): a Fit
    # candidate is kept only if its anchor sits ON the clad surface - the
    # strip grid fills the face BBOX, so on non-rect faces (the user's giant
    # non-planar fragments) column centres can land outside the real polygon
    # and the opening hung in empty air. The probe is the anchor projected
    # back along its own normal (undoing the Backing-Embed offset the wall
    # contact contract adds), so the tolerance stays float-noise small.
    ft_en = b.N("GeometryNodeInputNamedAttribute", (2350, -3800))
    ft_en.data_type = "FLOAT"
    ft_en.inputs["Name"].default_value = "vm_en"
    ft_nrm = b.N("GeometryNodeInputNamedAttribute", (2350, -3950))
    ft_nrm.data_type = "FLOAT_VECTOR"
    ft_nrm.inputs["Name"].default_value = "vm_normal"
    ft_e1 = b.N("ShaderNodeMath", (2500, -3800), operation="SUBTRACT")
    b.L(gi.outputs["Backing Offset"], ft_e1.inputs[0])
    b.L(gi.outputs["Embed"], ft_e1.inputs[1])
    ft_e2 = b.N("ShaderNodeMath", (2650, -3800), operation="DIVIDE")
    b.L(ft_e1.outputs["Value"], ft_e2.inputs[0])
    b.L(ft_en.outputs["Attribute"], ft_e2.inputs[1])
    ft_sv = b.N("ShaderNodeVectorMath", (2800, -3800), operation="SCALE")
    b.L(ft_nrm.outputs["Attribute"], ft_sv.inputs[0])
    b.L(ft_e2.outputs["Value"], ft_sv.inputs["Scale"])
    ft_probe = b.N("ShaderNodeVectorMath", (2950, -3800), operation="SUBTRACT")
    b.L(pos.outputs["Position"], ft_probe.inputs[0])
    b.L(ft_sv.outputs["Vector"], ft_probe.inputs[1])
    ft_prox = b.N("GeometryNodeProximity", (3100, -3800))
    b.L(mesh_only, ft_prox.inputs["Geometry"])
    b.L(ft_probe.outputs["Vector"], ft_prox.inputs["Sample Position"])
    st_fd = b.N("GeometryNodeStoreNamedAttribute", (300, -3450), data_type="FLOAT",
                domain="POINT")
    b.L(st_od.outputs["Geometry"], st_fd.inputs["Geometry"])
    st_fd.inputs["Name"].default_value = "vm_fd"
    b.L(ft_prox.outputs["Distance"], st_fd.inputs["Value"])
    fd_rd = b.N("GeometryNodeInputNamedAttribute", (3250, -3800))
    fd_rd.data_type = "FLOAT"
    fd_rd.inputs["Name"].default_value = "vm_fd"
    ft_ok = b.N("FunctionNodeCompare", (3400, -3800), data_type="FLOAT",
                operation="LESS_EQUAL")
    b.L(fd_rd.outputs["Attribute"], ft_ok.inputs["A"])
    ft_ok.inputs["B"].default_value = CLAD_EPS
    fit_not2 = b.N("FunctionNodeBooleanMath", (3400, -3950), operation="NOT")
    b.L(is_fit, fit_not2.inputs[0])
    ft_gate = b.N("FunctionNodeBooleanMath", (3550, -3850), operation="OR")
    b.L(fit_not2.outputs["Boolean"], ft_gate.inputs[0])
    b.L(ft_ok.outputs["Result"], ft_gate.inputs[1])

    # combine: masks AND edge guard AND greedy AND column filter AND occupancy
    def _flag(name, sock):
        if V28_FLAGS.get(name, True):
            return sock
        tnode = b.N("FunctionNodeCompare", (760, -400), data_type="FLOAT",
                    operation="GREATER_THAN")
        tnode.inputs["A"].default_value = 1.0
        tnode.inputs["B"].default_value = 0.0
        return tnode.outputs["Result"]
    and2a = b.N("FunctionNodeBooleanMath", (800, -400), operation="AND")
    b.L(and2.outputs["Boolean"], and2a.inputs[0])
    b.L(_flag("gate1", g1_ok.outputs["Result"]), and2a.inputs[1])
    and2b = b.N("FunctionNodeBooleanMath", (950, -400), operation="AND")
    b.L(and2a.outputs["Boolean"], and2b.inputs[0])
    b.L(_flag("greedy", greedy_ok.outputs["Boolean"]), and2b.inputs[1])
    # Column Select applies to Fit points in BOTH layouts (v2.8 strip columns)
    fit_not = b.N("FunctionNodeBooleanMath", (3500, -2450), operation="NOT")
    b.L(is_fit, fit_not.inputs[0])
    col_gate = b.N("FunctionNodeBooleanMath", (3650, -2450), operation="OR")
    b.L(fit_not.outputs["Boolean"], col_gate.inputs[0])
    b.L(cs_sw, col_gate.inputs[1])
    and2c = b.N("FunctionNodeBooleanMath", (1100, -400), operation="AND")
    b.L(and2b.outputs["Boolean"], and2c.inputs[0])
    b.L(col_gate.outputs["Boolean"], and2c.inputs[1])
    occ_gate = b.N("FunctionNodeBooleanMath", (3800, -2450), operation="OR")
    b.L(fit_not.outputs["Boolean"], occ_gate.inputs[0])
    b.L(_flag("occ", occ_ok.outputs["Boolean"]), occ_gate.inputs[1])
    and2d = b.N("FunctionNodeBooleanMath", (1250, -400), operation="AND")
    b.L(and2c.outputs["Boolean"], and2d.inputs[0])
    b.L(occ_gate.outputs["Boolean"], and2d.inputs[1])
    # v2.9 slot_occ: the same horizontal-clearance rule evaluated on the SLOT
    # candidates (their wall probe position mp_p3) so Exact N ranks only slots
    # that will survive occ_gate above
    so_prox = b.N("GeometryNodeProximity", (5100, -3500))
    b.L(mark_join.outputs["Geometry"], so_prox.inputs["Geometry"])
    b.L(mp_p3.outputs["Vector"], so_prox.inputs["Sample Position"])
    so_d = b.N("ShaderNodeVectorMath", (5250, -3500), operation="SUBTRACT")
    b.L(so_prox.outputs["Position"], so_d.inputs[0])
    b.L(mp_p3.outputs["Vector"], so_d.inputs[1])
    so_sep = b.N("ShaderNodeSeparateXYZ", (5400, -3500))
    b.L(so_d.outputs["Vector"], so_sep.inputs["Vector"])
    so_xy = b.N("ShaderNodeCombineXYZ", (5550, -3500))
    b.L(so_sep.outputs["X"], so_xy.inputs["X"])
    b.L(so_sep.outputs["Y"], so_xy.inputs["Y"])
    so_len = b.N("ShaderNodeVectorMath", (5700, -3500), operation="LENGTH")
    b.L(so_xy.outputs["Vector"], so_len.inputs[0])
    so_far = b.N("FunctionNodeCompare", (5850, -3500), data_type="FLOAT", operation="GREATER_EQUAL")
    b.L(so_len.outputs["Value"], so_far.inputs["A"])
    b.L(occ_thr.outputs["Value"], so_far.inputs["B"])
    so_inv = b.N("FunctionNodeBooleanMath", (5850, -3650), operation="NOT")
    b.L(so_prox.outputs["Is Valid"], so_inv.inputs[0])
    so_ok = b.N("FunctionNodeBooleanMath", (6000, -3550), operation="OR")
    b.L(so_inv.outputs["Boolean"], so_ok.inputs[0])
    b.L(so_far.outputs["Result"], so_ok.inputs[1])
    # slot candidates only exist on the Fit path - NO is_fit gate here: is_fit
    # comes from the Placement Mode GEOMETRY switch whose Fit branch contains
    # this slot stage, so linking it in makes a dependency cycle (measured:
    # Blender drops the link and every opening layer goes empty)
    b.L(_flag("occ", so_ok.outputs["Boolean"]), keep_k4.inputs[1])
    and2e = b.N("FunctionNodeBooleanMath", (1400, -400), operation="AND")
    b.L(and2d.outputs["Boolean"], and2e.inputs[0])
    b.L(ft_gate.outputs["Boolean"], and2e.inputs[1])

    keep_f = b.N("ShaderNodeMath", operation="ADD", location=(600, -500))
    # v2.4 evaluation-context contract: the whole gate decision is materialized
    # as a point attribute in a STORE context first (and2d chains several new
    # v2.8 fields), then the cap/delete read it back as a plain named field.
    st_keep = b.N("GeometryNodeStoreNamedAttribute", (300, -400), data_type="FLOAT",
                domain="POINT")
    b.L(st_fd.outputs["Geometry"], st_keep.inputs["Geometry"])
    st_keep.inputs["Name"].default_value = "vm_keep"
    mk_conv = b.N("ShaderNodeMath", (300, -550), operation="ADD")
    b.L(and2e.outputs["Boolean"], mk_conv.inputs[0])
    mk_conv.inputs[1].default_value = 0.0
    b.L(mk_conv.outputs["Value"], st_keep.inputs["Value"])
    mk_rd = b.N("GeometryNodeInputNamedAttribute", (450, -450))
    mk_rd.data_type = "FLOAT"
    mk_rd.inputs["Name"].default_value = "vm_keep"
    b.L(mk_rd.outputs["Attribute"], keep_f.inputs[0])
    keep_f.inputs[1].default_value = 0.0
    acc = b.N("GeometryNodeAccumulateField", (800, -500), domain="POINT")
    b.L(keep_f.outputs["Value"], acc.inputs["Value"])
    cmp_cap_n = b.N("FunctionNodeCompare", (1000, -500), data_type="FLOAT", operation="GREATER_THAN")
    b.L(acc.outputs["Leading"], cmp_cap_n.inputs["A"])
    b.L(gi.outputs["Max Instances"], cmp_cap_n.inputs["B"])
    # v2.8 ROUND-ROBIN cap for Fit: rank = per-face kept rank * #faces + face
    # ordinal, so the budget visits EVERY qualifying wall before any wall gets a
    # second opening (first-N in point order starved every wall after the first).
    gfi_a = b.N("GeometryNodeInputNamedAttribute", (1200, -5200))
    gfi_a.data_type = "FLOAT"
    gfi_a.inputs["Name"].default_value = "vm_fi"
    gffo_a = b.N("GeometryNodeInputNamedAttribute", (1200, -5350))
    gffo_a.data_type = "FLOAT"
    gffo_a.inputs["Name"].default_value = "vm_ffo"
    gffn_a = b.N("GeometryNodeInputNamedAttribute", (1200, -5500))
    gffn_a.data_type = "FLOAT"
    gffn_a.inputs["Name"].default_value = "vm_ffn"
    acc_r = b.N("GeometryNodeAccumulateField", (1400, -5200), domain="POINT")
    b.L(keep_f.outputs["Value"], acc_r.inputs["Value"])
    b.L(gfi_a.outputs["Attribute"], acc_r.inputs["Group ID"])
    ffn_g = b.N("ShaderNodeMath", (1400, -5500), operation="MAXIMUM")
    b.L(gffn_a.outputs["Attribute"], ffn_g.inputs[0])
    ffn_g.inputs[1].default_value = 1.0
    # 'Leading' is 1-based for KEPT points but a DROPPED point's Leading counts
    # only the kept points strictly before it - subtract the point's OWN keep
    # value (v2.8.1 bug: rr_0 = Leading - 1 went NEGATIVE for a dropped first
    # point of a face and the min-offset cap below then deleted everything).
    rr_0 = b.N("ShaderNodeMath", (1550, -5350), operation="SUBTRACT")
    b.L(acc_r.outputs["Leading"], rr_0.inputs[0])
    b.L(keep_f.outputs["Value"], rr_0.inputs[1])
    # vm_ffo is a 1-based face ordinal (Accumulate Leading) -> 0-based here too
    ffo_0 = b.N("ShaderNodeMath", (1550, -5550), operation="SUBTRACT")
    b.L(gffo_a.outputs["Attribute"], ffo_0.inputs[0])
    ffo_0.inputs[1].default_value = 1.0
    rr_1 = b.N("ShaderNodeMath", (1650, -5350), operation="MULTIPLY_ADD")
    b.L(rr_0.outputs["Value"], rr_1.inputs[0])
    b.L(ffn_g.outputs["Value"], rr_1.inputs[1])
    b.L(ffo_0.outputs["Value"], rr_1.inputs[2])
    # v2.8.2 CAP ACCOUNTING: the kept set must be exactly the Max SMALLEST
    # round-robin ranks - but raw ranks have interior GAPS whenever faces run
    # out of candidates, so threshold arithmetic on the rank value undercounts
    # (v2.8.1: 15 kept where 25 were budgeted, 0 kept where 3 were budgeted).
    # Sort the candidates by rank and keep the first Max in SORTED order:
    # gap-free by construction. The rank is materialized as vm_rr first (the
    # store evaluates in the UNSORTED context, so the per-face accumulate order
    # - and therefore the rank itself - stays stable and deterministic).
    rr_st = b.N("GeometryNodeStoreNamedAttribute", (1750, -5150), data_type="FLOAT",
                domain="POINT")
    b.L(st_keep.outputs["Geometry"], rr_st.inputs["Geometry"])
    rr_st.inputs["Name"].default_value = "vm_rr"
    b.L(rr_1.outputs["Value"], rr_st.inputs["Value"])
    rr_rd = b.N("GeometryNodeInputNamedAttribute", (1750, -5250))
    rr_rd.data_type = "FLOAT"
    rr_rd.inputs["Name"].default_value = "vm_rr"
    rr_sort = b.N("GeometryNodeSortElements", (1900, -5150))
    rr_sort.domain = "POINT"
    b.L(rr_st.outputs["Geometry"], rr_sort.inputs["Geometry"])
    b.L(rr_rd.outputs["Attribute"], rr_sort.inputs["Sort Weight"])
    rr_sort_sw = b.N("GeometryNodeSwitch", (2050, -5100))
    rr_sort_sw.input_type = "GEOMETRY"
    if V28_FLAGS.get("rr", True):
        b.L(is_fit, rr_sort_sw.inputs["Switch"])
    else:
        rr_sort_sw.inputs["Switch"].default_value = False
    b.L(rr_st.outputs["Geometry"], rr_sort_sw.inputs["False"])
    b.L(rr_sort.outputs["Geometry"], rr_sort_sw.inputs["True"])
    geo_capped = rr_sort_sw.outputs["Output"]
    # global kept-rank in SORTED order: Leading > Max deletes -> exactly Max kept
    acc2 = b.N("GeometryNodeAccumulateField", (1900, -5450), domain="POINT")
    b.L(keep_f.outputs["Value"], acc2.inputs["Value"])
    cmp_cap_fit = b.N("FunctionNodeCompare", (2100, -5350), data_type="FLOAT",
                      operation="GREATER_THAN")
    b.L(acc2.outputs["Leading"], cmp_cap_fit.inputs["A"])
    b.L(gi.outputs["Max Instances"], cmp_cap_fit.inputs["B"])
    cap_sw = b.N("GeometryNodeSwitch", (2100, -500))
    cap_sw.input_type = "BOOLEAN"
    if V28_FLAGS.get("rr", True):
        b.L(is_fit, cap_sw.inputs["Switch"])
        b.L(cmp_cap_n.outputs["Result"], cap_sw.inputs["False"])
        b.L(cmp_cap_fit.outputs["Result"], cap_sw.inputs["True"])
        cmp_cap = cap_sw.outputs["Output"]
    else:
        cmp_cap = cmp_cap_n.outputs["Result"]
    not_keep2 = b.N("FunctionNodeCompare", (800, -700), data_type="FLOAT",
                    operation="LESS_THAN")
    b.L(mk_rd.outputs["Attribute"], not_keep2.inputs["A"])
    not_keep2.inputs["B"].default_value = 0.5
    del_sel = b.N("FunctionNodeBooleanMath", (1200, -600), operation="OR")
    b.L(not_keep2.outputs["Result"], del_sel.inputs[0])
    b.L(cmp_cap, del_sel.inputs[1])
    dele = b.N("GeometryNodeDeleteGeometry", (1400, 100), domain="POINT")
    b.L(geo_capped, dele.inputs["Geometry"])
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
    b.L(max1_p.outputs["Value"], sx_f.inputs[1])
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

    # ---------------- v2.4.1: counter-scale instances (world-size contract) ---
    # Instances are placed in the host's LOCAL space, so without compensation
    # every tile/door/window inherits the object's unapplied scale and stretches
    # with it. Divide the instance scale by the world-meters-per-meter factor of
    # EACH instance axis (axes taken from the actual per-point placement
    # rotation, so this is exact for any face orientation; the object scale is
    # read from Self Object and gated to 1 for un-scaled hosts).
    # v2.6: the Slots auto-fit factor (vm_fitk, see Opening Fit) multiplies the
    # scale here - points without the attribute (Scatter/Random/Cladding) get 1.
    fitk_attr = b.N("GeometryNodeInputNamedAttribute", (2950, 80))
    fitk_attr.data_type = "FLOAT"
    fitk_attr.inputs["Name"].default_value = "vm_fitk"
    fitk_use = b.N("GeometryNodeSwitch", (3000, -20))
    fitk_use.input_type = "FLOAT"
    b.L(fitk_attr.outputs["Exists"], fitk_use.inputs["Switch"])
    fitk_use.inputs["False"].default_value = 1.0
    b.L(fitk_attr.outputs["Attribute"], fitk_use.inputs["True"])
    scale_k = b.N("ShaderNodeVectorMath", (3020, 150), operation="SCALE")
    b.L(scale_out, scale_k.inputs[0])
    b.L(fitk_use.outputs["Output"], scale_k.inputs["Scale"])
    def axis_eff(axis_const, loc):
        rvn = b.N("FunctionNodeRotateVector", loc)
        rvn.inputs["Vector"].default_value = axis_const
        b.L(rot_out, rvn.inputs["Rotation"])
        return ws["eff_of"](rvn.outputs["Vector"], (loc[0] + 250, loc[1]))

    eff_ix = axis_eff((1.0, 0.0, 0.0), (2200, 420))
    eff_iy = axis_eff((0.0, 1.0, 0.0), (2200, 340))
    eff_iz = axis_eff((0.0, 0.0, 1.0), (2200, 260))
    eff_i = b.N("ShaderNodeCombineXYZ", (2900, 340))
    b.L(eff_ix, eff_i.inputs["X"])
    b.L(eff_iy, eff_i.inputs["Y"])
    b.L(eff_iz, eff_i.inputs["Z"])
    scale_fixed = b.N("ShaderNodeVectorMath", (3100, 200), operation="DIVIDE")
    b.L(scale_k.outputs["Vector"], scale_fixed.inputs[0])
    b.L(eff_i.outputs["Vector"], scale_fixed.inputs[1])

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
    # v2.5: with Slots + No-Repeat the instance index comes from the slot's
    # stored vm_pick (adjacent columns always differ); otherwise the v1 random
    # draw is kept bit-identically.
    no_rep = b.N("FunctionNodeBooleanMath", (1500, 600), operation="AND")
    b.L(is_slots, no_rep.inputs[0])
    b.L(gi.outputs["No-Repeat"], no_rep.inputs[1])

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
        pk_attr = b.N("GeometryNodeInputNamedAttribute", (1850, y - 300))
        pk_attr.data_type = "FLOAT"
        pk_attr.inputs["Name"].default_value = "vm_pick"
        pick_sw = b.N("GeometryNodeSwitch", (2000, y - 150))
        pick_sw.input_type = "INT"
        b.L(no_rep.outputs["Boolean"], pick_sw.inputs["Switch"])
        b.L(pk_attr.outputs["Attribute"], pick_sw.inputs["True"])
        b.L(rv_i.outputs["Value"], pick_sw.inputs["False"])
        iop = b.N("GeometryNodeInstanceOnPoints", (2200, y))
        b.L(dele.outputs["Geometry"], iop.inputs["Points"])
        b.L(selection_sock, iop.inputs["Selection"])
        b.L(ci.outputs["Instances"], iop.inputs["Instance"])
        iop.inputs["Pick Instance"].default_value = True
        b.L(pick_sw.outputs["Output"], iop.inputs["Instance Index"])
        b.L(rot_out, iop.inputs["Rotation"])
        b.L(scale_fixed.outputs["Vector"], iop.inputs["Scale"])
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
        m_ = b.N("ShaderNodeMath", operation="MULTIPLY_ADD", location=(2300, -550 - 120 * i))
        b.L(sep_c.outputs[ch], m_.inputs[0])
        b.L(inv_t.outputs["Value"], m_.inputs[1])
        b.L(gi.outputs["Tint Amount"], m_.inputs[2])
        b.L(m_.outputs["Value"], comb_c.inputs[i])

    join_i = b.N("GeometryNodeJoinGeometry", (2250, 300))
    b.L(iop_p.outputs["Instances"], join_i.inputs["Geometry"])
    b.L(iop_d.outputs["Instances"], join_i.inputs["Geometry"])
    store_c = b.N("GeometryNodeStoreNamedAttribute", (2450, 150), data_type="FLOAT_COLOR", domain="INSTANCE")
    b.L(join_i.outputs["Geometry"], store_c.inputs["Geometry"])
    store_c.inputs["Name"].default_value = "Color"
    b.L(comb_c.outputs["Color"], store_c.inputs["Value"])
    # v2.8: mark placed OPENINGS + their anchors so LATER modifiers can keep the
    # gap law across layers (doors vs windows can never overlap)
    mk_1 = b.N("ShaderNodeMath", (2450, -50), operation="ADD")
    b.L(is_fit, mk_1.inputs[0]); mk_1.inputs[1].default_value = 0.0
    mk_2 = b.N("ShaderNodeMath", (2600, -50), operation="ADD")
    b.L(not_debris.outputs["Boolean"], mk_2.inputs[0]); mk_2.inputs[1].default_value = 0.0
    mk_f = b.N("ShaderNodeMath", (2750, -50), operation="MULTIPLY")
    b.L(mk_1.outputs["Value"], mk_f.inputs[0])
    b.L(mk_2.outputs["Value"], mk_f.inputs[1])
    store_mk = b.N("GeometryNodeStoreNamedAttribute", (2850, 150), data_type="FLOAT",
                   domain="INSTANCE")
    b.L(store_c.outputs["Geometry"], store_mk.inputs["Geometry"])
    store_mk.inputs["Name"].default_value = "vm_openmark"
    b.L(mk_f.outputs["Value"], store_mk.inputs["Value"])
    store_an = b.N("GeometryNodeStoreNamedAttribute", (3050, 150), data_type="FLOAT_VECTOR",
                   domain="INSTANCE")
    b.L(store_mk.outputs["Geometry"], store_an.inputs["Geometry"])
    store_an.inputs["Name"].default_value = "vm_anchor"
    b.L(pos.outputs["Position"], store_an.inputs["Value"])

    join_all = b.N("GeometryNodeJoinGeometry", (2650, 100))
    b.L(base_out, join_all.inputs["Geometry"])
    b.L(store_an.outputs["Geometry"], join_all.inputs["Geometry"])
    b.L(join_all.outputs["Geometry"], go.inputs["Geometry"])

    # ---- v2.7 About panel: appended LAST so every v2.5/v2.6 socket IDENTIFIER
    # is unchanged (old stacks that re-point at this group keep their values),
    # then MOVED to the top of the interface ----
    p_about = b.panel("About", f"Engine version + quick usage ({ENGINE_VERSION}): tells you exactly which code this modifier runs")
    b.sock("Engine Version", "NodeSocketString", p_about, f"{ENGINE_VERSION}",
           desc=f"Version of the VM engine code behind this modifier ({ENGINE_VERSION}). If this "
                "panel/socket is missing the stack runs a PRE-v2.8 group - see USAGE.txt "
                "'Which version am I running?' and 'Upgrading old stacks'")
    b.sock("Usage Hint", "NodeSocketString", p_about,
           f"{ENGINE_VERSION} quick use: Fit+Slots puts doors/windows on walls (openings snap to the "
           "wall's opening grid - they SPREAD over all walls and never overlap, in Random "
           "AND Slots layouts); Cladding stays INSIDE every face (no phantom slabs on "
           "triangles/slivers); VM_RoofCap caps flat tops (Style 'Hip' on a square top = "
           "pyramid, on a round top = cone; 'Gable' for ridge roofs). Old stack? See "
           "USAGE.txt 'Which version am I running?'.",
           desc="One-line usage reminder")

    b.finish_menu_defaults()
    b.ng.description = (
        f"VM_SceneDetailer {ENGINE_VERSION} - semantic architectural application engine (Scatter/Fit/"
        "Cladding + HouseCraft Slots openings; openings spread round-robin over all walls "
        "with the gap law in BOTH layouts; cladding confined to real face polygons). The "
        f"About panel shows the Engine Version socket ('{ENGINE_VERSION}'). Which code does my stack "
        "run / how do I upgrade? See USAGE.txt 'Which version am I running?'")
    try:
        b.iface.move(p_about, 0)   # render About first, identifiers unchanged
    except Exception as e:
        log(f"  !! About panel move failed: {e}")
    return b.ng


# ---------------------------------------------------------------------------- VM_RoofCap
def build_roofcap_group():
    """v2.4 per-region roof cap.

    Every qualifying top face (up-facing quad >= Min Roof Face Size) is treated as
    its own roof region and gets its own gable/hip prism along its LOCAL long axis.
    Regions that cannot be resolved (non-quad tops, undersized fragments) are
    SKIPPED CLEANLY - no geometry is emitted for them and they are counted in the
    verification report. Honest limits: gables of different regions may intersect
    on compounds (valleys are out of scope); tops are assumed level (up-facing).
    Generated faces carry the 'vm_roofgen' face attribute so Fit never hangs
    doors/windows on generated gables.
    """
    b = NGBuilder("VM_RoofCap")
    iface = b.iface
    iface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    p = b.panel("Roof", "Per-region pitched roof generated over each qualifying flat top face")
    b.sock("Pitch", "NodeSocketFloat", p, math.radians(35.0), 0.0, math.radians(89.0), "ANGLE")
    b.sock("Overhang", "NodeSocketFloat", p, 0.25, 0.0, 10.0, "DISTANCE")
    b.menu_sock("Style", p, "Flat", "Flat (DEFAULT since v2.7) = near-flat cap with a very subtle incline + thin edge fascia, NEVER any invented gable triangles (for flat-topped designs); Gable = full-length ridge along the region's long axis; Hip = ridge shortened by half the short side (both opt-in pitch)")
    b.sock("Incline", "NodeSocketFloat", p, math.radians(2.5), 0.0, math.radians(45.0), "ANGLE",
           "Flat style: subtle incline of the flat cap along the region's long axis "
           "(world angle, default 2.5 deg - the roof reads flat but drains)")
    b.sock("Fascia", "NodeSocketFloat", p, 0.12, 0.0, 10.0, "DISTANCE",
           "Flat style: thin edge fascia skirt height at the cap's low edge (world m; "
           "kept >= 3 cm on the low side of the incline)")
    b.sock("Roof Material", "NodeSocketMaterial", p, None, desc="Material for the generated roof faces")
    b.sock("Min Roof Face Size", "NodeSocketFloat", p, 0.4, 0.0, 100.0, "DISTANCE", "Per-region: up-facing quads whose short side is smaller are SKIPPED CLEANLY (reported in verification), never garbaged")
    b.sock("Largest Face Only", "NodeSocketBool", p, False, desc="Per-region: cap only the largest qualifying top face (single-roof mode)")
    iface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

    gi = b.N("NodeGroupInput", (-2400, 0))
    go = b.N("NodeGroupOutput", (3800, 0))
    EPS = 0.002

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

    # process only the host mesh; incoming instances (from earlier modifiers)
    # pass through untouched via the final join
    del_inst = b.N("GeometryNodeDeleteGeometry", (-2400, 250), domain="INSTANCE")
    b.L(gi.outputs["Geometry"], del_inst.inputs["Geometry"])
    del_inst.inputs["Selection"].default_value = True
    mesh_in = del_inst.outputs["Geometry"]

    # ---------------- unit roof template (built in-group: no external refs) ----------------
    # unit gable prism over [-1,1]^2, eave at z=0, ridge y=0 at z=1;
    # ridge length is parameterized per region at Set Position time.
    grid = b.N("GeometryNodeMeshGrid", (-2400, -2300))
    grid.inputs["Vertices X"].default_value = 2
    grid.inputs["Vertices Y"].default_value = 2
    grid.inputs["Size X"].default_value = 2.0
    grid.inputs["Size Y"].default_value = 2.0
    t_ex = b.N("GeometryNodeExtrudeMesh", (-2200, -2300))
    t_ex.mode = "FACES"
    b.L(grid.outputs["Mesh"], t_ex.inputs["Mesh"])
    t_ex.inputs["Selection"].default_value = True
    t_off = b.N("ShaderNodeCombineXYZ", (-2350, -2450))
    t_off.inputs["Z"].default_value = 1.0
    b.L(t_off.outputs["Vector"], t_ex.inputs["Offset"])   # offset MUST be linked
    t_ex.inputs["Individual"].default_value = False
    tpos = b.N("GeometryNodeInputPosition", (-2200, -2550))
    tsep = b.N("ShaderNodeSeparateXYZ", (-2050, -2550))
    b.L(tpos.outputs["Position"], tsep.inputs["Vector"])
    tsel = b.N("FunctionNodeCompare", (-1900, -2550), data_type="FLOAT", operation="GREATER_THAN")
    b.L(tsep.outputs["Z"], tsel.inputs["A"])
    tsel.inputs["B"].default_value = 0.5
    tcomb = b.N("ShaderNodeCombineXYZ", (-1900, -2700))
    b.L(tsep.outputs["X"], tcomb.inputs["X"])
    b.L(tsep.outputs["Z"], tcomb.inputs["Z"])
    t_sp = b.N("GeometryNodeSetPosition", (-1750, -2300))
    b.L(t_ex.outputs["Mesh"], t_sp.inputs["Geometry"])
    b.L(tsel.outputs["Result"], t_sp.inputs["Selection"])
    b.L(tcomb.outputs["Vector"], t_sp.inputs["Position"])
    tcpos = b.N("GeometryNodeInputPosition", (-1750, -2650))
    tcsep = b.N("ShaderNodeSeparateXYZ", (-1600, -2650))
    b.L(tcpos.outputs["Position"], tcsep.inputs["Vector"])
    tcd = b.N("FunctionNodeCompare", (-1450, -2650), data_type="FLOAT", operation="GREATER_THAN")
    b.L(tcsep.outputs["Z"], tcd.inputs["A"])
    tcd.inputs["B"].default_value = 0.9
    t_del = b.N("GeometryNodeDeleteGeometry", (-1300, -2300), domain="FACE")
    b.L(t_sp.outputs["Geometry"], t_del.inputs["Geometry"])
    b.L(tcd.outputs["Result"], t_del.inputs["Selection"])
    st_t = b.N("GeometryNodeStoreNamedAttribute", (-1150, -2300), data_type="FLOAT_VECTOR", domain="POINT")
    b.L(t_del.outputs["Geometry"], st_t.inputs["Geometry"])
    st_t.inputs["Name"].default_value = "vm_t"
    b.L(tcpos.outputs["Position"], st_t.inputs["Value"])
    template = st_t.outputs["Geometry"]

    # ---------------- per-region qualification + frame (face domain) ----------------
    idx = b.N("GeometryNodeInputIndex", (-2400, -500))
    nrm = b.N("GeometryNodeInputNormal", (-2400, -650))
    nsep = b.N("ShaderNodeSeparateXYZ", (-2250, -650))
    b.L(nrm.outputs["Normal"], nsep.inputs["Vector"])
    # v2.4.1 world-space sizing: Overhang / Min Roof Face Size are WORLD meters,
    # Pitch is a WORLD angle (host's unapplied scale read from Self Object)
    ws = world_scale_block(b, loc=(-2800, 400))
    sx_g, sy_g, sz_g = ws["sx"], ws["sy"], ws["sz"]
    cof = b.N("GeometryNodeCornersOfFace", (-2400, -800))
    b.L(idx.outputs["Index"], cof.inputs["Face Index"])
    is_quad = b.N("FunctionNodeCompare", (-2200, -800), data_type="FLOAT", operation="EQUAL")
    b.L(cof.outputs["Total"], is_quad.inputs["A"])
    is_quad.inputs["B"].default_value = 4.0

    def corner(k):
        cof_ = b.N("GeometryNodeCornersOfFace", (-2400, -1000 - 250 * k))
        b.L(idx.outputs["Index"], cof_.inputs["Face Index"])
        coff = b.N("GeometryNodeOffsetCornerInFace", (-2250, -1000 - 250 * k))
        b.L(cof_.outputs["Corner Index"], coff.inputs["Corner Index"])
        coff.inputs["Offset"].default_value = k
        voc = b.N("GeometryNodeVertexOfCorner", (-2150, -1000 - 250 * k))
        b.L(coff.outputs["Corner Index"], voc.inputs["Corner Index"])
        si = b.N("GeometryNodeSampleIndex", (-2050, -1000 - 250 * k))
        si.data_type = "FLOAT_VECTOR"
        si.domain = "POINT"
        b.L(mesh_in, si.inputs["Geometry"])
        pnode = b.N("GeometryNodeInputPosition", (-2200, -1150 - 250 * k))
        b.L(pnode.outputs["Position"], si.inputs["Value"])
        b.L(voc.outputs["Vertex Index"], si.inputs["Index"])
        return si.outputs["Value"]

    # corner sampling NOT shared between consumers (see the VM_SceneDetailer note)
    posf = b.N("GeometryNodeInputPosition", (-1850, -650))
    fsep = b.N("ShaderNodeSeparateXYZ", (-1700, -650))
    b.L(posf.outputs["Position"], fsep.inputs["Vector"])

    e0 = b.N("ShaderNodeVectorMath", (-1850, -900), operation="SUBTRACT")
    b.L(corner(1), e0.inputs[0])
    b.L(corner(0), e0.inputs[1])
    e0d = b.N("ShaderNodeVectorMath", (-1700, -900), operation="DOT_PRODUCT")
    b.L(e0.outputs["Vector"], e0d.inputs[0])
    b.L(e0.outputs["Vector"], e0d.inputs[1])
    nondeg = b.N("FunctionNodeCompare", (-1550, -900), data_type="FLOAT", operation="GREATER_THAN")
    b.L(e0d.outputs["Value"], nondeg.inputs["A"])
    nondeg.inputs["B"].default_value = 1e-10
    end_ = b.N("ShaderNodeVectorMath", (-1700, -1050), operation="DOT_PRODUCT")
    b.L(e0.outputs["Vector"], end_.inputs[0])
    b.L(nrm.outputs["Normal"], end_.inputs[1])
    eproj = b.N("ShaderNodeVectorMath", (-1550, -1050), operation="SCALE")
    b.L(nrm.outputs["Normal"], eproj.inputs[0])
    b.L(end_.outputs["Value"], eproj.inputs["Scale"])
    eperp = b.N("ShaderNodeVectorMath", (-1400, -950), operation="SUBTRACT")
    b.L(e0.outputs["Vector"], eperp.inputs[0])
    b.L(eproj.outputs["Vector"], eperp.inputs[1])
    u0 = b.N("ShaderNodeVectorMath", (-1250, -950), operation="NORMALIZE")
    b.L(eperp.outputs["Vector"], u0.inputs[0])
    v0 = b.N("ShaderNodeVectorMath", (-1250, -1100), operation="CROSS_PRODUCT")
    b.L(nrm.outputs["Normal"], v0.inputs[0])
    b.L(u0.outputs["Vector"], v0.inputs[1])
    v0n = b.N("ShaderNodeVectorMath", (-1100, -1100), operation="NORMALIZE")
    b.L(v0.outputs["Vector"], v0n.inputs[0])

    def extents(uv):
        diffs = []
        # v2.8.2: sample up to 32 corners (OffsetCornerInFace WRAPS, so faces
        # with fewer corners just repeat samples and min/max is unchanged).
        # 4-corner sampling made an n-gon top measure ~0.39 m across instead of
        # 4.0 m - the hip height and overhang then scaled from that garbage
        # (cone apex 1.745 instead of 3.075, overhang blown to 2x).
        for k in range(32):
            d = b.N("ShaderNodeVectorMath", (-1850, -1400 - 220 * k), operation="SUBTRACT")
            b.L(corner(k), d.inputs[0])
            b.L(posf.outputs["Position"], d.inputs[1])
            dot = b.N("ShaderNodeVectorMath", (-1700, -1400 - 220 * k), operation="DOT_PRODUCT")
            b.L(d.outputs["Vector"], dot.inputs[0])
            b.L(uv, dot.inputs[1])
            diffs.append(dot.outputs["Value"])
        mins, maxs = list(diffs), list(diffs)
        while len(mins) > 1:
            mins = [m("MINIMUM", mins[i], mins[i + 1], loc=(-1550, -1400 - 10 * i)) for i in range(0, len(mins), 2)]
            maxs = [m("MAXIMUM", maxs[i], maxs[i + 1], loc=(-1400, -1400 - 10 * i)) for i in range(0, len(maxs), 2)]
        return mins[0], maxs[0]

    ua_lo, ua_hi = extents(u0.outputs["Vector"])
    va_lo, va_hi = extents(v0n.outputs["Vector"])
    W = m("SUBTRACT", ua_hi, ua_lo, loc=(-1250, -1400))
    H = m("SUBTRACT", va_hi, va_lo, loc=(-1250, -1500))
    long_u = b.N("FunctionNodeCompare", (-1100, -1450), data_type="FLOAT", operation="GREATER_EQUAL")
    b.L(W, long_u.inputs["A"])
    b.L(H, long_u.inputs["B"])
    usw = b.N("GeometryNodeSwitch", (-950, -1350))
    usw.input_type = "VECTOR"
    b.L(long_u.outputs["Result"], usw.inputs["Switch"])
    b.L(v0n.outputs["Vector"], usw.inputs["False"])
    b.L(u0.outputs["Vector"], usw.inputs["True"])
    u_l = usw.outputs["Output"]
    v_c = b.N("ShaderNodeVectorMath", (-800, -1350), operation="CROSS_PRODUCT")
    b.L(nrm.outputs["Normal"], v_c.inputs[0])
    b.L(u_l, v_c.inputs[1])
    v_l = b.N("ShaderNodeVectorMath", (-650, -1350), operation="NORMALIZE")
    b.L(v_c.outputs["Vector"], v_l.inputs[0])
    Wl = m("MAXIMUM", W, H, loc=(-950, -1500))
    Hs = m("MINIMUM", W, H, loc=(-950, -1600))

    # ---- v2.4 evaluation-context contract (see VM_SceneDetailer): corner-sampled
    # fields must be materialized as face attributes before being used in a
    # selection context. Stores first, then the qualification reads them back.
    # v2.9: buried tops (an extruded floor's old cap, overlapped boxes) are
    # never roof regions - see exterior_face_field
    store_chain, r_ext = store_exterior(b, mesh_in, "vm_rexp", (-1000, -3400))
    for nm_, dt, src in (("vm_rc", "FLOAT_VECTOR", posf.outputs["Position"]),
                         ("vm_ru", "FLOAT_VECTOR", u_l),
                         ("vm_rv", "FLOAT_VECTOR", v_l.outputs["Vector"]),
                         ("vm_rw", "FLOAT", Wl),
                         ("vm_rh", "FLOAT", Hs),
                         ("vm_rz", "FLOAT", fsep.outputs["Z"]),
                         ("vm_quad", "FLOAT", is_quad.outputs["Result"]),
                         ("vm_ndg", "FLOAT", nondeg.outputs["Result"])):
        st = b.N("GeometryNodeStoreNamedAttribute", (550, -1600), data_type=dt, domain="FACE")
        b.L(store_chain, st.inputs["Geometry"])
        st.inputs["Name"].default_value = nm_
        if dt == "FLOAT" and src.bl_idname == "FunctionNodeCompare":
            # store booleans as floats via +0.0 (compare result -> float field)
            conv = b.N("ShaderNodeMath", (450, -1750), operation="ADD")
            b.L(src, conv.inputs[0])
            conv.inputs[1].default_value = 0.0
            b.L(conv.outputs["Value"], st.inputs["Value"])
        else:
            b.L(src, st.inputs["Value"])
        store_chain = st.outputs["Geometry"]

    def named_face(name, yoff):
        n = b.N("GeometryNodeInputNamedAttribute", (700, -1900 - 120 * yoff))
        n.data_type = "FLOAT"
        n.inputs["Name"].default_value = name
        return n.outputs["Attribute"]
    nq = named_face("vm_quad", 0)
    ndg = named_face("vm_ndg", 1)
    nrw = named_face("vm_rw", 2)
    nrh2 = named_face("vm_rh", 3)

    # ---------------- per-region qualification (reads the stored attributes) --
    up_raw = b.N("FunctionNodeCompare", (-2100, -650), data_type="FLOAT", operation="GREATER_EQUAL")
    b.L(nsep.outputs["Z"], up_raw.inputs["A"])
    up_raw.inputs["B"].default_value = 0.98
    up = b.N("FunctionNodeBooleanMath", (-1950, -650), operation="AND")
    b.L(up_raw.outputs["Result"], up.inputs[0])
    b.L(r_ext, up.inputs[1])
    quad_ok = b.N("FunctionNodeCompare", (850, -1980), data_type="FLOAT", operation="GREATER_EQUAL")
    b.L(nq, quad_ok.inputs["A"])
    quad_ok.inputs["B"].default_value = 0.5
    ndg_ok = b.N("FunctionNodeCompare", (850, -2100), data_type="FLOAT", operation="GREATER_EQUAL")
    b.L(ndg, ndg_ok.inputs["A"])
    ndg_ok.inputs["B"].default_value = 0.5
    sz_w = b.N("FunctionNodeCompare", (850, -2220), data_type="FLOAT", operation="GREATER_EQUAL")
    b.L(nrw, sz_w.inputs["A"])
    # v2.4.1: Min Roof Face Size is WORLD meters -> compare world extents
    # (vm_rw runs along vm_ru, vm_rh along vm_rv; named-attr reads are safe in
    # this selection context per the evaluation-context contract)
    def ws_region_eff(name, y):
        nv = b.N("GeometryNodeInputNamedAttribute", (450, y))
        nv.data_type = "FLOAT_VECTOR"
        nv.inputs["Name"].default_value = name
        return ws["eff_of"](nv.outputs["Attribute"], (650, y))
    eff_ru_q = ws_region_eff("vm_ru", -2220)
    eff_rv_q = ws_region_eff("vm_rv", -2340)
    mrs_w = b.N("ShaderNodeMath", (700, -2220), operation="DIVIDE")
    b.L(gi.outputs["Min Roof Face Size"], mrs_w.inputs[0])
    b.L(eff_ru_q, mrs_w.inputs[1])
    b.L(mrs_w.outputs["Value"], sz_w.inputs["B"])
    sz_h = b.N("FunctionNodeCompare", (850, -2340), data_type="FLOAT", operation="GREATER_EQUAL")
    b.L(nrh2, sz_h.inputs["A"])
    mrs_h = b.N("ShaderNodeMath", (700, -2400), operation="DIVIDE")
    b.L(gi.outputs["Min Roof Face Size"], mrs_h.inputs[0])
    b.L(eff_rv_q, mrs_h.inputs[1])
    b.L(mrs_h.outputs["Value"], sz_h.inputs["B"])
    q1 = b.N("FunctionNodeBooleanMath", (1000, -1950), operation="AND")
    b.L(up.outputs["Boolean"], q1.inputs[0])
    b.L(quad_ok.outputs["Result"], q1.inputs[1])
    q2 = b.N("FunctionNodeBooleanMath", (1150, -2000), operation="AND")
    b.L(q1.outputs["Boolean"], q2.inputs[0])
    b.L(ndg_ok.outputs["Result"], q2.inputs[1])
    q3 = b.N("FunctionNodeBooleanMath", (1300, -2050), operation="AND")
    b.L(q2.outputs["Boolean"], q3.inputs[0])
    b.L(sz_w.outputs["Result"], q3.inputs[1])
    qual = b.N("FunctionNodeBooleanMath", (1450, -2100), operation="AND")
    b.L(q3.outputs["Boolean"], qual.inputs[0])
    b.L(sz_h.outputs["Result"], qual.inputs[1])

    # Largest Face Only: keep the single largest qualifying region
    area = m("MULTIPLY", nrw, nrh2, loc=(1000, -2450))
    stat = b.N("GeometryNodeAttributeStatistic", (1150, -2450))
    stat.data_type = "FLOAT"
    stat.domain = "FACE"
    b.L(store_chain, stat.inputs["Geometry"])
    b.L(qual.outputs["Boolean"], stat.inputs["Selection"])
    b.L(area, stat.inputs["Attribute"])
    big = b.N("FunctionNodeCompare", (1300, -2450), data_type="FLOAT", operation="GREATER_EQUAL")
    b.L(area, big.inputs["A"])
    b.L(m("SUBTRACT", stat.outputs["Max"], 1e-5, loc=(1250, -2600)), big.inputs["B"])
    keep_big = b.N("FunctionNodeBooleanMath", (1450, -2350), operation="AND")
    b.L(qual.outputs["Boolean"], keep_big.inputs[0])
    b.L(big.outputs["Result"], keep_big.inputs[1])
    fsel_sw = b.N("GeometryNodeSwitch", (1600, -2250))
    fsel_sw.input_type = "BOOLEAN"
    b.L(gi.outputs["Largest Face Only"], fsel_sw.inputs["Switch"])
    b.L(qual.outputs["Boolean"], fsel_sw.inputs["False"])
    b.L(keep_big.outputs["Boolean"], fsel_sw.inputs["True"])
    final_sel = fsel_sw.outputs["Output"]

    # ---- v2.6 Style 'Flat' + COMPLETE COVERAGE fallback ----------------------
    # In 'Flat' style NO gable is ever invented: every up-facing top gets a
    # near-flat cap (subtle incline + thin fascia). In Gable/Hip style every top
    # that cannot take a gable cleanly (non-quad, undersized, Largest-Face-Only
    # losers, Flat mode) gets a FLAT CAP instead of being skipped - a skipped
    # region used to leave a HOLE exposing the interior (the user's bug).
    # NOTE: exactly ONE Menu Switch may consume a menu interface socket (two
    # switches empty the socket's enum in Blender 5.2) - the flat flag comes
    # from the switch's per-item bool output; the value inputs are linked below.
    style_sw = b.N("GeometryNodeMenuSwitch", (1700, -2550))
    style_sw.data_type = "FLOAT"
    # v2.9.1: a new Menu Switch starts with items 'A'/'B' - they leaked into
    # the Style menu as two meaningless choices (found via the MCP input probe)
    style_sw.enum_items.clear()
    for _it in ("Gable", "Hip", "Flat"):
        style_sw.enum_items.new(_it)
    b.L(gi.outputs["Style"], style_sw.inputs["Menu"])
    flat_mode = style_sw.outputs["Flat"]
    not_flat = b.N("FunctionNodeBooleanMath", (1850, -2550), operation="NOT")
    b.L(flat_mode, not_flat.inputs[0])
    gable_sel = b.N("FunctionNodeBooleanMath", (2000, -2450), operation="AND")
    b.L(final_sel, gable_sel.inputs[0])
    b.L(not_flat.outputs["Boolean"], gable_sel.inputs[1])
    gable_not = b.N("FunctionNodeBooleanMath", (2000, -2650), operation="NOT")
    b.L(gable_sel.outputs["Boolean"], gable_not.inputs[0])
    # ---- v2.8 CONE selection: Style 'Hip' on a NON-QUAD top (a cylinder's
    # round n-gon top) generates a CONE ('Hip' = ridge shortened by half the
    # short side -> a round top's ridge shrinks to the apex). Everything else
    # unresolvable keeps the v2.6 flat-cap complete coverage.
    hip_b = style_sw.outputs["Hip"]
    nq_lo = b.N("FunctionNodeCompare", (2250, -2800), data_type="FLOAT",
                operation="LESS_THAN")
    b.L(nq, nq_lo.inputs["A"])
    nq_lo.inputs["B"].default_value = 0.5
    cone_q1 = b.N("FunctionNodeBooleanMath", (2400, -2800), operation="AND")
    b.L(up.outputs["Boolean"], cone_q1.inputs[0])
    b.L(nq_lo.outputs["Result"], cone_q1.inputs[1])
    cone_q2 = b.N("FunctionNodeBooleanMath", (2550, -2800), operation="AND")
    b.L(cone_q1.outputs["Boolean"], cone_q2.inputs[0])
    b.L(ndg_ok.outputs["Result"], cone_q2.inputs[1])
    cone_q3 = b.N("FunctionNodeBooleanMath", (2700, -2800), operation="AND")
    b.L(cone_q2.outputs["Boolean"], cone_q3.inputs[0])
    b.L(sz_w.outputs["Result"], cone_q3.inputs[1])
    cone_q4 = b.N("FunctionNodeBooleanMath", (2850, -2800), operation="AND")
    b.L(cone_q3.outputs["Boolean"], cone_q4.inputs[0])
    b.L(sz_h.outputs["Result"], cone_q4.inputs[1])
    cone_q5 = b.N("FunctionNodeBooleanMath", (3000, -2800), operation="AND")
    b.L(cone_q4.outputs["Boolean"], cone_q5.inputs[0])
    b.L(hip_b, cone_q5.inputs[1])
    lfo_not = b.N("FunctionNodeBooleanMath", (3000, -2950), operation="NOT")
    b.L(gi.outputs["Largest Face Only"], lfo_not.inputs[0])
    lfo_ok = b.N("FunctionNodeBooleanMath", (3150, -2900), operation="OR")
    b.L(lfo_not.outputs["Boolean"], lfo_ok.inputs[0])
    b.L(big.outputs["Result"], lfo_ok.inputs[1])
    cone_sel = b.N("FunctionNodeBooleanMath", (3300, -2800), operation="AND")
    b.L(cone_q5.outputs["Boolean"], cone_sel.inputs[0])
    b.L(lfo_ok.outputs["Boolean"], cone_sel.inputs[1])
    cone_not = b.N("FunctionNodeBooleanMath", (3450, -2800), operation="NOT")
    b.L(cone_sel.outputs["Boolean"], cone_not.inputs[0])
    cap_sel0 = b.N("FunctionNodeBooleanMath", (2150, -2650), operation="AND")
    b.L(up.outputs["Boolean"], cap_sel0.inputs[0])
    b.L(gable_not.outputs["Boolean"], cap_sel0.inputs[1])
    cap_sel = b.N("FunctionNodeBooleanMath", (2300, -2650), operation="AND")
    b.L(cap_sel0.outputs["Boolean"], cap_sel.inputs[0])
    b.L(cone_not.outputs["Boolean"], cap_sel.inputs[1])

    m2p = b.N("GeometryNodeMeshToPoints", (1750, -1500))
    m2p.mode = "FACES"
    b.L(store_chain, m2p.inputs["Mesh"])
    b.L(gable_sel.outputs["Boolean"], m2p.inputs["Selection"])

    iop = b.N("GeometryNodeInstanceOnPoints", (1150, -1500))
    b.L(m2p.outputs["Points"], iop.inputs["Points"])
    b.L(template, iop.inputs["Instance"])
    real = b.N("GeometryNodeRealizeInstances", (1400, -1500))
    b.L(iop.outputs["Instances"], real.inputs["Geometry"])

    def named(name, dt="FLOAT"):
        n = b.N("GeometryNodeInputNamedAttribute", (1500, -1900 - 120 * named.counter))
        named.counter += 1
        n.data_type = dt
        n.inputs["Name"].default_value = name
        return n.outputs["Attribute"]
    named.counter = 0
    t_v = named("vm_t", "FLOAT_VECTOR")
    rc_v = named("vm_rc", "FLOAT_VECTOR")
    ru_v = named("vm_ru", "FLOAT_VECTOR")
    rv_v = named("vm_rv", "FLOAT_VECTOR")
    rw_v = named("vm_rw")
    rh_v = named("vm_rh")
    rz_v = named("vm_rz")
    tsep2 = b.N("ShaderNodeSeparateXYZ", (1900, -1900))
    b.L(t_v, tsep2.inputs["Vector"])

    # per-region geometry: eave half extents A/B, roof height, ridge half length
    # v2.4.1: Overhang is WORLD meters -> local = Overhang / eff along the axis
    def named_ws(name, y):
        n_ = b.N("GeometryNodeInputNamedAttribute", (1750, y))
        n_.data_type = "FLOAT_VECTOR"
        n_.inputs["Name"].default_value = name
        return ws["eff_of"](n_.outputs["Attribute"], (1750, y - 90))
    eff_ru = named_ws("vm_ru", -2100)
    eff_rv = named_ws("vm_rv", -2250)
    oh_u = m("DIVIDE", gi.outputs["Overhang"], eff_ru, loc=(1850, -2150))
    oh_v = m("DIVIDE", gi.outputs["Overhang"], eff_rv, loc=(1850, -2300))
    A = m("MULTIPLY_ADD", rw_v, 0.5, oh_u, loc=(1900, -2100))   # A = rw*0.5 + Overhang
    B = m("MULTIPLY_ADD", rh_v, 0.5, oh_v, loc=(1900, -2250))   # B = rh*0.5 + Overhang
    sin_p = m("SINE", gi.outputs["Pitch"], loc=(1900, -2400))
    cos_p = m("MAXIMUM", m("COSINE", gi.outputs["Pitch"], loc=(1900, -2520)), 0.01, loc=(2050, -2520))
    tan_p = m("DIVIDE", sin_p, cos_p, loc=(2200, -2450))
    # v2.4.1: Pitch is a WORLD angle -> world roof height = B_w * tan(Pitch),
    # stored back in local units (Hh = B * eff_rv * tan_p / sz)
    Hh = m("DIVIDE", m("MULTIPLY", m("MULTIPLY", B, eff_rv, loc=(2250, -2350)),
                       tan_p, loc=(2350, -2350)), sz_g, loc=(2450, -2350))
    ridge_hip = m("MAXIMUM", m("SUBTRACT", A, B, loc=(2100, -2700)), 0.0, loc=(2250, -2700))
    # (the single Style menu switch was created earlier - link its value inputs)
    b.L(A, style_sw.inputs["Gable"])
    b.L(ridge_hip, style_sw.inputs["Hip"])
    b.L(A, style_sw.inputs["Flat"])
    ridge_g = style_sw.outputs["Output"]
    # x scale per template point: eave -> A, ridge -> ridge length
    dxs = m("SUBTRACT", ridge_g, A, loc=(2550, -2650))
    xs = m("MULTIPLY_ADD", tsep2.outputs["Z"], dxs, A, loc=(2700, -2550))         # xs = tz*(ridge-A) + A
    xw = m("MULTIPLY", tsep2.outputs["X"], xs, loc=(2850, -2550))
    yw = m("MULTIPLY", tsep2.outputs["Y"], B, loc=(2850, -2700))
    eps_l = m("DIVIDE", EPS, sz_g, loc=(2600, -2960))   # v2.4.1: EPS is WORLD meters
    zs = m("MULTIPLY_ADD", tsep2.outputs["Z"], Hh,
           m("ADD", rz_v, eps_l, loc=(2700, -2900)), loc=(2850, -2850))             # zs = tz*Hh + (rz+eps)
    px = b.N("ShaderNodeVectorMath", (3000, -2500), operation="SCALE")
    b.L(ru_v, px.inputs[0]); b.L(xw, px.inputs["Scale"])
    py = b.N("ShaderNodeVectorMath", (3000, -2700), operation="SCALE")
    b.L(rv_v, py.inputs[0]); b.L(yw, py.inputs["Scale"])
    pxy = b.N("ShaderNodeVectorMath", (3150, -2600), operation="ADD")
    b.L(px.outputs["Vector"], pxy.inputs[0])
    b.L(py.outputs["Vector"], pxy.inputs[1])
    # the region center enters only in x/y - z comes exclusively from zs below
    rcsep = b.N("ShaderNodeSeparateXYZ", (3150, -3000))
    b.L(rc_v, rcsep.inputs["Vector"])
    rcxy = b.N("ShaderNodeCombineXYZ", (3300, -3000))
    b.L(rcsep.outputs["X"], rcxy.inputs["X"])
    b.L(rcsep.outputs["Y"], rcxy.inputs["Y"])
    pxyz = b.N("ShaderNodeVectorMath", (3450, -2600), operation="ADD")
    b.L(rcxy.outputs["Vector"], pxyz.inputs[0])
    b.L(pxy.outputs["Vector"], pxyz.inputs[1])
    zv = b.N("ShaderNodeCombineXYZ", (3300, -2850))
    b.L(zs, zv.inputs["Z"])
    pfinal = b.N("ShaderNodeVectorMath", (3600, -2700), operation="ADD")
    b.L(pxyz.outputs["Vector"], pfinal.inputs[0])
    b.L(zv.outputs["Vector"], pfinal.inputs[1])
    sp2 = b.N("GeometryNodeSetPosition", (3600, -1500))
    b.L(real.outputs["Geometry"], sp2.inputs["Geometry"])
    b.L(pfinal.outputs["Vector"], sp2.inputs["Position"])

    sel_all = b.N("FunctionNodeBooleanMath", (3600, -1750), operation="OR")
    sel_all.inputs[0].default_value = True
    sel_all.inputs[1].default_value = True
    dressed = material_gate(b, sp2.outputs["Geometry"], gi.outputs["Roof Material"],
                            sel_all.outputs["Boolean"], (3750, -1500))
    # mark generated faces so Fit (doors/windows) never anchors on gable ends
    st_rg = b.N("GeometryNodeStoreNamedAttribute", (3950, -1500), data_type="FLOAT", domain="FACE")
    b.L(dressed, st_rg.inputs["Geometry"])
    st_rg.inputs["Name"].default_value = "vm_roofgen"
    st_rg.inputs["Value"].default_value = 1.0

    # ---------------- v2.6 FLAT CAP branch ----------------
    # Every up-facing top WITHOUT a gable (and ALL tops in Flat style) gets a
    # near-flat cap: the face outline extruded up into a thin slab, tilted by
    # 'Incline' along the region's long axis, with a thin vertical fascia skirt
    # (both rings expanded about the region center by the overhang). Handles
    # quads AND n-gons/triangles (the user's extrusion leftovers) - coverage is
    # COMPLETE: no top is ever left open. vm_roofgen = 2 marks cap faces.
    cap_sep = b.N("GeometryNodeSeparateGeometry", (2300, -3200))
    cap_sep.domain = "FACE"
    b.L(store_chain, cap_sep.inputs["Geometry"])
    b.L(cap_sel.outputs["Boolean"], cap_sep.inputs["Selection"])
    # v2.9.1: connected cap faces (a top split into several coplanar faces)
    # share ONE region frame and extrude as ONE slab (see region_frame)
    cap_reg = region_frame(b, cap_sep.outputs["Selection"], (2300, -6400))
    cap_ex = b.N("GeometryNodeExtrudeMesh", (2500, -3200))
    cap_ex.mode = "FACES"
    b.L(cap_reg, cap_ex.inputs["Mesh"])
    cap_ex.inputs["Selection"].default_value = True
    cap_off = b.N("ShaderNodeCombineXYZ", (2500, -3350))
    cap_off.inputs["Z"].default_value = 1.0
    b.L(cap_off.outputs["Vector"], cap_ex.inputs["Offset"])
    cap_ex.inputs["Individual"].default_value = False
    cap_t = b.N("GeometryNodeInputNamedAttribute", (2300, -3500))
    cap_t.data_type = "FLOAT_VECTOR"
    cap_t.inputs["Name"].default_value = "vm_t"     # unused; kept for symmetry
    cap_rc = named("vm_rc", "FLOAT_VECTOR")
    cap_ru = named("vm_ru", "FLOAT_VECTOR")
    cap_rv = named("vm_rv", "FLOAT_VECTOR")
    cap_rw = named("vm_rw")
    cap_rh = named("vm_rh")
    cap_rz = named("vm_rz")
    cap_eff_ru = ws["eff_of"](cap_ru, (2300, -3700))
    cap_eff_rv = ws["eff_of"](cap_rv, (2300, -3850))
    # overhang expansion per axis (clamped so tiny fragments cannot explode)
    su_1 = m("DIVIDE", m("MULTIPLY", gi.outputs["Overhang"], 2.0, loc=(2500, -3600)),
             m("MAXIMUM", cap_rw, 0.001, loc=(2500, -3700)), loc=(2650, -3600))
    su_c = m("MINIMUM", m("ADD", 1.0, su_1, loc=(2800, -3600)), 2.0, loc=(2950, -3600))
    sv_1 = m("DIVIDE", m("MULTIPLY", gi.outputs["Overhang"], 2.0, loc=(2500, -3900)),
             m("MAXIMUM", cap_rh, 0.001, loc=(2500, -4000)), loc=(2650, -3900))
    sv_c = m("MINIMUM", m("ADD", 1.0, sv_1, loc=(2800, -3900)), 2.0, loc=(2950, -3900))
    cap_pos = b.N("GeometryNodeInputPosition", (2300, -4150))
    cap_d = b.N("ShaderNodeVectorMath", (2500, -4150), operation="SUBTRACT")
    b.L(cap_pos.outputs["Position"], cap_d.inputs[0])
    b.L(cap_rc, cap_d.inputs[1])
    cap_du = b.N("ShaderNodeVectorMath", (2650, -4150), operation="DOT_PRODUCT")
    b.L(cap_d.outputs["Vector"], cap_du.inputs[0])
    b.L(cap_ru, cap_du.inputs[1])
    cap_dv = b.N("ShaderNodeVectorMath", (2650, -4300), operation="DOT_PRODUCT")
    b.L(cap_d.outputs["Vector"], cap_dv.inputs[0])
    b.L(cap_rv, cap_dv.inputs[1])
    cap_au = m("MULTIPLY", m("SUBTRACT", su_c, 1.0, loc=(2800, -4150)),
               cap_du.outputs["Value"], loc=(2950, -4150))
    cap_av = m("MULTIPLY", m("SUBTRACT", sv_c, 1.0, loc=(2800, -4300)),
               cap_dv.outputs["Value"], loc=(2950, -4300))
    cap_uu = b.N("ShaderNodeVectorMath", (3100, -4150), operation="SCALE")
    b.L(cap_ru, cap_uu.inputs[0])
    b.L(cap_au, cap_uu.inputs["Scale"])
    cap_vv = b.N("ShaderNodeVectorMath", (3100, -4300), operation="SCALE")
    b.L(cap_rv, cap_vv.inputs[0])
    b.L(cap_av, cap_vv.inputs["Scale"])
    cap_pxy1 = b.N("ShaderNodeVectorMath", (3250, -4200), operation="ADD")
    b.L(cap_pos.outputs["Position"], cap_pxy1.inputs[0])
    b.L(cap_uu.outputs["Vector"], cap_pxy1.inputs[1])
    cap_pxy2 = b.N("ShaderNodeVectorMath", (3400, -4200), operation="ADD")
    b.L(cap_pxy1.outputs["Vector"], cap_pxy2.inputs[0])
    b.L(cap_vv.outputs["Vector"], cap_pxy2.inputs[1])
    # subtle incline along the long axis (world angle) + fascia height.
    # The tilt is computed on the EXPANDED coordinate so the FINAL cap plane
    # (after the overhang expansion above) has exactly the requested incline.
    sin_i = m("SINE", gi.outputs["Incline"], loc=(2500, -4500))
    cos_i = m("MAXIMUM", m("COSINE", gi.outputs["Incline"], loc=(2500, -4620)), 0.01,
              loc=(2650, -4620))
    tan_i = m("DIVIDE", sin_i, cos_i, loc=(2800, -4550))
    du_exp = m("MULTIPLY", cap_du.outputs["Value"], su_c, loc=(2800, -4450))
    cap_dz = m("DIVIDE", m("MULTIPLY", m("MULTIPLY", tan_i, du_exp,
                                         loc=(2950, -4500)), cap_eff_ru, loc=(3100, -4500)),
               sz_g, loc=(3250, -4500))
    tilt_amp = m("DIVIDE", m("MULTIPLY", m("MULTIPLY", tan_i,
                                           m("MULTIPLY", m("MULTIPLY", cap_rw, su_c, loc=(2850, -4700)),
                                            0.5, loc=(2950, -4700)),
                                           loc=(3100, -4700)), cap_eff_ru, loc=(3250, -4700)),
                 sz_g, loc=(3400, -4700))
    fascia_l = m("DIVIDE", gi.outputs["Fascia"], sz_g, loc=(2950, -4850))
    fascia_eff = m("MAXIMUM", fascia_l,
                   m("ADD", tilt_amp, m("DIVIDE", 0.03, sz_g, loc=(3100, -4950)),
                     loc=(3250, -4850)), loc=(3400, -4850))
    cap_raise_top = m("ADD", fascia_eff, cap_dz, loc=(3550, -4600))
    cap_raise = b.N("GeometryNodeSwitch", (3700, -4500))
    cap_raise.input_type = "FLOAT"
    b.L(cap_ex.outputs["Top"], cap_raise.inputs["Switch"])
    cap_raise.inputs["False"].default_value = 0.0
    b.L(cap_raise_top, cap_raise.inputs["True"])
    cap_psep = b.N("ShaderNodeSeparateXYZ", (3550, -4200))
    b.L(cap_pxy2.outputs["Vector"], cap_psep.inputs["Vector"])
    cap_zbase = b.N("ShaderNodeMath", (3850, -4400), operation="ADD")
    b.L(cap_rz, cap_zbase.inputs[0])
    b.L(cap_raise.outputs["Output"], cap_zbase.inputs[1])
    cap_zsw = b.N("GeometryNodeSwitch", (4000, -4300))
    cap_zsw.input_type = "FLOAT"
    b.L(cap_ex.outputs["Top"], cap_zsw.inputs["Switch"])
    b.L(cap_psep.outputs["Z"], cap_zsw.inputs["False"])
    b.L(cap_zbase.outputs["Value"], cap_zsw.inputs["True"])
    cap_final = b.N("ShaderNodeCombineXYZ", (4150, -4250))
    b.L(cap_psep.outputs["X"], cap_final.inputs["X"])
    b.L(cap_psep.outputs["Y"], cap_final.inputs["Y"])
    b.L(cap_zsw.outputs["Output"], cap_final.inputs["Z"])
    cap_sp = b.N("GeometryNodeSetPosition", (4300, -3200))
    b.L(cap_ex.outputs["Mesh"], cap_sp.inputs["Geometry"])
    b.L(cap_final.outputs["Vector"], cap_sp.inputs["Position"])
    cap_dressed = material_gate(b, cap_sp.outputs["Geometry"], gi.outputs["Roof Material"],
                                sel_all.outputs["Boolean"], (4450, -3200))
    st_cap = b.N("GeometryNodeStoreNamedAttribute", (4600, -3200), data_type="FLOAT", domain="FACE")
    b.L(cap_dressed, st_cap.inputs["Geometry"])
    st_cap.inputs["Name"].default_value = "vm_roofgen"
    st_cap.inputs["Value"].default_value = 2.0

    # ---- v2.8 CONE branch (Style 'Hip' on a round/cylindrical top): the face
    # outline extruded up, the top ring pulled to 2% of the outline about the
    # region centre (a tiny n-gon apex - clean quads, never degenerate spikes)
    # and raised by the hip height (half the short side + overhang) * tan(Pitch)
    # -> the cone-like cap. vm_roofgen = 3 marks cone faces.
    cone_sep = b.N("GeometryNodeSeparateGeometry", (2300, -5200))
    cone_sep.domain = "FACE"
    b.L(store_chain, cone_sep.inputs["Geometry"])
    b.L(cone_sel.outputs["Boolean"], cone_sep.inputs["Selection"])
    cone_ex = b.N("GeometryNodeExtrudeMesh", (2500, -5200))
    cone_ex.mode = "FACES"
    b.L(cone_sep.outputs["Selection"], cone_ex.inputs["Mesh"])
    cone_ex.inputs["Selection"].default_value = True
    cone_off = b.N("ShaderNodeCombineXYZ", (2500, -5350))
    cone_off.inputs["Z"].default_value = 1.0
    b.L(cone_off.outputs["Vector"], cone_ex.inputs["Offset"])
    cone_ex.inputs["Individual"].default_value = True
    ct_au = m("SUBTRACT", m("MULTIPLY", m("MULTIPLY", cap_du.outputs["Value"], su_c,
                                          loc=(4700, -5150)), 0.02, loc=(4850, -5150)),
              cap_du.outputs["Value"], loc=(5000, -5150))
    ct_av = m("SUBTRACT", m("MULTIPLY", m("MULTIPLY", cap_dv.outputs["Value"], sv_c,
                                          loc=(4700, -5300)), 0.02, loc=(4850, -5300)),
              cap_dv.outputs["Value"], loc=(5000, -5300))
    c_au = b.N("GeometryNodeSwitch", (5150, -5150))
    c_au.input_type = "FLOAT"
    b.L(cone_ex.outputs["Top"], c_au.inputs["Switch"])
    b.L(cap_au, c_au.inputs["False"])
    b.L(ct_au, c_au.inputs["True"])
    c_av = b.N("GeometryNodeSwitch", (5150, -5300))
    c_av.input_type = "FLOAT"
    b.L(cone_ex.outputs["Top"], c_av.inputs["Switch"])
    b.L(cap_av, c_av.inputs["False"])
    b.L(ct_av, c_av.inputs["True"])
    c_uu = b.N("ShaderNodeVectorMath", (5300, -5150), operation="SCALE")
    b.L(cap_ru, c_uu.inputs[0])
    b.L(c_au.outputs["Output"], c_uu.inputs["Scale"])
    c_vv = b.N("ShaderNodeVectorMath", (5300, -5300), operation="SCALE")
    b.L(cap_rv, c_vv.inputs[0])
    b.L(c_av.outputs["Output"], c_vv.inputs["Scale"])
    c_p1 = b.N("ShaderNodeVectorMath", (5450, -5200), operation="ADD")
    b.L(cap_pos.outputs["Position"], c_p1.inputs[0])
    b.L(c_uu.outputs["Vector"], c_p1.inputs[1])
    c_p2 = b.N("ShaderNodeVectorMath", (5600, -5200), operation="ADD")
    b.L(c_p1.outputs["Vector"], c_p2.inputs[0])
    b.L(c_vv.outputs["Vector"], c_p2.inputs[1])
    c_sep2 = b.N("ShaderNodeSeparateXYZ", (5750, -5200))
    b.L(c_p2.outputs["Vector"], c_sep2.inputs["Vector"])
    c_ztop = m("ADD", cap_rz, m("ADD", Hh, eps_l, loc=(5750, -5400)), loc=(5900, -5400))
    c_zsw = b.N("GeometryNodeSwitch", (6050, -5250))
    c_zsw.input_type = "FLOAT"
    b.L(cone_ex.outputs["Top"], c_zsw.inputs["Switch"])
    b.L(c_sep2.outputs["Z"], c_zsw.inputs["False"])
    b.L(c_ztop, c_zsw.inputs["True"])
    c_fin = b.N("ShaderNodeCombineXYZ", (6200, -5250))
    b.L(c_sep2.outputs["X"], c_fin.inputs["X"])
    b.L(c_sep2.outputs["Y"], c_fin.inputs["Y"])
    b.L(c_zsw.outputs["Output"], c_fin.inputs["Z"])
    cone_sp = b.N("GeometryNodeSetPosition", (6350, -5200))
    b.L(cone_ex.outputs["Mesh"], cone_sp.inputs["Geometry"])
    b.L(c_fin.outputs["Vector"], cone_sp.inputs["Position"])
    cone_dressed = material_gate(b, cone_sp.outputs["Geometry"], gi.outputs["Roof Material"],
                                 sel_all.outputs["Boolean"], (6500, -5200))
    st_cone = b.N("GeometryNodeStoreNamedAttribute", (6650, -5200), data_type="FLOAT",
                  domain="FACE")
    b.L(cone_dressed, st_cone.inputs["Geometry"])
    st_cone.inputs["Name"].default_value = "vm_roofgen"
    st_cone.inputs["Value"].default_value = 3.0

    join = b.N("GeometryNodeJoinGeometry", (4800, -1300))
    b.L(gi.outputs["Geometry"], join.inputs["Geometry"])
    b.L(st_rg.outputs["Geometry"], join.inputs["Geometry"])
    b.L(st_cap.outputs["Geometry"], join.inputs["Geometry"])
    b.L(st_cone.outputs["Geometry"], join.inputs["Geometry"])
    b.L(join.outputs["Geometry"], go.inputs["Geometry"])

    # ---- v2.7 About panel (appended LAST -> v2.5/v2.6 identifiers unchanged,
    # then moved to the top of the interface) ----
    p_about = b.panel("About", f"Engine version + quick usage ({ENGINE_VERSION}): tells you exactly which code this modifier runs")
    b.sock("Engine Version", "NodeSocketString", p_about, f"{ENGINE_VERSION}",
           desc=f"Version of the VM engine code behind this modifier ({ENGINE_VERSION}). If this "
                "panel/socket is missing the stack runs a PRE-v2.8 group - see USAGE.txt "
                "'Which version am I running?' and 'Upgrading old stacks'")
    b.sock("Usage Hint", "NodeSocketString", p_about,
           f"{ENGINE_VERSION} quick use: a fresh VM_RoofCap caps flat tops with a subtle 2.5 deg incline "
           "(Style 'Gable'/'Hip' = opt-in pitch - gables are NEVER invented on flat tops; "
           "'Hip' on a square top = pyramid, on a round/cylindrical top = CONE). "
           "Old stack? See USAGE.txt 'Which version am I running?'.",
           desc="One-line usage reminder")

    b.finish_menu_defaults()
    b.ng.description = (
        f"VM_RoofCap {ENGINE_VERSION} - per-region roof caps over flat tops: Style 'Flat' (DEFAULT: "
        "subtle 2.5 deg incline + fascia, NEVER invented gable triangles) / 'Gable' / 'Hip' "
        "(opt-in pitch; hip on a square top = pyramid, on a round top = cone). The About "
        f"panel shows the Engine Version socket ('{ENGINE_VERSION}'). Which "
        "code does my stack run / how do I upgrade? See USAGE.txt 'Which version am I running?'")
    try:
        b.iface.move(p_about, 0)
    except Exception as e:
        log(f"  !! About panel move failed: {e}")
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
    plane_normals = []
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
        # v2.4.1: the TRUE world plane normal of the instance's face (X/Z span) -
        # cross(col2, col0) = +Y axis transformed by the inverse-transpose, so
        # unlike col1 it is not sheared by a non-uniform object scale
        cx_, cz_ = m.col[0], m.col[2]
        px_, py_, pz_ = (cz_.y * cx_.z - cz_.z * cx_.y,
                         cz_.z * cx_.x - cz_.x * cx_.z,
                         cz_.x * cx_.y - cz_.y * cx_.x)
        pl = max((px_ * px_ + py_ * py_ + pz_ * pz_) ** 0.5, 1e-9)
        plane_normals.append((round(px_ / pl, 3), round(py_ / pl, 3), round(pz_ / pl, 3)))
    host_verts = len(host.data.vertices)
    return dict(n_instances=n_inst, instance_verts=inst_verts, host_verts=host_verts,
                total_verts=host_verts + inst_verts, freq=dict(freq),
                distinct_scales=len(scales), distinct_yaws=len(yaws),
                positions=positions, rotations=rotations, updots=updots, normals=normals,
                plane_normals=plane_normals, named_positions=named_positions)


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
        # v2.4.1: 'np' = TRUE world plane normal of the instance's face span
        # (cross of its X/Z axes). cross(col0, col2) transforms by the inverse
        # transpose, so unlike col1 it is not sheared by a non-uniform object
        # scale - use it whenever the SURFACE orientation matters (zone bands).
        c0 = Vector((m.col[0].x, m.col[0].y, m.col[0].z))
        c2 = Vector((m.col[2].x, m.col[2].y, m.col[2].z))
        # NOTE: cross(col2, col0) = the +Y (depth/outward) axis transformed by
        # the inverse transpose - see the plane-normal comment in eval_stats
        boxes.append(dict(name=ob.name, lo=lo, hi=hi, org=m.translation.copy(),
                          n=Vector(m.col[1]).normalized(), np=c2.cross(c0).normalized()))
    return boxes


def host_planes(host):
    # BASE WALL planes from the host's original mesh verts - object.bound_box
    # reflects evaluated geometry (roof/instances) and would skew the planes
    bpy.context.view_layer.update()
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


def expected_courses(mesh_ob, zone_test, slot_w, overlap, row_h, skip_generated=False):
    """Independent Python re-implementation of the cladding row/slot formula,
    per face, for cross-checking the GN output. zone_test(normal, center) -> bool.
    Uses the EVALUATED mesh so VM_RoofCap-generated faces are included; pass
    skip_generated=True for layers that run BEFORE VM_RoofCap (they can never
    clad generated faces). v2.4.1: socket values are WORLD meters - mirrors the
    node group's world-space sizing (per-direction |S . axis| factors of the
    object's unapplied scale, identity-gated exactly like the node group)."""
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    me = mesh_ob.evaluated_get(dg).data
    has_rg = "vm_roofgen" in me.attributes
    total = 0
    per_face = []
    sp = max(slot_w * (1.0 - overlap), 0.001)
    _sc = mesh_ob.matrix_world.to_scale()
    _S = (abs(_sc.x), abs(_sc.y), abs(_sc.z))
    _ident = _S == (1.0, 1.0, 1.0)

    def eff_of(u):
        if _ident:
            return 1.0
        return max(((_S[0] * u.x) ** 2 + (_S[1] * u.y) ** 2 + (_S[2] * u.z) ** 2) ** 0.5, 1e-5)

    for p in me.polygons:
        if skip_generated and has_rg and me.attributes["vm_roofgen"].data[p.index].value > 0.5:
            continue
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
        # epsilon guards exact float boundaries (2.2/0.22 = 10.000...2 -> 11 rows;
        # evaluated mesh coords are float32 so the guard must exceed ~1e-7 noise)
        ns = max(1, math.ceil(W / (sp / eff_of(u)) - 1e-6))
        nr = max(1, math.ceil(H / (max(row_h, 0.001) / eff_of(v)) - 1e-6))
        per_face.append(dict(face=p.index, W=round(W, 3), H=round(H, 3), slots=ns, rows=nr, total=ns * nr))
        total += ns * nr
    return total, per_face


# ---------------------------------------------------------------------------- v2.4 shape matrix
def make_compound(name, col):
    """User's L-shaped STEPPED compound (extruded-cube workflow): tall block +
    lower wide wing sharing a corner, concave inner corner, two flat tops at
    different heights. Clean quads the way an edit-mode extrusion leaves them."""
    verts = [
        (0, 0, 0), (2, 0, 0), (5, 0, 0), (5, 1.2, 0), (2, 1.2, 0), (2, 2, 0), (0, 2, 0),
        (0, 0, 3.2), (2, 0, 3.2), (2, 2, 3.2), (0, 2, 3.2),
        (2, 0, 1.2), (5, 0, 1.2), (5, 1.2, 1.2), (2, 1.2, 1.2),
        (2, 1.2, 3.2),        # step wall A top-back corner (T-junction on the tall top)
    ]
    faces = [
        (0, 1, 5, 6),        # bottom (tall)
        (1, 2, 3, 4),        # bottom (wing)
        (0, 1, 8, 7),        # south tall wall  2.0w x 3.2h, base z=0
        (1, 2, 12, 11),      # south wing wall  3.0w x 1.2h, base z=0 (fragment)
        (0, 6, 10, 7),       # west tall wall   2.0w x 3.2h, base z=0
        (6, 5, 9, 10),       # north tall wall  2.0w x 3.2h, base z=0
        (11, 14, 15, 8),     # step wall A      1.2w x 2.0h, base z=1.2  <- per-face demo
        (4, 5, 9, 15),       # step wall B      0.8w x 3.2h, base z=0    (width fragment)
        (2, 3, 13, 12),      # wing east wall   1.2w x 1.2h, base z=0    (fragment)
        (3, 4, 14, 13),      # wing north wall  3.0w x 1.2h, base z=0    (fragment)
        (11, 12, 13, 14),    # wing top deck    3.0 x 1.2 flat, z=1.2    (roof region 2)
        (7, 8, 9, 10),       # tall top         2.0 x 2.0 flat, z=3.2    (roof region 1)
    ]
    return new_mesh_obj(name, verts, faces, col)


def make_tower_wing(name, col):
    """Tower + lower wing (multi-height, concave corners) + two unresolved roof
    regions on the wing deck: a triangular prism (non-quad top -> clean skip)
    and a tiny 0.3m quad block (below Min Roof Face Size -> clean skip)."""
    verts = [
        (0, 0, 0), (1.6, 0, 0), (4.6, 0, 0), (4.6, 1.2, 0), (1.6, 1.2, 0), (1.6, 1.6, 0), (0, 1.6, 0),
        (0, 0, 3.2), (1.6, 0, 3.2), (1.6, 1.6, 3.2), (0, 1.6, 3.2),
        (1.6, 0, 1.4), (4.6, 0, 1.4), (4.6, 1.2, 1.4), (1.6, 1.2, 1.4),
        (1.6, 1.2, 3.2),      # step wall top-back corner (T-junction on the tower top)
        # penthouse 1: triangular prism (top is a TRIANGLE -> RoofCap skips it)
        (2.2, 0.35, 1.35), (2.75, 0.35, 1.35), (2.475, 0.9, 1.35),
        (2.2, 0.35, 1.8), (2.75, 0.35, 1.8), (2.475, 0.9, 1.8),
        # penthouse 2: tiny 0.3 x 0.3 quad block (below Min Roof Face Size)
        (3.3, 0.4, 1.35), (3.6, 0.4, 1.35), (3.6, 0.7, 1.35), (3.3, 0.7, 1.35),
        (3.3, 0.4, 1.7), (3.6, 0.4, 1.7), (3.6, 0.7, 1.7), (3.3, 0.7, 1.7),
    ]
    faces = [
        (0, 1, 5, 6), (1, 2, 3, 4),
        (0, 1, 8, 7),        # tower south 1.6w x 3.2h, base 0
        (1, 2, 12, 11),      # wing south 3.0w x 1.4h, base 0 (below door height filter)
        (0, 6, 10, 7),       # tower west 1.6w x 3.2h, base 0
        (6, 5, 9, 10),       # tower north 1.6w x 3.2h, base 0
        (11, 14, 15, 8),     # step wall 1.2w x 1.8h, base z=1.4 <- per-face demo
        (4, 5, 9, 15),       # tower east lower strip 0.4w (width fragment)
        (2, 3, 13, 12),      # wing east 1.2w x 1.4h (fragment)
        (3, 4, 14, 13),      # wing north 3.0w x 1.4h (fragment)
        (11, 12, 13, 14),    # wing deck 3.0 x 1.4 flat (roof region)
        (7, 8, 9, 10),       # tower top 1.6 x 1.6 flat (roof region)
        (16, 17, 18),        # penthouse 1 bottom (triangle)
        (19, 20, 21),        # penthouse 1 top (TRIANGLE -> unresolved roof region)
        (16, 17, 20, 19), (17, 18, 21, 20), (18, 16, 19, 21),
        (22, 23, 24, 25),    # penthouse 2 bottom
        (26, 27, 28, 29),    # penthouse 2 top (0.3 x 0.3 -> below min roof size)
        (22, 23, 27, 26), (23, 24, 28, 27), (24, 25, 29, 28), (25, 22, 26, 29),
    ]
    return new_mesh_obj(name, verts, faces, col)


def make_warehouse(name, col):
    """Wide low warehouse box: one huge flat top -> one long gable."""
    verts = [(x, y, z) for z in (0.0, 2.2) for y in (0.0, 3.5) for x in (0.0, 6.0)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return new_mesh_obj(name, verts, faces, col)


def make_bug_repro(name, col):
    """The USER's exact bug shape (2026-10-21 screenshot): a tower + long low
    wing with a mono-pitched shed roof sloping down away from the tower. Two
    authentic extrusion-leftover defects are built in on purpose:
      (1) the tower wall strip above the shed's HIGH edge - its base edge sits
          ON the wing's roof surface, so v2.5-pre Fit put a DOOR standing on
          the wing roof (the reported roof-door bug);
      (2) the tower's south wall is a manual TRIANGLE FAN around an interior
          vertex with ONE triangle wound INWARD (a flipped fill - exactly what
          an extrude/fill leaves behind). v2.5-pre cladding swallowed that
          triangle's tiles inside the wall and z-fought its coplanar backs,
          leaving a bare triangle that renders BLACK in the viewport (the
          reported black-triangle artifact).
    All windings are hand-computed OUTWARD except the deliberate flip."""
    verts = [
        (0, 0, 0), (2.2, 0, 0), (7.2, 0, 0), (7.2, 2.2, 0), (2.2, 2.2, 0), (0, 2.2, 0),
        (0, 0, 3.6), (2.2, 0, 3.6), (2.2, 2.2, 3.6), (0, 2.2, 3.6),
        (2.2, 0, 1.9), (7.2, 0, 1.15), (7.2, 2.2, 1.15), (2.2, 2.2, 1.9),
        (1.1, 0.0, 2.2),        # fan center on the tower south wall
    ]
    faces = [
        (0, 5, 4, 1),           # bottom tall (-Z)
        (1, 4, 3, 2),           # bottom wing (-Z)
        (0, 6, 9, 5),           # tower west (-X)
        (5, 9, 8, 4),           # tower north (+Y)
        (1, 4, 13, 10),         # tower east BELOW the shed line (+X)
        (7, 10, 13, 8),         # tower east strip ABOVE (+X): base ON the shed roof
        (1, 2, 11, 10),         # wing south (-Y)
        (4, 13, 12, 3),         # wing north (+Y)
        (2, 3, 12, 11),         # wing east (+X)
        (10, 11, 12, 13),       # shed roof (up, slope band, shingled)
        (6, 7, 8, 9),           # tower top (up) -> VM_RoofCap gable region
        # tower south wall as a TRIANGLE FAN (extrusion-leftover fill):
        (0, 1, 14), (1, 7, 14), (6, 7, 14), (6, 0, 14),
    ]
    # face (6, 7, 14) is deliberately wound INWARD (the flipped fill defect) -
    # NO recalc here: the hand-computed windings are already outward except that
    # one triangle, and recalc_face_normals would silently "fix" the defect
    return new_mesh_obj(name, verts, faces, col, recalc=False)


def make_wide_wall(name, col, length):
    """Wide wall rig for the Slots acceptance: `length` x 2.0 x 4.5 box - one
    long face for wall-length-derived opening counts and multi-row sills."""
    verts = [(x, y, z) for z in (0.0, 4.5) for y in (0.0, 2.0) for x in (0.0, length)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return new_mesh_obj(name, verts, faces, col)


# ---------------------------------------------------------------- v2.6 UserShape2
# The USER's custom shape (2026-10-22 screenshots): blocky stepped massing -
# tall back-left tower + lower-left wing + small front annex + upper-right
# block + its step, ALL TOPS FLAT at stepped heights. Rebuilt at the exact
# proportions AND scale measured from his screenshots (floor grid squares +
# shingle-tile size): overall ~2.67 x 2.0 m footprint, tallest wall exactly
# 2.0 m - SMALLER than the 2.1-2.2 m default/demo 'Opening Height', which is
# what killed every Fit opening (see STAGE 7 root-cause evidence). Topology is
# the authentic extrusion result: merged boxes, quad walls, shared corner verts
# (T-junctions where steps meet), partially-occluded junction faces kept.
U2_BLOCKS = [
    # (x0, x1, y0, y1, z0, z1)  - meters, 1 screenshot unit = 2/3 m
    (0.0, 4 / 3, 2 / 3, 2.0, 0.0, 2.0),        # tower BL   (tallest)
    (0.0, 4 / 3, 0.0, 2 / 3, 0.0, 4 / 3),      # wing FL
    (4 / 3, 8 / 3, 4 / 3, 2.0, 0.0, 1.8),      # block BR   (upper right)
    (2.0, 8 / 3, 2 / 3, 4 / 3, 0.0, 1.0),      # step MRS
    (2.0, 8 / 3, 0.0, 2 / 3, 0.0, 2 / 3),      # annex FR   (front right)
]

def make_user_shape2(name, col):
    verts, faces = [], []
    for (x0, x1, y0, y1, z0, z1) in U2_BLOCKS:
        off = len(verts)
        verts += [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                  (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        faces += [tuple(i + off for i in fc)
                  for fc in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
                             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.to_mesh(me)
    bm.free()
    me.update()
    return ob

# ---------------------------------------------------------------- v2.8 UserShape3
# THE USER'S OWN HAND-BUILT MASSING (found in the delivered VM_Starter.blend as
# 'Cube.001', saved 2026-10-22 22:48): a small porch block at the south, a main
# box + east wing, and a hand-built gable-ish protrusion on top. Rebuilt VERBATIM
# (all 104 verts / 81 faces incl. the duplicated verts, the zero-area fill quads
# and the gable-end TRIANGLE - the defects that triggered the v2.8 bugs are kept
# on purpose so the fixes are proven against the real topology). The companion
# stray 'Cube' he left in the scene is preserved too.
USER3_V = [
    (-1.77503, -1.963124, -1.370318), (-1.77503, -1.963124, 1.370318),
    (-1.77503, 1.963124, -1.370318), (-1.77503, 1.963124, 1.370318),
    (1.77503, -1.963124, -1.370318), (1.77503, -1.963124, 1.370318),
    (1.77503, 1.963124, -1.370318), (1.77503, 1.963124, 1.370318),
    (-1.77503, -1.963124, 4.348815), (-1.77503, 1.963124, 4.348815),
    (1.77503, 1.963124, 4.348815), (1.77503, -1.963124, 4.348815),
    (-1.77503, -1.963124, 7.350567), (-1.77503, 1.963124, 7.350567),
    (1.77503, 1.963124, 7.350567), (1.77503, -1.963124, 7.350567),
    (5.108193, 1.963124, 1.370318), (5.108193, 1.963124, -1.370318),
    (5.108193, -1.963124, -1.370318), (5.108193, -1.963124, 1.370318),
    (1.77503, 1.963124, 4.306543), (1.77503, -1.963124, 4.306543),
    (5.108193, 1.963124, 4.306543), (5.108193, -1.963124, 4.306543),
    (-1.77503, -1.963124, -1.370318), (-1.77503, -1.963124, 1.370318),
    (1.77503, -1.963124, 1.370318), (1.77503, -1.963124, -1.370318),
    (1.77503, -1.963124, 4.348815), (-1.77503, -1.963124, 4.348815),
    (5.108193, -1.963124, 1.370318), (5.108193, -1.963124, -1.370318),
    (1.77503, 1.963124, 4.306543), (1.77503, -1.963124, 4.306543),
    (5.108193, 1.963124, 4.306543), (5.108193, -1.963124, 4.306543),
    (-1.77503, -5.461065, -1.370318), (-1.77503, -5.461065, 1.370318),
    (1.77503, -5.461065, 1.370318), (1.77503, -5.461065, -1.370318),
    (1.77503, -5.461065, 4.348815), (-1.77503, -5.461065, 4.348815),
    (5.108193, -5.461065, 1.370318), (5.108193, -5.461065, -1.370318),
    (1.77503, -5.461065, 4.306543), (5.108193, -5.461065, 4.306543),
    (1.77503, -5.461065, 4.334264), (1.77503, -1.963124, 4.334264),
    (5.108193, -1.963124, 4.334264), (5.108193, -5.461065, 4.334264),
    (-1.77503, -1.963124, 7.350567), (1.77503, -1.963124, 7.350567),
    (-1.77503, -1.963124, 7.350567), (1.77503, -1.963124, 7.350567),
    (-1.77503, 1.963124, 7.350567), (1.77503, 1.963124, 7.350567),
    (0.665753, -1.963124, 7.350567), (0.665753, -1.963124, 7.350567),
    (1.77503, -0.084793, 7.350567), (1.77503, -0.084793, 7.350567),
    (1.77503, -1.963124, 7.350567), (1.77503, -1.963124, 4.348815),
    (1.77503, -0.084793, 7.350567), (1.77503, -1.963124, 7.350567),
    (1.77503, -1.963124, 4.348815), (1.77503, -0.084793, 7.350567),
    (1.77503, -1.963124, 7.350567), (1.77503, -1.963124, 4.348815),
    (-1.721385, -1.963124, 4.348815), (-1.721385, 1.963124, 4.348815),
    (-1.77503, -1.963124, 7.350567), (1.77503, -1.963124, 7.350567),
    (-1.721385, -0.084793, 7.350567), (1.683069, -0.084793, 7.350567),
    (1.683069, 1.963124, 4.348815), (1.683069, -1.963124, 4.348815),
    (5.108193, -1.963124, 1.370318), (5.108193, -1.963124, 4.306543),
    (5.108193, -5.461065, 1.370318), (5.108193, -5.461065, 4.306543),
    (5.108193, 1.963124, 1.370318), (5.108193, -1.963124, 1.370318),
    (5.108193, 1.963124, 4.306543), (5.108193, -1.963124, 4.306543),
    (5.108193, 1.963124, 1.370318), (5.108193, -1.963124, 1.370318),
    (5.108193, 1.963124, 4.306543), (5.108193, -1.963124, 4.306543),
    (5.108193, 1.963124, 1.370318), (5.108193, -1.963124, 1.370318),
    (5.108193, 1.963124, 4.306543), (5.108193, -1.963124, 4.306543),
    (5.108193, 1.963124, 1.370318), (5.108193, -1.963124, 1.370318),
    (5.108193, 1.963124, 4.306543), (5.108193, -1.963124, 4.306543),
    (5.108193, -1.963124, 1.370318), (5.108193, -1.963124, 4.306543),
    (5.108193, -5.461065, 1.370318), (5.108193, -5.461065, 4.306543),
    (8.054026, -1.963124, 1.370318), (8.054026, -1.963124, 4.306543),
    (8.054026, -5.461065, 1.370318), (8.054026, -5.461065, 4.306543),
    (-1.77503, -8.368889, -1.370318), (-1.77503, -8.368889, 1.370318),
    (1.77503, -8.368889, 1.370318), (1.77503, -8.368889, -1.370318),
]
USER3_F = [
    (0, 1, 3, 2), (2, 3, 7, 6), (83, 82, 34, 77), (81, 83, 77, 76), (2, 6, 4, 0),
    (5, 7, 10, 11), (3, 1, 8, 9), (20, 21, 33, 32), (7, 3, 9, 10), (11, 58, 59, 61),
    (17, 80, 81, 18), (6, 7, 80, 17), (82, 20, 32, 34), (4, 6, 17, 18), (11, 8, 29, 28),
    (7, 5, 21, 20), (19, 16, 22, 23), (80, 7, 20, 82), (24, 27, 39, 36), (79, 77, 48, 49),
    (26, 28, 40, 38), (33, 26, 38, 44), (32, 33, 77, 34), (0, 4, 27, 24), (5, 11, 28, 26),
    (21, 5, 26, 33), (18, 81, 76, 31), (1, 0, 24, 25), (8, 1, 25, 29), (4, 18, 31, 27),
    (38, 78, 79, 44), (36, 39, 103, 100), (37, 38, 40, 41), (38, 39, 43, 78),
    (27, 31, 43, 39), (29, 25, 37, 41), (25, 24, 36, 37), (31, 76, 78, 43),
    (42, 30, 96, 98), (28, 29, 41, 40), (48, 47, 46, 49), (33, 44, 46, 47),
    (77, 33, 47, 48), (44, 79, 49, 46), (72, 68, 75, 73), (61, 59, 62, 64),
    (10, 58, 72, 69), (68, 69, 74, 75), (58, 11, 68, 72), (64, 62, 65, 67),
    (11, 10, 69, 68), (73, 75, 74), (69, 72, 73, 74), (93, 92, 76, 77), (94, 95, 79, 78),
    (95, 93, 77, 79), (92, 94, 78, 76), (84, 85, 81, 80), (87, 86, 82, 83),
    (85, 87, 83, 81), (86, 84, 80, 82), (88, 89, 85, 84), (91, 90, 86, 87),
    (89, 91, 87, 85), (90, 88, 84, 86), (16, 19, 89, 88), (23, 22, 90, 91),
    (19, 23, 91, 89), (22, 16, 88, 90), (35, 30, 92, 93), (42, 45, 95, 94),
    (45, 35, 93, 95), (30, 42, 94, 92), (96, 97, 99, 98), (45, 42, 98, 99),
    (35, 45, 99, 97), (30, 35, 97, 96), (103, 102, 101, 100), (37, 36, 100, 101),
    (38, 37, 101, 102), (39, 38, 102, 103),
]
USER3_LOC = (19.218236923217773, -16.399208068847656, 1.3703184127807617)


def make_user_massing(name, col):
    """The user's own hand-built massing, byte-for-byte topology (no normal
    recalc: the flipped fill quads and duplicated verts are part of the test)."""
    me = bpy.data.meshes.new(name)
    me.from_pydata(USER3_V, [], [list(f) for f in USER3_F])
    me.update()
    ob = bpy.data.objects.new(name, me)
    ob.location = USER3_LOC
    col.objects.link(ob)
    return ob


def make_user_stray_cube(name, col):
    """The stray edit-mode cube he left parked in the scene (kept verbatim)."""
    vs = [(-3.31, -2.558, -1.911), (-3.31, -2.558, 1.911), (-3.31, 2.558, -1.911),
          (-3.31, 2.558, 1.911), (3.31, -2.558, -1.911), (3.31, -2.558, 1.911),
          (3.31, 2.558, -1.911), (3.31, 2.558, 1.911)]
    fs = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 2, 6, 4), (1, 5, 7, 3), (0, 4, 5, 1), (2, 3, 7, 6)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(vs, [], fs)
    me.update()
    ob = bpy.data.objects.new(name, me)
    ob.location = (11.258859634399414, 25.926729202270508, 1.911123275756836)
    col.objects.link(ob)
    return ob


# ---------------------------------------------------------------- v2.8 helpers
def _poly2d(mesh_ob):
    """Per-face (normal, center, canonical u, v, polygon2d, W, H) in LOCAL space
    - mirrors the engine's face frame (canonical +Y tangent)."""
    out = []
    me = mesh_ob.data
    for p in me.polygons:
        vs = [me.vertices[i].co.copy() for i in p.vertices]
        c = sum(vs, Vector((0, 0, 0))) / len(vs)
        n = p.normal.copy()
        if n.length < 1e-6:
            n = Vector((0, 0, 1))
        n.normalize()
        if abs(n.z) > 0.995:
            u = Vector((1, 0, 0))
        else:
            u = Vector((0, 0, 1)).cross(n).normalized()
            if u.y < -1e-6 or (abs(u.y) <= 1e-6 and u.x < 0):
                u = -u
        v = n.cross(u).normalized()
        rel = [w - c for w in vs]
        aa = [r.dot(u) for r in rel]
        bb = [r.dot(v) for r in rel]
        out.append(dict(idx=p.index, n=n, c=c, u=u, v=v,
                        poly=list(zip(aa, bb)), W=max(aa) - min(aa),
                        H=max(bb) - min(bb), alo=min(aa), blo=min(bb), area=p.area))
    return out


def _pt_in_poly(pt, poly):
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            if x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                inside = not inside
    return inside


def inst_table(host, prefixes):
    """[(prefix, world_anchor, world_lo, world_hi)] for evaluated instances."""
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    rows = []
    for inst in dg.object_instances:
        if not inst.is_instance or inst.parent is None:
            continue
        par = inst.parent
        if not (par == host or getattr(par, "original", None) == host):
            continue
        nm = inst.object.name
        pre = next((p for p in prefixes if nm.startswith(p)), None)
        if pre is None:
            continue
        m = inst.matrix_world
        cs = [m @ Vector(c) for c in inst.object.bound_box]
        lo = Vector((min(c.x for c in cs), min(c.y for c in cs), min(c.z for c in cs)))
        hi = Vector((max(c.x for c in cs), max(c.y for c in cs), max(c.z for c in cs)))
        rows.append((pre, m.translation.copy(), lo, hi))
    return rows


def containment_check(host, prefixes, eps=0.001):
    """(n_off_surface, details): cladding instances whose ANCHOR floats free of
    the surface they were laid on (the v2.8 phantom-wall-slab contract).

    The pass criterion is SURFACE ATTACHMENT: the anchor must lie within `eps`
    (local units) of the evaluated mesh being clad - the host faces PLUS any
    real geometry earlier modifiers generated (VM_RoofCap slopes legitimately
    carry shingles). Measured with Blender's own closest-point kernel, which is
    the same geometry truth the engine's Proximity gate uses.

    The v2.8.1 planar projected-polygon test is still computed for diagnostics
    only: it false-positives on strongly non-planar sliver quads (the user's
    extrusion leftovers) where an anchor sits ON the triangulated surface but
    outside the projected planar polygon - and it false-positives on every
    shingle laid on a generated cap face."""
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    ev = host.evaluated_get(dg)
    mwi = host.matrix_world.inverted()
    faces = _poly2d(host)
    off_surface, strict = [], []
    for (pre, org, lo, hi) in inst_table(host, prefixes):
        lp = mwi @ Vector(org)
        hit, loc, nrm, fidx = ev.closest_point_on_mesh(lp, depsgraph=dg)
        dist = (lp - loc).length if hit else 1e9
        strict_hit = False
        for f in faces:
            d = abs((lp - f["c"]).dot(f["n"]))
            if d > 0.05:
                continue
            rel = (lp - f["n"] * ((lp - f["c"]).dot(f["n"]))) - f["c"]
            if _pt_in_poly((rel.dot(f["u"]), rel.dot(f["v"])), f["poly"]):
                strict_hit = True
                break
        if not strict_hit:
            strict.append((pre, tuple(round(x, 3) for x in org), round(dist, 5)))
        if dist > eps:
            off_surface.append((pre, tuple(round(x, 3) for x in org), round(dist, 5)))
    return len(off_surface), dict(
        off_surface=off_surface, tol=eps,
        strict_planar_outside=len(strict), strict_planar=strict[:20])


def opening_spread(host):
    """walls used + per-plane counts + pairwise bbox intersections for openings."""
    faces = _poly2d(host)
    mwi = host.matrix_world.inverted()
    rows = inst_table(host, ("Door", "Window"))
    per_plane = Counter()
    plane_of = {}
    for i, (pre, org, lo, hi) in enumerate(rows):
        lp = mwi @ Vector(org)
        best = None
        for f in faces:
            d = (lp - f["c"]).dot(f["n"])
            if abs(d) > 0.3:
                continue
            rel = (lp - f["n"] * d) - f["c"]
            if _pt_in_poly((rel.dot(f["u"]), rel.dot(f["v"])), f["poly"]):
                key = f["idx"]
                if best is None or abs(d) < abs(best[1]):
                    best = (key, d)
        if best is not None:
            # v2.8.2: balance is counted per WALL FACE (the user's mesh wall
            # segments), not per merged plane - his hand-built massing carries
            # several wall faces 5-7 m apart on one plane, and merging them
            # made one 'wall' look crowded while each segment was balanced
            per_plane[best[0]] += 1
            plane_of[i] = best[0]
    inter = 0
    min_gap = 1e9
    pairs = 0
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            a, b = rows[i], rows[j]
            gap = max(max(a[2][k] - b[3][k], b[2][k] - a[3][k]) for k in range(3))
            min_gap = min(min_gap, gap)
            pairs += 1
            if gap <= 0:
                inter += 1
    counts = sorted(per_plane.values())
    return dict(total=len(rows), walls=len(per_plane), per_wall=dict(per_plane),
                intersections=inter, pairs=pairs, min_gap=round(min_gap, 4),
                spread_diff=(max(counts) - min(counts)) if counts else -1)

# The USER's exact action on StarterCube (2026-10-22 confusion report): he
# DUPLICATED StarterCube and extruded/stepped it into a tower + lower wing +
# annex compound. This is the authentic extrusion result: CLEAN exterior
# topology the way edit-mode extrusions leave it (the wall behind an extruded
# mass is not a face of the host any more - exactly like make_compound's step
# walls), with one genuine edit-mode extrusion step on the tower top (+0.35 m)
# after the copy. Massing heights are deliberate: only the TOWER walls can
# legally receive openings (wing/annex walls are shorter than the door layer's
# 'Min Face Height' 1.2, the tower's step wall above the wing is shorter than
# the window layer's 'Min Face Height' 1.5) - openings can never end up hidden
# inside the massing or sticking out above a short wall.
STAGE_COMPOUND_BLOCKS = [
    # interior volumes (x0, x1, y0, y1, z0, z1) - local meters, base z=0
    (-1.0, 1.0, -1.0, 1.0, 0.0, 2.55),       # tower (tallest)
    (1.0, 2.95, -1.0, 1.0, 0.0, 1.15),       # lower wing
    (1.0, 2.2, 1.0, 1.9, 0.0, 0.8),          # small front annex
]
STAGE_COMPOUND_EXTRUDE = 0.35                 # the user's last extrude/step


def build_compound_mesh(me):
    """Write the tower+lower-wing+annex compound into mesh datablock `me`
    (clean exterior massing + genuine bmesh extrude step on the tower top)."""
    P = {  # shared corner points (T-junctions where the steps meet)
        "T0": (-1, -1, 0), "T1": (1, -1, 0), "T2": (1, 1, 0), "T3": (-1, 1, 0),
        "T4": (-1, -1, 2.2), "T5": (1, -1, 2.2), "T6": (1, 1, 2.2), "T7": (-1, 1, 2.2),
        "W2": (2.95, -1, 0), "W3": (2.95, 1, 0),
        "A1": (1, -1, 1.15), "A2": (2.95, -1, 1.15), "A3": (2.95, 1, 1.15), "A4": (1, 1, 1.15),
        "N2": (2.2, 1, 0), "N3": (2.2, 1.9, 0), "N4": (1, 1.9, 0),
        "N5": (1, 1, 0.8), "N6": (2.2, 1, 0.8), "N7": (2.2, 1.9, 0.8), "N8": (1, 1.9, 0.8),
        "M": (2.2, 1, 1.15),                   # T-junction on the wing's north top edge
    }
    order = ["T0", "T1", "T2", "T3", "T4", "T5", "T6", "T7",
             "W2", "W3", "A1", "A2", "A3", "A4",
             "N2", "N3", "N4", "N5", "N6", "N7", "N8", "M"]
    idx = {k: i for i, k in enumerate(order)}
    verts = [P[k] for k in order]
    F = [
        ("T0", "T3", "T2", "T1"),        # tower bottom
        ("T1", "T2", "W3", "W2"),        # wing bottom
        ("T2", "N4", "N3", "N2"),        # annex bottom
        ("T4", "T5", "T6", "T7"),        # tower top
        ("A1", "A2", "A3", "A4"),        # wing top deck
        ("N5", "N6", "N7", "N8"),        # annex top
        ("T0", "T1", "T5", "T4"),        # tower south wall  3.0w x 2.55h (ground)
        ("T2", "T6", "T7", "T3"),        # tower north wall  3.0w x 2.55h (ground)
        ("T0", "T4", "T7", "T3"),        # tower west wall   2.0w x 2.55h (ground)
        ("A1", "T5", "T6", "A4"),        # tower east STEP wall 3.0w x 1.4h, base 1.15
        ("T1", "W2", "A2", "A1"),        # wing south wall   1.95w x 1.15h (too short for openings)
        ("W2", "W3", "A3", "A2"),        # wing east wall    2.0w x 1.15h
        ("N2", "W3", "A3", "M"),         # wing north wall (right of the annex) 0.75w x 1.15h
        ("N5", "N6", "M", "A4"),         # wing north wall (above the annex)    1.2w x 0.35h
        ("N4", "N3", "N7", "N8"),        # annex north wall  1.2w x 0.8h
        ("N2", "N3", "N7", "N6"),        # annex east wall   1.2w x 0.8h
        ("T2", "N4", "N8", "N5"),        # annex west wall   1.2w x 0.8h (flush with the tower plane)
        # annex south wall (against the wing) + wing west wall (against the
        # tower) are INTERNAL - edit-mode extrusions leave no face there
    ]
    faces = [tuple(idx[k] for k in fc) for fc in F]
    me.clear_geometry()
    me.from_pydata(verts, [], faces)
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()
    # the LAST edit-mode step, literally: extrude the tower top region upward
    bm = bmesh.new()
    bm.from_mesh(me)
    top = max(bm.faces, key=lambda f: f.calc_center_median().z)
    res = bmesh.ops.extrude_face_region(bm, geom=[top])
    new_verts = [el for el in res["geom"] if isinstance(el, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=new_verts, vec=(0, 0, STAGE_COMPOUND_EXTRUDE))
    bm.to_mesh(me)
    bm.free()
    me.update()
    return me


def point_in_blocks(p, blocks, eps=1e-4):
    for (x0, x1, y0, y1, z0, z1) in blocks:
        if (x0 + eps < p.x < x1 - eps and y0 + eps < p.y < y1 - eps
                and z0 + eps < p.z < z1 - eps):
            return True
    return False


def face_is_exterior(f, mw_inv, blocks):
    """True when the modeled face's surface really faces OUT of the block massing
    (the merged-block topology keeps a few hidden internal faces - openings must
    never be placed on those)."""
    c = mw_inv @ Vector(f["c"])
    n = (mw_inv.to_3x3() @ Vector(f["n"])).normalized()
    return not point_in_blocks(c + n * 0.06, blocks)


def opening_is_exterior(box, mw_inv, blocks):
    """The OPENING's own placement point must face out of the massing. A wall
    face can be half-hidden behind a lower wing (the tower's east wall above
    the wing reads exterior at its CENTER while a LOW opening on it is buried
    inside the wing) - so openings are tested at their own origin."""
    n = Vector((box["n"][0], box["n"][1], box["n"][2])).normalized()
    p = mw_inv @ (Vector(box["org"]) + n * 0.06)
    return not point_in_blocks(p, blocks)


def paint_slot_group(ob, group_name, face_selector):
    """Manual-placement demo: weight-paint a VERTEX GROUP on the faces selected
    by face_selector(face) -> bool (Blender-native weight painting; the user
    paints this in Weight Paint mode on his own mesh)."""
    vg = ob.vertex_groups.new(name=group_name)
    me = ob.data
    idxs = set()
    for p in me.polygons:
        if face_selector(p):
            idxs.update(p.vertices)
    vg.add(list(idxs), 1.0, "REPLACE")
    return sorted(idxs)


def face_table(host):
    """World-space data for every face of the BASE mesh (what the user modeled)."""
    # matrix_world is stale until the depsgraph updates - a fresh object placed at
    # (0,-60) would otherwise report LOCAL face coords against WORLD instance boxes
    bpy.context.view_layer.update()
    mw = host.matrix_world
    nmat = mw.to_3x3().inverted().transposed()
    wverts = [mw @ Vector(v.co) for v in host.data.vertices]
    bvh = BVHTree.FromPolygons(wverts, [tuple(p.vertices) for p in host.data.polygons])
    out = []
    for p in host.data.polygons:
        vs = [wverts[i] for i in p.vertices]
        c = sum(vs, Vector((0, 0, 0))) / len(vs)
        n = (nmat @ Vector(p.normal)).normalized()
        # v2.9 Python mirror of exterior_face_field: first hit along the normal
        # is the BACK of another face -> the face is buried inside the solid
        hit, hn, _, _ = bvh.ray_cast(c + n * 0.001, n, 10000.0)
        buried = (hit is not None and hn.dot(n) > 1e-4) or p.area <= 1e-6
        if abs(n.z) > 0.995:
            u = Vector((1, 0, 0))
        else:
            u = Vector((0, 0, 1)).cross(n).normalized()
        v = n.cross(u).normalized()
        aa = [(w - c).dot(u) for w in vs]
        bb = [(w - c).dot(v) for w in vs]
        out.append(dict(idx=p.index, n=n, c=c, u=u, v=v,
                        min_z=min(w.z for w in vs), max_z=max(w.z for w in vs),
                        w=max(aa) - min(aa), h=max(bb) - min(bb),
                        quad=len(vs) == 4, buried=buried))
    return out


def match_face(faces, n, org, box=None):
    """The modeled face an instance was placed against: same normal, smallest
    plane distance, tie-broken by whether the instance lies inside the face's
    tangent bounds (co-planar faces like step wall A/B must not steal each
    other's instances) and by how much of the instance BOX falls inside the
    face's height range (a door standing on the shared bottom edge of two
    coplanar stacked faces belongs to the UPPER face - its body lives there).
    (inst_boxes normals come from a 4x4 matrix column - keep only xyz.)"""
    nv = Vector((n[0], n[1], n[2])).normalized()
    org = Vector(org)
    best, best_score, best_d = None, 1e9, 1e9
    for f in faces:
        if (Vector(f["n"]) - nv).length > 0.25:
            continue
        d = abs((org - f["c"]).dot(f["n"]))
        du = abs((org - f["c"]).dot(f["u"]))
        dv = abs((org - f["c"]).dot(f["v"]))
        outside = max(0.0, du - (f["w"] / 2.0 + 0.6)) + max(0.0, dv - (f["h"] / 2.0 + 0.6))
        tight = du / max(f["w"], 0.2) + dv / max(f["h"], 0.2)   # coplanar tie-break
        contain = 0.0
        if box is not None:
            lo_z, hi_z = min(box["lo"].z, box["hi"].z), max(box["lo"].z, box["hi"].z)
            ov = max(0.0, min(hi_z, f["max_z"]) - max(lo_z, f["min_z"]))
            frac = ov / max(hi_z - lo_z, 1e-6)
            contain = 0.3 * (1.0 - frac)
        score = d + 10.0 * outside + 0.01 * tight + contain
        if score < best_score:
            best, best_score, best_d = f, score, d
    return best, best_d


def roof_report(host, min_size=0.4, largest_only=False, overhang=0.25,
                pitch=math.radians(35.0), eps=0.002, style="Gable", incline=math.radians(2.5),
                fascia=0.12):
    """Per-region roof truth from the base mesh + evaluated RoofCap output:
    qualifying regions, gable-skipped regions (with reasons), generated gable
    faces, flat-cap faces (v2.6 coverage fallback), strays (generated faces
    outside every region envelope), zero-area faces and UNCOVERED top faces.

    v2.6 contract: vm_roofgen = 1 marks gable/hup faces, = 2 marks FLAT CAP
    faces. Skipped-for-gable regions are FLAT-CAPPED (never left open), so a
    'skipped' entry means 'no gable', not 'no roof' - coverage completeness is
    reported by 'uncovered' (must stay empty)."""
    faces = face_table(host)
    up_faces = [f for f in faces if f["n"].z >= 0.98 and not f["buried"]]
    qual, skipped = [], []
    for f in up_faces:
        if not f["quad"]:
            skipped.append(dict(idx=f["idx"], reason="non-quad top"))
            continue
        if min(f["w"], f["h"]) < min_size:
            skipped.append(dict(idx=f["idx"], reason="below Min Roof Face Size"))
            continue
        qual.append(f)
    if largest_only and qual:
        qual.sort(key=lambda f: f["w"] * f["h"], reverse=True)
        skipped += [dict(idx=f["idx"], reason="Largest Face Only") for f in qual[1:]]
        qual = qual[:1]
    gable_regions = qual if style != "Flat" else []
    cap_regions = [f for f in up_faces if f not in gable_regions]

    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    me = host.evaluated_get(dg).data
    mw = host.matrix_world
    nmat = mw.to_3x3().inverted().transposed()
    has_rg = "vm_roofgen" in me.attributes
    rg_faces, cap_faces, cap_tops, zero_area, strays = 0, 0, 0, [], []
    gen_pts = []
    for p in me.polygons:
        if p.area < 1e-9:
            zero_area.append(p.index)
        rval = me.attributes["vm_roofgen"].data[p.index].value if has_rg else 0.0
        gen = rval > 0.5
        if rval > 0.5 and rval < 1.5:
            rg_faces += 1
        elif rval >= 1.5:
            cap_faces += 1
        n = (nmat @ Vector(p.normal)).normalized()
        if rval >= 1.5 and n.z >= 0.98:
            cap_tops += 1
        if n.z <= 0.55 or not gen:
            continue            # stray test covers GENERATED faces only (host
                                # tops are the user's own mesh, never our garbage)
        vs = [mw @ Vector(me.vertices[i].co) for i in p.vertices]
        c = sum(vs, Vector((0, 0, 0))) / len(vs)
        gen_pts.append((c, n, rval))
        ok = False
        check_regions = gable_regions if rval < 1.5 else up_faces
        for f in check_regions:
            b = (f["h"] / 2.0 + overhang) * math.tan(pitch) + fascia + 1.0
            ex = f["w"] / 2.0 + overhang + 0.35
            ey = f["h"] / 2.0 + overhang + 0.35
            du = abs((c - f["c"]).dot(f["u"]))
            dv = abs((c - f["c"]).dot(f["v"]))
            if du <= ex and dv <= ey and (f["min_z"] - 0.05) <= c.z <= (f["min_z"] + eps + b):
                ok = True
                break
        if not ok:
            strays.append(dict(face=p.index, kind="cap" if rval >= 1.5 else "gable",
                               center=tuple(round(x, 3) for x in c)))

    # coverage: every up-facing host face must have generated geometry over it
    uncovered = []
    for f in up_faces:
        if f in gable_regions:
            continue            # gable sits on it by construction (verified by
                                # generated==expected below)
        ok = False
        for c, n, rval in gen_pts:
            du = abs((c - f["c"]).dot(f["u"]))
            dv = abs((c - f["c"]).dot(f["v"]))
            if du <= f["w"] / 2.0 + overhang + 0.35 and dv <= f["h"] / 2.0 + overhang + 0.35 \
               and c.z >= f["min_z"] - 0.05:
                ok = True
                break
        if not ok:
            uncovered.append(dict(idx=f["idx"], center=tuple(round(x, 3) for x in f["c"])))
    return dict(qualifying=len(gable_regions), generated=rg_faces,
                expected_generated=4 * len(gable_regions),
                caps=cap_faces, cap_tops=cap_tops, expected_caps=len(cap_regions),
                skipped=[dict(idx=s["idx"], reason=s["reason"]) for s in skipped],
                zero_area=len(zero_area), strays=strays, uncovered=uncovered,
                cap_regions=[dict(idx=f["idx"], min_z=round(f["min_z"], 4),
                                  w=round(f["w"], 3), h=round(f["h"], 3)) for f in cap_regions],
                regions=[dict(idx=f["idx"], min_z=round(f["min_z"], 4),
                              w=round(f["w"], 3), h=round(f["h"], 3)) for f in gable_regions])


def shape_accept(tag, host, door_sill=0.0, win_sill=0.9, tol=0.05,
                 door_face_w=1.0, door_face_h=1.6, win_face_w=1.5, win_face_h=1.5,
                 n_regions_expected=None, roof_style="Gable"):
    """Numeric acceptance for one dressed shape: per-face anchoring, face
    filters, sill heights, no underground/detached parts, roof regions vs
    clean skips, zero stray roof faces, flat tops un-shingled, cladding counts
    vs the independent course formula. Returns (results_dict, checks_list)."""
    out = []
    faces = face_table(host)
    lo_h, hi_h = host_planes(host)
    mw = host.matrix_world
    doors = inst_boxes(host, "Door_")
    wins = inst_boxes(host, "Window_")
    planks = inst_boxes(host, "Plank_")
    shingles = inst_boxes(host, "Shingle_")

    def anchoring(boxes, sill, kind):
        rows = []
        sill_w = sill          # v2.4.1: Sill Height is WORLD meters (contract)
        for bx in boxes:
            f, d = match_face(faces, bx["n"], bx["org"], bx)
            if f is None:
                rows.append(dict(name=bx["name"], face=None, ok=False))
                continue
            base = f["min_z"] + sill_w
            delta = bx["lo"].z - base
            rows.append(dict(name=bx["name"], face=f["idx"], face_base=round(f["min_z"], 4),
                             base_z=round(bx["lo"].z, 4), delta=round(delta, 5),
                             face_w=round(f["w"], 3), face_h=round(f["h"], 3),
                             back=round(d, 5), ok=abs(delta) <= tol))
        return rows

    d_rows = anchoring(doors, door_sill, "door")
    w_rows = anchoring(wins, win_sill, "window")
    d_ok = all(r["ok"] for r in d_rows) and len(d_rows) > 0
    w_ok = all(r["ok"] for r in w_rows) and len(w_rows) > 0
    out.append((f"shape[{tag}]: every door base == its OWN face base + sill (per-face anchoring)",
                d_ok, f"{len(d_rows)} doors, deltas={[r['delta'] for r in d_rows]}, "
                      f"face bases={[r['face_base'] for r in d_rows]}"))
    out.append((f"shape[{tag}]: every window base == its face base + {win_sill} (sill height)",
                w_ok, f"{len(w_rows)} windows, deltas={[r['delta'] for r in w_rows]}, "
                      f"face bases={[r['face_base'] for r in w_rows]}"))
    d_fil = all(r["face_w"] >= door_face_w - 1e-6 and r["face_h"] >= door_face_h - 1e-6 for r in d_rows) and len(d_rows) > 0
    w_fil = all(r["face_w"] >= win_face_w - 1e-6 and r["face_h"] >= win_face_h - 1e-6 for r in w_rows) and len(w_rows) > 0
    out.append((f"shape[{tag}]: doors only on faces >= {door_face_w}x{door_face_h} (Min Face filters)",
                d_fil, f"host faces used: {[(r['face'], r['face_w'], r['face_h']) for r in d_rows]}"))
    out.append((f"shape[{tag}]: windows only on substantial walls >= {win_face_w}x{win_face_h}",
                w_fil, f"host faces used: {[(r['face'], r['face_w'], r['face_h']) for r in w_rows]}"))

    # nothing underground / detached: every instance base sits at/above its face base
    all_boxes = [("Door_", doors, door_sill), ("Window_", wins, win_sill),
                 ("Plank_", planks, 0.0), ("Shingle_", shingles, 0.0)]
    buried = []
    for pre, boxes, sill in all_boxes:
        for bx in boxes:
            f, _ = match_face(faces, bx["n"], bx["org"], bx)
            ref = (f["min_z"] + sill - 0.06) if f else (lo_h.z - 0.06)
            if bx["lo"].z < ref:
                buried.append((bx["name"], round(bx["lo"].z, 3), round(ref, 3)))
    out.append((f"shape[{tag}]: zero underground/detached parts (all {len(doors)+len(wins)+len(planks)+len(shingles)} "
                f"instances at/above their face base)",
                not buried, f"buried={buried[:6]}"))

    # wall-contact contract (doors + windows): back plane at Backing Offset - Embed
    backs = [r["back"] for r in d_rows + w_rows if r.get("back") is not None]
    out.append((f"shape[{tag}]: doors/windows flush on their walls (back plane measured on every instance)",
                all(0.0 <= bk <= 0.12 for bk in backs) and len(backs) > 0,
                f"back distances {[round(bk, 5) for bk in backs]}"))

    # no interpenetration between fitted parts
    pairs = [("dd", doors[i], doors[j]) for i in range(len(doors)) for j in range(i + 1, len(doors))]
    pairs += [("ww", wins[i], wins[j]) for i in range(len(wins)) for j in range(i + 1, len(wins))]
    pairs += [("dw", d, w) for d in doors for w in wins]
    gaps = [aabb_gap(a, b) for _, a, b in pairs]
    bad = [(k, a["name"], b["name"], round(aabb_gap(a, b), 5))
           for k, a, b in pairs if aabb_gap(a, b) < 0]
    out.append((f"shape[{tag}]: zero door/window bbox intersections",
                all(g >= 0 for g in gaps) and (not gaps or min(gaps) >= 0),
                f"{len(gaps)} pairs, min gap={round(min(gaps), 5) if gaps else 99.0}, "
                f"bad={bad[:6]}"))

    # roof: per-region generation, clean skips, no stray triangles
    rr = roof_report(host, style=roof_style)
    out.append((f"shape[{tag}]: RoofCap emits exactly 4 clean faces per resolvable region (no garbage)",
                rr["generated"] == rr["expected_generated"] and rr["zero_area"] == 0,
                f"generated={rr['generated']} expected={rr['expected_generated']}, "
                f"zero-area faces={rr['zero_area']}, regions={rr['regions']}"))
    out.append((f"shape[{tag}]: zero stray roof faces (every roof face inside its region envelope)",
                not rr["strays"], f"strays={rr['strays'][:4]}"))
    # v2.6: COMPLETE COVERAGE - every top that cannot take a gable is FLAT-CAPPED
    # (previously skipped-and-left-open = the gaping-hole bug). 'skipped' now
    # means 'no gable', never 'no roof'; 'uncovered' must stay empty.
    out.append((f"shape[{tag}]: complete roof coverage - every up-facing top covered "
                f"(flat caps on all gable-skipped tops, zero holes)",
                not rr["uncovered"] and rr["cap_tops"] == rr["expected_caps"],
                f"cap tops={rr['cap_tops']} expected={rr['expected_caps']} "
                f"(cap regions={rr['cap_regions']}), uncovered={rr['uncovered']}"))
    if n_regions_expected is not None:
        out.append((f"shape[{tag}]: unresolved roof regions skipped cleanly and reported",
                    rr["qualifying"] == n_regions_expected[0] and len(rr["skipped"]) == n_regions_expected[1],
                    f"qualifying={rr['qualifying']} (expect {n_regions_expected[0]}), "
                    f"skipped={rr['skipped']} (expect {n_regions_expected[1]}), "
                    f"all skipped regions flat-capped (v2.6)"))

    # slope-band zones: flat tops un-shingled (v2.4.1: classify on the TRUE world
    # plane normal 'np' - col1 is sheared by a non-uniform object scale)
    flat_sh = [b["name"] for b in shingles if b["np"].z >= 0.92]
    band_sh = [b for b in shingles if 0.55 <= b["np"].z < 0.92]
    out.append((f"shape[{tag}]: flat tops un-shingled (slope-band Roof zone)",
                len(flat_sh) == 0 and (len(band_sh) == len(shingles)),
                f"{len(shingles)} shingles: {len(band_sh)} in slope band [0.55,0.92), {len(flat_sh)} on flats"))

    # cladding re-tiling cross-check vs the independent formula
    exp_sh, _ = expected_courses(host, lambda n, c: 0.55 <= n.z < 0.92, 0.25, 0.35, 0.11)
    exp_pl, _ = expected_courses(host, lambda n, c: abs(n.z) <= 0.35, 2.0, 0.05, 0.22,
                                 skip_generated=True)
    out.append((f"shape[{tag}]: shingle/plank counts match the independent course formula",
                len(shingles) == exp_sh and len(planks) == exp_pl,
                f"shingles {len(shingles)} (expected {exp_sh}), planks {len(planks)} (expected {exp_pl})"))

    res = dict(doors=d_rows, windows=w_rows, n_doors=len(doors), n_windows=len(wins),
               n_planks=len(planks), n_shingles=len(shingles),
               expected_shingles=exp_sh, expected_planks=exp_pl,
               roof=rr, buried=buried,
               # world AABB dims sorted (long, mid, short) per instance - the
               # v2.4.1 world-size measurements (tiles must not stretch)
               plank_dims=sorted(tuple(round(v, 4) for v in
                                       sorted((bx["hi"] - bx["lo"]), reverse=True))
                                 for bx in planks),
               shingle_dims=sorted(tuple(round(v, 4) for v in
                                         sorted((bx["hi"] - bx["lo"]), reverse=True))
                                   for bx in shingles),
               min_gap=round(min(gaps), 5) if gaps else 99.0)
    return res, out


def compound_accept(tag, ob):
    """v2.7 acceptance for the duplicated-StarterCube compound (the user's exact
    action: duplicate StarterCube, extrude/step it into a tower + lower wing +
    annex): doors/windows on the EXTERIOR ground walls, ZERO gable triangles on
    the flat tops, complete roof coverage. Returns (results_dict, checks_list)."""
    faces = face_table(ob)
    inv = ob.matrix_world.inverted()
    doors = inst_boxes(ob, "Door_")
    wins = inst_boxes(ob, "Window_")
    tops = [f for f in faces if f["n"].z >= 0.98]

    def rows(boxes):
        out = []
        for b in boxes:
            f, _ = match_face(faces, b["n"], b["org"], b)
            out.append(dict(name=b["name"],
                            exterior=bool(f and face_is_exterior(f, inv, STAGE_COMPOUND_BLOCKS)
                                          and opening_is_exterior(b, inv, STAGE_COMPOUND_BLOCKS)),
                            face_base=round(f["min_z"], 4) if f else None,
                            base_z=round(b["lo"].z, 4),
                            height=round(b["hi"].z - b["lo"].z, 4),
                            face_h=round(f["h"], 4) if f else None))
        return out

    drows, wrows = rows(doors), rows(wins)
    out = []
    ground_ok = (len(drows) >= 1 and len(wrows) >= 1
                 and all(r["exterior"] and r["face_base"] is not None and r["face_base"] <= 0.06
                         and abs(r["base_z"]) <= 0.06 for r in drows)
                 and all(r["exterior"] and r["face_base"] is not None and r["face_base"] <= 0.06
                         and 0.25 <= r["base_z"] <= 1.05 for r in wrows))
    out.append((f"compound[{tag}]: doors AND windows on the EXTERIOR ground walls of the "
                f"tower+wing+annex edit (the copied stack survives the user's exact action)",
                ground_ok,
                f"{len(drows)} doors {[(r['name'], r['base_z'], r['face_base'], r['exterior']) for r in drows]}, "
                f"{len(wrows)} windows {[(r['name'], r['base_z'], r['face_base'], r['exterior']) for r in wrows]}"))
    rr = roof_report(ob, style="Flat")
    out.append((f"compound[{tag}]: ZERO gable triangles on the flat tops (saved Style 'Flat' "
                f"rides along with the duplicate) + COMPLETE roof coverage",
                rr["generated"] == 0 and rr["cap_tops"] == rr["expected_caps"] == len(tops)
                and not rr["uncovered"] and not rr["strays"] and rr["zero_area"] == 0,
                f"gable faces={rr['generated']} (expected 0), cap tops={rr['cap_tops']} "
                f"(expected {rr['expected_caps']}, host tops={len(tops)}), "
                f"uncovered={rr['uncovered']}, strays={rr['strays']}"))
    exp_pl, _ = expected_courses(ob, lambda n, c: abs(n.z) <= 0.35, 2.0, 0.05, 0.22,
                                 skip_generated=True)
    n_pl = len(inst_boxes(ob, "Plank_"))
    out.append((f"compound[{tag}]: cladding re-tiles the edited massing (plank count matches "
                f"the independent course formula)",
                n_pl == exp_pl and n_pl > 0, f"planks {n_pl} (formula {exp_pl})"))
    res = dict(n_doors=len(doors), n_windows=len(wins), doors=drows, windows=wrows,
               n_planks=n_pl, expected_planks=exp_pl,
               n_shingles=len(inst_boxes(ob, "Shingle_")), roof=rr, top_faces=len(tops))
    return res, out


def gable_showcase_accept(tag, ob):
    """v2.7 GableShowcase: the pitched style is OPT-IN and still works."""
    rr = roof_report(ob, style="Gable")
    sh = inst_boxes(ob, "Shingle_")
    exp, _ = expected_courses(ob, lambda n, c: 0.55 <= n.z < 0.92, 0.25, 0.35, 0.11)
    doors = inst_boxes(ob, "Door_")
    wins = inst_boxes(ob, "Window_")
    out = [(f"gable_showcase[{tag}]: Style 'Gable' OPTED IN generates the pitched roof "
            f"(4 clean faces for the region, zero strays, coverage complete)",
            rr["qualifying"] >= 1 and rr["generated"] == rr["expected_generated"] == 4
            and rr["zero_area"] == 0 and not rr["strays"] and not rr["uncovered"],
            f"qualifying={rr['qualifying']}, generated={rr['generated']} "
            f"(expected {rr['expected_generated']}), strays={rr['strays']}, "
            f"uncovered={rr['uncovered']}"),
           (f"gable_showcase[{tag}]: shingles clad the pitched slopes (course formula match)",
            len(sh) == exp and len(sh) > 0,
            f"{len(sh)} shingles (formula {exp}) in the slope band"),
           (f"gable_showcase[{tag}]: openings still present on the pitched twin",
            len(doors) + len(wins) >= 1,
            f"{len(doors)} doors, {len(wins)} windows")]
    return dict(roof=rr, n_shingles=len(sh), expected_shingles=exp,
                n_doors=len(doors), n_windows=len(wins)), out


def reflow_edit(host, scale=(1.5, 1.0, 1.4), extrude_z=0.6):
    """Live-edit semantics: edit the BASE MESH after the engine stack is on,
    exactly like edit mode - non-uniform scale + one more extrusion step."""
    me = host.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.scale(bm, vec=scale, verts=bm.verts)
    top = max(bm.faces, key=lambda f: (f.calc_center_median().z, f.index))
    res = bmesh.ops.extrude_face_region(bm, geom=[top])
    new_verts = [el for el in res["geom"] if isinstance(el, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=new_verts, vec=(0, 0, extrude_z))
    bm.to_mesh(me)
    bm.free()
    me.update()
    return dict(scale=scale, extrude_z=extrude_z)


# ---------------------------------------------------------------------------- main
def main():
    import faulthandler, signal, time
    if hasattr(signal, "SIGUSR1"):          # POSIX only (stack dump on demand)
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
        "Placement Mode": "Scatter", "Embed": 0.02, "Backing Offset": 0.0, "Fit Jitter": 0.0,
        "Stand On Face Base": False, "Sill Height": 0.0, "Min Face Width": 0.6, "Min Face Height": 1.2,
        "Ground Floor Only": False, "Ground Tolerance": 0.1, "Max Base Height": 0.5,
        "Slot Layout": "Random", "Count Mode": "Per Width", "Openings Per Width": 2.5,
        "Slot Count": 2, "Opening Width": 1.4, "Opening Height": 2.1,
        # v2.6: opening auto-fit + exact counts + manual (vertex-group) masks
        "Opening Fit": "Scale To Face", "Min Fit Scale": 0.5,
        "Exact Pick": "Spread", "Exact Count": 2,
        "Manual Mask": False, "Manual Mask Group": "VM_Slots", "Manual Threshold": 0.5,
        "Min Gap X": 0.4, "Min Gap Z": 0.3, "Slot Rows": 1, "Row Spacing": 2.4,
        "Column Select": "All", "Sill Line": "Common Z", "Slot Jitter": 0.02, "No-Repeat": True,
        "Row Height": 0.22, "Row Overlap": 0.35, "Stagger": 0.5, "Jitter": 0.01, "Slot Width": 0.25,
        "Density": 0.12, "Seed": 0, "Surface Offset": -0.02, "Align To Normal": True,
        "Random Rot X": 0.02, "Random Rot Y": 0.02, "Random Rot Z": 3.1416,
        "Scale Min": 0.55, "Scale Max": 1.7, "Tint Amount": 0.5,
        "Face Zone": "Walls", "Wall Slope": 0.35, "Roof Slope Min": 0.55, "Roof Slope Max": 0.92,
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
                            if k not in ("positions", "rotations", "updots", "normals",
                                         "named_positions", "plane_normals")}
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
    # v2.7: the canonical CURRENT-DEFAULTS demo - Style 'Flat' (was 'Gable':
    # the user saw invented gable triangles on his flat tops). Pitch stays
    # opt-in via GableShowcase.
    set_params(m_roof, ng_roof, {"Pitch": math.radians(35.0), "Overhang": 0.25,
                                 "Style": "Flat", "Incline": math.radians(2.5),
                                 "Fascia": 0.12, "Roof Material": mat_roof})
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
    # v2.4: Stand On Face Base (per-face anchoring) + Sill 0.0; the door seed is
    # chosen by the deterministic seed search below (3 doors, all on cube walls,
    # corners clear) since the v2.4 RoofCap/selection changes reshuffle draws.
    # v2.8.2: nominal opening sizes match the PACK geometry (doors ~0.76-0.79 m
    # wide/1.81 m tall, windows ~0.38 m wide at 0.35 scale) so the gap law and
    # the cross-layer clearance price the ACTUAL footprints - with the generic
    # 1.4 m nominal a 2 m wall legally holds one opening and the window layer
    # could never share a wall with a door (windows 0 everywhere).
    door_params = dict(defaults, **{
        "Placement Mode": "Fit", "Face Zone": "Walls",
        "Density": 0.35, "Seed": 229, "Embed": 0.02, "Backing Offset": 0.0435,
        "Stand On Face Base": True, "Sill Height": 0.0,
        "Opening Width": 0.7, "Opening Height": 1.85,
        "Min Face Width": 0.6, "Min Face Height": 1.2,
        # v2.5: doors default Ground Floor Only ON (the roof-door bug is
        # impossible by default; the cube's walls are all ground faces)
        "Ground Floor Only": True, "Ground Tolerance": 0.1,
        "Scale Min": 1.0, "Scale Max": 1.0,
        "Primary Props": col_doors, "Debris/Trash Props": col_debris, "Debris Ratio": 0.0,
        "Random Mask Threshold": 0.0, "Vertical Mask": False,
        "Max Instances": 3,
    })
    set_params(m_door, ng, door_params)

    # ---- v2.4 door seed search: deterministic, on cheap hidden rigs (cube +
    # VM_RoofCap = the starter's host geometry) with the starter's own
    # wall-contact contract as the predicate (3 doors, cube walls only, corners
    # clear, well separated) - the v2.4 RoofCap/selection changes reshuffle the
    # random draws so the layout is re-derived, never hard-coded.
    # v2.7: ONE seed serves THREE hosts - the StarterCube (Flat cap), the
    # StarterCompound (the user's duplicate + tower/wing/annex extrusion edit)
    # and the GableShowcase twin (opt-in pitched roof) - so the starter's saved
    # seed is guaranteed to dress all of them.
    log("== doors layer: deterministic seed search (cube + compound + gable twin)")
    drig = make_cube("DoorSearchRig", 2.0, col_scene)
    drig.location = (0, -40, 0)
    drig.hide_render = True
    m_drig_roof = drig.modifiers.new("VM_RoofCap", "NODES")
    m_drig_roof.node_group = ng_roof
    set_params(m_drig_roof, ng_roof, {"Pitch": math.radians(35.0), "Overhang": 0.25,
                                      "Style": "Flat", "Roof Material": None,
                                      "Min Roof Face Size": 0.4, "Largest Face Only": False})
    m_drig_door = drig.modifiers.new("VM_SceneDetailer_Door", "NODES")
    m_drig_door.node_group = ng
    set_params(m_drig_door, ng, door_params)
    exp_r = 1.0 + door_params["Backing Offset"] - door_params["Embed"]

    def new_compound_rig(name):
        me_r = bpy.data.meshes.new(name)
        build_compound_mesh(me_r)
        rig = bpy.data.objects.new(name, me_r)
        col_scene.objects.link(rig)
        rig.location = (0, -40, 0)
        rig.hide_render = True
        m_r = rig.modifiers.new("VM_RoofCap", "NODES"); m_r.node_group = ng_roof
        set_params(m_r, ng_roof, {"Pitch": math.radians(35.0), "Overhang": 0.25,
                                  "Style": "Flat", "Incline": math.radians(2.5),
                                  "Fascia": 0.12, "Roof Material": None,
                                  "Min Roof Face Size": 0.4, "Largest Face Only": False})
        return rig

    def new_gable_rig(name):
        rig = make_cube(name, 2.0, col_scene)
        rig.location = (0, -40, 0)
        rig.hide_render = True
        m_r = rig.modifiers.new("VM_RoofCap", "NODES"); m_r.node_group = ng_roof
        set_params(m_r, ng_roof, {"Pitch": math.radians(35.0), "Overhang": 0.25,
                                  "Style": "Gable", "Roof Material": None,
                                  "Min Roof Face Size": 0.4, "Largest Face Only": False})
        return rig

    dcrig = new_compound_rig("DoorCompoundRig")
    m_dcrig_door = dcrig.modifiers.new("VM_SceneDetailer_Door", "NODES")
    m_dcrig_door.node_group = ng
    set_params(m_dcrig_door, ng, door_params)
    dgrig = new_gable_rig("DoorGableRig")
    m_dgrig_door = dgrig.modifiers.new("VM_SceneDetailer_Door", "NODES")
    m_dgrig_door.node_group = ng
    set_params(m_dgrig_door, ng, door_params)
    comp_faces = face_table(dcrig)
    comp_inv = dcrig.matrix_world.inverted()

    def door_ok(dbs, rig=None):
        if len(dbs) != 3:
            return False, 0.0
        # instance origins are WORLD space; the contract is stated in host-local
        # coordinates (the rigs sit at y=-40 like the starter)
        host_inv = (rig or drig).matrix_world.inverted()
        dpos = [tuple(host_inv @ b["org"]) for b in dbs]
        on_cube = all((abs(abs(x) - exp_r) < 0.02 and abs(y) < 0.6) or
                      (abs(abs(y) - exp_r) < 0.02 and abs(x) < 0.6)
                      for (x, y, z) in dpos)
        min_sep = min([((a[0] - b2[0]) ** 2 + (a[1] - b2[1]) ** 2) ** 0.5
                       for i, a in enumerate(dpos) for b2 in dpos[i + 1:]] or [99.0])
        dgaps = [aabb_gap(dbs[i], dbs[j]) for i in range(len(dbs)) for j in range(i + 1, len(dbs))]
        return on_cube and min_sep > 0.85 and (not dgaps or min(dgaps) >= 0), min_sep

    def door_ok_compound(dbs):
        """v2.7 compound contract: >= 1 door, every door on an EXTERIOR GROUND
        wall of the tower+wing+annex massing, fully inside its wall height."""
        if len(dbs) < 1:
            return False
        for d in dbs:
            f, _ = match_face(comp_faces, d["n"], d["org"], d)
            if f is None or not face_is_exterior(f, comp_inv, STAGE_COMPOUND_BLOCKS):
                return False
            if not opening_is_exterior(d, comp_inv, STAGE_COMPOUND_BLOCKS):
                return False                     # low opening buried behind the wing
            if f["min_z"] > 0.06 or abs(d["lo"].z) > 0.06:
                return False                     # not a ground wall / not standing on it
            if (d["hi"].z - d["lo"].z) > f["h"] + 0.05 or d["hi"].z > f["max_z"] + 0.05:
                return False                     # door sticks out above its wall
        return True

    def door_ok_gable(dbs):
        if len(dbs) < 1:
            return False
        host_inv = dgrig.matrix_world.inverted()
        return all((abs(abs((host_inv @ b["org"]).x) - exp_r) < 0.02) or
                   (abs(abs((host_inv @ b["org"]).y) - exp_r) < 0.02) for b in dbs)

    # v2.7 JOINT search: the starter's saved seed dresses StarterCube AND its
    # duplicates (StarterCompound / GableShowcase share the saved stack), and
    # the cube's window contract (2-3 windows, corners clear, zero door/window/
    # plank intersections) is only satisfiable around SOME door layouts - so
    # door candidates are collected first and the window scan runs per
    # candidate until the full contract passes on ALL THREE hosts.
    door_candidates, door_tried = [], 0
    for seed in range(4000):
        door_tried = seed + 1
        for m_d in (m_drig_door, m_dcrig_door, m_dgrig_door):
            set_params(m_d, ng, dict(door_params, **{"Seed": seed}))
        drig.update_tag(); dcrig.update_tag(); dgrig.update_tag()
        bpy.context.view_layer.update()
        ok_d, sep_d = door_ok(inst_boxes(drig, "Door_"))
        if not (ok_d and door_ok_compound(inst_boxes(dcrig, "Door_"))
                and door_ok_gable(inst_boxes(dgrig, "Door_"))):
            continue
        if not door_candidates or sep_d > 1.2:
            door_candidates.append((seed, round(sep_d, 5)))
        if sep_d > 1.2 and len([1 for _, s in door_candidates if s > 1.2]) >= 3:
            break
    log(f"  door candidates after {door_tried} scans: {door_candidates}")

    # ---- windows layer (v2.2): SAME VM_SceneDetailer node group, windows
    # collection from pack_ingest (WeatheredWoodenWindow shutters + a
    # BrokenWindow01 unit). Identical wall-contact contract as the doors:
    # Backing Offset 0.045 / Embed 0.02 -> back plane at planks_thickness + 0.005.
    m_win = starter.modifiers.new("VM_SceneDetailer_Windows", "NODES")
    m_win.node_group = ng
    win_params = dict(defaults, **{
        "Placement Mode": "Fit", "Face Zone": "Walls",
        "Density": 0.35, "Embed": 0.02, "Backing Offset": 0.0435,
        "Stand On Face Base": True, "Sill Height": 0.9,
        "Opening Width": 0.42, "Opening Height": 0.95, "Min Gap X": 0.05,
        "Min Face Width": 1.5, "Min Face Height": 1.5,
        "Ground Floor Only": False, "Ground Tolerance": 0.1,
        "Scale Min": 0.35, "Scale Max": 0.35,
        "Primary Props": col_windows, "Debris/Trash Props": col_debris, "Debris Ratio": 0.0,
        "Random Mask Threshold": 0.0, "Vertical Mask": False,
        "Max Instances": 3,
    })
    # Deterministic reseed (shift/reseed, no geometry edits). Window sampling
    # only sees the HOST mesh (instance layers are deleted before sampling), so
    # the seed search runs on cheap hidden rigs against the real door/plank
    # boxes, then verifies on the full starter stack. Hard constraints: windows
    # stay on the wall (never hang off a corner, never on roof gables), base at
    # window height, and zero window/door, window/window, window/plank bbox
    # intersections. v2.7: the SAME seed also serves the StarterCompound and
    # the GableShowcase twin (see the doors search above).
    log("== windows layer: deterministic seed search (cube + compound + gable twin)")
    rig = make_cube("WinSearchRig", 2.0, col_scene)
    rig.location = (0, -40, 0)
    rig.hide_render = True
    m_rig_roof = rig.modifiers.new("VM_RoofCap", "NODES")
    m_rig_roof.node_group = ng_roof
    set_params(m_rig_roof, ng_roof, {"Pitch": math.radians(35.0), "Overhang": 0.25,
                                     "Style": "Flat", "Roof Material": None})
    # v2.8.2: the rig carries the DOOR layer first (same seed as the starter's
    # doors) so the window layer's cross-layer clearance sees the real door
    # anchors and dodges them exactly like the delivered stack does.
    m_rig_door = rig.modifiers.new("VM_SceneDetailer_Door", "NODES")
    m_rig_door.node_group = ng
    set_params(m_rig_door, ng, dict(door_params))
    m_rig_win = rig.modifiers.new("VM_SceneDetailer_Windows", "NODES")
    m_rig_win.node_group = ng
    set_params(m_rig_win, ng, win_params)
    wcrig = new_compound_rig("WinCompoundRig")
    m_wcrig_door = wcrig.modifiers.new("VM_SceneDetailer_Door", "NODES")
    m_wcrig_door.node_group = ng
    m_wcrig_win = wcrig.modifiers.new("VM_SceneDetailer_Windows", "NODES")
    m_wcrig_win.node_group = ng
    set_params(m_wcrig_win, ng, win_params)
    wgrig = new_gable_rig("WinGableRig")
    m_wgrig_door = wgrig.modifiers.new("VM_SceneDetailer_Door", "NODES")
    m_wgrig_door.node_group = ng
    m_wgrig_win = wgrig.modifiers.new("VM_SceneDetailer_Windows", "NODES")
    m_wgrig_win.node_group = ng
    set_params(m_wgrig_win, ng, win_params)
    planks_b = inst_boxes(starter, "Plank_")
    lo_h, hi_h = host_planes(starter)
    doors_b = []          # refreshed per door candidate below

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

    def win_ok_compound(wins):
        """v2.7 compound contract (acceptance-literal): >= 1 window and every
        window on an EXTERIOR GROUND wall at window height, not buried in the
        massing. Door-collision cleanliness is PREFERRED by the scan but not
        required (the acceptance asks for openings on ground walls)."""
        if len(wins) < 1:
            return False
        for w in wins:
            f, _ = match_face(comp_faces, w["n"], w["org"], w)
            if f is None or not face_is_exterior(f, comp_inv, STAGE_COMPOUND_BLOCKS):
                return False
            if not opening_is_exterior(w, comp_inv, STAGE_COMPOUND_BLOCKS):
                return False
            if f["min_z"] > 0.06 or not (0.25 <= w["lo"].z <= 1.05):
                return False
            if (w["hi"].z - w["lo"].z) > f["h"] + 0.05 or w["hi"].z > f["max_z"] + 0.05:
                return False
        return True

    def win_ok_compound_strict(wins):
        """The PREFERRED variant: also zero window/door bbox intersections."""
        if not win_ok_compound(wins):
            return False
        wdoors = inst_boxes(wcrig, "Door_")
        return not any(aabb_gap(w, d) < 0 for w in wins for d in wdoors)

    def win_ok_gable(wins):
        return len(wins) >= 1 and all(0.25 <= w["lo"].z <= 1.05 for w in wins)

    # ---- the JOINT scan: per door candidate, scan window seeds with a cheap
    # one-rig prefilter (the cube contract is the rare one: measured ~1 per 500
    # seeds) and only then evaluate the compound/gable hosts. The first
    # RELAXED pass wins; a STRICT (collision-free compound) pass found within
    # the same scan replaces it.
    win_seed_used, win_fallback, win_tried = 0, None, 0
    door_seed_used = door_candidates[0][0] if door_candidates else 229
    chosen, chosen_strict = None, None
    for dseed, dsep in door_candidates[:4]:
        set_params(m_door, ng, dict(door_params, **{"Seed": dseed}))
        set_params(m_rig_door, ng, dict(door_params, **{"Seed": dseed}))
        set_params(m_wcrig_door, ng, dict(door_params, **{"Seed": dseed}))
        set_params(m_wgrig_door, ng, dict(door_params, **{"Seed": dseed}))
        starter.update_tag(); rig.update_tag(); wcrig.update_tag(); wgrig.update_tag()
        bpy.context.view_layer.update()
        doors_b = inst_boxes(starter, "Door_")
        for seed in range(10000):
            win_tried += 1
            set_params(m_rig_win, ng, dict(win_params, **{"Seed": seed}))
            rig.update_tag()
            bpy.context.view_layer.update()
            ok, vis, mgap = win_evaluate(inst_boxes(rig, "Window_"))
            if not ok:
                continue
            if win_fallback is None:
                win_fallback = dict(door=dseed, seed=seed, visible=vis, min_gap=round(mgap, 5))
            set_params(m_wcrig_win, ng, dict(win_params, **{"Seed": seed}))
            set_params(m_wgrig_win, ng, dict(win_params, **{"Seed": seed}))
            wcrig.update_tag(); wgrig.update_tag()
            bpy.context.view_layer.update()
            wcomp = inst_boxes(wcrig, "Window_")
            if not (win_ok_compound(wcomp) and win_ok_gable(inst_boxes(wgrig, "Window_"))):
                continue
            if win_ok_compound_strict(wcomp) and vis >= 1:
                chosen_strict = (dseed, seed)
                break
            if chosen is None and vis >= 1:
                chosen = (dseed, seed)   # first acceptance-literal pass
        if chosen_strict or chosen:
            break
    if chosen_strict is None and chosen is None and win_fallback:
        chosen = (win_fallback["door"], win_fallback["seed"])
    if chosen_strict is None and chosen is None:
        chosen = (door_candidates[0][0] if door_candidates else 229, 0)
    door_seed_used, win_seed_used = chosen_strict or chosen
    set_params(m_door, ng, dict(door_params, **{"Seed": door_seed_used}))
    set_params(m_win, ng, dict(win_params, **{"Seed": win_seed_used}))
    starter.update_tag()
    bpy.context.view_layer.update()
    f_ok, f_vis, f_gap = win_evaluate(inst_boxes(starter, "Window_"))
    results["doors_seed_search"] = dict(
        seed=door_seed_used, seeds_tried=door_tried,
        candidates=[dict(seed=s, min_sep=sep) for s, sep in door_candidates],
        hosts=["StarterCube(Flat)", "StarterCompound", "GableShowcase(Gable)"])
    results["windows_seed_search"] = dict(seed=win_seed_used, seeds_tried=win_tried,
                                          fallback=win_fallback,
                                          full_stack_ok=f_ok, full_stack_visible=f_vis,
                                          full_stack_min_gap=round(f_gap, 5))
    log(f"  JOINT seed pair chosen: door={door_seed_used} win={win_seed_used} "
        f"after {win_tried} window scans (fallback={win_fallback})")

    # ================================================== v2.7: GableShowcase + StarterCompound
    log("\n== v2.7: GableShowcase (pitched OPT-IN) + StarterCompound (the user's exact action) ==")
    # (1) GableShowcase: the StarterCube's twin with the pitched style explicitly
    # requested - side by side, the two design languages of the engine.
    gs = starter.copy()
    gs.data = starter.data.copy()
    gs.name = "GableShowcase"
    col_scene.objects.link(gs)
    gs.location = (5.5, -40, 0)
    set_params(gs.modifiers["VM_RoofCap"], ng_roof,
               {"Pitch": math.radians(35.0), "Overhang": 0.25,
                "Style": "Gable", "Roof Material": mat_roof})
    gs.update_tag()
    bpy.context.view_layer.update()
    gs_res, gs_chk = gable_showcase_accept("GableShowcase", gs)
    for name, cond, detail in gs_chk:
        check(name, cond, detail)
    results["gable_showcase"] = gs_res
    log(f"  GableShowcase: {gs_res['n_shingles']} shingles (formula {gs_res['expected_shingles']}), "
        f"{gs_res['n_doors']} doors, {gs_res['n_windows']} windows")

    # (2) StarterCompound: the user's EXACT action - duplicate StarterCube (the
    # saved modifier stack copies along untouched), then extrude/step the base
    # mesh into a tower + lower wing + annex compound (build_compound_mesh).
    sc = starter.copy()
    sc.data = starter.data.copy()
    sc.name = "StarterCompound"
    col_scene.objects.link(sc)
    sc.location = (11.5, -40, 0)
    build_compound_mesh(sc.data)          # his edit-mode work: extrude + steps
    sc.update_tag()
    bpy.context.view_layer.update()
    sc_res, sc_chk = compound_accept("StarterCompound", sc)
    for name, cond, detail in sc_chk:
        check(name, cond, detail)
    results["starter_compound"] = sc_res
    log(f"  StarterCompound: {sc_res['n_doors']} doors, {sc_res['n_windows']} windows, "
        f"{sc_res['n_planks']} planks (formula {sc_res['expected_planks']}), "
        f"gable faces={sc_res['roof']['generated']}")

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
                                if k not in ("positions", "rotations", "updots", "normals",
                                             "named_positions", "plane_normals")}
    log(f"  StarterCube: {s_house['n_instances']} instances, freq={s_house['freq']}")

    # ================================================== test rigs
    log("\n== building verification rigs ==")
    test_fit = make_cube("TestFit", 2.0, col_scene); test_fit.location = (60, 0, 0)
    mod_fit = test_fit.modifiers.new("VM_SceneDetailer", "NODES"); mod_fit.node_group = ng
    fit_params = dict(defaults, **{
        "Placement Mode": "Fit", "Face Zone": "Walls", "Density": 0.6, "Seed": 2,
        "Embed": 0.03, "Stand On Face Base": True, "Sill Height": 0.0, "Scale Min": 1.0, "Scale Max": 1.0,
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
    # v2.4 contract change: Roof zone is a SLOPE BAND (pitched faces only, flat
    # tops are NOT roof). The rig gets a VM_RoofCap first so roof-zone cladding
    # has pitched faces to land on.
    mod_zones_roof = test_zones.modifiers.new("VM_RoofCap", "NODES"); mod_zones_roof.node_group = ng_roof
    set_params(mod_zones_roof, ng_roof, {"Pitch": math.radians(35.0), "Overhang": 0.25,
                                         "Style": "Gable", "Roof Material": None,
                                         "Min Roof Face Size": 0.4, "Largest Face Only": False})
    mod_zones = test_zones.modifiers.new("VM_SceneDetailer", "NODES"); mod_zones.node_group = ng
    zones_params = dict(clad_params, **{"Face Zone": "Roof"})
    set_params(mod_zones, ng, zones_params)

    test_mat = make_cube("TestMat", 2.0, col_scene); test_mat.location = (90, 0, 0)
    # v2.4: RoofCap first (no material) so the zone-material gate is proven on
    # pitched faces too - and so is the new rule that flat tops are Floor, not Roof
    mod_mat_roof = test_mat.modifiers.new("VM_RoofCap", "NODES"); mod_mat_roof.node_group = ng_roof
    set_params(mod_mat_roof, ng_roof, {"Pitch": math.radians(35.0), "Overhang": 0.25,
                                       "Style": "Gable", "Roof Material": None,
                                       "Min Roof Face Size": 0.4, "Largest Face Only": False})
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
    log("\n== STAGE 2: Face Zone selection (v2.4: Roof = slope band) ==")
    sz = run(test_zones, mod_zones, "clad_zone_roof", zones_params)
    zc2 = zone_counts_on_cube(sz["positions"], sz["normals"])
    results["zone_roof_counts"] = zc2
    log(f"  roof-zone cladding positions: {zc2}")
    on_slope = sum(1 for (nx, ny, nz) in sz["normals"] if 0.55 <= nz < 0.92)
    on_flat = sum(1 for (nx, ny, nz) in sz["normals"] if nz >= 0.92)
    on_wall2 = sum(1 for (nx, ny, nz) in sz["normals"] if abs(nz) <= 0.35)
    results["zone_roof_band"] = dict(on_slope=on_slope, on_flat=on_flat, on_wall=on_wall2)
    log(f"  roof-band cladding: {on_slope} on slopes, {on_flat} on flat tops, {on_wall2} on walls")
    check("zone: Roof slope-band cladding lands only on pitched faces (contract v2.4: "
          "flat tops are NOT roof)",
          on_slope == sz["n_instances"] and sz["n_instances"] > 0 and on_flat == 0 and on_wall2 == 0,
          f"{on_slope}/{sz['n_instances']} on slopes (0.55<=N.z<0.92), flat tops={on_flat}, walls={on_wall2}")
    check("zone: walls vs roof give disjoint placements",
          zc["on_top"] == 0 and on_wall2 == 0, "walls-only fit + slope-band roof clad")

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

    # starter roof cladding cross-check (slopes from VM_RoofCap, v2.4 slope band)
    exp_roof, per_roof = expected_courses(
        starter,
        lambda n, c: 0.55 <= n.z < 0.92, 0.25, 0.35, 0.11)
    results["starter_roof_expected"] = per_roof
    n_shingle = sum(v for k, v in s_house["freq"].items() if k.startswith("Shingle_"))
    check("clad: starter roof shingle count matches formula", n_shingle == exp_roof,
          f"actual={n_shingle} expected={exp_roof} over {len(per_roof)} roof faces")
    n_plank = sum(v for k, v in s_house["freq"].items() if k.startswith("Plank_"))
    exp_wall, per_wallf = expected_courses(
        starter, lambda n, c: abs(n.z) <= 0.35 and c.z <= 2.01, 2.0, 0.05, 0.22,
        skip_generated=True)
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
    # v2.8 gap law: fit openings live on edge-guarded strips, so their count is
    # non-decreasing with density and SATURATES at the legal strip budget
    # (more density can no longer cram extra openings past the gap law).
    check("sweep: fit counts non-decreasing with density (gap-law saturation is legal)",
          sweep[0.1]["fit"] <= sweep[0.35]["fit"] <= sweep[0.6]["fit"], f"{sweep}")
    check("sweep: cladding density-independent (tile-driven)",
          len({sweep[d]["clad"] for d in sweep}) == 1, f"{sweep}")

    # cap in each mode (fit uses a wide-wall rig with small openings so >= 25
    # legal strips exist - the gap law caps small hosts before Max Instances)
    cap_fit_host = make_wide_wall("CapFitHost", col_scene, 12.5)
    cap_fit_host.location = (70, -30, 0)
    mod_cap_fit = cap_fit_host.modifiers.new("VM_SceneDetailer", "NODES")
    mod_cap_fit.node_group = ng
    cap_fit_params = dict(fit_params, **{"Density": 4.0, "Opening Width": 0.5,
                                         "Min Gap X": 0.1, "Openings Per Width": 0.5,
                                         "Max Instances": 25})
    for tag, ob, mod, prm in (("cap_scatter", house_a, mod_a, baseline),
                              ("cap_fit", cap_fit_host, mod_cap_fit, cap_fit_params),
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
        # v2.4 zone bands: Roof = slope band, Floor = flat planes both ways
        z = ("wall" if abs(n.z) <= 0.35 else
             ("roof" if 0.55 <= n.z < 0.92 else
              ("floor" if (n.z <= -0.55 or n.z >= 0.92) else "other")))
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
        rr1 = roof_report(ob)
        results[f"roofcap_{style}_regions"] = rr1
        check(f"roofcap: {style} per-region output is exactly 4 clean faces (2 slopes + 2 ends)",
              rr1["generated"] == 4 and rr1["qualifying"] == 1 and rr1["zero_area"] == 0
              and not rr1["strays"],
              f"generated={rr1['generated']}, regions={rr1['regions']}, zero-area={rr1['zero_area']}, "
              f"strays={rr1['strays']}")

    # ================================================== STAGE 6: SHAPE-ROBUSTNESS MATRIX (v2.4)
    log("\n== STAGE 6: SHAPE-ROBUSTNESS MATRIX (user extrudes shapes FIRST, engine dresses them) ==")
    shape_door_params = dict(defaults, **{
        "Placement Mode": "Fit", "Face Zone": "Walls",
        # NOTE: Max Instances keeps the FIRST N points in face order, so density
        # is kept low enough that candidates spread over all eligible faces and
        # leave wall room for windows (crowded walls make the seed search fail)
        "Density": 0.2, "Embed": 0.02, "Backing Offset": 0.0435,
        "Stand On Face Base": True, "Sill Height": 0.0,
        # v2.8.2: pack-sized nominal openings (see door_params above) + the cap
        # leaves at least one wall door-free so the window layer has legal room
        "Opening Width": 0.7, "Opening Height": 1.85,
        "Min Face Width": 1.0, "Min Face Height": 1.6,
        # v2.5: doors default Ground Floor Only ON + Max Base Height ceiling -
        # a door can never land on a roof-adjacent wall segment (the user's
        # roof-door bug). Explicit upper doors use the override probe below.
        "Ground Floor Only": True, "Ground Tolerance": 0.1, "Max Base Height": 0.5,
        "Scale Min": 1.0, "Scale Max": 1.0,
        "Primary Props": col_doors, "Debris/Trash Props": col_debris, "Debris Ratio": 0.0,
        "Random Mask Threshold": 0.0, "Vertical Mask": False,
        "Max Instances": 2,
    })
    shape_win_params = dict(defaults, **{
        "Placement Mode": "Fit", "Face Zone": "Walls",
        "Density": 0.15, "Embed": 0.02, "Backing Offset": 0.0435,
        "Stand On Face Base": True, "Sill Height": 0.9,
        "Opening Width": 0.42, "Opening Height": 0.95, "Min Gap X": 0.05,
        "Min Face Width": 1.5, "Min Face Height": 1.5,
        "Ground Floor Only": False, "Ground Tolerance": 0.1,
        "Scale Min": 0.35, "Scale Max": 0.35,
        "Primary Props": col_windows, "Debris/Trash Props": col_debris, "Debris Ratio": 0.0,
        "Random Mask Threshold": 0.0, "Vertical Mask": False,
        # v2.5: ONE window per shape rig - the window layer shares walls with the
        # door layer and the wall-contact contract needs real gap between them
        # (the starter and the Slots rigs carry the multi-window demos)
        "Max Instances": 1,
    })
    roofcap_params = {"Pitch": math.radians(35.0), "Overhang": 0.25, "Style": "Gable",
                      "Roof Material": mat_roof, "Min Roof Face Size": 0.4, "Largest Face Only": False}

    def dress_shape(host):
        m1 = host.modifiers.new("VM_SceneDetailer_Planks", "NODES"); m1.node_group = ng
        set_params(m1, ng, plank_params)
        m2 = host.modifiers.new("VM_RoofCap", "NODES"); m2.node_group = ng_roof
        set_params(m2, ng_roof, roofcap_params)
        m3 = host.modifiers.new("VM_SceneDetailer_Shingles", "NODES"); m3.node_group = ng
        set_params(m3, ng, shingle_params)
        m4 = host.modifiers.new("VM_SceneDetailer_Door", "NODES"); m4.node_group = ng
        dp = dict(shape_door_params)   # v2.5: Ground Floor Only ON (roof protection)
        set_params(m4, ng, dp)
        m5 = host.modifiers.new("VM_SceneDetailer_Windows", "NODES"); m5.node_group = ng
        set_params(m5, ng, shape_win_params)
        return m4, m5, dp

    def search_shape_seed(host, mod, base, prefix, pred, max_seeds=1200):
        used, tried, fb = 0, 0, None
        for seed in range(max_seeds):
            tried = seed + 1
            set_params(mod, ng, dict(base, **{"Seed": seed}))
            host.update_tag()
            bpy.context.view_layer.update()
            ok, score = pred(inst_boxes(host, prefix))
            if not ok:
                continue
            if fb is None or score > fb["score"]:
                fb = dict(seed=seed, score=round(float(score), 4))
            if score >= 1.0:
                used = seed
                break
        else:
            used = fb["seed"] if fb else 0
        set_params(mod, ng, dict(base, **{"Seed": used}))
        host.update_tag()
        bpy.context.view_layer.update()
        return used, tried, fb

    def mk_door_pred(faces, want_raised):
        def pred(boxes):
            if len(boxes) < 2:
                return False, 0.0
            raised = 0
            per_face = {}
            for bx in boxes:
                f, _ = match_face(faces, bx["n"], bx["org"], bx)
                if f is None or abs(bx["lo"].z - f["min_z"]) > 0.06:
                    return False, 0.0
                per_face[f["idx"]] = per_face.get(f["idx"], 0) + 1
                if f["min_z"] > 0.5:
                    raised += 1
            gaps = [aabb_gap(boxes[i], boxes[j]) for i in range(len(boxes)) for j in range(i + 1, len(boxes))]
            if any(g < 0 for g in gaps):
                return False, 0.0
            # v2.5: a SPREAD layout (doors on several walls, never stacked on one)
            # is the full-score preference - it leaves wall room for the window
            # layer and matches the HouseCraft look (a door per facade).
            spread = len(per_face) >= 2 and max(per_face.values()) <= 2
            if want_raised and raised == 0:
                # v2.4.1: a raised-wall door is a PREFERENCE, not a hard reject -
                # with the world-meter face filters a scaled compound can have
                # every candidate land on the early faces (Max Instances keeps
                # the FIRST N in face order), and an unvalidated fallback seed
                # is worse than a clean ground-wall layout (0.25 keeps the
                # fallback biased TOWARD raised layouts when they exist)
                return True, 0.25
            if spread:
                return True, 1.0
            # fallback ordering: raised-but-crowded beats unraised layouts
            return True, (0.6 if raised else 0.5)
        return pred

    def mk_win_pred(host, faces):
        sill_w = 0.9          # v2.4.1: Sill Height is WORLD meters (contract)
        def pred(boxes):
            if len(boxes) < 1:
                return False, 0.0
            for bx in boxes:
                f, _ = match_face(faces, bx["n"], bx["org"], bx)
                if f is None or abs(bx["lo"].z - (f["min_z"] + sill_w)) > 0.06:
                    return False, 0.0
                if f["w"] < 1.5 or f["h"] < 1.5:
                    return False, 0.0
            gaps = [aabb_gap(boxes[i], boxes[j]) for i in range(len(boxes)) for j in range(i + 1, len(boxes))]
            gaps += [aabb_gap(bx, d) for bx in boxes for d in inst_boxes(host, "Door_")]
            if any(g < 0 for g in gaps):
                return False, 0.0
            return True, 1.0
        return pred

    shape_matrix = {}
    shape_specs = [
        ("CompoundTest", make_compound, (0, -60, 0), None, False,
         "L-shaped stepped compound: tall block + lower wing, concave inner corner, two flat tops",
         (2, 0)),
        ("CompoundScaled", make_compound, (12, -60, 0), (1.6, 1.0, 1.6), False,
         "same compound NON-UNIFORMLY scaled (x1.6 wider/taller), object scale left as-is",
         (2, 0)),
        ("TowerWing", make_tower_wing, (28, -60, 0), None, False,
         "tower + lower wing + two unresolved roof regions (triangle top, 0.3m quad top)",
         (2, 2)),
        ("Warehouse", make_warehouse, (44, -60, 0), None, True,
         "wide low warehouse box: one huge flat top -> one long gable", (1, 0)),
    ]
    for tag, builder, loc, oscale, ground_only, desc, n_regions in shape_specs:
        log(f"\n-- shape {tag}: {desc}")
        host = builder(tag, col_scene)
        host.location = loc
        if oscale:
            host.scale = oscale
        faces = face_table(host)
        m_d, m_w, dp = dress_shape(host)
        dseed, dtried, dfb = search_shape_seed(host, m_d, dp, "Door_",
                                               mk_door_pred(faces, want_raised=False))
        wseed, wtried, wfb = search_shape_seed(host, m_w, shape_win_params, "Window_",
                                               mk_win_pred(host, faces))
        res, chk = shape_accept(tag, host, n_regions_expected=n_regions)
        for name, cond, detail in chk:
            check(name, cond, detail)
        shape_matrix[tag] = dict(desc=desc, door_seed=dseed, win_seed=wseed,
                                 seeds_tried=dict(door=dtried, window=wtried),
                                 fallbacks=dict(door=dfb, window=wfb), **res)
        results["shape_matrix"] = shape_matrix
        log(f"  {tag}: doors={res['n_doors']} windows={res['n_windows']} "
            f"planks={res['n_planks']} shingles={res['n_shingles']}, "
            f"roof regions={res['roof']['qualifying']}, skipped={res['roof']['skipped']}")

    # ---- acceptance A on the compound (v2.5 contract change, documented):
    # 'Ground Floor Only' is now the door DEFAULT and 'Max Base Height' is a hard
    # ceiling on placement-face bases in BOTH Fit layouts - a door can never land
    # on a roof-adjacent wall segment (the user's roof-door bug). The v2.4
    # per-face anchoring demo (step-wall door standing at its own face base) is
    # preserved as the EXPLICIT upper-door override below.
    ct = bpy.data.objects["CompoundTest"]
    ct_rows = shape_matrix["CompoundTest"]["doors"]
    step_doors = [r for r in ct_rows if r.get("face_base", 0.0) > 0.5]
    gnd_doors = [r for r in ct_rows if r.get("face_base", 0.0) <= 0.5]
    check("accept(A): DEFAULT door rules (Ground Floor Only ON + Max Base Height 0.5): zero doors "
          "on raised/roof-adjacent faces - the user's roof-door case is IMPOSSIBLE by default",
          len(gnd_doors) >= 1 and len(step_doors) == 0,
          f"ground-wall doors={[(r['face'], r['base_z']) for r in gnd_doors]}, "
          f"raised/roof-adjacent doors={step_doors}")
    check("accept(A): doors on ground walls stand at z=0 (none dragged by the step, none underground)",
          len(gnd_doors) >= 1 and all(abs(r["base_z"]) <= 0.05 for r in gnd_doors),
          f"ground-wall door rows: {gnd_doors}")

    # ---- Max Base Height proven at both ends: the CEILING alone (Ground Floor
    # Only OFF) still kills the roof-door case, and the OVERRIDE (ceiling raised)
    # brings back explicit upper doors standing on their OWN face bases.
    m_ct_d = ct.modifiers["VM_SceneDetailer_Door"]
    dseed_ct = shape_matrix["CompoundTest"]["door_seed"]
    set_params(m_ct_d, ng, dict(shape_door_params, **{"Ground Floor Only": False, "Seed": dseed_ct}))
    ct.update_tag(); bpy.context.view_layer.update()
    gfaces = face_table(ct)
    cdoors = inst_boxes(ct, "Door_")
    raised_c = []
    for bx in cdoors:
        f, _ = match_face(gfaces, bx["n"], bx["org"], bx)
        if f is not None and f["min_z"] > 0.5:
            raised_c.append(bx["name"])
    check("fit: Max Base Height ALONE (Ground Floor Only OFF) still blocks every roof-adjacent "
          "face - no opening above zmin + Max Base Height",
          len(cdoors) > 0 and not raised_c,
          f"{len(cdoors)} doors with GFO OFF + Max Base Height 0.5; raised-face doors={raised_c}")
    # explicit upper doors: raise the ceiling and search a layout that uses it
    ov_params = dict(shape_door_params, **{"Ground Floor Only": False, "Max Base Height": 2.0})
    oseed, otried, ofb = search_shape_seed(ct, m_ct_d, ov_params, "Door_",
                                           mk_door_pred(gfaces, want_raised=True))
    odoors = inst_boxes(ct, "Door_")
    raised_o = []
    for bx in odoors:
        f, _ = match_face(gfaces, bx["n"], bx["org"], bx)
        if f is not None and f["min_z"] > 0.5:
            raised_o.append((bx["name"], round(bx["lo"].z, 3), round(f["min_z"], 3)))
    check("fit: Max Base Height override allows EXPLICIT upper doors, each standing on its OWN "
          "face base (v2.4 per-face anchoring preserved for the override case)",
          len(raised_o) >= 1 and all(abs(bz - fz) <= 0.05 for _, bz, fz in raised_o),
          f"override upper doors (name, base_z, face_base)={raised_o}, seed={oseed} "
          f"after {otried} candidates")
    results["max_base_height_override"] = dict(seed=oseed, seeds_tried=otried,
                                               upper_doors=raised_o, ceiling_doors=raised_c)
    set_params(m_ct_d, ng, dict(shape_door_params, **{"Seed": dseed_ct}))   # restore the defaults
    ct.update_tag(); bpy.context.view_layer.update()

    # ---- Largest Face Only toggle proof on CompoundTest (2 regions -> 1 roof)
    m_ct_r = ct.modifiers["VM_RoofCap"]
    set_params(m_ct_r, ng_roof, dict(roofcap_params, **{"Largest Face Only": True}))
    ct.update_tag(); bpy.context.view_layer.update()
    rr_largest = roof_report(ct, largest_only=True)
    results["largest_face_only"] = rr_largest
    check("roofcap: Largest Face Only caps just the biggest top (2 regions -> 1 roof, clean)",
          rr_largest["qualifying"] == 1 and rr_largest["generated"] == 4 and rr_largest["zero_area"] == 0
          and not rr_largest["strays"],
          f"regions={rr_largest['regions']}, generated={rr_largest['generated']}, "
          f"skipped={rr_largest['skipped']}")
    set_params(m_ct_r, ng_roof, roofcap_params)
    ct.update_tag(); bpy.context.view_layer.update()

    # ---- clean-skip proof rig: non-quad + undersized tops never garble geometry
    skip_host = make_tower_wing("SkipTest", col_scene)
    skip_host.location = (80, -60, 0)
    m_skip = skip_host.modifiers.new("VM_RoofCap", "NODES"); m_skip.node_group = ng_roof
    set_params(m_skip, ng_roof, roofcap_params)
    skip_host.update_tag(); bpy.context.view_layer.update()
    rr_skip = roof_report(skip_host)
    results["roofcap_skips"] = rr_skip
    check("roofcap: unresolvable regions (non-quad top, undersized top) SKIPPED CLEANLY, never garbage",
          rr_skip["qualifying"] == 2 and len(rr_skip["skipped"]) == 2
          and rr_skip["generated"] == 8 and rr_skip["zero_area"] == 0 and not rr_skip["strays"],
          f"qualifying={rr_skip['qualifying']}, skipped={rr_skip['skipped']}, "
          f"generated={rr_skip['generated']}, zero-area={rr_skip['zero_area']}, strays={rr_skip['strays']}")

    # ================================================== LIVE-EDIT REFLOW (v2.4)
    log("\n== LIVE-EDIT REFLOW: dress FIRST, edit the base mesh AFTER (user workflow) ==")
    rf = make_compound("ReflowTest", col_scene)
    rf.location = (62, -60, 0)
    rf_faces = face_table(rf)
    m_rf_d, m_rf_w, rf_dp = dress_shape(rf)
    rseed, rtried, rfb = search_shape_seed(rf, m_rf_d, rf_dp, "Door_",
                                           mk_door_pred(rf_faces, want_raised=False))
    rwseed, rwtried, rwfb = search_shape_seed(rf, m_rf_w, shape_win_params, "Window_",
                                              mk_win_pred(rf, rf_faces))
    res_before, chk_before = shape_accept("ReflowTest-before-edit", rf, n_regions_expected=(2, 0))
    for name, cond, detail in chk_before:
        check(name, cond, detail)
    edit_info = reflow_edit(rf)
    rf.update_tag(); bpy.context.view_layer.update()
    # the base mesh changed, so the random layout reshuffled - as it would for the
    # user, keep shaping then re-pick a clean seed on the NEW geometry
    rf_faces2 = face_table(rf)
    rseed2, rtried2, rfb2 = search_shape_seed(rf, m_rf_d, rf_dp, "Door_",
                                              mk_door_pred(rf_faces2, want_raised=False))
    rwseed2, rwtried2, rwfb2 = search_shape_seed(rf, m_rf_w, shape_win_params, "Window_",
                                                 mk_win_pred(rf, rf_faces2))
    res_after, chk_after = shape_accept("ReflowTest-after-edit", rf, n_regions_expected=(2, 0))
    for name, cond, detail in chk_after:
        check(name, cond, detail)
    new_tall = 3.2 * edit_info["scale"][2] + edit_info["extrude_z"]
    new_wing = 1.2 * edit_info["scale"][2]
    region_zs = sorted(r["min_z"] for r in res_after["roof"]["regions"])
    check("reflow: roofs REGENERATED on the edited mesh (region heights track the new tops)",
          len(region_zs) == 2 and abs(region_zs[0] - new_wing) <= 0.01 and abs(region_zs[1] - new_tall) <= 0.01,
          f"region base heights {region_zs}, expected [{round(new_wing, 3)}, {round(new_tall, 3)}] "
          f"(mesh scaled {edit_info['scale']} then extruded +{edit_info['extrude_z']}m)")
    check("reflow: cladding RE-TILED to the new dimensions (counts changed to match the formula)",
          res_after["n_shingles"] != res_before["n_shingles"] or res_after["n_planks"] != res_before["n_planks"],
          f"planks {res_before['n_planks']}->{res_after['n_planks']} "
          f"(formula {res_before['expected_planks']}->{res_after['expected_planks']}), "
          f"shingles {res_before['n_shingles']}->{res_after['n_shingles']} "
          f"(formula {res_before['expected_shingles']}->{res_after['expected_shingles']})")
    reflow_anchor = (not res_after["buried"]) and all(abs(r["delta"]) <= 0.05 for r in res_after["doors"]) \
        and all(abs(r["delta"]) <= 0.05 for r in res_after["windows"])
    check("reflow: parts re-anchored on the NEW faces after the edit (no underground/float artifacts)",
          reflow_anchor,
          f"door deltas after edit={[r['delta'] for r in res_after['doors']]}, "
          f"window deltas={[r['delta'] for r in res_after['windows']]}, buried={res_after['buried']}")
    results["reflow"] = dict(
        edit=edit_info,
        before_seeds=dict(door=rseed, win=rwseed, door_fb=rfb, win_fb=rwfb),
        after_seeds=dict(door=rseed2, win=rwseed2, door_fb=rfb2, win_fb=rwfb2),
        before=dict(n_doors=res_before["n_doors"], n_windows=res_before["n_windows"],
                    n_planks=res_before["n_planks"], n_shingles=res_before["n_shingles"],
                    expected_planks=res_before["expected_planks"],
                    expected_shingles=res_before["expected_shingles"],
                    doors=res_before["doors"], roof=res_before["roof"]),
        after=dict(n_doors=res_after["n_doors"], n_windows=res_after["n_windows"],
                   n_planks=res_after["n_planks"], n_shingles=res_after["n_shingles"],
                   expected_planks=res_after["expected_planks"],
                   expected_shingles=res_after["expected_shingles"],
                   doors=res_after["doors"], windows=res_after["windows"], roof=res_after["roof"]),
        door_seed=rseed, win_seed=rwseed)

    # ================================================== v2.4.1 WORLD-SPACE SIZING
    log("\n== v2.4.1 WORLD-SPACE SIZING: unapplied object scale must NOT stretch parts ==")
    cs_tag, ct_tag = "CompoundScaled", "CompoundTest"
    cso = bpy.data.objects[cs_tag]
    cs_scale = tuple(round(v, 3) for v in cso.matrix_world.to_scale())
    cs_res, ct_res = shape_matrix[cs_tag], shape_matrix[ct_tag]
    log(f"  CompoundScaled object scale (unapplied): {cs_scale}")

    # reference rig: the SAME compound with (1.6,1.0,1.6) baked into the VERTICES
    # (edit-mode style, object scale 1). World-space sizing means the object-scale
    # rig must dress EXACTLY like this one - that is the contract.
    wref = make_compound("CompoundWorldRef", col_scene)
    wref.location = (28, -80, 0)
    wref.data.transform(Matrix.Diagonal(Vector((1.6, 1.0, 1.6, 1.0))))
    wref.data.update()
    m_wd, m_ww, _ = dress_shape(wref)
    set_params(m_wd, ng, dict(shape_door_params, **{"Ground Floor Only": False,
                                                    "Seed": cs_res["door_seed"]}))
    set_params(m_ww, ng, dict(shape_win_params, **{"Seed": cs_res["win_seed"]}))
    wref.update_tag()
    bpy.context.view_layer.update()
    # WorldRef is a PARITY PROBE, not a demo shape: it dresses with the same
    # cladding/roof layers (the world-meter contract content) plus the Fit
    # layers so sills can be compared. Door/window LAYOUT is not part of the
    # world-meter contract (Density is a count knob, see USAGE.txt), so its own
    # shape checks are measured for the record but NOT registered - the
    # registered proof is the CS<->WorldRef parity check below.
    res_wref, chk_wref = shape_accept("CompoundWorldRef", wref, n_regions_expected=(2, 0))
    log(f"  [WorldRef probe] {sum(1 for _, c, _ in chk_wref if c)}/{len(chk_wref)} shape checks green "
        f"(door/window layout checks not registered - Density is a count knob)")

    # ---- (1) counts grow with the building: formula parity in WORLD space
    check("world-space: CompoundScaled tile counts follow the WORLD course formula "
          "(scaled building -> more tiles, tile size unchanged)",
          cs_res["n_planks"] == cs_res["expected_planks"]
          and cs_res["n_shingles"] == cs_res["expected_shingles"]
          and cs_res["n_planks"] > ct_res["n_planks"]
          and cs_res["n_shingles"] > ct_res["n_shingles"],
          f"planks {cs_res['n_planks']} (world formula {cs_res['expected_planks']}, "
          f"CompoundTest {ct_res['n_planks']}), shingles {cs_res['n_shingles']} "
          f"(world formula {cs_res['expected_shingles']}, CompoundTest {ct_res['n_shingles']})")

    def dims_stats(dims):
        if not dims:
            return dict(long=(0, 0), mid=(0, 0), short=(0, 0))
        return dict(long=(min(d[0] for d in dims), max(d[0] for d in dims)),
                    mid=(min(d[1] for d in dims), max(d[1] for d in dims)),
                    short=(min(d[2] for d in dims), max(d[2] for d in dims)))

    def close2(a, b, tol=0.02):
        return abs(a - b) <= tol * max(abs(b), 1e-9)

    cs_d = dims_stats(cs_res["plank_dims"])
    ct_d = dims_stats(ct_res["plank_dims"])
    sh_cs = dims_stats(cs_res["shingle_dims"])
    sh_ct = dims_stats(ct_res["shingle_dims"])

    # ---- (2) no stretched tiles: the 'block-like' dims are gone
    check("world-space: no tile stretched by the unapplied (1.6,1.0,1.6) scale - "
          "plank height/thickness and shingle height/thickness match CompoundTest within 2% "
          "(v2.4 defect: every plank 1.6x taller/thicker = 'large blocks')",
          all(close2(a, b) for a, b in zip(cs_d["mid"], ct_d["mid"]))
          and all(close2(a, b) for a, b in zip(cs_d["short"], ct_d["short"]))
          and all(close2(a, b) for a, b in zip(sh_cs["mid"], sh_ct["mid"]))
          and all(close2(a, b) for a, b in zip(sh_cs["short"], sh_ct["short"])),
          f"CompoundScaled plank h/t {cs_d['mid']}/{cs_d['short']} vs CompoundTest "
          f"{ct_d['mid']}/{ct_d['short']}; shingle h/t {sh_cs['mid']}/{sh_cs['short']} vs "
          f"{sh_ct['mid']}/{sh_ct['short']}; plank length (slot-driven) "
          f"{cs_d['long']} vs {ct_d['long']} (same plank species, no x1.6 blow-up)")

    # ---- (3) object-scale == vertex-scale reference (the world-space contract)
    def dim_mismatch(a, b, tol=0.01):
        if len(a) != len(b):
            return -1
        return sum(1 for x, y in zip(a, b) if max(abs(p - q) for p, q in zip(x, y)) > tol)

    mm_pl = dim_mismatch(cs_res["plank_dims"], res_wref["plank_dims"])
    mm_sh = dim_mismatch(cs_res["shingle_dims"], res_wref["shingle_dims"])
    cs_sills = [round(r["base_z"] - r["face_base"], 4) for r in cs_res["windows"]]
    wr_sills = [round(r["base_z"] - r["face_base"], 4) for r in res_wref["windows"]]
    check("world-space: CompoundScaled (object scale UNAPPLIED) == CompoundWorldRef "
          "(same shape scaled in EDIT mode): identical world tile layout and sills",
          (cs_res["n_planks"], cs_res["n_shingles"])
          == (res_wref["n_planks"], res_wref["n_shingles"])
          and mm_pl == 0 and mm_sh == 0
          and len(cs_sills) == len(wr_sills) and len(cs_sills) > 0
          and all(abs(a - b) <= 0.01 for a, b in zip(cs_sills, wr_sills)),
          f"counts planks/shingles CS={(cs_res['n_planks'], cs_res['n_shingles'])} vs "
          f"WorldRef={(res_wref['n_planks'], res_wref['n_shingles'])}; "
          f"plank dims mismatches={mm_pl}, shingle dims mismatches={mm_sh}; "
          f"sills CS={cs_sills} WorldRef={wr_sills} "
          f"(doors/windows CS={(cs_res['n_doors'], cs_res['n_windows'])} vs "
          f"WorldRef={(res_wref['n_doors'], res_wref['n_windows'])} - layout counts are "
          f"Density-knob dependent, not part of the world-meter contract)")

    # ---- (4) Sill Height is WORLD meters above the face base
    check("world-space: CompoundScaled window sill = 0.9 WORLD meters above its face base "
          "(v2.4 defect: 0.9 x z-scale = 1.44 -> windows sat visually high)",
          len(cs_sills) > 0 and all(abs(s - 0.9) <= 0.02 for s in cs_sills),
          f"world sill offsets {[round(r['base_z'] - r['face_base'], 4) for r in cs_res['windows']]} "
          f"(CompoundTest {[round(r['base_z'] - r['face_base'], 4) for r in ct_res['windows']]})")

    # ---- (5) shingle rows / plank rows carry the world Row Height pitch
    def row_pitch(res_tag, host_name):
        fcs = face_table(bpy.data.objects[host_name])
        best = None
        for f in fcs:
            if abs(f["n"].y) > 0.9 and f["h"] > 1.0 and f["min_z"] < 0.1:
                best = round(f["h"] / max(1, math.ceil(f["h"] / 0.22 - 1e-6)), 4)
                break
        return best
    ct_pitch = row_pitch(ct_res, ct_tag)
    cs_pitch = row_pitch(cs_res, cs_tag)
    check("world-space: plank course pitch tracks Row Height 0.22 WORLD meters on both "
          "CompoundTest and the 1.6x CompoundScaled (rows re-count, pitch unchanged)",
          cs_pitch is not None and ct_pitch is not None and abs(cs_pitch - ct_pitch) <= 0.005
          and cs_pitch <= 0.22 + 1e-6,
          f"plank row pitch CompoundScaled {cs_pitch} m vs CompoundTest {ct_pitch} m "
          f"(Row Height = 0.22 world m; CS tall-wall rows "
          f"{math.ceil(5.12 / 0.22)} vs CT {math.ceil(3.2 / 0.22)})")

    # ---- (6) hard regression: v2.4 counts for unscaled scenes
    check("regression v2.4: unscaled scenes keep their v2.4 counts "
          "(CompoundTest 145/888, ReflowTest-after 240/1236, TowerWing 121/752, Warehouse 120/1840)",
          (ct_res["n_planks"], ct_res["n_shingles"]) == (145, 888)
          and (res_after["n_planks"], res_after["n_shingles"]) == (240, 1236)
          and (shape_matrix["TowerWing"]["n_planks"], shape_matrix["TowerWing"]["n_shingles"]) == (121, 752)
          and (shape_matrix["Warehouse"]["n_planks"], shape_matrix["Warehouse"]["n_shingles"]) == (120, 1840),
          f"CompoundTest {ct_res['n_planks']}/{ct_res['n_shingles']}, "
          f"ReflowTest-after {res_after['n_planks']}/{res_after['n_shingles']}, "
          f"TowerWing {shape_matrix['TowerWing']['n_planks']}/{shape_matrix['TowerWing']['n_shingles']}, "
          f"Warehouse {shape_matrix['Warehouse']['n_planks']}/{shape_matrix['Warehouse']['n_shingles']}")

    results["world_space"] = dict(
        compound_scaled_object_scale=cs_scale,
        counts=dict(CompoundScaled=dict(planks=cs_res["n_planks"], shingles=cs_res["n_shingles"],
                                        expected_planks=cs_res["expected_planks"],
                                        expected_shingles=cs_res["expected_shingles"],
                                        doors=cs_res["n_doors"], windows=cs_res["n_windows"]),
                    CompoundTest=dict(planks=ct_res["n_planks"], shingles=ct_res["n_shingles"]),
                    CompoundWorldRef=dict(planks=res_wref["n_planks"], shingles=res_wref["n_shingles"],
                                          doors=res_wref["n_doors"], windows=res_wref["n_windows"])),
        plank_dims=dict(CompoundScaled=cs_d, CompoundTest=ct_d,
                        CompoundWorldRef=dims_stats(res_wref["plank_dims"])),
        shingle_dims=dict(CompoundScaled=sh_cs, CompoundTest=sh_ct,
                          CompoundWorldRef=dims_stats(res_wref["shingle_dims"])),
        sills=dict(CompoundScaled=cs_sills, CompoundTest=[
            round(r["base_z"] - r["face_base"], 4) for r in ct_res["windows"]],
            CompoundWorldRef=wr_sills),
        row_pitch=dict(CompoundScaled=cs_pitch, CompoundTest=ct_pitch),
        worldref_plank_mismatches=mm_pl, worldref_shingle_mismatches=mm_sh)

    # ================================================== STAGE 7 (v2.5): OPENING PLACEMENT MATH (Slots)
    log("\n== STAGE 7: OPENING PLACEMENT MATH (v2.5 Slots: HouseCraft slot logic) ==")
    col_plank_l = bpy.data.collections.new("VM_Tiles_PlankLegacy")
    col_shingle_l = bpy.data.collections.new("VM_Tiles_ShingleLegacy")
    col_assets.children.link(col_plank_l)
    col_assets.children.link(col_shingle_l)
    make_tile_variants(col_plank_l, "PlankL", 2.0, 0.2, 0.02, 3, mat_plank,
                       [0.010, -0.008, 0.006], straddle=False)
    make_tile_variants(col_shingle_l, "ShingleL", 0.25, 0.15, 0.012, 4, mat_shingle,
                       [0.006, -0.005, 0.008, -0.004], straddle=False)

    def slots_params(primary, col, extra):
        base = dict(defaults, **{
            "Placement Mode": "Fit", "Face Zone": "Walls",
            "Slot Layout": "Slots", "Sill Line": "Common Z",
            "Embed": 0.02, "Backing Offset": 0.0435, "Stand On Face Base": True,
            "Fit Jitter": 0.0, "Slot Jitter": 0.02, "No-Repeat": True,
            "Ground Floor Only": False, "Ground Tolerance": 0.1, "Max Base Height": 0.5,
            "Scale Min": 1.0, "Scale Max": 1.0,
            "Primary Props": col, "Debris/Trash Props": col_debris, "Debris Ratio": 0.0,
            "Random Mask Threshold": 0.0, "Vertical Mask": False,
            "Max Instances": 40, "Seed": 5,
        })
        base.update(extra)
        return base

    # doors: the FIRST column of each face's grid; windows: the columns BESIDE it
    # (Skip First) on the SAME grid params so the two layers can never collide.
    slots_door_extra = {
        "Count Mode": "Per Width", "Openings Per Width": 2.5,
        "Opening Width": 1.5, "Opening Height": 2.2,
        "Min Gap X": 0.4, "Min Gap Z": 0.3, "Slot Rows": 1, "Row Spacing": 2.4,
        "Column Select": "First Only", "Sill Height": 0.0,
        "Min Face Width": 1.0, "Min Face Height": 1.6,
        "Ground Floor Only": True,
    }
    slots_win_extra = {
        "Count Mode": "Per Width", "Openings Per Width": 2.5,
        "Opening Width": 0.8, "Opening Height": 0.9,
        "Min Gap X": 0.4, "Min Gap Z": 0.3, "Slot Rows": 2, "Row Spacing": 2.4,
        "Column Select": "Skip First", "Sill Height": 0.9,
        "Min Face Width": 1.2, "Min Face Height": 1.1,
        "Ground Floor Only": False,
        "Scale Min": 0.5, "Scale Max": 0.5,
    }

    def dress_slots(host, door_extra=None, win_extra=None, win_col=None):
        m1 = host.modifiers.new("VM_SceneDetailer_Planks", "NODES"); m1.node_group = ng
        set_params(m1, ng, plank_params)
        m2 = host.modifiers.new("VM_RoofCap", "NODES"); m2.node_group = ng_roof
        set_params(m2, ng_roof, roofcap_params)
        m3 = host.modifiers.new("VM_SceneDetailer_Shingles", "NODES"); m3.node_group = ng
        set_params(m3, ng, shingle_params)
        m4 = host.modifiers.new("VM_SceneDetailer_Door", "NODES"); m4.node_group = ng
        dp = slots_params("door", col_doors, door_extra or slots_door_extra)
        set_params(m4, ng, dp)
        m5 = host.modifiers.new("VM_SceneDetailer_Windows", "NODES"); m5.node_group = ng
        wp = slots_params("win", win_col or col_windows, win_extra or slots_win_extra)
        set_params(m5, ng, wp)
        host.update_tag(); bpy.context.view_layer.update()
        return m4, m5, dp, wp

    def slots_accept(tag, host, mgx=0.4, mgz=0.3, win_rows=2):
        """Numeric acceptance for the HouseCraft opening placement math."""
        faces = face_table(host)
        lo_h, hi_h = host_planes(host)
        doors = inst_boxes(host, "Door_")
        wins = inst_boxes(host, "Window_")
        opens = [(b, "door") for b in doors] + [(b, "window") for b in wins]
        out = dict(n_doors=len(doors), n_windows=len(wins), rows=[])

        bad_zone, bad_flush, bad_ceiling = [], [], []
        matched = []
        for bx, kind in opens:
            f, d = match_face(faces, bx["n"], bx["org"], bx)
            if f is None or abs(f["n"].z) > 0.35:
                bad_zone.append((bx["name"], None if f is None else round(f["n"].z, 3)))
                continue
            matched.append((bx, kind, f, d))
            if d > 0.12:
                bad_flush.append((bx["name"], round(d, 4)))
            if f["min_z"] > lo_h.z + 0.5 + 0.05:
                bad_ceiling.append((bx["name"], round(f["min_z"], 3)))
        check(f"slots[{tag}]: every opening on a WALL face - zero roof-zone/slope-band/gable "
              f"placements ({len(opens)} openings)",
              len(opens) > 0 and not bad_zone,
              f"{len(opens)} openings ({len(doors)} doors + {len(wins)} windows), "
              f"non-wall placements={bad_zone}")
        check(f"slots[{tag}]: every opening flush on its wall (back plane measured per instance)",
              not bad_flush and len(matched) == len(opens),
              f"back distances > 0.12: {bad_flush}")
        check(f"slots[{tag}]: zero openings above zmin + Max Base Height 0.5 "
              f"(roof-adjacent wall segments can never receive openings)",
              not bad_ceiling and len(opens) > 0,
              f"host zmin={round(lo_h.z, 3)}, offenders={bad_ceiling}")

        gaps = [aabb_gap(opens[i][0], opens[j][0])
                for i in range(len(opens)) for j in range(i + 1, len(opens))]
        check(f"slots[{tag}]: zero pairwise opening bbox intersections",
              not gaps or min(gaps) >= 0.0,
              f"{len(gaps)} pairs, min gap={round(min(gaps), 5) if gaps else 99.0}")

        # per-face neighbour analysis: horizontal neighbours (same row) and
        # vertical neighbours (same column) -> Min Gap X / Min Gap Z + No-Repeat
        per_face = {}
        for bx, kind, f, d in matched:
            u = (bx["org"] - f["c"]).dot(f["u"])
            per_face.setdefault(f["idx"], []).append((u, bx["org"].z, bx["name"], kind, bx))

        def cluster(items, key):
            groups = []
            for it in sorted(items, key=key):
                for g in groups:
                    if abs(key(it) - key(g[0])) <= 0.1:
                        g.append(it)
                        break
                else:
                    groups.append([it])
            return groups

        h_gaps, v_gaps, h_dups, v_dups = [], [], [], []
        face_cols = {}
        for fi, items in per_face.items():
            row_groups = cluster(items, lambda t: t[1])
            col_groups = cluster(items, lambda t: t[0])
            face_cols[fi] = len(col_groups)
            for g in row_groups:
                g.sort()
                for i in range(len(g) - 1):
                    h_gaps.append(aabb_gap(g[i][4], g[i + 1][4]))
                    h_dups.append((g[i][2], g[i + 1][2]))
            for g in col_groups:
                g.sort(key=lambda t: t[1])
                for i in range(len(g) - 1):
                    v_gaps.append(aabb_gap(g[i][4], g[i + 1][4]))
                    v_dups.append((g[i][2], g[i + 1][2]))
        check(f"slots[{tag}]: horizontal neighbour gaps >= Min Gap X {mgx} "
              f"(column pitch = Opening Width + Min Gap X + 2*Slot Jitter enforced)",
              not h_gaps or min(h_gaps) >= mgx - 0.005,
              f"{len(h_gaps)} horizontal neighbour pairs, min bbox gap="
              f"{round(min(h_gaps), 5) if h_gaps else 99.0}")
        check(f"slots[{tag}]: vertical neighbour gaps >= Min Gap Z {mgz} "
              f"(Min Gap Z clamps the row pitch - no opening stacks on another)",
              not v_gaps or min(v_gaps) >= mgz - 0.005,
              f"{len(v_gaps)} vertical neighbour pairs, min bbox gap="
              f"{round(min(v_gaps), 5) if v_gaps else 99.0}")
        # variant identity = the instance's object name (Door_XX / Window_XX)
        same_h = [p for p in h_dups if p[0] == p[1]]
        same_v = [p for p in v_dups if p[0] == p[1]]
        check(f"slots[{tag}]: No-Repeat - no adjacent duplicate variants "
              f"({len(h_dups)} horizontal + {len(v_dups)} vertical adjacencies)",
              not same_h and not same_v,
              f"horizontal duplicates={same_h[:6]}, vertical duplicates={same_v[:6]}, "
              f"adjacency sample={((h_dups + v_dups)[:4])}")

        # common sill line: every window base on ONE world-z line per row
        zb = sorted(round(b["lo"].z, 4) for b in wins)
        clusters = []
        for z in zb:
            if clusters and z - clusters[-1][-1] <= 0.1:
                clusters[-1].append(z)
            else:
                clusters.append([z])
        spreads = [round(max(c) - min(c), 5) for c in clusters]
        out["rows"] = [round(sum(c) / len(c), 4) for c in clusters]
        out["row_spreads"] = spreads
        check(f"slots[{tag}]: window bases aligned on the shared sill line "
              f"(spread <= 0.01 world m across ALL walls, per row)",
              wins and len(clusters) == win_rows and all(s <= 0.01 for s in spreads),
              f"{len(wins)} windows, row base lines={[round(sum(c)/len(c),4) for c in clusters]}, "
              f"per-row spreads={spreads}")
        out.update(faces_used={str(k): v for k, v in face_cols.items()},
                   min_h_gap=round(min(h_gaps), 5) if h_gaps else 99.0,
                   min_v_gap=round(min(v_gaps), 5) if v_gaps else 99.0,
                   n_pairs=len(gaps), min_pair_gap=round(min(gaps), 5) if gaps else 99.0,
                   n_h_adj=len(h_dups), n_v_adj=len(v_dups),
                   same_variant_h=same_h, same_variant_v=same_v)
        return out

    # ---- rigs: the acceptance shapes (TowerWing + CompoundTest classes + wide wall)
    # compound windows: ONE row (their wing walls are 1.2-1.4 m high - the row-fit
    # gate drops any row that would float above its wall), sill 0.25 world m
    slots_specs = [
        ("SlotsTowerWing", make_tower_wing, (96, -60, 0), 1),
        ("SlotsCompound", make_compound, (112, -60, 0), 1),
    ]
    slots_res = {}
    for tag, builder, loc, wrows in slots_specs:
        host = builder(tag, col_scene)
        host.location = loc
        # compound walls are 1.2-3.2 m wide: BOTH layers use Explicit 2 columns so
        # the door layer (First Only) and the window layer (Skip First) share ONE
        # grid - door and window can never land on the same column
        de = dict(slots_door_extra, **{"Count Mode": "Explicit", "Slot Count": 2})
        we = dict(slots_win_extra, **{"Count Mode": "Explicit", "Slot Count": 2,
                                      "Slot Rows": wrows, "Sill Height": 0.25})
        dress_slots(host, de, we)
        slots_res[tag] = slots_accept(tag, host, win_rows=wrows)
        results.setdefault("slots_rigs", {})[tag] = dict(location=loc, **slots_res[tag])
        log(f"  {tag}: {slots_res[tag]['n_doors']} doors + {slots_res[tag]['n_windows']} windows, "
            f"faces={slots_res[tag]['faces_used']}")

    # wide wall + half-size wall: wall-length-derived counts (doubling the wall
    # must roughly double the opening count)
    wall_big = make_wide_wall("SlotsWallBig", col_scene, 12.0); wall_big.location = (132, -60, 0)
    wall_small = make_wide_wall("SlotsWallSmall", col_scene, 6.0); wall_small.location = (152, -60, 0)
    dress_slots(wall_big, slots_door_extra, dict(slots_win_extra, **{"Sill Height": 0.9}))
    dress_slots(wall_small, slots_door_extra, dict(slots_win_extra, **{"Sill Height": 0.9}))
    slots_res["SlotsWallBig"] = slots_accept("SlotsWallBig", wall_big, win_rows=2)
    slots_res["SlotsWallSmall"] = slots_accept("SlotsWallSmall", wall_small, win_rows=2)

    def long_face_cols(res):
        return max(res["faces_used"].values()) if res["faces_used"] else 0

    cols_big, cols_small = long_face_cols(slots_res["SlotsWallBig"]), long_face_cols(slots_res["SlotsWallSmall"])
    n_big = slots_res["SlotsWallBig"]["n_doors"] + slots_res["SlotsWallBig"]["n_windows"]
    n_small = slots_res["SlotsWallSmall"]["n_doors"] + slots_res["SlotsWallSmall"]["n_windows"]
    check("slots[wall-length]: doubling the wall width doubles the opening columns "
          "(wall-length-derived counts, Per Width = 2.5 m per opening)",
          cols_small >= 1 and cols_big == 2 * cols_small,
          f"6.0 m wall -> {cols_small} columns, 12.0 m wall -> {cols_big} columns "
          f"(ratio {cols_big / max(cols_small, 1):.2f}); total openings {n_small} -> {n_big}")
    check("slots[No-Repeat]: adjacency evidence on the wide wall "
          "(both horizontal and vertical neighbour pairs exercised)",
          slots_res["SlotsWallBig"]["n_h_adj"] >= 2 and slots_res["SlotsWallBig"]["n_v_adj"] >= 2,
          f"SlotsWallBig adjacencies: {slots_res['SlotsWallBig']['n_h_adj']} horizontal, "
          f"{slots_res['SlotsWallBig']['n_v_adj']} vertical "
          f"(Min Gap X {slots_res['SlotsWallBig']['min_h_gap']}, "
          f"Min Gap Z {slots_res['SlotsWallBig']['min_v_gap']})")
    results["slots_wall_scaling"] = dict(
        cols_6m=cols_small, cols_12m=cols_big,
        openings_6m=n_small, openings_12m=n_big,
        res_6m=slots_res["SlotsWallSmall"], res_12m=slots_res["SlotsWallBig"])

    # ================================================== v2.5 BUG REPRO + FIX
    log("\n== v2.5 BUG REPRO: the user's tower+wing shape (door on the wing roof + black triangle) ==")
    bug_before = make_bug_repro("BugBefore", col_scene)
    bug_before.location = (170, -60, 0)
    bug_after = make_bug_repro("BugAfter", col_scene)
    bug_after.location = (188, -60, 0)

    # BEFORE = v2.5-pre behavior on the exact shape: random Fit, Ground Floor
    # Only OFF, no Max Base Height ceiling, legacy [0, th] cladding tiles
    m_bb1 = bug_before.modifiers.new("VM_SceneDetailer_Planks", "NODES"); m_bb1.node_group = ng
    set_params(m_bb1, ng, dict(plank_params, **{"Primary Props": col_plank_l}))
    m_bb2 = bug_before.modifiers.new("VM_RoofCap", "NODES"); m_bb2.node_group = ng_roof
    set_params(m_bb2, ng_roof, roofcap_params)
    m_bb3 = bug_before.modifiers.new("VM_SceneDetailer_Shingles", "NODES"); m_bb3.node_group = ng
    set_params(m_bb3, ng, dict(shingle_params, **{"Primary Props": col_shingle_l}))
    m_bb4 = bug_before.modifiers.new("VM_SceneDetailer_Door", "NODES"); m_bb4.node_group = ng
    legacy_door = dict(shape_door_params, **{
        "Slot Layout": "Random", "Ground Floor Only": False, "Max Base Height": 100.0,
        # density low enough that the first-N cap spans ALL eligible faces (the
        # roof-adjacent strip is the 4th eligible face and must stay reachable)
        "Density": 0.15, "Max Instances": 6, "Min Face Width": 1.0, "Min Face Height": 1.6})
    bug_faces = face_table(bug_before)
    bseed, btried, bfb = search_shape_seed(bug_before, m_bb4, legacy_door, "Door_",
                                           mk_door_pred(bug_faces, want_raised=True))
    log(f"  BugBefore: legacy seed {bseed} after {btried} candidates (roof-door repro)")

    # AFTER = the new rules on the SAME shape: Slots + Ground Floor Only ON +
    # Max Base Height 0.5 + straddled cladding tiles (door Min Face Width 1.5 so
    # the fan's narrow triangle fragments never stack door slots on one column)
    dress_slots(bug_after, dict(slots_door_extra, **{"Seed": 7, "Min Face Width": 1.5}),
                dict(slots_win_extra, **{"Sill Height": 0.35, "Seed": 7}))

    def roof_door_report(host, ground_only_expected):
        faces = face_table(host)
        lo_h, hi_h = host_planes(host)
        doors = inst_boxes(host, "Door_")
        raised, on_roof = [], []
        for bx in doors:
            f, _ = match_face(faces, bx["n"], bx["org"], bx)
            if f is None:
                continue
            if f["min_z"] > lo_h.z + 0.5 + 0.05:
                raised.append((bx["name"], round(bx["lo"].z, 3), round(f["min_z"], 3)))
        return raised, len(doors)

    raised_b, n_d_b = roof_door_report(bug_before, False)
    raised_a, n_d_a = roof_door_report(bug_after, True)
    check("bugfix(roof-door): the user's exact tower+wing shape REPRODUCES with v2.5-pre rules "
          "(Ground Floor Only OFF, no ceiling) - a door stands on the wing roof via the "
          "roof-adjacent tower strip (base z == the strip's bottom edge == the roof surface)",
          len(raised_b) >= 1,
          f"{n_d_b} doors with legacy rules; roof-adjacent (name, base_z, face_base)={raised_b}")
    check("bugfix(roof-door): with the v2.5 rules (Ground Floor Only ON + Max Base Height 0.5) "
          "the SAME shape gets zero roof-adjacent doors - the case is impossible",
          n_d_a > 0 and not raised_a,
          f"{n_d_a} doors with the new rules; roof-adjacent doors={raised_a}")

    # black triangle: cladding coverage of the flipped-normal triangle fragment.
    # The discriminative metric is ORIENTATION-FREE: how far each tile's back
    # side CROSSES the wall plane. Legacy [0, th] tiles never cross (back face
    # coplanar -> z-fight on inward-wound fragments -> the black triangle);
    # straddled tiles cross by th/2 (every wall face covered, any winding).
    def triangle_report(host):
        faces = face_table(host)
        # the flipped fill = a wall face whose winding disagrees with the
        # MAJORITY of its coplanar neighbours (the extrusion-fill signature)
        flipped = []
        for f in faces:
            if abs(f["n"].z) > 0.35:
                continue
            same = opp = 0
            for g in faces:
                if g is f or abs(g["n"].z) > 0.35:
                    continue
                if abs((f["c"] - g["c"]).dot(Vector(f["n"]))) < 0.05:
                    d = Vector(f["n"]).dot(Vector(g["n"]))
                    if d > 0.5:
                        same += 1
                    elif d < -0.5:
                        opp += 1
            if opp > same and opp > 0:
                flipped.append(f["idx"])
        planks = inst_boxes(host, "Plank_") + inst_boxes(host, "PlankL_")
        crossings, per_face_tiles = [], {}
        for p in planks:
            f, _ = match_face(faces, p["n"], p["org"], p)
            if f is None:
                continue
            n = Vector(f["n"])
            cross = -min((Vector(c) - Vector(p["org"])).dot(n) for c in (p["lo"], p["hi"]))
            crossings.append(round(cross, 4))
            per_face_tiles[f["idx"]] = per_face_tiles.get(f["idx"], 0) + 1
        return sorted(set(flipped)), crossings, per_face_tiles

    flip_b, cross_b, tiles_b = triangle_report(bug_before)
    flip_a, cross_a, tiles_a = triangle_report(bug_after)
    check("bugfix(black-triangle): root cause = cladding on a flipped-normal triangle fragment "
          "(extrusion fill): v2.5-pre tiles grew [0, th] from the wall plane -> on an inward-wound "
          "fragment they buried INSIDE the wall and z-fought its coplanar backs -> bare black "
          "triangle. v2.5 tiles STRADDLE the plane and cover every wall face whatever its winding",
          flip_b and flip_a and cross_b and max(cross_b) <= 0.001
          and cross_a and min(cross_a) >= 0.005,
          f"flipped fill faces before={flip_b} after={flip_a}; tile back-side crossing of the "
          f"wall plane BEFORE max={max(cross_b) if cross_b else 99} (never crosses -> z-fight -> "
          f"black), AFTER min={min(cross_a) if cross_a else -99} (straddles -> covered); "
          f"tiles per face before={tiles_b} after={tiles_a}")
    results["bug_fix"] = dict(
        before=dict(seed=bseed, seeds_tried=btried, n_doors=n_d_b,
                    roof_adjacent=raised_b, flipped=flip_b,
                    tile_crossing=sorted(cross_b)[:12], tiles_per_face=tiles_b),
        after=dict(n_doors=n_d_a, roof_adjacent=raised_a, flipped=flip_a,
                   tile_crossing=sorted(cross_a)[:12], tiles_per_face=tiles_a))

    # ================================================== v2.5 PACK-SWAP DEMO
    log("\n== v2.5 PACK-SWAP: one base model, two full looks, socket-level pack swap ==")
    col_medieval = bpy.data.collections["MedievalWindows_WALLFLAT"]
    ps_looked = []
    pack_hosts = []
    for i, (tag, wcol) in enumerate((("PackSwapA", col_windows),
                                     ("PackSwapB", col_medieval))):
        host = make_wide_wall(tag, col_scene, 6.0)
        host.location = (206 + 16 * i, -60, 0)
        m4, m5, dp, wp = dress_slots(host, dict(slots_door_extra, **{"Seed": 11}),
                                     dict(slots_win_extra, **{"Seed": 11, "Sill Height": 0.9}),
                                     win_col=wcol)
        pack_hosts.append((tag, host, m4, m5))
        ps_looked.append(tag)
    (tag_a, host_a, m4_a, m5_a), (tag_b, host_b, m4_b, m5_b) = pack_hosts

    def pack_snapshot(host, wpre):
        hinv = host.matrix_world.inverted()
        doors = inst_boxes(host, "Door_")
        wins = inst_boxes(host, wpre)
        dpos = sorted(tuple(round(v, 3) for v in (hinv @ b["org"])) for b in doors)
        wpos = sorted(tuple(round(v, 3) for v in (hinv @ b["org"])) for b in wins)
        return dict(n_doors=len(doors), n_windows=len(wins),
                    door_names=sorted({b["name"] for b in doors}),
                    win_names=sorted({b["name"] for b in wins}),
                    door_slots=dpos, win_slots=wpos)

    snap_a = pack_snapshot(host_a, "Window_")
    snap_b = pack_snapshot(host_b, "MedievalWindows_")
    same_slots = (snap_a["door_slots"] == snap_b["door_slots"]
                  and snap_a["win_slots"] == snap_b["win_slots"])
    check("pack-swap: same base model, identical slot layout - ONLY the pack collection "
          "sockets are repointed (Windows: louvered shutters -> MedievalWindows); every "
          "instance origin identical between the two looks",
          same_slots and snap_a["n_windows"] == snap_b["n_windows"]
          and snap_a["win_names"] != snap_b["win_names"],
          f"look A: {snap_a['n_doors']} doors {snap_a['door_names'][:3]} + "
          f"{snap_a['n_windows']} windows {snap_a['win_names']}; "
          f"look B: {snap_b['n_doors']} doors + {snap_b['n_windows']} windows "
          f"{snap_b['win_names'][:4]}...; slot origins identical={same_slots}")
    same_ng = (m4_a.node_group == m4_b.node_group == ng and m5_a.node_group == m5_b.node_group == ng)
    check("pack-swap: both looks run on the SAME VM_SceneDetailer node group "
          "(socket-level swap, zero pack-specific code)",
          same_ng and host_a.data.vertices.keys() == host_b.data.vertices.keys(),
          f"shared node group={same_ng}; identical base mesh "
          f"({len(host_a.data.vertices)} verts each)")
    results["pack_swap"] = dict(look_a=snap_a, look_b=snap_b, slots_identical=same_slots,
                                same_node_group=bool(same_ng))

    # ================================================== STAGE 7: USER SHAPE 2 (v2.6)
    # The user's 2026-10-22 bug report on his OWN custom massing:
    #   (1) Fit DEAD: zero doors/windows on the shape -> root cause + fix
    #   (2) roof style: flat tops must get FLAT caps (no invented gables), zero
    #       holes at junctions
    #   (3) HouseCraft parity: manual painted placement + exact counts
    log("\n== STAGE 7: UserShape2 (user's custom massing) - v2.6 fixes ==")
    u2 = make_user_shape2("UserShape2", col_scene)
    u2.location = (162.0, -60.0, 0.0)
    u2_faces = face_table(u2)
    u2_walls = [f for f in u2_faces if abs(f["n"].z) <= 0.35]
    log(f"  UserShape2 rebuilt from his screenshots: {len(u2_faces)} faces, "
        f"{len(u2_walls)} wall faces, max wall height "
        f"{max(f['h'] for f in u2_walls):.3f} m, wall widths "
        f"{sorted({round(f['w'], 2) for f in u2_walls})}")
    render_from("preview_user2_massing", (165.6, -64.6, 3.4), (163.2, -59.9, 1.0), 38)

    u2_roof = u2.modifiers.new("VM_RoofCap", "NODES"); u2_roof.node_group = ng_roof
    # v2.7: pin the roof state explicitly (the group default is 'Flat' now, but
    # the shipped demo must not depend on defaults)
    set_params(u2_roof, ng_roof, {"Pitch": math.radians(35.0), "Overhang": 0.15,
                                  "Style": "Flat", "Incline": math.radians(2.5),
                                  "Fascia": 0.12, "Roof Material": mat_roof,
                                  "Min Roof Face Size": 0.4, "Largest Face Only": False})
    u2_door = u2.modifiers.new("VM_SceneDetailer_Door", "NODES"); u2_door.node_group = ng
    u2_win = u2.modifiers.new("VM_SceneDetailer_Windows", "NODES"); u2_win.node_group = ng

    def u2_count(pref):
        return len(inst_boxes(u2, pref))

    def u2_update(*mods):
        for m_ in mods:
            u2.update_tag()
        bpy.context.view_layer.update()

    # ---- the v2.5 stack the user dressed with (sockets read from his session's
    # autosave VM_Starter_33160_autosave.blend == the delivered v2.5 Slots demo
    # stack: Explicit-2, doors 'First Only', windows 'Skip First', door Opening
    # Height 2.2 m, window 0.9 m + 0.25 sill)
    u2_d_v25 = dict(defaults, **{
        "Placement Mode": "Fit", "Face Zone": "Walls",
        "Stand On Face Base": True, "Sill Height": 0.0, "Sill Line": "Common Z",
        "Min Face Width": 1.0, "Min Face Height": 1.6,
        "Ground Floor Only": True, "Ground Tolerance": 0.1, "Max Base Height": 0.5,
        "Slot Layout": "Slots", "Count Mode": "Explicit", "Slot Count": 2,
        "Opening Width": 1.5, "Opening Height": 2.2,
        "Min Gap X": 0.4, "Min Gap Z": 0.3, "Slot Rows": 1, "Row Spacing": 2.4,
        "Column Select": "First Only",
        "Density": 0.12, "Embed": 0.02, "Backing Offset": 0.0435,
        "Scale Min": 1.0, "Scale Max": 1.0,
        "Primary Props": col_doors, "Debris/Trash Props": col_debris, "Debris Ratio": 0.0,
        "Max Instances": 40, "Seed": 5, "Opening Fit": "Drop"})
    u2_w_v25 = dict(u2_d_v25, **{
        "Sill Height": 0.25, "Min Face Width": 1.2, "Min Face Height": 1.1,
        "Ground Floor Only": False, "Opening Width": 0.8, "Opening Height": 0.9,
        "Column Select": "Skip First", "Scale Min": 0.5, "Scale Max": 0.5,
        "Primary Props": col_windows})

    def u2_gate_evidence(P, colsel):
        """Per-face gate evidence: exactly which filter rejected each wall."""
        oh, sill = P["Opening Height"], P["Sill Height"]
        rows = []
        for f in u2_walls:
            fails = []
            if f["w"] < P["Min Face Width"]:
                fails.append(f"MinFaceWidth {f['w']:.2f}<{P['Min Face Width']}")
            if f["h"] < P["Min Face Height"]:
                fails.append(f"MinFaceHeight {f['h']:.2f}<{P['Min Face Height']}")
            # Common Z sill line = host zmin (0) + Sill Height
            row_base = sill
            if not (row_base + oh <= f["h"] + 1e-6):
                fails.append(f"row-fit OpeningHeight {oh} > wall {f['h']:.2f} - sill {sill}")
            gap_pitch = P["Opening Width"] + P["Min Gap X"] + 2 * P["Slot Jitter"]
            cols = max(1, int(f["w"] / gap_pitch))
            if P["Count Mode"] == "Explicit":
                cols = min(P["Slot Count"], cols)
            if colsel == "First Only" and cols < 1:
                fails.append("First Only on a 0-column grid")
            if colsel == "Skip First" and cols < 2:
                fails.append(f"Skip First on a {cols}-column grid (gap law clamps it)")
            rows.append(dict(idx=f["idx"], w=round(f["w"], 3), h=round(f["h"], 3),
                             cols=cols, fails=fails))
        return rows

    # ---- (A) BEFORE: the user's v2.5 stack reproduces the bug exactly --------
    set_params(u2_door, ng, u2_d_v25)
    set_params(u2_win, ng, u2_w_v25)
    u2_update(u2_door, u2_win)
    n_d_before, n_w_before = u2_count("Door_"), u2_count("Window_")
    ev_d = u2_gate_evidence(u2_d_v25, "First Only")
    ev_w = u2_gate_evidence(u2_w_v25, "Skip First")
    log(f"  REPRO (v2.5 stack, Opening Fit=Drop): doors={n_d_before} windows={n_w_before}")
    for r in ev_d + ev_w:
        log(f"    face {r['idx']}: {r['w']}x{r['h']} cols={r['cols']} fails={r['fails']}")
    check("user2(FIT-DEAD repro): the user's v2.5 stack on his exact massing places ZERO doors "
          "(row-fit gate: every wall is shorter than the 2.2 m Opening Height)",
          n_d_before == 0 and all(r["fails"] for r in ev_d),
          f"{n_d_before} doors; wall faces={len(ev_d)}; rejections="
          f"{[(r['idx'], r['fails']) for r in ev_d][:8]}")
    check("user2(FIT-DEAD repro): ZERO windows (row-fit on short walls + the cross-layer "
          "'Skip First'/'Explicit-2' split emptied by the gap-law 1-column clamp)",
          n_w_before == 0 and all(r["fails"] for r in ev_w),
          f"{n_w_before} windows; rejections={[(r['idx'], r['fails']) for r in ev_w][:8]}")
    results["user2_repro"] = dict(n_doors=n_d_before, n_windows=n_w_before,
                                  door_gates=ev_d, win_gates=ev_w,
                                  params=dict(door=dict((k, u2_d_v25[k]) for k in
                                                        ("Slot Layout", "Count Mode", "Slot Count",
                                                         "Opening Width", "Opening Height",
                                                         "Column Select", "Min Face Width",
                                                         "Min Face Height", "Opening Fit")),
                                              win=dict((k, u2_w_v25[k]) for k in
                                                       ("Slot Layout", "Count Mode", "Slot Count",
                                                        "Opening Width", "Opening Height",
                                                        "Sill Height", "Column Select",
                                                        "Min Face Width", "Min Face Height",
                                                        "Opening Fit"))))

    # ---- (B) AFTER: v2.6 'Scale To Face' (contract change, now the default) --
    set_params(u2_door, ng, dict(u2_d_v25, **{"Opening Fit": "Scale To Face"}))
    set_params(u2_win, ng, dict(u2_w_v25, **{"Opening Fit": "Scale To Face"}))
    u2_update(u2_door, u2_win)
    n_d_fit, n_w_fit = u2_count("Door_"), u2_count("Window_")
    log(f"  AFTER (same stack, Opening Fit=Scale To Face): doors={n_d_fit} windows={n_w_fit}")
    check("user2(fix): 'Scale To Face' puts doors back on the ground-floor walls of the SAME "
          "shape with the SAME v2.5 stack (openings auto-shrink to the 2.0 m walls)",
          n_d_fit > 0, f"{n_d_fit} doors (was 0); boxes="
                       f"{[(round(b['lo'].z, 3), round((b['hi'] - b['lo']).z, 3)) for b in inst_boxes(u2, 'Door_')]}")

    # ---- (C) acceptance: DEFAULT Fit settings show doors AND windows ---------
    # v2.8.2: openings priced at the PACK sizes (the delivered demo recipe) -
    # the generic 1.4 m nominal legally holds ONE opening on a 2 m wall, so no
    # gap-law engine can show doors AND windows on this 2.67 m massing at once
    u2_default_states = {}
    for layout in ("Slots", "Random"):
        set_params(u2_door, ng, dict(defaults, **{
            "Placement Mode": "Fit", "Face Zone": "Walls", "Slot Layout": layout,
            "Stand On Face Base": True, "Seed": 0,
            "Opening Width": 0.7, "Opening Height": 1.85,
            "Primary Props": col_doors, "Debris/Trash Props": col_debris, "Debris Ratio": 0.0,
            "Max Instances": 40}))
        set_params(u2_win, ng, dict(defaults, **{
            "Placement Mode": "Fit", "Face Zone": "Walls", "Slot Layout": layout,
            "Stand On Face Base": True, "Sill Height": 0.9, "Seed": 1,
            "Opening Width": 0.42, "Opening Height": 0.95, "Min Gap X": 0.05,
            "Primary Props": col_windows, "Debris/Trash Props": col_debris, "Debris Ratio": 0.0,
            "Scale Min": 0.35, "Scale Max": 0.35, "Max Instances": 40}))
        u2_update(u2_door, u2_win)
        nd, nw = u2_count("Door_"), u2_count("Window_")
        u2_default_states[layout] = dict(n_doors=nd, n_windows=nw)
        log(f"  DEFAULT Fit settings (Slot Layout={layout}): doors={nd} windows={nw}")
    check("user2(accept): under the default Fit stack (Scale To Face) with pack-sized "
          "openings the rebuilt massing shows doors AND windows on the ground-floor walls "
          "(both Slot layouts)",
          all(v["n_doors"] > 0 and v["n_windows"] > 0 for v in u2_default_states.values()),
          f"default-settings counts: {u2_default_states}")
    results["user2_default_fit"] = u2_default_states

    # ---- (D) MANUAL placement via painted VERTEX GROUP ----------------------
    # Paint ONE wall (the tower's west wall) with the vertex group
    # 'VM_Slots_Doors' exactly as the user would in Weight Paint mode.
    u2_west = [f for f in u2_walls if f["n"].x < -0.9 and abs(f["max_z"] - 2.0) < 0.01]
    assert len(u2_west) == 1, u2_west
    painted_face = u2_west[0]

    def sel_painted(p):
        n = p.normal
        zs = [u2.data.vertices[i].co.z for i in p.vertices]
        return n.x < -0.9 and abs(max(zs) - 2.0) < 0.01

    paint_slot_group(u2, "VM_Slots_Doors", sel_painted)
    set_params(u2_door, ng, dict(defaults, **{
        "Placement Mode": "Fit", "Face Zone": "Walls", "Slot Layout": "Slots",
        "Stand On Face Base": True, "Seed": 0,
        "Manual Mask": True, "Manual Mask Group": "VM_Slots_Doors",
        "Manual Threshold": 0.5,
        "Primary Props": col_doors, "Debris/Trash Props": col_debris, "Debris Ratio": 0.0,
        "Max Instances": 40}))
    set_params(u2_win, ng, dict(defaults, **{
        "Placement Mode": "Fit", "Face Zone": "Walls", "Slot Layout": "Slots",
        "Stand On Face Base": True, "Sill Height": 0.9, "Seed": 1,
        "Manual Mask": True, "Manual Mask Group": "VM_Slots_Nowhere",  # unpainted -> none
        "Primary Props": col_windows, "Debris/Trash Props": col_debris, "Debris Ratio": 0.0,
        "Scale Min": 0.5, "Scale Max": 0.5, "Max Instances": 40}))
    u2.update_tag(); bpy.context.view_layer.update()
    m_doors = inst_boxes(u2, "Door_")
    m_wins = inst_boxes(u2, "Window_")
    inside, outside = [], []
    for b in m_doors:
        f, d = match_face(u2_faces, b["n"], b["org"], b)
        du = abs((Vector(b["org"]) - painted_face["c"]).dot(painted_face["u"]))
        dv = abs((Vector(b["org"]) - painted_face["c"]).dot(painted_face["v"]))
        ok = (f is not None and f["idx"] == painted_face["idx"]
              and du <= painted_face["w"] / 2 + 0.3 and dv <= painted_face["h"] / 2 + 0.3)
        (inside if ok else outside).append(dict(name=b["name"], du=round(du, 3), dv=round(dv, 3),
                                                face=f["idx"] if f else None))
    check("user2(manual): openings land ONLY inside the painted vertex-group area "
          "(bbox containment on the painted wall), zero outside",
          len(m_doors) >= 1 and not outside and not m_wins,
          f"painted wall face {painted_face['idx']} "
          f"(w={painted_face['w']:.2f} h={painted_face['h']:.2f}): "
          f"{len(m_doors)} doors inside={inside}, outside={outside}; "
          f"windows with unpainted group name: {len(m_wins)} (expected 0)")
    results["user2_manual"] = dict(painted_face=painted_face["idx"],
                                   painted_w=painted_face["w"], painted_h=painted_face["h"],
                                   doors_inside=inside, doors_outside=outside,
                                   n_windows_unpainted=len(m_wins))
    # view the PAINTED wall head-on (it faces -X world / west)
    render_from("preview_user2_manual", (157.5, -61.8, 2.4), (161.9, -58.9, 0.95), 45)

    # ---- (E) EXACT COUNT: 'Exactly N' per layer -----------------------------
    set_params(u2_door, ng, dict(defaults, **{
        "Placement Mode": "Fit", "Face Zone": "Walls", "Slot Layout": "Slots",
        "Count Mode": "Exact N", "Exact Count": 2, "Exact Pick": "Spread",
        "Stand On Face Base": True, "Seed": 0, "Manual Mask": False,
        "Opening Width": 0.7, "Opening Height": 1.85,
        "Primary Props": col_doors, "Debris/Trash Props": col_debris, "Debris Ratio": 0.0,
        "Max Instances": 40}))
    set_params(u2_win, ng, dict(defaults, **{
        "Placement Mode": "Fit", "Face Zone": "Walls", "Slot Layout": "Slots",
        "Count Mode": "Exact N", "Exact Count": 1, "Exact Pick": "Spread",
        "Stand On Face Base": True, "Sill Height": 0.55, "Seed": 1, "Manual Mask": False,
        "Opening Width": 0.42, "Opening Height": 0.95, "Min Gap X": 0.05,
        "Primary Props": col_windows, "Debris/Trash Props": col_debris, "Debris Ratio": 0.0,
        "Scale Min": 0.35, "Scale Max": 0.35, "Max Instances": 40}))
    u2.update_tag(); bpy.context.view_layer.update()
    n_d_exact, n_w_exact = u2_count("Door_"), u2_count("Window_")
    check("user2(exact count): 'Exactly-2-Doors' places EXACTLY 2 doors (and Exactly-1 "
          "window = 1) - HouseCraft choose-exactly-the-number parity",
          n_d_exact == 2 and n_w_exact == 1,
          f"doors={n_d_exact} (Exact Count 2), windows={n_w_exact} (Exact Count 1)")
    results["user2_exact"] = dict(n_doors=n_d_exact, n_windows=n_w_exact,
                                  door_slots=sorted(tuple(round(v, 3) for v in (u2.matrix_world.inverted() @ b["org"]))
                                                    for b in inst_boxes(u2, "Door_")))
    # north-west 3/4 view: the two exact doors land on the west tower wall and
    # the north upper-block wall - both visible from here
    render_from("preview_user2_exact2", (157.8, -55.8, 3.1), (162.1, -58.9, 0.9), 38)

    # ---- (F) RoofCap 'Flat': subtle incline, NO gable triangles, no holes ----
    set_params(u2_door, ng, dict(defaults, **{
        "Placement Mode": "Fit", "Face Zone": "Walls", "Slot Layout": "Slots",
        "Stand On Face Base": True, "Seed": 0, "Manual Mask": False,
        "Primary Props": col_doors, "Debris/Trash Props": col_debris, "Debris Ratio": 0.0,
        "Max Instances": 40}))
    set_params(u2_win, ng, dict(defaults, **{
        "Placement Mode": "Fit", "Face Zone": "Walls", "Slot Layout": "Slots",
        "Stand On Face Base": True, "Sill Height": 0.55, "Seed": 1, "Manual Mask": False,
        "Primary Props": col_windows, "Debris/Trash Props": col_debris, "Debris Ratio": 0.0,
        "Scale Min": 0.5, "Scale Max": 0.5, "Max Instances": 40}))
    set_params(u2_roof, ng_roof, {"Pitch": math.radians(35.0), "Overhang": 0.15,
                                  "Style": "Flat", "Incline": math.radians(2.5),
                                  "Fascia": 0.12, "Roof Material": mat_roof,
                                  "Min Roof Face Size": 0.4, "Largest Face Only": False})
    u2.update_tag(); bpy.context.view_layer.update()

    def cap_inclines(host):
        dg = bpy.context.evaluated_depsgraph_get(); dg.update()
        me = host.evaluated_get(dg).data
        mw = host.matrix_world
        nmat = mw.to_3x3().inverted().transposed()
        if "vm_roofgen" not in me.attributes:
            return [], []
        attr = me.attributes["vm_roofgen"]
        tops, gables = [], 0
        for p in me.polygons:
            v = attr.data[p.index].value
            if v >= 1.5:
                n = (nmat @ Vector(p.normal)).normalized()
                if n.z >= 0.9:
                    tops.append(round(math.degrees(math.acos(max(-1.0, min(1.0, n.z)))), 3))
            elif v >= 0.5:
                gables += 1
        return tops, gables

    rr_flat = roof_report(u2, overhang=0.15, style="Flat")
    tops, n_gable_faces = cap_inclines(u2)
    incl_err = max(abs(t - 2.5) for t in tops) if tops else 99.0
    log(f"  Flat roof: cap top inclines={tops} deg, gable faces={n_gable_faces}, "
        f"cap tops={rr_flat['cap_tops']} expected={rr_flat['expected_caps']}, "
        f"uncovered={rr_flat['uncovered']}")
    check("user2(flat roof): 'Flat' style caps every top with the subtle Incline measured "
          "at 2.5 deg (2-3 deg band), zero gable triangles invented",
          tops and incl_err <= 0.75 and n_gable_faces == 0,
          f"measured inclines={tops} deg (socket 2.5 deg, tolerance +/-0.75), "
          f"gable faces={n_gable_faces} (expected 0)")
    check("user2(flat roof): roof coverage COMPLETE - every flat top capped, zero interior "
          "exposed through the top (the gaping-hole bug is gone)",
          not rr_flat["uncovered"] and rr_flat["cap_tops"] == rr_flat["expected_caps"]
          and rr_flat["cap_tops"] == len([f for f in u2_faces if f["n"].z >= 0.98])
          and not rr_flat["strays"] and rr_flat["zero_area"] == 0,
          f"cap tops={rr_flat['cap_tops']} expected={rr_flat['expected_caps']} "
          f"(host tops={len([f for f in u2_faces if f['n'].z >= 0.98])}), "
          f"uncovered={rr_flat['uncovered']}, strays={rr_flat['strays']}, "
          f"zero-area={rr_flat['zero_area']}")
    results["user2_flat_roof"] = dict(inclines=tops, gable_faces=n_gable_faces,
                                      cap_tops=rr_flat["cap_tops"],
                                      expected_caps=rr_flat["expected_caps"],
                                      uncovered=rr_flat["uncovered"],
                                      strays=rr_flat["strays"],
                                      cap_regions=rr_flat["cap_regions"])
    render_from("preview_user2_flat_roof", (165.8, -63.2, 4.2), (163.2, -59.9, 1.5), 38)
    render_from("preview_user2_flat_top", (163.2, -60.0, 9.5), (163.2, -60.0, 0.0), 35)
    render_from("preview_user2_openings", (165.0, -64.4, 2.6), (162.7, -59.9, 1.0), 40)

    # ---- (G) same shape, Gable style for comparison (the user's screenshot) --
    set_params(u2_roof, ng_roof, {"Pitch": math.radians(35.0), "Overhang": 0.15,
                                  "Style": "Gable", "Roof Material": mat_roof,
                                  "Min Roof Face Size": 0.4, "Largest Face Only": False})
    u2.update_tag(); bpy.context.view_layer.update()
    rr_gable = roof_report(u2, overhang=0.15, style="Gable")
    tops_g, n_gable_faces_g = cap_inclines(u2)
    check("user2(gable comparison): same massing with Gable style generates the pitched "
          "gable roofs (comparison render) while keeping coverage complete via caps",
          n_gable_faces_g == rr_gable["expected_generated"] and not rr_gable["uncovered"],
          f"gable faces={n_gable_faces_g} expected={rr_gable['expected_generated']}, "
          f"caps={rr_gable['cap_tops']}, uncovered={rr_gable['uncovered']}")
    results["user2_gable_roof"] = dict(gable_faces=n_gable_faces_g,
                                       qualifying=rr_gable["qualifying"],
                                       caps=rr_gable["cap_tops"],
                                       uncovered=rr_gable["uncovered"])
    render_from("preview_user2_gable_roof", (165.8, -63.2, 4.2), (163.2, -59.9, 1.5), 38)

    # leave UserShape2 delivered in the FIXED default state (Flat roof + default
    # Fit openings) so the shipped blend opens showing the bug-free result
    set_params(u2_roof, ng_roof, {"Pitch": math.radians(35.0), "Overhang": 0.15,
                                  "Style": "Flat", "Incline": math.radians(2.5),
                                  "Fascia": 0.12, "Roof Material": mat_roof,
                                  "Min Roof Face Size": 0.4, "Largest Face Only": False})
    u2.update_tag(); bpy.context.view_layer.update()

    # ================================================== renders
    log("\n== renders (Cycles CPU 32spp 960x540) ==")
    render_from("preview_stage1_fit_walls", (64.2, -5.2, 2.6), (60, 0, 1.0), 35)
    render_from("preview_stage2_zones_roof", (84.0, -5.0, 3.6), (80, 0, 1.0), 35)
    render_from("preview_stage3_cladding", (72.6, -3.4, 1.9), (70, 0, 1.0), 45)
    render_from("preview_stage4_materials", (93.6, -4.4, 2.8), (90, 0, 1.0), 35)
    render_from("preview_stage5_roofcap", (106.5, -10.5, 5.5), (103.5, 0, 1.6), 35)
    render_from("preview_starter_house", (-3.0, -47.6, 2.3), (0, -40, 1.3), 38)
    # v2.7: the two design languages side by side + the user's exact action
    render_from("preview_starter_pair", (-2.8, -48.8, 3.4), (2.75, -40, 1.4), 32)
    render_from("preview_starter_compound", (7.2, -47.2, 4.8), (12.4, -40, 1.5), 35)
    render_from("preview_starter_compound_top", (12.4, -40.0, 11.0), (12.4, -40.0, 0.0), 35)
    render_from("preview_gable_showcase", (2.4, -46.2, 3.2), (5.5, -40, 1.5), 40)
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

    # ---- v2.4 shape-matrix renders (CompoundTest + closeup are the acceptance shots)
    render_from("preview_compound", (8.5, -67.5, 5.2), (2.4, -59.6, 1.7), 32)
    ct_doors_w = inst_boxes(ct, "Door_")
    ct_faces_w = face_table(ct)
    step_box = None
    for bx in ct_doors_w:
        f, _ = match_face(ct_faces_w, bx["n"], bx["org"], bx)
        if f is not None and f["min_z"] > 0.5:
            step_box = bx      # the Max Base Height override state has upper doors
            break
    if step_box is None and ct_doors_w:
        step_box = ct_doors_w[0]   # v2.5 default state: ground doors only
    if step_box:
        p_w = Vector(step_box["org"])
        n0 = Vector((step_box["n"][0], step_box["n"][1], step_box["n"][2]))
        tan0 = Vector((-n0.y, n0.x, 0.0)).normalized()
        cam_pos = p_w + n0 * 3.4 + tan0 * 1.7 + Vector((0, 0, 1.1))
        render_from("preview_compound_closeup", tuple(cam_pos), tuple(p_w + Vector((0, 0, 0.5))), 40)
        log(f"  compound close-up aimed at door (base z={step_box['lo'].z:.3f}, normal {tuple(n0)})")
    else:
        render_from("preview_compound_closeup", (5.0, -63.0, 2.2), (2.0, -59.8, 1.5), 40)
    render_from("preview_shape_scaled", (23.5, -67.5, 7.5), (16.0, -59.3, 2.2), 32)
    render_from("preview_shape_tower", (35.5, -65.5, 5.0), (30.2, -59.5, 1.7), 35)
    render_from("preview_shape_warehouse", (52.5, -65.5, 5.0), (47.0, -58.4, 1.6), 35)
    render_from("preview_reflow", (70.5, -66.5, 6.5), (64.6, -59.4, 2.3), 32)
    # v2.4.1 acceptance shots: the two previews the world-space fix is judged on -
    # CompoundScaled tiles must read as planks (not 1.6x blocks) and ReflowTest
    # must keep its edit-mode re-tiling look
    render_from("preview_compoundscaled", (21.5, -67.0, 5.8), (15.6, -59.2, 2.5), 35)
    render_from("preview_reflow_after", (69.5, -66.0, 5.5), (64.2, -59.5, 2.2), 35)

    # ---- v2.5 acceptance shots: Slots placement math + bug before/after + pack swap
    render_from("preview_slots_towerwing", (103.0, -68.0, 6.0), (98.3, -59.2, 2.0), 32)
    render_from("preview_slots_compound", (119.5, -66.5, 5.4), (114.2, -59.4, 1.9), 35)
    render_from("preview_slots_widerow", (138.0, -72.0, 5.5), (138.0, -59.5, 2.0), 30)
    # bug before/after: the SAME camera relative to the SAME user shape
    render_from("preview_bug_doors_before", (181.0, -67.5, 5.6), (173.6, -58.6, 2.1), 32)
    render_from("preview_bug_doors_before_crop", (178.0, -64.5, 3.6), (172.6, -59.4, 2.6), 45)
    render_from("preview_bug_doors_after", (199.0, -67.5, 5.6), (191.6, -58.6, 2.1), 32)
    render_from("preview_bug_doors_after_crop", (196.0, -64.5, 3.6), (190.6, -59.4, 2.6), 45)

    # viewport-look (Workbench studio lighting) shots of the black-triangle
    # artifact: backfacing geometry shades BLACK exactly like the user's solid
    # viewport - before = the bare flipped fill (tiles buried inside the wall),
    # after = the same fragment fully clad by the straddled tiles
    def render_viewport(tag, loc, target, lens=32):
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.display.shading.light = "STUDIO"
        scene.display.shading.color_type = "MATERIAL"
        render_from(tag, loc, target, lens)
        scene.render.engine = "CYCLES"

    render_viewport("preview_bug_triangle_before_viewport", (176.5, -63.6, 3.4),
                    (171.4, -59.7, 2.7), 50)
    render_viewport("preview_bug_triangle_after_viewport", (194.5, -63.6, 3.4),
                    (189.4, -59.7, 2.7), 50)
    # pack-swap: same camera offset on each look + the side-by-side pair
    render_from("preview_packswap_a", (201.5, -65.5, 3.8), (207.0, -59.0, 1.4), 35)
    render_from("preview_packswap_b", (217.5, -65.5, 3.8), (223.0, -59.0, 1.4), 35)
    render_from("preview_packswap_pair", (214.0, -84.0, 7.0), (214.0, -59.0, 1.5), 32)

    # ================================================== v2.8 STAGE 9: the user's
    # own massing (Cube.001) + the phantom-slab / opening-spread acceptance
    log("\n== v2.8: user massing Cube.001 (verbatim) + bug-fix acceptance ==")
    u3 = make_user_massing("Cube.001", col_scene)
    make_user_stray_cube("Cube", col_scene)
    # his EXACT saved modifier stack (sockets read from the delivered file)
    u3_plank = dict(plank_params)
    u3_roof = {"Pitch": math.radians(35.0), "Overhang": 0.25, "Style": "Flat",
               "Incline": math.radians(2.5), "Fascia": 0.12, "Roof Material": mat_roof}
    u3_shingle = dict(defaults, **{
        "Placement Mode": "Cladding", "Face Zone": "Roof",
        "Row Height": 0.11, "Row Overlap": 0.35, "Stagger": 0.5, "Jitter": 0.004,
        "Slot Width": 0.25, "Primary Props": col_shingle, "Debris/Trash Props": col_debris,
        "Debris Ratio": 0.0, "Scale Min": 1.0, "Scale Max": 1.0,
        "Wall Material": None, "Roof Material": None, "Floor Material": None,
        "Max Instances": 4000})
    u3_door = dict(defaults, **{
        "Placement Mode": "Fit", "Face Zone": "Walls", "Primary Props": col_doors,
        "Debris/Trash Props": col_debris, "Debris Ratio": 0.0,
        "Backing Offset": 0.0435, "Stand On Face Base": True, "Sill Height": 0.0,
        "Min Face Width": 0.6, "Min Face Height": 1.2, "Ground Floor Only": True,
        "Max Base Height": 0.5, "Slot Layout": "Random", "Density": 0.35, "Seed": 20,
        "Scale Min": 1.0, "Scale Max": 1.0, "Max Instances": 3,
        "Wall Material": None, "Roof Material": None, "Floor Material": None})
    u3_win = dict(defaults, **{
        "Placement Mode": "Fit", "Face Zone": "Walls", "Primary Props": col_windows,
        "Debris/Trash Props": col_debris, "Debris Ratio": 0.0,
        "Backing Offset": 0.0435, "Stand On Face Base": True, "Sill Height": 0.9,
        "Min Face Width": 1.5, "Min Face Height": 1.5, "Ground Floor Only": False,
        "Max Base Height": 0.5, "Slot Layout": "Random",
        "Density": 31.119234085083008, "Seed": 696, "Scale Min": 0.5, "Scale Max": 0.5,
        "Max Instances": 40,
        "Wall Material": None, "Roof Material": None, "Floor Material": None})
    m_u3 = []
    for _nm, _grp, _params in (("VM_SceneDetailer_Planks", ng, u3_plank),
                               ("VM_RoofCap", ng_roof, u3_roof),
                               ("VM_SceneDetailer_Shingles", ng, u3_shingle),
                               ("VM_SceneDetailer_Door", ng, u3_door),
                               ("VM_SceneDetailer_Windows", ng, u3_win)):
        _m = u3.modifiers.new(_nm, "NODES")
        _m.node_group = _grp
        set_params(_m, _grp, _params)
        m_u3.append(_m)
    u3.update_tag()
    bpy.context.view_layer.update()

    # ---- acceptance 1: cladding containment (the phantom wall slab) ----
    n_out_c, det_c = containment_check(u3, ("Plank", "Shingle"))
    faces3 = _poly2d(u3)
    keep3 = Counter()
    for (pre, org, lo, hi) in inst_table(u3, ("Plank", "Shingle")):
        lp = u3.matrix_world.inverted() @ Vector(org)
        for f in faces3:
            d = abs((lp - f["c"]).dot(f["n"]))
            if d > 0.05:
                continue
            rel = (lp - f["n"] * ((lp - f["c"]).dot(f["n"]))) - f["c"]
            if _pt_in_poly((rel.dot(f["u"]), rel.dot(f["v"])), f["poly"]):
                keep3[f["idx"]] += 1
                break
    nonrect = {f["idx"]: f for f in faces3 if f["area"] > 0.01 and f["W"] * f["H"] > 1e-6
               and f["area"] / (f["W"] * f["H"]) < 0.98}
    # v2.2 bbox layout would have produced these slots on the non-rect faces:
    def _bbox_slots(f, slot_w, overlap, row_h):
        sp = max(slot_w * (1 - overlap), 0.001)
        return max(1, math.ceil(f["W"] / sp)) * max(1, math.ceil(f["H"] / max(row_h, 0.001)))
    phantom_src = {}
    for fi, f in nonrect.items():
        z = f["n"].z
        zone = ("wall" if abs(z) <= 0.35 else ("roof" if 0.55 <= z < 0.92 else "other"))
        if zone == "wall":
            phantom_src[fi] = (_bbox_slots(f, 2.0, 0.05, 0.22), keep3.get(fi, 0), "plank")
        elif zone == "roof":
            phantom_src[fi] = (_bbox_slots(f, 0.25, 0.35, 0.11), keep3.get(fi, 0), "shingle")
    log(f"  v2.8 cladding: non-rect faces bbox_slots -> kept (v2.2 flooded the bbox): "
        f"{phantom_src}")
    check("v2.8(cladding containment): ZERO cladding anchors off-surface "
          "(the phantom wall slab cannot exist - anchor-on-surface test)",
          n_out_c == 0,
          f"{sum(keep3.values())} tiles kept on real surface, "
          f"{n_out_c} off-surface (0 required; v2.7 engine: 263 empty-air slots - "
          f"20 plank slots on the gable triangle f51 + 243 shingle slots from the "
          f"sliver fragments); strict planar-polygon outliers (diagnostic, known "
          f"false positives on non-planar slivers/cap faces)={det_c['strict_planar_outside']}")

    # ---- acceptance 2: opening spread (the cram-on-one-wall bug) ----
    sp3 = opening_spread(u3)
    log(f"  v2.8 openings: {sp3}")
    check("v2.8(opening spread): openings appear on >= 3 distinct walls of the user's "
          "object (round-robin spread, NOT first-N on one wall)",
          sp3["walls"] >= 3,
          f"{sp3['total']} openings on {sp3['walls']} walls, per-wall counts "
          f"{sorted(sp3['per_wall'].values())} (v2.7 engine: 43 openings, 1 wall)")
    check("v2.8(gap law): ZERO pairwise opening bbox intersections (doors vs doors, "
          "windows vs windows, doors vs windows - the dense overlapping row is gone)",
          sp3["intersections"] == 0,
          f"{sp3['pairs']} pairs tested, intersecting={sp3['intersections']}, "
          f"min pairwise bbox gap={sp3['min_gap']} m")
    check("v2.8(balanced spread): per-wall opening counts differ by <= 1",
          0 <= sp3["spread_diff"] <= 1,
          f"per-wall counts {sorted(sp3['per_wall'].values())}, max-min={sp3['spread_diff']}")

    # ---- determinism: same scene, same seeds -> identical evaluation ----
    s_det1 = eval_stats(u3)
    u3.update_tag()
    bpy.context.view_layer.update()
    s_det2 = eval_stats(u3)
    check("v2.8(deterministic): the user's massing evaluates identically on re-eval "
          "(fixed seeds, no hidden state)",
          s_det1["n_instances"] == s_det2["n_instances"]
          and s_det1["positions"] == s_det2["positions"]
          and s_det1["freq"] == s_det2["freq"],
          f"{s_det1['n_instances']} instances twice, positions/variant mix identical")

    # ================================================== v2.8: VM_RoofCap 'Hip'
    # square top = pyramid, round top = CONE ('roofs without modeling')
    log("\n== v2.8: VM_RoofCap 'Hip' on a SQUARE top (pyramid) + CIRCLE top (cone) ==")
    hip_sq = make_cube("HipPyramid", 3.0, col_scene)
    hip_sq.location = (38.0, -16.0, 0.0)
    m_hips = hip_sq.modifiers.new("VM_RoofCap", "NODES")
    m_hips.node_group = ng_roof
    set_params(m_hips, ng_roof, {"Style": "Hip", "Pitch": math.radians(35.0),
                                 "Overhang": 0.25, "Roof Material": mat_roof})
    bm_c = bmesh.new()
    bmesh.ops.create_cone(bm_c, cap_ends=True, cap_tris=False, segments=32,
                          radius1=2.0, radius2=2.0, depth=3.0)
    me_c = bpy.data.meshes.new("HipCone")
    bm_c.to_mesh(me_c)
    bm_c.free()
    hip_cn = bpy.data.objects.new("HipCone", me_c)
    hip_cn.location = (48.0, -16.0, 0.0)
    col_scene.objects.link(hip_cn)
    me_c.materials.append(mat_wall)
    m_hipc = hip_cn.modifiers.new("VM_RoofCap", "NODES")
    m_hipc.node_group = ng_roof
    set_params(m_hipc, ng_roof, {"Style": "Hip", "Pitch": math.radians(35.0),
                                 "Overhang": 0.25, "Roof Material": mat_roof})
    hip_sq.update_tag(); hip_cn.update_tag()
    bpy.context.view_layer.update()

    def gen_report(host):
        dg = bpy.context.evaluated_depsgraph_get()
        dg.update()
        me = host.evaluated_get(dg).data
        rg = me.attributes.get("vm_roofgen")
        gen = [p for p in me.polygons if rg and rg.data[p.index].value > 0.5]
        zs = [v.co.z for v in me.vertices]
        zmax = max(zs) if zs else 0.0
        apex_verts = [v for v in me.vertices if v.co.z > zmax - 0.02]
        apex_spread = max(
            [((a.co.x - b.co.x) ** 2 + (a.co.y - b.co.y) ** 2) ** 0.5
             for i, a in enumerate(apex_verts) for b in apex_verts[i + 1:]] or [0.0])
        up_gen = [p for p in gen if p.normal.z > 0.5]
        band = [p for p in gen if 0.55 <= p.normal.z < 0.92]
        return dict(n_gen=len(gen), zmax=round(zmax, 3), n_apex=len(apex_verts),
                    apex_spread=round(apex_spread, 4), n_slope_band=len(band), n_up=len(up_gen),
                    gen_faces=[len(p.vertices) for p in gen])

    r_sq = gen_report(hip_sq)
    r_cn = gen_report(hip_cn)
    log(f"  HipPyramid: {r_sq}")
    log(f"  HipCone:    {r_cn}")
    exp_apex_sq = (1.5 + 0.25) * math.tan(math.radians(35.0))
    check("v2.8(hip square top): VM_RoofCap 'Hip' on a square top builds a clean "
          "PYRAMID - exactly 4 roof faces meeting at one apex at the hip height",
          r_sq["n_gen"] == 4 and r_sq["apex_spread"] <= 0.05
          and abs(r_sq["zmax"] - (3.0 + exp_apex_sq)) < 0.02,
          f"generated faces={r_sq['n_gen']} (corner counts {r_sq['gen_faces']}), "
          f"apex verts={r_sq['n_apex']} (one apex: xy spread {r_sq['apex_spread']}), "
          f"apex z={r_sq['zmax']} vs expected "
          f"{round(3.0 + exp_apex_sq, 3)} (eave 3.0 + (half-side 1.5 + overhang 0.25) * tan 35)")
    exp_apex_cn = (2.0 + 0.25) * math.tan(math.radians(35.0))
    check("v2.8(hip circle top): VM_RoofCap 'Hip' on a 32-gon CIRCLE top builds a clean "
          "CONE-like cap - 32 sloped side faces in the roof slope band (shingle-able) "
          "+ a tiny apex ring, at the hip height",
          r_cn["n_gen"] == 33 and r_cn["n_slope_band"] == 32
          and abs(r_cn["zmax"] - (1.5 + exp_apex_cn)) < 0.02,
          f"generated faces={r_cn['n_gen']} (32 sides + 1 apex ring), roof-band sides="
          f"{r_cn['n_slope_band']}, apex z={r_cn['zmax']} vs expected "
          f"{round(1.5 + exp_apex_cn, 3)} (eave 1.5 + (radius 2 + overhang 0.25) * tan 35)")
    results["v28_user_massing"] = dict(containment_outside=n_out_c, spread=sp3,
                                       phantom_src={str(k): v for k, v in phantom_src.items()},
                                       hip_square=r_sq, hip_circle=r_cn)

    # ---- v2.8 renders (the acceptance shots against his screenshots) ----
    render_viewport("preview_user3_v28_viewport", (10.5, -30.5, 7.5), (21.5, -18.5, 3.2), 30)
    render_from("preview_user3_v28_textured", (21.5, -33.5, 8.5), (22.0, -18.5, 3.0), 32)
    render_from("preview_hip_square", (33.5, -21.5, 5.5), (38.0, -16.0, 1.6), 38)
    render_from("preview_hip_cone", (43.5, -21.5, 5.5), (48.0, -16.0, 1.6), 38)

    # ================================================== v2.9: BURIED FACES
    # The user's 2026-10-26 screenshot: a two-storey house + corner annex,
    # with a ROOF appearing on the first floor INSIDE the building. Modeled the
    # common way: the upper storey is a duplicated box stacked on the lower one
    # (leaves two coincident internal faces at the floor line) and the annex is
    # a box pushed INTO the main block (its inner wall + part of its top are
    # buried). Every face was zone-qualified by its normal alone -> the buried
    # floor became a roof region and got a cap + shingles inside the house.
    log("\n== v2.9: BURIED FACES (stacked storeys + overlapping annex in ONE mesh) ==")
    MAIN = (-2.0, 2.0, -1.5, 1.5, 0.0, 5.2)       # lower + upper storey (floor at 2.6)
    ANNEX = (1.5, 4.2, -1.5, -0.25, 0.0, 2.4)      # pushed 0.5 m into the main block

    def _box(x0, x1, y0, y1, z0, z1):
        vs = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
              (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        fs = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        return vs, fs
    bv, bf = [], []
    for bx in ((-2.0, 2.0, -1.5, 1.5, 0.0, 2.6), (-2.0, 2.0, -1.5, 1.5, 2.6, 5.2), ANNEX):
        vs, fs = _box(*bx)
        o = len(bv)
        bv += vs
        bf += [tuple(i + o for i in f) for f in fs]
    me_bf = bpy.data.meshes.new("BuriedFloorHouse")
    me_bf.from_pydata(bv, [], bf)
    me_bf.update()
    me_bf.materials.append(mat_wall)
    bfh = bpy.data.objects.new("BuriedFloorHouse", me_bf)
    bfh.location = (60.0, -16.0, 0.0)
    col_scene.objects.link(bfh)
    for _nm, _grp, _params in (("VM_SceneDetailer_Planks", ng, u3_plank),
                               ("VM_RoofCap", ng_roof, u3_roof),
                               ("VM_SceneDetailer_Shingles", ng, u3_shingle),
                               ("VM_SceneDetailer_Door", ng, u3_door),
                               ("VM_SceneDetailer_Windows", ng, u3_win)):
        _m = bfh.modifiers.new(_nm, "NODES")
        _m.node_group = _grp
        set_params(_m, _grp, _params)
    bfh.update_tag()
    bpy.context.view_layer.update()

    bf_faces = face_table(bfh)
    bf_up_all = [f for f in bf_faces if f["n"].z >= 0.98]
    bf_buried = [f["idx"] for f in bf_faces if f["buried"]]
    bf_up_ext = [f for f in bf_up_all if not f["buried"]]
    log(f"  base mesh: {len(bf_faces)} faces, up-facing={len(bf_up_all)} "
        f"(exterior {len(bf_up_ext)}), buried faces={bf_buried}")

    # roof generated over the buried floor = generated faces whose centre sits
    # deep inside the main block below its top (the visible bug)
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    ev_me = bfh.evaluated_get(dg).data
    rg = ev_me.attributes.get("vm_roofgen")
    gen_inside, gen_total = 0, 0
    for p in ev_me.polygons:
        if not (rg and rg.data[p.index].value > 0.5):
            continue
        gen_total += 1
        c = Vector(p.center)
        # x < 1.0: the annex cap's own overhang + fascia legitimately reach
        # x = 1.25 (annex west edge 1.5 - overhang 0.25)
        if -1.8 < c.x < 1.0 and -1.3 < c.y < 1.3 and c.z < MAIN[5] - 0.1:
            gen_inside += 1
    rr_bf = roof_report(bfh, overhang=0.25, style="Flat")

    def _deep_in(p, bx, m=0.05):
        return (bx[0] + m < p.x < bx[1] - m and bx[2] + m < p.y < bx[3] - m
                and bx[4] + m < p.z < bx[5] - m)
    mwi_bf = bfh.matrix_world.inverted()
    rows_bf = inst_table(bfh, ("Plank", "Shingle", "Door", "Window"))
    in_main = Counter(pre for (pre, org, lo, hi) in rows_bf if _deep_in(mwi_bf @ Vector(org), MAIN))
    in_annex = Counter(pre for (pre, org, lo, hi) in rows_bf if _deep_in(mwi_bf @ Vector(org), ANNEX))
    per_pre = Counter(pre for (pre, _o, _l, _h) in rows_bf)
    log(f"  instances: {dict(per_pre)}; anchored deep inside MAIN: {dict(in_main)}; "
        f"inside ANNEX (partial-overlap diagnostic): {dict(in_annex)}")
    log(f"  generated roof faces: {gen_total}, inside the main block below its top: {gen_inside}; "
        f"roof_report caps={rr_bf['caps']} uncovered={rr_bf['uncovered']}")

    check("v2.9(buried floor detected): the stacked-storey seam faces and the annex's "
          "inner wall are classified BURIED (ray along the normal hits a back face)",
          len(bf_buried) >= 3 and len(bf_up_ext) == 2,
          f"buried face idx={bf_buried}; up-facing {len(bf_up_all)} -> exterior "
          f"{len(bf_up_ext)} (main top + annex top)")
    check("v2.9(no roof inside the building): VM_RoofCap emits ZERO roof faces on the "
          "buried first-floor seam (the user's 'roof on a floor' bug)",
          gen_inside == 0 and gen_total > 0 and not rr_bf["uncovered"],
          f"{gen_total} generated roof faces, {gen_inside} inside the main block "
          f"(v2.8 engine capped the buried floor too), uncovered exterior tops="
          f"{rr_bf['uncovered']}")
    check("v2.9(no dressing inside the building): ZERO planks/shingles/doors/windows "
          "anchored deep inside the main block",
          sum(in_main.values()) == 0 and per_pre.get("Plank", 0) > 0,
          f"inside main: {dict(in_main)}; totals {dict(per_pre)}")
    results["v29_buried_faces"] = dict(buried=bf_buried, up_all=len(bf_up_all),
                                       up_exterior=len(bf_up_ext), gen_total=gen_total,
                                       gen_inside=gen_inside, in_main=dict(in_main),
                                       in_annex=dict(in_annex), totals=dict(per_pre))
    render_from("preview_buried_floor_house", (54.5, -23.5, 6.5), (60.5, -16.0, 2.4), 32)

    # ================================================== v2.9.1: SPLIT COPLANAR TOPS
    # The user's TestFit top was 4 coplanar faces: each got its OWN tilted cap
    # (own centre, own long axis) -> 4 overlapping slabs and a dark triangle
    # where they crossed. Now a connected patch of cap faces = ONE region.
    log("\n== v2.9.1: SPLIT COPLANAR TOPS (2x2 grid top + L-shaped 3-quad top) ==")

    def _split_top_mesh(name, top_cells, H, cell=2.0):
        """Prism whose top is the given unit cells (one quad each, shared
        vertices); walls along the outline, one n-gon bottom."""
        cells = set(top_cells)
        edges = Counter()
        for (i, j) in cells:
            for a, b_ in (((i, j), (i + 1, j)), ((i + 1, j), (i + 1, j + 1)),
                          ((i + 1, j + 1), (i, j + 1)), ((i, j + 1), (i, j))):
                edges[frozenset((a, b_))] += 1
        nxt = {}
        for (i, j) in cells:      # CCW boundary edges (interior edges cancel)
            for a, b_ in (((i, j), (i + 1, j)), ((i + 1, j), (i + 1, j + 1)),
                          ((i + 1, j + 1), (i, j + 1)), ((i, j + 1), (i, j))):
                if edges[frozenset((a, b_))] == 1:
                    nxt[a] = b_
        loop, cur = [], next(iter(sorted(nxt)))
        while cur not in loop:
            loop.append(cur)
            cur = nxt[cur]
        grid = sorted({c for (i, j) in cells for c in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))})
        top_id = {g: k for k, g in enumerate(grid)}
        verts = [(g[0] * cell, g[1] * cell, H) for g in grid]
        bot_id = {g: len(verts) + k for k, g in enumerate(loop)}
        verts += [(g[0] * cell, g[1] * cell, 0.0) for g in loop]
        faces = [tuple(top_id[c] for c in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)))
                 for (i, j) in sorted(cells)]
        faces.append(tuple(bot_id[g] for g in reversed(loop)))
        for k, a in enumerate(loop):
            b_ = loop[(k + 1) % len(loop)]
            faces.append((bot_id[a], bot_id[b_], top_id[b_], top_id[a]))
        me_ = bpy.data.meshes.new(name)
        me_.from_pydata(verts, [], faces)
        me_.update()
        me_.materials.append(mat_wall)
        return me_

    def _cap_top_report(host):
        """Cap-top faces of the evaluated RoofCap output: connected slabs
        (islands of shared vertices), plane residual per slab (one incline
        plane = 0), summed top area (overlapping per-face caps over-count)."""
        dg_ = bpy.context.evaluated_depsgraph_get()
        dg_.update()
        me_ = host.evaluated_get(dg_).data
        rg_ = me_.attributes.get("vm_roofgen")
        tops = [p for p in me_.polygons
                if rg_ and 1.5 <= rg_.data[p.index].value < 2.5 and p.normal.z >= 0.9]
        parent = {}

        def find(v):
            while parent.setdefault(v, v) != v:
                parent[v] = parent[parent[v]]
                v = parent[v]
            return v
        for p in tops:
            for v in p.vertices[1:]:
                parent[find(v)] = find(p.vertices[0])
        slabs = {}
        for p in tops:
            slabs.setdefault(find(p.vertices[0]), []).append(p)
        resid = 0.0
        for ps in slabs.values():
            pts = [Vector(me_.vertices[v].co) for p in ps for v in p.vertices]
            p0, n0 = pts[0], Vector(ps[0].normal)
            resid = max(resid, max(abs((q - p0).dot(n0)) for q in pts))
        return dict(top_faces=len(tops), slabs=len(slabs), plane_resid=round(resid, 6),
                    top_area=round(sum(p.area for p in tops), 4))

    split_specs = (("SplitTopGrid", [(0, 0), (1, 0), (0, 1), (1, 1)], 2.6, (70.0, -16.0, 0.0),
                    (4.0 + 0.5) * (4.0 + 0.5)),
                   ("SplitTopL", [(0, 0), (1, 0), (0, 1)], 2.6, (78.0, -16.0, 0.0), None))
    split_res = {}
    for nm, cells, H, loc, exp_area in split_specs:
        so = bpy.data.objects.new(nm, _split_top_mesh(nm, cells, H))
        so.location = loc
        col_scene.objects.link(so)
        for _nm, _grp, _params in (("VM_SceneDetailer_Planks", ng, u3_plank),
                                   ("VM_RoofCap", ng_roof, u3_roof),
                                   ("VM_SceneDetailer_Shingles", ng, u3_shingle),
                                   ("VM_SceneDetailer_Door", ng, u3_door),
                                   ("VM_SceneDetailer_Windows", ng, u3_win)):
            _m = so.modifiers.new(_nm, "NODES")
            _m.node_group = _grp
            set_params(_m, _grp, _params)
        so.update_tag()
        bpy.context.view_layer.update()
        ct = _cap_top_report(so)
        rr = roof_report(so, overhang=0.25, style="Flat")
        if exp_area is not None:
            # one slab over the whole 4x4 top + 0.25 m overhang each side; the
            # 2.5 deg incline stretches the sloped area by 1/cos
            ct["expected_area"] = round(exp_area / math.cos(math.radians(2.5)), 4)
        split_res[nm] = dict(cap=ct, uncovered=rr["uncovered"], strays=len(rr["strays"]),
                             host_tops=len(cells))
        log(f"  {nm}: host top faces={len(cells)} cap={ct} uncovered={rr['uncovered']} "
            f"strays={len(rr['strays'])}")
    sg, sl = split_res["SplitTopGrid"], split_res["SplitTopL"]
    check("v2.9.1(split top = ONE cap): a top split into coplanar faces gets ONE "
          "connected cap slab on ONE incline plane (2x2 grid and L-shaped 3-quad tops)",
          all(r["cap"]["slabs"] == 1 and r["cap"]["plane_resid"] < 1e-3
              and r["cap"]["top_faces"] == r["host_tops"] for r in (sg, sl)),
          f"grid: {sg['cap']}; L: {sl['cap']}")
    check("v2.9.1(no overlapping caps): the 2x2 split top's cap area equals ONE "
          "4x4 m cap + overhang (per-face caps over-counted it by ~27%)",
          abs(sg["cap"]["top_area"] - sg["cap"]["expected_area"]) < 0.02 * sg["cap"]["expected_area"],
          f"top area {sg['cap']['top_area']} vs expected {sg['cap']['expected_area']}")
    check("v2.9.1(split tops fully covered): no uncovered top face and no stray cap face",
          all(not r["uncovered"] and r["strays"] == 0 for r in (sg, sl)),
          f"grid uncovered={sg['uncovered']} strays={sg['strays']}; "
          f"L uncovered={sl['uncovered']} strays={sl['strays']}")
    results["v291_split_tops"] = split_res
    render_from("preview_split_tops", (68.0, -24.5, 7.5), (75.0, -13.5, 2.4), 34)

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

    # ---- v2.8: the user's own massing re-measured ON the delivered blend ----
    u3d = bpy.data.objects.get("Cube.001")
    if u3d is not None:
        n_out_d, det_d = containment_check(u3d, ("Plank", "Shingle"))
        sp_d = opening_spread(u3d)
        log(f"  v2.8 delivered Cube.001: cladding outside={n_out_d}, openings={sp_d}")
        check("accept(v2.8 delivered): the user's Cube.001 survives the rebuild AND keeps "
              "ZERO cladding anchors off-surface (no phantom slab)",
              n_out_d == 0,
              f"{n_out_d} cladding anchors off-surface (0 required; strict planar-polygon "
              f"outliers diagnostic={det_d['strict_planar_outside']}), object "
              f"present with {len(u3d.data.vertices)} verts / {len(u3d.data.polygons)} faces")
        check("accept(v2.8 delivered): the user's Cube.001 openings spread over >= 3 walls "
              "with zero pairwise bbox intersections and per-wall counts balanced <= 1",
              sp_d["walls"] >= 3 and sp_d["intersections"] == 0 and 0 <= sp_d["spread_diff"] <= 1,
              f"{sp_d['total']} openings on {sp_d['walls']} walls, per-wall "
              f"{sorted(sp_d['per_wall'].values())}, intersections={sp_d['intersections']}, "
              f"min gap={sp_d['min_gap']}, max-min={sp_d['spread_diff']}")
        results["v28_delivered"] = dict(containment_outside=n_out_d, spread=sp_d)
    else:
        check("accept(v2.8 delivered): the user's Cube.001 survives the rebuild", False,
              "Cube.001 missing from the delivered VM_Starter.blend")

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

    # ================================================== v2.7 acceptance (measured on the delivered blends)
    log("\n== v2.7 ACCEPTANCE (delivered VM_Starter.blend: defaults, versions, compound) ==")

    def probe_versions(tag):
        bad, total = [], 0
        for ob in bpy.data.objects:
            for m in ob.modifiers:
                if m.type != 'NODES' or m.node_group is None:
                    continue
                if m.node_group.name.split(".")[0] not in ("VM_SceneDetailer", "VM_RoofCap"):
                    continue
                total += 1
                try:
                    v = str(getattr(m.properties.inputs,
                                    socket_id(m.node_group, "Engine Version")).value)
                except Exception as e:
                    v = f"<missing:{e}>"
                if v != ENGINE_VERSION:
                    bad.append((ob.name, m.name, v))
        check(f"version: Engine Version socket reads '{ENGINE_VERSION}' on EVERY VM modifier in {tag}",
              total > 0 and not bad, f"{total} VM modifiers probed, non-{ENGINE_VERSION}: {bad[:8]}")
        return total, bad

    def probe_descriptions(tag):
        descs = {n: (bpy.data.node_groups[n].description or "")[:80]
                 for n in ("VM_SceneDetailer", "VM_RoofCap")}
        ok = all(ENGINE_VERSION in d for d in descs.values())
        check(f"version: node-group DESCRIPTIONS carry {ENGINE_VERSION} in {tag} "
              f"(visible in the node-group selector tooltip)",
              ok, f"descriptions={descs}")

    def sock_val(ob, mod_name, sock_name):
        m = ob.modifiers.get(mod_name)
        return getattr(m.properties.inputs, socket_id(m.node_group, sock_name)).value

    # ---- (1) starter read-back: the saved stack IS the current-defaults demo
    sc_rb = bpy.data.objects["StarterCube"]
    rb_style = sock_val(sc_rb, "VM_RoofCap", "Style")
    rb_incl = float(sock_val(sc_rb, "VM_RoofCap", "Incline"))
    rb_fit = sock_val(sc_rb, "VM_SceneDetailer_Door", "Opening Fit")
    rb_ver = str(sock_val(sc_rb, "VM_RoofCap", "Engine Version"))
    check("starter read-back (delivered VM_Starter.blend): saved VM_RoofCap Style='Flat' "
          "(gables never invented on flat tops), Incline=2.5 deg, layers on 'Scale To Face', "
          f"Engine Version '{ENGINE_VERSION}'",
          rb_style == "Flat" and abs(rb_incl - math.radians(2.5)) < 1e-5
          and rb_fit == "Scale To Face" and rb_ver == ENGINE_VERSION,
          f"Style={rb_style}, Incline={math.degrees(rb_incl):.3f} deg, "
          f"Opening Fit={rb_fit}, Engine Version={rb_ver}")
    results["starter_readback"] = dict(style=rb_style, incline_deg=round(math.degrees(rb_incl), 4),
                                       opening_fit=rb_fit, engine_version=rb_ver)

    # ---- (2) compound + gable showcase read-back (the user's exact action)
    comp_rb = bpy.data.objects["StarterCompound"]
    c_res, c_chk = compound_accept("delivered blend", comp_rb)
    for name, cond, detail in c_chk:
        check(name, cond, detail)
    results["starter_compound_readback"] = c_res
    gs_rb = bpy.data.objects["GableShowcase"]
    g_res, g_chk = gable_showcase_accept("delivered blend", gs_rb)
    for name, cond, detail in g_chk:
        check(name, cond, detail)
    results["gable_showcase_readback"] = g_res

    # ---- (3) version visibility across the delivered file
    n_vm, bad_vm = probe_versions("VM_Starter.blend")
    probe_descriptions("VM_Starter.blend")
    results["version_probe"] = {"VM_Starter.blend": dict(total=n_vm, bad=bad_vm)}

    # ================================================== v2.7 ACCEPTANCE 1: the untouched default path
    log("\n== v2.7 DEFAULT PATH: fresh scene + fresh cube + Add Modifier, ZERO socket tweaks ==")
    bpy.ops.scene.new(type='NEW')
    df_scene = bpy.context.scene
    df_scene.render.engine = "CYCLES"
    df_scene.cycles.device = "CPU"
    df_scene.cycles.samples = 32
    df_scene.cycles.use_denoising = True
    df_scene.render.resolution_x = 960
    df_scene.render.resolution_y = 540
    df_scene.render.resolution_percentage = 100
    if bpy.data.worlds.get("World") is not None:
        df_scene.world = bpy.data.worlds["World"]
    df_cube = make_cube("DefaultPathCube", 2.0, df_scene.collection)
    m_dp1 = df_cube.modifiers.new("VM_SceneDetailer", "NODES")
    m_dp1.node_group = bpy.data.node_groups["VM_SceneDetailer"]
    m_dp2 = df_cube.modifiers.new("VM_RoofCap", "NODES")
    m_dp2.node_group = bpy.data.node_groups["VM_RoofCap"]
    # ^^ ZERO socket writes - this is the untouched default path
    df_cube.update_tag()
    bpy.context.view_layer.update()
    df_boxes = inst_boxes(df_cube, "Door_") + inst_boxes(df_cube, "Window_")
    df_stats = eval_stats(df_cube)
    df_zc = zone_counts_on_cube(df_stats["positions"], df_stats["normals"])
    df_tops, df_gables = cap_inclines(df_cube)
    df_incl_err = max(abs(t - 2.5) for t in df_tops) if df_tops else 99.0
    check("default path: fresh scene + fresh cube + Add Modifier (ZERO socket tweaks) -> "
          "openings present on the walls out of the box",
          len(df_boxes) >= 1 and df_stats["n_instances"] > 0
          and df_zc["on_wall"] == df_stats["n_instances"]
          and df_zc["on_top"] == 0 and df_zc["on_bottom"] == 0,
          f"{len(df_boxes)} opening instances, freq={df_stats['freq']}, zone counts={df_zc}")
    check("default path: fresh VM_RoofCap defaults to FLAT cap - zero gable triangles, "
          "subtle incline measured at 2.5 deg",
          df_gables == 0 and bool(df_tops) and df_incl_err <= 0.75,
          f"gable faces={df_gables} (expected 0), measured cap inclines={df_tops} deg "
          f"(socket 2.5 deg, tolerance +/-0.75)")
    results["default_path"] = dict(freq=df_stats["freq"], zone=df_zc,
                                   gable_faces=df_gables, inclines=df_tops,
                                   n_openings=len(df_boxes))
    df_cam_d = bpy.data.cameras.new("DefaultPathCam")
    df_cam = bpy.data.objects.new("DefaultPathCam", df_cam_d)
    df_scene.collection.objects.link(df_cam)
    df_scene.camera = df_cam
    df_cam.location = (4.4, -5.4, 2.9)
    look_at(df_cam, (0, 0, 1.0))
    df_cam_d.lens = 38
    df_sun_d = bpy.data.lights.new("DefaultPathSun", "SUN")
    df_sun_d.energy = 3.5
    df_sun = bpy.data.objects.new("DefaultPathSun", df_sun_d)
    df_scene.collection.objects.link(df_sun)
    df_sun.rotation_euler = (math.radians(52), math.radians(8), math.radians(35))
    df_scene.render.filepath = os.path.join(ROOT, "renders", "preview_default_path.png")
    bpy.ops.render.render(write_still=True)
    log("  rendered preview_default_path.png (untouched default path)")

    # ================================================== v2.7 VM_Tools_Addon (part 1: same file)
    log("\n== v2.7 VM_Tools_Addon: Dress Object / Copy / Paste / Save Preset ==")
    # load the add-on from THIS folder: an installed + enabled copy in Blender's
    # user add-ons is already in sys.modules and would shadow the one under test
    import importlib.util
    _inst = sys.modules.get("VM_Tools_Addon")
    if _inst is not None:
        try:
            _inst.unregister()
        except Exception:
            pass
    _spec = importlib.util.spec_from_file_location("VM_Tools_Addon", os.path.join(_HERE, "VM_Tools_Addon.py"))
    vmt = importlib.util.module_from_spec(_spec)
    sys.modules["VM_Tools_Addon"] = vmt
    _spec.loader.exec_module(vmt)
    vmt.register()
    bpy.ops.scene.new(type='NEW')
    ad_scene = bpy.context.scene
    ad_scene.render.engine = "CYCLES"
    ad_scene.cycles.device = "CPU"
    ad_scene.cycles.samples = 32
    ad_scene.cycles.use_denoising = True
    ad_scene.render.resolution_x = 960
    ad_scene.render.resolution_y = 540
    ad_scene.render.resolution_percentage = 100
    if bpy.data.worlds.get("World") is not None:
        ad_scene.world = bpy.data.worlds["World"]
    ad_col = ad_scene.collection
    cube_a = make_cube("AddonSource", 2.0, ad_col)
    cube_b = make_cube("AddonPasted", 2.0, ad_col)
    cube_b.location = (4.5, 0, 0)

    bpy.ops.object.select_all(action='DESELECT')
    cube_a.select_set(True)
    ad_scene.view_layers[0].objects.active = cube_a
    bpy.ops.vm.dress_object()
    # 'the only remaining manual step': assign the variant collections (fetched
    # by NAME from the reopened file - pre-open Python refs are dead here)
    for mod_name, col_name in (("VM_SceneDetailer_Planks", "VM_Tiles_Plank"),
                               ("VM_SceneDetailer_Shingles", "VM_Tiles_Shingle"),
                               ("VM_SceneDetailer_Door", "VM_Doors"),
                               ("VM_SceneDetailer_Windows", "VM_Windows")):
        m_ = cube_a.modifiers[mod_name]
        set_params(m_, m_.node_group, {"Primary Props": bpy.data.collections[col_name],
                                       "Debris/Trash Props": bpy.data.collections["VM_Debris_Trash"]})
    cube_a.update_tag()
    bpy.context.view_layer.update()
    a_names = [m.name for m in cube_a.modifiers]
    a_roof_style = sock_val(cube_a, "VM_RoofCap", "Style")
    a_door_fit = sock_val(cube_a, "VM_SceneDetailer_Door", "Opening Fit")
    check("addon(dress): 'VM: Dress Object' applies the FULL default v2.7 stack in one click "
          "(wall cladding + VM_RoofCap + roof cladding + doors + windows)",
          a_names == ["VM_SceneDetailer_Planks", "VM_RoofCap", "VM_SceneDetailer_Shingles",
                      "VM_SceneDetailer_Door", "VM_SceneDetailer_Windows"]
          and a_roof_style == "Flat" and a_door_fit == "Scale To Face",
          f"modifiers={a_names}, RoofCap Style={a_roof_style}, Door Opening Fit={a_door_fit}")

    ad_scene.view_layers[0].objects.active = cube_a
    bpy.ops.vm.copy_engine_setup()
    bpy.ops.object.select_all(action='DESELECT')
    cube_b.select_set(True)
    ad_scene.view_layers[0].objects.active = cube_b
    bpy.ops.vm.paste_engine_setup()
    snap_a = vmt.snapshot_object(cube_a)
    snap_b = vmt.snapshot_object(cube_b)
    mism_ab = [k for k in range(max(len(snap_a), len(snap_b)))
               if (snap_a[k] if k < len(snap_a) else None) != (snap_b[k] if k < len(snap_b) else None)]
    n_socks = vmt.count_sockets(snap_a)
    check("addon(copy/paste): cube B's VM stack == cube A's (same groups, identical socket "
          "values incl. collection pointers, counted)",
          snap_a == snap_b and len(snap_a) == 5 and n_socks >= 100 and not mism_ab,
          f"{len(snap_a)} modifiers, {n_socks} sockets compared per object, "
          f"modifier-index mismatches={mism_ab}, collection pointers "
          f"{[v for s in snap_b for k, v in s['values'].items() if v[1][0] == 'id' and v[1][2]][:8]}")
    results["addon_copy_paste"] = dict(n_modifiers=len(snap_a), n_sockets=n_socks,
                                       mismatches=mism_ab)

    ad_scene.view_layers[0].objects.active = cube_a
    bpy.ops.vm.save_preset(name="acceptance_v27")
    preset_path = os.path.join(os.path.expanduser(
        os.path.join("~", ".config", "vm_engine", "presets")), "acceptance_v27.json")
    preset_ok = os.path.isfile(preset_path)
    preset_meta = json.load(open(preset_path)) if preset_ok else {}
    preset_snap = preset_meta.get("modifiers", [])
    check("addon(preset): 'VM: Save Preset' stores the full stack config + collection NAMES "
          "to ~/.config/vm_engine/presets/<name>.json",
          preset_ok and len(preset_snap) == 5 and vmt.count_sockets(preset_snap) == n_socks,
          f"{preset_path}: exists={preset_ok}, {len(preset_snap)} modifiers, "
          f"{vmt.count_sockets(preset_snap)} sockets")

    # renders: the pasted cube must look IDENTICAL to the source
    ad_cam_d = bpy.data.cameras.new("AddonCam")
    ad_cam = bpy.data.objects.new("AddonCam", ad_cam_d)
    ad_col.objects.link(ad_cam)
    ad_scene.camera = ad_cam
    ad_sun_d = bpy.data.lights.new("AddonSun", "SUN")
    ad_sun_d.energy = 3.5
    ad_sun = bpy.data.objects.new("AddonSun", ad_sun_d)
    ad_col.objects.link(ad_sun)
    ad_sun.rotation_euler = (math.radians(52), math.radians(8), math.radians(35))

    def ad_render(tag, loc, target, lens):
        ad_cam.location = loc
        look_at(ad_cam, target)
        ad_cam_d.lens = lens
        ad_scene.render.filepath = os.path.join(ROOT, "renders", tag + ".png")
        bpy.ops.render.render(write_still=True)
        log(f"  rendered {tag}.png")

    ad_render("preview_addon_pair", (2.25, -10.5, 4.6), (2.25, 0, 1.2), 35)
    ad_render("preview_addon_source", (0.0, -6.2, 2.7), (0.0, 0, 1.1), 45)
    ad_render("preview_addon_pasted", (4.5, -6.2, 2.7), (4.5, 0, 1.1), 45)

    # ---- VM_SceneDetailer.blend / VM_RoofCap.blend: images + version probes
    for path in (BLEND_PATH, ROOFCAP_PATH):
        rep2 = blend_image_report(path)
        results["images_packed"][os.path.basename(path)] = rep2
        check(f"images_packed {os.path.basename(path)}: {rep2['packed']}/{rep2['total']}",
              rep2["total"] > 0 and not rep2["unpacked"],
              f"{rep2['packed']}/{rep2['total']} image datablocks packed, unpacked={rep2['unpacked']}")
        n_vm2, bad_vm2 = probe_versions(os.path.basename(path))
        probe_descriptions(os.path.basename(path))
        results["version_probe"][os.path.basename(path)] = dict(total=n_vm2, bad=bad_vm2)

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

    # ================================================== v2.7 VM_Tools_Addon part 2 + VM_Assets.blend
    log("\n== v2.7 preset CROSS-FILE load + VM_Assets.blend asset packaging ==")
    bpy.ops.wm.read_factory_settings()      # a genuinely FRESH file
    vmt.register()                          # factory reset may drop scripted classes
    # same-named collections + materials in the fresh file (the preset re-matches
    # references BY NAME - this is the 'setups travel across .blend files' path)
    for cname in ("VM_Tiles_Plank", "VM_Tiles_Shingle", "VM_Doors", "VM_Windows",
                  "VM_Debris_Trash"):
        bpy.data.collections.new(cname)
    for mname in ("VM_WallWeatheredPlanks", "VM_RoofClayTiles", "VM_FloorGrass"):
        bpy.data.materials.new(mname)
    # the engine is present in the file (as it would be after appending the node
    # groups or dragging them from the VM_Assets.blend Asset Browser)
    ng2 = build_node_group()
    ng2r = build_roofcap_group()
    cube_c = make_cube("PresetTarget", 2.0, bpy.context.scene.collection)
    bpy.ops.object.select_all(action='DESELECT')
    cube_c.select_set(True)
    bpy.context.scene.view_layers[0].objects.active = cube_c
    bpy.ops.vm.load_preset(name="acceptance_v27")
    snap_c = vmt.snapshot_object(cube_c)
    mism_c = [k for k in range(max(len(snap_c), len(preset_snap)))
              if (snap_c[k] if k < len(snap_c) else None)
              != (preset_snap[k] if k < len(preset_snap) else None)]
    check("addon(preset CROSS-FILE): Load Preset in a FRESH file with same-named collections/"
          "materials rebuilds the identical stack (counted, 0 mismatches)",
          snap_c == preset_snap and len(snap_c) == 5 and not mism_c,
          f"{len(snap_c)} modifiers, {vmt.count_sockets(snap_c)} sockets, "
          f"modifier-index mismatches={mism_c}")
    results["addon_preset_crossfile"] = dict(n_modifiers=len(snap_c),
                                             n_sockets=vmt.count_sockets(snap_c),
                                             mismatches=mism_c)

    # ---- v2.10: VM_Assets.blend = THE ENGINE LIBRARY the add-on imports from
    # into ANY file: both node groups (also marked as Blender assets), the whole
    # AssetLibrary pack tree, the default materials and the clean BASE PRESETS
    # (a VM_Presets JSON text). Built from the starter so it carries exactly the
    # collections/materials/images the engine was verified with.
    bpy.ops.wm.open_mainfile(filepath=STARTER_PATH)
    vmt.register()
    lib_root = bpy.data.collections[vmt.LIBRARY_COLLECTION]
    keep_obs = set(lib_root.all_objects)
    for ob in list(bpy.data.objects):
        if ob not in keep_obs:
            bpy.data.objects.remove(ob)      # the library ships assets, not a scene
    keep_cols = {lib_root} | set(lib_root.children_recursive)
    for c in list(bpy.data.collections):
        if c not in keep_cols and not c.all_objects:
            bpy.data.collections.remove(c)
    for mats_ in vmt.AUTO_MATERIALS.values():
        for mname in mats_.values():
            bpy.data.materials[mname].use_fake_user = True
    probe = make_cube("PresetProbe", 2.0, bpy.context.scene.collection)
    lib_presets = {}
    for pname, style, desc in (
            ("Base - Flat roof", "Flat", "The default pack at default settings: plank walls, flat "
             "clay-tile roof cap, shingle roof cladding, doors and windows"),
            ("Base - Gable roof", "Gable", "Base preset with a gable roof cap"),
            ("Base - Hip roof", "Hip", "Base preset with a hip roof cap")):
        pw = []
        vmt.dress_object(probe, pw)
        rc = probe.modifiers["VM_RoofCap"]
        set_params(rc, rc.node_group, {"Style": style})
        lib_presets[pname] = dict(description=desc, modifiers=vmt.snapshot_object(probe))
    bpy.data.objects.remove(probe)
    txt = bpy.data.texts.get(vmt.PRESETS_TEXT) or bpy.data.texts.new(vmt.PRESETS_TEXT)
    txt.from_string(json.dumps(dict(engine_version=ENGINE_VERSION, presets=lib_presets), indent=1))
    txt.use_fake_user = True
    for ngn_, desc in (
            ("VM_SceneDetailer",
             f"VM engine {ENGINE_VERSION} - semantic architectural application engine (Scatter/Fit/"
             "Cladding + Slots openings; 'Opening Fit: Scale To Face'; About panel shows "
             f"Engine Version '{ENGINE_VERSION}'). Best used through the VM Engine add-on "
             "(Import Engine / Apply Preset / Dress Object)."),
            ("VM_RoofCap",
             f"VM engine {ENGINE_VERSION} - per-region roof caps: Style 'Flat' DEFAULT (subtle incline, "
             "never invented gables) / 'Gable' / 'Hip' opt-in. About panel shows Engine "
             f"Version '{ENGINE_VERSION}'.")):
        ng_ = bpy.data.node_groups[ngn_]
        ng_.asset_mark()
        ng_.asset_data.description = desc
        ng_.asset_data.author = "kristo / ViperMesh"
        ng_.use_fake_user = True
    bpy.data.orphans_purge(do_recursive=True)   # the starter's scene leftovers
    bpy.ops.wm.save_as_mainfile(filepath=ASSETS_PATH)
    log(f"  saved {ASSETS_PATH}")

    bpy.ops.wm.open_mainfile(filepath=ASSETS_PATH)
    vmt.register()
    marked = sorted(n.name for n in bpy.data.node_groups
                    if n.name.split(".")[0] in ("VM_SceneDetailer", "VM_RoofCap")
                    and n.asset_data is not None)
    check("assets: VM_Assets.blend ships BOTH node groups marked as Blender assets "
          "(Asset Browser: drag the engine onto any object in any file)",
          sorted(m.split(".")[0] for m in marked) == ["VM_RoofCap", "VM_SceneDetailer"],
          f"marked assets: {marked}")
    lib_meta = vmt.library_info(ASSETS_PATH)
    # names the library itself ships (the packs carry their own 'Glass.001' etc.)
    lib_names = {d.name for coll in (bpy.data.node_groups, bpy.data.collections,
                                     bpy.data.materials, bpy.data.objects) for d in coll}
    lib_cols = sorted(c.name for c in bpy.data.collections)
    lib_stray = sorted(o.name for o in bpy.data.objects
                       if o not in set(bpy.data.collections[vmt.LIBRARY_COLLECTION].all_objects))
    lib_need = vmt.default_collections()
    check(f"library: VM_Assets.blend is the full engine library - groups + AssetLibrary pack "
          f"collections + default materials + >=3 clean base presets tagged '{ENGINE_VERSION}'",
          lib_meta.get("engine_version") == ENGINE_VERSION
          and len(lib_meta.get("presets", {})) >= 3
          and all(c in lib_cols for c in lib_need) and not lib_stray
          and all(bpy.data.materials.get(m) for d in vmt.AUTO_MATERIALS.values() for m in d.values())
          and all(len(pr["modifiers"]) == 5 for pr in lib_meta.get("presets", {}).values()),
          f"engine_version={lib_meta.get('engine_version')}, presets="
          f"{sorted(lib_meta.get('presets', {}))}, pack collections={lib_need}, "
          f"objects outside AssetLibrary={lib_stray}, file collections={len(lib_cols)}")
    results["vm_assets"] = dict(marked=marked, path=ASSETS_PATH, presets=sorted(lib_meta.get("presets", {})),
                                collections=lib_cols,
                                descriptions={n.name: (n.asset_data.description or "")[:60]
                                              for n in bpy.data.node_groups
                                              if n.asset_data is not None})

    # ---- v2.10: the add-on works ACROSS FILES - a genuinely empty file gets the
    # engine, the pack and a clean base preset from one 'Apply Preset' click
    log("\n== v2.10 add-on: import engine + clean presets in a FRESH file ==")
    bpy.ops.wm.read_factory_settings()
    vmt.register()
    vmt.LIBRARY_PATH_OVERRIDE = ASSETS_PATH
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    fx_scene = bpy.context.scene

    def fx_cube(name, x):
        c_ = make_cube(name, 2.0, fx_scene.collection)
        c_.location = (x, 0, 0)
        bpy.ops.object.select_all(action='DESELECT')
        c_.select_set(True)
        fx_scene.view_layers[0].objects.active = c_
        return c_

    import re

    def dup_names():
        return sorted(d.name for coll in (bpy.data.node_groups, bpy.data.collections,
                                          bpy.data.materials, bpy.data.objects)
                      for d in coll if re.search(r"\.\d{3}$", d.name) and d.name not in lib_names)

    def mod_instances(ob):
        # instances per layer, attributed by the pack collection they come from
        ob.update_tag()
        freq = eval_stats(ob)["freq"]
        out = {}
        for mod_name, cols_ in vmt.AUTO_COLLECTIONS.items():
            col_ = bpy.data.collections.get(cols_["Primary Props"])
            members = {o.name for o in col_.all_objects} if col_ else set()
            out[mod_name] = sum(n for o, n in freq.items() if o in members)
        return out

    fx_a = fx_cube("FreshA", 0.0)
    r_a = bpy.ops.vm.apply_preset(preset="lib:Base - Flat roof")
    snap_fa = vmt.snapshot_object(fx_a)
    cols_fa = {s_["name"]: [v[1][2] for v in s_["values"].values()
                            if v[1][1] == "NodeSocketCollection" and v[1][2]] for s_ in snap_fa}
    inst_fa = mod_instances(fx_a)
    lib_col_fx = bpy.data.collections.get(vmt.LIBRARY_COLLECTION)
    excluded = []
    if lib_col_fx is not None:
        for lc in fx_scene.view_layers[0].layer_collection.children:
            if lc.collection == lib_col_fx:
                excluded.append(lc.exclude)
    fx_ver = vmt.file_engine_version()
    check("addon(fresh file): ONE 'Apply Preset' click (Base - Flat roof) imports the engine + "
          "pack into an EMPTY file and builds the full stack with every pack collection "
          "assigned - plank walls, ONE door, windows on the other walls, the pack stays hidden",
          r_a == {'FINISHED'} and len(snap_fa) == 5 and fx_ver == ENGINE_VERSION
          and inst_fa.get("VM_SceneDetailer_Planks", 0) > 0 and inst_fa.get("VM_SceneDetailer_Door") == 1
          and inst_fa.get("VM_SceneDetailer_Windows", 0) >= 2
          and all(cols_fa.get(n) for n in ("VM_SceneDetailer_Planks", "VM_SceneDetailer_Shingles",
                                           "VM_SceneDetailer_Door", "VM_SceneDetailer_Windows"))
          and excluded == [True] and not dup_names(),
          f"result={r_a}, engine={fx_ver}, instances per layer={inst_fa}, collections={cols_fa}, "
          f"AssetLibrary excluded={excluded}, .00N duplicates={dup_names()}")
    n_data = (len(bpy.data.node_groups), len(bpy.data.collections), len(bpy.data.materials),
              len(bpy.data.objects))
    fx_b = fx_cube("FreshB", 5.0)
    bpy.ops.vm.apply_preset(preset="lib:Base - Gable roof")
    fx_c = fx_cube("FreshC", 10.0)
    bpy.ops.vm.dress_object()
    n_data2 = (len(bpy.data.node_groups), len(bpy.data.collections), len(bpy.data.materials),
               len(bpy.data.objects) - 2)
    snap_fc = vmt.snapshot_object(fx_c)
    inst_fb = mod_instances(fx_b)
    b_style = str(getattr(fx_b.modifiers["VM_RoofCap"].properties.inputs,
                          socket_id(fx_b.modifiers["VM_RoofCap"].node_group, "Style")).value)
    check("addon(fresh file): applying more presets / Dress Object on new objects imports "
          "NOTHING twice; Dress Object == the clean 'Base - Flat roof' preset; the Gable "
          "preset gets shingles on its slopes",
          n_data == n_data2 and not dup_names() and snap_fc == snap_fa and b_style == "Gable"
          and inst_fb.get("VM_SceneDetailer_Shingles", 0) > 0,
          f"datablocks (groups, collections, materials, objects) {n_data} -> {n_data2}, "
          f"Gable cube Style={b_style} instances={inst_fb}, Dress == Flat preset: {snap_fc == snap_fa}, "
          f"duplicates={dup_names()}")

    # ---- v2.10: UPDATE an older engine in place - settings survive
    planks_a = fx_a.modifiers["VM_SceneDetailer_Planks"]
    set_params(planks_a, planks_a.node_group, {"Row Height": 0.31})
    for g_ in vmt.VM_GROUPS:
        it_ = vmt.find_input(vmt.resolve_group(g_), "Engine Version")
        it_.default_value = "v2.8"
        vmt.sync_version_labels(vmt.resolve_group(g_))
    fx_a.update_tag()
    old_ver = vmt.file_engine_version()
    inst_before = mod_instances(fx_a)
    snap_before = vmt.snapshot_object(fx_a)
    r_u = bpy.ops.vm.import_engine()
    snap_after = vmt.snapshot_object(fx_a)
    inst_after = mod_instances(fx_a)
    row_h = sock_val(fx_a, "VM_SceneDetailer_Planks", "Row Height")
    labels = sorted({str(sock_val(o, m.name, "Engine Version")) for o in (fx_a, fx_b, fx_c)
                     for m in o.modifiers if vmt.is_vm_modifier(m)})

    def strip_ver(sn):
        return [dict(s_, values={k: v for k, v in s_["values"].items() if v[0] != "Engine Version"})
                for s_ in sn]
    check(f"addon(update): 'Import / Update Engine' upgrades an OLD engine ({old_ver}) to "
          f"{ENGINE_VERSION} IN PLACE - every modifier keeps its settings (edited Row Height "
          f"0.31 survives), the About panel of every object shows the new version, nothing duplicated",
          r_u == {'FINISHED'} and old_ver == "v2.8" and vmt.file_engine_version() == ENGINE_VERSION
          and abs(row_h - 0.31) < 1e-6 and strip_ver(snap_before) == strip_ver(snap_after)
          and inst_before == inst_after and labels == [ENGINE_VERSION] and not dup_names()
          and len(bpy.data.node_groups) == n_data[0],
          f"{old_ver} -> {vmt.file_engine_version()}, Row Height={row_h}, settings identical="
          f"{strip_ver(snap_before) == strip_ver(snap_after)}, instances {inst_before} -> "
          f"{inst_after}, About labels={labels}, node groups={len(bpy.data.node_groups)}, "
          f"duplicates={dup_names()}")
    # ---- v2.10: UPPER STOREYS get windows (the user's multi-storey report)
    def storey_mesh(name, boxes, x, bisect_z=None):
        me_ = bpy.data.meshes.new(name)
        bm_ = bmesh.new()
        for (x0, y0, z0, x1, y1, z1) in boxes:
            bmesh.ops.create_cube(bm_, size=1.0, matrix=Matrix.LocRotScale(
                ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), None, (x1 - x0, y1 - y0, z1 - z0)))
        if bisect_z is not None:
            bmesh.ops.bisect_plane(bm_, geom=bm_.verts[:] + bm_.edges[:] + bm_.faces[:],
                                   plane_co=(0, 0, bisect_z), plane_no=(0, 0, 1))
        bm_.to_mesh(me_)
        bm_.free()
        ob_ = bpy.data.objects.new(name, me_)
        fx_scene.collection.objects.link(ob_)
        ob_.location = (x, 12.0, 0)
        bpy.ops.object.select_all(action='DESELECT')
        ob_.select_set(True)
        fx_scene.view_layers[0].objects.active = ob_
        bpy.ops.vm.dress_object()
        return ob_

    st_cases = {
        "two boxes stacked": storey_mesh("StoreyStacked", [(0, 0, 0, 5, 4, 3), (0, 0, 3, 5, 4, 6)], 0.0),
        "one mesh, edge loop at 3 m": storey_mesh("StoreyLoop", [(0, 0, 0, 5, 4, 6)], 8.0, bisect_z=3.0),
        "setback upper storey": storey_mesh("StoreySetback", [(0, 0, 0, 5, 4, 3), (0.8, 0.6, 3, 4.2, 3.4, 6)], 16.0),
        "one 6 m wall face": storey_mesh("StoreyTall", [(0, 0, 0, 5, 4, 6)], 24.0),
    }
    win_names = {o.name for o in bpy.data.collections["VM_Windows"].all_objects}
    dg_st = bpy.context.evaluated_depsgraph_get()
    dg_st.update()
    st_rows = {k: Counter() for k in st_cases}
    by_ob = {o.name: k for k, o in st_cases.items()}
    for inst in dg_st.object_instances:
        if inst.is_instance and inst.parent is not None and inst.parent.original.name in by_ob                 and inst.object.name in win_names:
            z_ = inst.matrix_world.translation.z
            st_rows[by_ob[inst.parent.original.name]]["upper" if z_ > 3.0 else "ground"] += 1
    check("v2.10(upper storeys): Dress Object puts windows on BOTH storeys - stacked boxes, "
          "one mesh with a storey edge loop, a setback upper storey and a single 6 m wall "
          "(before: upper-storey walls got none)",
          all(r["ground"] >= 2 and r["upper"] >= 2 for r in st_rows.values()),
          f"windows per storey: {{{', '.join(f'{k}: {dict(v)}' for k, v in st_rows.items())}}}")
    results["upper_storeys"] = {k: dict(v) for k, v in st_rows.items()}

    results["addon_library"] = dict(fresh_instances=inst_fa, update_instances=inst_after,
                                    datablocks=n_data)
    vmt.LIBRARY_PATH_OVERRIDE = ""

    def _jsonable(o):
        # results carry Counter/dict data keyed by tuples (plane keys, zone keys)
        # - json.dump cannot encode non-str KEYS, so stringify them recursively
        if isinstance(o, dict):
            return {(k if isinstance(k, (str, int, float, bool)) else str(k)): _jsonable(v)
                    for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [_jsonable(v) for v in o]
        return o

    with open(os.path.join(ROOT, "verification_v2.json"), "w") as f:
        json.dump({"results": _jsonable(results),
                   "checks": [{"name": n, "pass": p, "detail": d} for n, p, d in checks]}, f, indent=2, default=str)

    failed = [c[0] for c in checks if not c[1]]
    log(f"\n== CHECKS: {len(checks) - len(failed)}/{len(checks)} passed")
    if failed:
        log("!! FAILED: " + ", ".join(failed))

    # deliverables
    os.makedirs(DELIVER, exist_ok=True)
    for f in ("build_engine.py", "pack_ingest.py", "USAGE.txt", "VM_Tools_Addon.py"):
        src = os.path.join(_HERE, f)   # sources live next to this script, not in the build dir
        if os.path.abspath(src) != os.path.abspath(os.path.join(DELIVER, f)):
            shutil.copy2(src, os.path.join(DELIVER, f))
    for rep_name in sorted(os.listdir(ROOT)):
        if rep_name.endswith("_ingest.json"):
            shutil.copy2(os.path.join(ROOT, rep_name), os.path.join(DELIVER, rep_name))
    shutil.copy2(STARTER_PATH, os.path.join(DELIVER, "VM_Starter.blend"))
    shutil.copy2(BLEND_PATH, os.path.join(DELIVER, "VM_SceneDetailer.blend"))
    shutil.copy2(ROOFCAP_PATH, os.path.join(DELIVER, "VM_RoofCap.blend"))
    shutil.copy2(ASSETS_PATH, os.path.join(DELIVER, "VM_Assets.blend"))
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
