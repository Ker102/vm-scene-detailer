"""Print a tile maker's vm_wear / vm_cut per height band, to find what makes
a colour artefact (a gouge band, a crisp `z <` line) before touching the
material. Makes the pools in a factory-startup file; no library needed.
  blender -b --factory-startup --python attr_profile.py -- <maker> [n] [maker n ...]
  e.g. -- make_worn_shakes 20 make_torn_asphalt 4
Prints for 3 variants of each: bottom-to-top bands 'wear/cut' (means over the
band's vertices, front and back), and how many FRONT vertices carry cut > 0.5."""
import bpy, sys
sys.path.insert(0, r"C:\Users\krist\Desktop\main-projects\Projects\vm-scene-detailer")
import build_engine as be
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["make_worn_shakes", "20"]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
mat = bpy.data.materials.new("m")
pairs = [(args[i], int(args[i + 1]) if i + 1 < len(args) and args[i + 1].isdigit() else 6)
         for i in range(len(args)) if not args[i].isdigit()]
for fn_name, n in pairs:
    col = bpy.data.collections.new(fn_name); sc.collection.children.link(col)
    getattr(be, fn_name)(col, fn_name, n, mat)
    obs = sorted(col.objects, key=lambda o: o.name)
    for ob in obs[::max(len(obs) // 3, 1)][:3]:
        me = ob.data
        if "vm_cut" not in me.attributes:
            print(ob.name, "no vm_ attributes (an intact _tile_mesh tile)")
            continue
        w_a, c_a = me.attributes["vm_wear"], me.attributes["vm_cut"]
        zs = [v.co.z for v in me.vertices]
        lo, hi = min(zs), max(zs)
        bins = [[0, 0.0, 0.0] for _ in range(12)]
        ys = sorted(v.co.y for v in me.vertices)
        back = ys[0] + 1e-4
        n_front = n_cut = 0
        for v in me.vertices:
            k = min(int((v.co.z - lo) / (hi - lo + 1e-9) * 12), 11)
            bins[k][0] += 1; bins[k][1] += w_a.data[v.index].value; bins[k][2] += c_a.data[v.index].value
            if v.co.y > back:
                n_front += 1; n_cut += c_a.data[v.index].value > 0.5
        print(f"{ob.name} z {lo:.2f}..{hi:.2f} front cut>0.5: {n_cut}/{n_front}")
        print("   bands wear/cut, bottom first:",
              " ".join(f"{b_[1] / max(b_[0], 1):.2f}/{b_[2] / max(b_[0], 1):.2f}" for b_ in bins))
