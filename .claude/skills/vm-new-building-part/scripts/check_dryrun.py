"""Dry-run ONE block of new checks from build_engine.main() in minutes, instead
of the 50-min full build. The block runs from the line holding `from:<text>`
(e.g. the "# ---- v2.32: ROOF DAMAGE" comment) to the next "    # ---- v"
section comment, against the library the last full build wrote
(build/VM_Assets.blend - the build only copies it to build/stage at the very end).
  blender -b --factory-startup --python .claude/skills/vm-new-building-part/scripts/check_dryrun.py -- "from:v2.32: ROOF DAMAGE" [rebuild] [pools:all]
`rebuild` swaps in the node groups built from the working copy of
build_engine.py (~2.5 min) - use it after changing nodes. Asset pools come
from the library (a NEW pool needs one full build first); `pools:all` (or
pools:<collection>,...) refills the roof pools from the working copy's makers.
The block sees: fx_cube, check, results, fx_scene, vmt, set_params and the
module globals of build_engine (constants, helpers)."""
import bpy, sys, os, time, importlib.util
import builtins, functools
from collections import Counter
from mathutils import Matrix, Vector
builtins.print = functools.partial(builtins.print, flush=True)
HERE = r"C:\Users\krist\Desktop\main-projects\Projects\vm-scene-detailer"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FROM = next((a[5:] for a in ARGS if a.startswith("from:")), None)
if not FROM:
    raise SystemExit("give from:<text of the block's first comment line>")
T0 = time.time()
spec = importlib.util.spec_from_file_location("VM_Tools_Addon", os.path.join(HERE, "VM_Tools_Addon.py"))
vmt = importlib.util.module_from_spec(spec); sys.modules["VM_Tools_Addon"] = vmt; spec.loader.exec_module(vmt)
bpy.ops.wm.read_factory_settings(use_empty=True)
vmt.register(); vmt.LIBRARY_PATH_OVERRIDE = os.path.join(HERE, "build", "VM_Assets.blend")
sys.path.insert(0, HERE)
import build_engine as be
vmt.import_engine(vmt.LIBRARY_PATH_OVERRIDE, [])     # the pack in first (as in main(): pools exist)
# (a rebuilt group must carry the LIBRARY's version label: the add-on's
# import step (run by Dress / Apply Preset) swaps any group whose version
# differs from the library's back to the library copy - silently testing the
# old nodes after an ENGINE_VERSION bump)
be.ENGINE_VERSION = vmt.library_info(vmt.LIBRARY_PATH_OVERRIDE).get("engine_version", be.ENGINE_VERSION)
if "rebuild" in ARGS:
    for nm_, fn_ in (("VM_SceneDetailer", be.build_node_group), ("VM_RoofCap", be.build_roofcap_group)):
        old_ = bpy.data.node_groups[nm_]; new_ = fn_()
        old_.user_remap(new_); bpy.data.node_groups.remove(old_); new_.name = nm_
    print(f"REBUILT {time.time() - T0:.0f}s")
# v2.35 `pools:all` / `pools:<collection>,<collection>`: refill tile pools from
# the working copy's makers (a changed asset set, a pool layout the checks
# depend on) - same makers and counts as the library build in main(); the
# materials stay the library's (the checks measure geometry)
POOLS = {
    "VM_Tiles_Shingle": (be.make_shake_variants, "VM_Shake", 6),
    "VM_Tiles_ShingleBroken": (be.make_broken_shakes, "VM_Shake", 12),
    "VM_Tiles_ShingleWorn": (be.make_worn_shakes, "VM_Shake", 20),
    "VM_Tiles_ShakeShard": (be.make_roof_shards, "VM_Shake", 12),
    "VM_Tiles_Shingle_Asphalt": (be.make_asphalt_tabs, "VM_Asphalt", 8),
    "VM_Tiles_Shingle_AsphaltBroken": (be.make_torn_asphalt, "VM_Asphalt", 10),
    "VM_Tiles_Shingle_AsphaltWorn": (be.make_worn_asphalt, "VM_Asphalt", 20),
    "VM_Tiles_AsphaltShard": (lambda c_, n_, k_, m_: be.make_roof_shards(c_, n_, k_, m_, asphalt=True, seed=61),
                              "VM_Asphalt", 10),
}
PSEL = next((a[6:] for a in ARGS if a.startswith("pools:")), None)
if PSEL:
    for cn_ in (POOLS if PSEL == "all" else PSEL.split(",")):
        maker_, mat_, n_ = POOLS[cn_]
        col_ = bpy.data.collections[cn_]
        for ob_ in list(col_.objects):
            bpy.data.objects.remove(ob_)
        maker_(col_, cn_.replace("VM_Tiles_", ""), n_, bpy.data.materials[mat_])
    print(f"POOLS {PSEL} {time.time() - T0:.0f}s")
src = open(os.path.join(HERE, "build_engine.py"), encoding="utf-8").read()
a = src.index(FROM)
a = src.rindex("\n", 0, a) + 1
b = src.index("\n    # ---- v", a + 10)
block = "\n".join(l_[4:] for l_ in src[a:b].split("\n"))
print(f"BLOCK {block.count(chr(10))} lines from {FROM!r}")
fx_scene = bpy.context.scene


def fx_cube(name, x):
    c_ = be.make_cube(name, 2.0, fx_scene.collection)
    c_.location = (x, 0, 0)
    bpy.ops.object.select_all(action='DESELECT')
    c_.select_set(True)
    fx_scene.view_layers[0].objects.active = c_
    return c_


n_fail = [0]


def check(name, cond, detail):
    n_fail[0] += 0 if cond else 1
    print(f"  CHECK {name}: {'PASS' if cond else 'FAIL'}  ({detail})")


g = dict(be.__dict__)
g.update(fx_cube=fx_cube, check=check, results={}, fx_scene=fx_scene, vmt=vmt, Counter=Counter,
         Matrix=Matrix, Vector=Vector, set_params=be.set_params, bpy=bpy)
exec(compile(block, "check_block", "exec"), g)
print(f"DONE {time.time() - T0:.0f}s, {n_fail[0]} failed")
