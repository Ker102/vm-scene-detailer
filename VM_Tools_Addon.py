bl_info = {
    "name": "VM Tools - Dress / Copy / Paste Engine + Modifier Controls",
    "author": "kristo / ViperMesh",
    "version": (1, 1, 0),
    "blender": (4, 2, 0),
    "location": "Properties > Modifiers tab | 3D Viewport N-Panel > VM",
    "description": "One click dresses any mesh with the full VM v2.7 engine stack; copy/paste complete engine setups between objects; save/load presets as JSON across .blend files",
    "category": "Object",
}

import bpy
import json
import os
import math
from bpy.props import StringProperty

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
        "Wall Material": "VM_WallWeatheredPlanks",
        "Roof Material": "VM_RoofClayTiles",
        "Floor Material": "VM_FloorGrass",
    },
    "VM_RoofCap": {"Roof Material": "VM_RoofClayTiles"},
}


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
            write_socket(m, ng, ident, payload, warnings)
        n += 1
    ob.update_tag()
    return n


def count_sockets(snap):
    return sum(len(s.get("values", {})) for s in snap)


# ------------------------------------------------------------------ v2.7 dress recipe
def dress_stack():
    """The FULL default v2.7 engine stack, layer by layer (the StarterCube
    recipe): wall cladding -> VM_RoofCap (Flat by default) -> roof cladding ->
    doors -> windows. Collection sockets stay EMPTY: assigning the variant
    collections in the Assets panels is the only remaining manual step."""
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
        "Row Height": ["val", "", 0.22], "Row Overlap": ["val", "", 0.05],
        "Stagger": ["val", "", 0.0], "Jitter": ["val", "", 0.002],
        "Slot Width": ["val", "", 2.0], "Surface Offset": ["val", "", -0.02],
        "Max Instances": ["val", "", 2000],
    })
    roof = {
        "Style": ["val", "", "Flat"],            # v2.7 default: never invent gables
        "Incline": ["val", "", math.radians(2.5)],
        "Fascia": ["val", "", 0.12],
        "Pitch": ["val", "", math.radians(35.0)],
        "Overhang": ["val", "", 0.25],
    }
    shingles = dict(base, **{
        "Placement Mode": ["val", "", "Cladding"],
        "Face Zone": ["val", "", "Roof"],
        "Row Height": ["val", "", 0.11], "Row Overlap": ["val", "", 0.35],
        "Stagger": ["val", "", 0.5], "Jitter": ["val", "", 0.004],
        "Slot Width": ["val", "", 0.25],
        "Max Instances": ["val", "", 4000],
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
    })
    wins = dict(slots, **{
        "Column Select": ["val", "", "Skip First"],
        "Sill Height": ["val", "", 0.9],
        "Opening Width": ["val", "", 0.8], "Opening Height": ["val", "", 0.9],
        "Min Face Width": ["val", "", 1.2], "Min Face Height": ["val", "", 1.1],
        "Scale Min": ["val", "", 0.5], "Scale Max": ["val", "", 0.5],
        "Ground Floor Only": ["val", "", False],
    })
    return [
        ("VM_SceneDetailer_Planks", "VM_SceneDetailer", planks),
        ("VM_RoofCap", "VM_RoofCap", roof),
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
        applied += 1
    ob.update_tag()
    return applied


# ------------------------------------------------------------------ operators
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
    bl_description = ("Apply the FULL default VM v2.7 stack to selected object(s): wall "
                      "cladding + VM_RoofCap (Flat) + roof cladding + doors + windows. "
                      "Only remaining step: assign the variant collections in the Assets panels")
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
        for ob in targets:
            total += dress_object(ob, warnings)
        for ob in targets:
            ob.update_tag()
        msg = (f"VM v2.7 stack applied to {len(targets)} object(s) "
               f"({total} modifiers) - now assign the variant collections in the Assets panels")
        self.report({'INFO'}, msg)
        if warnings:
            self.report({'WARNING'}, "; ".join(sorted(set(warnings))[:6]))
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
        meta = dict(engine="VM v2.7", source_object=ob.name, modifiers=snap)
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


# ------------------------------------------------------------------ UI
def _draw_buttons(layout, context):
    col = layout.column(align=True)
    col.scale_y = 1.3
    col.operator(VM_OT_toggle_all_modifiers.bl_idname, icon='RESTRICT_VIEW_OFF')
    col.operator(VM_OT_dress_object.bl_idname, icon='MODIFIER')
    row = col.row(align=True)
    row.operator(VM_OT_copy_engine_setup.bl_idname, icon='COPYDOWN')
    row.operator(VM_OT_paste_engine_setup.bl_idname, icon='PASTEDOWN')
    row = col.row(align=True)
    row.prop(context.scene, "vm_preset_name", text="Preset")
    row = col.row(align=True)
    row.operator(VM_OT_save_preset.bl_idname, icon='FILE_TICK')
    row.operator(VM_OT_load_preset.bl_idname, icon='FILE_FOLDER')
    layout.label(text="Dress = full v2.7 stack; then assign collections.")


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


classes = (VM_OT_toggle_all_modifiers, VM_OT_dress_object, VM_OT_copy_engine_setup,
           VM_OT_paste_engine_setup, VM_OT_save_preset, VM_OT_load_preset,
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


def unregister():
    for c in reversed(classes):
        try:
            bpy.utils.unregister_class(c)
        except Exception:
            pass
    if hasattr(bpy.types.Scene, "vm_preset_name"):
        try:
            del bpy.types.Scene.vm_preset_name
        except Exception:
            pass


if __name__ == "__main__":
    register()
