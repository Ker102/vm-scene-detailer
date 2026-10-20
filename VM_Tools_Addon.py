bl_info = {
    "name": "VM Tools - Modifier Quick Controls",
    "author": "kristo / ViperMesh",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "Properties > Modifiers tab | 3D Viewport N-Panel > VM",
    "description": "One-click hide/restore ALL modifiers on selected objects (clean view for base-shape editing)",
    "category": "Object",
}

import bpy
import json

STATE_KEY = "vm_mod_vis_state"


class VM_OT_toggle_all_modifiers(bpy.types.Operator):
    bl_idname = "vm.toggle_all_modifiers"
    bl_label = "Toggle All Modifiers"
    bl_description = ("Hide ALL modifiers on selected objects (clean view for editing "
                      "the base shape); click again to restore exactly what was visible")
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


class VM_PT_panel_modifiers(bpy.types.Panel):
    bl_label = "VM Tools"
    bl_idname = "VM_PT_tools_modifiers"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "modifier"

    def draw(self, context):
        row = self.layout.row()
        row.scale_y = 1.6
        row.operator(VM_OT_toggle_all_modifiers.bl_idname, icon='RESTRICT_VIEW_OFF')
        self.layout.label(text="One click = clean view, click again = restore.")


class VM_PT_panel_view3d(bpy.types.Panel):
    bl_label = "VM Tools"
    bl_idname = "VM_PT_tools_view3d"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "VM"

    def draw(self, context):
        row = self.layout.row()
        row.scale_y = 1.5
        row.operator(VM_OT_toggle_all_modifiers.bl_idname, icon='RESTRICT_VIEW_OFF')


classes = (VM_OT_toggle_all_modifiers, VM_PT_panel_modifiers, VM_PT_panel_view3d)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
