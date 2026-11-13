bl_info = {
    "name": "VM Engine - Import / Update / Presets / Dress",
    "author": "kristo / ViperMesh",
    "version": (2, 36, 0),
    "blender": (4, 2, 0),
    "location": "Properties > Modifiers tab | 3D Viewport N-Panel > VM",
    "description": "The VM engine's interface across .blend files: import or update the engine + asset library from VM_Assets.blend, apply clean base presets or your own, dress any mesh in one click, copy/paste setups",
    "category": "Object",
}

import bpy
import re
import json
import os
import math
import time
from bpy.props import BoolProperty, EnumProperty, StringProperty

# ------------------------------------------------------------------ constants
VM_GROUPS = ("VM_SceneDetailer", "VM_RoofCap")
PRESET_DIR = os.path.expanduser(os.path.join("~", ".config", "vm_engine", "presets"))
STATE_KEY = "vm_mod_vis_state"          # Toggle All Modifiers memory
COPY_KEY = "vm_engine_setup_copy"       # Copy/Paste Engine Setup buffer (scene custom prop)

ID_SOCKETS = {
    "NodeSocketCollection": "collections",
    "NodeSocketObject": "objects",
    "NodeSocketMaterial": "materials",
    "NodeSocketImage": "images",
}

# materials auto-wired by NAME when they exist in the file (never a hard
# dependency: missing materials are simply left for the user to assign)
AUTO_MATERIALS = {
    "VM_SceneDetailer_Planks": {
        # v2.12: the wall surface is only seen where siding is missing - old
        # dark sheathing boards behind it
        "Wall Material": "VM_Sheathing",
        # v2.11: the roof surface is only ever seen between the shakes - a dark
        # underlay, not a second roof texture
        "Roof Material": "VM_RoofUnderlay",
        "Edge Board Material": "VM_SidingBoard",
        # v2.10: no grass on the building's own bottom - the floor layer below
        # covers it with boards and a wood material
    },
    "VM_SceneDetailer_Shingles": {"Edge Board Material": "VM_Shake"},
    "VM_SceneDetailer_Floor": {"Floor Material": "VM_WallWeatheredPlanks"},
    # v2.24: the porch posts / beam and its deck boards
    "VM_RoofCap": {"Roof Material": "VM_RoofUnderlay", "Porch Material": "VM_SidingBoard",
                   "Deck Material": "VM_WallWeatheredPlanks"},
    # v2.15: the windows layer cuts every opening - board jambs, weathered
    # bare boards inside
    "VM_SceneDetailer_Windows": {"Jamb Material": "VM_SidingBoard",
                                 "Interior Material": "VM_WallWeatheredPlanks",
                                 "Interior Floor Material": "VM_WallWeatheredPlanks",
                                 # v2.18: glass in every window, broken in damage
                                 "Glass Material": "VM_WindowGlass",
                                 # v2.19: vines (off until turned on)
                                 "Stem Material": "VM_VineStem", "Leaf Material": "VM_VineLeaf"},
}

# v2.10: the pack collections each layer uses by default - wired BY NAME when
# they exist in the file (after Import Engine they always do)
AUTO_COLLECTIONS = {
    # v2.13: broken pieces + worn tiles for the Damage panel
    "VM_SceneDetailer_Planks": {"Primary Props": "VM_Tiles_Plank",
                                "Broken Props": "VM_Tiles_PlankBroken",
                                "Worn Props": "VM_Tiles_PlankWorn"},
    "VM_SceneDetailer_Floor": {"Primary Props": "VM_Tiles_Plank"},
    "VM_SceneDetailer_Shingles": {"Primary Props": "VM_Tiles_Shingle",
                                  "Broken Props": "VM_Tiles_ShingleBroken",
                                  "Worn Props": "VM_Tiles_ShingleWorn"},
    "VM_SceneDetailer_Door": {"Primary Props": "VM_Doors"},
    # v2.29: the diagonal sheathing boards behind the damaged siding
    "VM_SceneDetailer_Windows": {"Primary Props": "VM_Windows",
                                 "Sheathing Props": "VM_Tiles_Sheathing",
                                 "Stud Props": "VM_Tiles_Stud",
                                 # v2.29: the yard props (Poly Haven CC0)
                                 "Yard Wall Props": "VM_Yard_Wall",
                                 "Yard Clutter Props": "VM_Yard_Clutter",
                                 "Yard Plant Props": "VM_Yard_Plants",
                                 "Yard Shrub Props": "VM_Yard_Shrubs",
                                 # v2.32: the roof under a hole + shards round it
                                 "Batten Props": "VM_Tiles_Batten",
                                 "Rafter Props": "VM_Tiles_Rafter",
                                 "Roof Debris Props": "VM_Tiles_ShakeShard"},
}
DEBRIS_COLLECTION = "VM_Debris_Trash"

LIBRARY_COLLECTION = "AssetLibrary"    # root of the pack collections in VM_Assets.blend
PRESETS_TEXT = "VM_Presets"            # JSON text datablock in VM_Assets.blend
LIBRARY_PATH_OVERRIDE = ""             # tests / scripts: force a library file
BASE_PRESET = "Base - Flat roof"       # what Dress Object applies


# ------------------------------------------------------------------ helpers
def group_base(ng):
    return ng.name.split(".")[0] if ng else ""


def is_vm_modifier(m):
    """VM_* named node modifiers, or any modifier backed by a VM node group.
    Everything else is a NON-VM modifier and is never copied/pasted/touched."""
    if m.type != 'NODES':
        return False
    if m.name.startswith("VM_"):
        return True
    return m.node_group is not None and group_base(m.node_group) in VM_GROUPS


def vm_modifiers(ob):
    return [m for m in ob.modifiers if is_vm_modifier(m)]


def resolve_group(base_name):
    exact = bpy.data.node_groups.get(base_name)
    if exact is not None and group_base(exact) == base_name:
        return exact
    for cand in bpy.data.node_groups:
        if group_base(cand) == base_name:
            return cand
    return None


def find_input(ng, key):
    """Interface INPUT socket lookup: identifier FIRST (rename-safe), then the
    display name as fallback across group revisions."""
    by_name = None
    for it in ng.interface.items_tree:
        if it.item_type == 'SOCKET' and it.in_out == 'INPUT':
            if it.identifier == key:
                return it
            if it.name == key and by_name is None:
                by_name = it
    return by_name


def read_socket(mod, ng, it):
    """Serialize one modifier socket value -> [kind, socket_type, payload].
    ID pointers are stored BY NAME so presets travel across .blend files.
    Returns None for geometry/unsupported sockets."""
    sock = getattr(mod.properties.inputs, it.identifier, None)
    if sock is None:
        return None
    st = it.socket_type
    try:
        if st in ID_SOCKETS:
            v = getattr(sock, "value", None)
            return ["id", st, v.name if v else None]
        if st == 'NodeSocketVector':
            return ["vec", st, [float(x) for x in sock.value]]
        if st in ('NodeSocketFloat', 'NodeSocketInt', 'NodeSocketBool',
                  'NodeSocketString', 'NodeSocketMenu'):
            v = getattr(sock, "value", None)
            if st == 'NodeSocketFloat':
                v = float(v)
            elif st == 'NodeSocketInt':
                v = int(v)
            elif st == 'NodeSocketBool':
                v = bool(v)
            else:
                v = str(v)
            return ["val", st, v]
    except Exception:
        return None
    return None


def write_socket(mod, ng, key, payload, warnings):
    """Set one modifier socket from a serialized payload. Rename-safe
    (identifier first, name fallback). Missing datablocks / old-group sockets
    are REPORTED into `warnings`, never silently dropped."""
    it = find_input(ng, key)
    if it is None:
        warnings.append(f"socket '{key}' not present in {ng.name} (different group revision)")
        return False
    sock = getattr(mod.properties.inputs, it.identifier, None)
    if sock is None:
        warnings.append(f"socket '{key}' has no modifier input on {ng.name}")
        return False
    kind, st, val = payload
    try:
        if kind == "id":
            ref = None
            if val:
                ref = getattr(bpy.data, ID_SOCKETS[st]).get(val)
                if ref is None:
                    warnings.append(f"{st.replace('NodeSocket', '').lower()} '{val}' "
                                    f"not found in this file - '{key}' left empty")
            sock.value = ref
        elif kind == "vec":
            sock.value = tuple(val)
        else:
            sock.value = val
        return True
    except Exception as e:
        warnings.append(f"socket '{key}' ({st}) not set: {e}")
        return False


def snapshot_object(ob):
    """FULL copy of every VM modifier on `ob`: node group + every socket value
    keyed by interface IDENTIFIER (rename-safe) + display names for reports."""
    out = []
    for m in ob.modifiers:
        if not is_vm_modifier(m):
            continue
        ng = m.node_group
        if ng is None:
            continue
        vals = {}
        for it in ng.interface.items_tree:
            if it.item_type != 'SOCKET' or it.in_out != 'INPUT':
                continue
            if it.socket_type == 'NodeSocketGeometry':
                continue
            payload = read_socket(m, ng, it)
            if payload is not None:
                vals[it.identifier] = [it.name, payload]
        out.append(dict(name=m.name, group=group_base(ng), group_full=ng.name, values=vals))
    return out


def apply_snapshot(ob, snap, warnings):
    """Fully REPLACE the VM stack of `ob` with `snap` (non-VM modifiers are
    left untouched). Returns the number of modifiers applied."""
    for m in list(ob.modifiers):
        if is_vm_modifier(m):
            ob.modifiers.remove(m)
    n = 0
    for spec in snap:
        ng = bpy.data.node_groups.get(spec.get("group_full")) or resolve_group(spec["group"])
        if ng is None:
            warnings.append(f"node group '{spec['group']}' missing in this file - "
                            f"modifier '{spec['name']}' NOT created (append the VM "
                            f"node groups or add VM_Assets.blend to the Asset Browser)")
            continue
        m = ob.modifiers.new(spec["name"], 'NODES')
        m.node_group = ng
        for ident, (disp, payload) in spec.get("values", {}).items():
            if disp == "Engine Version":
                continue        # a label of the GROUP, never carried by a preset
            write_socket(m, ng, ident, payload, warnings)
        n += 1
    ob.update_tag()
    return n


def count_sockets(snap):
    return sum(len(s.get("values", {})) for s in snap)


# ------------------------------------------------------------------ v2.7 dress recipe
def dress_stack():
    """The FULL default engine stack, layer by layer: interior floorboards ->
    VM_RoofCap (Flat by default) -> wall cladding -> roof cladding -> doors ->
    windows. Collection sockets stay EMPTY here; dress_object / the library
    presets wire the pack collections by name."""
    base = {
        "Debris Ratio": ["val", "", 0.0],
        "Embed": ["val", "", 0.02],
        "Scale Min": ["val", "", 1.0],
        "Scale Max": ["val", "", 1.0],
        "Primary Props": ["id", "NodeSocketCollection", None],
        "Debris/Trash Props": ["id", "NodeSocketCollection", None],
    }
    planks = dict(base, **{
        "Placement Mode": ["val", "", "Cladding"],
        "Face Zone": ["val", "", "Walls"],
        # v2.11 lap siding: 17 cm courses, each board laps the one below
        # (board = row / (1 - overlap) = 21 cm), joints staggered, boards cut
        # to every wall and gable outline
        "Row Height": ["val", "", 0.17], "Row Overlap": ["val", "", 0.19],
        "Stagger": ["val", "", 0.37], "Jitter": ["val", "", 0.0],
        "Slot Width": ["val", "", 2.4], "Surface Offset": ["val", "", 0.0],
        "Trim To Face": ["val", "", True],
        "Max Instances": ["val", "", 6000],
        # v2.11 corner boards over the siding ends on every outside corner
        "Edge Boards": ["val", "", True],
        "Edge Board Width": ["val", "", 0.1], "Edge Board Thickness": ["val", "", 0.025],
        "Edge Board Offset": ["val", "", 0.024],
        # v2.12 damage is opt-in (Add Damage Zone / the Weathered preset)
        "Damage": ["val", "", False], "Max Tilt": ["val", "", math.radians(12.0)],
    })
    # v2.10: floorboards on the building's bottom, laid from the inside
    floor = dict(base, **{
        "Placement Mode": ["val", "", "Cladding"],
        "Face Zone": ["val", "", "Interior Floor"],
        "Row Height": ["val", "", 0.16], "Row Overlap": ["val", "", 0.0],
        "Stagger": ["val", "", 0.5], "Jitter": ["val", "", 0.0],
        "Slot Width": ["val", "", 1.6], "Surface Offset": ["val", "", 0.0],
        "Trim To Face": ["val", "", True],
        "Max Instances": ["val", "", 4000],
    })
    roof = {
        "Style": ["val", "", "Flat"],            # v2.7 default: never invent gables
        "Incline": ["val", "", math.radians(2.5)],
        "Fascia": ["val", "", 0.12],
        "Pitch": ["val", "", math.radians(35.0)],
        "Overhang": ["val", "", 0.25],
        # v2.11 Gable/Hip are framed like real roofs (flush gable ends, eave
        # drop, slab with fascia + soffit); Flat is unaffected
        "Built Roof": ["val", "", True],
        "Roof Thickness": ["val", "", 0.12],
    }
    shingles = dict(base, **{
        "Placement Mode": ["val", "", "Cladding"],
        "Face Zone": ["val", "", "Roof"],
        # v2.11 wooden shakes: 13 cm exposure, each shake 42 cm long (three
        # layers deep), ~25 cm apart, cut flush at the eave and the ridge
        "Row Height": ["val", "", 0.13], "Row Overlap": ["val", "", 0.69],
        "Stagger": ["val", "", 0.5], "Jitter": ["val", "", 0.0],
        "Slot Width": ["val", "", 0.8], "Surface Offset": ["val", "", 0.0],
        "Trim To Face": ["val", "", True],
        "Max Instances": ["val", "", 8000],
        # v2.11 ridge cap (and hip caps) over the top courses
        "Edge Boards": ["val", "", True],
        "Edge Board Width": ["val", "", 0.13], "Edge Board Thickness": ["val", "", 0.025],
        "Edge Board Offset": ["val", "", 0.045],
        "Damage": ["val", "", False], "Max Tilt": ["val", "", math.radians(8.0)],
    })
    slots = dict(base, **{
        "Placement Mode": ["val", "", "Fit"],
        "Face Zone": ["val", "", "Walls"],
        "Slot Layout": ["val", "", "Slots"],
        "Count Mode": ["val", "", "Per Width"],
        "Openings Per Width": ["val", "", 2.5],
        "Opening Fit": ["val", "", "Scale To Face"],   # v2.6/v2.7 contract
        "Min Fit Scale": ["val", "", 0.5],
        "Sill Line": ["val", "", "Common Z"],
        "Stand On Face Base": ["val", "", True],
        "Min Gap X": ["val", "", 0.4], "Min Gap Z": ["val", "", 0.3],
        "Slot Rows": ["val", "", 1], "Row Spacing": ["val", "", 2.4],
        "Slot Jitter": ["val", "", 0.02], "No-Repeat": ["val", "", True],
        "Backing Offset": ["val", "", 0.0435],
        "Ground Tolerance": ["val", "", 0.1],
        "Max Instances": ["val", "", 40],
    })
    doors = dict(slots, **{
        "Column Select": ["val", "", "First Only"],
        "Sill Height": ["val", "", 0.0],
        "Opening Width": ["val", "", 1.4], "Opening Height": ["val", "", 2.1],
        "Min Face Width": ["val", "", 0.6], "Min Face Height": ["val", "", 1.2],
        "Ground Floor Only": ["val", "", True],
        "Max Base Height": ["val", "", 0.5],
        "Max Instances": ["val", "", 1],     # v2.10: ONE front door, not one per wall
    })
    wins = dict(slots, **{
        "Column Select": ["val", "", "All"],  # v2.10: the door's slot is already taken
        "Sill Height": ["val", "", 0.9],
        "Opening Width": ["val", "", 0.8], "Opening Height": ["val", "", 0.9],
        "Min Face Width": ["val", "", 1.2], "Min Face Height": ["val", "", 1.1],
        "Scale Min": ["val", "", 0.5], "Scale Max": ["val", "", 0.5],
        "Ground Floor Only": ["val", "", False],
        # v2.10: upper storeys get windows too - no base-height ceiling, one
        # row per 3 m storey on a tall wall (rows that do not fit are dropped)
        "Max Base Height": ["val", "", 1000.0],
        "Slot Rows": ["val", "", 16], "Row Spacing": ["val", "", 3.0],
        # v2.15: the LAST opening layer cuts the door's and the windows'
        # openings through the wall (jambs, interior, siding cut around them)
        "Cut Openings": ["val", "", True],
        "Opening Inset": ["val", "", 0.03], "Wall Depth": ["val", "", 0.15],
        "Window Glass": ["val", "", True],
        # v2.29: barrels, crates, plants, bushes, logs round the building
        "Yard": ["val", "", True],
    })
    return [
        # v2.11: the roof cap runs BEFORE the wall planks so its gable
        # triangles get siding too; the floor stays first (the cap's underside
        # is never mistaken for a floor)
        ("VM_SceneDetailer_Floor", "VM_SceneDetailer", floor),
        ("VM_RoofCap", "VM_RoofCap", roof),
        ("VM_SceneDetailer_Planks", "VM_SceneDetailer", planks),
        ("VM_SceneDetailer_Shingles", "VM_SceneDetailer", shingles),
        ("VM_SceneDetailer_Door", "VM_SceneDetailer", doors),
        ("VM_SceneDetailer_Windows", "VM_SceneDetailer", wins),
    ]


def dress_object(ob, warnings):
    stack = dress_stack()
    for m in list(ob.modifiers):
        if is_vm_modifier(m) and any(m.name == nm for nm, _, _ in stack):
            ob.modifiers.remove(m)
    applied = 0
    for mod_name, group, vals in stack:
        ng = resolve_group(group)
        if ng is None:
            warnings.append(f"node group '{group}' missing in this file - "
                            f"'{mod_name}' NOT created (append the VM node groups first)")
            continue
        m = ob.modifiers.new(mod_name, 'NODES')
        m.node_group = ng
        for key, payload in vals.items():
            write_socket(m, ng, key, payload, warnings)
        for key, mat_name in AUTO_MATERIALS.get(mod_name, {}).items():
            if bpy.data.materials.get(mat_name) is not None:
                write_socket(m, ng, key, ["id", "NodeSocketMaterial", mat_name], warnings)
        if group == "VM_SceneDetailer":
            cols = dict(AUTO_COLLECTIONS.get(mod_name, {}), **{"Debris/Trash Props": DEBRIS_COLLECTION})
            for key, col_name in cols.items():
                if bpy.data.collections.get(col_name) is not None:
                    write_socket(m, ng, key, ["id", "NodeSocketCollection", col_name], warnings)
        applied += 1
    ob.update_tag()
    return applied


# ------------------------------------------------------------------ v2.10 engine library
def _addon_prefs(context=None):
    context = context or bpy.context
    addon = context.preferences.addons.get(__name__)
    return addon.preferences if addon else None


def library_path(context=None):
    """VM_Assets.blend to import from: override -> add-on preference -> next to
    this add-on -> the usual delivery folder. Returns '' when none exists."""
    prefs = _addon_prefs(context)
    cands = [LIBRARY_PATH_OVERRIDE, os.environ.get("VM_LIBRARY", ""),
             getattr(prefs, "library_path", "") if prefs else "",
             managed_library(),                 # where 'Check for Updates' installs it
             os.path.join(os.path.dirname(os.path.abspath(__file__)), "VM_Assets.blend"),
             os.path.expanduser(os.path.join("~", "Downloads", "blender-engine", "VM_Assets.blend"))]
    for c in cands:
        if c and os.path.isfile(bpy.path.abspath(c)):
            return bpy.path.abspath(c)
    return ""


_LIB_CACHE = {}


def _blend_json(path, text_name):
    """The JSON text datablock `text_name` of a .blend (cached per file and mtime);
    {} if the file or the text cannot be read."""
    if not path or not os.path.isfile(path):
        return {}
    key = (path, os.path.getmtime(path), text_name)
    if key in _LIB_CACHE:
        return _LIB_CACHE[key]
    info = {}
    if bpy.data.filepath and os.path.samefile(path, bpy.data.filepath):
        t = bpy.data.texts.get(text_name)          # Blender cannot load from the open file
        return json.loads(t.as_string()) if t else {}
    before = set(bpy.data.texts)
    try:
        with bpy.data.libraries.load(path, link=False) as (src, dst):
            dst.texts = [text_name] if text_name in src.texts else []
        for t in dst.texts:
            if t is not None:
                info = json.loads(t.as_string())
    except Exception as e:
        print(f"VM: cannot read {path}: {e}")
    finally:
        for t in set(bpy.data.texts) - before:
            bpy.data.texts.remove(t)
    if info:                                       # never cache a failed read
        for k in [k for k in _LIB_CACHE if k[0] == path and k[2] == text_name]:
            del _LIB_CACHE[k]
        _LIB_CACHE[key] = info
    return info


def library_info(path):
    """{'engine_version', 'presets': {name: {description, modifiers}}} from the
    library's VM_Presets text; {} if unreadable."""
    return _blend_json(path, PRESETS_TEXT)


# ------------------------------------------------------------------ example assets
# The engine's own library (VM_Assets.blend) ships NO doors, windows or yard props:
# its VM_Doors / VM_DoorHandles / VM_Windows / VM_Yard_* collections are empty
# placeholders for the user's own objects. The example set used for the demo builds
# (Sketchfab CC-BY doors and windows, Poly Haven CC0 yard) is a separate, optional
# file, VM_ExampleAssets.blend: an 'AssetLibrary' root of the same layout whose
# objects carry ob['vm_example'] and a 'VM_ExampleInfo' text (credits, collections).
EXAMPLES_ASSET = "VM_ExampleAssets.blend"
EXAMPLES_TEXT = "VM_ExampleInfo"


def example_library_path(context=None):
    """VM_ExampleAssets.blend: env VM_EXAMPLES -> where 'Check for Updates' puts it
    -> next to the library -> next to this add-on -> the delivery folder; '' if none."""
    lib = library_path(context)
    cands = [os.environ.get("VM_EXAMPLES", ""), managed_examples(),
             os.path.join(os.path.dirname(lib), EXAMPLES_ASSET) if lib else "",
             os.path.join(os.path.dirname(os.path.abspath(__file__)), EXAMPLES_ASSET),
             os.path.expanduser(os.path.join("~", "Downloads", "blender-engine", EXAMPLES_ASSET))]
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return ""


def example_info(path):
    return _blend_json(path, EXAMPLES_TEXT)


def examples_missing(path):
    """Example objects (by name, in their collection) this file does not have yet."""
    out = []
    for col, names in example_info(path).get("collections", {}).items():
        c = bpy.data.collections.get(col)
        out += [n for n in names if c is None or c.objects.get(n) is None]
    return out


def import_examples(path, report, context=None):
    """Append the example set and merge it into the engine's placeholder
    collections (imports the engine first when this file has none). Objects the
    file already has are kept as they are."""
    if resolve_group("VM_SceneDetailer") is None or bpy.data.collections.get(LIBRARY_COLLECTION) is None:
        lib = library_path(context)
        if lib:
            import_engine(lib, report)
    if not examples_missing(path):
        report.append("the example assets are already in this file")
        return report
    before = {k: {d.name_full for d in getattr(bpy.data, k)} for k in DEDUPE_KINDS}
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.collections = [LIBRARY_COLLECTION] if LIBRARY_COLLECTION in src.collections else []
    if not any(c is not None for c in dst.collections):
        raise RuntimeError(f"{os.path.basename(path)} has no '{LIBRARY_COLLECTION}' collection")
    _merge_appended(before, prefer_new=False)
    col = bpy.data.collections.get(LIBRARY_COLLECTION)
    if col is not None:
        col.use_fake_user = False
        scene = (context or bpy.context).scene
        if scene.collection.children.get(col.name) is None:
            scene.collection.children.link(col)
        _exclude_from_view_layers(col)
    added = [o for o in bpy.data.objects if o.name_full not in before["objects"] and o.get("vm_example")]
    report.append(f"added {len(added)} example assets (doors, windows, yard props and plants)")
    return report


def group_version(ng):
    if ng is None:
        return ""
    for it in ng.interface.items_tree:
        if it.item_type == 'SOCKET' and it.name == "Engine Version":
            return str(getattr(it, "default_value", "") or "")
    return "pre-v2.7"


def sync_version_labels(ng):
    """Modifiers keep their own copy of every input, so after a group update the
    About panel would still show the old 'Engine Version' - reset it on every
    modifier that uses `ng` to the group's (new) default."""
    its = [it for it in (find_input(ng, "Engine Version"), find_input(ng, "Usage Hint")) if it is not None]
    if not its:
        return
    for ob in bpy.data.objects:
        for m in ob.modifiers:
            if m.type == 'NODES' and m.node_group == ng:
                for it in its:
                    sock = getattr(m.properties.inputs, it.identifier, None)
                    if sock is not None:
                        sock.value = it.default_value


def file_engine_version():
    ng = resolve_group("VM_SceneDetailer")
    return group_version(ng) if ng else ""


def default_collections():
    return sorted({c for d in AUTO_COLLECTIONS.values() for c in d.values()} | {DEBRIS_COLLECTION})


def _exclude_from_view_layers(col):
    def walk(lc):
        if lc.collection == col:
            lc.exclude = True
            return True
        return any(walk(ch) for ch in lc.children)
    for scene in bpy.data.scenes:
        if col.name in scene.collection.children:
            for vl in scene.view_layers:
                walk(vl.layer_collection)


# node_groups: the packs' own groups (Auto Smooth, plant shader groups); the VM groups
# and their '.VM_* NN' parts are updated by import_engine / _tidy_engine_parts instead
DEDUPE_KINDS = ("collections", "objects", "meshes", "materials", "images", "node_groups")


def _is_engine_group(g):
    return group_base(g) in VM_GROUPS or any(g.name.startswith("." + b + " ") for b in VM_GROUPS)


def _input_ids(ng):
    return {it.identifier for it in ng.interface.items_tree
            if it.item_type == 'SOCKET' and it.in_out == 'INPUT'}


def fill_new_slots(new_ids):
    """After an UPDATE every modifier keeps its values, but a socket the old
    engine did not have (v2.32 'Batten Props', 'Rafter Props', 'Roof Debris
    Props'...) starts EMPTY, while Dress Object fills it - so an updated house
    would have roof holes with no battens under them. Fill the default material
    / collection slot of those NEW sockets only (`new_ids`: group base ->
    identifiers added by this update); slots that existed before keep whatever
    the user chose, empty included."""
    n = 0
    for ob in bpy.data.objects:
        for m in vm_modifiers(ob):
            ng = m.node_group
            fresh = new_ids.get(group_base(ng)) if ng is not None else None
            if not fresh:
                continue
            want = [(k, "NodeSocketMaterial", v) for k, v in AUTO_MATERIALS.get(m.name, {}).items()]
            if group_base(ng) == "VM_SceneDetailer":
                cols = dict(AUTO_COLLECTIONS.get(m.name, {}), **{"Debris/Trash Props": DEBRIS_COLLECTION})
                want += [(k, "NodeSocketCollection", v) for k, v in cols.items()]
            for key, st, name in want:
                it = find_input(ng, key)
                if it is None or it.identifier not in fresh:
                    continue
                sock = getattr(m.properties.inputs, it.identifier, None)
                ref = getattr(bpy.data, ID_SOCKETS[st]).get(name)
                if sock is not None and sock.value is None and ref is not None:
                    sock.value = ref
                    n += 1
    return n


def _lib_name(d):
    wr = d.library_weak_reference
    return wr.id_name[2:] if wr is not None else re.sub(r"\.\d{3}$", "", d.name)


def _merge_appended(before, prefer_new):
    """Appending the node groups also appends everything they reference (the
    pack collections, their objects, meshes, materials, images), so after an
    import each of those can exist twice: the file's own and the library's
    '.001' copy. Merge every such pair into ONE datablock.
      prefer_new=False (same engine version, something was missing): keep the
        file's own; the library copy is dropped.
      prefer_new=True (UPDATE from an older engine): the library's NEW assets
        replace the old ones (new tile pools, new materials), so an update
        really looks like the new engine - but only datablocks that came from
        the library before; anything of the user's that merely shares a name
        is kept.
    Whatever only the dropped collection holds (objects or collections the
    user added, or new pieces of a pack) moves into the kept one.
    The two AssetLibrary roots are never remapped onto each other (both are
    children of the scene collection - remapping one onto the other never
    returns); the dropped root is simply deleted. Each pair is one remap and
    everything dropped goes in ONE batch_remove: per-ID remove() on a big file
    took hours (v2.36 fix)."""
    old_root = bpy.data.collections.get(LIBRARY_COLLECTION)
    if old_root is not None and old_root.name_full not in before["collections"]:
        old_root = None
    old_assets = {o.name_full for o in old_root.all_objects} if old_root is not None else set()
    pairs = []                                  # (kind, keep, drop, lib_name, rename)
    for kind in DEDUPE_KINDS:
        coll = getattr(bpy.data, kind)
        for d in [d for d in coll if d.name_full not in before[kind] and d.library is None]:
            if kind == "node_groups" and _is_engine_group(d):
                continue
            lib_name = _lib_name(d)
            old = coll.get(lib_name)
            if old is None or old == d or old.name_full not in before[kind]:
                continue
            wr_o, wr_n = old.library_weak_reference, d.library_weak_reference
            from_lib = ((wr_o is not None and wr_n is not None and wr_o.id_name == wr_n.id_name)
                        or (kind == "objects" and old.name_full in old_assets)
                        or (kind == "collections" and lib_name == LIBRARY_COLLECTION))
            if prefer_new and from_lib:
                pairs.append((kind, d, old, lib_name, True))
            else:
                pairs.append((kind, old, d, lib_name, False))
    if not pairs:
        return 0
    dropped = {dr.as_pointer() for _k, _kp, dr, _n, _r in pairs}

    def gone(x):
        return x.as_pointer() in dropped
    for kind, keep, drop, lib_name, _r in pairs:
        if kind != "collections":
            continue
        for o in list(drop.objects):
            if not gone(o) and keep.objects.get(o.name) is None:
                keep.objects.link(o)
        for c in list(drop.children):
            if not gone(c) and c != keep and keep.children.get(c.name) is None:
                keep.children.link(c)
    for kind, keep, drop, lib_name, _r in pairs:
        if not (kind == "collections" and lib_name == LIBRARY_COLLECTION):
            drop.user_remap(keep)
    bpy.data.batch_remove([drop for _k, _kp, drop, _n, _r in pairs])
    for kind, keep, _d, lib_name, rename in pairs:
        if rename and keep.name != lib_name:
            keep.name = lib_name
    return len(pairs)


def _tidy_engine_parts():
    """Since v2.31 each VM group is built from hidden subgroups '.<group> NN'.
    After an update the old group's parts are unused and the appended ones got
    '.001' names: drop the unused parts and give the live ones their library
    names back, so updates never pile up copies."""
    for base in VM_GROUPS:
        pre = "." + base + " "
        for g in [g for g in bpy.data.node_groups if g.name.startswith(pre) and g.users == 0]:
            bpy.data.node_groups.remove(g)
        for g in [g for g in bpy.data.node_groups if g.name.startswith(pre)]:
            want = re.sub(r"\.\d{3}$", "", g.name)
            if want != g.name and bpy.data.node_groups.get(want) is None:
                g.name = want


def import_engine(path, report):
    """Bring the engine into the CURRENT file without duplicating anything:
    missing node groups, the pack collections (AssetLibrary tree, excluded from
    the view layer so the asset objects stay out of sight) and the default
    materials. OUTDATED node groups are updated in place: every modifier is
    remapped to the library version and keeps its values (socket identifiers
    are stable across engine builds)."""
    lib_version = library_info(path).get("engine_version", "")
    want_cols = [c for c in default_collections() if bpy.data.collections.get(c) is None]
    want_mats = sorted({m for d in AUTO_MATERIALS.values() for m in d.values()
                        if bpy.data.materials.get(m) is None})
    missing = [g for g in VM_GROUPS if resolve_group(g) is None]
    outdated = [g for g in VM_GROUPS if g not in missing and lib_version
                and group_version(resolve_group(g)) != lib_version]
    if not (missing or outdated or want_cols or want_mats):
        return report
    before = {k: {d.name_full for d in getattr(bpy.data, k)} for k in DEDUPE_KINDS}
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.node_groups = [g for g in missing + outdated if g in src.node_groups]
        # an update brings the whole pack tree too, so every pool is the new engine's
        dst.collections = [LIBRARY_COLLECTION] if ((want_cols or outdated)
                                                   and LIBRARY_COLLECTION in src.collections) else []
        dst.materials = [m for m in want_mats if m in src.materials]
    got_root = any(c is not None for c in dst.collections)
    new_ids = {}                                # group base -> sockets this update adds
    for ng in dst.node_groups:
        if ng is None:
            continue
        if ng.asset_data is not None:
            ng.asset_clear()
        base = group_base(ng)
        old = resolve_group(base) if base in outdated else None
        if old is not None and old != ng:
            new_ids[base] = _input_ids(ng) - _input_ids(old)
            old_v = group_version(old)
            old_name = old.name
            old.user_remap(ng)
            bpy.data.node_groups.remove(old)
            ng.name = old_name
            sync_version_labels(ng)
            report.append(f"updated {base} {old_v} -> {group_version(ng)}")
        else:
            ng.name = base
            report.append(f"imported {base} {group_version(ng)}")
    _tidy_engine_parts()
    mat_names = [_lib_name(m) for m in dst.materials if m is not None]    # names after the merge
    n_merged = _merge_appended(before, prefer_new=bool(outdated))
    col = bpy.data.collections.get(LIBRARY_COLLECTION)
    if got_root and col is not None:
        scene = bpy.context.scene
        if scene.collection.children.get(col.name) is None:
            scene.collection.children.link(col)
        _exclude_from_view_layers(col)
        report.append(("updated" if outdated else "imported")
                      + f" the asset pack ({len(col.children_recursive)} collections)")
    if outdated and n_merged:
        report.append(f"{n_merged} asset datablocks replaced by the library's")
    n_slots = fill_new_slots(new_ids)
    if n_slots:
        report.append(f"{n_slots} new default slot(s) filled (e.g. roof battens / rafters)")
    mats = [bpy.data.materials[n] for n in mat_names if bpy.data.materials.get(n) is not None]
    for mat in mats:
        mat.use_fake_user = True
    if mats:
        report.append(f"imported {len(mats)} default material(s)")
    return report


def user_presets():
    if not os.path.isdir(PRESET_DIR):
        return []
    return sorted(f[:-5] for f in os.listdir(PRESET_DIR) if f.endswith(".json"))


_PRESET_ITEMS = []


def preset_items(self, context):
    """Dropdown: the library's clean base presets first, then the user's own."""
    items = []
    for name, p in library_info(library_path(context)).get("presets", {}).items():
        items.append(("lib:" + name, name, p.get("description", "")))
    for name in user_presets():
        items.append(("user:" + name, name + " (mine)", "Saved with VM: Save Preset"))
    if not items:
        items.append(("none", "No presets found", "Set the VM_Assets.blend path in the add-on preferences"))
    _PRESET_ITEMS[:] = items       # Blender needs the item strings kept alive
    return _PRESET_ITEMS


def load_preset_snapshot(key, context=None):
    kind, _, name = key.partition(":")
    if kind == "lib":
        p = library_info(library_path(context)).get("presets", {}).get(name)
        return p.get("modifiers") if p else None
    if kind == "user" and os.path.isfile(_preset_path(name)):
        with open(_preset_path(name)) as f:
            return json.load(f).get("modifiers")
    return None


# ------------------------------------------------------------------ operators
class VM_OT_import_engine(bpy.types.Operator):
    bl_idname = "vm.import_engine"
    bl_label = "Import / Update Engine"
    bl_description = ("Bring the VM engine into this file from VM_Assets.blend: missing node "
                      "groups, the asset pack collections and default materials. Older engine "
                      "groups are updated in place - every modifier keeps its settings")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        path = library_path(context)
        if not path:
            self.report({'WARNING'}, "VM_Assets.blend not found - set its path in the add-on preferences")
            return {'CANCELLED'}
        report = import_engine(path, [])
        for g in VM_GROUPS:
            if resolve_group(g) is not None:
                sync_version_labels(resolve_group(g))
        if report:                      # nothing imported: no need to re-evaluate every house
            for ob in context.scene.objects:
                if vm_modifiers(ob):
                    ob.update_tag()
        self.report({'INFO'}, ("; ".join(report) if report else "Engine already up to date")
                    + f" (engine {file_engine_version()})")
        return {'FINISHED'}


class VM_OT_import_examples(bpy.types.Operator):
    bl_idname = "vm.import_examples"
    bl_label = "Add Example Assets"
    bl_description = ("Add the optional example doors, windows and yard props / plants "
                      "(VM_ExampleAssets.blend) to this file's asset collections, so dressed "
                      "houses get openings and a yard. Your own objects there stay")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        path = example_library_path(context)
        if not path:
            self.report({'WARNING'}, "VM_ExampleAssets.blend not found - tick 'Include example "
                                     "assets' under Updates and download it, or put it next to "
                                     "VM_Assets.blend")
            return {'CANCELLED'}
        try:
            report = import_examples(path, [], context)
        except Exception as e:
            self.report({'ERROR'}, f"Example assets not added: {e}")
            return {'CANCELLED'}
        for ob in context.scene.objects:
            if vm_modifiers(ob):
                ob.update_tag()
        self.report({'INFO'}, "; ".join(report))
        return {'FINISHED'}


class VM_OT_apply_preset(bpy.types.Operator):
    bl_idname = "vm.apply_preset"
    bl_label = "Apply Preset"
    bl_description = ("Replace the VM stack of the selected object(s) with a CLEAN preset - the "
                      "library's base presets (pack collections at default settings) or one you "
                      "saved. Imports the engine first if this file does not have it")
    bl_options = {'REGISTER', 'UNDO'}

    preset: StringProperty(name="Preset", default="")

    @classmethod
    def poll(cls, context):
        return any(o.type == 'MESH' for o in context.selected_objects)

    def execute(self, context):
        key = self.preset or getattr(context.scene, "vm_preset_choice", "")
        snap = load_preset_snapshot(key, context)
        if not snap:
            self.report({'WARNING'}, f"Preset '{key}' not found")
            return {'CANCELLED'}
        path = library_path(context)
        report = import_engine(path, []) if path else []
        targets = [o for o in context.selected_objects if o.type == 'MESH']
        warnings = []
        total = sum(apply_snapshot(ob, snap, warnings) for ob in targets)
        self.report({'INFO'}, f"'{key.partition(':')[2]}' applied: {total} modifiers on "
                              f"{len(targets)} object(s)" + (f" ({'; '.join(report)})" if report else ""))
        if warnings:
            self.report({'WARNING'}, f"{len(warnings)} note(s): " + "; ".join(sorted(set(warnings))[:6]))
        return {'FINISHED'}


class VM_OT_toggle_all_modifiers(bpy.types.Operator):
    bl_idname = "vm.toggle_all_modifiers"
    bl_label = "Toggle All Modifiers"
    bl_description = ("Hide ALL modifiers on selected objects (clean view for base-shape "
                      "editing); click again to restore exactly what was visible")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return any(o.modifiers for o in context.selected_objects)

    def execute(self, context):
        objs = [o for o in context.selected_objects if o.modifiers]
        if not objs:
            self.report({'WARNING'}, "No modifiers on selected objects")
            return {'CANCELLED'}
        scn = context.scene
        stored = json.loads(scn.get(STATE_KEY, "{}"))
        any_visible = any(m.show_viewport for o in objs for m in o.modifiers)

        if any_visible:
            mem = {o.name: [m.show_viewport for m in o.modifiers] for o in objs}
            stored.update(mem)
            scn[STATE_KEY] = json.dumps(stored)
            for o in objs:
                for m in o.modifiers:
                    m.show_viewport = False
            self.report({'INFO'}, f"Clean view: hid all modifiers on {len(objs)} object(s)")
        else:
            n = 0
            for o in objs:
                prev = stored.get(o.name)
                if prev and len(prev) == len(o.modifiers):
                    for m, v in zip(o.modifiers, prev):
                        m.show_viewport = v
                        n += 1
                else:
                    for m in o.modifiers:
                        m.show_viewport = True
                        n += 1
                stored.pop(o.name, None)
            scn[STATE_KEY] = json.dumps(stored)
            self.report({'INFO'}, f"Modifiers back: restored {n}")

        for o in objs:
            o.update_tag()
        return {'FINISHED'}


class VM_OT_dress_object(bpy.types.Operator):
    bl_idname = "vm.dress_object"
    bl_label = "VM: Dress Object"
    bl_description = ("One click: the full default stack (wall cladding + flat roof cap + roof "
                      "cladding + doors + windows) with the pack collections assigned. Imports "
                      "the engine first if this file does not have it")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return any(o.type == 'MESH' for o in context.selected_objects)

    def execute(self, context):
        targets = [o for o in context.selected_objects if o.type == 'MESH']
        if not targets:
            self.report({'WARNING'}, "Select at least one mesh object")
            return {'CANCELLED'}
        warnings = []
        total = 0
        path = library_path(context)
        report = import_engine(path, []) if path else []
        base = load_preset_snapshot("lib:" + BASE_PRESET, context) if path else None
        for ob in targets:
            total += apply_snapshot(ob, base, warnings) if base else dress_object(ob, warnings)
        for ob in targets:
            ob.update_tag()
        msg = (f"VM stack applied to {len(targets)} object(s) ({total} modifiers)"
               + (f" - {'; '.join(report)}" if report else ""))
        self.report({'INFO'}, msg)
        if warnings:
            self.report({'WARNING'}, "; ".join(sorted(set(warnings))[:6]))
        return {'FINISHED'}


DAMAGE_ZONE_RADIUS = 2.5


def damage_layers(ob):
    """v2.12: the object's cladding layers that can take damage (any VM layer in
    Cladding placement with the Damage panel - the interior floor excluded)."""
    out = []
    for m in ob.modifiers:
        if not is_vm_modifier(m) or m.node_group is None or m.name == "VM_SceneDetailer_Floor":
            continue
        it_d = find_input(m.node_group, "Damage Object")
        it_m = find_input(m.node_group, "Placement Mode")
        if it_d is None or it_m is None:
            continue
        sock = getattr(m.properties.inputs, it_m.identifier, None)
        if sock is not None and str(sock.value) == "Cladding":
            out.append(m)
    return out


def opening_damage_layers(ob):
    """v2.16: the object's opening layers that cut their openings (Fit with
    Cut Openings on) - they damage the doors / windows they cut with the same
    damage field as the cladding."""
    out = []
    for m in ob.modifiers:
        if not is_vm_modifier(m) or m.node_group is None:
            continue
        it_c = find_input(m.node_group, "Cut Openings")
        it_m = find_input(m.node_group, "Placement Mode")
        if it_c is None or it_m is None:
            continue
        sock_c = getattr(m.properties.inputs, it_c.identifier, None)
        sock_m = getattr(m.properties.inputs, it_m.identifier, None)
        if sock_c is not None and sock_m is not None and sock_c.value and str(sock_m.value) == "Fit":
            out.append(m)
    return out


def add_damage_zone(ob, location, collection, radius=DAMAGE_ZONE_RADIUS, amount=0.85):
    """Create an Empty that drives the damage of every cladding layer of `ob`
    (move / scale the empty's position to move the damage). Returns the empty."""
    emp = bpy.data.objects.new(f"VM_DamageZone_{ob.name}", None)
    emp.empty_display_type = 'SPHERE'
    emp.empty_display_size = radius          # the sphere shows where damage fades out
    emp.location = location
    collection.objects.link(emp)
    warnings = []
    for m in damage_layers(ob) + opening_damage_layers(ob):
        for key, payload in (("Damage", ["val", "", True]),
                             ("Damage Object", ["id", "NodeSocketObject", emp.name]),
                             ("Damage Radius", ["val", "", float(radius)]),
                             ("Damage Amount", ["val", "", float(amount)])):
            write_socket(m, m.node_group, key, payload, warnings)
    ob.update_tag()
    return emp


class VM_OT_add_damage_zone(bpy.types.Operator):
    bl_idname = "vm.add_damage_zone"
    bl_label = "VM: Add Damage Zone"
    bl_description = ("Damage the selected objects' cladding around a new Empty at the 3D cursor: "
                      "missing boards and shakes at the centre, broken and loose ones around "
                      "them. Move the Empty to move the damage; its sphere is the radius")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return any(o.type == 'MESH' for o in context.selected_objects)

    def execute(self, context):
        targets = [o for o in context.selected_objects if o.type == 'MESH' and damage_layers(o)]
        if not targets:
            self.report({'WARNING'}, "No VM cladding layers on the selection - Dress Object first")
            return {'CANCELLED'}
        for ob in targets:
            add_damage_zone(ob, context.scene.cursor.location.copy(), context.collection)
        self.report({'INFO'}, f"Damage zone added to {len(targets)} object(s) - move the Empty "
                              f"to move the damage")
        return {'FINISHED'}


class VM_OT_copy_engine_setup(bpy.types.Operator):
    bl_idname = "vm.copy_engine_setup"
    bl_label = "VM: Copy Engine Setup"
    bl_description = ("Copy ALL VM_* modifiers of the active object: node group + every "
                      "socket value + collection/object references (non-VM modifiers are "
                      "never touched)")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        ob = context.active_object
        snap = snapshot_object(ob)
        if not snap:
            self.report({'WARNING'}, f"{ob.name} has no VM_* modifiers to copy")
            return {'CANCELLED'}
        context.scene[COPY_KEY] = json.dumps(snap)
        self.report({'INFO'}, f"Copied engine setup: {len(snap)} VM modifier(s), "
                              f"{count_sockets(snap)} sockets (from '{ob.name}')")
        return {'FINISHED'}


class VM_OT_paste_engine_setup(bpy.types.Operator):
    bl_idname = "vm.paste_engine_setup"
    bl_label = "VM: Paste Engine Setup"
    bl_description = ("Paste the copied engine setup onto selected object(s), fully "
                      "replacing their VM stack if present (non-VM modifiers untouched)")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return bool(context.scene.get(COPY_KEY)) and \
            any(o.type == 'MESH' for o in context.selected_objects)

    def execute(self, context):
        try:
            snap = json.loads(context.scene.get(COPY_KEY, ""))
        except Exception:
            self.report({'WARNING'}, "No valid engine setup in the copy buffer")
            return {'CANCELLED'}
        targets = [o for o in context.selected_objects if o.type == 'MESH']
        if not targets:
            self.report({'WARNING'}, "Select at least one mesh object")
            return {'CANCELLED'}
        warnings = []
        total = 0
        for ob in targets:
            total += apply_snapshot(ob, snap, warnings)
        self.report({'INFO'}, f"Pasted engine setup: {total} modifiers onto "
                              f"{len(targets)} object(s), {count_sockets(snap)} sockets each")
        if warnings:
            self.report({'WARNING'}, "; ".join(sorted(set(warnings))[:6]))
        return {'FINISHED'}


def _preset_path(name):
    return os.path.join(PRESET_DIR, name.strip() + ".json")


class VM_OT_save_preset(bpy.types.Operator):
    bl_idname = "vm.save_preset"
    bl_label = "VM: Save Preset"
    bl_description = ("Save the active object's full VM engine setup (all socket values + "
                      "collection NAMES) to ~/.config/vm_engine/presets/<name>.json so it "
                      "can travel across .blend files")
    bl_options = {'REGISTER'}

    name: StringProperty(name="Preset Name", default="")

    def execute(self, context):
        name = (self.name or getattr(context.scene, "vm_preset_name", "") or "").strip()
        if not name:
            self.report({'WARNING'}, "Give the preset a name first")
            return {'CANCELLED'}
        ob = context.active_object
        if ob is None:
            self.report({'WARNING'}, "No active object to snapshot")
            return {'CANCELLED'}
        snap = snapshot_object(ob)
        if not snap:
            self.report({'WARNING'}, f"{ob.name} has no VM_* modifiers to save")
            return {'CANCELLED'}
        os.makedirs(PRESET_DIR, exist_ok=True)
        meta = dict(engine=file_engine_version(), source_object=ob.name, modifiers=snap)
        path = _preset_path(name)
        with open(path, "w") as f:
            json.dump(meta, f, indent=2)
        self.report({'INFO'}, f"Preset '{name}' saved ({len(snap)} modifiers, "
                              f"{count_sockets(snap)} sockets) -> {path}")
        return {'FINISHED'}


class VM_OT_load_preset(bpy.types.Operator):
    bl_idname = "vm.load_preset"
    bl_label = "VM: Load Preset"
    bl_description = ("Load a saved engine preset onto selected object(s). Collections/"
                      "materials are re-matched BY NAME in the current file; missing names "
                      "are reported, never silently dropped")
    bl_options = {'REGISTER', 'UNDO'}

    name: StringProperty(name="Preset Name", default="")

    def execute(self, context):
        name = (self.name or getattr(context.scene, "vm_preset_name", "") or "").strip()
        path = _preset_path(name) if name else ""
        if not name or not os.path.isfile(path):
            avail = sorted(os.listdir(PRESET_DIR)) if os.path.isdir(PRESET_DIR) else []
            self.report({'WARNING'}, f"Preset '{name}' not found at {path} (available: {avail[:8]})")
            return {'CANCELLED'}
        with open(path) as f:
            meta = json.load(f)
        snap = meta.get("modifiers", [])
        targets = [o for o in context.selected_objects if o.type == 'MESH']
        if not targets:
            self.report({'WARNING'}, "Select at least one mesh object")
            return {'CANCELLED'}
        warnings = []
        total = 0
        for ob in targets:
            total += apply_snapshot(ob, snap, warnings)
        self.report({'INFO'}, f"Preset '{name}' loaded: {total} modifiers onto "
                              f"{len(targets)} object(s), {count_sockets(snap)} sockets each")
        if warnings:
            self.report({'WARNING'}, f"{len(warnings)} note(s): " + "; ".join(sorted(set(warnings))[:6]))
        return {'FINISHED'}


# ------------------------------------------------------------------ v2.36 updates
# 'Check for Updates' in the VM panel: the latest GitHub Release of the update
# repo carries VM_Tools_Addon.py and VM_Assets.blend, tagged with the engine
# version ('v2.37'). Downloads run in a background thread (Blender stays
# usable), every file is checked (size, sha256 when GitHub gives one, the
# version inside it) before it replaces anything, and the replaced files are
# kept as *_previous. Nothing touches the network unless Blender's 'Allow
# Online Access' is on.
ADDON_VERSION = "v2.36"                      # the engine version this add-on ships with
UPDATE_REPO = "Ker102/vm-scene-detailer"    # default 'owner/repo' whose Releases carry the files
ADDON_ASSET, LIBRARY_ASSET = "VM_Tools_Addon.py", "VM_Assets.blend"
UPDATE_DIR = os.path.expanduser(os.path.join("~", ".config", "vm_engine"))
CHECK_EVERY = 24 * 3600                      # automatic check at most once a day
_UPD = dict(status="idle", latest="", notes="", html_url="", assets={}, error="", checked=0.0,
            done=0, total=0, cancel=False, restart=False, message="", examples_sha="")
_KEEP = ("latest", "notes", "html_url", "assets", "checked", "examples_sha")   # update_state.json
_JOB = dict(thread=None, result=None)


def update_dir():
    return os.environ.get("VM_UPDATE_DIR") or UPDATE_DIR      # VM_UPDATE_DIR: tests


def managed_library():
    return os.path.join(update_dir(), "library", LIBRARY_ASSET)


def managed_examples():
    return os.path.join(update_dir(), "library", EXAMPLES_ASSET)


def _state_file():
    return os.path.join(update_dir(), "update_state.json")


def _load_update_state():
    try:
        with open(_state_file()) as f:
            d = json.load(f)
        for k in _KEEP:
            if k in d:
                _UPD[k] = d[k]
    except Exception:
        pass


def _save_update_state():
    try:
        os.makedirs(update_dir(), exist_ok=True)
        with open(_state_file(), "w") as f:
            json.dump({k: _UPD[k] for k in _KEEP}, f)
    except Exception as e:
        print(f"VM: cannot save the update state: {e}")


def ver_tuple(v):
    return tuple(int(n) for n in re.findall(r"\d+", v or "")[:3]) or (0,)


def _update_settings(context=None):
    prefs = _addon_prefs(context)
    repo = (getattr(prefs, "update_repo", "") or UPDATE_REPO).strip().strip("/")
    return repo, (getattr(prefs, "update_token", "") or "").strip()


def online_allowed():
    return bool(getattr(bpy.app, "online_access", True))


def _http(url, token="", accept="application/vnd.github+json", timeout=30):
    """GET with the GitHub headers; a token is sent to GitHub only, never to the
    storage host a download redirects to."""
    import urllib.request
    import urllib.parse

    class _Redirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            new = super().redirect_request(req, fp, code, msg, headers, newurl)
            if new is not None and (urllib.parse.urlsplit(newurl).netloc
                                    != urllib.parse.urlsplit(req.full_url).netloc):
                new.remove_header("Authorization")
            return new
    req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": "VM-Engine-Updater",
                                               "X-GitHub-Api-Version": "2022-11-28"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    return urllib.request.build_opener(_Redirect).open(req, timeout=timeout)


def fetch_latest_release(repo, token=""):
    """{latest, notes, html_url, assets: {name: {url, size, digest}}} of the repo's
    latest release (no bpy calls: safe in a thread)."""
    api = os.environ.get("VM_UPDATE_API", "https://api.github.com").rstrip("/")   # VM_UPDATE_API: tests
    with _http(f"{api}/repos/{repo}/releases/latest", token, timeout=15) as r:
        rel = json.loads(r.read().decode("utf-8"))
    assets = {a["name"]: dict(url=a["url"], size=int(a.get("size") or 0), digest=a.get("digest") or "")
              for a in rel.get("assets", [])}
    return dict(latest=rel.get("tag_name", ""), notes=rel.get("body") or "",
                html_url=rel.get("html_url", ""), assets=assets)


def installed_versions(context=None):
    path = library_path(context)
    return ADDON_VERSION, (library_info(path).get("engine_version", "") if path else "")


def examples_wanted(context=None):
    """The 'Include example assets' preference (tests without registered
    preferences set _UPD['include_examples_test'])."""
    prefs = _addon_prefs(context)
    if prefs is not None:
        return bool(getattr(prefs, "include_examples", False))
    return bool(_UPD.get("include_examples_test"))


def wanted_assets(context=None):
    """The release files this machine needs: the add-on if it is older than the
    release, the library if it is older or missing, and - only when 'Include
    example assets' is ticked - the example set if it is missing or the release
    carries a different one (compared with the sha256 recorded when it was
    installed; releases re-use the same example file until the examples change)."""
    latest = _UPD.get("latest", "")
    if not latest:
        return []
    addon_v, lib_v = installed_versions(context)
    want = []
    if ver_tuple(latest) > ver_tuple(addon_v):
        want.append(ADDON_ASSET)
    if not lib_v or ver_tuple(latest) > ver_tuple(lib_v):
        want.append(LIBRARY_ASSET)
    ex = _UPD.get("assets", {}).get(EXAMPLES_ASSET)
    if ex and examples_wanted(context):
        rec = _UPD.get("examples_sha") or ""
        if not example_library_path(context) or (rec and ex.get("digest", "").startswith("sha256:")
                                                 and ex["digest"][7:].lower() != rec):
            want.append(EXAMPLES_ASSET)
    return [a for a in want if a in _UPD.get("assets", {})]


def _apply_check(info):
    _UPD.update(latest=info["latest"], notes=info["notes"], html_url=info["html_url"],
                assets=info["assets"], checked=time.time(), error="")
    _save_update_state()


def _download(asset, dest, token):
    """Stream one release file to `dest` (thread), counting into _UPD['done'];
    the size and the sha256 GitHub publishes must match."""
    import hashlib
    h, n = hashlib.sha256(), 0
    with _http(asset["url"], token, accept="application/octet-stream", timeout=60) as r, open(dest, "wb") as f:
        while True:
            if _UPD["cancel"]:
                raise RuntimeError("cancelled")
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            h.update(chunk)
            n += len(chunk)
            _UPD["done"] += len(chunk)
    if asset.get("size") and n != asset["size"]:
        raise RuntimeError(f"{os.path.basename(dest)}: got {n} bytes, expected {asset['size']}")
    dg = asset.get("digest", "")
    if dg.startswith("sha256:") and dg[7:].lower() != h.hexdigest():
        raise RuntimeError(f"{os.path.basename(dest)}: checksum does not match the release")


def _download_job(names, token):
    """Thread body: download every wanted file into update_dir()/download."""
    out = {}
    tmp = os.path.join(update_dir(), "download")
    os.makedirs(tmp, exist_ok=True)
    for nm in names:
        dest = os.path.join(tmp, nm)                   # keeps its extension (.blend loads)
        _download(_UPD["assets"][nm], dest, token)
        out[nm] = dest
    return out


def install_downloaded(files, context=None):
    """Main thread: verify the downloaded files, then put them in place (the
    replaced ones kept as *_previous). Raises before replacing anything when a
    file is not the release it claims to be. Returns what was installed."""
    import shutil
    latest = _UPD["latest"]
    done = []
    lib_dl = files.get(LIBRARY_ASSET)
    ex_dl = files.get(EXAMPLES_ASSET)
    if ex_dl and not example_info(ex_dl).get("collections"):
        raise RuntimeError("the downloaded example file has no VM_ExampleInfo")
    if lib_dl:
        _LIB_CACHE.clear()
        got = library_info(lib_dl).get("engine_version", "")
        if got != latest:
            raise RuntimeError(f"the downloaded library says engine '{got or '?'}', the release is {latest}")
    add_dl = files.get(ADDON_ASSET)
    if add_dl:
        with open(add_dl, encoding="utf-8") as f:
            src = f.read()
        compile(src, ADDON_ASSET, "exec")
        m = re.search(r'^ADDON_VERSION\s*=\s*"([^"]+)"', src, re.M)
        if "bl_info" not in src or not m or m.group(1) != latest:
            raise RuntimeError(f"the downloaded add-on is not VM Tools {latest}")
    if lib_dl:
        dest = managed_library()
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if os.path.isfile(dest):
            os.replace(dest, os.path.join(os.path.dirname(dest), "VM_Assets_previous.blend"))
        shutil.move(lib_dl, dest)
        prefs = _addon_prefs(context)
        if prefs is not None:
            prefs.library_path = dest
        _LIB_CACHE.clear()
        done.append(f"library {latest} -> {dest}")
    if ex_dl:
        import hashlib
        h = hashlib.sha256()
        with open(ex_dl, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        dest = managed_examples()
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if os.path.isfile(dest):
            os.replace(dest, os.path.join(os.path.dirname(dest), "VM_ExampleAssets_previous.blend"))
        shutil.move(ex_dl, dest)
        _UPD["examples_sha"] = h.hexdigest()
        _save_update_state()
        _LIB_CACHE.clear()
        done.append(f"example assets -> {dest}")
    if add_dl:
        me = os.path.abspath(__file__)
        shutil.copy2(me, os.path.join(update_dir(), "VM_Tools_Addon_previous.py"))
        shutil.move(add_dl, me)
        done.append(f"add-on {latest} -> {me} (restart Blender to load it)")
    return done


def _redraw():
    wm = getattr(bpy.context, "window_manager", None)
    for win in (wm.windows if wm else []):
        for area in win.screen.areas:
            if area.type in ('VIEW_3D', 'PROPERTIES', 'PREFERENCES'):
                area.tag_redraw()


def _start_job(fn, on_done):
    """Run fn() in a thread; on_done(result, error) runs on the main thread."""
    import threading
    _JOB.update(result=None)

    def body():
        try:
            _JOB["result"] = (fn(), None)
        except Exception as e:
            _JOB["result"] = (None, e)
    _JOB["thread"] = threading.Thread(target=body, daemon=True)
    _JOB["thread"].start()

    def poll():
        _redraw()
        if _JOB["thread"].is_alive():
            return 0.25
        res, err = _JOB["result"] or (None, RuntimeError("no result"))
        on_done(res, err)
        _redraw()
        return None
    bpy.app.timers.register(poll, first_interval=0.25)


def _job_running():
    return _JOB.get("thread") is not None and _JOB["thread"].is_alive()


def _check_done(info, err, repo, quiet):
    if err is not None:
        _UPD.update(status="idle" if quiet else "error", error=f"could not check {repo}: {err}")
        return
    _apply_check(info)
    _UPD["status"] = "available" if wanted_assets() else "uptodate"


def start_check(context=None, quiet=False):
    if not online_allowed() or _job_running():
        return False
    repo, token = _update_settings(context)
    _UPD.update(status="checking", error="")
    _start_job(lambda: fetch_latest_release(repo, token),
               lambda info, err: _check_done(info, err, repo, quiet))
    return True


def _auto_check():
    """Startup timer: a quiet check at most once a day, only with online access."""
    try:
        if _job_running() or _UPD.get("status") != "idle":    # the user is already at it
            return None
        prefs = _addon_prefs()
        if prefs is not None and getattr(prefs, "auto_check_updates", True) \
                and time.time() - float(_UPD.get("checked") or 0) > CHECK_EVERY:
            start_check(quiet=True)
        elif _UPD.get("latest") and wanted_assets():
            _UPD["status"] = "available"
    except Exception as e:
        print(f"VM: update check skipped: {e}")
    return None


class VM_OT_check_updates(bpy.types.Operator):
    bl_idname = "vm.check_updates"
    bl_label = "Check for Updates"
    bl_description = ("Look for a newer VM engine (add-on + asset library) on the release page. "
                      "Needs Blender's 'Allow Online Access' (Preferences > System > Network)")

    def execute(self, context):
        if not online_allowed():
            self.report({'WARNING'}, "Online access is off - turn on Preferences > System > "
                                     "Network > Allow Online Access to check for updates")
            return {'CANCELLED'}
        if not start_check(context):
            self.report({'INFO'}, "Already busy - wait for the current check or download")
            return {'CANCELLED'}
        return {'FINISHED'}


class VM_OT_update_notes(bpy.types.Operator):
    bl_idname = "vm.update_notes"
    bl_label = "What's New"
    bl_description = "Show the release notes of the newest VM engine"

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=520)

    def draw(self, context):
        import textwrap
        col = self.layout.column(align=True)
        col.label(text=f"VM engine {_UPD.get('latest', '')}", icon='INFO')
        lines = []
        for ln in (_UPD.get("notes") or "No release notes.").splitlines():
            lines += textwrap.wrap(ln, 86) or [""]
        for ln in lines[:30]:
            col.label(text=ln)
        if len(lines) > 30:
            col.label(text="...")
        if _UPD.get("html_url"):
            self.layout.operator("wm.url_open", text="Open the release page",
                                 icon='URL').url = _UPD["html_url"]

    def execute(self, context):
        return {'FINISHED'}


class VM_OT_install_update(bpy.types.Operator):
    bl_idname = "vm.install_update"
    bl_label = "Download & Install"
    bl_description = ("Download the newer add-on and/or asset library and install them (the old "
                      "ones are kept as *_previous). Then use 'Update Engine' in each file")

    def invoke(self, context, event):
        names = wanted_assets(context)
        mb = sum(_UPD["assets"][n]["size"] for n in names) / 1e6
        return context.window_manager.invoke_confirm(
            self, event, title=f"Install VM engine {_UPD.get('latest', '')}?",
            message=f"Downloads {', '.join(names)} ({mb:.0f} MB). Blender stays usable meanwhile.",
            confirm_text="Download & Install")

    def execute(self, context):
        if not online_allowed():
            self.report({'WARNING'}, "Online access is off (Preferences > System > Network)")
            return {'CANCELLED'}
        names = wanted_assets(context)
        if not names or _job_running():
            self.report({'INFO'}, "Nothing to install" if not names else "Already busy")
            return {'CANCELLED'}
        _, token = _update_settings(context)
        _UPD.update(status="downloading", error="", done=0, cancel=False, message="",
                    total=sum(_UPD["assets"][n]["size"] for n in names))
        _start_job(lambda: _download_job(names, token), _install_done)
        return {'FINISHED'}


def _install_done(files, err):
    if err is not None:
        _UPD.update(status="error", error=f"download failed: {err}")
        return
    try:
        msg = install_downloaded(files)
    except Exception as e:
        _UPD.update(status="error", error=f"not installed: {e}")
        return
    _UPD.update(status="installed", restart=ADDON_ASSET in files, message="; ".join(msg),
                installed=sorted(files))
    print("VM: installed", msg)


class VM_OT_cancel_update(bpy.types.Operator):
    bl_idname = "vm.cancel_update"
    bl_label = "Cancel Download"
    bl_description = "Stop the download (nothing is replaced)"

    def execute(self, context):
        _UPD["cancel"] = True
        return {'FINISHED'}


def _draw_examples_opt_in(layout, context):
    prefs = _addon_prefs(context)
    if prefs is not None and EXAMPLES_ASSET in _UPD.get("assets", {}):
        layout.prop(prefs, "include_examples")


def _draw_updates(layout, context, opt_in=True):
    st = _UPD.get("status", "idle")
    want = wanted_assets(context) if st not in ("checking", "downloading") else []
    if st in ("idle", "uptodate") and not want:     # nothing to do: one quiet line
        layout.operator(VM_OT_check_updates.bl_idname,
                        text=(f"{ADDON_VERSION} is up to date - check again" if st == "uptodate"
                              else f"Check for Updates ({ADDON_VERSION})"),
                        icon='CHECKMARK' if st == "uptodate" else 'FILE_REFRESH')
        if opt_in:
            _draw_examples_opt_in(layout, context)
        return
    box = layout.box()
    box.label(text="Updates", icon='URL')
    if not online_allowed():
        box.label(text="Online access is off", icon='ERROR')
        box.operator("screen.userpref_show", text="Turn it on: Preferences > System",
                     icon='PREFERENCES').section = 'SYSTEM'
        return
    if st == "checking":
        box.label(text="Checking for updates...", icon='SORTTIME')
        return
    if st == "downloading":
        tot = max(_UPD.get("total") or 1, 1)
        box.progress(factor=min(_UPD.get("done", 0) / tot, 1.0), type='BAR',
                     text=f"Downloading {_UPD['latest']}: {_UPD['done'] / 1e6:.0f} / {tot / 1e6:.0f} MB")
        box.operator(VM_OT_cancel_update.bl_idname, icon='CANCEL')
        return
    if st == "installed":
        if _UPD.get("installed") == [EXAMPLES_ASSET]:
            box.label(text="Example assets installed", icon='CHECKMARK')
            box.label(text="'Add Example Assets' in a file.", icon='INFO')
            return
        box.label(text=f"VM engine {_UPD['latest']} installed", icon='CHECKMARK')
        if _UPD.get("restart"):
            box.label(text="Restart Blender, then", icon='INFO')
            box.label(text="'Update Engine' in each file.", icon='BLANK1')
        else:
            box.label(text="Now 'Update Engine' in each file.", icon='INFO')
        return
    if want:
        col = box.column(align=True)
        col.alert = True
        col.label(text=("Example assets ready to download" if want == [EXAMPLES_ASSET]
                        else f"VM engine {_UPD['latest']} is available"), icon='ERROR')
        mb = sum(_UPD["assets"][n]["size"] for n in want) / 1e6
        col = box.column(align=True)
        col.scale_y = 1.3
        col.operator(VM_OT_install_update.bl_idname, text=f"Download & Install ({mb:.0f} MB)", icon='IMPORT')
        box.operator(VM_OT_update_notes.bl_idname, icon='INFO')
        if opt_in:
            _draw_examples_opt_in(box, context)
    if st == "error":
        err = _UPD.get("error", "")
        for k in range(0, min(len(err), 240), 60):
            box.label(text=err[k:k + 60], icon='ERROR' if k == 0 else 'BLANK1')
    box.operator(VM_OT_check_updates.bl_idname, icon='FILE_REFRESH')


# ------------------------------------------------------------------ UI
def _draw_buttons(layout, context):
    _draw_updates(layout, context)
    path = library_path(context)
    lib_v = library_info(path).get("engine_version", "") if path else ""
    file_v = file_engine_version()
    box = layout.box()
    box.label(text="Engine", icon='NODETREE')
    box.label(text=f"This file: {file_v or 'not imported'}   Library: {lib_v or 'not found'}")
    if not path:
        box.label(text="Set VM_Assets.blend in the add-on preferences", icon='ERROR')
    elif file_v != lib_v:
        box.operator(VM_OT_import_engine.bl_idname,
                     text="Import Engine" if not file_v else f"Update Engine to {lib_v}", icon='IMPORT')
    else:
        box.operator(VM_OT_import_engine.bl_idname, text="Engine up to date (re-check)", icon='CHECKMARK')
    ex = example_library_path(context) if path else ""
    if ex and examples_missing(ex):
        box.operator(VM_OT_import_examples.bl_idname, icon='ASSET_MANAGER')

    box = layout.box()
    box.label(text="Presets", icon='PRESET')
    col = box.column(align=True)
    col.scale_y = 1.2
    col.operator(VM_OT_dress_object.bl_idname, icon='MODIFIER')
    row = col.row(align=True)
    row.prop(context.scene, "vm_preset_choice", text="")
    row.operator(VM_OT_apply_preset.bl_idname, text="Apply", icon='CHECKMARK')
    row = col.row(align=True)
    row.prop(context.scene, "vm_preset_name", text="Name")
    row.operator(VM_OT_save_preset.bl_idname, text="Save Mine", icon='FILE_TICK')

    box = layout.box()
    box.label(text="Object", icon='OBJECT_DATA')
    col = box.column(align=True)
    row = col.row(align=True)
    row.operator(VM_OT_copy_engine_setup.bl_idname, text="Copy Setup", icon='COPYDOWN')
    row.operator(VM_OT_paste_engine_setup.bl_idname, text="Paste Setup", icon='PASTEDOWN')
    col.operator(VM_OT_toggle_all_modifiers.bl_idname, icon='RESTRICT_VIEW_OFF')
    col.operator(VM_OT_add_damage_zone.bl_idname, text="Add Damage Zone", icon='MOD_EXPLODE')


class VM_PT_panel_modifiers(bpy.types.Panel):
    bl_label = "VM Tools"
    bl_idname = "VM_PT_tools_modifiers"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "modifier"

    def draw(self, context):
        _draw_buttons(self.layout, context)


class VM_PT_panel_view3d(bpy.types.Panel):
    bl_label = "VM Tools"
    bl_idname = "VM_PT_tools_view3d"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "VM"

    def draw(self, context):
        _draw_buttons(self.layout, context)


class VM_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    library_path: StringProperty(
        name="VM_Assets.blend", subtype='FILE_PATH', default="",
        description="The engine library: node groups, asset pack collections and base presets")
    auto_check_updates: BoolProperty(
        name="Check for updates automatically", default=True,
        description="Once a day, quietly look for a newer VM engine when Blender starts "
                    "(only when Preferences > System > Network > Allow Online Access is on)")
    update_repo: StringProperty(
        name="Update source", default=UPDATE_REPO,
        description="GitHub 'owner/repo' whose Releases carry VM_Tools_Addon.py and VM_Assets.blend")
    include_examples: BoolProperty(
        name="Include example assets", default=False,
        description="Also download the optional example doors, windows and yard props / plants "
                    "(VM_ExampleAssets.blend, about 140 MB; Sketchfab CC-BY and Poly Haven CC0 - the "
                    "credits are in its VM_ExampleInfo text). Without them, put your own objects in "
                    "VM_Doors, VM_Windows and VM_Yard_*")
    update_token: StringProperty(
        name="Access token", subtype='PASSWORD', default="",
        description="Only for a PRIVATE update source: a GitHub token with read access to it "
                    "(stored in your Blender preferences)")

    def draw(self, context):
        self.layout.prop(self, "library_path")
        found = library_path(context)
        self.layout.label(text=f"Using: {found}" if found else "Not found yet",
                          icon='CHECKMARK' if found else 'ERROR')
        box = self.layout.box()
        box.label(text="Updates", icon='URL')
        box.prop(self, "auto_check_updates")
        box.prop(self, "include_examples")
        box.prop(self, "update_repo")
        box.prop(self, "update_token")
        _draw_updates(box, context, opt_in=False)      # the checkbox is drawn above
        ex = example_library_path(context)
        self.layout.label(text=f"Example assets: {ex}" if ex else "Example assets: not installed (optional)",
                          icon='CHECKMARK' if ex else 'INFO')


classes = (VM_AddonPreferences, VM_OT_toggle_all_modifiers, VM_OT_dress_object,
           VM_OT_copy_engine_setup, VM_OT_paste_engine_setup, VM_OT_save_preset,
           VM_OT_load_preset, VM_OT_import_engine, VM_OT_import_examples, VM_OT_apply_preset, VM_OT_add_damage_zone,
           VM_OT_check_updates, VM_OT_update_notes, VM_OT_install_update, VM_OT_cancel_update,
           VM_PT_panel_modifiers, VM_PT_panel_view3d)


def register():
    for c in classes:
        try:
            bpy.utils.register_class(c)
        except ValueError:
            pass                     # already registered (re-register after factory reset)
    if not hasattr(bpy.types.Scene, "vm_preset_name"):
        bpy.types.Scene.vm_preset_name = StringProperty(
            name="Preset Name", default="",
            description="Name used by VM: Save Preset / VM: Load Preset")
    if not hasattr(bpy.types.Scene, "vm_preset_choice"):
        bpy.types.Scene.vm_preset_choice = EnumProperty(
            name="Preset", items=preset_items,
            description="Clean base presets from the library, then your saved presets")
    _load_update_state()
    if not bpy.app.background and not bpy.app.timers.is_registered(_auto_check):
        bpy.app.timers.register(_auto_check, first_interval=8.0, persistent=True)


def unregister():
    for c in reversed(classes):
        try:
            bpy.utils.unregister_class(c)
        except Exception:
            pass
    for prop in ("vm_preset_name", "vm_preset_choice"):
        if hasattr(bpy.types.Scene, prop):
            try:
                delattr(bpy.types.Scene, prop)
            except Exception:
                pass


if __name__ == "__main__":
    register()
