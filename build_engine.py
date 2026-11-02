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
ENGINE_VERSION = "v2.23"   # the ONE version label: About sockets, descriptions, checks, add-on
# v2.23 doors set INTO the wall (world m): the leaf front this far behind the
# wall face, a gap round the leaf in its hole, and the casing boards round it
DOOR_RECESS, DOOR_GAP = 0.03, 0.01
DOOR_SILL_CUT = 0.1   # the door hole runs this far below the threshold (no board under it)
CASING_W, CASING_HEAD, CASING_T = 0.09, 0.12, 0.025
RAKE_W = 0.17   # v2.23 rake boards along sloped wall edges (world m)
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


def make_glass_material(name):
    """v2.18 old window glass: thin (no refraction offset - a Fresnel mix of a
    tinted Transparent and a Glossy), a little grime, and BROKEN by the pane's
    Instancer attribute vm_gbrk (0 whole - 1 smashed): Voronoi shards (in
    meters, from vm_gsize) drop out where their random < vm_gbrk, those along
    the frame hold on longer, and the remaining glass shows its cracks."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n_ in list(nt.nodes):
        nt.nodes.remove(n_)
    N = nt.nodes.new
    L = nt.links.new

    def attr(nm_, x_, y_):
        a_ = N("ShaderNodeAttribute"); a_.attribute_type = "INSTANCER"; a_.attribute_name = nm_
        a_.location = (x_, y_)
        return a_

    def math_(op_, a_, b_, x_, y_):
        m_ = N("ShaderNodeMath"); m_.operation = op_; m_.location = (x_, y_)
        for k_, v_ in enumerate((a_, b_)):
            if isinstance(v_, (int, float)):
                m_.inputs[k_].default_value = v_
            else:
                L(v_, m_.inputs[k_])
        return m_.outputs[0]
    uv = N("ShaderNodeUVMap"); uv.uv_map = "UVMap"; uv.location = (-1600, 0)
    a_brk = attr("vm_gbrk", -1600, -300)
    a_seed = attr("vm_gseed", -1600, -450)
    a_size = attr("vm_gsize", -1600, -600)
    uvs = N("ShaderNodeSeparateXYZ"); uvs.location = (-1400, 0)
    L(uv.outputs["UV"], uvs.inputs["Vector"])
    szs = N("ShaderNodeSeparateXYZ"); szs.location = (-1400, -600)
    L(a_size.outputs["Vector"], szs.inputs["Vector"])
    u_m = math_("MULTIPLY", uvs.outputs["X"], szs.outputs["X"], -1200, 50)
    v_m = math_("MULTIPLY", uvs.outputs["Y"], szs.outputs["Z"], -1200, -50)
    w_m = math_("MULTIPLY", a_seed.outputs["Fac"], 37.0, -1200, -150)
    co = N("ShaderNodeCombineXYZ"); co.location = (-1050, 0)
    L(u_m, co.inputs["X"]); L(v_m, co.inputs["Y"]); L(w_m, co.inputs["Z"])
    vor = N("ShaderNodeTexVoronoi"); vor.location = (-850, 100)
    vor.inputs["Scale"].default_value = 7.0
    vor.inputs["Randomness"].default_value = 1.0
    L(co.outputs["Vector"], vor.inputs["Vector"])
    vor_e = N("ShaderNodeTexVoronoi"); vor_e.feature = "DISTANCE_TO_EDGE"; vor_e.location = (-850, -200)
    vor_e.inputs["Scale"].default_value = 7.0
    vor_e.inputs["Randomness"].default_value = 1.0
    L(co.outputs["Vector"], vor_e.inputs["Vector"])
    cell = N("ShaderNodeSeparateColor"); cell.location = (-650, 100)
    L(vor.outputs["Color"], cell.inputs["Color"])
    # distance to the nearest frame edge (m): shards there hold on
    d_u = math_("MINIMUM", u_m, math_("SUBTRACT", szs.outputs["X"], u_m, -1050, 200), -900, 250)
    d_v = math_("MINIMUM", v_m, math_("SUBTRACT", szs.outputs["Z"], v_m, -1050, 300), -900, 350)
    d_e = math_("MINIMUM", d_u, d_v, -750, 300)
    near = N("ShaderNodeMapRange"); near.location = (-600, 350)
    L(d_e, near.inputs["Value"])
    near.inputs["From Min"].default_value = 0.0
    near.inputs["From Max"].default_value = 0.12
    near.inputs["To Min"].default_value = 0.35
    near.inputs["To Max"].default_value = 1.0
    brk_eff = math_("MULTIPLY", a_brk.outputs["Fac"], near.outputs["Result"], -450, 300)
    gone = math_("LESS_THAN", cell.outputs["Red"], brk_eff, -300, 200)
    # cracks: thin lines along the shard edges, only on broken panes
    crack_l = math_("LESS_THAN", vor_e.outputs["Distance"], 0.012, -650, -200)
    crack = math_("MULTIPLY", crack_l, math_("GREATER_THAN", a_brk.outputs["Fac"], 0.05, -650, -350),
                  -450, -250)
    # the glass itself: thin, a touch green, grimy
    tr = N("ShaderNodeBsdfTransparent"); tr.location = (-300, -50)
    tr.inputs["Color"].default_value = (0.78, 0.84, 0.8, 1.0)
    gl = N("ShaderNodeBsdfGlossy"); gl.location = (-300, -180)
    gl.inputs["Roughness"].default_value = 0.06
    fr = N("ShaderNodeFresnel"); fr.location = (-300, 80)
    fr.inputs["IOR"].default_value = 1.5
    mix_g = N("ShaderNodeMixShader"); mix_g.location = (-100, -50)
    L(fr.outputs["Fac"], mix_g.inputs["Fac"])
    L(tr.outputs["BSDF"], mix_g.inputs[1]); L(gl.outputs["BSDF"], mix_g.inputs[2])
    grime_n = N("ShaderNodeTexNoise"); grime_n.location = (-650, -500)
    grime_n.inputs["Scale"].default_value = 3.0
    L(co.outputs["Vector"], grime_n.inputs["Vector"])
    grime = N("ShaderNodeMapRange"); grime.location = (-450, -500)
    L(grime_n.outputs["Fac"], grime.inputs["Value"])
    grime.inputs["From Min"].default_value = 0.35
    grime.inputs["From Max"].default_value = 0.75
    grime.inputs["To Min"].default_value = 0.08
    grime.inputs["To Max"].default_value = 0.4
    dirt = N("ShaderNodeBsdfDiffuse"); dirt.location = (-300, -350)
    dirt.inputs["Color"].default_value = (0.32, 0.3, 0.25, 1.0)
    mix_d = N("ShaderNodeMixShader"); mix_d.location = (50, -100)
    L(math_("MAXIMUM", grime.outputs["Result"], math_("MULTIPLY", crack, 0.85, -300, -600), -150, -550),
      mix_d.inputs["Fac"])
    L(mix_g.outputs["Shader"], mix_d.inputs[1]); L(dirt.outputs["BSDF"], mix_d.inputs[2])
    hole = N("ShaderNodeBsdfTransparent"); hole.location = (50, 100)
    mix_h = N("ShaderNodeMixShader"); mix_h.location = (250, 0)
    L(gone, mix_h.inputs["Fac"])
    L(mix_d.outputs["Shader"], mix_h.inputs[1]); L(hole.outputs["BSDF"], mix_h.inputs[2])
    out = N("ShaderNodeOutputMaterial"); out.location = (450, 0)
    L(mix_h.outputs["Shader"], out.inputs["Surface"])
    return mat


def make_leaf_material(name):
    """v2.20 ivy leaf (the leaf is real lobed geometry - no alpha): UVs in
    leaf space (base at 0,0, tip at 0,1). Five pale veins fan out from the
    stalk into the lobes; greens varied per leaf with a few yellowing ones
    (Object Info Random); glossy, lit through a little."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n_ in list(nt.nodes):
        nt.nodes.remove(n_)
    N = nt.nodes.new
    L = nt.links.new

    def math_(op_, a_, b_, x_, y_):
        m_ = N("ShaderNodeMath"); m_.operation = op_; m_.location = (x_, y_)
        for k_, v_ in enumerate((a_, b_)):
            if isinstance(v_, (int, float)):
                m_.inputs[k_].default_value = v_
            else:
                L(v_, m_.inputs[k_])
        return m_.outputs[0]
    uv = N("ShaderNodeUVMap"); uv.uv_map = "UVMap"; uv.location = (-1400, 0)
    sp = N("ShaderNodeSeparateXYZ"); sp.location = (-1200, 0)
    L(uv.outputs["UV"], sp.inputs["Vector"])
    phi = math_("ARCTAN2", sp.outputs["X"], sp.outputs["Y"], -1000, 100)
    dist = N("ShaderNodeVectorMath"); dist.operation = "LENGTH"; dist.location = (-1000, -50)
    L(uv.outputs["UV"], dist.inputs[0])
    # |sin(2.5 phi)| is 0 along the five lobe axes; times the distance from
    # the stalk -> lines of constant width
    off = math_("MULTIPLY", math_("ABSOLUTE", math_("SINE", math_("MULTIPLY", phi, 2.5, -850, 100), 0.0, -700, 100),
                                  0.0, -550, 100), dist.outputs["Value"], -400, 100)
    vein = math_("SUBTRACT", 1.0, math_("MINIMUM", math_("DIVIDE", off, 0.018, -250, 100), 1.0, -100, 100), 50, 100)
    vein = math_("MULTIPLY", vein, math_("LESS_THAN", dist.outputs["Value"], 0.75, -250, -50), 200, 100)
    oi = N("ShaderNodeObjectInfo"); oi.location = (-800, -300)
    ramp = N("ShaderNodeValToRGB"); ramp.location = (-600, -300)
    L(oi.outputs["Random"], ramp.inputs["Fac"])
    els = ramp.color_ramp.elements
    els[0].position = 0.0; els[0].color = (0.018, 0.05, 0.012, 1.0)
    els[1].position = 0.8; els[1].color = (0.05, 0.11, 0.02, 1.0)
    e3 = els.new(0.93); e3.color = (0.11, 0.15, 0.025, 1.0)
    e4 = els.new(1.0); e4.color = (0.28, 0.2, 0.04, 1.0)
    pale = N("ShaderNodeMix"); pale.data_type = "RGBA"; pale.location = (-300, -300)
    L(math_("MULTIPLY", vein, 0.6, 350, 100), pale.inputs["Factor"])
    L(ramp.outputs["Color"], pale.inputs["A"])
    pale.inputs["B"].default_value = (0.2, 0.26, 0.09, 1.0)
    bsdf = N("ShaderNodeBsdfPrincipled"); bsdf.location = (-50, -250)
    L(pale.outputs["Result"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.38
    tl = N("ShaderNodeBsdfTranslucent"); tl.location = (-50, -500)
    L(ramp.outputs["Color"], tl.inputs["Color"])
    mix_t = N("ShaderNodeMixShader"); mix_t.location = (200, -300)
    mix_t.inputs["Fac"].default_value = 0.2
    L(bsdf.outputs["BSDF"], mix_t.inputs[1]); L(tl.outputs["BSDF"], mix_t.inputs[2])
    out = N("ShaderNodeOutputMaterial"); out.location = (450, -300)
    L(mix_t.outputs["Shader"], out.inputs["Surface"])
    return mat


def make_textured_material(name, tdir, diff_f, rough_f=None, nor_f=None, scale=0.35, darken=1.0):
    """Principled material with Object-coord image textures (read-only asset lib).
    darken < 1 scales the colour's value (v2.12 sheathing behind the siding)."""
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
    if darken != 1.0:
        hsv = nt.nodes.new("ShaderNodeHueSaturation"); hsv.location = (-350, 200)
        hsv.inputs["Value"].default_value = darken
        nt.links.new(it_d.outputs["Color"], hsv.inputs["Color"])
        nt.links.new(hsv.outputs["Color"], bsdf.inputs["Base Color"])
    else:
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


def make_board_material(name, tdir, tex, n_boards, phase, tex_w, value_lo=0.75, value_hi=1.1,
                        darken=1.0):
    """v2.11 per-tile wood material for the 3D cladding tiles. The tile meshes
    carry UVs with U = meters ALONG the grain and V = 0..1 ACROSS the tile; the
    shader maps every instance onto ONE whole board of a plank texture
    (n_boards evenly spaced boards starting at `phase`, measured from the
    texture's normal map), picked by Object Info > Random, at a random offset
    along the grain, with a per-tile brightness shift. So no two neighbouring
    tiles show the same wood and no texture seam runs through a tile."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]

    def node(t, loc, **kw):
        n = nt.nodes.new(t)
        n.location = loc
        for k, v in kw.items():
            setattr(n, k, v)
        return n

    def math(op, a, b=None, loc=(0, 0)):
        n = node("ShaderNodeMath", loc, operation=op)
        for i, x in enumerate((a, b)):
            if x is None:
                continue
            if isinstance(x, (int, float)):
                n.inputs[i].default_value = x
            else:
                nt.links.new(x, n.inputs[i])
        return n.outputs["Value"]

    uv = node("ShaderNodeUVMap", (-1500, 0))
    sep = node("ShaderNodeSeparateXYZ", (-1300, 0))
    nt.links.new(uv.outputs["UV"], sep.inputs["Vector"])
    oi = node("ShaderNodeObjectInfo", (-1500, -300))
    r = oi.outputs["Random"]
    r_board = math("FRACT", math("MULTIPLY", r, 7.31, (-1300, -250)), None, (-1150, -250))
    r_val = math("FRACT", math("MULTIPLY", r, 3.17, (-1300, -400)), None, (-1150, -400))
    board = math("FLOOR", math("MULTIPLY", r_board, float(n_boards), (-1000, -250)), None, (-850, -250))
    v_in = math("MULTIPLY_ADD", sep.outputs["Y"], 0.84, (-1100, -50))
    v_in.node.inputs[2].default_value = 0.08
    v_b = math("ADD", v_in, board, (-850, -50))
    v_n = math("DIVIDE", v_b, float(n_boards), (-700, -50))
    v_out = math("ADD", v_n, phase, (-550, -50))
    u_n = math("DIVIDE", sep.outputs["X"], tex_w, (-1100, 100))
    u_out = math("MULTIPLY_ADD", r, 13.7, (-850, 100))
    u_out.node.inputs[2].default_value = 0.0
    nt.links.new(u_n, u_out.node.inputs[2])
    comb = node("ShaderNodeCombineXYZ", (-400, 50))
    nt.links.new(u_out, comb.inputs["X"])
    nt.links.new(v_out, comb.inputs["Y"])

    def img(suffix, loc, data):
        im = bpy.data.images.load(os.path.join(tdir, f"{tex}_{suffix}.jpg"), check_existing=True)
        if data:
            im.colorspace_settings.name = "Non-Color"
        n = node("ShaderNodeTexImage", loc, image=im)
        nt.links.new(comb.outputs["Vector"], n.inputs["Vector"])
        return n

    diff = img("diff", (-200, 300), False)
    hsv = node("ShaderNodeHueSaturation", (100, 300))
    val = math("MULTIPLY_ADD", r_val, value_hi - value_lo, (-100, 450))
    val.node.inputs[2].default_value = value_lo
    val_d = math("MULTIPLY", val, darken, (50, 450))
    nt.links.new(val_d, hsv.inputs["Value"])
    nt.links.new(diff.outputs["Color"], hsv.inputs["Color"])
    nt.links.new(hsv.outputs["Color"], bsdf.inputs["Base Color"])
    rough = img("rough", (-200, 0), True)
    nt.links.new(rough.outputs["Color"], bsdf.inputs["Roughness"])
    nor = img("nor", (-200, -300), True)
    nmap = node("ShaderNodeNormalMap", (100, -300))
    nt.links.new(nor.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def _tile_mesh(name, size_x, size_z, thick_lo, thick_hi, back, bevel, cuts_x, cuts_z, shape, uv_grain):
    """Closed wedge tile: X across/along the row, Z up the face, Y out of the
    face. Back plane at y=`back`, front at thick_lo (bottom edge, z=-size_z/2)
    tapering to thick_hi (top edge). `shape(v)` deforms each vertex last.
    UVs: U = meters along the grain (X for planks, Z for shakes), V = 0..1
    across it."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        x, y, z = v.co.x * size_x, v.co.y, v.co.z * size_z
        t = (0.5 - z / size_z)                       # 1 at the bottom edge, 0 at the top
        y = back if y < 0 else thick_hi + (thick_lo - thick_hi) * t
        v.co = (x, y, z)
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel, segments=1, affect="EDGES",
                        clamp_overlap=True)
    for k in range(1, cuts_x + 1):
        x0 = -size_x / 2 + size_x * k / (cuts_x + 1)
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                               plane_co=(x0, 0, 0), plane_no=(1, 0, 0))
    for k in range(1, cuts_z + 1):
        z0 = -size_z / 2 + size_z * k / (cuts_z + 1)
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                               plane_co=(0, 0, z0), plane_no=(0, 0, 1))
    uvl = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for lp in f.loops:
            x, z = lp.vert.co.x, lp.vert.co.z
            if uv_grain == "X":
                lp[uvl].uv = (x + size_x / 2, min(max(z / size_z + 0.5, 0.0), 1.0))
            else:
                lp[uvl].uv = (z + size_z / 2, min(max(x / size_x + 0.5, 0.0), 1.0))
    for v in bm.verts:
        shape(v)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = False
    return me


def make_siding_variants(col, name, n, mat, length=2.0, width=0.2, butt=0.022, top=0.006, seed=7):
    """v2.11 lap-siding boards (the user's 'walls are not a flat surface'
    reference): a wedge profile - thick bottom edge, thin top - so every course
    laps over the one below and casts a real shadow line; chamfered edges catch
    the light; each variant has its own slight bow and twist."""
    import random
    rng = random.Random(seed)
    out = []
    for i in range(n):
        bow = rng.uniform(-0.004, 0.004)
        twist = rng.uniform(-0.003, 0.003)
        cup = rng.uniform(0.0, 0.002)

        def shape(v, bow=bow, twist=twist, cup=cup):
            s = v.co.x / (length / 2)                       # -1..1 along the board
            v.co.z += bow * (1 - s * s)
            v.co.y += twist * s * (v.co.z / (width / 2)) + cup * (1 - s * s) * (v.co.y > 0)

        me = _tile_mesh(f"{name}_{i + 1:02d}", length, width, butt, top, -0.006, 0.0018,
                        7, 1, shape, "X")
        me.materials.append(mat)
        ob = bpy.data.objects.new(f"{name}_{i + 1:02d}", me)
        col.objects.link(ob)
        out.append(ob)
    return out


def make_shake_variants(col, name, n, mat, length=0.42, butt=0.024, tip=0.004, seed=11):
    """v2.11 split wooden shakes for the roof: tapered (thick butt at the bottom
    edge), cupped across the width, random widths (gaps between shakes) and
    some chipped butt corners."""
    import random
    rng = random.Random(seed)
    out = []
    for i in range(n):
        w = rng.uniform(0.165, 0.235)
        cup = rng.uniform(0.003, 0.008)
        chip = rng.choice([0.0, 0.0, 0.03, 0.05]) * rng.choice([-1, 1])
        lean = rng.uniform(-0.004, 0.004)

        def shape(v, w=w, cup=cup, chip=chip, lean=lean):
            sx = v.co.x / (w / 2)
            v.co.y += cup * sx * sx * (0.5 - v.co.z / length)
            v.co.x += lean * (0.5 - v.co.z / length)
            if chip and v.co.z < -length / 2 + 0.001 and sx * (1 if chip > 0 else -1) > 0.55:
                v.co.z += abs(chip) * (abs(sx) - 0.55) / 0.45

        me = _tile_mesh(f"{name}_{i + 1:02d}", w, length, butt, tip, -0.004, 0.0015,
                        3, 4, shape, "Z")
        me.materials.append(mat)
        ob = bpy.data.objects.new(f"{name}_{i + 1:02d}", me)
        col.objects.link(ob)
        out.append(ob)
    return out


def _outline_tile(name, outline, front_y, back, uv_grain, lo, span):
    """v2.13 damaged tile from a 2D outline: `outline` is the tile's silhouette
    as (x, z) points in order (X along/across the row, Z up the face), extruded
    from the flat back plane y=`back` to the front surface y=front_y(x, z) - the
    same wedge as the intact tiles, so jagged ends, splits and bites are REAL
    geometry. UVs follow _tile_mesh: U = meters along the grain, V = 0..1 across
    (`lo`, `span` = the across-grain extent)."""
    bm = bmesh.new()
    fv = [bm.verts.new((x, front_y(x, z), z)) for x, z in outline]
    bv = [bm.verts.new((x, back, z)) for x, z in outline]
    bm.faces.new(fv)
    bm.faces.new(list(reversed(bv)))
    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bv[i], bv[j], fv[j], fv[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    uvl = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for lp in f.loops:
            x, z = lp.vert.co.x, lp.vert.co.z
            if uv_grain == "X":
                lp[uvl].uv = (x, min(max((z - lo) / span, 0.0), 1.0))
            else:
                lp[uvl].uv = (z, min(max((x - lo) / span, 0.0), 1.0))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p_ in me.polygons:
        p_.use_smooth = False
    return me


def _jag(rng, a, b, n, depth, spike=0.0, spike_w=(0.008, 0.02)):
    """Jagged break line from a to b (the 'along' coordinate fixed at 0):
    returns [(offset, t)] with t running a -> b across the tile and offset the
    break's reach (+ = longer). One splinter spike sticks out when spike > 0."""
    pts = [(rng.uniform(-depth, depth * 0.4), a)]
    for k in range(1, n):
        pts.append((rng.uniform(-depth, depth * 0.6), a + (b - a) * (k + rng.uniform(-0.3, 0.3)) / n))
    if spike > 0:
        t0 = rng.uniform(a + (b - a) * 0.2, a + (b - a) * 0.7)
        w = rng.uniform(*spike_w) * (1 if b > a else -1)
        pts += [(depth * 0.3, t0), (spike, t0 + w * 0.4), (spike * 0.8, t0 + w), (0.0, t0 + w * 1.3)]
    pts.append((rng.uniform(-depth, depth * 0.4), b))
    return sorted(pts, key=lambda q: q[1] * (1 if b > a else -1))


def _mirror_x(outline):
    return [(-x, z) for x, z in reversed(outline)]


def make_broken_siding(col, name, n, mat, width=0.2, butt=0.022, top=0.006, seed=13):
    """v2.13 BROKEN siding pieces for the Damage panel's Broken Props: 1 m long,
    the NAILED (kept) end square at the origin, the free end a jagged break with
    a splinter. Pairs: _L runs along +X, _R is its mirror along -X (the engine
    picks the one whose nailed end sits next to an intact board)."""
    import random
    rng = random.Random(seed)
    h = width / 2

    def front(x, z):
        return -0.006 + butt + (top - butt) * (z + h) / width
    for i in range(n):
        # v2.14 variety: shallow snaps to deep ragged breaks, no / short / long
        # splinter, and sometimes a bite out of the top edge by the break
        depth = rng.uniform(0.03, 0.13)
        spike = rng.choice([0.0, rng.uniform(0.06, 0.14), rng.uniform(0.15, 0.3)])
        jag = _jag(rng, h, -h, rng.randint(3, 8), depth, spike=spike)
        top_e = []
        if rng.random() < 0.4:
            a0, bw, d = rng.uniform(0.35, 0.6), rng.uniform(0.1, 0.25), rng.uniform(0.02, 0.06)
            top_e = [(a0, h), (a0 + bw * 0.3, h - d), (a0 + bw * 0.7, h - d * 0.6), (a0 + bw, h)]
        ol = [(0.0, -h), (0.0, h)] + top_e + [(1.0 + off, t) for off, t in jag]
        for side, o in (("L", ol), ("R", _mirror_x(ol))):
            nm = f"{name}_{i + 1:02d}_{side}"
            me = _outline_tile(nm, o, front, -0.006, "X", -h, width)
            me.materials.append(mat)
            col.objects.link(bpy.data.objects.new(nm, me))


def make_broken_shakes(col, name, n, mat, width=0.2, butt=0.016, tip=0.004, seed=17):
    """v2.13 BROKEN shakes: the nailed top edge at the origin, 1 m down -Z
    (scaled to what remains), the butt broken off in a jagged line - often split
    up the grain. _L / _R are mirrored break patterns."""
    import random
    rng = random.Random(seed)
    w = width / 2

    def front(x, z):
        return -0.004 + tip + (butt - tip) * (-z)
    for i in range(n):
        jag = _jag(rng, w, -w, rng.randint(3, 6), rng.uniform(0.08, 0.22),
                   spike=rng.choice([0.0, rng.uniform(0.1, 0.3)]), spike_w=(0.015, 0.03))
        ol = [(-w, 0.0), (w, 0.0)] + [(t, -1.0 - off) for off, t in jag]
        ol = list(reversed(ol))
        for side, o in (("L", ol), ("R", _mirror_x(ol))):
            nm = f"{name}_{i + 1:02d}_{side}"
            me = _outline_tile(nm, o, front, -0.004, "Z", -w, width)
            me.materials.append(mat)
            col.objects.link(bpy.data.objects.new(nm, me))


def make_worn_siding(col, name, n, mat, length=2.0, width=0.2, butt=0.022, top=0.006, seed=19):
    """v2.13 WORN siding (the Damage panel's Worn Props, a band around the
    damage): full-size boards with an end SPLIT running up the grain, CHIPPED
    corners and BITES out of the edges - the same 2 x 0.2 m as the intact tiles."""
    import random
    rng = random.Random(seed)
    L, h = length / 2, width / 2

    def front(x, z):
        return -0.006 + butt + (top - butt) * (z + h) / width
    for i in range(n):
        right = [(L, -h)]
        if rng.random() < 0.3:                                # broken-off bottom corner
            c1, c2 = rng.uniform(0.02, 0.05), rng.uniform(0.03, 0.08)
            right = [(L - c2, -h), (L - c2 * 0.5, -h + c1 * 0.6), (L, -h + c1)]
        if rng.random() < 0.75:                               # end split
            z0, g, sl = rng.uniform(-0.02, 0.03), rng.uniform(0.003, 0.007), rng.uniform(0.3, 1.0)
            right += [(L, z0 - g / 2), (L - sl, z0), (L, z0 + g / 2)]
        right += [(L, h)]
        top_e = []
        if rng.random() < 0.5:                                # bite out of the top edge
            a0, bw, d = rng.uniform(-0.6, 0.4), rng.uniform(0.15, 0.4), rng.uniform(0.02, 0.06)
            top_e = [(a0 + bw, h), (a0 + bw * 0.6, h - d), (a0 + bw * 0.25, h - d * 0.7), (a0, h)]
        if rng.random() < 0.6:                                # top edge, worn ragged
            a1 = rng.uniform(-0.8, -0.75)
            top_e += [(a1 + 0.12, h), (a1 + 0.07, h - rng.uniform(0.01, 0.03)), (a1, h)]
        left = []
        if rng.random() < 0.6:                                # chipped corner
            c1, c2 = rng.uniform(0.03, 0.06), rng.uniform(0.06, 0.15)
            left = [(-L + c2, h), (-L + c2 * 0.45, h - c1 * 0.5), (-L, h - c1)]
        else:
            left = [(-L, h)]
        bot = []
        if rng.random() < 0.4:                                # bite out of the bottom edge
            a0, bw, d = rng.uniform(-0.4, 0.6), rng.uniform(0.1, 0.3), rng.uniform(0.02, 0.04)
            bot = [(a0, -h), (a0 + bw * 0.35, -h + d), (a0 + bw * 0.7, -h + d * 0.6), (a0 + bw, -h)]
        if rng.random() < 0.4:                                # second split, other end
            z1, g, sl = rng.uniform(-0.02, 0.03), rng.uniform(0.003, 0.006), rng.uniform(0.2, 0.8)
            left += [(-L, z1 + g / 2), (-L + sl, z1), (-L, z1 - g / 2)]
        ol = [(-L, -h)] + bot + right + top_e + left
        nm = f"{name}_{i + 1:02d}"
        me = _outline_tile(nm, ol, front, -0.006, "X", -h, width)
        me.materials.append(mat)
        col.objects.link(bpy.data.objects.new(nm, me))


def make_worn_shakes(col, name, n, mat, length=0.42, width=0.2, butt=0.024, tip=0.004, seed=23):
    """v2.13 WORN shakes: full-size, SPLIT up from the butt, with chipped and
    broken butt corners."""
    import random
    rng = random.Random(seed)
    L, w = length / 2, width / 2

    def front(x, z):
        return -0.004 + tip + (butt - tip) * (L - z) / length
    for i in range(n):
        bot = [(-w, -L)]
        if rng.random() < 0.3:
            c1 = rng.uniform(0.03, 0.08)
            bot = [(-w, -L + c1), (-w + c1 * 0.7, -L)]
        if rng.random() < 0.8:                                # split up from the butt
            x0, g, sl = rng.uniform(-w * 0.3, w * 0.3), rng.uniform(0.004, 0.01), rng.uniform(0.1, 0.3)
            bot += [(x0 - g / 2, -L), (x0, -L + sl), (x0 + g / 2, -L)]
        if rng.random() < 0.5:
            c1 = rng.uniform(0.03, 0.07)
            bot += [(w - c1 * 0.8, -L), (w, -L + c1)]
        else:
            bot += [(w, -L)]
        ol = bot + [(w, L), (-w, L)]
        nm = f"{name}_{i + 1:02d}"
        me = _outline_tile(nm, ol, front, -0.004, "Z", -w, width)
        me.materials.append(mat)
        col.objects.link(bpy.data.objects.new(nm, me))


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


def own_face_field(b, loc):
    """v2.16: 1.0 on faces of the building's own mesh, 0.0 on faces an earlier
    layer made (edge boards vm_trim, the opening interior shell vm_inner)."""
    acc = None
    for k, nm in enumerate(("vm_trim", "vm_inner")):
        rd = b.N("GeometryNodeInputNamedAttribute", (loc[0], loc[1] - 150 * k))
        rd.data_type = "FLOAT"
        rd.inputs["Name"].default_value = nm
        lt = b.N("ShaderNodeMath", (loc[0] + 150, loc[1] - 150 * k), operation="LESS_THAN")
        b.L(rd.outputs["Attribute"], lt.inputs[0])
        lt.inputs[1].default_value = 0.5
        if acc is None:
            acc = lt.outputs["Value"]
        else:
            mul = b.N("ShaderNodeMath", (loc[0] + 300, loc[1]), operation="MULTIPLY")
            b.L(acc, mul.inputs[0]); b.L(lt.outputs["Value"], mul.inputs[1])
            acc = mul.outputs["Value"]
    return acc


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
    # v2.16: faces an earlier layer made (edge boards, interior shell) belong
    # to no zone - they never take cladding, openings or a zone material
    conv = b.N("ShaderNodeMath", (loc[0] + 1250, loc[1]), operation="MULTIPLY")
    b.L(ext, conv.inputs[0])
    b.L(own_face_field(b, (loc[0] + 900, loc[1] - 400)), conv.inputs[1])
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
    b.menu_sock("Face Zone", p_zone, "Walls", "Which faces Fit/Cladding use (Scatter uses all faces). "
                "'Interior Floor' (v2.10): the building's downward-facing bottom faces, dressed from the "
                "INSIDE - boards lie on the bottom face facing up into the rooms")
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

    # v2.10 Interior Floor: exterior bottom faces (N.z <= -Roof Slope Min). The
    # selection is STORED before the sampling mesh flips those faces (below),
    # so it survives the flip that turns their normals up into the building.
    ifl_raw = zone_and(floor_lo.outputs["Result"], (-1000, 390))
    ifl_rd = b.N("GeometryNodeInputNamedAttribute", (-1250, 350))
    ifl_rd.data_type = "BOOLEAN"
    ifl_rd.inputs["Name"].default_value = "vm_ifl"
    zone_sel, zone_bools = b.menu_switch(
        ["All", "Walls", "Roof", "Floor", "Interior Floor"], "BOOLEAN", gi.outputs["Face Zone"],
        {"All": ext_ok, "Walls": is_wall.outputs["Boolean"], "Roof": is_roof.outputs["Boolean"],
         "Floor": is_floor.outputs["Boolean"], "Interior Floor": ifl_rd.outputs["Attribute"]},
        loc=(-1050, 650))

    # ---------------- base materials by zone (gated Set Material) ----------------
    # v2.11: on the MESH component only - Set Material on the whole input reaches
    # into earlier layers' instances and turns their object references into
    # anonymous geometry (the floor layer's boards lost their identity under
    # the wall layer once the floor moved to the bottom of the stack)
    mat_sep = b.N("GeometryNodeSeparateComponents", (-950, 1300))
    b.L(host_geo, mat_sep.inputs["Geometry"])
    base1 = material_gate(b, mat_sep.outputs["Mesh"], gi.outputs["Wall Material"],
                          is_wall.outputs["Boolean"], (-800, 1100))
    base2 = material_gate(b, base1, gi.outputs["Roof Material"],
                          is_roof.outputs["Boolean"], (-500, 1100))
    base3 = material_gate(b, base2, gi.outputs["Floor Material"],
                          is_floor.outputs["Boolean"], (-200, 1100))
    mat_join = b.N("GeometryNodeJoinGeometry", (0, 1300))
    for out_name in ("Instances", "Curve", "Point Cloud"):
        b.L(mat_sep.outputs[out_name], mat_join.inputs["Geometry"])
    b.L(base3, mat_join.inputs["Geometry"])
    base_out = mat_join.outputs["Geometry"]

    # sampling must only see the HOST MESH: in stacked modifiers the input also
    # carries earlier instances, and their faces must never receive new parts
    del_inst = b.N("GeometryNodeDeleteGeometry", (-200, 1350), domain="INSTANCE")
    b.L(base_out, del_inst.inputs["Geometry"])
    del_inst.inputs["Selection"].default_value = True
    # v2.10 Interior Floor: flip the bottom faces of the SAMPLING mesh only (the
    # output mesh keeps its normals) so every frame, course and offset below
    # treats them as an up-facing floor seen from inside the building
    st_ifl = b.N("GeometryNodeStoreNamedAttribute", (-50, 1350), data_type="BOOLEAN", domain="FACE")
    b.L(del_inst.outputs["Geometry"], st_ifl.inputs["Geometry"])
    st_ifl.inputs["Name"].default_value = "vm_ifl"
    b.L(ifl_raw.outputs["Boolean"], st_ifl.inputs["Value"])
    ifl_flip_sel = b.N("FunctionNodeBooleanMath", (-50, 1500), operation="AND")
    b.L(zone_bools["Interior Floor"], ifl_flip_sel.inputs[0])
    b.L(ifl_raw.outputs["Boolean"], ifl_flip_sel.inputs[1])
    ifl_flip = b.N("GeometryNodeFlipFaces", (100, 1350))
    b.L(st_ifl.outputs["Geometry"], ifl_flip.inputs["Mesh"])
    b.L(ifl_flip_sel.outputs["Boolean"], ifl_flip.inputs["Selection"])
    mesh_only = ifl_flip.outputs["Mesh"]

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

    # v2.11 Trim To Face follows the face OUTLINE: each corner's (u, v)
    # coordinate in the face frame (first 4 corners; Offset Corner wraps, so a
    # triangle repeats one corner and its zero-length edge is ignored)
    corner_ab = []
    for k in range(4):
        d_k = b.N("ShaderNodeVectorMath", (-1150, -4100 - 250 * k), operation="SUBTRACT")
        b.L(corner_pos(k), d_k.inputs[0])
        b.L(posf.outputs["Position"], d_k.inputs[1])
        ab_k = []
        for axis in (u_out, v_out):
            dt = b.N("ShaderNodeVectorMath", (-1000, -4100 - 250 * k), operation="DOT_PRODUCT")
            b.L(d_k.outputs["Vector"], dt.inputs[0])
            b.L(axis, dt.inputs[1])
            ab_k.append(dt.outputs["Value"])
        corner_ab.append(ab_k)

    # store frame data on faces -> transfer to face points / read for selection
    store_chain = mesh_only
    own_idx = b.N("GeometryNodeAccumulateField", (-600, -2600), domain="FACE")
    b.L(own_face_field(b, (-900, -2600)), own_idx.inputs["Value"])
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
              # v2.16: the index counts the building's OWN faces only - edge
              # boards split into damage pieces must not reshuffle the picks
              ("vm_fi", "FLOAT", own_idx.outputs["Trailing"]),
              # v2.4.1 world-space factors materialized here too: fields derived
              # from the Normal INPUT are only valid on the mesh domain (they
              # evaluate as garbage on POINT domains - the same class of problem
              # as the v2.4 corner-sampling contract), so point/selection
              # consumers read these back as simple named attributes.
              ("vm_eu", "FLOAT", eff_u),
              ("vm_ev", "FLOAT", eff_v),
              ("vm_en", "FLOAT", eff_n)]
    for k in range(4):
        stores += [(f"vm_ca{k}", "FLOAT", corner_ab[k][0]), (f"vm_cb{k}", "FLOAT", corner_ab[k][1])]
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
    # v2.22: a dormer's front wall (vm_dfront, VM_RoofCap) is MADE to hold one
    # window - the minimum face size never rules it out
    na_df = named_face("vm_dfront")
    df_face = b.N("FunctionNodeCompare", (-850, -1350), data_type="FLOAT", operation="GREATER_THAN")
    b.L(na_df, df_face.inputs["A"])
    df_face.inputs["B"].default_value = 0.5
    sel_wd = b.N("FunctionNodeBooleanMath", (-750, -1150), operation="OR")
    b.L(sel_w.outputs["Result"], sel_wd.inputs[0])
    b.L(df_face.outputs["Result"], sel_wd.inputs[1])
    sel_hd = b.N("FunctionNodeBooleanMath", (-750, -1250), operation="OR")
    b.L(sel_h.outputs["Result"], sel_hd.inputs[0])
    b.L(df_face.outputs["Result"], sel_hd.inputs[1])
    sel_f1 = b.N("FunctionNodeBooleanMath", (-650, -1100), operation="AND")
    b.L(zone_sel, sel_f1.inputs[0])
    b.L(sel_wd.outputs["Boolean"], sel_f1.inputs[1])
    sel_f2 = b.N("FunctionNodeBooleanMath", (-500, -1100), operation="AND")
    b.L(sel_f1.outputs["Boolean"], sel_f2.inputs[0])
    b.L(sel_hd.outputs["Boolean"], sel_f2.inputs[1])
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
    # v2.22: the dormer fronts of one slope are COPLANAR, each its own face -
    # their face-relative strip 0 collided in the greedy (one window per
    # slope). Dormer fronts take an ABSOLUTE column on the plane instead.
    dfc_d = b.N("ShaderNodeVectorMath", (1600, -3150), operation="DOT_PRODUCT")
    b.L(r_c, dfc_d.inputs[0]); b.L(r_u, dfc_d.inputs[1])
    dfc_q = b.N("ShaderNodeMath", (1750, -3150), operation="DIVIDE")
    b.L(dfc_d.outputs["Value"], dfc_q.inputs[0]); b.L(strip_pitch.outputs["Value"], dfc_q.inputs[1])
    dfc_f = b.N("ShaderNodeMath", (1900, -3150), operation="FLOOR")
    b.L(dfc_q.outputs["Value"], dfc_f.inputs[0])
    dfc_o = b.N("ShaderNodeMath", (2050, -3150), operation="ADD")
    b.L(dfc_f.outputs["Value"], dfc_o.inputs[0]); dfc_o.inputs[1].default_value = 32.0
    dfc_c = b.N("ShaderNodeClamp", (2200, -3150))
    b.L(dfc_o.outputs["Value"], dfc_c.inputs["Value"])
    dfc_c.inputs["Min"].default_value = 0.0; dfc_c.inputs["Max"].default_value = 63.0
    dfc_is = b.N("FunctionNodeCompare", (2200, -3050), data_type="FLOAT", operation="GREATER_THAN")
    b.L(rnamed("vm_dfront"), dfc_is.inputs["A"]); dfc_is.inputs["B"].default_value = 0.5
    dfc_sw = b.N("GeometryNodeSwitch", (2350, -3100))
    dfc_sw.input_type = "FLOAT"
    b.L(dfc_is.outputs["Result"], dfc_sw.inputs["Switch"])
    b.L(s_rand.outputs["Value"], dfc_sw.inputs["False"])
    b.L(dfc_c.outputs["Result"], dfc_sw.inputs["True"])
    b.L(dfc_sw.outputs["Output"], rg1.inputs["Value"])
    rg2 = b.N("GeometryNodeStoreNamedAttribute", (2200, -150), data_type="FLOAT", domain="POINT")
    b.L(rg1.outputs["Geometry"], rg2.inputs["Geometry"])
    rg2.inputs["Name"].default_value = "vm_grow"
    rg2.inputs["Value"].default_value = 0.0
    rg3 = b.N("GeometryNodeStoreNamedAttribute", (2400, -150), data_type="FLOAT", domain="POINT")
    b.L(rg2.outputs["Geometry"], rg3.inputs["Geometry"])
    rg3.inputs["Name"].default_value = "vm_gate1"
    eg_f = b.N("ShaderNodeMath", (2200, -4000), operation="ADD")
    # v2.22: a dormer front is made for its one window - no edge guard (the
    # opening's Scale To Face fits it to the narrow wall)
    eg_df = b.N("FunctionNodeBooleanMath", (2050, -4000), operation="OR")
    b.L(edge_ok.outputs["Boolean"], eg_df.inputs[0])
    b.L(dfc_is.outputs["Result"], eg_df.inputs[1])
    b.L(eg_df.outputs["Boolean"], eg_f.inputs[0])
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
    # v2.22: a dormer's front wall (vm_dfront, from VM_RoofCap) is short - its
    # window sits 15 cm over the roof, not at the storey's Sill Height
    df_v = snamed("vm_dfront")
    df_is = b.N("FunctionNodeCompare", (3850, -1450), data_type="FLOAT", operation="GREATER_THAN")
    b.L(df_v, df_is.inputs["A"])
    df_is.inputs["B"].default_value = 0.5
    df_sill = b.N("ShaderNodeMath", (3850, -1400), operation="DIVIDE")
    df_sill.inputs[0].default_value = 0.15
    b.L(sz_g, df_sill.inputs[1])
    df_sw = b.N("GeometryNodeSwitch", (3950, -1450))
    df_sw.input_type = "FLOAT"
    b.L(df_is.outputs["Result"], df_sw.inputs["Switch"])
    b.L(sill_l.outputs["Value"], df_sw.inputs["False"])
    b.L(df_sill.outputs["Value"], df_sw.inputs["True"])
    b.L(df_sw.outputs["Output"], targ_face.inputs[1])
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
    # v2.22: coplanar dormer fronts each count their slot column from 0 - give
    # them an ABSOLUTE column (0.5 m world bins along the plane) so the greedy
    # keeps a window on every dormer, not one per slope
    sdf_d = b.N("ShaderNodeVectorMath", (5750, -600), operation="DOT_PRODUCT")
    b.L(sc_v, sdf_d.inputs[0]); b.L(su_v, sdf_d.inputs[1])
    sdf_w = b.N("ShaderNodeMath", (5900, -600), operation="MULTIPLY")
    b.L(sdf_d.outputs["Value"], sdf_w.inputs[0]); b.L(seu_v, sdf_w.inputs[1])
    sdf_q = b.N("ShaderNodeMath", (6050, -600), operation="MULTIPLY_ADD")
    b.L(sdf_w.outputs["Value"], sdf_q.inputs[0])
    sdf_q.inputs[1].default_value = 2.0
    sdf_q.inputs[2].default_value = 32.0
    sdf_f = b.N("ShaderNodeMath", (6200, -600), operation="FLOOR")
    b.L(sdf_q.outputs["Value"], sdf_f.inputs[0])
    sdf_c = b.N("ShaderNodeClamp", (6350, -600))
    b.L(sdf_f.outputs["Value"], sdf_c.inputs["Value"])
    sdf_c.inputs["Min"].default_value = 0.0; sdf_c.inputs["Max"].default_value = 63.0
    sdf_sw = b.N("GeometryNodeSwitch", (6500, -600))
    sdf_sw.input_type = "FLOAT"
    b.L(df_is.outputs["Result"], sdf_sw.inputs["Switch"])
    b.L(sgi_v, sdf_sw.inputs["False"])
    b.L(sdf_c.outputs["Result"], sdf_sw.inputs["True"])
    b.L(sdf_sw.outputs["Output"], sg_a.inputs["Value"])
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

    # v2.10 Trim To Face: the socket is created LAST (socket identifiers keep
    # their order for old stacks) and linked into this OR at the end
    trim_in = b.N("FunctionNodeBooleanMath", (2050, -2350), operation="OR")
    trim_in.inputs[1].default_value = False
    trim_on = trim_in.outputs["Boolean"]
    keep_i = b.N("FunctionNodeCompare", (2200, -2500), data_type="FLOAT", operation="LESS_THAN")
    b.L(gi_v, keep_i.inputs["A"])
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
    # Trim To Face: a staggered row gets ONE extra slot (no wrap) so its cut
    # end boards sit at both face edges
    sh_pos = b.N("FunctionNodeCompare", (2350, -2700), data_type="FLOAT", operation="GREATER_THAN")
    b.L(sh_m.outputs["Value"], sh_pos.inputs["A"])
    sh_pos.inputs["B"].default_value = 1e-4
    sh_xtra = b.N("FunctionNodeBooleanMath", (2500, -2700), operation="AND")
    b.L(trim_on, sh_xtra.inputs[0]); b.L(sh_pos.outputs["Result"], sh_xtra.inputs[1])
    ns_k = b.N("ShaderNodeMath", (2650, -2700), operation="ADD")
    b.L(ns_v, ns_k.inputs[0]); b.L(sh_xtra.outputs["Boolean"], ns_k.inputs[1])
    b.L(ns_k.outputs["Value"], keep_i.inputs["B"])
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
    # ---- TRIM TO FACE: every tile is sized to its cell and CUT to the face.
    # v2.10 (floorboards): length = slot spacing; slot k of a row is centred at
    # alo + (k + 0.5 - shift) * sp; u jitter is dropped (it would open seams).
    # v2.11 (lap siding, shakes): height = row spacing / (1 - Row Overlap), so
    # courses lap; the tile is clipped to the face's bottom and top (no shake
    # rises past the ridge, the eave course ends flush) and its length to the
    # face OUTLINE across its whole height (gable triangles: boards follow the
    # rake; exact for convex faces - triangles and quads).
    def tm(op, a, b_=None, c_=None):
        n = b.N("ShaderNodeMath", random_loc(), operation=op)
        for i_, x_ in enumerate((a, b_, c_)):
            if x_ is None:
                continue
            if isinstance(x_, (int, float)):
                n.inputs[i_].default_value = x_
            else:
                b.L(x_, n.inputs[i_])
        return n.outputs["Value"]

    def tcmp(op, a, b_):
        n = b.N("FunctionNodeCompare", random_loc(), data_type="FLOAT", operation=op)
        b.L(a, n.inputs["A"])
        if isinstance(b_, (int, float)):
            n.inputs["B"].default_value = b_
        else:
            b.L(b_, n.inputs["B"])
        return n.outputs["Result"]

    def tsw(cond, if_false, if_true):
        n = b.N("GeometryNodeSwitch", random_loc())
        n.input_type = "FLOAT"
        b.L(cond, n.inputs["Switch"])
        for key, x_ in (("False", if_false), ("True", if_true)):
            if isinstance(x_, (int, float)):
                n.inputs[key].default_value = x_
            else:
                b.L(x_, n.inputs[key])
        return n.outputs["Output"]

    def tand(a, b_):
        n = b.N("FunctionNodeBooleanMath", random_loc(), operation="AND")
        b.L(a, n.inputs[0]); b.L(b_, n.inputs[1])
        return n.outputs["Boolean"]

    ca = [named(f"vm_ca{k}") for k in range(4)]
    cb = [named(f"vm_cb{k}") for k in range(4)]

    def outline_span(b0):
        """[lo, hi] of the face outline along u at height b0 (local units)."""
        los, his = [], []
        for k in range(4):
            k2 = (k + 1) % 4
            d_ = tm("SUBTRACT", cb[k2], cb[k])
            straddle = tcmp("LESS_EQUAL", tm("MULTIPLY", tm("SUBTRACT", cb[k], b0),
                                             tm("SUBTRACT", cb[k2], b0)), 0.0)
            sloped = tcmp("GREATER_THAN", tm("ABSOLUTE", d_), 1e-6)
            valid = tand(straddle, sloped)
            f_ = tm("DIVIDE", tm("SUBTRACT", b0, cb[k]), tsw(sloped, 1.0, d_))
            a_ = tm("MULTIPLY_ADD", f_, tm("SUBTRACT", ca[k2], ca[k]), ca[k])
            los.append(tsw(valid, 1e6, a_))
            his.append(tsw(valid, -1e6, a_))
        while len(los) > 1:
            los = [tm("MINIMUM", los[i], los[i + 1]) for i in range(0, len(los), 2)]
            his = [tm("MAXIMUM", his[i], his[i + 1]) for i in range(0, len(his), 2)]
        return los[0], his[0]

    # height: the row centre +- half the lapped tile, clipped to the face
    k_lap = tm("DIVIDE", 1.0, tm("MAXIMUM", tm("SUBTRACT", 1.0, gi.outputs["Row Overlap"]), 0.05))
    t_hz = tm("MULTIPLY", tm("MULTIPLY", sp_h.outputs["Value"], 0.5), k_lap)
    t_bot = tm("MAXIMUM", tm("SUBTRACT", bhalf.outputs["Value"], t_hz), tm("ADD", blo_v, 1e-4))
    t_top = tm("MINIMUM", tm("ADD", bhalf.outputs["Value"], t_hz),
               tm("SUBTRACT", tm("ADD", blo_v, h_v), 1e-4))
    t_b = tm("MULTIPLY", tm("ADD", t_bot, t_top), 0.5)
    t_hgt = tm("SUBTRACT", t_top, t_bot)
    # length: the slot, clipped to the outline at the tile's bottom AND top
    lo1, hi1 = outline_span(t_bot)
    lo2, hi2 = outline_span(t_top)
    t_c = tm("MULTIPLY_ADD", tm("SUBTRACT", tm("ADD", gi_v, 0.5), sh_m.outputs["Value"]),
             sp_w.outputs["Value"], alo_v)
    t_half = tm("MULTIPLY", sp_w.outputs["Value"], 0.5)
    t_lo = tm("MAXIMUM", tm("SUBTRACT", t_c, t_half), tm("MAXIMUM", lo1, lo2))
    t_hi = tm("MINIMUM", tm("ADD", t_c, t_half), tm("MINIMUM", hi1, hi2))
    t_a = tm("MULTIPLY", tm("ADD", t_lo, t_hi), 0.5)
    t_len = tm("SUBTRACT", t_hi, t_lo)
    a_use = tsw(trim_on, a_fin.outputs["Value"], t_a)
    b_use = tsw(trim_on, b_fin.outputs["Value"], t_b)
    # slivers (< 2 cm long or < 1 cm high in WORLD meters) are dropped
    ev_pts = named("vm_ev")
    trim_ok = tand(tcmp("GREATER_THAN", tm("MULTIPLY", t_len, eu_pts), 0.02),
                   tcmp("GREATER_THAN", tm("MULTIPLY", t_hgt, ev_pts), 0.01))
    trim_keep = b.N("FunctionNodeBooleanMath", random_loc(), operation="IMPLY")
    b.L(trim_on, trim_keep.inputs[0]); b.L(trim_ok, trim_keep.inputs[1])
    # tile size from the Primary Props bounds (the variants share one nominal size)
    t_ci = b.N("GeometryNodeCollectionInfo", (3450, -4100))
    b.L(gi.outputs["Primary Props"], t_ci.inputs["Collection"])
    t_ci.inputs["Separate Children"].default_value = True
    t_ci.inputs["Reset Children"].default_value = True
    t_real = b.N("GeometryNodeRealizeInstances", (3600, -4100))
    b.L(t_ci.outputs["Instances"], t_real.inputs["Geometry"])
    t_bb = b.N("GeometryNodeBoundBox", (3750, -4100))
    b.L(t_real.outputs["Geometry"], t_bb.inputs["Geometry"])
    t_ext = b.N("ShaderNodeVectorMath", (3900, -4100), operation="SUBTRACT")
    b.L(t_bb.outputs["Max"], t_ext.inputs[0]); b.L(t_bb.outputs["Min"], t_ext.inputs[1])
    t_exs = b.N("ShaderNodeSeparateXYZ", (4050, -4100))
    b.L(t_ext.outputs["Vector"], t_exs.inputs["Vector"])
    t_lx = tm("MAXIMUM", t_exs.outputs["X"], 0.001)
    t_lz = tm("MAXIMUM", t_exs.outputs["Z"], 0.001)
    # world tile scale: X = cut length / tile length, Z = cut height / tile height
    t_xs = tm("DIVIDE", tm("MULTIPLY", t_len, eu_pts), t_lx)
    t_zs = tm("DIVIDE", tm("MULTIPLY", t_hgt, ev_pts), t_lz)
    st_tx = b.N("GeometryNodeStoreNamedAttribute", (3450, -2200), data_type="FLOAT", domain="POINT")
    b.L(real.outputs["Geometry"], st_tx.inputs["Geometry"])
    st_tx.inputs["Name"].default_value = "vm_tx"
    b.L(t_xs, st_tx.inputs["Value"])
    st_tz = b.N("GeometryNodeStoreNamedAttribute", (3600, -2200), data_type="FLOAT", domain="POINT")
    b.L(st_tx.outputs["Geometry"], st_tz.inputs["Geometry"])
    st_tz.inputs["Name"].default_value = "vm_tz"
    b.L(t_zs, st_tz.inputs["Value"])
    u_fin = b.N("ShaderNodeVectorMath", (3950, -3450), operation="SCALE")
    b.L(u_v, u_fin.inputs[0])
    b.L(a_use, u_fin.inputs["Scale"])
    v_fin = b.N("ShaderNodeVectorMath", (3950, -3520), operation="SCALE")
    b.L(v_v, v_fin.inputs[0])
    b.L(b_use, v_fin.inputs["Scale"])
    p_sum1 = b.N("ShaderNodeVectorMath", (4100, -3485), operation="ADD")
    b.L(u_fin.outputs["Vector"], p_sum1.inputs[0])
    b.L(v_fin.outputs["Vector"], p_sum1.inputs[1])
    p_sum3 = b.N("ShaderNodeVectorMath", (4250, -3485), operation="ADD")
    b.L(c_v, p_sum3.inputs[0])
    b.L(p_sum1.outputs["Vector"], p_sum3.inputs[1])
    # v2.13: a tile end CUT at the face outline (a wall corner, the rake) sits
    # under trim - it counts as nailed for the Damage support rule. Its local
    # position is stored (far away when the end is not cut).
    pe_chain = st_tz.outputs["Geometry"]
    for nm_, a_end, cut_ in (
            ("vm_pe_lo", t_lo, tcmp("GREATER_THAN", t_lo, tm("ADD", tm("SUBTRACT", t_c, t_half), 1e-4))),
            ("vm_pe_hi", t_hi, tcmp("LESS_THAN", t_hi, tm("SUBTRACT", tm("ADD", t_c, t_half), 1e-4)))):
        pe_u = b.N("ShaderNodeVectorMath", random_loc(), operation="SCALE")
        b.L(u_v, pe_u.inputs[0]); b.L(a_end, pe_u.inputs["Scale"])
        pe_s = b.N("ShaderNodeVectorMath", random_loc(), operation="ADD")
        b.L(pe_u.outputs["Vector"], pe_s.inputs[0]); b.L(v_fin.outputs["Vector"], pe_s.inputs[1])
        pe_p = b.N("ShaderNodeVectorMath", random_loc(), operation="ADD")
        b.L(c_v, pe_p.inputs[0]); b.L(pe_s.outputs["Vector"], pe_p.inputs[1])
        pe_sw = b.N("GeometryNodeSwitch", random_loc())
        pe_sw.input_type = "VECTOR"
        b.L(tand(trim_on, cut_), pe_sw.inputs["Switch"])
        pe_sw.inputs["False"].default_value = (1e6, 1e6, 1e6)
        b.L(pe_p.outputs["Vector"], pe_sw.inputs["True"])
        st_pe = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT_VECTOR",
                    domain="POINT")
        b.L(pe_chain, st_pe.inputs["Geometry"])
        st_pe.inputs["Name"].default_value = nm_
        b.L(pe_sw.outputs["Output"], st_pe.inputs["Value"])
        pe_chain = st_pe.outputs["Geometry"]
    setpos_c = b.N("GeometryNodeSetPosition", (3750, -2200))
    b.L(pe_chain, setpos_c.inputs["Geometry"])
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
    keep_c1 = b.N("FunctionNodeBooleanMath", (3700, -3000), operation="AND")
    b.L(keep_ij.outputs["Boolean"], keep_c1.inputs[0])
    b.L(trim_keep.outputs["Boolean"], keep_c1.inputs[1])
    b.L(keep_c1.outputs["Boolean"], keep_c2.inputs[0])
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
    # v2.22: ... except on a dormer front - it stands on the roof, above the
    # eave, and cannot share wall space with a door in the wall below it
    occ_dfa = b.N("GeometryNodeInputNamedAttribute", (2050, -3200))
    occ_dfa.data_type = "FLOAT"
    occ_dfa.inputs["Name"].default_value = "vm_dfront"
    occ_df = b.N("FunctionNodeCompare", (2200, -3200), data_type="FLOAT", operation="GREATER_THAN")
    b.L(occ_dfa.outputs["Attribute"], occ_df.inputs["A"])
    occ_df.inputs["B"].default_value = 0.5
    occ_far2 = b.N("FunctionNodeBooleanMath", (2300, -3250), operation="OR")
    b.L(occ_far.outputs["Result"], occ_far2.inputs[0])
    b.L(occ_df.outputs["Result"], occ_far2.inputs[1])
    b.L(occ_far2.outputs["Boolean"], occ_ok.inputs[1])
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
    # v2.22: dormer fronts are exempt here too (see occ_df above)
    so_dfa = b.N("GeometryNodeInputNamedAttribute", (5850, -3350))
    so_dfa.data_type = "FLOAT"
    so_dfa.inputs["Name"].default_value = "vm_dfront"
    so_df = b.N("FunctionNodeCompare", (6000, -3350), data_type="FLOAT", operation="GREATER_THAN")
    b.L(so_dfa.outputs["Attribute"], so_df.inputs["A"])
    so_df.inputs["B"].default_value = 0.5
    so_far2 = b.N("FunctionNodeBooleanMath", (6000, -3450), operation="OR")
    b.L(so_far.outputs["Result"], so_far2.inputs[0])
    b.L(so_df.outputs["Result"], so_far2.inputs[1])
    b.L(so_far2.outputs["Boolean"], so_ok.inputs[1])
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
    # v2.22: Fit openings stand UP too - Align Y alone turns +Y onto a normal
    # like (0, -1, -0.0001) (a dormer front) by a 180 deg roll about X, and the
    # window hung upside down below its sill (same fix as v2.11 cladding)
    align_fz = b.N("FunctionNodeAlignRotationToVector", (1100, 800))
    align_fz.axis = "Z"
    align_fz.pivot_axis = "Y"
    b.L(align_y.outputs["Rotation"], align_fz.inputs["Rotation"])
    align_fz.inputs["Vector"].default_value = (0.0, 0.0, 1.0)
    align_fz.inputs["Factor"].default_value = 1.0
    b.L(align_fz.outputs["Rotation"], fit_rot.inputs["Rotation"])
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
    # v2.11: cladding tiles also turn about the normal so local Z points UP the
    # face (up the wall / up the roof slope) on EVERY face - Align Y alone left
    # Z pointing downhill on half the roof slopes, so a tapered tile (thick
    # bottom edge: lap siding, shakes) lay upside down there. Flat faces (floor)
    # have no 'up' in their plane and keep the Align Y result.
    align_zu = b.N("FunctionNodeAlignRotationToVector", (1100, 900))
    align_zu.axis = "Z"
    align_zu.pivot_axis = "Y"
    b.L(align_y.outputs["Rotation"], align_zu.inputs["Rotation"])
    align_zu.inputs["Vector"].default_value = (0.0, 0.0, 1.0)
    align_zu.inputs["Factor"].default_value = 1.0
    b.L(align_zu.outputs["Rotation"], rot_sw2.inputs["True"])
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
    # v2.10 Trim To Face: length/width come from the stored cell size
    def trim_axis(name, normal_sock, loc):
        rd = b.N("GeometryNodeInputNamedAttribute", (loc[0] - 150, loc[1]))
        rd.data_type = "FLOAT"
        rd.inputs["Name"].default_value = name
        sw = b.N("GeometryNodeSwitch", loc)
        sw.input_type = "FLOAT"
        b.L(trim_on, sw.inputs["Switch"])
        b.L(normal_sock, sw.inputs["False"])
        b.L(rd.outputs["Attribute"], sw.inputs["True"])
        return sw.outputs["Output"]
    scale_c = b.N("ShaderNodeCombineXYZ", (1650, 60))
    b.L(trim_axis("vm_tx", sxs.outputs["Value"], (1500, -250)), scale_c.inputs["X"])
    b.L(rv_scale.outputs["Value"], scale_c.inputs["Y"])
    b.L(trim_axis("vm_tz", sz.outputs["Value"], (1500, -350)), scale_c.inputs["Z"])
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
    # v2.22 nothing is laid INSIDE a dormer (VM_RoofCap): the roof's shakes
    # under it are dropped - the host's dormer points carry each dormer's
    # frame (front sill centre, out, across, half width, heights)
    dm_pts = b.N("GeometryNodeSeparateGeometry", (2250, 500), domain="POINT")
    b.L(mesh_only, dm_pts.inputs["Geometry"])
    dm_k_rd = b.N("GeometryNodeInputNamedAttribute", (2050, 500))
    dm_k_rd.data_type = "FLOAT_VECTOR"
    dm_k_rd.inputs["Name"].default_value = "vm_dmk"
    dm_k_sep = b.N("ShaderNodeSeparateXYZ", (2100, 450))
    b.L(dm_k_rd.outputs["Attribute"], dm_k_sep.inputs["Vector"])
    dm_k_on = b.N("FunctionNodeCompare", (2150, 450), data_type="FLOAT", operation="GREATER_THAN")
    b.L(dm_k_sep.outputs["X"], dm_k_on.inputs["A"])
    dm_k_on.inputs["B"].default_value = 1e-4
    b.L(dm_k_on.outputs["Result"], dm_pts.inputs["Selection"])
    dm_pt = dm_pts.outputs["Selection"]
    # (Sample Nearest needs a target; an empty one reads index 0 -> no dormer
    # data -> half width 0 -> nothing is inside)
    dm_near = b.N("GeometryNodeSampleNearest", (2400, 500), domain="POINT")
    b.L(dm_pt, dm_near.inputs["Geometry"])
    dm_ipos = b.N("GeometryNodeInputPosition", (2250, 650))
    b.L(dm_ipos.outputs["Position"], dm_near.inputs["Sample Position"])

    def dm_get(name_):
        rd_ = b.N("GeometryNodeInputNamedAttribute", (2400, 650))
        rd_.data_type = "FLOAT_VECTOR"
        rd_.inputs["Name"].default_value = name_
        si_ = b.N("GeometryNodeSampleIndex", (2550, 650), data_type="FLOAT_VECTOR", domain="POINT")
        b.L(dm_pt, si_.inputs["Geometry"])
        b.L(rd_.outputs["Attribute"], si_.inputs["Value"])
        b.L(dm_near.outputs["Index"], si_.inputs["Index"])
        return si_.outputs["Value"]

    def dm_v(op_, a_, b_, out_="Vector"):
        n_ = b.N("ShaderNodeVectorMath", (2700, 650), operation=op_)
        b.L(a_, n_.inputs[0]); b.L(b_, n_.inputs[1])
        return n_.outputs[out_]

    def dm_m(op_, a_, b_):
        n_ = b.N("ShaderNodeMath", (2700, 700), operation=op_)
        for i_, x_ in enumerate((a_, b_)):
            if isinstance(x_, (int, float)):
                n_.inputs[i_].default_value = x_
            else:
                b.L(x_, n_.inputs[i_])
        return n_.outputs["Value"]

    def dm_c(op_, a_, b_):
        n_ = b.N("FunctionNodeCompare", (2700, 750), data_type="FLOAT", operation=op_)
        b.L(a_, n_.inputs["A"])
        if isinstance(b_, (int, float)):
            n_.inputs["B"].default_value = b_
        else:
            b.L(b_, n_.inputs["B"])
        return n_.outputs["Result"]

    def dm_and(a_, b_):
        n_ = b.N("FunctionNodeBooleanMath", (2700, 800), operation="AND")
        b.L(a_, n_.inputs[0]); b.L(b_, n_.inputs[1])
        return n_.outputs["Boolean"]
    dm_rel = dm_v("SUBTRACT", dm_ipos.outputs["Position"], dm_get("vm_dmo"))
    dm_a = dm_m("ABSOLUTE", dm_v("DOT_PRODUCT", dm_rel, dm_get("vm_dmu"), "Value"), 0.0)
    dm_d = dm_m("MULTIPLY", dm_v("DOT_PRODUCT", dm_rel, dm_get("vm_dmn"), "Value"), -1.0)
    dm_rs = b.N("ShaderNodeSeparateXYZ", (2700, 850))
    b.L(dm_rel, dm_rs.inputs["Vector"])
    dm_ks = b.N("ShaderNodeSeparateXYZ", (2700, 900))
    b.L(dm_get("vm_dmk"), dm_ks.inputs["Vector"])
    dm_zs = b.N("ShaderNodeSeparateXYZ", (2700, 950))
    b.L(dm_get("vm_dmz"), dm_zs.inputs["Vector"])
    dm_hw = dm_ks.outputs["X"]
    # the roof's underside over the point: eave + (1 - |a| / half width) * ridge rise
    dm_roof = dm_m("ADD", dm_zs.outputs["X"],
                   dm_m("MULTIPLY", dm_zs.outputs["Y"],
                        dm_m("SUBTRACT", 1.0, dm_m("DIVIDE", dm_a, dm_m("MAXIMUM", dm_hw, 1e-4)))))
    dm_in = dm_and(dm_and(dm_c("GREATER_THAN", dm_hw, 1e-4), dm_c("GREATER_THAN", dm_d, 0.05)),
                   dm_and(dm_and(dm_c("LESS_THAN", dm_a, dm_m("SUBTRACT", dm_hw, 0.1)),
                                 dm_c("GREATER_THAN", dm_rs.outputs["Z"], -0.1)),
                          dm_c("LESS_THAN", dm_rs.outputs["Z"], dm_m("SUBTRACT", dm_roof, 0.02))))
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
    # (after every per-index store, so dropping some shifts nothing)
    dm_del = b.N("GeometryNodeDeleteGeometry", (3150, 300), domain="INSTANCE")
    b.L(store_an.outputs["Geometry"], dm_del.inputs["Geometry"])
    b.L(dm_in, dm_del.inputs["Selection"])

    join_all = b.N("GeometryNodeJoinGeometry", (2650, 100))
    b.L(base_out, join_all.inputs["Geometry"])
    b.L(dm_del.outputs["Geometry"], join_all.inputs["Geometry"])
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
    # v2.10: created after every older socket so their identifiers never shift
    b.sock("Trim To Face", "NodeSocketBool", p_pl, False,
           desc="Cladding (v2.10): size every tile to exactly its cell (length = slot spacing, "
                "width = row spacing) and CUT tiles at the face edges - for floorboards. Off = "
                "wall behaviour (tiles keep their size and overlap past corners)")
    b.L(gi.outputs["Trim To Face"], trim_in.inputs[0])

    # ---- v2.11 EDGE BOARDS (corner boards / ridge caps): a board profile laid
    # along every CONVEX edge whose two faces are both in this layer's Face Zone
    # - the outside corners of the walls (corner boards that cover the siding
    # ends) and the ridge + hip lines of the roof (ridge cap over the shakes).
    # The profile is an L whose legs open to the edge's own angle (90 deg wall
    # corner, 110 deg ridge at 35 deg pitch), set out from the faces by Edge
    # Board Offset so it sits ON the cladding. Realized mesh with UVs along the
    # edge (meters) -> the tile wood material works on it.
    b.sock("Edge Boards", "NodeSocketBool", p_pl, False,
           desc="Cladding (v2.11): boards along the zone's convex edges - corner boards on "
                "wall corners, a ridge cap on roof ridges and hips")
    b.sock("Edge Board Width", "NodeSocketFloat", p_pl, 0.1, 0.0, 2.0, "DISTANCE",
           "Edge Boards: width of each leg (world meters)")
    b.sock("Edge Board Thickness", "NodeSocketFloat", p_pl, 0.025, 0.0, 1.0, "DISTANCE",
           "Edge Boards: board thickness (world meters)")
    b.sock("Edge Board Offset", "NodeSocketFloat", p_pl, 0.024, -1.0, 1.0, "DISTANCE",
           "Edge Boards: how far the boards stand off the faces - the cladding thickness")
    b.sock("Edge Board Material", "NodeSocketMaterial", p_pl, None,
           desc="Edge Boards: material (empty = none assigned)")

    def em(op, a_, b_=None, loc=(5200, -6000)):
        n_ = b.N("ShaderNodeMath", loc, operation=op)
        for i_, x_ in enumerate((a_, b_)):
            if x_ is None:
                continue
            if isinstance(x_, (int, float)):
                n_.inputs[i_].default_value = x_
            else:
                b.L(x_, n_.inputs[i_])
        return n_.outputs["Value"]

    ew, et, eo = (gi.outputs["Edge Board Width"], gi.outputs["Edge Board Thickness"],
                  gi.outputs["Edge Board Offset"])
    # edge data materialized on the EDGE domain (store context), then one point
    # per selected edge carries it (Mesh to Points / Edges)
    st_ez = b.N("GeometryNodeStoreNamedAttribute", (4600, -5800), data_type="FLOAT", domain="FACE")
    b.L(mesh_only, st_ez.inputs["Geometry"])
    st_ez.inputs["Name"].default_value = "vm_ez"
    b.L(zone_sel, st_ez.inputs["Value"])
    ev_n = b.N("GeometryNodeInputMeshEdgeVertices", (4600, -6100))
    e_ang = b.N("GeometryNodeInputMeshEdgeAngle", (4600, -6250))
    e_nrm = b.N("GeometryNodeInputNormal", (4600, -6400))
    e_chain = st_ez.outputs["Geometry"]
    for k_, (nm_, dt_, src_) in enumerate((("vm_ep1", "FLOAT_VECTOR", ev_n.outputs["Position 1"]),
                                            ("vm_ep2", "FLOAT_VECTOR", ev_n.outputs["Position 2"]),
                                            ("vm_eang", "FLOAT", e_ang.outputs["Unsigned Angle"]),
                                            ("vm_enrm", "FLOAT_VECTOR", e_nrm.outputs["Normal"]))):
        st_ = b.N("GeometryNodeStoreNamedAttribute", (4800 + 150 * k_, -5800), data_type=dt_,
                  domain="EDGE")
        b.L(e_chain, st_.inputs["Geometry"])
        st_.inputs["Name"].default_value = nm_
        b.L(src_, st_.inputs["Value"])
        e_chain = st_.outputs["Geometry"]
    ez_rd = b.N("GeometryNodeInputNamedAttribute", (4800, -6100))
    ez_rd.data_type = "FLOAT"
    ez_rd.inputs["Name"].default_value = "vm_ez"
    e_nb = b.N("GeometryNodeInputMeshEdgeNeighbors", (4800, -6250))
    e_both = b.N("FunctionNodeCompare", (4950, -6100), data_type="FLOAT", operation="GREATER_EQUAL")
    b.L(ez_rd.outputs["Attribute"], e_both.inputs["A"])
    e_both.inputs["B"].default_value = 0.999
    e_two = b.N("FunctionNodeCompare", (4950, -6250), data_type="INT", operation="EQUAL")
    b.L(e_nb.outputs["Face Count"], e_two.inputs["A"])
    e_two.inputs["B"].default_value = 2
    e_cvx = b.N("FunctionNodeCompare", (4950, -6400), data_type="FLOAT", operation="GREATER_THAN")
    b.L(e_ang.outputs["Signed Angle"], e_cvx.inputs["A"])
    e_cvx.inputs["B"].default_value = 0.17          # ~10 deg: real corners, not split coplanar faces
    e_s1 = b.N("FunctionNodeBooleanMath", (5100, -6150), operation="AND")
    b.L(e_both.outputs["Result"], e_s1.inputs[0]); b.L(e_two.outputs["Result"], e_s1.inputs[1])
    e_s2 = b.N("FunctionNodeBooleanMath", (5250, -6200), operation="AND")
    b.L(e_s1.outputs["Boolean"], e_s2.inputs[0]); b.L(e_cvx.outputs["Result"], e_s2.inputs[1])
    e_on = b.N("FunctionNodeBooleanMath", (5250, -6000), operation="AND")
    b.L(gi.outputs["Edge Boards"], e_on.inputs[0]); b.L(is_clad, e_on.inputs[1])
    e_s3 = b.N("FunctionNodeBooleanMath", (5400, -6200), operation="AND")
    b.L(e_s2.outputs["Boolean"], e_s3.inputs[0]); b.L(e_on.outputs["Boolean"], e_s3.inputs[1])
    e_pts = b.N("GeometryNodeMeshToPoints", (5550, -5800))
    e_pts.mode = "EDGES"
    b.L(e_chain, e_pts.inputs["Mesh"])
    b.L(e_s3.outputs["Boolean"], e_pts.inputs["Selection"])

    def e_named(name, dt="FLOAT_VECTOR"):
        n_ = b.N("GeometryNodeInputNamedAttribute", (5550, -6100))
        n_.data_type = dt
        n_.inputs["Name"].default_value = name
        return n_.outputs["Attribute"]
    ep1, ep2, enrm = e_named("vm_ep1"), e_named("vm_ep2"), e_named("vm_enrm")
    eang = e_named("vm_eang", "FLOAT")
    e_dir = b.N("ShaderNodeVectorMath", (5700, -6100), operation="SUBTRACT")
    b.L(ep2, e_dir.inputs[0]); b.L(ep1, e_dir.inputs[1])
    e_len = b.N("ShaderNodeVectorMath", (5850, -6100), operation="LENGTH")
    b.L(e_dir.outputs["Vector"], e_len.inputs[0])
    # unit L profile (length 1 along +Z), legs along the two faces of a 90 deg
    # corner, bisector -> +Y after the 45 deg turn
    e_st = em("ADD", eo, et)                                    # s + t
    e_full = em("ADD", e_st, ew)                                # w + s + t
    # v2.23 three blocks that only TOUCH (overlapping boxes shaded black where
    # one's face lay inside the other - the dark X on a ridge cap's end), each
    # solid down to the faces (no hollow under the legs seen end-on at a
    # gable): leg A on face x=0, leg B on face y=0, the corner block between
    e_hw = em("MULTIPLY", ew, -0.5)                             # -w/2
    e_hs = em("MULTIPLY", e_st, 0.5)                            # (s + t)/2
    legs = []
    for sx_, sy_, tx_, ty_ in ((e_st, ew, e_hs, e_hw), (ew, e_st, e_hw, e_hs), (e_st, e_st, e_hs, e_hs)):
        cs = b.N("ShaderNodeCombineXYZ", (5400, -6600))
        b.L(sx_, cs.inputs["X"]); b.L(sy_, cs.inputs["Y"]); cs.inputs["Z"].default_value = 1.0
        cube = b.N("GeometryNodeMeshCube", (5550, -6600))
        b.L(cs.outputs["Vector"], cube.inputs["Size"])
        ct = b.N("ShaderNodeCombineXYZ", (5400, -6750))
        b.L(tx_, ct.inputs["X"]); b.L(ty_, ct.inputs["Y"]); ct.inputs["Z"].default_value = 0.5
        tr = b.N("GeometryNodeTransform", (5700, -6600))
        b.L(cube.outputs["Mesh"], tr.inputs["Geometry"])
        b.L(ct.outputs["Vector"], tr.inputs["Translation"])
        legs.append(tr.outputs["Geometry"])
    e_lj = b.N("GeometryNodeJoinGeometry", (5850, -6600))
    for lg in legs:
        b.L(lg, e_lj.inputs["Geometry"])
    e_rot45 = b.N("GeometryNodeTransform", (6000, -6600))
    b.L(e_lj.outputs["Geometry"], e_rot45.inputs["Geometry"])
    e_rot45.inputs["Rotation"].default_value = (0.0, 0.0, math.radians(45.0))
    # rotation: Z along the edge, Y (bisector) along the edge's outward normal
    e_az = b.N("FunctionNodeAlignRotationToVector", (6000, -6100))
    e_az.axis = "Z"
    b.L(e_dir.outputs["Vector"], e_az.inputs["Vector"])
    e_ay = b.N("FunctionNodeAlignRotationToVector", (6150, -6100))
    e_ay.axis = "Y"
    e_ay.pivot_axis = "Z"
    b.L(e_az.outputs["Rotation"], e_ay.inputs["Rotation"])
    b.L(enrm, e_ay.inputs["Vector"])
    # legs open to the edge angle: X scale = cot(angle between the face normals / 2)
    e_f = em("MINIMUM", em("MAXIMUM", em("DIVIDE", 1.0, em("MAXIMUM", em("TANGENT", em(
        "MULTIPLY", eang, 0.5)), 0.05)), 0.3), 3.0)
    e_sc = b.N("ShaderNodeCombineXYZ", (6150, -6250))
    b.L(e_f, e_sc.inputs["X"]); e_sc.inputs["Y"].default_value = 1.0
    b.L(e_len.outputs["Value"], e_sc.inputs["Z"])
    e_sp = b.N("GeometryNodeSetPosition", (6150, -5800))      # points onto vertex 1
    b.L(e_pts.outputs["Points"], e_sp.inputs["Geometry"])
    b.L(ep1, e_sp.inputs["Position"])
    e_iop = b.N("GeometryNodeInstanceOnPoints", (6300, -5800))
    b.L(e_sp.outputs["Geometry"], e_iop.inputs["Points"])
    b.L(e_rot45.outputs["Geometry"], e_iop.inputs["Instance"])
    b.L(e_ay.outputs["Rotation"], e_iop.inputs["Rotation"])
    b.L(e_sc.outputs["Vector"], e_iop.inputs["Scale"])
    e_dn = b.N("ShaderNodeVectorMath", (6300, -6100), operation="NORMALIZE")
    b.L(e_dir.outputs["Vector"], e_dn.inputs[0])
    st_ed = b.N("GeometryNodeStoreNamedAttribute", (6450, -5800), data_type="FLOAT_VECTOR",
                domain="INSTANCE")
    b.L(e_iop.outputs["Instances"], st_ed.inputs["Geometry"])
    st_ed.inputs["Name"].default_value = "vm_edir"
    b.L(e_dn.outputs["Vector"], st_ed.inputs["Value"])
    e_real = b.N("GeometryNodeRealizeInstances", (6600, -5800))
    b.L(st_ed.outputs["Geometry"], e_real.inputs["Geometry"])
    # UVs: U = meters along the edge (wood grain), V = across the leg
    e_pos = b.N("GeometryNodeInputPosition", (6600, -6100))
    e_rel = b.N("ShaderNodeVectorMath", (6750, -6100), operation="SUBTRACT")
    b.L(e_pos.outputs["Position"], e_rel.inputs[0]); b.L(ep1, e_rel.inputs[1])
    e_u = b.N("ShaderNodeVectorMath", (6900, -6100), operation="DOT_PRODUCT")
    b.L(e_rel.outputs["Vector"], e_u.inputs[0]); b.L(e_named("vm_edir"), e_u.inputs[1])
    e_side = b.N("ShaderNodeVectorMath", (6750, -6250), operation="CROSS_PRODUCT")
    b.L(e_named("vm_edir"), e_side.inputs[0]); b.L(enrm, e_side.inputs[1])
    e_v0 = b.N("ShaderNodeVectorMath", (6900, -6250), operation="DOT_PRODUCT")
    b.L(e_rel.outputs["Vector"], e_v0.inputs[0]); b.L(e_side.outputs["Vector"], e_v0.inputs[1])
    e_v = em("DIVIDE", em("ABSOLUTE", e_v0.outputs["Value"]), em("MAXIMUM", e_full, 0.01))
    e_uv = b.N("ShaderNodeCombineXYZ", (7050, -6150))
    b.L(e_u.outputs["Value"], e_uv.inputs["X"]); b.L(e_v, e_uv.inputs["Y"])
    st_uv = b.N("GeometryNodeStoreNamedAttribute", (6750, -5800), data_type="FLOAT2",
                domain="CORNER")
    b.L(e_real.outputs["Geometry"], st_uv.inputs["Geometry"])
    st_uv.inputs["Name"].default_value = "UVMap"
    b.L(e_uv.outputs["Vector"], st_uv.inputs["Value"])
    e_mat = b.N("GeometryNodeSetMaterial", (6900, -5800))
    b.L(st_uv.outputs["Geometry"], e_mat.inputs["Geometry"])
    b.L(gi.outputs["Edge Board Material"], e_mat.inputs["Material"])
    st_trim = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT", domain="FACE")
    b.L(e_mat.outputs["Geometry"], st_trim.inputs["Geometry"])
    st_trim.inputs["Name"].default_value = "vm_trim"
    st_trim.inputs["Value"].default_value = 1.0
    b.L(st_trim.outputs["Geometry"], join_all.inputs["Geometry"])

    # ---- v2.12 DAMAGE (movable weathering of the cladding tiles). A noise field
    # (patch size Damage Scale) plus a per-tile random picks the damaged tiles;
    # Damage Amount sets how many, and a Damage Object + Damage Radius confines
    # them to a fading patch around that object - move the object and the
    # damage moves. Inside a patch the SEVERITY decides each tile's fate: the
    # centre goes MISSING (the dark underlay shows through like a hole), around
    # it tiles are BROKEN (shortened from one end - a shake loses its butt) and
    # at the edge they hang LOOSE (swung out from the top nail line; long
    # boards also slip on one nail). Only Cladding layers; openings never.
    p_dmg = b.panel("Damage", "Cladding (v2.12): missing, broken and loose boards / shakes - "
                              "drive it with a Damage Object to move it over the building")
    b.sock("Damage", "NodeSocketBool", p_dmg, False,
           desc="Cladding (v2.12): damage the tiles - missing, broken and loose boards / shakes")
    b.sock("Damage Amount", "NodeSocketFloat", p_dmg, 0.25, 0.0, 1.0, "FACTOR",
           "How much of the cladding is damaged (inside the Damage Radius when a radius is set)")
    b.sock("Damage Object", "NodeSocketObject", p_dmg, None,
           desc="Centre of the damage patch (an Empty - move it to move the damage). Used when "
                "Damage Radius > 0")
    b.sock("Damage Radius", "NodeSocketFloat", p_dmg, 0.0, 0.0, 1000.0, "DISTANCE",
           "Damage fades out to zero at this distance from the Damage Object (world meters). "
           "0 = damage over the whole building")
    b.sock("Damage Scale", "NodeSocketFloat", p_dmg, 1.2, 0.05, 100.0, "DISTANCE",
           "Size of the damage patches (world meters)")
    b.sock("Damage Seed", "NodeSocketInt", p_dmg, 0, desc="Reshuffle the damage pattern")
    b.sock("Missing Share", "NodeSocketFloat", p_dmg, 0.35, 0.0, 1.0, "FACTOR",
           "Share of the damaged tiles that are MISSING (the worst-hit ones)")
    b.sock("Broken Share", "NodeSocketFloat", p_dmg, 0.3, 0.0, 1.0, "FACTOR",
           "Share of the damaged tiles that are BROKEN (shortened); the rest hang loose")
    b.sock("Max Tilt", "NodeSocketFloat", p_dmg, math.radians(12.0), 0.0, math.radians(90.0), "ANGLE",
           "Loose tiles: largest angle - a shake curls out from its top edge, a long board "
           "hangs from the nail at one end")

    # v2.13: REAL damaged geometry + no floating pieces
    b.sock("Broken Props", "NodeSocketCollection", p_dmg, None,
           desc="Damage (v2.13): broken pieces - nailed end at the origin, 1 m long along +X "
                "(name _L) / -X (_R) for boards, down -Z for shakes. Empty = the tile is just cut short")
    b.sock("Worn Props", "NodeSocketCollection", p_dmg, None,
           desc="Damage (v2.13): full-size worn tiles (split, chipped, bitten) used in the Wear "
                "band around the damage. Empty = no wear")
    b.sock("Wear", "NodeSocketFloat", p_dmg, 0.12, 0.0, 1.0, "FACTOR",
           "How far beyond the damage the tiles are worn (cracked, split, chipped)")
    # v2.21 sockets are created LAST (identifier order); placeholders here
    rh_ph = b.N("ShaderNodeMath", random_loc(), operation="ADD")
    rh_ph.inputs[1].default_value = 0.0
    hb_ph = b.N("ShaderNodeMath", random_loc(), operation="ADD")
    hb_ph.inputs[1].default_value = 0.0

    d_pos = b.N("GeometryNodeInputPosition", (3200, 600))
    d_idx = b.N("GeometryNodeInputIndex", (3200, 500))
    d_seed = gi.outputs["Damage Seed"]
    d_sv = b.N("ShaderNodeVectorMath", (3350, 700), operation="SCALE")
    d_sv.inputs[0].default_value = (17.31, 9.73, 5.11)
    b.L(d_seed, d_sv.inputs["Scale"])
    d_nv = b.N("ShaderNodeVectorMath", (3500, 650), operation="ADD")
    b.L(d_pos.outputs["Position"], d_nv.inputs[0]); b.L(d_sv.outputs["Vector"], d_nv.inputs[1])
    d_noise = b.N("ShaderNodeTexNoise", (3650, 650))
    b.L(d_nv.outputs["Vector"], d_noise.inputs["Vector"])
    b.L(em("DIVIDE", geo_f, em("MAXIMUM", gi.outputs["Damage Scale"], 0.01)), d_noise.inputs["Scale"])
    d_noise.inputs["Detail"].default_value = 2.0

    def d_rand(off):
        rv = b.N("FunctionNodeRandomValue", (3650, 450), data_type="FLOAT_VECTOR")
        rv.inputs["Min"].default_value = (0.0, 0.0, 0.0)
        rv.inputs["Max"].default_value = (1.0, 1.0, 1.0)
        b.L(d_idx.outputs["Index"], rv.inputs["ID"])
        b.L(seed_node(b, d_seed, off), rv.inputs["Seed"])
        sp_ = b.N("ShaderNodeSeparateXYZ", (3800, 450))
        b.L(rv.outputs["Value"], sp_.inputs["Vector"])
        return rv.outputs["Value"], sp_.outputs
    _, r_a = d_rand(101)
    r_b_vec, _ = d_rand(211)
    # score: patch noise (contrast-stretched) + a per-tile share for ragged edges
    d_ns = em("MINIMUM", em("MAXIMUM", tm("MULTIPLY_ADD", em("SUBTRACT", d_noise.outputs["Fac"], 0.5),
                                          2.5, 0.5), 0.0), 1.0)
    d_score = tm("MULTIPLY_ADD", d_ns, 0.65, em("MULTIPLY", r_a["X"], 0.35))
    # mask: 1 everywhere (radius 0) or a smooth fade around the Damage Object
    d_oi = b.N("GeometryNodeObjectInfo", (3350, 900))
    d_oi.transform_space = "RELATIVE"
    b.L(gi.outputs["Damage Object"], d_oi.inputs["Object"])
    d_dv = b.N("ShaderNodeVectorMath", (3500, 900), operation="DISTANCE")
    b.L(d_pos.outputs["Position"], d_dv.inputs[0]); b.L(d_oi.outputs["Location"], d_dv.inputs[1])
    d_rl = em("DIVIDE", gi.outputs["Damage Radius"], geo_f)
    d_mr = b.N("ShaderNodeMapRange", (3650, 900), interpolation_type="SMOOTHSTEP")
    b.L(d_dv.outputs["Value"], d_mr.inputs["Value"])
    b.L(d_rl, d_mr.inputs["From Min"])
    b.L(em("MULTIPLY", d_rl, 0.3), d_mr.inputs["From Max"])
    d_mask = tsw(tcmp("GREATER_THAN", gi.outputs["Damage Radius"], 0.0), 1.0, d_mr.outputs["Result"])
    d_thr = em("SUBTRACT", 1.0, em("MULTIPLY", gi.outputs["Damage Amount"], d_mask))
    def dmg_margin(vec_):
        nv_ = vmath("ADD", vec_, d_sv.outputs["Vector"])
        nz_ = b.N("ShaderNodeTexNoise", random_loc())
        b.L(nv_, nz_.inputs["Vector"])
        b.L(em("DIVIDE", geo_f, em("MAXIMUM", gi.outputs["Damage Scale"], 0.01)), nz_.inputs["Scale"])
        nz_.inputs["Detail"].default_value = 2.0
        ns_ = em("MINIMUM", em("MAXIMUM", tm("MULTIPLY_ADD", em("SUBTRACT", nz_.outputs["Fac"], 0.5),
                                             2.5, 0.5), 0.0), 1.0)
        dv_ = vmath("DISTANCE", vec_, d_oi.outputs["Location"], out="Value")
        mr_ = b.N("ShaderNodeMapRange", random_loc(), interpolation_type="SMOOTHSTEP")
        b.L(dv_, mr_.inputs["Value"])
        b.L(d_rl, mr_.inputs["From Min"])
        b.L(em("MULTIPLY", d_rl, 0.3), mr_.inputs["From Max"])
        mk_ = tsw(tcmp("GREATER_THAN", gi.outputs["Damage Radius"], 0.0), 1.0, mr_.outputs["Result"])
        thr_ = em("SUBTRACT", 1.0, em("MULTIPLY", gi.outputs["Damage Amount"], mk_))
        # the tiles' per-tile random share averages 0.5 on a ring of samples
        return em("SUBTRACT", tm("MULTIPLY_ADD", ns_, 0.65, 0.175), thr_)


    def calm_pts(geo_):
        # v2.20 keep only the points well outside the damage (a trim / outline
        # end there still holds a board; inside a patch it may be gone)
        dl_ = b.N("GeometryNodeDeleteGeometry", random_loc(), domain="POINT")
        b.L(geo_, dl_.inputs["Geometry"])
        b.L(tcmp("GREATER_THAN", dmg_margin(b.N("GeometryNodeInputPosition", random_loc()).outputs["Position"]), -0.1),
            dl_.inputs["Selection"])
        return dl_.outputs["Geometry"]
    d_live = tand(gi.outputs["Damage"], is_clad)
    d_on = tand(d_live, tcmp("GREATER_THAN", d_score, d_thr))
    # v2.13 the wear band: just short of the damage threshold (inside the mask)
    d_worn = tand(tand(d_live, tcmp("GREATER_THAN", d_mask, 0.001)),
                  tcmp("GREATER_THAN", d_score, em("SUBTRACT", d_thr, gi.outputs["Wear"])))
    # severity: how far past the threshold (saturating 0.3 deep - the heart of a
    # patch) plus a small per-tile random, so the categories mix at their borders
    d_sev = tm("MULTIPLY_ADD", em("MINIMUM", em("DIVIDE", em("SUBTRACT", d_score, d_thr), 0.3), 1.0),
               0.8, em("MULTIPLY", r_a["Y"], 0.2))
    d_lim_m = em("SUBTRACT", 1.0, gi.outputs["Missing Share"])
    d_lim_b = em("SUBTRACT", d_lim_m, gi.outputs["Broken Share"])
    # category: 0 intact, 1 missing, 2 broken, 3 loose, 4 worn
    d_cat = tsw(d_on, tsw(d_worn, 0.0, 4.0), tsw(tcmp("GREATER_EQUAL", d_sev, d_lim_m), tsw(
        tcmp("GREATER_EQUAL", d_sev, d_lim_b), 3.0, 2.0), 1.0))
    # the tile frame from the Primary Props bounds: long tiles (siding) break and
    # hang along X; tall tiles (shakes) break from the butt (bottom)
    bb_mn = b.N("ShaderNodeSeparateXYZ", (3650, -300))
    b.L(t_bb.outputs["Min"], bb_mn.inputs["Vector"])
    bb_mx = b.N("ShaderNodeSeparateXYZ", (3650, -450))
    b.L(t_bb.outputs["Max"], bb_mx.inputs["Vector"])
    d_long = tcmp("GREATER_THAN", t_exs.outputs["X"], t_exs.outputs["Z"])

    def v3(x, y, z):
        n_ = b.N("ShaderNodeCombineXYZ", random_loc())
        for k_, val in zip("XYZ", (x, y, z)):
            if isinstance(val, (int, float)):
                n_.inputs[k_].default_value = val
            else:
                b.L(val, n_.inputs[k_])
        return n_.outputs["Vector"]

    def vsw(cond, if_false, if_true):
        n_ = b.N("GeometryNodeSwitch", random_loc())
        n_.input_type = "VECTOR"
        b.L(cond, n_.inputs["Switch"])
        b.L(if_false, n_.inputs["False"]); b.L(if_true, n_.inputs["True"])
        return n_.outputs["Output"]

    def vmath(op, a_, b_, out="Vector"):
        n_ = b.N("ShaderNodeVectorMath", random_loc(), operation=op)
        b.L(a_, n_.inputs[0])
        sk_ = n_.inputs["Scale"] if op == "SCALE" else n_.inputs[1]
        if b_ is None:                                 # a one-operand op
            pass
        elif isinstance(b_, (int, float)):             # a constant scale
            sk_.default_value = b_
        else:
            b.L(b_, sk_)
        return n_.outputs[out]

    def dnamed(name, dt):
        n_ = b.N("GeometryNodeInputNamedAttribute", random_loc())
        n_.data_type = dt
        n_.inputs["Name"].default_value = name
        return n_.outputs["Attribute"]
    i_rot = b.N("GeometryNodeInputInstanceRotation", (3200, 300)).outputs["Rotation"]
    i_scl = b.N("GeometryNodeInputInstanceScale", (3200, 250)).outputs["Scale"]
    i_scs = b.N("ShaderNodeSeparateXYZ", (3350, 250))
    b.L(i_scl, i_scs.inputs["Vector"])

    def end_pos(x_local):
        rv_ = b.N("FunctionNodeRotateVector", random_loc())
        b.L(v3(em("MULTIPLY", x_local, i_scs.outputs["X"]), 0.0, 0.0), rv_.inputs["Vector"])
        b.L(i_rot, rv_.inputs["Rotation"])
        return vmath("ADD", d_pos.outputs["Position"], rv_.outputs["Vector"])
    # pass 1: category, randoms, both ends and the placement (store context -
    # the fields below run after Deletes / conversions where indices shift)
    stores1 = [("vm_dcat0", "FLOAT", d_cat), ("vm_drnd", "FLOAT_VECTOR", r_b_vec),
               ("vm_elo", "FLOAT_VECTOR", end_pos(bb_mn.outputs["X"])),
               ("vm_ehi", "FLOAT_VECTOR", end_pos(bb_mx.outputs["X"])),
               ("vm_irot", "QUATERNION", i_rot), ("vm_iscl", "FLOAT_VECTOR", i_scl)]
    for lk in list(b.ng.links):
        if lk.from_node == dm_del and lk.to_node == join_all:
            b.ng.links.remove(lk)
    d_chain = dm_del.outputs["Geometry"]
    for nm_, dt_, val_ in stores1:
        st_ = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type=dt_, domain="INSTANCE")
        b.L(d_chain, st_.inputs["Geometry"])
        st_.inputs["Name"].default_value = nm_
        b.L(val_, st_.inputs["Value"])
        d_chain = st_.outputs["Geometry"]
    cat0 = dnamed("vm_dcat0", "FLOAT")
    dr_s = b.N("ShaderNodeSeparateXYZ", (3650, -100))
    b.L(dnamed("vm_drnd", "FLOAT_VECTOR"), dr_s.inputs["Vector"])

    def is_c(cat_sock, k):
        return tcmp("EQUAL", cat_sock, float(k))

    def bor(a_, b_):
        n_ = b.N("FunctionNodeBooleanMath", random_loc(), operation="OR")
        b.L(a_, n_.inputs[0]); b.L(b_, n_.inputs[1])
        return n_.outputs["Boolean"]

    def bnot(a_):
        n_ = b.N("FunctionNodeBooleanMath", random_loc(), operation="NOT")
        b.L(a_, n_.inputs[0])
        return n_.outputs["Boolean"]

    # ---- v2.23 RAKE BOARDS (the user's 'above the windows the planks don't
    # cover all of the wall'): a course is cut to the outline's narrower width
    # (at its bottom or its top), so along a SLOPED edge of a wall - a gable's
    # rake, a dormer front's, a dormer cheek on the roof - the courses step and
    # leave triangles of bare wall. With Edge Boards on, a flat board lies on
    # the siding along every sloped edge where the zone's wall ends, RAKE_W
    # wide (it covers the steps of a course up to ~0.2 m high).
    def sxyz(v_):
        n_ = b.N("ShaderNodeSeparateXYZ", random_loc())
        b.L(v_, n_.inputs["Vector"])
        return n_.outputs["X"], n_.outputs["Y"], n_.outputs["Z"]
    r_n = b.N("GeometryNodeInputNormal", random_loc()).outputs["Normal"]
    r_chain = st_ez.outputs["Geometry"]
    for nm_, val_ in (("vm_rkzn", vsw(zone_sel, v3(0.0, 0.0, 0.0), r_n)),
                      ("vm_rkzc", vsw(zone_sel, v3(0.0, 0.0, 0.0),
                                     b.N("GeometryNodeInputPosition", random_loc()).outputs["Position"]))):
        st_ = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT_VECTOR", domain="FACE")
        b.L(r_chain, st_.inputs["Geometry"])
        st_.inputs["Name"].default_value = nm_
        b.L(val_, st_.inputs["Value"])
        r_chain = st_.outputs["Geometry"]
    r_ez = dnamed("vm_ez", "FLOAT")
    r_den = em("MAXIMUM", r_ez, 0.01)
    for nm_, val_ in (("vm_rkn", vmath("SCALE", dnamed("vm_rkzn", "FLOAT_VECTOR"), em("DIVIDE", 1.0, r_den))),
                      ("vm_rkc", vmath("SCALE", dnamed("vm_rkzc", "FLOAT_VECTOR"), em("DIVIDE", 1.0, r_den))),
                      ("vm_ep1", ev_n.outputs["Position 1"]), ("vm_ep2", ev_n.outputs["Position 2"])):
        st_ = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT_VECTOR", domain="EDGE")
        b.L(r_chain, st_.inputs["Geometry"])
        st_.inputs["Name"].default_value = nm_
        b.L(val_, st_.inputs["Value"])
        r_chain = st_.outputs["Geometry"]
    r_d = vmath("SUBTRACT", ev_n.outputs["Position 2"], ev_n.outputs["Position 1"])
    r_dz = em("DIVIDE", em("ABSOLUTE", sxyz(r_d)[2]), em("MAXIMUM", vmath("LENGTH", r_d, None, out="Value"), 1e-6))
    r_one = bor(tand(tcmp("GREATER_THAN", r_ez, 0.25), tcmp("LESS_THAN", r_ez, 0.75)),
                tand(tcmp("GREATER_THAN", r_ez, 0.99), tcmp("LESS_THAN", e_nb.outputs["Face Count"], 1.5)))
    r_sel = tand(tand(e_on.outputs["Boolean"], r_one),
                 tand(tand(tcmp("GREATER_THAN", r_dz, 0.12), tcmp("LESS_THAN", r_dz, 0.985)),
                      tcmp("LESS_THAN", em("ABSOLUTE", sxyz(dnamed("vm_rkn", "FLOAT_VECTOR"))[2]), 0.35)))
    r_pts = b.N("GeometryNodeMeshToPoints", random_loc())
    r_pts.mode = "EDGES"
    b.L(r_chain, r_pts.inputs["Mesh"])
    rp1, rp2 = dnamed("vm_ep1", "FLOAT_VECTOR"), dnamed("vm_ep2", "FLOAT_VECTOR")
    rn_ = vmath("NORMALIZE", dnamed("vm_rkn", "FLOAT_VECTOR"), None)
    rd_ = vmath("SUBTRACT", rp2, rp1)
    rdn = vmath("NORMALIZE", rd_, None)
    r_mid = vmath("SCALE", vmath("ADD", rp1, rp2), 0.5)
    # across the board, in the wall, INTO the wall face (towards its centre)
    r_x = vmath("NORMALIZE", vmath("CROSS_PRODUCT", rn_, rdn), None)
    r_in = tcmp("GREATER_THAN", vmath("DOT_PRODUCT", r_x, vmath("SUBTRACT", dnamed("vm_rkc", "FLOAT_VECTOR"), r_mid),
                                      out="Value"), 0.0)
    r_p = vmath("SCALE", r_x, tsw(r_in, -1.0, 1.0))
    # ... a real wall: not the thin end strip of a roof slab (a gable's barge
    # strip is wall-like too, its centre half a Roof Thickness off its edge)
    r_far = tcmp("GREATER_THAN", em("MULTIPLY", em("ABSOLUTE", vmath(
        "DOT_PRODUCT", r_x, vmath("SUBTRACT", dnamed("vm_rkc", "FLOAT_VECTOR"), r_mid), out="Value")), geo_f), 0.12)
    b.L(tand(r_sel, r_far), r_pts.inputs["Selection"])
    r_w = em("DIVIDE", RAKE_W, geo_f)
    # the two rakes of a gable overlap at the apex: one lies a hair proud
    r_up = tcmp("GREATER_THAN", vmath("DOT_PRODUCT", r_p, vmath("CROSS_PRODUCT", rn_, v3(0.0, 0.0, 1.0)), out="Value"), 0.0)
    r_off = em("ADD", em("ADD", eo, em("MULTIPLY", et, 0.5)), tsw(r_up, 0.0, 0.003))
    r_c = vmath("ADD", r_mid, vmath("ADD", vmath("SCALE", r_p, em("MULTIPLY", r_w, 0.5)), vmath("SCALE", rn_, r_off)))
    r_ax = b.N("FunctionNodeAlignRotationToVector", random_loc())
    r_ax.axis = "X"
    b.L(rdn, r_ax.inputs["Vector"])
    r_az = b.N("FunctionNodeAlignRotationToVector", random_loc())
    r_az.axis = "Z"; r_az.pivot_axis = "X"
    b.L(r_ax.outputs["Rotation"], r_az.inputs["Rotation"])
    b.L(rn_, r_az.inputs["Vector"])
    r_chain2 = r_pts.outputs["Points"]
    rk_hi = tcmp("GREATER_THAN", sxyz(rp2)[2], sxyz(rp1)[2])
    rk_t = vsw(rk_hi, rp1, rp2)
    rk_du = vmath("NORMALIZE", vmath("SUBTRACT", rk_t, vsw(rk_hi, rp2, rp1)), None)
    rk_hz = vmath("NORMALIZE", vmath("CROSS_PRODUCT", rn_, v3(0.0, 0.0, 1.0)), None)
    rk_hd = vmath("SCALE", rk_hz, tsw(tcmp("GREATER_THAN", vmath("DOT_PRODUCT", rk_hz, rk_du, out="Value"), 0.0), -1.0, 1.0))
    for nm_, val_ in (("vm_rkd", rdn), ("vm_rka", r_p), ("vm_rkm", rn_),
                      ("vm_rkt", rk_t), ("vm_rku", rk_du), ("vm_rkh", rk_hd)):
        st_ = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT_VECTOR", domain="POINT")
        b.L(r_chain2, st_.inputs["Geometry"])
        st_.inputs["Name"].default_value = nm_
        b.L(val_, st_.inputs["Value"])
        r_chain2 = st_.outputs["Geometry"]
    r_rot_st = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="QUATERNION", domain="POINT")
    b.L(r_chain2, r_rot_st.inputs["Geometry"])
    r_rot_st.inputs["Name"].default_value = "vm_rkr"
    b.L(r_az.outputs["Rotation"], r_rot_st.inputs["Value"])
    r_sz_st = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT_VECTOR", domain="POINT")
    b.L(r_rot_st.outputs["Geometry"], r_sz_st.inputs["Geometry"])
    r_sz_st.inputs["Name"].default_value = "vm_rks"
    b.L(v3(vmath("LENGTH", rd_, None, out="Value"), r_w, et), r_sz_st.inputs["Value"])
    r_mv = b.N("GeometryNodeSetPosition", random_loc())
    b.L(r_sz_st.outputs["Geometry"], r_mv.inputs["Geometry"])
    b.L(r_c, r_mv.inputs["Position"])
    r_cube = b.N("GeometryNodeMeshCube", random_loc())
    r_cube.inputs["Size"].default_value = (1.0, 1.0, 1.0)
    r_iop = b.N("GeometryNodeInstanceOnPoints", random_loc())
    b.L(r_mv.outputs["Geometry"], r_iop.inputs["Points"])
    b.L(r_cube.outputs["Mesh"], r_iop.inputs["Instance"])
    b.L(dnamed("vm_rkr", "QUATERNION"), r_iop.inputs["Rotation"])
    b.L(dnamed("vm_rks", "FLOAT_VECTOR"), r_iop.inputs["Scale"])
    r_real0 = b.N("GeometryNodeRealizeInstances", random_loc())
    b.L(r_iop.outputs["Instances"], r_real0.inputs["Geometry"])
    # the upper end is cut PLUMB (a gable's two rakes meet in a vertical
    # joint at the apex, not overlapping): a corner past the vertical plane
    # through the edge's top slides back along the board onto it
    rk_top = dnamed("vm_rkt", "FLOAT_VECTOR")
    rk_dup, rk_h = dnamed("vm_rku", "FLOAT_VECTOR"), dnamed("vm_rkh", "FLOAT_VECTOR")
    rk_rp = b.N("GeometryNodeInputPosition", random_loc()).outputs["Position"]
    rk_s = em("MAXIMUM", vmath("DOT_PRODUCT", vmath("SUBTRACT", rk_rp, rk_top), rk_h, out="Value"), 0.0)
    rk_mv = b.N("GeometryNodeSetPosition", random_loc())
    b.L(r_real0.outputs["Geometry"], rk_mv.inputs["Geometry"])
    b.L(vmath("SCALE", rk_dup, em("DIVIDE", em("MULTIPLY", rk_s, -1.0),
                                  em("MAXIMUM", vmath("DOT_PRODUCT", rk_dup, rk_h, out="Value"), 0.05))),
        rk_mv.inputs["Offset"])
    r_real = rk_mv
    r_pp = b.N("GeometryNodeInputPosition", random_loc()).outputs["Position"]
    r_uv = v3(em("MULTIPLY", vmath("DOT_PRODUCT", r_pp, dnamed("vm_rkd", "FLOAT_VECTOR"), out="Value"), geo_f),
              em("MULTIPLY", em("ADD", vmath("DOT_PRODUCT", r_pp, dnamed("vm_rka", "FLOAT_VECTOR"), out="Value"),
                                vmath("DOT_PRODUCT", r_pp, dnamed("vm_rkm", "FLOAT_VECTOR"), out="Value")), geo_f), 0.0)
    r_uvs = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT2", domain="CORNER")
    b.L(r_real.outputs["Geometry"], r_uvs.inputs["Geometry"])
    r_uvs.inputs["Name"].default_value = "UVMap"
    b.L(r_uv, r_uvs.inputs["Value"])
    r_mat = b.N("GeometryNodeSetMaterial", random_loc())
    b.L(r_uvs.outputs["Geometry"], r_mat.inputs["Geometry"])
    b.L(gi.outputs["Edge Board Material"], r_mat.inputs["Material"])
    r_tr = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT", domain="FACE")
    b.L(r_mat.outputs["Geometry"], r_tr.inputs["Geometry"])
    r_tr.inputs["Name"].default_value = "vm_trim"
    r_tr.inputs["Value"].default_value = 1.0
    b.L(r_tr.outputs["Geometry"], join_all.inputs["Geometry"])
    # ---- v2.20 NO LONE BOARDS (the user's 'the boards ARE the wall - where
    # they are gone you see inside, and no single plank may float'). The
    # cutting layer now opens the wall wherever a board is gone, so a board
    # left alone in a hole would hang in the air: a long board in the damage
    # that keeps fewer than two of its four neighbours (the course above, the
    # course below, the board at either end - intact or worn) falls out too.
    # Run twice: a pair that only held each other goes as well.
    def d_rotv(vec_, rot_):
        rv_ = b.N("FunctionNodeRotateVector", random_loc())
        b.L(vec_, rv_.inputs["Vector"]); b.L(rot_, rv_.inputs["Rotation"])
        return rv_.outputs["Vector"]
    d_upv = d_rotv(v3(0.0, 0.0, 1.0), i_rot)
    d_pitch = em("MULTIPLY", em("MULTIPLY", t_exs.outputs["Z"], i_scs.outputs["Z"]),
                 em("SUBTRACT", 1.0, gi.outputs["Row Overlap"]))

    def iso_pass(chain_):
        hold_ = bor(is_c(cat0, 0), is_c(cat0, 4))
        elo_, ehi_ = dnamed("vm_elo", "FLOAT_VECTOR"), dnamed("vm_ehi", "FLOAT_VECTOR")
        # the holding boards as 17 points each along their length
        p_ = b.N("GeometryNodeInstancesToPoints", random_loc())
        b.L(chain_, p_.inputs["Instances"])
        b.L(tand(hold_, d_long), p_.inputs["Selection"])
        du_ = b.N("GeometryNodeDuplicateElements", random_loc(), domain="POINT")
        b.L(p_.outputs["Points"], du_.inputs["Geometry"])
        du_.inputs["Amount"].default_value = 17
        sp_ = b.N("GeometryNodeSetPosition", random_loc())
        b.L(du_.outputs["Geometry"], sp_.inputs["Geometry"])
        b.L(vmath("ADD", elo_, vmath("SCALE", vmath("SUBTRACT", ehi_, elo_),
                                     em("DIVIDE", du_.outputs["Duplicate Index"], 16.0))), sp_.inputs["Position"])
        ds_ = b.N("GeometryNodeAttributeDomainSize", random_loc())
        ds_.component = "POINTCLOUD"
        b.L(p_.outputs["Points"], ds_.inputs["Geometry"])
        ok_ = tcmp("GREATER_THAN", ds_.outputs["Point Count"], 0.5)

        def hit_(cloud_, pos_, dist_):
            px_ = b.N("GeometryNodeProximity", random_loc())
            px_.target_element = "POINTS"
            b.L(cloud_, px_.inputs["Geometry"])
            b.L(pos_, px_.inputs["Sample Position"])
            return tcmp("LESS_THAN", px_.outputs["Distance"], dist_)
        # a course above / below: three points over the board one pitch up /
        # down land on a holding board (own course is a whole pitch away)
        th_ = em("MULTIPLY", d_pitch, 0.6)
        n_ = None
        for s_ in (1.0, -1.0):
            row_ = None
            for f_ in (0.15, 0.5, 0.85):
                at_ = vmath("ADD", vmath("ADD", elo_, vmath("SCALE", vmath("SUBTRACT", ehi_, elo_), f_)),
                            vmath("SCALE", d_upv, em("MULTIPLY", d_pitch, s_)))
                x_ = tand(ok_, hit_(sp_.outputs["Geometry"], at_, th_))
                row_ = x_ if row_ is None else bor(row_, x_)
            v_ = tsw(row_, 0.0, 1.0)
            n_ = v_ if n_ is None else em("ADD", n_, v_)
        # the end neighbours: a holding board's opposite end, or the face
        # outline (a corner / rake end sits under trim)
        for mine_, theirs_ in (("vm_elo", "vm_ehi"), ("vm_ehi", "vm_elo")):
            j_ = b.N("GeometryNodeJoinGeometry", random_loc())
            for sel_, attr_ in ((hold_, theirs_), (None, "vm_pe_lo"), (None, "vm_pe_hi")):
                i2p_ = b.N("GeometryNodeInstancesToPoints", random_loc())
                b.L(chain_, i2p_.inputs["Instances"])
                if sel_ is not None:
                    b.L(sel_, i2p_.inputs["Selection"])
                b.L(dnamed(attr_, "FLOAT_VECTOR"), i2p_.inputs["Position"])
                b.L(i2p_.outputs["Points"] if sel_ is not None else calm_pts(i2p_.outputs["Points"]),
                    j_.inputs["Geometry"])
            n_ = em("ADD", n_, tsw(hit_(j_.outputs["Geometry"], dnamed(mine_, "FLOAT_VECTOR"),
                                        em("DIVIDE", 0.04, geo_f)), 0.0, 1.0))
        iso_ = tand(tand(tand(d_live, d_long), hold_),
                    tand(tcmp("GREATER_THAN", d_mask, 0.001), tcmp("LESS_THAN", n_, 1.5)))
        st_ = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT", domain="INSTANCE")
        b.L(chain_, st_.inputs["Geometry"])
        st_.inputs["Name"].default_value = "vm_dcat0"
        b.L(tsw(iso_, cat0, 1.0), st_.inputs["Value"])
        return st_.outputs["Geometry"]
    d_chain = iso_pass(iso_pass(d_chain))

    # pass 2: SUPPORT + HOLE EDGES. Tiles on one face share their X direction, so
    # a tile's min-X end meets its row neighbour's max-X end: each end is tested
    # against the OPPOSITE ends of the other tiles (never its own).
    # - a broken / hanging board keeps an end that meets an intact or worn
    #   board's end or an outline-cut end; with none it falls off (missing);
    # - v2.14 an intact / worn board end is COVERED when it meets an intact /
    #   worn board's end, the outline, or the end a broken / hanging board
    #   kept. One end uncovered: the board breaks there (the jagged end faces
    #   the hole, it keeps the covered end). Both uncovered: it falls out;
    # - v2.14 an intact board whose top edge is bared by a hole above, and a
    #   shake next to a hole, wears (split / chipped / bitten).
    # Shakes hang under the course above: no support rule.
    def end_cloud(sel_, attr_, extra=()):
        parts = []
        for sel_k, attr_k in ((sel_, attr_),) + tuple(extra):
            i2p = b.N("GeometryNodeInstancesToPoints", random_loc())
            b.L(d_chain, i2p.inputs["Instances"])
            if sel_k is not None:
                b.L(sel_k, i2p.inputs["Selection"])
            sp_ = b.N("GeometryNodeSetPosition", random_loc())
            b.L(i2p.outputs["Points"], sp_.inputs["Geometry"])
            b.L(dnamed(attr_k, "FLOAT_VECTOR"), sp_.inputs["Position"])
            parts.append(calm_pts(sp_.outputs["Geometry"]) if attr_k.startswith("vm_pe_") else sp_.outputs["Geometry"])
        j_ = b.N("GeometryNodeJoinGeometry", random_loc())
        for g_ in parts:
            b.L(g_, j_.inputs["Geometry"])
        return j_.outputs["Geometry"]

    def near(cloud, pos_, dist_):
        px_ = b.N("GeometryNodeProximity", random_loc())
        px_.target_element = "POINTS"
        b.L(cloud, px_.inputs["Geometry"])
        b.L(pos_, px_.inputs["Sample Position"])
        return tcmp("LESS_THAN", px_.outputs["Distance"], em("DIVIDE", dist_, geo_f))
    # v2.20 an end cut at the outline is held by the trim there - but not
    # inside a damaged patch, where that corner board may be gone with the
    # wall (judged at the outline end itself, not at the board offering it)
    outline_ends = (None, "vm_pe_lo"), (None, "vm_pe_hi")
    holds = bor(is_c(cat0, 0), is_c(cat0, 4))                 # intact or worn
    sup_lo = near(end_cloud(holds, "vm_ehi", outline_ends), dnamed("vm_elo", "FLOAT_VECTOR"), 0.04)
    sup_hi = near(end_cloud(holds, "vm_elo", outline_ends), dnamed("vm_ehi", "FLOAT_VECTOR"), 0.04)
    d_hang = tand(d_long, bor(is_c(cat0, 2), is_c(cat0, 3)))
    # kept end: 1 = the max-X end, 0 = the min-X end. A hanging board keeps a
    # supported end (stored first: the cover test below needs its position)
    side_r = tsw(tcmp("LESS_THAN", dr_s.outputs["Y"], 0.5), 1.0, 0.0)
    side_h = tsw(tand(sup_lo, sup_hi), tsw(sup_hi, 0.0, 1.0), side_r)
    st_ = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT_VECTOR",
              domain="INSTANCE")
    b.L(d_chain, st_.inputs["Geometry"])
    st_.inputs["Name"].default_value = "vm_ekept"
    b.L(vsw(tcmp("GREATER_THAN", side_h, 0.5), dnamed("vm_elo", "FLOAT_VECTOR"),
            dnamed("vm_ehi", "FLOAT_VECTOR")), st_.inputs["Value"])
    d_chain = st_.outputs["Geometry"]
    kept_end = (d_hang, "vm_ekept"),
    cov_lo = near(end_cloud(holds, "vm_ehi", outline_ends + kept_end), dnamed("vm_elo", "FLOAT_VECTOR"), 0.04)
    cov_hi = near(end_cloud(holds, "vm_elo", outline_ends + kept_end), dnamed("vm_ehi", "FLOAT_VECTOR"), 0.04)

    # points along the tiles of a category set (9 per tile, end to end) + a
    # guard: Proximity to an EMPTY cloud reads distance 0, so an empty cloud
    # must never count as 'near' (Damage off / no gaps -> no rule fires)
    def span_cloud(sel_, n_pts=9):
        p_ = b.N("GeometryNodeInstancesToPoints", random_loc())
        b.L(d_chain, p_.inputs["Instances"])
        b.L(sel_, p_.inputs["Selection"])
        d_ = b.N("GeometryNodeDuplicateElements", random_loc(), domain="POINT")
        b.L(p_.outputs["Points"], d_.inputs["Geometry"])
        d_.inputs["Amount"].default_value = n_pts
        t_ = b.N("ShaderNodeVectorMath", random_loc(), operation="SCALE")
        b.L(vmath("SUBTRACT", dnamed("vm_ehi", "FLOAT_VECTOR"), dnamed("vm_elo", "FLOAT_VECTOR")),
            t_.inputs[0])
        b.L(em("DIVIDE", d_.outputs["Duplicate Index"], float(n_pts - 1)), t_.inputs["Scale"])
        sp_ = b.N("GeometryNodeSetPosition", random_loc())
        b.L(d_.outputs["Geometry"], sp_.inputs["Geometry"])
        b.L(vmath("ADD", dnamed("vm_elo", "FLOAT_VECTOR"), t_.outputs["Vector"]), sp_.inputs["Position"])
        ds_ = b.N("GeometryNodeAttributeDomainSize", random_loc())
        ds_.component = "POINTCLOUD"
        b.L(p_.outputs["Points"], ds_.inputs["Geometry"])
        return sp_.outputs["Geometry"], tcmp("GREATER_THAN", ds_.outputs["Point Count"], 0.5)

    def near_any(cloud_ok, pos_, dist_):
        return tand(cloud_ok[1], near(cloud_ok[0], pos_, dist_))
    # an end is OPEN when nothing covers it and a gap (missing / broken /
    # hanging tile) starts right there - a plain end at the face edge is not
    gap_c = span_cloud(bnot(holds))
    open_lo = tand(bnot(cov_lo), near_any(gap_c, dnamed("vm_elo", "FLOAT_VECTOR"), 0.06))
    open_hi = tand(bnot(cov_hi), near_any(gap_c, dnamed("vm_ehi", "FLOAT_VECTOR"), 0.06))
    d_hold = tand(d_long, holds)
    d_edge = tand(d_hold, bor(open_lo, open_hi))
    d_lone = tand(d_edge, tand(open_lo, open_hi))
    cov_hi = bnot(open_hi)                                    # the end an edge break keeps
    # bared top / hole next door: points along every missing tile
    miss_c = span_cloud(is_c(cat0, 1))

    def top_pt(fx):
        rv_ = b.N("FunctionNodeRotateVector", random_loc())
        b.L(v3(em("MULTIPLY", em("MULTIPLY", bb_mx.outputs["X"], fx), i_scs.outputs["X"]), 0.0,
               em("MULTIPLY", bb_mx.outputs["Z"], i_scs.outputs["Z"])), rv_.inputs["Vector"])
        b.L(i_rot, rv_.inputs["Rotation"])
        return vmath("ADD", d_pos.outputs["Position"], rv_.outputs["Vector"])
    bared = bor(near_any(miss_c, top_pt(-0.6), 0.16),
                bor(near_any(miss_c, top_pt(0.0), 0.16), near_any(miss_c, top_pt(0.6), 0.16)))
    d_bare = tand(is_c(cat0, 0), tsw(d_long, near_any(miss_c, d_pos.outputs["Position"], 0.3), bared))
    d_side = tsw(d_long, side_r, tsw(d_edge, side_h, tsw(cov_hi, 0.0, 1.0)))
    # v2.21 a swinging board hangs from a nail under the course above: with
    # that course gone over its kept end (and no calm wall there - the top
    # course sits under the eaves) it would hang in the air, so it falls
    sw_k = dnamed("vm_ekept", "FLOAT_VECTOR")
    sw_far = vsw(tcmp("LESS_THAN", vmath("DISTANCE", sw_k, dnamed("vm_elo", "FLOAT_VECTOR"), out="Value"),
                      em("DIVIDE", 0.01, geo_f)),
                 dnamed("vm_elo", "FLOAT_VECTOR"), dnamed("vm_ehi", "FLOAT_VECTOR"))
    sw_hold = span_cloud(holds, 17)
    sw_tuck = None
    for f_ in (0.04, 0.12):
        at_ = vmath("ADD", vmath("ADD", sw_k, vmath("SCALE", vmath("SUBTRACT", sw_far, sw_k), f_)),
                    vmath("SCALE", d_upv, d_pitch))
        px_ = b.N("GeometryNodeProximity", random_loc())
        px_.target_element = "POINTS"
        b.L(sw_hold[0], px_.inputs["Geometry"])
        b.L(at_, px_.inputs["Sample Position"])
        x_ = bor(tand(sw_hold[1], tcmp("LESS_THAN", px_.outputs["Distance"], em("MULTIPLY", d_pitch, 0.6))),
                 tcmp("LESS_THAN", dmg_margin(at_), -0.1))
        sw_tuck = x_ if sw_tuck is None else bor(sw_tuck, x_)
    d_fall = bor(bor(tand(d_hang, bnot(bor(sup_lo, sup_hi))), d_lone),
                 tand(tand(d_long, is_c(cat0, 3)), bnot(sw_tuck)))
    d_cat2 = tsw(d_fall, tsw(d_edge, tsw(d_bare, cat0, 4.0), 2.0), 1.0)
    # remaining length of a broken tile: a hole-edge break loses only its end
    # (70-95 %), a broken tile in the damage anything from a stub to most of it
    d_frac = tsw(d_edge, tm("MULTIPLY_ADD", dr_s.outputs["X"], 0.7, 0.15),
                 tm("MULTIPLY_ADD", dr_s.outputs["X"], 0.25, 0.7))
    for nm_, val_ in (("vm_dcat", d_cat2), ("vm_dside", d_side), ("vm_dfrac", d_frac)):
        st_ = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT", domain="INSTANCE")
        b.L(d_chain, st_.inputs["Geometry"])
        st_.inputs["Name"].default_value = nm_
        b.L(val_, st_.inputs["Value"])
        d_chain = st_.outputs["Geometry"]
    cat = dnamed("vm_dcat", "FLOAT")
    side = dnamed("vm_dside", "FLOAT")
    side_hi = tcmp("GREATER_THAN", side, 0.5)
    d_end = tsw(side_hi, bb_mn.outputs["X"], bb_mx.outputs["X"])

    # ---- v2.20 GAP MARKERS: every wall board that is gone (missing, fallen) or
    # gone in part (broken short, hanging) leaves an invisible marker - an
    # instance of one loose vertex at the centre of the box its gap covers
    # (vm_kr its rotation, vm_ks its size: the board's footprint from 3 cm
    # behind the wall face to 5 cm in front). The cutting layer cuts those
    # boxes through the wall - the boards are the wall, there is nothing
    # behind them - and drops the markers. A broken board's gap starts 5 cm
    # under its jagged end; a hanging board keeps 15 cm round its nail.
    k_out = em("DIVIDE", 0.05, geo_f)
    k_dep = em("DIVIDE", 0.03, geo_f)
    k_n = d_rotv(v3(0.0, 1.0, 0.0), i_rot)
    k_nz = b.N("ShaderNodeSeparateXYZ", random_loc())
    b.L(k_n, k_nz.inputs["Vector"])
    k_sel = tand(tand(d_live, d_long), tand(tcmp("LESS_THAN", em("ABSOLUTE", k_nz.outputs["Z"]), 0.5),
                                            bor(is_c(cat, 1), bor(is_c(cat, 2), is_c(cat, 3)))))
    k_lo, k_hi = dnamed("vm_elo", "FLOAT_VECTOR"), dnamed("vm_ehi", "FLOAT_VECTOR")
    k_keep = vsw(side_hi, k_lo, k_hi)
    k_free = vsw(side_hi, k_hi, k_lo)
    k_len = em("MAXIMUM", vmath("DISTANCE", k_lo, k_hi, out="Value"), 1e-6)
    # (v2.21 a hanging board's gap opens its whole length: when the cutting
    # layer drops the board, no strip of wall may stay behind its nail end)
    k_kl = tsw(is_c(cat, 2), 0.0,
               em("SUBTRACT", em("MULTIPLY", dnamed("vm_dfrac", "FLOAT"), k_len), em("DIVIDE", 0.05, geo_f)))
    k_c = tsw(is_c(cat, 1), em("MINIMUM", em("DIVIDE", em("SUBTRACT", k_len, em("MAXIMUM", k_kl, 0.0)), k_len),
                               1.0), 1.0)
    k_zc = em("MULTIPLY", em("MULTIPLY", em("ADD", bb_mn.outputs["Z"], bb_mx.outputs["Z"]), 0.5), i_scs.outputs["Z"])
    k_ctr = vmath("ADD", vmath("ADD", k_free, vmath("SCALE", vmath("SUBTRACT", k_keep, k_free), em("MULTIPLY", k_c, 0.5))),
                  vmath("ADD", vmath("SCALE", d_upv, k_zc),
                        vmath("SCALE", k_n, em("MULTIPLY", em("SUBTRACT", k_out, k_dep), 0.5))))
    k_size = v3(em("ADD", em("MULTIPLY", k_len, k_c), em("DIVIDE", 0.02, geo_f)), em("ADD", k_out, k_dep),
                em("ADD", em("MULTIPLY", em("SUBTRACT", bb_mx.outputs["Z"], bb_mn.outputs["Z"]), i_scs.outputs["Z"]),
                   em("DIVIDE", 0.01, geo_f)))
    k_vert = b.N("GeometryNodeMeshLine", random_loc())
    k_vert.inputs["Count"].default_value = 1

    def gap_markers(pts_):
        # points carrying vm_kr / vm_ks -> marker instances (vm_cutph = 1)
        st_ = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT", domain="POINT")
        b.L(pts_, st_.inputs["Geometry"])
        st_.inputs["Name"].default_value = "vm_cutph"
        st_.inputs["Value"].default_value = 1.0
        iop_ = b.N("GeometryNodeInstanceOnPoints", random_loc())
        b.L(st_.outputs["Geometry"], iop_.inputs["Points"])
        b.L(k_vert.outputs["Mesh"], iop_.inputs["Instance"])
        b.L(dnamed("vm_kr", "QUATERNION"), iop_.inputs["Rotation"])
        b.L(iop_.outputs["Instances"], join_all.inputs["Geometry"])
    k_chain = d_chain
    for nm_, dt_, val_ in (("vm_kr", "QUATERNION", i_rot), ("vm_ks", "FLOAT_VECTOR", k_size)):
        st_ = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type=dt_, domain="INSTANCE")
        b.L(k_chain, st_.inputs["Geometry"])
        st_.inputs["Name"].default_value = nm_
        b.L(val_, st_.inputs["Value"])
        k_chain = st_.outputs["Geometry"]
    k_pts = b.N("GeometryNodeInstancesToPoints", random_loc())
    b.L(k_chain, k_pts.inputs["Instances"])
    b.L(k_sel, k_pts.inputs["Selection"])
    b.L(k_ctr, k_pts.inputs["Position"])
    gap_markers(k_pts.outputs["Points"])
    # v2.21 ROOF HOLES: a missing shake deep in the damage leaves a marker too
    # - its whole footprint, from 30 cm under the roof face (through the
    # deck) to just over it. vm_kroof flags it (the cutting layer puts the
    # rafters and battens under it) and vm_kb is the point on the deck under
    # the shake's centre
    rf_dep = em("DIVIDE", 0.3, geo_f)
    rf_cx = em("MULTIPLY", em("MULTIPLY", em("ADD", bb_mn.outputs["X"], bb_mx.outputs["X"]), 0.5), i_scs.outputs["X"])
    # (the box tops out a hair over the deck: the course above lies on the
    # missing shake's thickness and must not be cut)
    rf_h = em("MULTIPLY", em("SUBTRACT", bb_mx.outputs["Z"], bb_mn.outputs["Z"]), i_scs.outputs["Z"])
    rf_cz = em("MULTIPLY", em("MULTIPLY", em("ADD", bb_mn.outputs["Z"], bb_mx.outputs["Z"]), 0.5), i_scs.outputs["Z"])
    rf_out = em("DIVIDE", 0.006, geo_f)
    rf_kb = vmath("ADD", d_pos.outputs["Position"],
                  d_rotv(v3(rf_cx, em("MULTIPLY", bb_mn.outputs["Y"], i_scs.outputs["Y"]), rf_cz), i_rot))
    rf_sel = tand(tand(tand(d_live, is_c(cat, 1)), tcmp("GREATER_THAN", rh_ph.outputs["Value"], 0.001)),
                  tand(tcmp("GREATER_EQUAL", k_nz.outputs["Z"], 0.5),
                       tcmp("GREATER_THAN", em("SUBTRACT", tm("MULTIPLY_ADD", d_ns, 0.65, 0.175), d_thr),
                            em("MULTIPLY", em("SUBTRACT", 1.0, rh_ph.outputs["Value"]), 0.25))))
    rf_size = v3(em("ADD", em("MULTIPLY", em("SUBTRACT", bb_mx.outputs["X"], bb_mn.outputs["X"]), i_scs.outputs["X"]),
                    em("DIVIDE", 0.01, geo_f)),
                 em("ADD", rf_out, rf_dep), rf_h)
    rf_chain = d_chain
    for nm_, dt_, val_ in (("vm_kr", "QUATERNION", i_rot), ("vm_ks", "FLOAT_VECTOR", rf_size),
                           ("vm_kb", "FLOAT_VECTOR", rf_kb), ("vm_kroof", "FLOAT", 1.0)):
        st_ = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type=dt_, domain="INSTANCE")
        b.L(rf_chain, st_.inputs["Geometry"])
        st_.inputs["Name"].default_value = nm_
        if isinstance(val_, float):
            st_.inputs["Value"].default_value = val_
        else:
            b.L(val_, st_.inputs["Value"])
        rf_chain = st_.outputs["Geometry"]
    rf_pts = b.N("GeometryNodeInstancesToPoints", random_loc())
    b.L(rf_chain, rf_pts.inputs["Instances"])
    b.L(rf_sel, rf_pts.inputs["Selection"])
    b.L(vmath("ADD", rf_kb, vmath("SCALE", k_n, em("MULTIPLY", em("SUBTRACT", rf_out, rf_dep), 0.5))),
        rf_pts.inputs["Position"])
    gap_markers(rf_pts.outputs["Points"])

    # replacement collections (fallback when empty: cut short / no wear)
    def coll_count(sock_name):
        ci_ = b.N("GeometryNodeCollectionInfo", random_loc())
        b.L(gi.outputs[sock_name], ci_.inputs["Collection"])
        ci_.inputs["Separate Children"].default_value = True
        ci_.inputs["Reset Children"].default_value = True
        ds_ = b.N("GeometryNodeAttributeDomainSize", random_loc())
        ds_.component = "INSTANCES"
        b.L(ci_.outputs["Instances"], ds_.inputs["Geometry"])
        return ci_.outputs["Instances"], ds_.outputs["Instance Count"]
    br_inst, br_n = coll_count("Broken Props")
    wo_inst, wo_n = coll_count("Worn Props")
    has_br = tcmp("GREATER_THAN", br_n, 0.5)
    has_wo = tcmp("GREATER_THAN", wo_n, 0.5)
    sel_br = tand(is_c(cat, 2), has_br)
    # v2.14: a loose (hanging / curled) tile is a worn one too - no clean flat
    # free end swinging over a hole
    sel_wo = tand(bor(is_c(cat, 4), is_c(cat, 3)), has_wo)
    d_del = b.N("GeometryNodeDeleteGeometry", random_loc(), domain="INSTANCE")
    b.L(d_chain, d_del.inputs["Geometry"])
    b.L(bor(is_c(cat, 1), bor(sel_br, sel_wo)), d_del.inputs["Selection"])
    # fallback broken: the tile itself cut short about its kept end
    d_f = dnamed("vm_dfrac", "FLOAT")                              # what remains
    d_sc = b.N("GeometryNodeScaleInstances", random_loc())
    b.L(d_del.outputs["Geometry"], d_sc.inputs["Instances"])
    b.L(tand(is_c(cat, 2), bnot(has_br)), d_sc.inputs["Selection"])
    b.L(vsw(d_long, v3(1.0, 1.0, d_f), v3(d_f, 1.0, 1.0)), d_sc.inputs["Scale"])
    b.L(vsw(d_long, v3(0.0, 0.0, bb_mx.outputs["Z"]), v3(d_end, 0.0, 0.0)), d_sc.inputs["Center"])
    d_sc.inputs["Local Space"].default_value = True
    # loose: a shake curls out about its top edge (+Y is the face normal); a
    # long board HANGS from the nail at its kept end - the free end drops
    # (in-plane turn) and swings a little off the wall over the boards below
    d_tx = em("MULTIPLY", gi.outputs["Max Tilt"],
              tsw(d_long, tm("MULTIPLY_ADD", dr_s.outputs["X"], 0.7, 0.3),
                  em("MULTIPLY", dr_s.outputs["X"], 0.3)))
    d_sgn = tsw(side_hi, 1.0, -1.0)            # nail at min X: +turn drops the +X end
    d_ty = tsw(d_long, 0.0, em("MULTIPLY", d_sgn, em("MULTIPLY", gi.outputs["Max Tilt"],
                                                     tm("MULTIPLY_ADD", dr_s.outputs["Z"], 0.6, 0.4))))
    d_tz = tsw(d_long, 0.0, em("MULTIPLY", d_sgn, 0.015))
    d_eul = b.N("FunctionNodeEulerToRotation", random_loc())
    b.L(v3(d_tx, d_ty, d_tz), d_eul.inputs["Euler"])
    def loosen(inst_geo, sel_):
        rot_ = b.N("GeometryNodeRotateInstances", random_loc())
        b.L(inst_geo, rot_.inputs["Instances"])
        b.L(sel_, rot_.inputs["Selection"])
        b.L(d_eul.outputs["Rotation"], rot_.inputs["Rotation"])
        b.L(v3(tsw(d_long, 0.0, d_end), 0.0, bb_mx.outputs["Z"]), rot_.inputs["Pivot Point"])
        rot_.inputs["Local Space"].default_value = True
        return rot_.outputs["Instances"]
    b.L(loosen(d_sc.outputs["Instances"], is_c(cat, 3)), join_all.inputs["Geometry"])

    # broken pieces: placed at the kept end (board) / top edge (shake), the
    # remaining length scaled, same rotation and cross-section as the tile
    def replace(sel_, inst_, n_sock, pick_, pos_, scale_):
        i2p = b.N("GeometryNodeInstancesToPoints", random_loc())
        b.L(d_chain, i2p.inputs["Instances"])
        b.L(sel_, i2p.inputs["Selection"])
        sp_ = b.N("GeometryNodeSetPosition", random_loc())
        b.L(i2p.outputs["Points"], sp_.inputs["Geometry"])
        if pos_ is not None:
            b.L(pos_, sp_.inputs["Position"])
        iop_ = b.N("GeometryNodeInstanceOnPoints", random_loc())
        b.L(sp_.outputs["Geometry"], iop_.inputs["Points"])
        b.L(inst_, iop_.inputs["Instance"])
        iop_.inputs["Pick Instance"].default_value = True
        b.L(pick_, iop_.inputs["Instance Index"])
        b.L(dnamed("vm_irot", "QUATERNION"), iop_.inputs["Rotation"])
        b.L(scale_, iop_.inputs["Scale"])
        return iop_.outputs["Instances"]
    p_pos = b.N("GeometryNodeInputPosition", random_loc()).outputs["Position"]
    p_scs = b.N("ShaderNodeSeparateXYZ", random_loc())
    b.L(dnamed("vm_iscl", "FLOAT_VECTOR"), p_scs.inputs["Vector"])
    p_off = b.N("FunctionNodeRotateVector", random_loc())
    b.L(vsw(d_long, v3(0.0, 0.0, em("MULTIPLY", bb_mx.outputs["Z"], p_scs.outputs["Z"])),
            v3(em("MULTIPLY", d_end, p_scs.outputs["X"]), 0.0, 0.0)), p_off.inputs["Vector"])
    b.L(dnamed("vm_irot", "QUATERNION"), p_off.inputs["Rotation"])
    br_pairs = em("MAXIMUM", em("FLOOR", em("DIVIDE", br_n, 2.0)), 1.0)
    br_k = em("MINIMUM", em("FLOOR", em("MULTIPLY", dr_s.outputs["Z"], br_pairs)), em("SUBTRACT", br_pairs, 1.0))
    br_bit = tsw(d_long, tsw(tcmp("LESS_THAN", dr_s.outputs["Y"], 0.5), 0.0, 1.0), side)
    b.L(replace(sel_br, br_inst, br_n, tm("MULTIPLY_ADD", br_k, 2.0, br_bit),
                vmath("ADD", p_pos, p_off.outputs["Vector"]),
                vsw(d_long, v3(p_scs.outputs["X"], p_scs.outputs["Y"],
                               em("MULTIPLY", em("MULTIPLY", d_f, t_exs.outputs["Z"]), p_scs.outputs["Z"])),
                    v3(em("MULTIPLY", em("MULTIPLY", d_f, t_exs.outputs["X"]), p_scs.outputs["X"]),
                       p_scs.outputs["Y"], p_scs.outputs["Z"]))),
        join_all.inputs["Geometry"])
    wo_k = em("MINIMUM", em("FLOOR", em("MULTIPLY", dr_s.outputs["Z"], wo_n)), em("SUBTRACT", wo_n, 1.0))
    # worn pieces carry vm_dcat / vm_dside / vm_drnd over, so loose ones hang
    # exactly like the plain tile would
    b.L(loosen(replace(sel_wo, wo_inst, wo_n, wo_k, None, dnamed("vm_iscl", "FLOAT_VECTOR")),
               is_c(cat, 3)), join_all.inputs["Geometry"])

    # ---- v2.15 REAL OPENINGS + INTERIOR (the user's 'a window where there is
    # no wall', 'with the damage holes we are supposed to see the interior').
    # A Fit layer with Cut Openings ON cuts every opening placed so far that no
    # earlier layer cut (its own + the earlier layers' - turn it on on the LAST
    # opening layer):
    # - the host mesh gets a real hole the size of the prop (minus Opening
    #   Inset, so the frame laps the wall) with jambs Wall Depth deep;
    # - an INTERIOR shell (the host's faces turned inward, Interior Material /
    #   Interior Floor Material) is what you see through it;
    # - every incoming cladding tile that crosses an opening is cut back to
    #   the opening's sides (split in two when it spans it).
    p_cut = b.panel("Openings", "Fit (v2.15): cut real openings through the wall - jambs, an "
                    "interior behind them, cladding cut around them")
    b.sock("Cut Openings", "NodeSocketBool", p_cut, False,
           desc="Fit (v2.15): cut every opening placed so far (this layer's and the earlier "
                "layers') through the host mesh, show the interior through it and cut the "
                "cladding around it. Turn it on on the LAST opening layer")
    b.sock("Opening Inset", "NodeSocketFloat", p_cut, 0.03, 0.0, 1.0, "DISTANCE",
           "Openings: the hole is the prop's outline shrunk by this (world m) - the frame "
           "laps the wall")
    b.sock("Wall Depth", "NodeSocketFloat", p_cut, 0.15, 0.0, 5.0, "DISTANCE",
           "Openings: jamb depth into the wall (world m)")
    b.sock("Jamb Material", "NodeSocketMaterial", p_cut, None,
           desc="Openings: material of the jambs (empty = none assigned)")
    b.sock("Interior Material", "NodeSocketMaterial", p_cut, None,
           desc="Openings: inside walls and ceiling (empty = none assigned)")
    b.sock("Interior Floor Material", "NodeSocketMaterial", p_cut, None,
           desc="Openings: inside floor (empty = the Interior Material)")
    for lk in list(b.ng.links):
        if lk.from_node == join_all and lk.to_node == go:
            b.ng.links.remove(lk)
    c_sep = b.N("GeometryNodeSeparateComponents", random_loc())
    b.L(join_all.outputs["Geometry"], c_sep.inputs["Geometry"])
    c_inst0 = c_sep.outputs["Instances"]
    ib_ = b.N("GeometryNodeInputInstanceBounds", random_loc())
    is_new = tand(tcmp("GREATER_THAN", dnamed("vm_openmark", "FLOAT"), 0.5),
                  tcmp("LESS_THAN", dnamed("vm_cutdone", "FLOAT"), 0.5))
    c_chain = c_inst0
    for nm_, dt_, val_ in (("vm_obmin", "FLOAT_VECTOR", ib_.outputs["Min"]),
                           ("vm_obmax", "FLOAT_VECTOR", ib_.outputs["Max"]),
                           ("vm_orot", "QUATERNION", i_rot), ("vm_oscl", "FLOAT_VECTOR", i_scl)):
        st_ = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type=dt_, domain="INSTANCE")
        b.L(c_chain, st_.inputs["Geometry"])
        st_.inputs["Name"].default_value = nm_
        b.L(val_, st_.inputs["Value"])
        c_chain = st_.outputs["Geometry"]
    c_inst = c_chain

    def rot(vec_, rot_):
        rv_ = b.N("FunctionNodeRotateVector", random_loc())
        b.L(vec_, rv_.inputs["Vector"]); b.L(rot_, rv_.inputs["Rotation"])
        return rv_.outputs["Vector"]

    def vmul(a_, b_):
        return vmath("MULTIPLY", a_, b_)
    # one point per new opening, at its cut box centre
    o_pts = b.N("GeometryNodeInstancesToPoints", random_loc())
    b.L(c_inst, o_pts.inputs["Instances"])
    b.L(is_new, o_pts.inputs["Selection"])
    o_cnt = b.N("GeometryNodeAttributeDomainSize", random_loc())
    o_cnt.component = "POINTCLOUD"
    b.L(o_pts.outputs["Points"], o_cnt.inputs["Geometry"])
    has_open = tcmp("GREATER_THAN", o_cnt.outputs["Point Count"], 0.5)
    o_rot = dnamed("vm_orot", "QUATERNION")
    o_lo = vmul(dnamed("vm_obmin", "FLOAT_VECTOR"), dnamed("vm_oscl", "FLOAT_VECTOR"))
    o_hi = vmul(dnamed("vm_obmax", "FLOAT_VECTOR"), dnamed("vm_oscl", "FLOAT_VECTOR"))
    lx, _ly, lz = sxyz(o_lo)
    hx, _hy, hz = sxyz(o_hi)
    # v2.23 a DOOR (tall opening) is a bare leaf, not a framed prop: its hole
    # is the leaf plus a 1 cm gap (and down past the threshold), deep enough
    # to take the leaf set back into the wall (below), and it gets a casing
    o_dr = tcmp("GREATER_THAN", em("SUBTRACT", hz, lz), em("MULTIPLY", em("SUBTRACT", hx, lx), 1.8))
    dr_set = em("ADD", _hy, em("DIVIDE", em("ADD", em("SUBTRACT", gi.outputs["Backing Offset"], gi.outputs["Embed"]),
                                            DOOR_RECESS), geo_f))
    ins_l = tsw(o_dr, em("DIVIDE", gi.outputs["Opening Inset"], geo_f), em("DIVIDE", -DOOR_GAP, geo_f))
    ins_z = tsw(o_dr, ins_l, em("DIVIDE", -0.5 * (DOOR_GAP + DOOR_SILL_CUT), geo_f))
    dep_l = tsw(o_dr, em("DIVIDE", gi.outputs["Wall Depth"], geo_f),
                em("MAXIMUM", em("DIVIDE", gi.outputs["Wall Depth"], geo_f), em("ADD", dr_set, em("DIVIDE", 0.03, geo_f))))
    out_l = em("DIVIDE", 0.05, geo_f)
    o_hu = em("MAXIMUM", em("SUBTRACT", em("MULTIPLY", em("SUBTRACT", hx, lx), 0.5), ins_l), 0.001)
    o_hz = em("MAXIMUM", em("SUBTRACT", em("MULTIPLY", em("SUBTRACT", hz, lz), 0.5), ins_z), 0.001)
    o_ctr_l = v3(em("MULTIPLY", em("ADD", lx, hx), 0.5), em("MULTIPLY", em("SUBTRACT", out_l, dep_l), 0.5),
                 em("ADD", em("MULTIPLY", em("ADD", lz, hz), 0.5), tsw(o_dr, 0.0, em("DIVIDE", 0.5 * (DOOR_GAP - DOOR_SILL_CUT), geo_f))))
    o_pos = b.N("GeometryNodeInputPosition", random_loc()).outputs["Position"]
    o_ctr = vmath("ADD", o_pos, rot(o_ctr_l, o_rot))
    o_chain = o_pts.outputs["Points"]
    for nm_, val_ in (("vm_cctr", o_ctr), ("vm_cu", rot(v3(1.0, 0.0, 0.0), o_rot)),
                      ("vm_cn", rot(v3(0.0, 1.0, 0.0), o_rot)), ("vm_cup", rot(v3(0.0, 0.0, 1.0), o_rot)),
                      ("vm_csize", v3(em("MULTIPLY", o_hu, 2.0), em("ADD", dep_l, out_l),
                                      em("MULTIPLY", o_hz, 2.0))),
                      ("vm_chalf", v3(o_hu, 0.0, o_hz))):
        st_ = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT_VECTOR", domain="POINT")
        b.L(o_chain, st_.inputs["Geometry"])
        st_.inputs["Name"].default_value = nm_
        b.L(val_, st_.inputs["Value"])
        o_chain = st_.outputs["Geometry"]
    o_cloud = o_chain
    # the cut boxes: a unit cube per opening; its inner (-Y) face is marked so
    # the hole opens into the interior once the boolean is done
    cube_ = b.N("GeometryNodeMeshCube", random_loc())
    cube_.inputs["Size"].default_value = (1.0, 1.0, 1.0)
    cb_n = sxyz(b.N("GeometryNodeInputNormal", random_loc()).outputs["Normal"])[1]
    cb_chain = cube_.outputs["Mesh"]
    for nm_, val_ in (("vm_cutback", tsw(tcmp("LESS_THAN", cb_n, -0.5), 0.0, 1.0)), ("vm_cutter", 1.0)):
        st_ = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT", domain="FACE")
        b.L(cb_chain, st_.inputs["Geometry"])
        st_.inputs["Name"].default_value = nm_
        if isinstance(val_, float):
            st_.inputs["Value"].default_value = val_
        else:
            b.L(val_, st_.inputs["Value"])
        cb_chain = st_.outputs["Geometry"]
    o_mv = b.N("GeometryNodeSetPosition", random_loc())
    b.L(o_cloud, o_mv.inputs["Geometry"])
    b.L(dnamed("vm_cctr", "FLOAT_VECTOR"), o_mv.inputs["Position"])
    o_iop = b.N("GeometryNodeInstanceOnPoints", random_loc())
    b.L(o_mv.outputs["Geometry"], o_iop.inputs["Points"])
    b.L(cb_chain, o_iop.inputs["Instance"])
    b.L(o_rot, o_iop.inputs["Rotation"])
    b.L(dnamed("vm_csize", "FLOAT_VECTOR"), o_iop.inputs["Scale"])
    o_real = b.N("GeometryNodeRealizeInstances", random_loc())
    b.L(o_iop.outputs["Instances"], o_real.inputs["Geometry"])
    # the host: every mesh face but the edge boards and the old interior
    # shell (rebuilt below, so a second cutting layer stays clean)
    c_mesh = c_sep.outputs["Mesh"]
    is_trim = tcmp("GREATER_THAN", dnamed("vm_trim", "FLOAT"), 0.5)
    c_host = b.N("GeometryNodeDeleteGeometry", random_loc(), domain="FACE")
    b.L(c_mesh, c_host.inputs["Geometry"])
    b.L(bor(is_trim, tcmp("GREATER_THAN", dnamed("vm_inner", "FLOAT"), 0.5)), c_host.inputs["Selection"])
    c_trims = b.N("GeometryNodeDeleteGeometry", random_loc(), domain="FACE")
    b.L(c_mesh, c_trims.inputs["Geometry"])
    b.L(bnot(is_trim), c_trims.inputs["Selection"])
    c_bool = b.N("GeometryNodeMeshBoolean", random_loc(), operation="DIFFERENCE", solver="EXACT")
    b.L(c_host.outputs["Geometry"], c_bool.inputs["Mesh 1"])
    b.L(o_real.outputs["Geometry"], c_bool.inputs["Mesh 2"])
    c_bool.inputs["Hole Tolerant"].default_value = True
    c_open = b.N("GeometryNodeDeleteGeometry", random_loc(), domain="FACE")
    b.L(c_bool.outputs["Mesh"], c_open.inputs["Geometry"])
    b.L(tcmp("GREATER_THAN", dnamed("vm_cutback", "FLOAT"), 0.5), c_open.inputs["Selection"])
    is_jamb = tcmp("GREATER_THAN", dnamed("vm_cutter", "FLOAT"), 0.5)
    # jamb boards get wood UVs in meters, the grain along each jamb's length
    # (up the side jambs, along the wall on the head and the sill)
    j_eval = b.N("GeometryNodeFieldOnDomain", random_loc(), domain="FACE", data_type="FLOAT_VECTOR")
    b.L(b.N("GeometryNodeInputNormal", random_loc()).outputs["Normal"], j_eval.inputs[0])
    jnx, jny, jnz = sxyz(j_eval.outputs[0])
    jpx, jpy, jpz = sxyz(b.N("GeometryNodeInputPosition", random_loc()).outputs["Position"])
    j_flat = tcmp("GREATER_THAN", em("ABSOLUTE", jnz), 0.5)
    j_along = em("SUBTRACT", em("MULTIPLY", jpy, jnx), em("MULTIPLY", jpx, jny))   # along the wall
    j_wall_u = tsw(tcmp("GREATER_THAN", em("ABSOLUTE", jnx), em("ABSOLUTE", jny)), jpx, jpy)
    j_uv = v3(em("MULTIPLY", tsw(j_flat, jpz, j_wall_u), geo_f),
              em("MULTIPLY", tsw(j_flat, j_along, em("ADD", jpx, jpy)), geo_f), 0.0)
    j_st = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT2", domain="CORNER")
    b.L(c_open.outputs["Geometry"], j_st.inputs["Geometry"])
    j_st.inputs["Name"].default_value = "UVMap"
    b.L(is_jamb, j_st.inputs["Selection"])
    b.L(j_uv, j_st.inputs["Value"])
    c_walls = material_gate(b, j_st.outputs["Geometry"], gi.outputs["Jamb Material"], is_jamb,
                            random_loc())
    # the interior: the host's own faces turned inward a hair inside the wall
    sh_ = b.N("GeometryNodeDeleteGeometry", random_loc(), domain="FACE")
    b.L(c_open.outputs["Geometry"], sh_.inputs["Geometry"])
    b.L(is_jamb, sh_.inputs["Selection"])
    sh_n = b.N("GeometryNodeInputNormal", random_loc()).outputs["Normal"]
    sh_mv = b.N("GeometryNodeSetPosition", random_loc())
    b.L(sh_.outputs["Geometry"], sh_mv.inputs["Geometry"])
    b.L(vmath("SCALE", sh_n, em("DIVIDE", -0.004, geo_f)), sh_mv.inputs["Offset"])
    sh_fl = b.N("GeometryNodeFlipFaces", random_loc())
    b.L(sh_mv.outputs["Geometry"], sh_fl.inputs["Mesh"])
    sh_st = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT", domain="FACE")
    b.L(sh_fl.outputs["Mesh"], sh_st.inputs["Geometry"])
    sh_st.inputs["Name"].default_value = "vm_inner"
    sh_st.inputs["Value"].default_value = 1.0
    sh_m1 = material_gate(b, sh_st.outputs["Geometry"], gi.outputs["Interior Material"],
                          bnot(is_jamb), random_loc())
    sh_up = tcmp("GREATER_THAN", sxyz(b.N("GeometryNodeInputNormal", random_loc()).outputs["Normal"])[2], 0.7)
    sh_m2 = material_gate(b, sh_m1, gi.outputs["Interior Floor Material"], sh_up, random_loc())

    # cladding cut around the openings: a tile crossing its nearest opening is
    # split into the piece left of it and the piece right of it (each scaled
    # about its own outer end); two passes catch a tile spanning two openings
    def trim_pass(geo_):
        sn_ = b.N("GeometryNodeSampleNearest", random_loc(), domain="POINT")
        b.L(o_cloud, sn_.inputs["Geometry"])
        t_p = b.N("GeometryNodeInputPosition", random_loc()).outputs["Position"]
        b.L(t_p, sn_.inputs["Sample Position"])

        def o_at(name_):
            si_ = b.N("GeometryNodeSampleIndex", random_loc(), data_type="FLOAT_VECTOR", domain="POINT")
            b.L(o_cloud, si_.inputs["Geometry"])
            b.L(dnamed(name_, "FLOAT_VECTOR"), si_.inputs["Value"])
            b.L(sn_.outputs["Index"], si_.inputs["Index"])
            return si_.outputs["Value"]
        oc, ou, on, oup, ohalf = (o_at("vm_cctr"), o_at("vm_cu"), o_at("vm_cn"), o_at("vm_cup"),
                                  o_at("vm_chalf"))
        hu_, _hy, hz_ = sxyz(ohalf)
        ib2 = b.N("GeometryNodeInputInstanceBounds", random_loc())
        bmn_x, _bmy, bmn_z = sxyz(ib2.outputs["Min"])
        bmx_x, _bxy, bmx_z = sxyz(ib2.outputs["Max"])
        isx, _isy, isz = sxyz(i_scl)
        rel = vmath("SUBTRACT", t_p, oc)

        def dot(a_, b_):
            return vmath("DOT_PRODUCT", a_, b_, out="Value")
        tx_ = rot(v3(1.0, 0.0, 0.0), i_rot)
        e_lo = vmath("ADD", rel, vmath("SCALE", tx_, em("MULTIPLY", bmn_x, isx)))
        e_hi = vmath("ADD", rel, vmath("SCALE", tx_, em("MULTIPLY", bmx_x, isx)))
        a_l, a_h = dot(e_lo, ou), dot(e_hi, ou)
        a0, a1 = em("MINIMUM", a_l, a_h), em("MAXIMUM", a_l, a_h)
        zc = dot(rel, oup)
        z0 = em("ADD", zc, em("MULTIPLY", bmn_z, isz))
        z1 = em("ADD", zc, em("MULTIPLY", bmx_z, isz))
        z_ov = em("SUBTRACT", em("MINIMUM", z1, hz_), em("MAXIMUM", z0, em("MULTIPLY", hz_, -1.0)))
        eps_ = em("DIVIDE", 0.005, geo_f)
        hit = tand(tand(has_open, tcmp("LESS_THAN", dnamed("vm_openmark", "FLOAT"), 0.5)),
                   tand(tand(tcmp("GREATER_THAN", a1, em("SUBTRACT", eps_, hu_)),
                             tcmp("LESS_THAN", a0, em("SUBTRACT", hu_, eps_))),
                        tand(tcmp("GREATER_THAN", z_ov, eps_),
                             tand(tcmp("LESS_THAN", em("ABSOLUTE", dot(rel, on)), em("DIVIDE", 0.3, geo_f)),
                                  tcmp("GREATER_THAN", dot(rot(v3(0.0, 1.0, 0.0), i_rot), on), 0.9)))))
        g_ = geo_
        for nm_, dt_, val_ in (("vm_ta0", "FLOAT", a0), ("vm_ta1", "FLOAT", a1), ("vm_thu", "FLOAT", hu_),
                               ("vm_tz0", "FLOAT", z0), ("vm_tz1", "FLOAT", z1), ("vm_thz", "FLOAT", hz_),
                               ("vm_tsg", "FLOAT", dot(tx_, ou)), ("vm_tou", "FLOAT_VECTOR", ou),
                               ("vm_thit", "FLOAT", tsw(hit, 0.0, 1.0))):
            st_ = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type=dt_, domain="INSTANCE")
            b.L(g_, st_.inputs["Geometry"])
            st_.inputs["Name"].default_value = nm_
            b.L(val_, st_.inputs["Value"])
            g_ = st_.outputs["Geometry"]
        t_hit = tcmp("GREATER_THAN", dnamed("vm_thit", "FLOAT"), 0.5)
        keep_ = b.N("GeometryNodeDeleteGeometry", random_loc(), domain="INSTANCE")
        b.L(g_, keep_.inputs["Geometry"])
        b.L(t_hit, keep_.inputs["Selection"])
        # pieces: 0 = left of the hole, 1 = right of it, 2 = the part of the
        # board above / below the hole across its width (a notched board)
        dup_ = b.N("GeometryNodeDuplicateElements", random_loc(), domain="INSTANCE")
        b.L(g_, dup_.inputs["Geometry"])
        b.L(t_hit, dup_.inputs["Selection"])
        dup_.inputs["Amount"].default_value = 3
        st_ = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT", domain="INSTANCE")
        b.L(dup_.outputs["Geometry"], st_.inputs["Geometry"])
        st_.inputs["Name"].default_value = "vm_tside"
        b.L(dup_.outputs["Duplicate Index"], st_.inputs["Value"])
        ta0, ta1 = dnamed("vm_ta0", "FLOAT"), dnamed("vm_ta1", "FLOAT")
        thu, thz = dnamed("vm_thu", "FLOAT"), dnamed("vm_thz", "FLOAT")
        tz0, tz1 = dnamed("vm_tz0", "FLOAT"), dnamed("vm_tz1", "FLOAT")
        side_ = dnamed("vm_tside", "FLOAT")
        right = tcmp("GREATER_THAN", side_, 0.5)
        mid = tcmp("GREATER_THAN", side_, 1.5)
        nhu = em("MULTIPLY", thu, -1.0)
        p0 = tsw(mid, tsw(right, ta0, thu), em("MAXIMUM", ta0, nhu))
        p1 = tsw(mid, tsw(right, nhu, ta1), em("MINIMUM", ta1, thu))
        p_len = em("SUBTRACT", p1, p0)
        f_ = em("DIVIDE", p_len, em("MAXIMUM", em("SUBTRACT", ta1, ta0), 1e-6))
        k_bot = em("SUBTRACT", em("MULTIPLY", thz, -1.0), tz0)      # board left below the hole
        k_top = em("SUBTRACT", tz1, thz)                            # ... and above it
        bot_ = tcmp("GREATER_EQUAL", k_bot, k_top)
        k_z = tsw(mid, em("SUBTRACT", tz1, tz0), em("MAXIMUM", k_bot, k_top))
        fz = em("DIVIDE", k_z, em("MAXIMUM", em("SUBTRACT", tz1, tz0), 1e-6))
        pos_sg = tcmp("GREATER_THAN", dnamed("vm_tsg", "FLOAT"), 0.0)
        ib3 = b.N("GeometryNodeInputInstanceBounds", random_loc())
        b3n_x, _b3ny, b3n_z = sxyz(ib3.outputs["Min"])
        b3x_x, _b3xy, b3x_z = sxyz(ib3.outputs["Max"])
        # every piece is the board scaled about its a0 end (+ its kept edge),
        # then slid along the wall to where the piece starts
        sc_ = b.N("GeometryNodeScaleInstances", random_loc())
        b.L(st_.outputs["Geometry"], sc_.inputs["Instances"])
        b.L(v3(f_, 1.0, fz), sc_.inputs["Scale"])
        b.L(v3(tsw(pos_sg, b3x_x, b3n_x), 0.0, tsw(bot_, b3x_z, b3n_z)), sc_.inputs["Center"])
        sc_.inputs["Local Space"].default_value = True
        tr_ = b.N("GeometryNodeTranslateInstances", random_loc())
        b.L(sc_.outputs["Instances"], tr_.inputs["Instances"])
        b.L(vmath("SCALE", dnamed("vm_tou", "FLOAT_VECTOR"), em("SUBTRACT", p0, ta0)), tr_.inputs["Translation"])
        tr_.inputs["Local Space"].default_value = False
        drop_ = b.N("GeometryNodeDeleteGeometry", random_loc(), domain="INSTANCE")
        b.L(tr_.outputs["Instances"], drop_.inputs["Geometry"])
        b.L(bor(tcmp("LESS_THAN", p_len, em("DIVIDE", 0.02, geo_f)),
                tcmp("LESS_THAN", k_z, em("DIVIDE", 0.01, geo_f))), drop_.inputs["Selection"])
        j_ = b.N("GeometryNodeJoinGeometry", random_loc())
        b.L(keep_.outputs["Geometry"], j_.inputs["Geometry"])
        b.L(drop_.outputs["Geometry"], j_.inputs["Geometry"])
        return j_.outputs["Geometry"]
    c_tiles = trim_pass(trim_pass(c_inst))
    # v2.23 the door leaf goes INTO its hole: its front DOOR_RECESS behind the
    # wall face (it stood on the siding, its back on the backing plane)
    dl_lo = sxyz(vmul(dnamed("vm_obmin", "FLOAT_VECTOR"), dnamed("vm_oscl", "FLOAT_VECTOR")))
    dl_hi = sxyz(vmul(dnamed("vm_obmax", "FLOAT_VECTOR"), dnamed("vm_oscl", "FLOAT_VECTOR")))
    dl_is = tand(is_new, tcmp("GREATER_THAN", em("SUBTRACT", dl_hi[2], dl_lo[2]),
                              em("MULTIPLY", em("SUBTRACT", dl_hi[0], dl_lo[0]), 1.8)))
    dl_set = em("ADD", dl_hi[1], em("DIVIDE", em("ADD", em("SUBTRACT", gi.outputs["Backing Offset"], gi.outputs["Embed"]),
                                                 DOOR_RECESS), geo_f))
    dl_tr = b.N("GeometryNodeTranslateInstances", random_loc())
    b.L(c_tiles, dl_tr.inputs["Instances"])
    b.L(dl_is, dl_tr.inputs["Selection"])
    b.L(rot(v3(0.0, em("MULTIPLY", dl_set, -1.0), 0.0), i_rot), dl_tr.inputs["Translation"])
    dl_tr.inputs["Local Space"].default_value = False
    c_tiles = dl_tr.outputs["Instances"]
    c_done = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT", domain="INSTANCE")
    b.L(c_tiles, c_done.inputs["Geometry"])
    c_done.inputs["Name"].default_value = "vm_cutdone"
    b.L(tsw(is_new, dnamed("vm_cutdone", "FLOAT"), 1.0), c_done.inputs["Value"])
    c_join = b.N("GeometryNodeJoinGeometry", random_loc())
    for g_ in (c_walls, sh_m2, c_trims.outputs["Geometry"], c_done.outputs["Geometry"],
               c_sep.outputs["Curve"], c_sep.outputs["Point Cloud"], c_sep.outputs["Volume"]):
        b.L(g_, c_join.inputs["Geometry"])
    c_sw = b.N("GeometryNodeSwitch", random_loc())
    c_sw.input_type = "GEOMETRY"
    b.L(tand(tand(gi.outputs["Cut Openings"], is_fit), has_open), c_sw.inputs["Switch"])
    b.L(join_all.outputs["Geometry"], c_sw.inputs["False"])
    b.L(c_join.outputs["Geometry"], c_sw.inputs["True"])

    # ---- v2.16 DAMAGE REACHES THE TRIM AND THE OPENINGS (the user's 'the
    # damage should have affected those corner boards as well', 'adding damage
    # should affect the windows - damage them or remove them, they can't float
    # on a few planks').
    # (a) corner boards / ridge caps: with Damage on each edge board is laid in
    # ~1 m pieces and every piece takes the siding's own damage field - gone,
    # broken short (keeps its upper nail) or hanging loose from its upper end.
    # Damage off = one board per edge, exactly as before.
    for lk in list(b.ng.links):
        if lk.from_node == e_sp and lk.to_node == e_iop:
            b.ng.links.remove(lk)
    e_wlen = em("MULTIPLY", e_len.outputs["Value"], geo_f)
    e_n = tsw(d_live, 1.0, em("MAXIMUM", em("FLOOR", em("ADD", e_wlen, 0.5)), 1.0))
    e_dup = b.N("GeometryNodeDuplicateElements", random_loc(), domain="POINT")
    b.L(e_sp.outputs["Geometry"], e_dup.inputs["Geometry"])
    b.L(e_n, e_dup.inputs["Amount"])
    e_k = e_dup.outputs["Duplicate Index"]
    e_chain2 = e_dup.outputs["Geometry"]
    for nm_, val_ in (("vm_esk", e_k), ("vm_esn", e_n)):        # (vm_en is the slots' own)
        st_ = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT", domain="POINT")
        b.L(e_chain2, st_.inputs["Geometry"])
        st_.inputs["Name"].default_value = nm_
        b.L(val_, st_.inputs["Value"])
        e_chain2 = st_.outputs["Geometry"]
    ek_, en_ = dnamed("vm_esk", "FLOAT"), dnamed("vm_esn", "FLOAT")

    def e_at(frac_):
        return vmath("ADD", ep1, vmath("SCALE", e_dir.outputs["Vector"], em("DIVIDE", frac_, en_)))
    # the damage field is read at each piece's centre
    e_mid = b.N("GeometryNodeSetPosition", random_loc())
    b.L(e_chain2, e_mid.inputs["Geometry"])
    b.L(e_at(em("ADD", ek_, 0.5)), e_mid.inputs["Position"])
    e_up = tcmp("GREATER_EQUAL", sxyz(e_dir.outputs["Vector"])[2], 0.0)     # local +Z end is the upper
    e_top = tsw(tcmp("GREATER_THAN", em("ABSOLUTE", sxyz(e_dn.outputs["Vector"])[2]), 0.3),
                tsw(tcmp("LESS_THAN", r_a["Z"], 0.5), 0.0, 1.0), tsw(e_up, 0.0, 1.0))
    e_chain3 = e_mid.outputs["Geometry"]
    for nm_, val_ in (("vm_ecat", tsw(d_live, 0.0, d_cat)), ("vm_etop", e_top),
                      ("vm_efr", tm("MULTIPLY_ADD", r_a["Y"], 0.45, 0.35)),
                      ("vm_etl", tm("MULTIPLY_ADD", r_a["X"], 0.7, 0.3))):
        st_ = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT", domain="POINT")
        b.L(e_chain3, st_.inputs["Geometry"])
        st_.inputs["Name"].default_value = nm_
        b.L(val_, st_.inputs["Value"])
        e_chain3 = st_.outputs["Geometry"]
    # v2.20 a corner piece with no wall board holding on next to it (the wall
    # round it is gone - see the gap markers) falls too: nothing to nail to
    es_hold = tand(d_long, bor(is_c(cat, 0), is_c(cat, 4)))
    es_p = b.N("GeometryNodeInstancesToPoints", random_loc())
    b.L(d_chain, es_p.inputs["Instances"])
    b.L(es_hold, es_p.inputs["Selection"])
    es_du = b.N("GeometryNodeDuplicateElements", random_loc(), domain="POINT")
    b.L(es_p.outputs["Points"], es_du.inputs["Geometry"])
    es_du.inputs["Amount"].default_value = 9
    es_sp = b.N("GeometryNodeSetPosition", random_loc())
    b.L(es_du.outputs["Geometry"], es_sp.inputs["Geometry"])
    b.L(vmath("ADD", dnamed("vm_elo", "FLOAT_VECTOR"),
              vmath("SCALE", vmath("SUBTRACT", dnamed("vm_ehi", "FLOAT_VECTOR"), dnamed("vm_elo", "FLOAT_VECTOR")),
                    em("DIVIDE", es_du.outputs["Duplicate Index"], 8.0))), es_sp.inputs["Position"])
    es_n = b.N("GeometryNodeAttributeDomainSize", random_loc())
    es_n.component = "POINTCLOUD"
    b.L(es_p.outputs["Points"], es_n.inputs["Geometry"])
    es_px = b.N("GeometryNodeProximity", random_loc())
    es_px.target_element = "POINTS"
    b.L(es_sp.outputs["Geometry"], es_px.inputs["Geometry"])
    es_free = tand(tand(d_live, tcmp("GREATER_THAN", es_n.outputs["Point Count"], 0.5)),
                   tcmp("GREATER_THAN", es_px.outputs["Distance"], em("DIVIDE", 0.25, geo_f)))
    st_ = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT", domain="POINT")
    b.L(e_chain3, st_.inputs["Geometry"])
    st_.inputs["Name"].default_value = "vm_ecat"
    b.L(tsw(es_free, dnamed("vm_ecat", "FLOAT"), 1.0), st_.inputs["Value"])
    e_chain3 = st_.outputs["Geometry"]
    e_start = b.N("GeometryNodeSetPosition", random_loc())
    b.L(e_chain3, e_start.inputs["Geometry"])
    b.L(e_at(ek_), e_start.inputs["Position"])
    b.L(e_start.outputs["Geometry"], e_iop.inputs["Points"])
    b.L(v3(e_f, 1.0, em("DIVIDE", e_len.outputs["Value"], en_)), e_iop.inputs["Scale"])
    # v2.20 a corner board piece that is gone / broken short leaves a gap
    # marker too: a box round the wall corner (its two leg widths deep on both
    # faces), the length of the gap
    ke_cat = dnamed("vm_ecat", "FLOAT")
    ke_cz = tsw(tcmp("GREATER_THAN", dnamed("vm_etop", "FLOAT"), 0.5), 0.0, 1.0)
    ke_zf = em("SUBTRACT", 1.0, ke_cz)
    ke_c = tsw(is_c(ke_cat, 1), em("MINIMUM", em("SUBTRACT", 1.03, dnamed("vm_efr", "FLOAT")), 1.0), 1.0)
    ke_zc = em("ADD", ke_zf, em("MULTIPLY", em("SUBTRACT", ke_cz, ke_zf), em("MULTIPLY", ke_c, 0.5)))
    ke_a = em("MULTIPLY", em("ADD", e_full, em("DIVIDE", 0.02, geo_f)), 0.7071)
    ke_rot = e_ay.outputs["Rotation"]
    ke_sel = tand(tand(d_live, tcmp("GREATER_THAN", em("ABSOLUTE", sxyz(e_dn.outputs["Vector"])[2]), 0.7)),
                  bor(is_c(ke_cat, 1), is_c(ke_cat, 2)))
    ke_del = b.N("GeometryNodeDeleteGeometry", random_loc(), domain="POINT")
    b.L(e_chain3, ke_del.inputs["Geometry"])
    b.L(bnot(ke_sel), ke_del.inputs["Selection"])
    ke_chain = ke_del.outputs["Geometry"]
    for nm_, dt_, val_ in (("vm_kr", "QUATERNION", ke_rot),
                           ("vm_ks", "FLOAT_VECTOR", v3(em("MULTIPLY", em("MULTIPLY", ke_a, 2.0), e_f),
                                                        em("ADD", em("ADD", k_out, ke_a), k_dep),
                                                        em("ADD", em("MULTIPLY", ke_c, em("DIVIDE", e_len.outputs["Value"], en_)),
                                                           em("DIVIDE", 0.01, geo_f))))):
        st_ = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type=dt_, domain="POINT")
        b.L(ke_chain, st_.inputs["Geometry"])
        st_.inputs["Name"].default_value = nm_
        b.L(val_, st_.inputs["Value"])
        ke_chain = st_.outputs["Geometry"]
    ke_mv = b.N("GeometryNodeSetPosition", random_loc())
    b.L(ke_chain, ke_mv.inputs["Geometry"])
    b.L(vmath("ADD", e_at(em("ADD", ek_, ke_zc)),
              rot(v3(0.0, em("MULTIPLY", em("SUBTRACT", k_out, em("ADD", ke_a, k_dep)), 0.5), 0.0), ke_rot)),
        ke_mv.inputs["Position"])
    gap_markers(ke_mv.outputs["Geometry"])
    for lk in list(b.ng.links):
        if lk.from_node == e_iop and lk.to_node == st_ed:
            b.ng.links.remove(lk)
    ecat = dnamed("vm_ecat", "FLOAT")
    etop = tcmp("GREATER_THAN", dnamed("vm_etop", "FLOAT"), 0.5)
    e_del = b.N("GeometryNodeDeleteGeometry", random_loc(), domain="INSTANCE")
    b.L(e_iop.outputs["Instances"], e_del.inputs["Geometry"])
    b.L(is_c(ecat, 1), e_del.inputs["Selection"])
    e_cz = tsw(etop, 0.0, 1.0)                                  # the kept (upper) end, local z
    e_br = b.N("GeometryNodeScaleInstances", random_loc())
    b.L(e_del.outputs["Geometry"], e_br.inputs["Instances"])
    b.L(is_c(ecat, 2), e_br.inputs["Selection"])
    b.L(v3(1.0, 1.0, dnamed("vm_efr", "FLOAT")), e_br.inputs["Scale"])
    b.L(v3(0.0, 0.0, e_cz), e_br.inputs["Center"])
    e_br.inputs["Local Space"].default_value = True
    # broken or loose: the free end swings off the corner (+Y = outward)
    e_ang = em("MULTIPLY", em("MULTIPLY", gi.outputs["Max Tilt"], dnamed("vm_etl", "FLOAT")),
               tsw(etop, -1.0, 1.0))
    e_ang = em("MULTIPLY", e_ang, tsw(is_c(ecat, 3), 0.35, 1.0))
    e_eul = b.N("FunctionNodeEulerToRotation", random_loc())
    b.L(v3(e_ang, 0.0, 0.0), e_eul.inputs["Euler"])
    e_rt = b.N("GeometryNodeRotateInstances", random_loc())
    b.L(e_br.outputs["Instances"], e_rt.inputs["Instances"])
    b.L(bor(is_c(ecat, 2), is_c(ecat, 3)), e_rt.inputs["Selection"])
    b.L(e_eul.outputs["Rotation"], e_rt.inputs["Rotation"])
    b.L(v3(0.0, 0.0, e_cz), e_rt.inputs["Pivot Point"])
    e_rt.inputs["Local Space"].default_value = True
    b.L(e_rt.outputs["Instances"], st_ed.inputs["Geometry"])

    # (b) openings: the cutting layer reads the damage around every opening it
    # cut (the same field, sampled on a ring just outside the frame). Heavy
    # damage -> the prop is GONE (the raw opening + jambs stay) or HANGS off
    # one top corner (a door swings open on its hinge); some damage -> it sits
    # LOOSE, a few degrees off. Damage off / no cut = untouched.
    o_live = tand(tand(gi.outputs["Damage"], is_fit), gi.outputs["Cut Openings"])

    def dmg_at(vec_):
        return tsw(tcmp("GREATER_THAN", dmg_margin(vec_), 0.0), 0.0, 1.0)
    ob_ib = b.N("GeometryNodeInputInstanceBounds", random_loc())
    obx_n, _oby, obz_n = sxyz(vmul(ob_ib.outputs["Min"], i_scl))
    obx_x, _obyx, obz_x = sxyz(vmul(ob_ib.outputs["Max"], i_scl))
    ring_ = em("DIVIDE", 0.15, geo_f)
    o_ip = b.N("GeometryNodeInputPosition", random_loc()).outputs["Position"]
    samples_ = []
    for fx_, fz_ in ((0.0, -0.1), (0.5, -0.1), (1.0, -0.1), (1.1, 0.5), (1.0, 1.1), (0.5, 1.1),
                     (0.0, 1.1), (-0.1, 0.5), (0.5, 0.5)):
        lx_ = tm("MULTIPLY_ADD", em("SUBTRACT", obx_x, obx_n), fx_, obx_n)
        lz_ = tm("MULTIPLY_ADD", em("SUBTRACT", obz_x, obz_n), fz_, obz_n)
        lx_ = em("ADD", lx_, em("MULTIPLY", ring_, (fx_ > 1.0) - (fx_ < 0.0)))
        lz_ = em("ADD", lz_, em("MULTIPLY", ring_, (fz_ > 1.0) - (fz_ < 0.0)))
        samples_.append(dmg_at(vmath("ADD", o_ip, rot(v3(lx_, 0.0, lz_), i_rot))))
    while len(samples_) > 1:
        samples_ = [em("ADD", samples_[i], samples_[i + 1]) if i + 1 < len(samples_) else samples_[i]
                    for i in range(0, len(samples_), 2)]
    o_frac = em("DIVIDE", samples_[0], 9.0)
    o_rv = b.N("FunctionNodeRandomValue", random_loc(), data_type="FLOAT_VECTOR")
    o_rv.inputs["Min"].default_value = (0.0, 0.0, 0.0)
    o_rv.inputs["Max"].default_value = (1.0, 1.0, 1.0)
    b.L(seed_node(b, d_seed, 307), o_rv.inputs["Seed"])
    o_rx, o_ry, o_rz = sxyz(o_rv.outputs["Value"])
    is_open = tand(o_live, tcmp("GREATER_THAN", dnamed("vm_openmark", "FLOAT"), 0.5))
    o_gone_share = em("DIVIDE", gi.outputs["Missing Share"],
                      em("MAXIMUM", em("ADD", gi.outputs["Missing Share"], gi.outputs["Broken Share"]), 0.01))
    heavy = tcmp("GREATER_EQUAL", o_frac, 0.35)
    some = tcmp("GREATER_EQUAL", o_frac, 0.12)
    # category: 0 intact, 1 gone, 3 hanging, 4 loose
    o_cat = tsw(tand(is_open, some), 0.0,
                tsw(heavy, tsw(tcmp("LESS_THAN", o_rx, 0.5), 4.0, 3.0),
                    tsw(tcmp("LESS_THAN", o_rx, o_gone_share), 3.0, 1.0)))
    # v2.21 5 = partly broken (windows only, any the damage touches that is
    # not gone): stays put, a jagged part broken away
    o_hv = b.N("FunctionNodeRandomValue", random_loc(), data_type="FLOAT_VECTOR")
    o_hv.inputs["Min"].default_value = (0.0, 0.0, 0.0)
    o_hv.inputs["Max"].default_value = (1.0, 1.0, 1.0)
    b.L(seed_node(b, d_seed, 313), o_hv.inputs["Seed"])
    o_hx, o_hy, o_hz = sxyz(o_hv.outputs["Value"])
    o_win = bnot(tcmp("GREATER_THAN", em("SUBTRACT", obz_x, obz_n), em("MULTIPLY", em("SUBTRACT", obx_x, obx_n), 1.8)))
    o_cat = tsw(tand(tand(tand(o_win, is_open), tand(tcmp("GREATER_EQUAL", o_frac, 0.05),
                                                     bnot(is_c(o_cat, 1)))),
                     tcmp("LESS_THAN", o_hx, hb_ph.outputs["Value"])), o_cat, 5.0)
    # ---- v2.17 WALL HOLES: at the heart of a damage patch (where the siding is
    # long gone) the wall itself is broken through - a ragged hole made of
    # small tilted plank-shaped cuts, its broken edges in the Interior
    # Material, the interior seen through it. Wall Holes 0 = none.
    p_hole = b.panel("Wall Holes", "Fit (v2.17): the cutting layer breaks holes through the wall at "
                     "the heart of the damage")
    b.sock("Wall Holes", "NodeSocketFloat", p_hole, 1.0, 0.0, 1.0, "FACTOR",
           "v2.20: the wall opens wherever the cladding's boards are gone (0 = never; 0.5 and up "
           "= every gap, below that only the deeper ones; needs Damage on the cladding and Cut "
           "Openings here)")
    # v2.20 the holes are the GAPS: every gap marker the cladding left (a
    # missing / fallen board, the broken-off part of one, a gone corner board
    # piece) cuts its box through the wall here - you look into the building
    # wherever the boards are gone, past their own broken ends. Wall Holes 0 =
    # no holes; from 0.5 up every gap opens, below that only the deeper ones.
    h_cut = tand(tand(gi.outputs["Cut Openings"], is_fit), tcmp("GREATER_THAN", gi.outputs["Wall Holes"], 0.001))
    is_ph = tcmp("GREATER_THAN", dnamed("vm_cutph", "FLOAT"), 0.5)
    h_ip = b.N("GeometryNodeInputPosition", random_loc()).outputs["Position"]
    h_deep = bor(tcmp("GREATER_EQUAL", gi.outputs["Wall Holes"], 0.5),
                 tcmp("GREATER_THAN", dmg_margin(h_ip), em("SUBTRACT", 0.3, gi.outputs["Wall Holes"])))
    h_pts = b.N("GeometryNodeInstancesToPoints", random_loc())
    b.L(c_inst, h_pts.inputs["Instances"])
    b.L(tand(h_cut, tand(is_ph, h_deep)), h_pts.inputs["Selection"])
    h_cnt = b.N("GeometryNodeAttributeDomainSize", random_loc())
    h_cnt.component = "POINTCLOUD"
    b.L(h_pts.outputs["Points"], h_cnt.inputs["Geometry"])
    has_hole = tcmp("GREATER_THAN", h_cnt.outputs["Point Count"], 0.5)
    h_cb = cube_.outputs["Mesh"]
    for nm_, val_ in (("vm_cutback", tsw(tcmp("LESS_THAN", cb_n, -0.5), 0.0, 1.0)), ("vm_cutter", 2.0)):
        st_ = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT", domain="FACE")
        b.L(h_cb, st_.inputs["Geometry"])
        st_.inputs["Name"].default_value = nm_
        if isinstance(val_, float):
            st_.inputs["Value"].default_value = val_
        else:
            b.L(val_, st_.inputs["Value"])
        h_cb = st_.outputs["Geometry"]
    h_iop = b.N("GeometryNodeInstanceOnPoints", random_loc())
    b.L(h_pts.outputs["Points"], h_iop.inputs["Points"])
    b.L(h_cb, h_iop.inputs["Instance"])
    b.L(dnamed("vm_kr", "QUATERNION"), h_iop.inputs["Rotation"])
    b.L(dnamed("vm_ks", "FLOAT_VECTOR"), h_iop.inputs["Scale"])
    # an opening's jamb lying inside a gap stood in a wall that is gone now:
    # it goes with the wall (no frame of jambs floating in the hole)
    def gap_at(pos_, dep_=None):
        # pos_ lies inside the footprint (wall plane) of the nearest gap box
        # (and, given dep_, within dep_ of it off the wall)
        sn_ = b.N("GeometryNodeSampleNearest", random_loc(), domain="POINT")
        b.L(h_pts.outputs["Points"], sn_.inputs["Geometry"])
        b.L(pos_, sn_.inputs["Sample Position"])

        def at_(field_, dt_):
            si_ = b.N("GeometryNodeSampleIndex", random_loc(), data_type=dt_, domain="POINT")
            b.L(h_pts.outputs["Points"], si_.inputs["Geometry"])
            b.L(field_, si_.inputs["Value"])
            b.L(sn_.outputs["Index"], si_.inputs["Index"])
            return si_.outputs["Value"]
        inv_ = b.N("FunctionNodeInvertRotation", random_loc())
        b.L(at_(dnamed("vm_kr", "QUATERNION"), "QUATERNION"), inv_.inputs["Rotation"])
        l_ = sxyz(rot(vmath("SUBTRACT", pos_, at_(b.N("GeometryNodeInputPosition", random_loc()).outputs["Position"],
                                                   "FLOAT_VECTOR")), inv_.outputs["Rotation"]))
        sz_ = sxyz(at_(dnamed("vm_ks", "FLOAT_VECTOR"), "FLOAT_VECTOR"))
        m_ = em("DIVIDE", 0.03, geo_f)
        in_ = tand(has_hole, tand(tcmp("LESS_THAN", em("ABSOLUTE", l_[0]), tm("MULTIPLY_ADD", sz_[0], 0.5, m_)),
                                  tcmp("LESS_THAN", em("ABSOLUTE", l_[2]), tm("MULTIPLY_ADD", sz_[2], 0.5, m_))))
        if dep_ is not None:
            in_ = tand(in_, tcmp("LESS_THAN", em("ABSOLUTE", l_[1]), tm("MULTIPLY_ADD", sz_[1], 0.5, dep_)))
        return in_
    # how much of an opening's surround (8 points 10 cm round its cut) is
    # gap - kept per opening on the cut points
    def ring_gap(ctr_, cu_, cup_, hu_, hz_):
        n_ = None
        for fu_, fz_ in ((-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0)):
            off_ = vmath("ADD", vmath("SCALE", cu_, em("MULTIPLY", em("ADD", hu_, em("DIVIDE", 0.1, geo_f)), float(fu_))),
                         vmath("SCALE", cup_, em("MULTIPLY", em("ADD", hz_, em("DIVIDE", 0.1, geo_f)), float(fz_))))
            x_ = tsw(gap_at(vmath("ADD", ctr_, off_)), 0.0, 1.0)
            n_ = x_ if n_ is None else em("ADD", n_, x_)
        return n_
    og_hu, _og_hy, og_hz = sxyz(dnamed("vm_chalf", "FLOAT_VECTOR"))
    og_st = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT", domain="POINT")
    b.L(o_cloud, og_st.inputs["Geometry"])
    og_st.inputs["Name"].default_value = "vm_ogap"
    b.L(ring_gap(dnamed("vm_cctr", "FLOAT_VECTOR"), dnamed("vm_cu", "FLOAT_VECTOR"), dnamed("vm_cup", "FLOAT_VECTOR"),
                 og_hu, og_hz), og_st.inputs["Value"])
    o_gcl = og_st.outputs["Geometry"]

    def og_near(pos_, mu_, mz_):
        # pos_ is round an opening that stands mostly in gap (within mu_ / mz_
        # of its cut sideways / up-down)
        sn_ = b.N("GeometryNodeSampleNearest", random_loc(), domain="POINT")
        b.L(o_gcl, sn_.inputs["Geometry"])
        b.L(pos_, sn_.inputs["Sample Position"])

        def at_(name_, dt_):
            si_ = b.N("GeometryNodeSampleIndex", random_loc(), data_type=dt_, domain="POINT")
            b.L(o_gcl, si_.inputs["Geometry"])
            b.L(dnamed(name_, dt_), si_.inputs["Value"])
            b.L(sn_.outputs["Index"], si_.inputs["Index"])
            return si_.outputs["Value"]
        rel_ = vmath("SUBTRACT", pos_, at_("vm_cctr", "FLOAT_VECTOR"))
        hu_, _hy, hz_ = sxyz(at_("vm_chalf", "FLOAT_VECTOR"))
        return tand(tand(has_open, tcmp("GREATER_EQUAL", at_("vm_ogap", "FLOAT"), 4.0)),
                    tand(tcmp("LESS_THAN", em("ABSOLUTE", vmath("DOT_PRODUCT", rel_, at_("vm_cu", "FLOAT_VECTOR"), out="Value")),
                              em("ADD", hu_, mu_)),
                         tcmp("LESS_THAN", em("ABSOLUTE", vmath("DOT_PRODUCT", rel_, at_("vm_cup", "FLOAT_VECTOR"), out="Value")),
                              em("ADD", hz_, mz_))))
    # an opening whose surround is mostly gap stood in a wall that is gone:
    # the door / window (frame, jambs and all) goes with it - the raw hole stays
    o_cat = tsw(tand(tand(h_cut, tcmp("GREATER_THAN", dnamed("vm_openmark", "FLOAT"), 0.5)),
                     og_near(o_ip, em("DIVIDE", 0.2, geo_f), em("DIVIDE", 0.2, geo_f))), o_cat, 1.0)
    hj_cut = dnamed("vm_cutter", "FLOAT")
    hj_in = tand(tand(tcmp("GREATER_THAN", hj_cut, 0.5), tcmp("LESS_THAN", hj_cut, 1.5)),
                 og_near(b.N("GeometryNodeInputPosition", random_loc()).outputs["Position"],
                         em("DIVIDE", 0.05, geo_f), em("DIVIDE", 0.05, geo_f)))
    for lk in list(b.ng.links):
        if lk.to_node == c_open and lk.to_socket.name == "Selection":
            b.ng.links.remove(lk)
    b.L(bor(tcmp("GREATER_THAN", dnamed("vm_cutback", "FLOAT"), 0.5), hj_in), c_open.inputs["Selection"])
    # the boxes overlap each other: as INSTANCES each one is its own boolean
    # operand (no costly Self Intersection pass over one realized mesh)
    b.L(h_iop.outputs["Instances"], c_bool.inputs["Mesh 2"])
    # the broken edges of a hole are the wall's own boards, not jambs
    is_hole = tcmp("GREATER_THAN", dnamed("vm_cutter", "FLOAT"), 1.5)
    for lk in list(b.ng.links):
        if lk.to_node == c_join and lk.from_socket == c_walls:
            b.ng.links.remove(lk)
    b.L(material_gate(b, c_walls, gi.outputs["Interior Material"], is_hole, random_loc()),
        c_join.inputs["Geometry"])
    # v2.23 DOOR CASING: two side boards and a head board (Jamb Material) on
    # the siding round every door this layer cut - they hide the cut board
    # ends and frame the leaf set back in its hole - and a sill from the leaf
    # out to the casing's face (over the floor's ends under the door). A door whose wall is gone
    # (it went with its wall above) takes its casing with it.
    cs_ucx = em("MULTIPLY", em("ADD", lx, hx), 0.5)
    cs_hu = em("ADD", em("MULTIPLY", em("SUBTRACT", hx, lx), 0.5), em("DIVIDE", DOOR_GAP, geo_f))
    cs_top = em("ADD", hz, em("DIVIDE", DOOR_GAP, geo_f))
    cs_w, cs_h = em("DIVIDE", CASING_W, geo_f), em("DIVIDE", CASING_HEAD, geo_f)
    cs_t = em("DIVIDE", CASING_T, geo_f)
    cs_ear = em("DIVIDE", 0.02, geo_f)
    cs_cube = b.N("GeometryNodeMeshCube", random_loc())
    cs_cube.inputs["Size"].default_value = (1.0, 1.0, 1.0)
    cs_back = em("DIVIDE", em("ADD", em("SUBTRACT", gi.outputs["Backing Offset"], gi.outputs["Embed"]), DOOR_RECESS), geo_f)
    cs_join = b.N("GeometryNodeJoinGeometry", random_loc())
    cs_ty, cs_tc = cs_t, em("MULTIPLY", cs_t, 0.5)
    for k_, (cx_, cz_, sx_, sz_, sy_, cy_) in enumerate((
            (em("SUBTRACT", cs_ucx, em("ADD", cs_hu, em("MULTIPLY", cs_w, 0.5))), em("MULTIPLY", em("ADD", lz, cs_top), 0.5),
             cs_w, em("SUBTRACT", cs_top, lz), cs_ty, cs_tc),
            (em("ADD", cs_ucx, em("ADD", cs_hu, em("MULTIPLY", cs_w, 0.5))), em("MULTIPLY", em("ADD", lz, cs_top), 0.5),
             cs_w, em("SUBTRACT", cs_top, lz), cs_ty, cs_tc),
            (cs_ucx, em("ADD", cs_top, em("MULTIPLY", cs_h, 0.5)),
             em("MULTIPLY", em("ADD", cs_hu, em("ADD", cs_w, cs_ear)), 2.0), cs_h, cs_ty, cs_tc),
            (cs_ucx, em("ADD", lz, em("DIVIDE", -0.005, geo_f)), em("MULTIPLY", cs_hu, 2.0), em("DIVIDE", 0.07, geo_f),
             em("ADD", cs_t, cs_back), em("MULTIPLY", em("SUBTRACT", cs_t, cs_back), 0.5)))):
        cs_mv = b.N("GeometryNodeSetPosition", random_loc())
        b.L(o_cloud, cs_mv.inputs["Geometry"])
        b.L(vmath("ADD", o_pos, rot(v3(cx_, cy_, cz_), o_rot)), cs_mv.inputs["Position"])
        cs_k = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT", domain="POINT")
        b.L(cs_mv.outputs["Geometry"], cs_k.inputs["Geometry"])
        cs_k.inputs["Name"].default_value = "vm_casing"
        cs_k.inputs["Value"].default_value = 1.0 if k_ < 2 else 2.0      # 2 = grain along the wall
        cs_iop = b.N("GeometryNodeInstanceOnPoints", random_loc())
        b.L(cs_k.outputs["Geometry"], cs_iop.inputs["Points"])
        b.L(o_dr, cs_iop.inputs["Selection"])
        b.L(cs_cube.outputs["Mesh"], cs_iop.inputs["Instance"])
        b.L(o_rot, cs_iop.inputs["Rotation"])
        b.L(v3(sx_, sy_, sz_), cs_iop.inputs["Scale"])
        b.L(cs_iop.outputs["Instances"], cs_join.inputs["Geometry"])
    cs_real = b.N("GeometryNodeRealizeInstances", random_loc())
    b.L(cs_join.outputs["Geometry"], cs_real.inputs["Geometry"])
    # wood UVs in meters, the grain up the side boards and along the head
    cs_head = tcmp("GREATER_THAN", dnamed("vm_casing", "FLOAT"), 1.5)
    cs_p = b.N("GeometryNodeInputPosition", random_loc()).outputs["Position"]
    cs_cu, cs_cup = dnamed("vm_cu", "FLOAT_VECTOR"), dnamed("vm_cup", "FLOAT_VECTOR")
    cs_uv = v3(em("MULTIPLY", vmath("DOT_PRODUCT", cs_p, vsw(cs_head, cs_cup, cs_cu), out="Value"), geo_f),
               em("MULTIPLY", em("ADD", vmath("DOT_PRODUCT", cs_p, vsw(cs_head, cs_cu, cs_cup), out="Value"),
                                 vmath("DOT_PRODUCT", cs_p, dnamed("vm_cn", "FLOAT_VECTOR"), out="Value")), geo_f), 0.0)
    cs_st = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT2", domain="CORNER")
    b.L(cs_real.outputs["Geometry"], cs_st.inputs["Geometry"])
    cs_st.inputs["Name"].default_value = "UVMap"
    b.L(cs_uv, cs_st.inputs["Value"])
    cs_gone = b.N("GeometryNodeDeleteGeometry", random_loc(), domain="FACE")
    b.L(cs_st.outputs["Geometry"], cs_gone.inputs["Geometry"])
    b.L(og_near(b.N("GeometryNodeInputPosition", random_loc()).outputs["Position"],
                em("DIVIDE", 0.25, geo_f), em("DIVIDE", 0.25, geo_f)), cs_gone.inputs["Selection"])
    cs_tr = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT", domain="FACE")
    b.L(cs_gone.outputs["Geometry"], cs_tr.inputs["Geometry"])
    cs_tr.inputs["Name"].default_value = "vm_trim"
    cs_tr.inputs["Value"].default_value = 1.0
    b.L(material_gate(b, cs_tr.outputs["Geometry"], gi.outputs["Jamb Material"], bor(cs_head, bnot(cs_head)),
                      random_loc()), c_join.inputs["Geometry"])
    # holes alone (no opening on the building) also need the cut
    for lk in list(b.ng.links):
        if lk.to_node == c_sw and lk.to_socket.name == "Switch":
            b.ng.links.remove(lk)
    b.L(tand(tand(gi.outputs["Cut Openings"], is_fit), bor(has_open, has_hole)), c_sw.inputs["Switch"])
    # the cutting layer used the markers up (an earlier, non-cutting layer
    # passes them on)
    o_chain = c_sw.outputs["Output"]
    h_fall = b.N("GeometryNodeDeleteGeometry", random_loc(), domain="INSTANCE")
    b.L(o_chain, h_fall.inputs["Geometry"])
    # ... and the short board ends left round such an opening (they were
    # nailed to boards that crossed it) fall with its wall
    hs_ib = b.N("GeometryNodeInputInstanceBounds", random_loc())
    hs_len = em("MULTIPLY", em("SUBTRACT", sxyz(hs_ib.outputs["Max"])[0], sxyz(hs_ib.outputs["Min"])[0]),
                sxyz(i_scl)[0])
    hs_stub = tand(tand(tcmp("LESS_THAN", dnamed("vm_openmark", "FLOAT"), 0.5), tcmp("LESS_THAN", hs_len, em("DIVIDE", 0.45, geo_f))),
                   og_near(b.N("GeometryNodeInputPosition", random_loc()).outputs["Position"],
                           em("DIVIDE", 0.5, geo_f), em("DIVIDE", 0.25, geo_f)))
    # v2.21 ... and a swinging board that crosses an opening: the cut would
    # take its middle and leave the rest hanging in the air
    def open_cut_at(pos_, mg_):
        sn_ = b.N("GeometryNodeSampleNearest", random_loc(), domain="POINT")
        b.L(o_cloud, sn_.inputs["Geometry"])
        b.L(pos_, sn_.inputs["Sample Position"])

        def at_(name_):
            si_ = b.N("GeometryNodeSampleIndex", random_loc(), data_type="FLOAT_VECTOR", domain="POINT")
            b.L(o_cloud, si_.inputs["Geometry"])
            b.L(dnamed(name_, "FLOAT_VECTOR"), si_.inputs["Value"])
            b.L(sn_.outputs["Index"], si_.inputs["Index"])
            return si_.outputs["Value"]
        rel_ = vmath("SUBTRACT", pos_, at_("vm_cctr"))
        hu_, _hy, hz_ = sxyz(at_("vm_chalf"))
        return tand(tand(has_open, tand(gi.outputs["Cut Openings"], is_fit)),
                    tand(tcmp("LESS_THAN", em("ABSOLUTE", vmath("DOT_PRODUCT", rel_, at_("vm_cu"), out="Value")),
                              em("ADD", hu_, mg_)),
                         tcmp("LESS_THAN", em("ABSOLUTE", vmath("DOT_PRODUCT", rel_, at_("vm_cup"), out="Value")),
                              em("ADD", hz_, mg_))))
    sw_k = dnamed("vm_ekept", "FLOAT_VECTOR")
    sw_far = vsw(tcmp("LESS_THAN", vmath("DISTANCE", sw_k, dnamed("vm_elo", "FLOAT_VECTOR"), out="Value"),
                      em("DIVIDE", 0.01, geo_f)),
                 dnamed("vm_elo", "FLOAT_VECTOR"), dnamed("vm_ehi", "FLOAT_VECTOR"))
    sw_x = None
    for f_ in (0.05, 0.2, 0.35, 0.5, 0.65):
        x_ = open_cut_at(vmath("ADD", sw_k, vmath("SCALE", vmath("SUBTRACT", sw_far, sw_k), f_)),
                         em("DIVIDE", 0.02, geo_f))
        sw_x = x_ if sw_x is None else bor(sw_x, x_)
    hs_swing = tand(tand(tcmp("GREATER_THAN", dnamed("vm_dcat", "FLOAT"), 2.5),
                         tcmp("LESS_THAN", dnamed("vm_dcat", "FLOAT"), 3.5)),
                    tand(tcmp("LESS_THAN", dnamed("vm_openmark", "FLOAT"), 0.5), sw_x))
    # v2.21 ... and the boards that crossed such an opening (ripped out with
    # its wall): the opening's cut took their middle, the gaps their ends -
    # what is left would float in the hole
    hs_cross = tand(tcmp("LESS_THAN", dnamed("vm_openmark", "FLOAT"), 0.5),
                    og_near(b.N("GeometryNodeInputPosition", random_loc()).outputs["Position"],
                            em("SUBTRACT", em("MULTIPLY", hs_len, 0.5), em("DIVIDE", 0.03, geo_f)), 0.0))
    b.L(tand(tand(gi.outputs["Cut Openings"], is_fit),
             bor(bor(is_ph, hs_swing), tand(has_hole, bor(hs_stub, hs_cross)))),
        h_fall.inputs["Selection"])
    # (the wall behind a board this layer drops is cut open too - the cut
    # boxes of the boards' own footprints join the gap boxes; a swinging
    # board's gap the cladding cut already)
    hx_lo = vmul(hs_ib.outputs["Min"], i_scl)
    hx_hi = vmul(hs_ib.outputs["Max"], i_scl)
    hx_lx, hx_ly, hx_lz = sxyz(hx_lo)
    hx_hx, _hx_hy, hx_hz = sxyz(hx_hi)
    hx_ctr = vmath("ADD", vmath("ADD", b.N("GeometryNodeInputPosition", random_loc()).outputs["Position"],
                                rot(v3(em("MULTIPLY", em("ADD", hx_lx, hx_hx), 0.5), hx_ly,
                                       em("MULTIPLY", em("ADD", hx_lz, hx_hz), 0.5)), i_rot)),
                   vmath("SCALE", rot(v3(0.0, 1.0, 0.0), i_rot), em("DIVIDE", 0.01, geo_f)))
    hx_chain = c_inst
    for nm_, dt_, val_ in (("vm_kr", "QUATERNION", i_rot),
                           ("vm_ks", "FLOAT_VECTOR", v3(em("ADD", em("SUBTRACT", hx_hx, hx_lx), em("DIVIDE", 0.02, geo_f)),
                                                        em("DIVIDE", 0.08, geo_f),
                                                        em("ADD", em("SUBTRACT", hx_hz, hx_lz), em("DIVIDE", 0.01, geo_f))))):
        st_ = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type=dt_, domain="INSTANCE")
        b.L(hx_chain, st_.inputs["Geometry"])
        st_.inputs["Name"].default_value = nm_
        b.L(val_, st_.inputs["Value"])
        hx_chain = st_.outputs["Geometry"]
    hx_pts = b.N("GeometryNodeInstancesToPoints", random_loc())
    b.L(hx_chain, hx_pts.inputs["Instances"])
    b.L(tand(tand(h_cut, bnot(is_ph)),
             tand(tcmp("LESS_THAN", dnamed("vm_openmark", "FLOAT"), 0.5), tand(has_hole, bor(hs_stub, hs_cross)))),
        hx_pts.inputs["Selection"])
    b.L(hx_ctr, hx_pts.inputs["Position"])
    hx_join = b.N("GeometryNodeJoinGeometry", random_loc())
    b.L(h_pts.outputs["Points"], hx_join.inputs["Geometry"])
    b.L(hx_pts.outputs["Points"], hx_join.inputs["Geometry"])
    for lk in list(b.ng.links):
        if lk.to_node == h_iop and lk.to_socket.name == "Points":
            b.ng.links.remove(lk)
    b.L(hx_join.outputs["Geometry"], h_iop.inputs["Points"])
    o_chain = h_fall.outputs["Geometry"]
    # v2.21 under every roof hole: the roof's frame - two rafters (on a
    # 60 cm grid along the eaves, so neighbouring holes share them) running
    # down the slope under the deck, and battens across them (25 cm grid)
    # just under the shakes - in the Interior Material (wood)
    rf_p = b.N("GeometryNodeDeleteGeometry", random_loc(), domain="POINT")
    b.L(h_pts.outputs["Points"], rf_p.inputs["Geometry"])
    b.L(tcmp("LESS_THAN", dnamed("vm_kroof", "FLOAT"), 0.5), rf_p.inputs["Selection"])
    rf_kr = dnamed("vm_kr", "QUATERNION")
    rf_u, rf_n, rf_s = (rot(v3(*a_), rf_kr) for a_ in ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)))
    rf_kb = dnamed("vm_kb", "FLOAT_VECTOR")
    rf_sx, _rf_sy, rf_sz = sxyz(dnamed("vm_ks", "FLOAT_VECTOR"))
    rf_cube = b.N("GeometryNodeMeshCube", random_loc())
    rf_cube.inputs["Size"].default_value = (1.0, 1.0, 1.0)
    rf_true = b.N("FunctionNodeInputBool", random_loc())
    rf_true.boolean = True
    rf_mesh = material_gate(b, rf_cube.outputs["Mesh"], gi.outputs["Interior Material"],
                            rf_true.outputs["Boolean"], random_loc())

    def rf_frame(n_, axis_, grid_, start_, under_, size_, half_):
        # (only the pieces whose grid line crosses the hole; each runs just
        # past the hole - beyond it they would poke out of the roof's edges)
        du_ = b.N("GeometryNodeDuplicateElements", random_loc(), domain="POINT")
        b.L(rf_p.outputs["Geometry"], du_.inputs["Geometry"])
        du_.inputs["Amount"].default_value = n_
        g_ = em("DIVIDE", grid_, geo_f)
        at_ = vmath("DOT_PRODUCT", rf_kb, axis_, out="Value")
        off_ = em("SUBTRACT", em("MULTIPLY", em("ADD", em("FLOOR", em("DIVIDE", at_, g_)),
                                             em("ADD", du_.outputs["Duplicate Index"], start_)), g_), at_)
        pos_ = vmath("ADD", vmath("ADD", rf_kb, vmath("SCALE", axis_, off_)),
                     vmath("SCALE", rf_n, em("DIVIDE", -under_, geo_f)))
        dl_ = b.N("GeometryNodeDeleteGeometry", random_loc(), domain="POINT")
        b.L(du_.outputs["Geometry"], dl_.inputs["Geometry"])
        b.L(tcmp("GREATER_THAN", em("ABSOLUTE", off_), half_), dl_.inputs["Selection"])
        iop_ = b.N("GeometryNodeInstanceOnPoints", random_loc())
        b.L(dl_.outputs["Geometry"], iop_.inputs["Points"])
        b.L(rf_mesh, iop_.inputs["Instance"])
        b.L(rf_kr, iop_.inputs["Rotation"])
        b.L(size_, iop_.inputs["Scale"])
        sp_ = b.N("GeometryNodeSetPosition", random_loc())
        b.L(iop_.outputs["Instances"], sp_.inputs["Geometry"])
        b.L(pos_, sp_.inputs["Position"])
        return sp_.outputs["Geometry"]
    rf_geo = b.N("GeometryNodeJoinGeometry", random_loc())
    b.L(rf_frame(2, rf_u, 0.6, 0.0, 0.08,
                 v3(em("DIVIDE", 0.05, geo_f), em("DIVIDE", 0.11, geo_f), em("ADD", rf_sz, em("DIVIDE", 0.08, geo_f))),
                 em("ADD", em("MULTIPLY", rf_sx, 0.5), em("DIVIDE", 0.02, geo_f))),
        rf_geo.inputs["Geometry"])
    b.L(rf_frame(3, rf_s, 0.25, -1.0, 0.017,
                 v3(em("ADD", rf_sx, em("DIVIDE", 0.08, geo_f)), em("DIVIDE", 0.025, geo_f), em("DIVIDE", 0.06, geo_f)),
                 em("ADD", em("MULTIPLY", rf_sz, 0.5), em("DIVIDE", 0.02, geo_f))),
        rf_geo.inputs["Geometry"])
    for nm_, val_ in (("vm_ocat", o_cat), ("vm_ofrac", o_frac)):
        st_ = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT", domain="INSTANCE")
        b.L(o_chain, st_.inputs["Geometry"])
        st_.inputs["Name"].default_value = nm_
        b.L(val_, st_.inputs["Value"])
        o_chain = st_.outputs["Geometry"]
    ocat = dnamed("vm_ocat", "FLOAT")
    o_del = b.N("GeometryNodeDeleteGeometry", random_loc(), domain="INSTANCE")
    b.L(o_chain, o_del.inputs["Geometry"])
    b.L(is_c(ocat, 1), o_del.inputs["Selection"])
    # door (tall opening): swings open on a side hinge; window: drops about a
    # top corner, in the wall plane, pulled a hair off the wall
    o_door = tcmp("GREATER_THAN", em("SUBTRACT", obz_x, obz_n),
                  em("MULTIPLY", em("SUBTRACT", obx_x, obx_n), 1.8))
    o_left = tcmp("LESS_THAN", o_ry, 0.5)                      # hinge / nail at min X
    o_sg = tsw(o_left, -1.0, 1.0)
    o_hang = is_c(ocat, 3)
    o_a = tsw(o_hang, em("MULTIPLY", gi.outputs["Max Tilt"], tm("MULTIPLY_ADD", o_rz, 0.4, 0.35)),
              tsw(o_door, tm("MULTIPLY_ADD", o_rz, 0.9, 0.5), tm("MULTIPLY_ADD", o_rz, 0.35, 0.2)))
    o_a = em("MULTIPLY", o_a, o_sg)
    ob_ib2 = b.N("GeometryNodeInputInstanceBounds", random_loc())
    pb_n_x, pb_n_y, pb_n_z = sxyz(ob_ib2.outputs["Min"])
    pb_x_x, pb_x_y, pb_x_z = sxyz(ob_ib2.outputs["Max"])
    o_px = tsw(o_left, pb_x_x, pb_n_x)
    o_eul = b.N("FunctionNodeEulerToRotation", random_loc())
    b.L(vsw(tand(o_door, o_hang), v3(0.0, o_a, 0.0), v3(0.0, 0.0, o_a)), o_eul.inputs["Euler"])
    o_rot = b.N("GeometryNodeRotateInstances", random_loc())
    b.L(o_del.outputs["Geometry"], o_rot.inputs["Instances"])
    b.L(bor(o_hang, is_c(ocat, 4)), o_rot.inputs["Selection"])
    b.L(o_eul.outputs["Rotation"], o_rot.inputs["Rotation"])
    b.L(v3(o_px, 0.0, pb_x_z), o_rot.inputs["Pivot Point"])          # top corner / hinge side
    o_rot.inputs["Local Space"].default_value = True
    o_off = b.N("GeometryNodeTranslateInstances", random_loc())
    b.L(o_rot.outputs["Instances"], o_off.inputs["Instances"])
    b.L(tand(o_hang, bnot(o_door)), o_off.inputs["Selection"])
    o_off.inputs["Translation"].default_value = (0.0, 0.012, 0.0)
    o_off.inputs["Local Space"].default_value = True

    # ---- v2.18 GLASS: the cutting layer glazes every window it cut - one pane
    # just in front of the window's back, the size of the hole. The pane
    # carries how broken it is (vm_gbrk, read by the glass material as an
    # Instancer attribute): hanging windows are mostly smashed, loose ones
    # half, intact ones only on the Broken Panes share (Damage on).
    p_gl = b.panel("Glass", "Fit (v2.18): glaze the windows this layer cut, broken in damage")
    b.sock("Window Glass", "NodeSocketBool", p_gl, False,
           desc="Fit (v2.18): a glass pane in every window cut by this layer (Cut Openings on)")
    b.sock("Glass Material", "NodeSocketMaterial", p_gl, None,
           desc="Glass: the pane material (VM_WindowGlass breaks by the pane's vm_gbrk)")
    b.sock("Broken Panes", "NodeSocketFloat", p_gl, 0.2, 0.0, 1.0, "FACTOR",
           "Glass: share of the undamaged windows that still have some broken panes (Damage on)")
    g_on = tand(tand(gi.outputs["Window Glass"], tand(gi.outputs["Cut Openings"], is_fit)), has_open)
    g_win = tand(g_on, tand(tcmp("GREATER_THAN", dnamed("vm_openmark", "FLOAT"), 0.5), bnot(o_door)))
    g_ip = b.N("GeometryNodeInputPosition", random_loc()).outputs["Position"]
    g_px, g_py, g_pz = sxyz(g_ip)
    g_rv = b.N("FunctionNodeRandomValue", random_loc(), data_type="FLOAT_VECTOR")
    g_rv.inputs["Min"].default_value = (0.0, 0.0, 0.0)
    g_rv.inputs["Max"].default_value = (1.0, 1.0, 1.0)
    # keyed on where the window is, not on its index (damage deletes instances)
    b.L(em("FLOOR", tm("MULTIPLY_ADD", g_px, 731.0, tm("MULTIPLY_ADD", g_py, 1237.0,
                                                       em("MULTIPLY", g_pz, 389.0)))), g_rv.inputs["ID"])
    b.L(seed_node(b, d_seed, 503), g_rv.inputs["Seed"])
    g_rx, g_ry, g_rz = sxyz(g_rv.outputs["Value"])
    g_brk = tsw(gi.outputs["Damage"], 0.0,
                tsw(is_c(ocat, 5), tsw(is_c(ocat, 3),
                    tsw(is_c(ocat, 4),
                        tsw(tcmp("LESS_THAN", g_rx, gi.outputs["Broken Panes"]), 0.0,
                            tm("MULTIPLY_ADD", g_ry, 0.25, 0.12)),
                        tm("MULTIPLY_ADD", g_ry, 0.3, 0.4)),
                    tm("MULTIPLY_ADD", g_ry, 0.2, 0.75)), tm("MULTIPLY_ADD", g_ry, 0.1, 0.88)))
    g_ib = b.N("GeometryNodeInputInstanceBounds", random_loc())
    g_lo = vmul(g_ib.outputs["Min"], i_scl)
    g_hi = vmul(g_ib.outputs["Max"], i_scl)
    glx, gly, glz = sxyz(g_lo)
    ghx, _ghy, ghz = sxyz(g_hi)
    g_chain = o_off.outputs["Instances"]
    for nm_, dt_, val_ in (("vm_grot", "QUATERNION", i_rot),
                           ("vm_gctr", "FLOAT_VECTOR", vmath("ADD", g_ip, rot(v3(
                               em("MULTIPLY", em("ADD", glx, ghx), 0.5),
                               em("ADD", gly, em("DIVIDE", 0.004, geo_f)),
                               em("MULTIPLY", em("ADD", glz, ghz), 0.5)), i_rot))),
                           ("vm_gsz", "FLOAT_VECTOR", v3(
                               em("MAXIMUM", em("SUBTRACT", em("SUBTRACT", ghx, glx), em("MULTIPLY", ins_l, 2.0)),
                                  0.01),
                               1.0,
                               em("MAXIMUM", em("SUBTRACT", em("SUBTRACT", ghz, glz), em("MULTIPLY", ins_l, 2.0)),
                                  0.01))),
                           ("vm_gbrk", "FLOAT", g_brk), ("vm_gseed", "FLOAT", g_rz)):
        st_ = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type=dt_, domain="INSTANCE")
        b.L(g_chain, st_.inputs["Geometry"])
        st_.inputs["Name"].default_value = nm_
        b.L(val_, st_.inputs["Value"])
        g_chain = st_.outputs["Geometry"]
    g_pts = b.N("GeometryNodeInstancesToPoints", random_loc())
    b.L(g_chain, g_pts.inputs["Instances"])
    b.L(g_win, g_pts.inputs["Selection"])
    g_mv = b.N("GeometryNodeSetPosition", random_loc())
    b.L(g_pts.outputs["Points"], g_mv.inputs["Geometry"])
    b.L(dnamed("vm_gctr", "FLOAT_VECTOR"), g_mv.inputs["Position"])
    # the pane: a unit quad in the window's XZ plane facing +Y (outward), UVs 0-1
    g_grid = b.N("GeometryNodeMeshGrid", random_loc())
    g_grid.inputs["Size X"].default_value = 1.0
    g_grid.inputs["Size Y"].default_value = 1.0
    g_grid.inputs["Vertices X"].default_value = 2
    g_grid.inputs["Vertices Y"].default_value = 2
    g_uv = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT2", domain="CORNER")
    b.L(g_grid.outputs["Mesh"], g_uv.inputs["Geometry"])
    g_uv.inputs["Name"].default_value = "UVMap"
    b.L(g_grid.outputs["UV Map"], g_uv.inputs["Value"])
    g_tf = b.N("GeometryNodeTransform", random_loc())
    b.L(g_uv.outputs["Geometry"], g_tf.inputs["Geometry"])
    g_tf.inputs["Rotation"].default_value = (-1.5707963, 0.0, 0.0)
    g_mat = b.N("GeometryNodeSetMaterial", random_loc())
    b.L(g_tf.outputs["Geometry"], g_mat.inputs["Geometry"])
    b.L(gi.outputs["Glass Material"], g_mat.inputs["Material"])
    g_iop = b.N("GeometryNodeInstanceOnPoints", random_loc())
    b.L(g_mv.outputs["Geometry"], g_iop.inputs["Points"])
    b.L(g_mat.outputs["Geometry"], g_iop.inputs["Instance"])
    b.L(dnamed("vm_grot", "QUATERNION"), g_iop.inputs["Rotation"])
    b.L(dnamed("vm_gsz", "FLOAT_VECTOR"), g_iop.inputs["Scale"])
    # world size of the pane (the material lays its shards in meters)
    g_ws = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT_VECTOR", domain="INSTANCE")
    b.L(g_iop.outputs["Instances"], g_ws.inputs["Geometry"])
    g_ws.inputs["Name"].default_value = "vm_gsize"
    b.L(vmath("SCALE", dnamed("vm_gsz", "FLOAT_VECTOR"), geo_f), g_ws.inputs["Value"])
    g_chain2 = g_ws.outputs["Geometry"]
    for nm_ in ("vm_gbrk", "vm_gseed"):
        st_ = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT", domain="INSTANCE")
        b.L(g_chain2, st_.inputs["Geometry"])
        st_.inputs["Name"].default_value = nm_
        b.L(dnamed(nm_, "FLOAT"), st_.inputs["Value"])
        g_chain2 = st_.outputs["Geometry"]
    g_join = b.N("GeometryNodeJoinGeometry", random_loc())
    # v2.21 PARTLY BROKEN windows: realized, and the inner parts (sash bars,
    # louvre slats, muntins, glass) past a slanted break line through the
    # middle of the unit are gone - whole parts beyond it, the ones crossing it
    # snapped off on a jagged edge - while the outer frame always stays
    hb_sep = b.N("GeometryNodeSeparateGeometry", random_loc(), domain="INSTANCE")
    b.L(o_off.outputs["Instances"], hb_sep.inputs["Geometry"])
    b.L(tand(is_c(ocat, 5), tcmp("GREATER_THAN", dnamed("vm_openmark", "FLOAT"), 0.5)), hb_sep.inputs["Selection"])
    # the break line, per window, in its own frame: just off the centre toward
    # the chosen corner (so roughly half of the unit goes), slanted 20-60 deg
    hb_ib = b.N("GeometryNodeInputInstanceBounds", random_loc())
    hb_lo = vmul(hb_ib.outputs["Min"], i_scl)
    hb_hi = vmul(hb_ib.outputs["Max"], i_scl)
    hb_lx, _hb_ly, hb_lz = sxyz(hb_lo)
    hb_hx, _hb_hy, hb_hz = sxyz(hb_hi)
    hb_hw = em("MULTIPLY", em("SUBTRACT", hb_hx, hb_lx), 0.5)
    hb_hh = em("MULTIPLY", em("SUBTRACT", hb_hz, hb_lz), 0.5)
    hb_sx = tsw(tcmp("LESS_THAN", o_hy, 0.5), -1.0, 1.0)          # which corner
    hb_sz = tsw(tcmp("LESS_THAN", o_hz, 0.3), 1.0, -1.0)          # mostly a top corner
    hb_f = tm("MULTIPLY_ADD", tm("FRACT", em("MULTIPLY", o_hy, 7.31)), 0.2, 0.05)
    hb_o = vmath("ADD", b.N("GeometryNodeInputPosition", random_loc()).outputs["Position"],
                 rot(v3(em("MULTIPLY", em("ADD", hb_lx, hb_hx), 0.5), 0.0,
                        em("MULTIPLY", em("ADD", hb_lz, hb_hz), 0.5)), i_rot))
    hb_c = vmath("ADD", hb_o, rot(v3(em("MULTIPLY", em("MULTIPLY", hb_hw, hb_sx), hb_f), 0.0,
                                     em("MULTIPLY", em("MULTIPLY", hb_hh, hb_sz), hb_f)), i_rot))
    hb_ang = tm("MULTIPLY_ADD", tm("FRACT", em("MULTIPLY", o_hz, 5.17)), 0.7, 0.35)
    hb_d = rot(v3(em("MULTIPLY", hb_sx, em("COSINE", hb_ang)), 0.0, em("MULTIPLY", hb_sz, em("SINE", hb_ang))), i_rot)
    hb_u = rot(v3(1.0, 0.0, 0.0), i_rot)
    hb_h = v3(hb_hw, 0.0, hb_hh)
    # (Separate Geometry hands the wall mesh to BOTH outputs: only the
    # instances of the selection go on)
    hb_only = b.N("GeometryNodeSeparateComponents", random_loc())
    b.L(hb_sep.outputs["Selection"], hb_only.inputs["Geometry"])
    hb_chain = hb_only.outputs["Instances"]
    for nm_, val_ in (("vm_hbc", hb_c), ("vm_hbd", hb_d), ("vm_hbo", hb_o), ("vm_hbu", hb_u), ("vm_hbh", hb_h)):
        st_ = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT_VECTOR", domain="INSTANCE")
        b.L(hb_chain, st_.inputs["Geometry"])
        st_.inputs["Name"].default_value = nm_
        b.L(val_, st_.inputs["Value"])
        hb_chain = st_.outputs["Geometry"]
    hb_real = b.N("GeometryNodeRealizeInstances", random_loc())
    b.L(hb_chain, hb_real.inputs["Geometry"])
    # each loose part's centre: the mean of its points
    hb_isl = b.N("GeometryNodeInputMeshIsland", random_loc())
    hb_acc = b.N("GeometryNodeAccumulateField", random_loc(), data_type="FLOAT_VECTOR", domain="POINT")
    b.L(b.N("GeometryNodeInputPosition", random_loc()).outputs["Position"], hb_acc.inputs["Value"])
    b.L(hb_isl.outputs["Island Index"], hb_acc.inputs["Group ID"])
    hb_cnt = b.N("GeometryNodeAccumulateField", random_loc(), data_type="FLOAT", domain="POINT")
    hb_cnt.inputs["Value"].default_value = 1.0
    b.L(hb_isl.outputs["Island Index"], hb_cnt.inputs["Group ID"])
    hb_ctr = vmath("SCALE", hb_acc.outputs["Total"], em("DIVIDE", 1.0, em("MAXIMUM", hb_cnt.outputs["Total"], 1.0)))
    hb_hwr, _hb_0, hb_hhr = sxyz(dnamed("vm_hbh", "FLOAT_VECTOR"))
    def hb_local(pos_):
        """(|across|, |up|) of a point from the window centre, in its frame."""
        rel_ = vmath("SUBTRACT", pos_, dnamed("vm_hbo", "FLOAT_VECTOR"))
        ax_ = em("ABSOLUTE", vmath("DOT_PRODUCT", rel_, dnamed("vm_hbu", "FLOAT_VECTOR"), out="Value"))
        _x, _y, rz_ = sxyz(rel_)
        return ax_, em("ABSOLUTE", rz_)
    def hb_past(pos_):
        return vmath("DOT_PRODUCT", vmath("SUBTRACT", pos_, dnamed("vm_hbc", "FLOAT_VECTOR")),
                     dnamed("vm_hbd", "FLOAT_VECTOR"), out="Value")
    # a part centred within 4.5 cm of the outline is the frame: it stays
    cx_, cz_ = hb_local(hb_ctr)
    hb_frame = bor(tcmp("GREATER_THAN", cx_, em("SUBTRACT", hb_hwr, 0.045)),
                   tcmp("GREATER_THAN", cz_, em("SUBTRACT", hb_hhr, 0.045)))
    # the jagged snap line: the break line wobbled by a fine noise
    hb_nz = b.N("ShaderNodeTexNoise", random_loc())
    b.L(b.N("GeometryNodeInputPosition", random_loc()).outputs["Position"], hb_nz.inputs["Vector"])
    hb_nz.inputs["Scale"].default_value = 14.0
    hb_nz.inputs["Detail"].default_value = 3.0
    hb_pos = b.N("GeometryNodeInputPosition", random_loc()).outputs["Position"]
    px_, pz_ = hb_local(hb_pos)
    hb_inner = tand(tcmp("LESS_THAN", px_, em("SUBTRACT", hb_hwr, 0.06)),
                    tcmp("LESS_THAN", pz_, em("SUBTRACT", hb_hhr, 0.06)))
    hb_snap = tand(hb_inner, tcmp("GREATER_THAN", tm("MULTIPLY_ADD", em("SUBTRACT", hb_nz.outputs["Fac"], 0.5), 0.12,
                                                     hb_past(hb_pos)), 0.0))
    hb_nf = b.N("FunctionNodeBooleanMath", random_loc(), operation="NOT")
    b.L(hb_frame, hb_nf.inputs[0])
    hb_gone = tand(hb_nf.outputs["Boolean"], bor(tcmp("GREATER_THAN", hb_past(hb_ctr), 0.0), hb_snap))
    hb_del = b.N("GeometryNodeDeleteGeometry", random_loc(), domain="POINT")
    b.L(hb_real.outputs["Geometry"], hb_del.inputs["Geometry"])
    b.L(hb_gone, hb_del.inputs["Selection"])
    b.L(hb_sep.outputs["Inverted"], g_join.inputs["Geometry"])
    b.L(hb_del.outputs["Geometry"], g_join.inputs["Geometry"])
    b.L(g_chain2, g_join.inputs["Geometry"])
    b.L(g_join.outputs["Geometry"], go.inputs["Geometry"])
    rf_rl = b.N("GeometryNodeRealizeInstances", random_loc())
    b.L(rf_geo.outputs["Geometry"], rf_rl.inputs["Geometry"])
    rf_tag = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type="FLOAT", domain="FACE")
    b.L(rf_rl.outputs["Geometry"], rf_tag.inputs["Geometry"])
    rf_tag.inputs["Name"].default_value = "vm_rafter"
    rf_tag.inputs["Value"].default_value = 1.0
    b.L(rf_tag.outputs["Geometry"], g_join.inputs["Geometry"])
    if os.environ.get("VM_DBG_OCLOUD"):
        b.L(o_cloud, g_join.inputs["Geometry"])

    # ---- v2.19 VINES -> v2.20 IVY (the user's 'realistic ivy like the GN ivy
    # generators - grown along the house'). Every plant GROWS: a repeat zone
    # walks its tips over the building one step at a time. Each step leans up
    # (to the light), keeps some momentum, wanders, and is pressed back onto
    # the nearest surface - so it creeps round corners, under the eaves and on
    # over the roof. It steers sideways round any door / window this layer
    # cut, branches now and then (side shoots branch again), and stops at the
    # Vine Height or by chance. Plants gather at the wall corners. The trail
    # becomes tapering stems; lobed ivy leaves (real geometry) crowd along it,
    # facing out and hanging their tips, bigger on the old wood.
    p_vn = b.panel("Vines", "Any mode (v2.20): ivy that grows over the building from the ground")
    b.sock("Vines", "NodeSocketBool", p_vn, False,
           desc="v2.20: grow ivy over the building (use it on ONE layer - the add-on's Windows layer)")
    b.sock("Vine Count", "NodeSocketInt", p_vn, 8, 0, 500,
           desc="Vines: about how many plants (they gather at the wall corners)")
    b.sock("Vine Height", "NodeSocketFloat", p_vn, 4.0, 0.1, 100.0, "DISTANCE",
           "Vines: how high the tallest climb (world m) - past the eaves they creep onto the roof")
    b.sock("Vine Branches", "NodeSocketInt", p_vn, 9, 0, 50,
           desc="Vines: side shoots per plant (each may branch again)")
    b.sock("Leaf Density", "NodeSocketFloat", p_vn, 0.9, 0.0, 1.0, "FACTOR",
           "Vines: how leafy (share of the leaf places along the stems that carry a leaf)")
    b.sock("Vine Seed", "NodeSocketInt", p_vn, 0, desc="Vines: another set of plants")
    b.sock("Stem Material", "NodeSocketMaterial", p_vn, None, desc="Vines: the stems")
    b.sock("Leaf Material", "NodeSocketMaterial", p_vn, None,
           desc="Vines: the leaves (lobed ivy leaves; UVs in leaf space, base at 0,0, tip at 0,1)")
    b.sock("Leaf Size", "NodeSocketFloat", p_vn, 0.075, 0.005, 1.0, "DISTANCE",
           "Vines: leaf length (world m)")
    b.sock("Roof Holes", "NodeSocketFloat", p_dmg, 0.5, 0.0, 1.0, "FACTOR",
           "Damage (v2.21) on a roof: where the damage is deepest the missing shakes leave a HOLE "
           "through the roof (rafters and battens under it, the attic below) - 0 = none, 1 = under "
           "every missing shake. Needs Cut Openings on the cutting layer (the add-on's Windows layer)")
    b.sock("Half Broken", "NodeSocketFloat", p_dmg, 0.45, 0.0, 1.0, "FACTOR",
           "Openings (v2.21): share of the damaged windows that stay in place but are PARTLY "
           "broken - a jagged part of the frame and sash broken away, the glass smashed")
    b.L(gi.outputs["Roof Holes"], rh_ph.inputs[0])
    b.L(gi.outputs["Half Broken"], hb_ph.inputs[0])
    v_seed = gi.outputs["Vine Seed"]

    def vnorm(v_):
        return vmath("NORMALIZE", v_, v_)

    def v_rand(off_, id_=None, seed_=None):
        rv_ = b.N("FunctionNodeRandomValue", random_loc(), data_type="FLOAT_VECTOR")
        rv_.inputs["Min"].default_value = (0.0, 0.0, 0.0)
        rv_.inputs["Max"].default_value = (1.0, 1.0, 1.0)
        if id_ is not None:
            b.L(id_, rv_.inputs["ID"])
        b.L(seed_node(b, v_seed, off_) if seed_ is None else seed_, rv_.inputs["Seed"])
        return sxyz(rv_.outputs["Value"])

    def v_store(geo_, items_, domain_="POINT"):
        for nm_, dt_, val_ in items_:
            st_ = b.N("GeometryNodeStoreNamedAttribute", random_loc(), data_type=dt_, domain=domain_)
            b.L(geo_, st_.inputs["Geometry"])
            st_.inputs["Name"].default_value = nm_
            if isinstance(val_, (int, float)):
                st_.inputs["Value"].default_value = val_
            else:
                b.L(val_, st_.inputs["Value"])
            geo_ = st_.outputs["Geometry"]
        return geo_
    v_up = v3(0.0, 0.0, 1.0)
    v_off = em("DIVIDE", 0.055, geo_f)                   # stems stand in front of the cladding
    v_step = em("DIVIDE", 0.065, geo_f)
    v_base = bb_sep.outputs["Z"]
    # the surface they creep over: the building's own mesh (walls, roof) and
    # its trim boards (they climb over a corner board, never through it), not
    # the interior; face normals kept for the snapping
    v_srf = b.N("GeometryNodeDeleteGeometry", random_loc(), domain="FACE")
    b.L(mesh_only, v_srf.inputs["Geometry"])
    b.L(tcmp("GREATER_THAN", dnamed("vm_inner", "FLOAT"), 0.5), v_srf.inputs["Selection"])
    v_host = v_store(v_srf.outputs["Geometry"],
                     (("vm_vn", "FLOAT_VECTOR", b.N("GeometryNodeInputNormal", random_loc()).outputs["Normal"]),),
                     "FACE")
    # the outside wall corners (vertical convex edges), flattened to z = 0
    v_ev = b.N("GeometryNodeInputMeshEdgeVertices", random_loc())
    v_ed = vmath("SUBTRACT", v_ev.outputs["Position 2"], v_ev.outputs["Position 1"])
    v_ea = b.N("GeometryNodeInputMeshEdgeAngle", random_loc())
    v_cor = b.N("GeometryNodeMeshToPoints", random_loc())
    v_cor.mode = "EDGES"
    b.L(v_srf.outputs["Geometry"], v_cor.inputs["Mesh"])
    b.L(tand(tcmp("GREATER_THAN", em("ABSOLUTE", sxyz(v_ed)[2]),
                  em("MULTIPLY", vmath("LENGTH", v_ed, v_ed, out="Value"), 0.9)),
             tcmp("GREATER_THAN", v_ea.outputs["Signed Angle"], 0.3)), v_cor.inputs["Selection"])
    v_cpx, v_cpy, _v_cpz = sxyz(b.N("GeometryNodeInputPosition", random_loc()).outputs["Position"])
    v_corf = b.N("GeometryNodeSetPosition", random_loc())
    b.L(v_cor.outputs["Points"], v_corf.inputs["Geometry"])
    b.L(v3(v_cpx, v_cpy, 0.0), v_corf.inputs["Position"])
    v_ccn = b.N("GeometryNodeAttributeDomainSize", random_loc())
    v_ccn.component = "POINTCLOUD"
    b.L(v_cor.outputs["Points"], v_ccn.inputs["Geometry"])
    # candidate roots on the walls; kept by chance, far likelier near a corner
    v_nz = sxyz(b.N("GeometryNodeInputNormal", random_loc()).outputs["Normal"])[2]
    v_dist = b.N("GeometryNodeDistributePointsOnFaces", random_loc(), distribute_method="RANDOM")
    b.L(v_host, v_dist.inputs["Mesh"])
    b.L(tand(gi.outputs["Vines"], tand(tand(tcmp("LESS_THAN", em("ABSOLUTE", v_nz), 0.3),
                                              tcmp("LESS_THAN", dnamed("vm_trim", "FLOAT"), 0.5)),
                                         tcmp("GREATER_THAN", dnamed("vm_ext", "FLOAT"), 0.5))),
        v_dist.inputs["Selection"])
    b.L(em("MULTIPLY", 20.0, em("MULTIPLY", geo_f, geo_f)), v_dist.inputs["Density"])
    b.L(seed_node(b, v_seed, 601), v_dist.inputs["Seed"])
    v_cand = v_store(v_dist.outputs["Points"], (("vm_n", "FLOAT_VECTOR", v_dist.outputs["Normal"]),))
    v_cnt = b.N("GeometryNodeAttributeDomainSize", random_loc())
    v_cnt.component = "POINTCLOUD"
    b.L(v_cand, v_cnt.inputs["Geometry"])
    v_px, v_py, _v_pz = sxyz(b.N("GeometryNodeInputPosition", random_loc()).outputs["Position"])
    v_cpr = b.N("GeometryNodeProximity", random_loc())
    v_cpr.target_element = "POINTS"
    b.L(v_corf.outputs["Geometry"], v_cpr.inputs["Geometry"])
    b.L(v3(v_px, v_py, 0.0), v_cpr.inputs["Sample Position"])
    v_near = tsw(tcmp("GREATER_THAN", v_ccn.outputs["Point Count"], 0.5), 0.0,
                 em("MAXIMUM", em("SUBTRACT", 1.0, em("DIVIDE", v_cpr.outputs["Distance"], em("DIVIDE", 0.7, geo_f))),
                    0.0))
    v_r1x, v_r1y, _v_r1z = v_rand(611)
    v_pick = b.N("GeometryNodeDeleteGeometry", random_loc(), domain="POINT")
    b.L(v_cand, v_pick.inputs["Geometry"])
    b.L(tcmp("GREATER_EQUAL", v_r1x, em("MULTIPLY", em("DIVIDE", gi.outputs["Vine Count"],
                                                        em("MAXIMUM", v_cnt.outputs["Point Count"], 1.0)),
                                         tm("MULTIPLY_ADD", v_near, 2.2, 0.4))),
        v_pick.inputs["Selection"])
    # each root: at the foot of the wall, pressed onto the nearest surface
    # there and a hair in front of it, heading up
    v_r0 = v3(v_px, v_py, em("ADD", v_base, em("DIVIDE", 0.06, geo_f)))
    v_rpx = b.N("GeometryNodeProximity", random_loc())
    v_rpx.target_element = "FACES"
    b.L(v_host, v_rpx.inputs["Geometry"])
    b.L(v_r0, v_rpx.inputs["Sample Position"])
    v_rsn = b.N("GeometryNodeSampleNearestSurface", random_loc(), data_type="FLOAT_VECTOR")
    b.L(v_host, v_rsn.inputs["Mesh"])
    b.L(dnamed("vm_vn", "FLOAT_VECTOR"), v_rsn.inputs["Value"])
    b.L(v_r0, v_rsn.inputs["Sample Position"])
    v_rsnap = v_store(v_pick.outputs["Geometry"], (("vm_n", "FLOAT_VECTOR", v_rsn.outputs["Value"]),))
    v_root = b.N("GeometryNodeSetPosition", random_loc())
    b.L(v_rsnap, v_root.inputs["Geometry"])
    b.L(vmath("ADD", v_rpx.outputs["Position"], vmath("SCALE", v_rsn.outputs["Value"], v_off)),
        v_root.inputs["Position"])
    v_iters = em("MINIMUM", em("MAXIMUM", em("FLOOR", em("DIVIDE", em("MULTIPLY", gi.outputs["Vine Height"], 1.6),
                                                          0.065)), 6.0), 140.0)
    v_roots = v_store(v_root.outputs["Geometry"], (
        ("vm_dir", "FLOAT_VECTOR", v_up),
        ("vm_id", "INT", b.N("GeometryNodeInputIndex", random_loc()).outputs["Index"]),
        ("vm_gen", "FLOAT", 0.0), ("vm_born", "FLOAT", 0.0), ("vm_step", "FLOAT", 0.0),
        ("vm_blen", "FLOAT", 1e6),
        ("vm_lim", "FLOAT", em("ADD", v_base, em("DIVIDE", em("MULTIPLY", gi.outputs["Vine Height"],
                                                             tm("MULTIPLY_ADD", v_r1y, 0.4, 0.6)), sz_g)))))

    # inside a door / window this layer cut (with a 6 cm margin)
    def v_inside(pos_):
        sn_ = b.N("GeometryNodeSampleNearest", random_loc(), domain="POINT")
        b.L(o_cloud, sn_.inputs["Geometry"])
        b.L(pos_, sn_.inputs["Sample Position"])

        def at_(name_):
            si_ = b.N("GeometryNodeSampleIndex", random_loc(), data_type="FLOAT_VECTOR", domain="POINT")
            b.L(o_cloud, si_.inputs["Geometry"])
            b.L(dnamed(name_, "FLOAT_VECTOR"), si_.inputs["Value"])
            b.L(sn_.outputs["Index"], si_.inputs["Index"])
            return si_.outputs["Value"]
        rel_ = vmath("SUBTRACT", pos_, at_("vm_cctr"))
        hu_, _hy, hz_ = sxyz(at_("vm_chalf"))
        mg_ = em("DIVIDE", 0.06, geo_f)
        # ... or in a hole the damage broke through the wall
        return bor(tand(tand(has_open, tand(gi.outputs["Cut Openings"], is_fit)),
                        tand(tcmp("LESS_THAN", em("ABSOLUTE", vmath("DOT_PRODUCT", rel_, at_("vm_cu"), out="Value")),
                                  em("ADD", hu_, mg_)),
                             tcmp("LESS_THAN", em("ABSOLUTE", vmath("DOT_PRODUCT", rel_, at_("vm_cup"), out="Value")),
                                  em("ADD", hz_, mg_)))),
                   gap_at(pos_, em("ADD", v_off, mg_)))
    # ---- the growth: Tips (the growing ends) and Trail (every point so far)
    v_ri = b.N("GeometryNodeRepeatInput", random_loc())
    v_ro = b.N("GeometryNodeRepeatOutput", random_loc())
    v_ri.pair_with_output(v_ro)
    v_ro.repeat_items[0].name = "Tips"
    v_ro.repeat_items.new("GEOMETRY", "Trail")
    b.L(v_iters, v_ri.inputs["Iterations"])
    b.L(v_roots, v_ri.inputs["Tips"])
    b.L(v_roots, v_ri.inputs["Trail"])
    v_it = v_ri.outputs["Iteration"]

    def it_seed(off_):
        return em("ADD", em("MULTIPLY", v_it, 131.0), seed_node(b, v_seed, off_))
    v_gen = dnamed("vm_gen", "FLOAT")
    v_vid = dnamed("vm_id", "INT")
    # branching: a share of the tips sprouts a side shoot here (main stems
    # Vine Branches over their life, shoots half as often, theirs never)
    vb_x, vb_y, vb_z = v_rand(0, v_vid, it_seed(651))
    vb_p = em("MULTIPLY", em("DIVIDE", gi.outputs["Vine Branches"], em("MAXIMUM", v_iters, 1.0)),
              tsw(tcmp("LESS_THAN", v_gen, 0.5), tsw(tcmp("LESS_THAN", v_gen, 1.5), 0.0, 0.5), 1.3))
    vb_dup = b.N("GeometryNodeDuplicateElements", random_loc(), domain="POINT")
    b.L(v_ri.outputs["Tips"], vb_dup.inputs["Geometry"])
    b.L(tcmp("LESS_THAN", vb_x, vb_p), vb_dup.inputs["Selection"])
    vb_turn = b.N("FunctionNodeAxisAngleToRotation", random_loc())
    b.L(dnamed("vm_n", "FLOAT_VECTOR"), vb_turn.inputs["Axis"])
    b.L(em("MULTIPLY", tsw(tcmp("LESS_THAN", vb_y, 0.5), 1.0, -1.0), tm("MULTIPLY_ADD", vb_z, 0.7, 0.6)),
        vb_turn.inputs["Angle"])
    vb_new = v_store(vb_dup.outputs["Geometry"], (
        ("vm_blen", "FLOAT", em("DIVIDE", tsw(tcmp("LESS_THAN", v_gen, 0.5), tm("MULTIPLY_ADD", vb_z, 0.45, 0.25),
                                              tm("MULTIPLY_ADD", vb_z, 1.1, 0.5)), geo_f)),
        ("vm_dir", "FLOAT_VECTOR", rot(dnamed("vm_dir", "FLOAT_VECTOR"), vb_turn.outputs["Rotation"])),
        ("vm_id", "INT", em("ADD", em("MULTIPLY", em("ADD", v_it, 1.0), 100000.0),
                            b.N("GeometryNodeInputIndex", random_loc()).outputs["Index"])),
        ("vm_born", "FLOAT", v_it), ("vm_step", "FLOAT", v_it),
        ("vm_gen", "FLOAT", em("ADD", v_gen, 1.0))))
    vt_all = b.N("GeometryNodeJoinGeometry", random_loc())
    b.L(v_ri.outputs["Tips"], vt_all.inputs["Geometry"])
    b.L(vb_new, vt_all.inputs["Geometry"])
    # one step: up + momentum + a wander, flattened onto the surface
    vm_p = b.N("GeometryNodeInputPosition", random_loc()).outputs["Position"]
    vm_n = dnamed("vm_n", "FLOAT_VECTOR")
    vw_x, vw_y, vw_z = v_rand(0, v_vid, it_seed(661))
    vm_w = vmath("SUBTRACT", vmath("SCALE", v3(vw_x, vw_y, vw_z), 2.0), v3(1.0, 1.0, 1.0))
    vm_d0 = vmath("ADD", vmath("ADD", vmath("SCALE", dnamed("vm_dir", "FLOAT_VECTOR"), 0.7),
                               vmath("SCALE", v_up, tsw(tcmp("LESS_THAN", v_gen, 0.5), 0.22, 0.5))),
                  vmath("SCALE", vm_w, 0.65))
    vm_dt = vnorm(vmath("SUBTRACT", vm_d0, vmath("SCALE", vm_n, vmath("DOT_PRODUCT", vm_d0, vm_n, out="Value"))))
    vm_cand = vmath("ADD", vm_p, vmath("SCALE", vm_dt, v_step))
    # an opening ahead: slide along it sideways (the way it leaned) instead
    vm_side = vnorm(vmath("CROSS_PRODUCT", vm_n, v_up))
    vm_sg = tsw(tcmp("LESS_THAN", vmath("DOT_PRODUCT", vm_dt, vm_side, out="Value"), 0.0), 1.0, -1.0)
    vm_alt = vmath("ADD", vm_p, vmath("SCALE", vm_side, em("MULTIPLY", vm_sg, v_step)))
    vm_inc = v_inside(vm_cand)
    vm_p1 = vsw(vm_inc, vm_cand, vm_alt)
    # ... pressed back onto the nearest surface
    vm_px = b.N("GeometryNodeProximity", random_loc())
    vm_px.target_element = "FACES"
    b.L(v_host, vm_px.inputs["Geometry"])
    b.L(vm_p1, vm_px.inputs["Sample Position"])
    vm_sn = b.N("GeometryNodeSampleNearestSurface", random_loc(), data_type="FLOAT_VECTOR")
    b.L(v_host, vm_sn.inputs["Mesh"])
    b.L(dnamed("vm_vn", "FLOAT_VECTOR"), vm_sn.inputs["Value"])
    b.L(vm_p1, vm_sn.inputs["Sample Position"])
    vm_p2 = vmath("ADD", vm_px.outputs["Position"], vmath("SCALE", vm_sn.outputs["Value"], v_off))
    vk_x, _vk_y, _vk_z = v_rand(0, v_vid, it_seed(671))
    # (a snap onto the far side of a thin part - the roof's top seen from
    # under the eaves - would pass the stem through it: the tip stops there)
    vm_flip = tcmp("LESS_THAN", vmath("DOT_PRODUCT", vm_n, vm_sn.outputs["Value"], out="Value"), -0.3)
    # (in a concave corner - wall under the soffit - the snapped point can sit
    # too close to the other surface: the tip stops there too)
    vm_px2 = b.N("GeometryNodeProximity", random_loc())
    vm_px2.target_element = "FACES"
    b.L(v_host, vm_px2.inputs["Geometry"])
    b.L(vm_p2, vm_px2.inputs["Sample Position"])
    vm_tight = tcmp("LESS_THAN", vm_px2.outputs["Distance"], em("MULTIPLY", v_off, 0.8))
    vm_dead = bor(bor(tand(vm_inc, v_inside(vm_alt)), bor(vm_flip, vm_tight)), tcmp("LESS_THAN", vk_x, 0.004))
    vm_mv = v_store(vt_all.outputs["Geometry"], (
        ("vm_np", "FLOAT_VECTOR", vm_p2),
        ("vm_dead", "FLOAT", tsw(vm_dead, 0.0, 1.0)),
        ("vm_dir", "FLOAT_VECTOR", vnorm(vmath("SUBTRACT", dnamed("vm_np", "FLOAT_VECTOR"), vm_p))),
        ("vm_mvd", "FLOAT", vmath("DISTANCE", dnamed("vm_np", "FLOAT_VECTOR"), vm_p, out="Value")),
        ("vm_n", "FLOAT_VECTOR", vm_sn.outputs["Value"])))
    vm_set = b.N("GeometryNodeSetPosition", random_loc())
    b.L(vm_mv, vm_set.inputs["Geometry"])
    b.L(dnamed("vm_np", "FLOAT_VECTOR"), vm_set.inputs["Position"])
    # tips stop: blocked, by chance, at their height, past their shoot length,
    # stuck (barely moved) or below the ground line
    vm_z = sxyz(b.N("GeometryNodeInputPosition", random_loc()).outputs["Position"])[2]
    vm_stop = bor(bor(tcmp("GREATER_THAN", dnamed("vm_dead", "FLOAT"), 0.5),
                      tcmp("GREATER_THAN", vm_z, dnamed("vm_lim", "FLOAT"))),
                  bor(bor(tcmp("GREATER_THAN", em("MULTIPLY", em("SUBTRACT", v_it, dnamed("vm_born", "FLOAT")), v_step),
                               dnamed("vm_blen", "FLOAT")),
                          tcmp("LESS_THAN", dnamed("vm_mvd", "FLOAT"), em("MULTIPLY", v_step, 0.15))),
                      tcmp("LESS_THAN", vm_z, v_base)))
    vm_live = b.N("GeometryNodeDeleteGeometry", random_loc(), domain="POINT")
    b.L(vm_set.outputs["Geometry"], vm_live.inputs["Geometry"])
    b.L(vm_stop, vm_live.inputs["Selection"])
    vm_tips = v_store(vm_live.outputs["Geometry"], (("vm_step", "FLOAT", em("ADD", v_it, 1.0)),))
    vm_trail = b.N("GeometryNodeJoinGeometry", random_loc())
    for g_ in (v_ri.outputs["Trail"], vb_new, vm_tips):
        b.L(g_, vm_trail.inputs["Geometry"])
    b.L(vm_tips, v_ro.inputs["Tips"])
    b.L(vm_trail.outputs["Geometry"], v_ro.inputs["Trail"])
    v_trail = v_ro.outputs["Trail"]
    # ---- stems: the trail strung into curves (one per shoot, in step order),
    # smoothed, tapering to the tip - main stems twice the shoots' girth
    v_p2c = b.N("GeometryNodePointsToCurves", random_loc())
    b.L(v_trail, v_p2c.inputs["Points"])
    b.L(dnamed("vm_id", "INT"), v_p2c.inputs["Curve Group ID"])
    b.L(dnamed("vm_step", "FLOAT"), v_p2c.inputs["Weight"])
    v_cr = b.N("GeometryNodeCurveSplineType", random_loc())
    v_cr.spline_type = "CATMULL_ROM"
    b.L(v_p2c.outputs["Curves"], v_cr.inputs["Curve"])
    v_res = b.N("GeometryNodeSetSplineResolution", random_loc())
    b.L(v_cr.outputs["Curve"], v_res.inputs["Curve"])
    v_res.inputs["Resolution"].default_value = 3
    v_t = b.N("GeometryNodeSplineParameter", random_loc()).outputs["Factor"]
    v_prof = b.N("GeometryNodeCurvePrimitiveCircle", random_loc())
    v_prof.inputs["Resolution"].default_value = 5
    v_prof.inputs["Radius"].default_value = 1.0
    v_tube = b.N("GeometryNodeCurveToMesh", random_loc())
    b.L(v_res.outputs["Curve"], v_tube.inputs["Curve"])
    b.L(v_prof.outputs["Curve"], v_tube.inputs["Profile Curve"])
    b.L(em("MULTIPLY", em("DIVIDE", tsw(tcmp("LESS_THAN", dnamed("vm_gen", "FLOAT"), 0.5), 0.006, 0.012), geo_f),
           tm("MULTIPLY_ADD", v_t, -0.65, 1.0)), v_tube.inputs["Scale"])
    v_smat = b.N("GeometryNodeSetMaterial", random_loc())
    b.L(v_tube.outputs["Mesh"], v_smat.inputs["Geometry"])
    b.L(gi.outputs["Stem Material"], v_smat.inputs["Material"])
    v_sinst = b.N("GeometryNodeGeometryToInstance", random_loc())
    b.L(v_smat.outputs["Geometry"], v_sinst.inputs["Geometry"])
    # ---- the ivy leaf: a lobed outline (terminal lobe, two side lobes, two
    # small basal lobes, a heart notch at the stalk) filled, cupped a little.
    # Leaf space: base at the origin, tip at +Y 1, facing +Z; UVs = leaf space
    lf_c = b.N("GeometryNodeCurvePrimitiveCircle", random_loc())
    lf_c.inputs["Resolution"].default_value = 48
    lf_c.inputs["Radius"].default_value = 1.0
    lf_x, lf_y, _lf_z = sxyz(b.N("GeometryNodeInputPosition", random_loc()).outputs["Position"])
    lf_th = em("ARCTAN2", lf_x, lf_y)                                   # from +Y
    lf_lobe = em("POWER", tm("MULTIPLY_ADD", em("COSINE", em("MULTIPLY", lf_th, 5.0)), 0.5, 0.5), 1.3)
    lf_r = em("MULTIPLY", tm("MULTIPLY_ADD", em("COSINE", lf_th), 0.2, 0.8), tm("MULTIPLY_ADD", lf_lobe, 0.38, 0.62))
    lf_sp = b.N("GeometryNodeSetPosition", random_loc())
    b.L(lf_c.outputs["Curve"], lf_sp.inputs["Geometry"])
    b.L(v3(em("DIVIDE", em("MULTIPLY", em("SINE", lf_th), lf_r), 1.372),
           em("DIVIDE", tm("MULTIPLY_ADD", em("COSINE", lf_th), lf_r, 0.372), 1.372), 0.0), lf_sp.inputs["Position"])
    lf_fill = b.N("GeometryNodeFillCurve", random_loc())
    b.L(lf_sp.outputs["Geometry"], lf_fill.inputs["Curve"])
    lf_x2, lf_y2, _lf_z2 = sxyz(b.N("GeometryNodeInputPosition", random_loc()).outputs["Position"])
    lf_cup = b.N("GeometryNodeSetPosition", random_loc())
    b.L(lf_fill.outputs["Mesh"], lf_cup.inputs["Geometry"])
    b.L(v3(0.0, 0.0, tm("MULTIPLY_ADD", em("MULTIPLY", lf_x2, lf_x2), -0.3, em("MULTIPLY", lf_y2, 0.08))),
        lf_cup.inputs["Offset"])
    lf_uv = v_store(lf_cup.outputs["Geometry"], (("UVMap", "FLOAT2", v3(lf_x2, lf_y2, 0.0)),), "CORNER")
    lf_mat = b.N("GeometryNodeSetMaterial", random_loc())
    b.L(lf_uv, lf_mat.inputs["Geometry"])
    b.L(gi.outputs["Leaf Material"], lf_mat.inputs["Material"])
    # ---- leaves: up to three per trail point, a little off the stem and out
    # from the wall, facing out (tilted to the sky), tips hanging, bigger on
    # the old wood near the root
    lv_dup = b.N("GeometryNodeDuplicateElements", random_loc(), domain="POINT")
    b.L(v_trail, lv_dup.inputs["Geometry"])
    lv_dup.inputs["Amount"].default_value = 3
    lv_id = b.N("GeometryNodeInputIndex", random_loc()).outputs["Index"]
    lv_a, lv_b, lv_c = v_rand(641, lv_id)
    lv_d, lv_e, lv_f = v_rand(643, lv_id)
    lv_n = dnamed("vm_n", "FLOAT_VECTOR")
    lv_t1 = vnorm(vmath("CROSS_PRODUCT", lv_n, v3(0.31, 0.17, 0.93)))
    lv_t2 = vmath("CROSS_PRODUCT", lv_n, lv_t1)
    lv_pos = vmath("ADD", vmath("ADD", b.N("GeometryNodeInputPosition", random_loc()).outputs["Position"],
                                vmath("SCALE", lv_n, em("DIVIDE", tm("MULTIPLY_ADD", lv_d, 0.03, 0.006), geo_f))),
                   vmath("ADD", vmath("SCALE", lv_t1, em("DIVIDE", em("MULTIPLY", em("SUBTRACT", lv_e, 0.5), 0.07), geo_f)),
                         vmath("SCALE", lv_t2, em("DIVIDE", em("MULTIPLY", em("SUBTRACT", lv_f, 0.5), 0.07), geo_f))))
    lv_mv = b.N("GeometryNodeSetPosition", random_loc())
    b.L(lv_dup.outputs["Geometry"], lv_mv.inputs["Geometry"])
    b.L(lv_pos, lv_mv.inputs["Position"])
    lv_az = b.N("FunctionNodeAlignRotationToVector", random_loc())
    lv_az.axis = "Z"
    b.L(vnorm(vmath("ADD", lv_n, vmath("SCALE", v_up, 0.35))), lv_az.inputs["Vector"])
    lv_ay = b.N("FunctionNodeAlignRotationToVector", random_loc())
    lv_ay.axis = "Y"
    lv_ay.pivot_axis = "Z"
    b.L(lv_az.outputs["Rotation"], lv_ay.inputs["Rotation"])
    b.L(v_up, lv_ay.inputs["Vector"])
    lv_spin = b.N("FunctionNodeEulerToRotation", random_loc())
    b.L(v3(tm("MULTIPLY_ADD", lv_b, 0.45, -0.55), 0.0, tm("MULTIPLY_ADD", lv_a, 2.8, 1.74)), lv_spin.inputs["Euler"])
    lv_rot = b.N("FunctionNodeRotateRotation", random_loc())
    lv_rot.rotation_space = "LOCAL"
    b.L(lv_ay.outputs["Rotation"], lv_rot.inputs["Rotation"])
    b.L(lv_spin.outputs["Rotation"], lv_rot.inputs["Rotate By"])
    lv_age = em("MINIMUM", em("DIVIDE", dnamed("vm_step", "FLOAT"), em("MAXIMUM", v_iters, 1.0)), 1.0)
    lv_sz = em("DIVIDE", em("MULTIPLY", em("MULTIPLY", gi.outputs["Leaf Size"], tm("MULTIPLY_ADD", lv_c, 0.6, 0.65)),
                            tm("MULTIPLY_ADD", lv_age, -0.5, 1.15)), geo_f)
    lv_iop = b.N("GeometryNodeInstanceOnPoints", random_loc())
    b.L(lv_mv.outputs["Geometry"], lv_iop.inputs["Points"])
    b.L(tcmp("LESS_THAN", v_rand(647, lv_id)[0], gi.outputs["Leaf Density"]), lv_iop.inputs["Selection"])
    b.L(lf_mat.outputs["Geometry"], lv_iop.inputs["Instance"])
    b.L(lv_rot.outputs["Rotation"], lv_iop.inputs["Rotation"])
    b.L(lv_sz, lv_iop.inputs["Scale"])
    v_join = b.N("GeometryNodeJoinGeometry", random_loc())
    b.L(v_sinst.outputs["Instances"], v_join.inputs["Geometry"])
    b.L(lv_iop.outputs["Instances"], v_join.inputs["Geometry"])
    b.L(v_join.outputs["Geometry"], g_join.inputs["Geometry"])

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
def add_dormers(b, region_pts, roof_main, fl, ph):
    """v2.22 DORMERS (the user's 'roof-like extra parts with windows that come
    out of the roof if the roof is steep enough'): on every Gable region, a row
    of dormers along each slope. Each is found by raycasting the real slope
    (so it sits ON the roof whatever the pitch / overhang / Built Roof), and
    built analytically so it meets the slope exactly - no booleans:
      front wall (a quad, flagged vm_dfront: the window layer puts its window
      on it) + its little gable triangle, two cheeks (triangles from the slope
      up to the dormer eave), and two roof slopes (overhanging at the front and
      sides) that run back until they meet the main slope.
    A dormer only appears where it FITS under the main ridge (steep enough
    roofs) and the pitch is at least 'Dormer Min Pitch'.
    fl: fields/sockets from the roof cap (rc, ru, rv, rw, rh, rz, eff_ru,
    eff_rv, sz, gable, pitch, thick, built); ph: the dormer socket placeholders."""
    seq = [0]

    def loc():
        seq[0] += 1
        return (5200 + 20 * (seq[0] % 40), -7000 - 25 * seq[0])

    def M(op, a, b_=None, c_=None):
        n_ = b.N("ShaderNodeMath", loc(), operation=op)
        for i_, x_ in enumerate((a, b_, c_)):
            if x_ is None:
                continue
            if isinstance(x_, (int, float)):
                n_.inputs[i_].default_value = x_
            else:
                b.L(x_, n_.inputs[i_])
        return n_.outputs["Value"]

    def V(op, a, b_=None, out="Vector"):
        n_ = b.N("ShaderNodeVectorMath", loc(), operation=op)
        b.L(a, n_.inputs[0])
        if b_ is not None:
            if op == "SCALE":
                if isinstance(b_, (int, float)):
                    n_.inputs["Scale"].default_value = b_
                else:
                    b.L(b_, n_.inputs["Scale"])
            else:
                b.L(b_, n_.inputs[1])
        return n_.outputs[out]

    def C(op, a, b_):
        n_ = b.N("FunctionNodeCompare", loc(), data_type="FLOAT", operation=op)
        b.L(a, n_.inputs["A"])
        if isinstance(b_, (int, float)):
            n_.inputs["B"].default_value = b_
        else:
            b.L(b_, n_.inputs["B"])
        return n_.outputs["Result"]

    def AND(*xs):
        out_ = xs[0]
        for x_ in xs[1:]:
            n_ = b.N("FunctionNodeBooleanMath", loc(), operation="AND")
            b.L(out_, n_.inputs[0])
            b.L(x_, n_.inputs[1])
            out_ = n_.outputs["Boolean"]
        return out_

    def SW(cond, f_, t_):
        n_ = b.N("GeometryNodeSwitch", loc())
        n_.input_type = "FLOAT"
        b.L(cond, n_.inputs["Switch"])
        for key_, x_ in (("False", f_), ("True", t_)):
            if isinstance(x_, (int, float)):
                n_.inputs[key_].default_value = x_
            else:
                b.L(x_, n_.inputs[key_])
        return n_.outputs["Output"]

    def XYZ(x, y, z):
        n_ = b.N("ShaderNodeCombineXYZ", loc())
        for k_, val_ in zip("XYZ", (x, y, z)):
            if isinstance(val_, (int, float)):
                n_.inputs[k_].default_value = val_
            else:
                b.L(val_, n_.inputs[k_])
        return n_.outputs["Vector"]

    def SEP(v_):
        n_ = b.N("ShaderNodeSeparateXYZ", loc())
        b.L(v_, n_.inputs["Vector"])
        return n_.outputs["X"], n_.outputs["Y"], n_.outputs["Z"]

    def NAMED(name, dt="FLOAT"):
        n_ = b.N("GeometryNodeInputNamedAttribute", loc())
        n_.data_type = dt
        n_.inputs["Name"].default_value = name
        return n_.outputs["Attribute"]

    def STORE(geo_, name, dt, val, domain="POINT"):
        n_ = b.N("GeometryNodeStoreNamedAttribute", loc(), data_type=dt, domain=domain)
        b.L(geo_, n_.inputs["Geometry"])
        n_.inputs["Name"].default_value = name
        if isinstance(val, (int, float)):
            n_.inputs["Value"].default_value = val
        else:
            b.L(val, n_.inputs["Value"])
        return n_.outputs["Geometry"]

    sz = fl["sz"]
    # ---- candidates: 16 per slope side per region (k = 0..15, side -/+)
    dup = b.N("GeometryNodeDuplicateElements", loc(), domain="POINT")
    b.L(region_pts, dup.inputs["Geometry"])
    dup.inputs["Amount"].default_value = 32
    di = dup.outputs["Duplicate Index"]
    k_ = M("FLOORED_MODULO", di, 16.0)
    s_ = M("MULTIPLY_ADD", M("FLOOR", M("DIVIDE", di, 16.0)), 2.0, -1.0)
    rc, ru, rv = fl["rc"], fl["ru"], fl["rv"]
    rw, rh, rz = fl["rw"], fl["rh"], fl["rz"]
    e_u, e_v = fl["eff_ru"], fl["eff_rv"]
    hw_w = M("MULTIPLY", ph["Dormer Width"], 0.5)
    hw_l = M("DIVIDE", hw_w, e_u)
    n_ = M("FLOOR", M("DIVIDE", M("MULTIPLY", rw, e_u), M("MAXIMUM", ph["Dormer Spacing"], 0.5)))
    u_k = M("MULTIPLY", M("SUBTRACT", M("DIVIDE", M("ADD", k_, 0.5), M("MAXIMUM", n_, 1.0)), 0.5), rw)
    v_f = M("SUBTRACT", M("MULTIPLY", rh, 0.5), M("DIVIDE", ph["Dormer Setback"], e_v))
    dn = V("SCALE", rv, s_)                                   # outward, toward the eave
    rc_x, rc_y, _rc_z = SEP(rc)
    p_xy = V("ADD", V("ADD", XYZ(rc_x, rc_y, 0.0), V("SCALE", ru, u_k)), V("SCALE", dn, v_f))
    dl = M("DIVIDE", 0.5, e_v)                                # the second ray, 0.5 m up the slope
    p2_xy = V("SUBTRACT", p_xy, V("SCALE", dn, dl))

    def ray_z(pxy_):
        px_, py_, _pz = SEP(pxy_)
        rc_ = b.N("GeometryNodeRaycast", loc())
        b.L(roof_main, rc_.inputs["Target Geometry"])
        b.L(XYZ(px_, py_, M("ADD", rz, 1000.0)), rc_.inputs["Source Position"])
        rc_.inputs["Ray Direction"].default_value = (0.0, 0.0, -1.0)
        rc_.inputs["Ray Length"].default_value = 3000.0
        _hx, _hy, hz_ = SEP(rc_.outputs["Hit Position"])
        return hz_, rc_.outputs["Is Hit"]
    z1, h1 = ray_z(p_xy)
    z2, h2 = ray_z(p2_xy)
    g_ = M("DIVIDE", M("SUBTRACT", z2, z1), dl)               # slope rise per local unit inward
    g_s = M("MAXIMUM", g_, 0.01)
    t_l = SW(fl["built"], 0.0, M("DIVIDE", M("MAXIMUM", fl["thick"], 0.0), sz))
    e03 = M("DIVIDE", 0.03, sz)
    top_f = M("ADD", z1, t_l)
    zb = M("SUBTRACT", top_f, e03)                            # the front sill, just under the slope top
    td = M("TANGENT", M("MINIMUM", M("MAXIMUM", ph["Dormer Pitch"], 0.1), 1.4))
    hf_l = M("DIVIDE", ph["Dormer Height"], sz)
    hwz = M("DIVIDE", M("MULTIPLY", hw_w, td), sz)
    od_w = 0.15
    odz = M("DIVIDE", M("MULTIPLY", td, od_w), sz)
    od_u = M("DIVIDE", od_w, e_u)
    od_v = M("DIVIDE", od_w, e_v)
    # depths (local, inward from the front plane) where the dormer meets the
    # slope: the cheek back (its foot runs 3 cm under the slope top), the roof
    # eave back and the ridge back (the dormer roof's underside on the main
    # slope's underside, so the two slab tops meet)
    d_e = M("DIVIDE", hf_l, g_s)
    d_e2 = M("DIVIDE", M("ADD", M("SUBTRACT", M("SUBTRACT", hf_l, odz), e03), t_l), g_s)
    d_r = M("DIVIDE", M("ADD", M("SUBTRACT", M("ADD", hf_l, hwz), e03), t_l), g_s)
    rnd = b.N("FunctionNodeRandomValue", loc(), data_type="FLOAT")
    b.L(ph["Dormer Seed"], rnd.inputs["Seed"])
    ok = AND(fl["gable"], ph["Dormers"], C("GREATER_EQUAL", fl["pitch"], ph["Dormer Min Pitch"]),
             C("LESS_THAN", k_, n_), h1, h2, C("GREATER_THAN", g_, 0.05),
             C("LESS_EQUAL", M("ADD", d_r, M("DIVIDE", 0.15, e_v)), v_f),
             C("LESS_EQUAL", M("ADD", M("ABSOLUTE", u_k), M("ADD", hw_l, od_u)),
               M("SUBTRACT", M("MULTIPLY", rw, 0.5), M("DIVIDE", 0.3, e_u))),
             C("LESS_THAN", rnd.outputs["Value"], ph["Dormer Chance"]))
    px_, py_, _pz = SEP(p_xy)
    d_o = XYZ(px_, py_, zb)
    d_c = V("ADD", V("SUBTRACT", d_o, V("SCALE", dn, M("MULTIPLY", d_e, 0.3))),
            XYZ(0.0, 0.0, M("MULTIPLY", hf_l, 0.5)))
    geo_ = dup.outputs["Geometry"]
    for nm_, dt_, val_ in (("vm_dok", "FLOAT", M("ADD", ok, 0.0)),
                           ("vm_do", "FLOAT_VECTOR", d_o), ("vm_dn", "FLOAT_VECTOR", dn),
                           ("vm_du", "FLOAT_VECTOR", ru), ("vm_dc", "FLOAT_VECTOR", d_c),
                           ("vm_dk", "FLOAT_VECTOR", XYZ(hw_l, od_u, od_v)),
                           ("vm_dz", "FLOAT_VECTOR", XYZ(hf_l, hwz, odz)),
                           ("vm_dd", "FLOAT_VECTOR", XYZ(d_e, d_e2, d_r))):
        geo_ = STORE(geo_, nm_, dt_, val_)
    dbg_pts = None
    if os.environ.get("VM_DBG_DORM"):
        dbg_pts = geo_
        for nm_, val_ in (("vm_dbg1", XYZ(k_, s_, n_)), ("vm_dbg2", XYZ(z1, z2, g_)),
                          ("vm_dbg3", XYZ(d_r, v_f, u_k)),
                          ("vm_dbg4", XYZ(M("ADD", h1, 0.0), M("ADD", fl["gable"], 0.0),
                                          M("ADD", ph["Dormers"], 0.0))),
                          ("vm_dbg5", XYZ(fl["pitch"], ph["Dormer Min Pitch"], rw)),
                          ("vm_dbg6", XYZ(rh, e_u, e_v))):
            dbg_pts = STORE(dbg_pts, nm_, "FLOAT_VECTOR", val_)
        dsp_ = b.N("GeometryNodeSetPosition", loc())
        b.L(dbg_pts, dsp_.inputs["Geometry"])
        b.L(XYZ(px_, py_, z1), dsp_.inputs["Position"])
        dbg_pts = dsp_.outputs["Geometry"]
    keep = b.N("GeometryNodeDeleteGeometry", loc(), domain="POINT")
    b.L(geo_, keep.inputs["Geometry"])
    b.L(C("LESS_THAN", NAMED("vm_dok"), 0.5), keep.inputs["Selection"])

    # ---- the template: pieces with per-vertex codes (across, depth, height)
    # across: +-1 = the cheek line, +-2 = the overhanging eave, 0 = ridge
    # depth: 0 front, 1 front overhang, 2 cheek back, 3 eave back, 4 ridge back
    # height: 0 sill, 1 eave, 2 ridge, 3 overhanging eave
    pieces = (((-1, 0, 0), (1, 0, 0), (1, 0, 1), (-1, 0, 1)),     # front wall (vm_dfront)
              ((-1, 0, 1), (1, 0, 1), (0, 0, 2)),                  # its gable triangle
              ((-1, 0, 0), (-1, 0, 1), (-1, 2, 1)),                # cheeks
              ((1, 0, 0), (1, 0, 1), (1, 2, 1)),
              ((-2, 1, 3), (0, 1, 2), (0, 4, 2), (-2, 3, 3)),      # roof slopes
              ((2, 1, 3), (0, 1, 2), (0, 4, 2), (2, 3, 3)))
    tj = b.N("GeometryNodeJoinGeometry", loc())
    for pi_, codes_ in enumerate(pieces):
        ci_ = b.N("GeometryNodeMeshCircle", loc(), fill_type="NGON")
        ci_.inputs["Vertices"].default_value = len(codes_)
        isw_ = b.N("GeometryNodeIndexSwitch", loc(), data_type="VECTOR")
        while len(isw_.index_switch_items) < len(codes_):
            isw_.index_switch_items.new()
        b.L(b.N("GeometryNodeInputIndex", loc()).outputs["Index"], isw_.inputs["Index"])
        for vi_, cd_ in enumerate(codes_):
            isw_.inputs[vi_ + 1].default_value = cd_
        pg_ = STORE(ci_.outputs["Mesh"], "vm_dt", "FLOAT_VECTOR", isw_.outputs["Output"])
        pg_ = STORE(pg_, "vm_dfront", "FLOAT", 1.0 if pi_ == 0 else 0.0, domain="FACE")
        b.L(pg_, tj.inputs["Geometry"])
    iop = b.N("GeometryNodeInstanceOnPoints", loc())
    b.L(keep.outputs["Geometry"], iop.inputs["Points"])
    b.L(tj.outputs["Geometry"], iop.inputs["Instance"])
    real = b.N("GeometryNodeRealizeInstances", loc())
    b.L(iop.outputs["Instances"], real.inputs["Geometry"])

    # ---- every vertex from its codes and its dormer's numbers
    ta, tv, tz = SEP(NAMED("vm_dt", "FLOAT_VECTOR"))
    k_hw, k_ou, k_ov = SEP(NAMED("vm_dk", "FLOAT_VECTOR"))
    z_hf, z_hw, z_od = SEP(NAMED("vm_dz", "FLOAT_VECTOR"))
    dd_e, dd_e2, dd_r = SEP(NAMED("vm_dd", "FLOAT_VECTOR"))
    sg_ = M("MINIMUM", M("MAXIMUM", ta, -1.0), 1.0)
    a_l = M("MULTIPLY", sg_, M("ADD", k_hw, SW(C("GREATER_THAN", M("ABSOLUTE", ta), 1.5), 0.0, k_ou)))

    def pick(code_, vals_):
        out_ = vals_[0]
        for i_, x_ in enumerate(vals_[1:], start=1):
            out_ = SW(C("GREATER_THAN", code_, i_ - 0.5), out_, x_)
        return out_
    d_l = pick(tv, [0.0, M("MULTIPLY", k_ov, -1.0), dd_e, dd_e2, dd_r])
    z_l = pick(tz, [0.0, z_hf, M("ADD", z_hf, z_hw), M("SUBTRACT", z_hf, z_od)])
    pos_ = V("ADD", V("ADD", NAMED("vm_do", "FLOAT_VECTOR"), V("SCALE", NAMED("vm_du", "FLOAT_VECTOR"), a_l)),
             V("ADD", V("SCALE", NAMED("vm_dn", "FLOAT_VECTOR"), M("MULTIPLY", d_l, -1.0)), XYZ(0.0, 0.0, z_l)))
    sp_ = b.N("GeometryNodeSetPosition", loc())
    b.L(real.outputs["Geometry"], sp_.inputs["Geometry"])
    b.L(pos_, sp_.inputs["Position"])
    # every face turned to face OUT of its dormer
    fl_ = b.N("GeometryNodeFlipFaces", loc())
    b.L(sp_.outputs["Geometry"], fl_.inputs["Mesh"])
    b.L(C("LESS_THAN", V("DOT_PRODUCT", b.N("GeometryNodeInputNormal", loc()).outputs["Normal"],
                         V("SUBTRACT", b.N("GeometryNodeInputPosition", loc()).outputs["Position"],
                           NAMED("vm_dc", "FLOAT_VECTOR")), out="Value"), 0.0),
        fl_.inputs["Selection"])
    mg_ = b.N("GeometryNodeMergeByDistance", loc())
    b.L(fl_.outputs["Mesh"], mg_.inputs["Geometry"])
    mg_.inputs["Distance"].default_value = 0.0005
    out_ = mg_.outputs["Geometry"]
    # what the cladding layers need to find the inside of each dormer (the
    # roof's shakes under it are dropped there): kept on the dormer's points
    for nm_, src_ in (("vm_dmo", "vm_do"), ("vm_dmn", "vm_dn"), ("vm_dmu", "vm_du"),
                      ("vm_dmk", "vm_dk"), ("vm_dmz", "vm_dz")):
        out_ = STORE(out_, nm_, "FLOAT_VECTOR", NAMED(src_, "FLOAT_VECTOR"))
    for nm_ in ("vm_dok", "vm_do", "vm_dn", "vm_du", "vm_dc", "vm_dk", "vm_dz", "vm_dd", "vm_dt"):
        rm_ = b.N("GeometryNodeRemoveAttribute", loc())
        b.L(out_, rm_.inputs["Geometry"])
        rm_.inputs["Name"].default_value = nm_
        out_ = rm_.outputs["Geometry"]
    add_dormers.dbg = dbg_pts
    return out_


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
    template_plain = st_t.outputs["Geometry"]
    # v2.11 Built Roof: the socket pair is created LAST (identifier order) and
    # linked into these placeholders at the end of the group
    built_in = b.N("FunctionNodeBooleanMath", (-1150, -2050), operation="OR")
    built_in.inputs[1].default_value = False
    built_on = built_in.outputs["Boolean"]
    thick_in = b.N("ShaderNodeMath", (-1150, -1950), operation="ADD")
    thick_in.inputs[1].default_value = 0.0
    # v2.22 Dormers: sockets created LAST too, linked into these at the end
    dm_on = b.N("FunctionNodeBooleanMath", (-1150, -1850), operation="OR")
    dm_on.inputs[1].default_value = False
    dm_ph = {"Dormers": dm_on.outputs["Boolean"]}
    dm_nodes = {}
    for _k, _nm in enumerate(("Dormer Min Pitch", "Dormer Spacing", "Dormer Width", "Dormer Height",
                              "Dormer Setback", "Dormer Pitch", "Dormer Chance", "Dormer Seed")):
        _n = b.N("ShaderNodeMath", (-1000, -1850 - 40 * _k), operation="ADD")
        _n.inputs[1].default_value = 0.0
        dm_nodes[_nm] = _n
        dm_ph[_nm] = _n.outputs["Value"]
    # gable-end faces of the template (normal along x) are flagged and every
    # face gets its own vertices, so the gable ends can move independently of
    # the slopes (merged again after positioning)
    t_nrm = b.N("GeometryNodeInputNormal", (-1150, -2500))
    t_nsep = b.N("ShaderNodeSeparateXYZ", (-1000, -2500))
    b.L(t_nrm.outputs["Normal"], t_nsep.inputs["Vector"])
    t_nax = b.N("ShaderNodeMath", (-850, -2500), operation="ABSOLUTE")
    b.L(t_nsep.outputs["X"], t_nax.inputs[0])
    t_isg = b.N("FunctionNodeCompare", (-700, -2500), data_type="FLOAT", operation="GREATER_THAN")
    b.L(t_nax.outputs["Value"], t_isg.inputs["A"])
    t_isg.inputs["B"].default_value = 0.5
    st_tg = b.N("GeometryNodeStoreNamedAttribute", (-1000, -2300), data_type="FLOAT", domain="FACE")
    b.L(template_plain, st_tg.inputs["Geometry"])
    st_tg.inputs["Name"].default_value = "vm_tg"
    b.L(t_isg.outputs["Result"], st_tg.inputs["Value"])
    t_split = b.N("GeometryNodeSplitEdges", (-850, -2300))
    b.L(st_tg.outputs["Geometry"], t_split.inputs["Mesh"])
    t_sw = b.N("GeometryNodeSwitch", (-700, -2300))
    t_sw.input_type = "GEOMETRY"
    b.L(built_on, t_sw.inputs["Switch"])
    b.L(template_plain, t_sw.inputs["False"])
    b.L(t_split.outputs["Mesh"], t_sw.inputs["True"])
    template = t_sw.outputs["Output"]

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
    # ---- v2.11 BUILT ROOF (the user's realism goal): as real roofs are framed.
    # The slopes keep their overhang but drop below the wall top by
    # Overhang * tan(Pitch), so every slope passes exactly through the wall-top
    # line; in Gable style the gable ends move IN to the wall plane as true
    # triangles (the wall continued - its siding lines up with the wall below)
    # under the overhanging slopes. Hip ends are slopes and drop the same way.
    tg_rd = b.N("GeometryNodeInputNamedAttribute", (2550, -3100))
    tg_rd.data_type = "FLOAT"
    tg_rd.inputs["Name"].default_value = "vm_tg"
    is_ge = b.N("FunctionNodeCompare", (2700, -3100), data_type="FLOAT", operation="GREATER_THAN")
    b.L(tg_rd.outputs["Attribute"], is_ge.inputs["A"])
    is_ge.inputs["B"].default_value = 0.5
    is_g = b.N("FunctionNodeBooleanMath", (2850, -3100), operation="AND")
    b.L(is_ge.outputs["Result"], is_g.inputs[0])
    b.L(style_sw.outputs["Gable"], is_g.inputs[1])

    def bsw(cond, if_false, if_true, loc):
        n_ = b.N("GeometryNodeSwitch", loc)
        n_.input_type = "FLOAT"
        b.L(cond, n_.inputs["Switch"])
        b.L(if_false, n_.inputs["False"])
        b.L(if_true, n_.inputs["True"])
        return n_.outputs["Output"]

    xs_g = bsw(is_g.outputs["Boolean"], xs, m("SUBTRACT", A, oh_u, loc=(2850, -3250)), (3000, -3250))
    yb_g = bsw(is_g.outputs["Boolean"], B, m("SUBTRACT", B, oh_v, loc=(2850, -3400)), (3000, -3400))
    drop = m("DIVIDE", m("MULTIPLY", gi.outputs["Overhang"], tan_p, loc=(2700, -3550)), sz_g,
             loc=(2850, -3550))
    drop_k = bsw(is_g.outputs["Boolean"], m("ADD", 1.0, 0.0, loc=(2850, -3700)),
                 tsep2.outputs["Z"], (3000, -3700))
    xw = bsw(built_on, xw, m("MULTIPLY", tsep2.outputs["X"], xs_g, loc=(3150, -3250)), (3300, -3250))
    yw = bsw(built_on, yw, m("MULTIPLY", tsep2.outputs["Y"], yb_g, loc=(3150, -3400)), (3300, -3400))
    zs = bsw(built_on, zs, m("SUBTRACT", zs, m("MULTIPLY", drop, drop_k, loc=(3150, -3700)),
                             loc=(3300, -3650)), (3450, -3650))
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
    # v2.22 dormers on steep gable slopes (raycast onto this roof, then joined
    # with it so their roofs get the same slab / soffit / material)
    dm_geo = add_dormers(b, m2p.outputs["Points"], sp2.outputs["Geometry"],
                         dict(rc=rc_v, ru=ru_v, rv=rv_v, rw=rw_v, rh=rh_v, rz=rz_v, eff_ru=eff_ru,
                              eff_rv=eff_rv, sz=sz_g, gable=style_sw.outputs["Gable"],
                              pitch=gi.outputs["Pitch"], thick=thick_in.outputs["Value"],
                              built=built_on), dm_ph)
    dm_join = b.N("GeometryNodeJoinGeometry", (3600, -1300))
    b.L(sp2.outputs["Geometry"], dm_join.inputs["Geometry"])
    b.L(dm_geo, dm_join.inputs["Geometry"])
    # Built Roof: re-join the split template, then give the slopes a real slab
    # (Roof Thickness, extruded straight UP so its eave and rake edges are
    # vertical fascia faces) with a soffit underneath; gable ends stay flat
    sl_mg = b.N("GeometryNodeMergeByDistance", (3750, -1100))
    b.L(dm_join.outputs["Geometry"], sl_mg.inputs["Geometry"])
    sl_mg.inputs["Distance"].default_value = 0.0005
    sl_n = b.N("GeometryNodeInputNormal", (3750, -900))
    sl_ns = b.N("ShaderNodeSeparateXYZ", (3900, -900))
    b.L(sl_n.outputs["Normal"], sl_ns.inputs["Vector"])
    sl_sel = b.N("FunctionNodeCompare", (4050, -900), data_type="FLOAT", operation="GREATER_THAN")
    b.L(sl_ns.outputs["Z"], sl_sel.inputs["A"])
    sl_sel.inputs["B"].default_value = 0.1
    sl_not = b.N("FunctionNodeBooleanMath", (4200, -900), operation="NOT")
    b.L(sl_sel.outputs["Result"], sl_not.inputs[0])
    sl_bot = b.N("GeometryNodeDeleteGeometry", (3900, -800), domain="FACE")
    b.L(sl_mg.outputs["Geometry"], sl_bot.inputs["Geometry"])
    b.L(sl_not.outputs["Boolean"], sl_bot.inputs["Selection"])
    sl_flip = b.N("GeometryNodeFlipFaces", (4050, -800))
    b.L(sl_bot.outputs["Geometry"], sl_flip.inputs["Mesh"])
    sl_t = m("DIVIDE", m("MAXIMUM", thick_in.outputs["Value"], 0.0, loc=(3750, -700)), sz_g,
             loc=(3900, -700))
    sl_off = b.N("ShaderNodeCombineXYZ", (4050, -700))
    b.L(sl_t, sl_off.inputs["Z"])
    sl_ex = b.N("GeometryNodeExtrudeMesh", (4050, -1100))
    sl_ex.mode = "FACES"
    b.L(sl_mg.outputs["Geometry"], sl_ex.inputs["Mesh"])
    b.L(sl_sel.outputs["Result"], sl_ex.inputs["Selection"])
    b.L(sl_off.outputs["Vector"], sl_ex.inputs["Offset"])
    sl_ex.inputs["Individual"].default_value = False
    sl_join = b.N("GeometryNodeJoinGeometry", (4200, -1100))
    b.L(sl_ex.outputs["Mesh"], sl_join.inputs["Geometry"])
    b.L(sl_flip.outputs["Mesh"], sl_join.inputs["Geometry"])
    sl_mg2 = b.N("GeometryNodeMergeByDistance", (4350, -1100))
    b.L(sl_join.outputs["Geometry"], sl_mg2.inputs["Geometry"])
    sl_mg2.inputs["Distance"].default_value = 0.0005
    roof_geo = b.N("GeometryNodeSwitch", (4500, -1300))
    roof_geo.input_type = "GEOMETRY"
    b.L(built_on, roof_geo.inputs["Switch"])
    b.L(dm_join.outputs["Geometry"], roof_geo.inputs["False"])
    b.L(sl_mg2.outputs["Geometry"], roof_geo.inputs["True"])
    dressed = material_gate(b, roof_geo.outputs["Output"], gi.outputs["Roof Material"],
                            sel_all.outputs["Boolean"], (3750, -1500))
    # mark generated faces so Fit (doors/windows) never anchors on gable ends
    st_rg = b.N("GeometryNodeStoreNamedAttribute", (3950, -1500), data_type="FLOAT", domain="FACE")
    b.L(dressed, st_rg.inputs["Geometry"])
    st_rg.inputs["Name"].default_value = "vm_roofgen"
    st_rg.inputs["Value"].default_value = 1.0
    st_df = b.N("GeometryNodeStoreNamedAttribute", (4100, -1500), data_type="FLOAT", domain="FACE")
    b.L(st_rg.outputs["Geometry"], st_df.inputs["Geometry"])
    st_df.inputs["Name"].default_value = "vm_roofgen"
    st_df.inputs["Value"].default_value = 0.0
    df_rd = b.N("GeometryNodeInputNamedAttribute", (3950, -1650))
    df_rd.data_type = "FLOAT"
    df_rd.inputs["Name"].default_value = "vm_dfront"
    df_cmp = b.N("FunctionNodeCompare", (4100, -1650), data_type="FLOAT", operation="GREATER_THAN")
    b.L(df_rd.outputs["Attribute"], df_cmp.inputs["A"])
    df_cmp.inputs["B"].default_value = 0.5
    b.L(df_cmp.outputs["Result"], st_df.inputs["Selection"])
    # the front wall gets vertices of its own: later layers carry face
    # attributes over to points (averaged at shared corners), and its 0 / 1
    # flags must read back exact
    df_e = b.N("GeometryNodeInputNamedAttribute", (4100, -1750))
    df_e.data_type = "FLOAT"
    df_e.inputs["Name"].default_value = "vm_dfront"
    df_ecmp = b.N("FunctionNodeCompare", (4250, -1750), data_type="FLOAT", operation="GREATER_THAN")
    b.L(df_e.outputs["Attribute"], df_ecmp.inputs["A"])
    df_ecmp.inputs["B"].default_value = 0.25
    df_split = b.N("GeometryNodeSplitEdges", (4250, -1500))
    b.L(st_df.outputs["Geometry"], df_split.inputs["Mesh"])
    b.L(df_ecmp.outputs["Result"], df_split.inputs["Selection"])

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
    b.L(df_split.outputs["Mesh"], join.inputs["Geometry"])
    b.L(st_cap.outputs["Geometry"], join.inputs["Geometry"])
    b.L(st_cone.outputs["Geometry"], join.inputs["Geometry"])
    if getattr(add_dormers, "dbg", None) is not None:
        b.L(add_dormers.dbg, join.inputs["Geometry"])
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
    # v2.11: created after every older socket so their identifiers never shift
    b.sock("Built Roof", "NodeSocketBool", p, False,
           desc="Gable/Hip (v2.11): build the roof as a real one is framed - the slopes "
                "overhang and drop below the wall top, gable ends sit IN the wall plane, and the "
                "slopes are a slab of Roof Thickness with fascia edges and a soffit. Off = the "
                "v2.4 closed prism")
    b.sock("Roof Thickness", "NodeSocketFloat", p, 0.12, 0.0, 2.0, "DISTANCE",
           "Built Roof: slab thickness of the slopes (world meters)")
    b.L(gi.outputs["Built Roof"], built_in.inputs[0])
    b.L(gi.outputs["Roof Thickness"], thick_in.inputs[0])
    # v2.22: dormers - created after every older socket (identifier order)
    p_dm = b.panel("Dormers", "Gable (v2.22): dormers with a window, out of slopes steep enough to hold them")
    b.sock("Dormers", "NodeSocketBool", p_dm, True,
           desc="v2.22: dormers along every Gable slope that is steep enough to hold one under its "
                "ridge (and at least 'Dormer Min Pitch'); the window layer puts a window in each")
    b.sock("Dormer Min Pitch", "NodeSocketFloat", p_dm, math.radians(40.0), 0.0, math.radians(89.0),
           "ANGLE", "No dormers on roofs flatter than this")
    b.sock("Dormer Spacing", "NodeSocketFloat", p_dm, 2.8, 0.5, 100.0, "DISTANCE",
           "Wall meters per dormer along the slope (count = floor(wall length / this))")
    b.sock("Dormer Width", "NodeSocketFloat", p_dm, 1.2, 0.4, 10.0, "DISTANCE",
           "Width of a dormer's front wall (world m)")
    b.sock("Dormer Height", "NodeSocketFloat", p_dm, 1.1, 0.3, 10.0, "DISTANCE",
           "Height of a dormer's front wall from the slope to its eave (world m)")
    b.sock("Dormer Setback", "NodeSocketFloat", p_dm, 0.25, 0.0, 10.0, "DISTANCE",
           "How far the dormer front sits back from the wall below (world m)")
    b.sock("Dormer Pitch", "NodeSocketFloat", p_dm, math.radians(40.0), math.radians(5.0),
           math.radians(80.0), "ANGLE", "Pitch of the dormers' own little gable roofs")
    b.sock("Dormer Chance", "NodeSocketFloat", p_dm, 1.0, 0.0, 1.0, "FACTOR",
           "Share of the dormer places that get one (1 = every place)")
    b.sock("Dormer Seed", "NodeSocketInt", p_dm, 0, 0, 100000, desc="Another pick of which places get one")
    b.L(gi.outputs["Dormers"], dm_on.inputs[0])
    for _nm, _n in dm_nodes.items():
        b.L(gi.outputs[_nm], _n.inputs[0])

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
    # part 1 tests THIS build's in-code stack (vmt.dress_stack), so the add-on
    # must not fall back to a previously delivered library (its presets are
    # the LAST build's); the library path is restored for the v2.10 part
    _lib_path = vmt.library_path
    vmt.library_path = lambda context=None: ""
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
    check("addon(dress): 'VM: Dress Object' applies the FULL default stack in one click "
          "(wall cladding + interior floor + VM_RoofCap + roof cladding + doors + windows)",
          a_names == [n_ for n_, _, _ in vmt.dress_stack()]
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
          snap_a == snap_b and len(snap_a) == len(vmt.dress_stack()) and n_socks >= 100 and not mism_ab,
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
          preset_ok and len(preset_snap) == len(vmt.dress_stack()) and vmt.count_sockets(preset_snap) == n_socks,
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
          snap_c == preset_snap and len(snap_c) == len(vmt.dress_stack()) and not mism_c,
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
    # v2.11: the library ships the REAL cladding tiles - lapped siding boards and
    # split shakes (wedge profile, bevelled, bowed/cupped) with per-board wood
    # materials, a dark roof underlay and the edge-board trim. The engine stages
    # above keep the flat test tiles their checks were pinned on.
    wood_src = os.path.join(ASSET_SRC, "materials", "walls", "dark_planks")
    lib_mats = dict(
        siding=make_board_material("VM_SidingBoard", wood_src, "dark_planks", 8, 0.10, 2.0, 0.7, 1.15),
        shake=make_board_material("VM_Shake", wood_src, "dark_planks", 8, 0.10, 2.0, 0.65, 1.1, 0.6),
        under=make_principled("VM_RoofUnderlay", (0.03, 0.025, 0.02), rough=0.9),
        # v2.18: the windows' glass (breaks by each pane's vm_gbrk)
        glass=make_glass_material("VM_WindowGlass"),
        # v2.19: the vines
        vstem=make_principled("VM_VineStem", (0.09, 0.06, 0.035), rough=0.85),
        vleaf=make_leaf_material("VM_VineLeaf"),
        # v2.12: what missing siding reveals - old dark sheathing boards
        sheath=make_textured_material(
            "VM_Sheathing", os.path.join(ASSET_SRC, "materials", "walls", "weathered_plank_siding"),
            "weathered_plank_siding_diff.jpg", "weathered_plank_siding_rough.jpg",
            "weathered_plank_siding_nor.jpg", 0.5, darken=0.3))
    for cn, maker, mat_ in (("VM_Tiles_Plank", make_siding_variants, lib_mats["siding"]),
                            ("VM_Tiles_Shingle", make_shake_variants, lib_mats["shake"])):
        col_ = bpy.data.collections[cn]
        for ob in list(col_.objects):
            bpy.data.objects.remove(ob)
        maker(col_, cn.replace("VM_Tiles_", ""), 6, mat_)
    # v2.13: the Damage panel's broken pieces + worn tiles, next to the tiles
    tile_parent = next(c for c in bpy.data.collections
                       if bpy.data.collections["VM_Tiles_Plank"].name in c.children)
    for cn, maker, mat_, n_ in (("VM_Tiles_PlankBroken", make_broken_siding, lib_mats["siding"], 8),
                                ("VM_Tiles_PlankWorn", make_worn_siding, lib_mats["siding"], 10),
                                ("VM_Tiles_ShingleBroken", make_broken_shakes, lib_mats["shake"], 6),
                                ("VM_Tiles_ShingleWorn", make_worn_shakes, lib_mats["shake"], 8)):
        col_ = bpy.data.collections.new(cn)
        tile_parent.children.link(col_)
        maker(col_, cn.replace("VM_Tiles_", ""), n_, mat_)
    pack_images()
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
    weathered = {"Damage": True, "Damage Amount": 0.2}
    for pname, style, desc, extra in (
            ("Base - Flat roof", "Flat", "The default pack at default settings: plank walls, flat "
             "clay-tile roof cap, shingle roof cladding, doors and windows", {}),
            ("Base - Gable roof", "Gable", "Base preset with a gable roof cap", {}),
            ("Base - Hip roof", "Hip", "Base preset with a hip roof cap", {}),
            ("Base - Weathered gable", "Gable", "Gable preset with light damage over the whole "
             "building: missing, broken and loose boards and shakes (v2.12)", weathered)):
        pw = []
        vmt.dress_object(probe, pw)
        rc = probe.modifiers["VM_RoofCap"]
        set_params(rc, rc.node_group, {"Style": style})
        # v2.16: the windows layer (it cuts the openings) damages them too
        for mn_ in ("VM_SceneDetailer_Planks", "VM_SceneDetailer_Shingles", "VM_SceneDetailer_Windows"):
            if extra:
                set_params(probe.modifiers[mn_], probe.modifiers[mn_].node_group, extra)
        if extra:                       # v2.19: and it is overgrown (v2.20: thickly)
            wl_p = probe.modifiers["VM_SceneDetailer_Windows"]
            set_params(wl_p, wl_p.node_group, {"Vines": True, "Vine Count": 14, "Vine Branches": 12})
            # v2.21: and its roof is in a worse state - holes through it
            sl_p = probe.modifiers["VM_SceneDetailer_Shingles"]
            set_params(sl_p, sl_p.node_group, {"Damage Amount": 0.42, "Roof Holes": 0.6})
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
          and all(len(pr["modifiers"]) == len(vmt.dress_stack()) for pr in lib_meta.get("presets", {}).values()),
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
    vmt.library_path = _lib_path
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
          r_a == {'FINISHED'} and len(snap_fa) == len(vmt.dress_stack()) and fx_ver == ENGINE_VERSION
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

    # ---- v2.21: ROOF HOLES (rafters + battens seen through them) and
    # PARTLY BROKEN windows, on the Weathered gable preset
    fx_w = fx_cube("FreshW", 20.0)
    fx_w.data.transform(Matrix.Diagonal((3.0, 2.25, 1.5, 1.0)))   # a 6 x 4.5 x 3 m house
    bpy.ops.vm.apply_preset(preset="lib:Base - Weathered gable")
    wl_w = fx_w.modifiers["VM_SceneDetailer_Windows"]
    sl_w = fx_w.modifiers["VM_SceneDetailer_Shingles"]
    set_params(wl_w, wl_w.node_group, {"Half Broken": 1.0})

    def roof_scan():
        fx_w.update_tag()
        dg_w = bpy.context.evaluated_depsgraph_get()
        dg_w.update()
        me_w = fx_w.evaluated_get(dg_w).data
        mw_ = fx_w.matrix_world
        bb_ = [mw_ @ v_.co for v_ in fx_w.data.vertices]     # the house itself (not the evaluated roof)
        lo_ = Vector([min(c_[k_] for c_ in bb_) for k_ in range(3)])
        hi_ = Vector([max(c_[k_] for c_ in bb_) for k_ in range(3)])
        ra_ = me_w.attributes.get("vm_rafter")
        raf_ = [mw_ @ me_w.polygons[i_].center for i_, d_ in enumerate(ra_.data) if d_.value > 0.5]             if ra_ is not None and ra_.domain == "FACE" else []
        out_ = [c_ for c_ in raf_ if c_.z < hi_.z - 0.3 or not (lo_.x - 0.6 < c_.x < hi_.x + 0.6)
                or not (lo_.y - 0.6 < c_.y < hi_.y + 0.6)]
        # the partly broken units: no inner part left past their break line
        at_ = {n_: me_w.attributes.get(n_) for n_ in ("vm_hbc", "vm_hbd", "vm_hbo", "vm_hbu", "vm_hbh")}
        kept_, past_ = 0, 0
        if all(a_ is not None and a_.domain == "POINT" for a_ in at_.values()):
            for i_, v_ in enumerate(me_w.vertices):
                h_ = at_["vm_hbh"].data[i_].vector
                if h_.length < 1e-4:
                    continue
                rel_ = v_.co - at_["vm_hbo"].data[i_].vector
                inner_ = (abs(rel_.dot(at_["vm_hbu"].data[i_].vector)) < h_.x - 0.12
                          and abs(rel_.z) < h_.z - 0.12)
                d_ = (v_.co - at_["vm_hbc"].data[i_].vector).dot(at_["vm_hbd"].data[i_].vector)
                kept_ += 1
                past_ += int(inner_ and d_ > 0.07)
        return len(raf_), len(out_), kept_, past_
    rs_on = roof_scan()
    set_params(sl_w, sl_w.node_group, {"Roof Holes": 0.0})
    set_params(wl_w, wl_w.node_group, {"Half Broken": 0.0})
    rs_off = roof_scan()
    check("v2.21(roof holes / half broken): the Weathered preset breaks HOLES through the roof - the rafters "
          "and battens under the shakes show in them and never poke out past the roof; Half Broken leaves "
          "windows partly there (the frame and one side kept, every inner part past the break line gone); "
          "Roof Holes 0 / Half Broken 0 turn both off",
          rs_on[0] > 0 and rs_on[1] == 0 and rs_on[2] > 0 and rs_on[3] == 0
          and rs_off[0] == 0 and rs_off[2] == 0,
          f"rafter/batten faces {rs_on[0]} (outside the roof {rs_on[1]}), partly broken window points "
          f"kept {rs_on[2]} (inner past the line {rs_on[3]}); off: rafter faces {rs_off[0]}, "
          f"partly broken points {rs_off[2]}")
    results["roof_half_v221"] = dict(rafters=rs_on[0], out=rs_on[1], kept=rs_on[2], past=rs_on[3])
    bpy.data.objects.remove(fx_w)

    # ---- v2.22: DORMERS out of a steep gable roof, a window in each
    fx_d = fx_cube("FreshD", 34.0)
    fx_d.data.transform(Matrix.Diagonal((3.0, 2.25, 1.5, 1.0)))   # a 6 x 4.5 x 3 m house
    bpy.ops.vm.apply_preset(preset="lib:Base - Gable roof")
    rc_d = fx_d.modifiers["VM_RoofCap"]
    win_d = {o.name for o in bpy.data.collections["VM_Windows"].all_objects}
    shk_d = {o.name for o in bpy.data.collections["VM_Tiles_Shingle"].all_objects}

    def dormer_scan():
        fx_d.update_tag()
        dg_d = bpy.context.evaluated_depsgraph_get()
        dg_d.update()
        top_ = max((fx_d.matrix_world @ v_.co).z for v_ in fx_d.data.vertices)
        wins_, shk_ = [], []
        for inst in dg_d.object_instances:
            if not (inst.is_instance and inst.parent is not None and inst.parent.original == fx_d):
                continue
            m_ = inst.matrix_world.copy()
            if inst.object.name in win_d and m_.translation.z > top_ - 0.05:
                wins_.append(m_)
            elif inst.object.name in shk_d:
                shk_.append(m_.translation.copy())
        ev_ = fx_d.evaluated_get(dg_d)
        bvh_ = BVHTree.FromObject(ev_, dg_d)
        upright, open_, inside = 0, 0, 0
        for m_ in wins_:
            up_ = m_.col[2].to_3d().normalized()
            n_ = m_.col[1].to_3d().normalized()
            sz_ = m_.col[2].to_3d().length
            upright += int(up_.z > 0.95)
            c_ = m_.translation + up_ * 0.9 * sz_          # the middle of the window
            hit_ = bvh_.ray_cast(c_ + n_ * 1.0, -n_, 20.0)
            open_ += int(hit_[0] is None or hit_[3] > 1.25)   # >= 25 cm in past the front
            # roof shakes left INSIDE the dormer, behind its window
            for t_ in shk_:
                r_ = t_ - m_.translation
                if abs(r_.dot(m_.col[0].to_3d().normalized())) < 0.35 and -0.6 < r_.dot(n_) < -0.08                         and 0.05 < r_.z < 1.6 * sz_:
                    inside += 1
        return len(wins_), upright, open_, inside
    set_params(rc_d, rc_d.node_group, {"Pitch": math.radians(48.0)})
    ds_on = dormer_scan()
    set_params(rc_d, rc_d.node_group, {"Pitch": math.radians(35.0)})
    ds_flat = dormer_scan()
    set_params(rc_d, rc_d.node_group, {"Pitch": math.radians(48.0), "Dormers": False})
    ds_off = dormer_scan()
    check("v2.22(dormers): a Gable roof steep enough (>= Dormer Min Pitch) grows DORMERS along both slopes - "
          "each with an upright window cut through its front wall and no roof shakes left inside it; a "
          "35 deg roof or Dormers off has none",
          ds_on[0] >= 4 and ds_on[1] == ds_on[0] and ds_on[2] == ds_on[0] and ds_on[3] == 0
          and ds_flat[0] == 0 and ds_off[0] == 0,
          f"48 deg: dormer windows {ds_on[0]} (upright {ds_on[1]}, open through the wall {ds_on[2]}, "
          f"shakes inside {ds_on[3]}); 35 deg: {ds_flat[0]}; Dormers off: {ds_off[0]}")
    results["dormers_v222"] = dict(windows=ds_on[0], upright=ds_on[1], open=ds_on[2], inside=ds_on[3],
                                   flat=ds_flat[0], off=ds_off[0])

    # ---- v2.23: the door is SET INTO the wall (the user's 'the door is
    # basically just placed on top of the wall') with a casing round it; the
    # sloped edges of the walls (gable rakes, dormer fronts and cheeks) get a
    # rake board over the stepped board ends (the user's 'above the windows
    # the planks don't cover all of the wall')
    set_params(rc_d, rc_d.node_group, {"Pitch": math.radians(48.0), "Dormers": True})
    fx_d.update_tag()
    dg_s = bpy.context.evaluated_depsgraph_get()
    dg_s.update()
    door_d = {o.name for o in bpy.data.collections["VM_Doors"].all_objects}
    base_vs = [fx_d.matrix_world @ v_.co for v_ in fx_d.data.vertices]
    top_s = max(v_.z for v_ in base_vs)
    me_s = fx_d.evaluated_get(dg_s).data
    mw_s = fx_d.matrix_world
    cas_a = me_s.attributes.get("vm_casing")
    cas_vs = [mw_s @ me_s.vertices[i_].co for i_, d_ in enumerate(cas_a.data) if d_.value > 0.5] if cas_a else []
    set_in, cased = [], []
    for inst in dg_s.object_instances:
        if not (inst.is_instance and inst.parent is not None and inst.parent.original == fx_d
                and inst.object.name in door_d):
            continue
        m_ = inst.matrix_world.copy()
        n_ = m_.col[1].to_3d().normalized()
        y_hi = max(c_[1] for c_ in inst.object.bound_box)
        front_ = (m_ @ Vector((0.0, y_hi, 0.9))).dot(n_)
        wall_ = max(v_.dot(n_) for v_ in base_vs)
        set_in.append(round(front_ - wall_, 3))
        cased.append(sum(1 for v_ in cas_vs if (v_ - m_.translation).length < 2.6))   # (head ~2 m up)
    rh_a, rt_a, rn_a = (me_s.attributes.get(nm_) for nm_ in ("vm_rkh", "vm_rkt", "vm_rkm"))
    rk_v = []
    if rh_a and rt_a and rn_a:
        for i_, d_ in enumerate(rh_a.data):
            if d_.vector.length > 0.5:
                rk_v.append((me_s.vertices[i_].co.copy(), Vector(d_.vector), Vector(rt_a.data[i_].vector),
                             Vector(rn_a.data[i_].vector)))
    past_top = sum(1 for co_, h_, t_, _n in rk_v if (co_ - t_).dot(h_) > 0.002)
    off_wall = sum(1 for co_, _h, t_, n_ in rk_v if abs((co_ - t_).dot(n_)) > 0.08)
    rk_roof = sum(1 for co_, *_r in rk_v if (mw_s @ co_).z > top_s + 0.3)
    check("v2.23(doors set in, rake boards): every door leaf stands IN its hole (its face 1-6 cm behind the "
          "wall) framed by a casing (2 side boards, a head, a sill); the sloped wall edges carry rake boards "
          "lying on the wall, cut plumb at the top (none past its apex)",
          set_in and all(-0.06 <= s_ <= -0.01 for s_ in set_in) and all(c_ >= 32 for c_ in cased)
          and len(rk_v) >= 64 and rk_roof >= 32 and past_top == 0 and off_wall == 0,
          f"door faces vs the wall={set_in} m, casing vertices per door={cased}; rake board vertices="
          f"{len(rk_v)} (above the walls {rk_roof}), past the plumb cut={past_top}, off the wall={off_wall}")
    results["doors_v223"] = dict(set_in=set_in, casing=cased, rake_vertices=len(rk_v), rake_roof=rk_roof,
                                 past_top=past_top, off_wall=off_wall)
    bpy.data.objects.remove(fx_d)

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

    # ---- v2.10: INTERIOR FLOOR (the user's "grass inside the house" report)
    fl_ob = st_cases["one 6 m wall face"]          # 5 x 4 footprint at (24..29, 12..16)
    plank_names = {o.name for o in bpy.data.collections["VM_Tiles_Plank"].all_objects}
    fl_boards, fl_rows = [], Counter()
    for inst in dg_st.object_instances:
        if inst.is_instance and inst.parent is not None and inst.parent.original == fl_ob \
                and inst.object.name in plank_names:
            m_ = inst.matrix_world
            if m_.col[1].to_3d().normalized().z > 0.9:     # lies flat, face up
                t_ = m_.translation
                bbx_ = [c_[0] for c_ in inst.object.bound_box]     # local, unscaled
                ln_ = m_.col[0].to_3d().length * (max(bbx_) - min(bbx_))
                fl_boards.append((t_.x - ln_ / 2, t_.x + ln_ / 2, t_.y, t_.z))
                fl_rows[round(t_.y, 3)] += ln_
    fl_ev = fl_ob.evaluated_get(dg_st)
    fl_mats = sorted({fl_ev.data.materials[p_.material_index].name for p_ in fl_ev.data.polygons
                      if p_.normal.z < -0.9 and fl_ev.data.materials
                      and fl_ev.data.materials[p_.material_index]})
    fl_inside = all(24.0 - 1e-3 <= x0 and x1 <= 29.0 + 1e-3 and 12.0 <= y_ <= 16.0
                    and abs(z_) < 0.03 for x0, x1, y_, z_ in fl_boards)
    fl_full = bool(fl_rows) and all(abs(v - 5.0) < 0.02 for v in fl_rows.values())
    check("v2.10(floor): Dress Object lays floorboards on the building's bottom from the "
          "inside - flat, face up, every row exactly spans the 5 m floor (edge boards cut, "
          "nothing past the walls) and the bottom face is wood, not grass",
          len(fl_boards) > 0 and fl_inside and fl_full and len(fl_rows) == 25
          and fl_mats and "VM_FloorGrass" not in fl_mats,
          f"{len(fl_boards)} boards in {len(fl_rows)} rows, inside footprint={fl_inside}, "
          f"row lengths={sorted({round(v, 3) for v in fl_rows.values()})}, bottom material={fl_mats}")
    results["floor"] = dict(boards=len(fl_boards), rows=len(fl_rows), bottom_materials=fl_mats)

    # ---- v2.11: REAL CLADDING (the user's realism reference: a clapboard house
    # with a shake roof - walls and roof are NOT flat surfaces). A 6 x 4.5 x 3 m
    # cottage, Dress Object + Gable, measured in the cottage's local frame.
    ct_ob = storey_mesh("Cottage211", [(0, 0, 0, 6, 4.5, 3)], 40.0)
    rc_ = ct_ob.modifiers["VM_RoofCap"]
    set_params(rc_, rc_.node_group, {"Style": "Gable"})
    ct_ob.update_tag()
    dg_ct = bpy.context.evaluated_depsgraph_get()
    dg_ct.update()
    ct_off = Vector((40.0, 12.0, 0.0))
    tan_p = math.tan(math.radians(35.0))
    shake_names = {o.name for o in bpy.data.collections["VM_Tiles_Shingle"].all_objects}
    plank_names = {o.name for o in bpy.data.collections["VM_Tiles_Plank"].all_objects}
    ct_walls, ct_roof = [], []
    for inst in dg_ct.object_instances:
        if inst.is_instance and inst.parent is not None and inst.parent.original == ct_ob:
            nm_ = inst.object.name
            if nm_ in plank_names or nm_ in shake_names:
                m_ = inst.matrix_world.copy()
                cs_ = [m_ @ Vector(c_) - ct_off for c_ in inst.object.bound_box]
                n_ = m_.col[1].to_3d().normalized()
                if nm_ in shake_names:
                    ct_roof.append(cs_)
                elif abs(n_.z) < 0.3:
                    # wall boards only - the slab's eave fascia (a strip of
                    # siding 25 cm out, below the eave) is roof trim
                    ax_ = 0 if abs(n_.x) > abs(n_.y) else 1
                    pc_ = sum(c_[ax_] for c_ in cs_) / 8
                    if min(abs(pc_), abs(pc_ - (6.0, 4.5)[ax_])) < 0.1:
                        ct_walls.append((cs_, n_))
    # the gable walls are the ones whose siding rises above the 3 m wall top
    high = [n_ for cs_, n_ in ct_walls if max(c_.z for c_ in cs_) > 3.05]
    ga = 0 if high and abs(high[0].x) > abs(high[0].y) else 1      # gable normal axis
    span = (4.5, 6.0)[ga]                       # the gable's base, across the other axis
    apex = 3.0 + span / 2 * tan_p

    def rake(c_):
        return 3.0 + (span / 2 - abs(c_[1 - ga] - span / 2)) * tan_p
    outside = 0
    for cs_, n_ in ct_walls:
        for c_ in cs_:
            along = c_.y if abs(n_.x) > abs(n_.y) else c_.x
            length = 4.5 if abs(n_.x) > abs(n_.y) else 6.0
            on_gable = (abs(n_.x) > abs(n_.y)) == (ga == 0)
            if not (-0.03 <= along <= length + 0.03 and c_.z >= -0.03
                    and c_.z <= (rake(c_) if on_gable else 3.0) + 0.03):
                outside += 1
                break
    hts = sorted(max(c_.z for c_ in cs_) - min(c_.z for c_ in cs_) for cs_, _ in ct_walls)
    ht_med = hts[len(hts) // 2] if hts else 0.0
    gable_n = sum(1 for cs_, n_ in ct_walls if max(c_.z for c_ in cs_) > 3.05)
    roof_top = max((c_.z for cs_ in ct_roof for c_ in cs_), default=0.0)
    check("v2.11(siding): Dress Object clads the walls in LAPPED siding - each board is taller "
          "than its 17 cm course (it laps the one below), every board is cut to its wall / gable "
          "outline (nothing past a corner, the wall top or the rake) and the gable triangles are "
          "sided like the walls below them",
          len(ct_walls) > 100 and 0.18 < ht_med < 0.25 and outside == 0 and gable_n >= 10,
          f"{len(ct_walls)} wall boards, median board height={ht_med:.3f} (course 0.17), "
          f"boards outside the outline={outside}, boards on the gables={gable_n}, gable axis={'xy'[ga]}")
    ct_ev = ct_ob.evaluated_get(dg_ct)
    ct_me = ct_ev.data
    ct_mn = [m_.name if m_ else "" for m_ in ct_me.materials]

    def polys(mat_name):
        return [p_ for p_ in ct_me.polygons
                if ct_mn and ct_mn[p_.material_index] == mat_name]
    roof_ps = polys("VM_RoofUnderlay")
    roof_zs = [ct_me.vertices[v_].co.z for p_ in roof_ps for v_ in p_.vertices]
    flush = [p_ for p_ in ct_me.polygons
             if abs(p_.normal[ga]) > 0.99 and p_.center.z > 3.05
             and min(abs(p_.center[ga]), abs(p_.center[ga] - (6.0, 4.5)[ga])) < 0.01]
    check("v2.11(built roof): Gable roof is framed like a real one - the gable triangles sit "
          "FLUSH in the wall planes, the slopes are a slab of Roof Thickness (top = ridge + 0.12) "
          "and overhang + drop below the wall top at the eaves; no shake rises past the ridge",
          len(flush) >= 2 and roof_zs and abs(max(roof_zs) - (apex + 0.12)) < 0.02
          and min(roof_zs) < 2.9 and len(ct_roof) > 100 and roof_top < apex + 0.12 + 0.06,
          f"flush gable faces={len(flush)}, slab z {min(roof_zs, default=0):.3f}..{max(roof_zs, default=0):.3f} "
          f"(apex {apex:.3f} + 0.12), {len(ct_roof)} shakes, top shake z={roof_top:.3f}")
    cb_vs = [ct_me.vertices[v_].co for p_ in polys("VM_SidingBoard") for v_ in p_.vertices]
    corners_ok = 0
    for cx_, cy_ in ((0, 0), (6, 0), (0, 4.5), (6, 4.5)):
        near = [v_.z for v_ in cb_vs if abs(v_.x - cx_) < 0.2 and abs(v_.y - cy_) < 0.2]
        if near and min(near) < 0.1 and max(near) > 2.9:
            corners_ok += 1
    rc_vs = [ct_me.vertices[v_].co for p_ in polys("VM_Shake") for v_ in p_.vertices]
    rc_top = [v_ for v_ in rc_vs if v_.z > apex + 0.12]
    rc_len = (max(v_[ga] for v_ in rc_top) - min(v_[ga] for v_ in rc_top)) if rc_top else 0.0
    check("v2.11(edge boards): corner boards run the full height of all 4 outside wall corners "
          "(covering the siding ends) and a ridge cap runs the whole ridge over the top shakes",
          corners_ok == 4 and rc_len > (6.0, 4.5)[ga] * 0.95,
          f"corners with a full-height board={corners_ok}/4, ridge cap length={rc_len:.3f} "
          f"(ridge {(6.0, 4.5)[ga]} m + overhangs)")
    results["cladding_v211"] = dict(wall_boards=len(ct_walls), board_height=round(ht_med, 4),
                                    outside=outside, gable_boards=gable_n, shakes=len(ct_roof),
                                    flush_gable_faces=len(flush), corner_boards=corners_ok,
                                    ridge_cap=round(rc_len, 3))

    # ---- v2.12: MOVABLE DAMAGE (Add Damage Zone): a second cottage, damage
    # driven by an Empty; tiles are compared by their exact placement
    dz_ob = storey_mesh("Cottage212", [(0, 0, 0, 6, 4.5, 3)], 55.0)
    rc_ = dz_ob.modifiers["VM_RoofCap"]
    set_params(rc_, rc_.node_group, {"Style": "Gable"})
    # the damage checks measure the cladding itself: openings stay uncut here
    # (v2.15 cuts are checked on their own house below)
    wl_ = dz_ob.modifiers["VM_SceneDetailer_Windows"]
    set_params(wl_, wl_.node_group, {"Cut Openings": False})
    # v2.14: hanging / broken tiles are pieces from the Broken / Worn collections
    clad_names = plank_names | shake_names | {
        o_.name for cn_ in ("VM_Tiles_PlankBroken", "VM_Tiles_PlankWorn", "VM_Tiles_ShingleBroken",
                            "VM_Tiles_ShingleWorn") if cn_ in bpy.data.collections
        for o_ in bpy.data.collections[cn_].all_objects}

    def tile_keys():
        dz_ob.update_tag()
        dg_ = bpy.context.evaluated_depsgraph_get()
        dg_.update()
        out = {}
        for inst in dg_.object_instances:
            if inst.is_instance and inst.parent is not None and inst.parent.original == dz_ob \
                    and inst.object.name in clad_names:
                m_ = inst.matrix_world
                key = (tuple(round(x, 4) for x in m_.translation)
                       + tuple(round(x, 3) for x in m_.to_quaternion())
                       + tuple(round(x, 3) for x in m_.to_scale()))
                out[key] = m_.translation.copy()
        return out
    dz_clean = tile_keys()
    dz_emp = vmt.add_damage_zone(dz_ob, Vector((61.0, 12.0, 1.6)), fx_scene.collection)
    dz_r = vmt.DAMAGE_ZONE_RADIUS
    # v2.14: the boards at a hole's edge break too - a board whose neighbour
    # (inside the radius) is gone can reach one board length (2.4 m) past it
    dz_reach = dz_r + 2.45

    def zone_report(after, centre):
        gone = [dz_clean[k] for k in dz_clean if k not in after]       # missing / moved
        new = [after[k] for k in after if k not in dz_clean]           # broken / loose
        far = [t_ for t_ in gone if (t_ - centre).length > dz_reach]
        return gone, new, far
    dz_a = tile_keys()
    gone_a, new_a, far_a = zone_report(dz_a, dz_emp.location.copy())
    n_layers = len(vmt.damage_layers(dz_ob))
    check("v2.12(damage zone): 'Add Damage Zone' damages BOTH cladding layers around an Empty - "
          "tiles go missing, break and hang loose there, and NOT ONE tile outside the radius changes "
          "(+ the boards broken at the hole's edge, one board length)",
          n_layers == 2 and len(dz_a) < len(dz_clean) - 5 and len(new_a) > 5 and len(gone_a) > 15
          and not far_a,
          f"layers={n_layers}, tiles {len(dz_clean)} -> {len(dz_a)} ({len(dz_clean) - len(dz_a)} missing), "
          f"{len(gone_a)} changed, {len(new_a)} broken/loose, changed beyond {dz_reach:.2f} m={len(far_a)}")
    dz_emp.location = Vector((55.0, 16.5, 2.0))
    dz_b = tile_keys()
    gone_b, new_b, far_b = zone_report(dz_b, dz_emp.location.copy())
    old_c = Vector((61.0, 12.0, 1.6))
    healed = all(k in dz_b for k in dz_clean if (dz_clean[k] - old_c).length <= dz_r
                 and (dz_clean[k] - dz_emp.location).length > dz_reach)
    check("v2.12(movable): moving the Empty moves the damage - the tiles at the old spot are "
          "whole again (exactly as undamaged) and the new spot is damaged, still inside the radius",
          healed and len(gone_b) > 15 and not far_b,
          f"old spot restored={healed}, {len(gone_b)} changed at the new spot, beyond radius={len(far_b)}")
    for m_ in vmt.damage_layers(dz_ob):
        set_params(m_, m_.node_group, {"Damage": False})
    dz_c = tile_keys()
    check("v2.12(damage off): Damage off gives back EXACTLY the undamaged cladding (every tile "
          "placement identical)",
          dz_c.keys() == dz_clean.keys(),
          f"tiles {len(dz_clean)} -> {len(dz_c)}, identical={dz_c.keys() == dz_clean.keys()}")
    results["damage_v212"] = dict(clean=len(dz_clean), zone_tiles=len(dz_a), changed=len(gone_a),
                                  broken_loose=len(new_a), moved_changed=len(gone_b))

    # ---- v2.13: REAL broken geometry + NO floating pieces (the user's report:
    # 'some pieces are floating', 'no realistic damage geometry')
    for m_ in vmt.damage_layers(dz_ob):
        set_params(m_, m_.node_group, {"Damage": True})
    dz_emp.location = Vector((61.0, 12.0, 1.6))
    dz_ob.update_tag()
    dg_d = bpy.context.evaluated_depsgraph_get()
    dg_d.update()
    kinds = {}
    for cn_ in ("VM_Tiles_PlankBroken", "VM_Tiles_PlankWorn", "VM_Tiles_ShingleBroken",
                "VM_Tiles_ShingleWorn"):
        for o_ in bpy.data.collections[cn_].all_objects:
            kinds[o_.name] = cn_
    # v2.14 variety: a shallow 3-point snap is the plainest break (10 verts)
    jagged = all(len(o_.data.vertices) >= 10 for o_ in bpy.data.objects if o_.name in kinds
                 and "Broken" in kinds[o_.name])
    n_kind = Counter()
    pieces, ends = [], []
    for inst in dg_d.object_instances:
        if not (inst.is_instance and inst.parent is not None and inst.parent.original == dz_ob):
            continue
        nm_ = inst.object.name
        m_ = inst.matrix_world.copy()
        if nm_ in kinds:
            n_kind[kinds[nm_]] += 1
        if kinds.get(nm_) == "VM_Tiles_PlankBroken":
            pieces.append(m_.translation - Vector((55.0, 12.0, 0.0)))     # the nailed end
        elif nm_ in plank_names or kinds.get(nm_) == "VM_Tiles_PlankWorn":
            bx_ = [c_[0] for c_ in inst.object.bound_box]
            for x_ in (min(bx_), max(bx_)):
                ends.append(m_ @ Vector((x_, 0.0, 0.0)) - Vector((55.0, 12.0, 0.0)))

    def on_outline(q_):
        # the end sits on its wall's outline: a corner (under the corner board)
        # or the wall top / rake (under the eave)
        on_x_wall = min(abs(q_.x), abs(q_.x - 6.0)) < 0.1
        along, length = (q_.y, 4.5) if on_x_wall else (q_.x, 6.0)
        return min(abs(along), abs(along - length)) < 0.06 or q_.z > 2.9
    floating = [q_ for q_ in pieces if not on_outline(q_)
                and min(((q_ - e_).length for e_ in ends), default=9.0) > 0.06]
    check("v2.13(broken geometry): damage uses REAL damaged pieces - broken boards and shakes "
          "with jagged, splintered ends and worn (split / chipped / bitten) tiles around the damage",
          jagged and all(n_kind[k_] > 0 for k_ in ("VM_Tiles_PlankBroken", "VM_Tiles_ShingleBroken",
                                                   "VM_Tiles_ShingleWorn")),
          f"pieces placed: {dict(n_kind)}, broken meshes jagged={jagged}")
    check("v2.13(no floating): every broken board is still nailed where something holds it - its "
          "kept end meets an intact board's end or the wall outline (corner board / eave)",
          len(pieces) > 0 and not floating,
          f"{len(pieces)} broken boards, floating={[tuple(round(c_, 2) for c_ in q_) for q_ in floating[:6]]}")
    results["damage_v213"] = dict(kinds=dict(n_kind), broken_boards=len(pieces), floating=len(floating))

    # ---- v2.14: no clean flat board end left at a hole (the user's report:
    # 'some planks remain with flat edges around the holes') + more variety
    def board_ends(dg_):
        out_ = []                                    # (instance no., end, intact)
        for k_, inst in enumerate(dg_.object_instances):
            if not (inst.is_instance and inst.parent is not None and inst.parent.original == dz_ob):
                continue
            nm_ = inst.object.name
            if nm_ in plank_names or kinds.get(nm_) == "VM_Tiles_PlankWorn":
                m_ = inst.matrix_world.copy()
                bx_ = [c_[0] for c_ in inst.object.bound_box]
                for x_ in (min(bx_), max(bx_)):
                    out_.append((k_, m_ @ Vector((x_, 0.0, 0.0)) - Vector((55.0, 12.0, 0.0)),
                                 nm_ in plank_names))
        return out_

    def covered(q_, k_, ends_, extra_=()):
        return (any((q_ - e_).length < 0.06 for j_, e_, _i in ends_ if j_ != k_)
                or any((q_ - e_).length < 0.06 for e_ in extra_))
    now_ends = board_ends(dg_d)
    for m_ in vmt.damage_layers(dz_ob):
        set_params(m_, m_.node_group, {"Damage": False})
    dz_ob.update_tag()
    dg_c = bpy.context.evaluated_depsgraph_get()
    dg_c.update()
    clean_ends = board_ends(dg_c)
    for m_ in vmt.damage_layers(dz_ob):
        set_params(m_, m_.node_group, {"Damage": True})
    dz_ob.update_tag()
    owned = [(k_, q_) for k_, q_, intact_ in now_ends if intact_]
    # undamaged: the board's own end + a neighbour's end were there
    flat = [q_ for k_, q_ in owned
            if sum(1 for _j, e_, _i in clean_ends if (e_ - q_).length < 0.06) >= 2
            and not covered(q_, k_, now_ends, pieces)]
    outlines = {tuple(round(v_.co.x, 3) for v_ in o_.data.vertices)
                for o_ in bpy.data.collections["VM_Tiles_PlankBroken"].all_objects}
    check("v2.14(hole edges): no intact board shows a clean flat end at a hole - every board end "
          "meets another board, a broken board's nailed end or the wall outline; boards at a hole "
          "break there (jagged end facing the hole), hanging boards are worn (split ends)",
          len(owned) > 0 and not flat and n_kind["VM_Tiles_PlankBroken"] >= 20,
          f"{len(owned)} intact board ends, flat at a hole={len(flat)} "
          f"{[tuple(round(c_, 2) for c_ in q_) for q_ in flat[:6]]}, "
          f"broken boards={n_kind['VM_Tiles_PlankBroken']}, distinct broken outlines={len(outlines)}")
    results["damage_v214"] = dict(intact_ends=len(owned), flat=len(flat),
                                  broken_boards=n_kind["VM_Tiles_PlankBroken"],
                                  broken_outlines=len(outlines))

    # ---- v2.15: REAL OPENINGS + INTERIOR (the user's 'a window where there is
    # no wall', 'we are supposed to see the interior of the house')
    op_ob = storey_mesh("Cottage215", [(0, 0, 0, 6, 4.5, 3)], 70.0)
    rc_ = op_ob.modifiers["VM_RoofCap"]
    set_params(rc_, rc_.node_group, {"Style": "Gable"})
    board_kinds = {o_.name for cn_ in ("VM_Tiles_Plank", "VM_Tiles_PlankBroken", "VM_Tiles_PlankWorn")
                   for o_ in bpy.data.collections[cn_].all_objects}

    def opening_scan():
        op_ob.update_tag()
        dg_o = bpy.context.evaluated_depsgraph_get()
        dg_o.update()
        ev_o = op_ob.evaluated_get(dg_o)
        me_o = ev_o.data
        mats_o = [m_.name if m_ else None for m_ in me_o.materials]
        inner_ = me_o.attributes.get("vm_inner")
        n_inner = sum(1 for d_ in inner_.data if d_.value > 0.5) if inner_ else 0
        bvh_o = BVHTree.FromObject(ev_o, dg_o)
        opens_, boards_ = [], []
        for inst in dg_o.object_instances:
            if not (inst.is_instance and inst.parent is not None and inst.parent.original == op_ob):
                continue
            m_ = inst.matrix_world.copy()
            bb_ = [Vector(c_) for c_ in inst.object.bound_box]
            lo_ = Vector([min(c_[i] for c_ in bb_) for i in range(3)])
            hi_ = Vector([max(c_[i] for c_ in bb_) for i in range(3)])
            if inst.object.name.startswith(("Window", "Door")):
                sc_ = m_.to_scale()
                opens_.append(dict(name=inst.object.name, c=m_ @ ((lo_ + hi_) / 2),
                                   u=(m_.to_3x3() @ Vector((1, 0, 0))).normalized(),
                                   n=(m_.to_3x3() @ Vector((0, 1, 0))).normalized(),
                                   up=(m_.to_3x3() @ Vector((0, 0, 1))).normalized(),
                                   hu=(hi_.x - lo_.x) / 2 * sc_.x - 0.03, hz=(hi_.z - lo_.z) / 2 * sc_.z - 0.03))
            elif inst.object.name in board_kinds:
                zm_ = (lo_.z + hi_.z) / 2
                boards_.append([m_ @ Vector((lo_.x + (hi_.x - lo_.x) * k_ / 8, 0.0, zm_)) for k_ in range(9)])
        rays_ = []
        w2l_ = op_ob.matrix_world.inverted()              # the BVH is in object space
        for o_ in opens_:
            hit_ = bvh_o.ray_cast(w2l_ @ (o_["c"] + o_["n"] * 1.0), w2l_.to_3x3() @ -o_["n"], 30.0)
            rays_.append((o_["name"], None if hit_[0] is None else round(hit_[3], 2),
                          None if hit_[0] is None else mats_o[me_o.polygons[hit_[2]].material_index]))
        return opens_, boards_, rays_, n_inner, mats_o
    opens_o, boards_o, rays_o, inner_o, mats_on = opening_scan()
    # through every opening: nothing at the wall (1 m in front of the opening)
    # - the ray runs on into the interior (or out through an opening opposite)
    through = [r_ for r_ in rays_o if r_[1] is None or r_[1] > 1.2]
    sees_in = [r_ for r_ in rays_o if r_[2] == "VM_WallWeatheredPlanks"]
    check("v2.15(openings cut): every door and window opening is cut THROUGH the wall - jambs, and "
          "behind it the INTERIOR (inside walls / floor), not a solid wall",
          len(opens_o) >= 3 and len(through) == len(rays_o) and sees_in and inner_o > 0
          and "VM_SidingBoard" in mats_on,
          f"{len(opens_o)} openings, rays (first hit m, material)={rays_o}, interior faces={inner_o}")
    inside_hole = 0
    for pts_ in boards_o:
        for p_ in pts_:
            if any(abs((p_ - o_["c"]).dot(o_["u"])) < o_["hu"] - 0.01
                   and abs((p_ - o_["c"]).dot(o_["up"])) < o_["hz"] - 0.01
                   and abs((p_ - o_["c"]).dot(o_["n"])) < 0.3 for o_ in opens_o):
                inside_hole += 1
                break
    near_open = sum(1 for pts_ in boards_o if any(
        abs((pts_[4] - o_["c"]).dot(o_["n"])) < 0.3 and abs((pts_[4] - o_["c"]).dot(o_["up"])) < o_["hz"] + 0.3
        and min(abs((p_ - o_["c"]).dot(o_["u"])) for p_ in (pts_[0], pts_[8])) < o_["hu"] + 0.05
        for o_ in opens_o))
    check("v2.15(siding cut): the siding is cut around every opening - boards stop at its sides, "
          "boards above / below are notched, NO board crosses an opening",
          inside_hole == 0 and near_open > 0,
          f"{len(boards_o)} boards, crossing an opening={inside_hole}, cut at an opening={near_open}")
    wl_ = op_ob.modifiers["VM_SceneDetailer_Windows"]
    set_params(wl_, wl_.node_group, {"Cut Openings": False})
    opens_f, boards_f, rays_f, inner_f, _m = opening_scan()
    set_params(wl_, wl_.node_group, {"Cut Openings": True})
    solid = [r_ for r_ in rays_f if r_[1] is not None and r_[1] < 1.2]
    check("v2.15(cut off): Cut Openings off = the v2.14 wall (solid behind the openings, no interior)",
          len(solid) == len(rays_f) and inner_f == 0,
          f"rays={rays_f}, interior faces={inner_f}, boards {len(boards_o)} cut / {len(boards_f)} uncut")
    results["openings_v215"] = dict(openings=len(opens_o), rays=rays_o, interior_faces=inner_o,
                                    boards_crossing=inside_hole, boards_cut=near_open)

    # ---- v2.16: damage reaches the corner boards and the openings (the
    # user's 'the damage should have affected those corner boards', 'the
    # windows can't float on a few planks')
    def corner_cover(ob_, cx_, cy_):
        ob_.update_tag()
        dg_e = bpy.context.evaluated_depsgraph_get()
        dg_e.update()
        me_e = ob_.evaluated_get(dg_e).data
        mn_e = [m_.name if m_ else None for m_ in me_e.materials]
        w_ = ob_.matrix_world
        spans_ = []
        for p_ in me_e.polygons:
            if not mn_e or mn_e[p_.material_index] != "VM_SidingBoard":
                continue
            vs_ = [w_ @ me_e.vertices[v_].co for v_ in p_.vertices]
            if all(abs(v_.x - cx_) < 0.2 and abs(v_.y - cy_) < 0.2 for v_ in vs_):
                spans_.append((min(v_.z for v_ in vs_), max(v_.z for v_ in vs_)))
        zs_ = [0.15 + 0.1 * k_ for k_ in range(27)]
        return sum(1 for z_ in zs_ if any(a_ - 0.01 <= z_ <= b_ + 0.01 for a_, b_ in spans_)) / len(zs_)
    # the v2.13 zone (Empty at the cottage's (6, 0) corner) is still on dz_ob
    cov_hit = corner_cover(dz_ob, 61.0, 12.0)
    cov_far = corner_cover(dz_ob, 55.0, 16.5)
    check("v2.16(corner boards): a damage zone on a corner breaks its corner board - pieces gone, "
          "broken short or hanging loose - while a corner outside the zone keeps its full board",
          cov_hit < 0.75 and cov_far > 0.95,
          f"corner board height covered: in the zone {cov_hit:.0%}, outside {cov_far:.0%}")
    # a zone on one window of the cutting house: that window is gone or hangs,
    # windows well outside the radius stay exactly where they were
    def open_keys():
        op_ob.update_tag()
        dg_k = bpy.context.evaluated_depsgraph_get()
        dg_k.update()
        out_ = {}
        for inst in dg_k.object_instances:
            if inst.is_instance and inst.parent is not None and inst.parent.original == op_ob \
                    and inst.object.name.startswith(("Window", "Door")):
                m_ = inst.matrix_world
                out_[(inst.object.name,) + tuple(round(x_, 3) for x_ in m_.translation)
                     + tuple(round(x_, 3) for x_ in m_.to_quaternion())] = m_.translation.copy()
        return out_
    ok_clean = open_keys()

    def panes():
        # v2.18: the glass panes (instances carrying a pane size) and how broken
        dg_g = bpy.context.evaluated_depsgraph_get()
        dg_g.update()
        gs_ = op_ob.evaluated_get(dg_g).evaluated_geometry()     # keep it alive while reading
        pc_ = gs_.instances_pointcloud()
        if pc_ is None or "vm_gsize" not in pc_.attributes:
            return []
        sz_, bk_ = pc_.attributes["vm_gsize"].data, pc_.attributes["vm_gbrk"].data
        xf_ = pc_.attributes["instance_transform"].data            # (point .co is not the place)
        return [(op_ob.matrix_world @ xf_[i_].value.to_translation(), bk_[i_].value)
                for i_ in range(len(pc_.points)) if sz_[i_].vector.length > 0.01]
    gl_clean = panes()
    n_win = sum(1 for k_ in ok_clean if k_[0].startswith("Window"))
    tgt_ = next(o_ for o_ in opens_o if o_["name"].startswith("Window"))
    oz_emp = vmt.add_damage_zone(op_ob, tgt_["c"].copy(), fx_scene.collection, amount=0.95)
    n_olayers = len(vmt.opening_damage_layers(op_ob))
    ok_dmg = open_keys()

    def hole_faces():
        # v2.17: the broken edges of the wall holes (cut faces marked vm_cutter 2)
        dg_h = bpy.context.evaluated_depsgraph_get()
        dg_h.update()
        me_h = op_ob.evaluated_get(dg_h).data
        a_ = me_h.attributes.get("vm_cutter")
        if a_ is None or a_.domain != "FACE":
            return []
        return [op_ob.matrix_world @ me_h.polygons[i_].center for i_, d_ in enumerate(a_.data)
                if d_.value > 1.5]
    holes_dmg = hole_faces()

    def backing_scan():
        # v2.20: rays straight at the wall round the damaged window (not the
        # window itself): how many stop on the bare host face behind the
        # cladding (outward-facing, at the wall plane - not a board, trim or
        # hole edge) and how many go INTO the building
        op_ob.update_tag()
        dg_b = bpy.context.evaluated_depsgraph_get()
        dg_b.update()
        me_b = op_ob.evaluated_get(dg_b).data
        trim_b = me_b.attributes.get("vm_trim")
        n_b = tgt_["n"].normalized()
        sd_b = n_b.cross(Vector((0.0, 0.0, 1.0))).normalized()
        back_b, deep_b, tot_b = 0, 0, 0
        for i_ in range(-16, 17):
            for k_ in range(-12, 13):
                if abs(i_) < 7 and abs(k_) < 8:
                    continue
                q_ = tgt_["c"] + sd_b * (i_ * 0.1) + Vector((0.0, 0.0, k_ * 0.1))
                hit_b, loc_b, _nb, idx_b, obh_b, _mb = fx_scene.ray_cast(dg_b, q_ + n_b, -n_b, distance=6.0)
                tot_b += 1
                if not hit_b or (loc_b - q_ - n_b).length > 1.25:
                    deep_b += 1
                    continue
                if obh_b is None or obh_b.original != op_ob or idx_b >= len(me_b.polygons):
                    continue
                pl_ = me_b.polygons[idx_b]
                if trim_b is not None and trim_b.domain == "FACE" and trim_b.data[idx_b].value > 0.5:
                    continue
                if (op_ob.matrix_world.to_3x3() @ pl_.normal).normalized().dot(n_b) > 0.7:
                    back_b += 1
        return back_b, deep_b, tot_b
    bk_on = backing_scan()
    wl_h = op_ob.modifiers["VM_SceneDetailer_Windows"]
    set_params(wl_h, wl_h.node_group, {"Wall Holes": 0.0})
    bk_off = backing_scan()
    set_params(wl_h, wl_h.node_group, {"Wall Holes": 1.0})
    check("v2.20(no backing): the boards ARE the wall - where the damage took them you look INTO the "
          "building, never at a bare wall behind them (at most 3 %: the chips of worn boards; Wall Holes 0 "
          "shows that bare wall)",
          bk_on[2] > 0 and bk_on[0] <= 0.03 * bk_on[2] and bk_on[1] > 0.04 * bk_on[2]
          and bk_off[0] > 0.04 * bk_off[2],
          f"rays round the damaged window: bare wall {bk_on[0]}/{bk_on[2]}, into the building {bk_on[1]}; "
          f"Wall Holes 0: bare wall {bk_off[0]}, into {bk_off[1]}")
    results["backing_v220"] = dict(bare=bk_on[0], into=bk_on[1], rays=bk_on[2], bare_noholes=bk_off[0])
    gl_dmg = panes()
    changed_ = [k_ for k_ in ok_clean if k_ not in ok_dmg]
    hit_ = [k_ for k_ in changed_ if (ok_clean[k_] - tgt_["c"]).length < 1.2]
    far_moved = [k_ for k_ in changed_ if (ok_clean[k_] - tgt_["c"]).length > vmt.DAMAGE_ZONE_RADIUS + 1.5]
    check("v2.16(openings damaged): a damage zone on a window removes it or leaves it hanging off a "
          "corner (a door swings open) - no opening sits untouched in a stripped wall; openings "
          "outside the zone stay exactly in place",
          n_olayers == 1 and hit_ and not far_moved,
          f"opening layers damaged={n_olayers}, {len(ok_clean)} openings -> {len(ok_dmg)} intact or "
          f"moved, changed near the zone={len(hit_)}, changed far away={len(far_moved)}")
    for m_ in vmt.damage_layers(op_ob) + vmt.opening_damage_layers(op_ob):
        set_params(m_, m_.node_group, {"Damage": False})
    bpy.data.objects.remove(oz_emp)
    ok_back = open_keys()
    check("v2.16(openings heal): Damage off puts every opening back exactly",
          ok_back.keys() == ok_clean.keys(), f"identical={ok_back.keys() == ok_clean.keys()}")
    holes_off = hole_faces()
    gl_off = panes()
    h_far = max(((c_ - tgt_["c"]).length for c_ in holes_dmg), default=0.0)
    check("v2.17(wall holes): the heart of a damage zone breaks THROUGH the wall (ragged holes, "
          "their broken edges in the interior boards) - only inside the zone (a gap board may reach half a "
          "metre past its edge), none with Damage off",
          len(holes_dmg) > 0 and h_far < vmt.DAMAGE_ZONE_RADIUS + 0.5 and not holes_off,
          f"hole edge faces: zone {len(holes_dmg)} (farthest {h_far:.2f} m from its centre), "
          f"damage off {len(holes_off)}")
    check("v2.18(glass): every window cut by the layer is glazed - one pane per window, whole "
          "while Damage is off",
          n_win >= 3 and len(gl_clean) == n_win and all(b_ == 0.0 for _p, b_ in gl_clean),
          f"{n_win} windows, {len(gl_clean)} panes, broken={[round(b_, 2) for _p, b_ in gl_clean]}")
    gl_near = [b_ for p_, b_ in gl_dmg if (p_ - tgt_["c"]).length < 1.2]
    check("v2.18(glass broken): in a damage zone the window's glass is smashed (or gone with the "
          "window); Damage off makes every pane whole again",
          all(b_ >= 0.4 for b_ in gl_near) and len(gl_off) == n_win
          and all(b_ == 0.0 for _p, b_ in gl_off),
          f"panes at the damaged window={[round(b_, 2) for b_ in gl_near]}, panes after Damage off="
          f"{len(gl_off)} (broken {sum(1 for _p, b_ in gl_off if b_ > 0)})")
    # v2.19: vines climb the walls, cling to them, stop at the eaves
    def vine_scan():
        op_ob.update_tag()                      # a socket write alone does not re-evaluate
        dg_v = bpy.context.evaluated_depsgraph_get()
        dg_v.update()
        ev_v = op_ob.evaluated_get(dg_v)
        gs_v = ev_v.evaluated_geometry()
        pc_v = gs_v.instances_pointcloud()
        refs_v = list(gs_v.instance_references())
        ri_v = pc_v.attributes[".reference_index"].data if pc_v is not None and             ".reference_index" in pc_v.attributes else []
        stem_pts, n_leaf = [], 0
        for i_, r_ in enumerate(refs_v):
            me_r = getattr(r_, "mesh", None)
            if me_r is None or not me_r.materials:
                continue
            mn_r = {m_.name for m_ in me_r.materials if m_}
            n_use = sum(1 for d_ in ri_v if d_.value == i_)
            if "VM_VineStem" in mn_r:
                stem_pts += [op_ob.matrix_world @ v_.co for v_ in me_r.vertices][::7]
            if "VM_VineLeaf" in mn_r:
                n_leaf += n_use
        bvh_v = BVHTree.FromObject(ev_v, dg_v)
        w2l_v = op_ob.matrix_world.inverted()
        off_ = []
        for p_ in stem_pts:
            loc_, nrm_, _i, d_ = bvh_v.find_nearest(w2l_v @ p_)
            if loc_ is not None:
                # (inside only when clearly behind the face: a point level with
                # a board's end face lies beside it, not in it)
                off_.append(-d_ if (w2l_v @ p_ - loc_).dot(nrm_) < -0.5 * d_ else d_)
        return stem_pts, n_leaf, off_
    wl_v = op_ob.modifiers["VM_SceneDetailer_Windows"]
    # (-5 mm: a root vertex measured against the floor face it starts on)
    # this stage's file has no library materials yet: the scan tells stems
    # and leaves apart by theirs
    v_mats = {"Stem Material": bpy.data.materials.get("VM_VineStem")
              or make_principled("VM_VineStem", (0.09, 0.06, 0.035), rough=0.85),
              "Leaf Material": bpy.data.materials.get("VM_VineLeaf") or make_leaf_material("VM_VineLeaf")}
    set_params(wl_v, wl_v.node_group, dict(v_mats, Vines=True))
    vs_pts, vs_leaf, vs_off = vine_scan()
    set_params(wl_v, wl_v.node_group, {"Vines": False})
    vo_pts, vo_leaf, _vo = vine_scan()
    vs_top = max((p_.z for p_ in vs_pts), default=0.0)
    check("v2.19(vines) / v2.20(ivy): Vines on GROWS ivy over the building - leafy stems from the "
          "ground, creeping just in front of the surfaces (never inside them); Vines off = none",
          len(vs_pts) > 50 and vs_leaf >= 100 and vs_top > 1.2 and vs_off
          and min(vs_off) > -0.005 and max(vs_off) < 0.3 and not vo_pts and vo_leaf == 0,
          f"stem samples={len(vs_pts)}, leaves={vs_leaf}, top={vs_top:.2f} m, off the wall "
          f"{min(vs_off, default=0):.3f}-{max(vs_off, default=0):.3f} m, off: {len(vo_pts)} / {vo_leaf}")
    results["vines_v219"] = dict(stem_samples=len(vs_pts), leaves=vs_leaf, top=round(vs_top, 2),
                                 off_min=round(min(vs_off, default=0), 3),
                                 off_max=round(max(vs_off, default=0), 3))
    results["glass_v218"] = dict(windows=n_win, panes=len(gl_clean), near_broken=gl_near,
                                 panes_off=len(gl_off))
    results["damage_v216"] = dict(corner_cover_zone=round(cov_hit, 3), corner_cover_far=round(cov_far, 3),
                                  openings_changed=len(changed_), near=len(hit_), far=len(far_moved),
                                  hole_faces=len(holes_dmg), hole_far=round(h_far, 2))

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
