"""The v2.30 FLAT VM_SceneDetailer (delivered library) vs the v2.31 chunked
rebuild (same graph): multi-input link order and every node's settings /
unlinked input values, matched by creation index.
  blender -b --factory-startup --python flat_vs_chunk.py -- <v230 lib> <v231 src dir>"""
import bpy, sys, os
args = sys.argv[sys.argv.index("--") + 1:]
LIB, SRC = args[0], args[1]
with bpy.data.libraries.load(LIB, link=False) as (src, dst):
    dst.node_groups = [n for n in src.node_groups if n in ("VM_SceneDetailer", "VM_RoofCap")]
flat = {ng.name: ng for ng in dst.node_groups}
sys.path.insert(0, SRC)
os.environ["VM_CHUNK"] = "100"
import build_engine as be
print("SRC", be.ENGINE_VERSION)


for gname, fn in (("VM_SceneDetailer", be.build_node_group), ("VM_RoofCap", be.build_roofcap_group)):
    ngc = fn()
    b = be.NGBuilder._current
    fl = flat[gname]
    fnodes = list(fl.nodes)
    # builder node i -> node object (chunk or main)
    bnodes = {}
    for tree in [b.ng] + b._chunks:
        for n in tree.nodes:
            i = b.idx_of.get(n.as_pointer())
            if i is not None:
                bnodes[i] = n
    print(gname, "flat nodes", len(fnodes), "builder nodes", len(b.types))
    fidx = {n.as_pointer(): k for k, n in enumerate(fnodes)}
    # 1) multi-input order: flat (by creation index of the source node) vs chunked logical->real
    bad = 0
    for i, t in enumerate(b.types):
        if i >= len(fnodes):
            break
        fn_ = fnodes[i]
        if fn_.bl_idname != t:
            print("  TYPE MISMATCH at", i, fn_.bl_idname, t)
            break
        for s in fn_.inputs:
            if not s.is_multi_input or not s.links:
                continue
            f_order = [fidx[l.from_node.as_pointer()] for l in s.links]
            # chunked: real links of the same socket, mapped to logical sources
            cs = bnodes[i].inputs[s.identifier] if s.identifier in bnodes[i].inputs else None
            lls = [ll for ll in b.links if ll.alive and ll.to_socket.as_pointer() == cs.as_pointer()]
            byreal = {ll.real.as_pointer(): ll for ll in lls if ll.real is not None}
            c_order = [b.idx_of[byreal[l.as_pointer()].from_node.as_pointer()] for l in cs.links
                       if l.as_pointer() in byreal]
            if f_order != c_order:
                bad += 1
                if bad <= 6:
                    print(f"  JOIN ORDER node {i} {fn_.name}: flat {f_order} chunked {c_order}")
    print(f"  multi-input order differences: {bad}")
    # 2) unlinked input defaults + node properties
    diff = 0
    skip = {"location", "name", "label", "width", "height", "select", "dimensions", "location_absolute"}
    for i in range(min(len(fnodes), len(b.types))):
        a_, c_ = fnodes[i], bnodes.get(i)
        if c_ is None:
            continue
        for p in a_.bl_rna.properties:
            if p.identifier in skip or p.is_readonly or p.type in ("POINTER", "COLLECTION"):
                continue
            va, vc = getattr(a_, p.identifier, None), getattr(c_, p.identifier, None)
            if hasattr(va, "__len__") and not isinstance(va, str):
                va, vc = tuple(va), tuple(vc)
            if va != vc:
                diff += 1
                if diff <= 10:
                    print(f"  PROP node {i} {a_.name}.{p.identifier}: flat {va} chunked {vc}")
        for sa in a_.inputs:
            if sa.is_linked or not hasattr(sa, "default_value"):
                continue
            sc = c_.inputs.get(sa.identifier) if hasattr(c_.inputs, "get") else None
            sc = next((x for x in c_.inputs if x.identifier == sa.identifier), None)
            if sc is None:
                continue
            if sc.is_linked:
                diff += 1
                if diff <= 10:
                    print(f"  LINKED only in chunked: node {i} {a_.name}.{sa.identifier}")
                continue
            va, vc = sa.default_value, sc.default_value
            if hasattr(va, "__len__") and not isinstance(va, str):
                va, vc = tuple(va), tuple(vc)
            if va != vc:
                diff += 1
                if diff <= 10:
                    print(f"  VALUE node {i} {a_.name}.{sa.identifier}: flat {va} chunked {vc}")
    print(f"  property / value differences: {diff}")
