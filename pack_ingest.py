"""
pack_ingest.py - generic zero-config asset-pack adapter for VM_SceneDetailer (Blender 5.2).

Ingests ANY glTF/OBJ asset pack and emits engine-ready, normalized, classified
variant collections + a JSON ingest report. NO pack-specific parameters: the
same unmodified script handles doors, windows, shingles, props... (it has been
run as-is on WornWoodenDoorsPack + 4 window packs, see <Pack>_ingest.json).

What it does per pack (deterministic, sorted iteration, fixed rules only):
  1. import (scene.gltf / *.gltf / *.glb / *.obj; a directory is scanned for one)
  2. work on the AUTHORED MESH GEOMETRY (local verts) - the pack's showroom
     layout (object transforms) is a display arrangement, not part of the
     asset, so it is discarded (logged). Scale is normalized to real-world
     meters by a max-dimension heuristic:
         max dim > 40 units       -> cm/m-unit pack, auto-scale 0.01 (logged)
         max dim > 4 m            -> flagged "oversized"
         all axes < 0.05 m        -> flagged "undersized"
  3. auto-classify each meshed object by bbox aspect (measured after
     auto-orient: X=width, Y=depth, Z=height):
         WALLFLAT  depth <= 25% of min(width, height) and flat  -> wall slab
         TILE      same flatness AND small (max(w,h) <= 0.6 m)   -> cladding tile
         PROP      anything else (handles, boxes, chunky parts)
  4. auto-quarantine into <Pack>_Quarantine with per-object reasons - never
     silently mixed into Fit collections:
         degenerate          some bbox axis < 4 mm (zero-thickness sheets)
         multi-part leftover >=2 connected shells with disjoint bounding boxes
                             (loose scattered pieces that are not one part)
         non-flat (ajar)     PCA thickness > 1.05 x bbox depth: the shape is
                             swung/splayed inside its own bbox, so a
                             bbox-normalized wall fit leaves its panel hanging
                             in air off the wall plane (the "floating door")
  5. auto-orient (bake to identity, proper rotation only, no mirroring):
         slabs/tiles: thin axis -> Y (depth), largest -> Z (height, up),
                      middle -> X (width); origin x centered, y=0 ON the
                      wall-contact (back) face, z at the base for slabs
                      (Drop-To-Ground contract) / centered for tiles (cladding)
         props: same axis rule, origin centered on the ground plane
  6. output: normalized collections <Pack>_WALLFLAT / <Pack>_TILE /
     <Pack>_PROP / <Pack>_Quarantine, a JSON report per pack (counts per class,
     per-object decisions, scale factors applied, quarantine reasons) and the
     same report printed as a table.

Standalone (identical invocation for any pack, no per-pack flags):
  cd <blender dir> && ./blender -b --python pack_ingest.py -- \
      [--out DIR] [--save-blend] <pack.gltf|pack.obj|pack-dir> [...]

As a module (used by build_engine.py):
  from pack_ingest import ingest_pack
  report = ingest_pack(".../scene.gltf", out_dir=..., parent=collection)
"""

import bpy, bmesh, os, sys, json, math
from mathutils import Matrix, Vector

# --------------------------------------------------------------- generic rules
FLAT_RATIO = 0.25        # depth <= 25% of min(width, height) -> flat slab
AJAR_RATIO = 1.05        # PCA thickness > 1.05 x bbox depth -> non-flat (ajar)
TILE_MAX = 0.6           # flat AND max(w,h) <= 0.6 m -> TILE, else WALLFLAT
DEGENERATE_M = 0.004     # bbox axis below this -> degenerate sheet
CM_SCALE_DIM = 40.0      # max dim above this (units) -> cm pack, scale 0.01
OVERSIZE_M = 4.0         # max dim above this after scaling -> flagged
UNDSIZE_M = 0.05         # all axes below this after scaling -> flagged

log = lambda *a: print(*a, flush=True)


# ------------------------------------------------------------------- geometry
def mesh_verts(ob):
    """Authored (local) vertex coords - the showroom pose is discarded."""
    return [tuple(v.co) for v in ob.data.vertices]


def bbox_of(verts):
    lo = [min(v[i] for v in verts) for i in range(3)]
    hi = [max(v[i] for v in verts) for i in range(3)]
    return lo, hi


def scale_factor_for(dims):
    """Max-dimension heuristic for real-world scale (cm packs -> 0.01)."""
    mxd = max(dims)
    if mxd > CM_SCALE_DIM:
        return 0.01, "cm-scale pack (max dim %.1f units) auto-scaled 0.01" % mxd
    return 1.0, ""


def pca_extents(verts):
    """Extent of the point cloud along its 3 principal axes (largest first)."""
    n = len(verts)
    cen = Vector((0.0, 0.0, 0.0))
    for v in verts:
        cen += Vector(v)
    cen /= n
    cov = [[0.0] * 3 for _ in range(3)]
    for v in verts:
        d = Vector(v) - cen
        for i in range(3):
            for j in range(3):
                cov[i][j] += d[i] * d[j]
    for i in range(3):
        for j in range(3):
            cov[i][j] /= n
    a = [row[:] for row in cov]
    rot = [[1.0 if i == j else 0.0 for j in range(3)] for i in range(3)]
    for _ in range(80):
        p, q, best = 0, 1, 0.0
        for i in range(3):
            for j in range(i + 1, 3):
                if abs(a[i][j]) > best:
                    best, p, q = abs(a[i][j]), i, j
        if best < 1e-14:
            break
        app, aqq, apq = a[p][p], a[q][q], a[p][q]
        tau = (aqq - app) / (2.0 * apq)
        t = math.copysign(1.0, tau) / (abs(tau) + math.sqrt(1.0 + tau * tau))
        c = 1.0 / math.sqrt(1.0 + t * t)
        s = t * c
        for k in range(3):
            akp, akq = a[k][p], a[k][q]
            a[k][p], a[k][q] = c * akp - s * akq, s * akp + c * akq
        for k in range(3):
            apk, aqk = a[p][k], a[q][k]
            a[p][k], a[q][k] = c * apk - s * aqk, s * apk + c * aqk
        for k in range(3):
            vkp, vkq = rot[k][p], rot[k][q]
            rot[k][p], rot[k][q] = c * vkp - s * vkq, s * vkp + c * vkq
    out = []
    for ev, ax in sorted(((a[i][i], i) for i in range(3)), reverse=True):
        axis = Vector((rot[0][ax], rot[1][ax], rot[2][ax])).normalized()
        pr = [Vector(v).dot(axis) for v in verts]
        out.append(max(pr) - min(pr))
    return out


def shell_boxes(me):
    """Connected shells (vertex-connected) as (vert index list, bbox)."""
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    seen = set()
    shells = []
    for v in bm.verts:
        if v.index in seen:
            continue
        comp, stack = [], [v]
        seen.add(v.index)
        while stack:
            cur = stack.pop()
            comp.append(cur.index)
            for e in cur.link_edges:
                o = e.other_vert(cur)
                if o.index not in seen:
                    seen.add(o.index)
                    stack.append(o)
        shells.append(comp)
    coords = {v.index: (v.co.x, v.co.y, v.co.z) for v in bm.verts}
    bm.free()
    boxes = []
    for comp in shells:
        pts = [coords[i] for i in comp]
        lo, hi = bbox_of(pts)
        boxes.append((comp, lo, hi))
    return boxes


def boxes_disjoint(lo_a, hi_a, lo_b, hi_b, eps=1e-6):
    return any(hi_a[i] < lo_b[i] + eps or hi_b[i] < lo_a[i] + eps for i in range(3))


# ------------------------------------------------------------------ normalize
def normalize_variant(ob, kind):
    """Rebuild the object from its authored verts: real-world scale, axes
    permuted to X=width / Y=depth / Z=height (proper rotation, no mirroring),
    engine origin contract. Returns (scale_factor, axis_map)."""
    me = ob.data
    ob.parent = None
    ob.matrix_world = Matrix.Identity(4)   # showroom pose discarded
    verts = mesh_verts(ob)
    lo, hi = bbox_of(verts)
    dims = [hi[i] - lo[i] for i in range(3)]
    sf, _ = scale_factor_for(dims)
    if sf != 1.0:
        me.transform(Matrix.Scale(sf, 4))
        verts = mesh_verts(ob)
        lo, hi = bbox_of(verts)
        dims = [hi[i] - lo[i] for i in range(3)]

    order = sorted(range(3), key=lambda i: (dims[i], i))   # thin, mid, large
    thin, mid, large = order
    # map source axis -> target axis: thin->Y(1), mid->X(0), large->Z(2)
    target = {thin: 1, mid: 0, large: 2}
    m = [[0.0] * 3 for _ in range(3)]
    for src in range(3):
        m[target[src]][src] = 1.0
    det = (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
           - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
           + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
    if det < 0:                       # keep it a proper rotation: flip X and Y
        for src in range(3):
            m[0][src] *= -1.0
            m[1][src] *= -1.0
    mat = Matrix((m[0] + [0.0], m[1] + [0.0], m[2] + [0.0],
                  [0.0, 0.0, 0.0, 1.0]))   # rows are target axes -> y = M @ x
    me.transform(mat)
    verts = mesh_verts(ob)
    lo, hi = bbox_of(verts)
    # origin contract
    cx = (lo[0] + hi[0]) / 2.0
    if kind == "TILE":                # cladding: centered in the face plane
        cz = (lo[2] + hi[2]) / 2.0
        cy = lo[1]                    # y=0 ON the wall-contact face
    elif kind == "PROP":              # props: centered on the ground plane
        cz = lo[2]
        cy = (lo[1] + hi[1]) / 2.0
    else:                             # wall slabs: back-base-center
        cz = lo[2]
        cy = lo[1]
    me.transform(Matrix.Translation((-cx, -cy, -cz)))
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()
    axis_map = {"width_from": "xyz"[mid], "depth_from": "xyz"[thin], "height_from": "xyz"[large]}
    return sf, axis_map


# -------------------------------------------------------------------- ingest
def discover_pack_file(path):
    if os.path.isfile(path):
        return path
    for name in ("scene.gltf", "scene.glb", "scene.obj"):
        p = os.path.join(path, name)
        if os.path.isfile(p):
            return p
    found = []
    for f in sorted(os.listdir(path)):
        if f.lower().endswith((".gltf", ".glb", ".obj")):
            found.append(os.path.join(path, f))
    if found:
        return found[0]
    raise FileNotFoundError("no glTF/OBJ file found in %s" % path)


def import_pack(path):
    f = discover_pack_file(path)
    before = set(bpy.data.objects.keys())
    ext = os.path.splitext(f)[1].lower()
    if ext == ".obj":
        bpy.ops.wm.obj_import(filepath=f)
    else:
        bpy.ops.import_scene.gltf(filepath=f)
    new = [bpy.data.objects[n] for n in set(bpy.data.objects.keys()) - before]
    return f, sorted(new, key=lambda o: o.name)


def ingest_pack(path, out_dir=None, parent=None, save_blend=False):
    """Ingest one pack. Returns the report dict; creates <Pack>_<Class>
    collections (linked under `parent` when given) and writes
    <out_dir>/<Pack>_ingest.json. Zero pack-specific parameters."""
    pack = os.path.basename(os.path.normpath(path))
    if pack.lower().endswith((".gltf", ".glb", ".obj")):
        base = os.path.splitext(pack)[0]
        if base.lower() == "scene":
            pack = os.path.basename(os.path.normpath(os.path.dirname(path)))
        else:
            pack = base
    src, new_objs = import_pack(path)
    log("== pack_ingest: %s (%s)" % (pack, src))

    cols = {}
    for cls in ("WALLFLAT", "TILE", "PROP", "Quarantine"):
        c = bpy.data.collections.new("%s_%s" % (pack, cls))
        if parent is not None:
            parent.children.link(c)
        else:
            bpy.context.scene.collection.children.link(c)
        cols[cls] = c

    report = dict(pack=pack, source=src, ingester="pack_ingest.py (zero-config)",
                  objects_seen=len(new_objs), meshes=0, non_mesh_dropped=0,
                  scale_factors={}, flags=[], counts={}, quarantine=[],
                  objects=[])
    counters = {"WALLFLAT": 0, "TILE": 0, "PROP": 0, "Quarantine": 0}

    for ob in new_objs:
        if ob.type != "MESH":
            report["non_mesh_dropped"] += 1
            bpy.data.objects.remove(ob, do_unlink=True)
            continue
        report["meshes"] += 1
        entry = dict(source_name=ob.name)
        verts = mesh_verts(ob)
        if not verts:
            entry.update({"class": "Quarantine", "reason": "empty mesh (no vertices)",
                          "dims_m": [0.0, 0.0, 0.0], "scale_factor": 1.0,
                          "output_name": ob.name})
            counters["Quarantine"] += 1
            report["quarantine"].append(dict(name=ob.name, source=ob.name,
                                             reason=entry["reason"]))
            report["objects"].append(entry)
            bpy.data.objects.remove(ob, do_unlink=True)
            continue
        lo, hi = bbox_of(verts)
        dims0 = [hi[i] - lo[i] for i in range(3)]
        sf, scale_note = scale_factor_for(dims0)
        entry["scale_factor"] = sf
        report["scale_factors"][ob.name] = sf
        if scale_note:
            entry["scale_note"] = scale_note
            report["flags"].append("%s: %s" % (ob.name, scale_note))
        dims = [d * sf for d in dims0]

        decision = reason = None
        if min(dims) < DEGENERATE_M:
            decision = "Quarantine"
            reason = ("degenerate/zero-thickness sheet (min extent %.4f m < %.3f m)"
                      % (min(dims), DEGENERATE_M))
        thin_ax = min(range(3), key=lambda i: dims[i])
        depth = dims[thin_ax]
        other = sorted(dims)[1:]
        depth_ratio = depth / max(min(other), 1e-9)
        pca = [p * sf for p in pca_extents(verts)]      # to real-world meters
        pca_ratio = pca[2] / max(depth, 1e-9)
        entry.update(dims_m=[round(d, 4) for d in dims], depth_ratio=round(depth_ratio, 4),
                     pca_thickness=round(pca[2], 4), pca_ratio=round(pca_ratio, 4))
        if max(dims) > OVERSIZE_M:
            report["flags"].append("%s: oversized (%.2f m max dim)" % (ob.name, max(dims)))
        if max(dims) < UNDSIZE_M:
            report["flags"].append("%s: undersized (%.3f m max dim)" % (ob.name, max(dims)))

        flat_aspect = depth_ratio <= FLAT_RATIO
        if decision is None and not flat_aspect:
            decision, reason = "PROP", ("not flat: depth %.3f m > %.0f%% of min(w,h) "
                                        "(chunky part: handle/box/frame profile)"
                                        % (depth, FLAT_RATIO * 100))
        if decision is None and flat_aspect:
            # flat candidate -> it may still be unfit for a wall:
            # (a) loose multi-part leftovers, (b) non-flat (ajar) panels
            boxes = shell_boxes(ob.data)
            if len(boxes) >= 2:
                # loose-scattered test: cluster shells whose bounding boxes touch
                # or nearly touch (real assembly contact); >1 cluster = the mesh
                # is several loose pieces, not one part
                tol = max(0.002, 0.004 * max(dims))
                n = len(boxes)
                parent_uf = list(range(n))

                def find(a):
                    while parent_uf[a] != a:
                        parent_uf[a] = parent_uf[parent_uf[a]]
                        a = parent_uf[a]
                    return a

                for i in range(n):
                    for j in range(i + 1, n):
                        gap = max(max(boxes[i][1][k] - boxes[j][2][k],
                                      boxes[j][1][k] - boxes[i][2][k]) for k in range(3))
                        if gap <= tol * sf:
                            ri, rj = find(i), find(j)
                            if ri != rj:
                                parent_uf[ri] = rj
                clusters = len({find(i) for i in range(n)})
                if clusters > 1:
                    decision = "Quarantine"
                    reason = ("multi-part leftover: %d connected shells split into "
                              "%d loose clusters (gap > %.1f mm) - not one part"
                              % (len(boxes), clusters, tol * 1000))
        if decision is None and pca_ratio > AJAR_RATIO:
            decision = "Quarantine"
            reason = ("non-flat (ajar): PCA thickness %.4f m > %.2f x bbox depth "
                      "%.4f m - the panel is swung/splayed inside its own bbox, a "
                      "bbox-normalized wall fit leaves it hanging off the wall plane"
                      % (pca[2], AJAR_RATIO, depth))
        if decision is None:
            if max(other) <= TILE_MAX:
                decision = "TILE"
                reason = "flat and small (max(w,h) %.3f m <= %.2f m)" % (max(other), TILE_MAX)
            else:
                decision = "WALLFLAT"
                reason = "wall-flat slab (depth %.3f m <= %.0f%% of min(w,h))" % (
                    depth, FLAT_RATIO * 100)

        kind = decision if decision in ("TILE", "PROP") else "WALLFLAT"
        if decision == "Quarantine":
            kind = "WALLFLAT"          # orient slabs consistently before parking
        sf2, axis_map = normalize_variant(ob, kind)
        entry["orientation"] = axis_map
        entry["class"] = decision
        entry["reason"] = reason

        counters[decision] += 1
        col = cols[decision]
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        col.objects.link(ob)
        if decision == "Quarantine":
            ob.name = ob.data.name = "%s_Q%02d_%s" % (pack, counters[decision],
                                                      ob.name.replace(" ", "_"))
            report["quarantine"].append(dict(name=ob.name, source=entry["source_name"],
                                             reason=reason))
        else:
            ob.name = ob.data.name = "%s_%s_%02d" % (pack, decision, counters[decision])
        entry["output_name"] = ob.name
        report["objects"].append(entry)

    report["counts"] = dict(counters)
    report["collections"] = {k: v.name for k, v in cols.items()}

    if out_dir is None:
        out_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "%s_ingest.json" % pack), "w") as f:
        json.dump(report, f, indent=1)
    if save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, "%s_ingested.blend" % pack))
    print_report(report)
    return report


def print_report(rep):
    log("---- pack_ingest report: %s ----" % rep["pack"])
    log("source: %s   meshes=%d  non-mesh leftovers dropped=%d"
        % (rep["source"], rep["meshes"], rep["non_mesh_dropped"]))
    log("counts: WALLFLAT=%d TILE=%d PROP=%d QUARANTINE=%d"
        % (rep["counts"]["WALLFLAT"], rep["counts"]["TILE"],
           rep["counts"]["PROP"], rep["counts"]["Quarantine"]))
    if rep["scale_factors"]:
        vals = sorted(set(rep["scale_factors"].values()))
        log("scale factors applied: %s (per object in the JSON report)"
            % (", ".join("x%g" % v for v in vals)))
    log("%-42s %-10s %-28s %s" % ("object", "class", "dims w/d/h (m)", "reason"))
    for e in rep["objects"]:
        d = e.get("dims_m", [0, 0, 0])
        log("%-42s %-10s %-28s %s"
            % (e["output_name"][:42], e["class"],
               "%.3f x %.3f x %.3f" % (d[0], d[1], d[2]), e["reason"][:90]))
    for q in rep["quarantine"]:
        log("  QUARANTINED %s: %s" % (q["name"], q["reason"]))
    for fl in rep["flags"]:
        log("  FLAG %s" % fl)
    log("---- end report: %s ----" % rep["pack"])


# ----------------------------------------------------------------------- CLI
def main(argv):
    args = argv[argv.index("--") + 1:] if "--" in argv else argv[1:]
    out_dir, save_blend, packs = None, False, []
    i = 0
    while i < len(args):
        if args[i] == "--out":
            out_dir = args[i + 1]; i += 2
        elif args[i] == "--save-blend":
            save_blend = True; i += 1
        else:
            packs.append(args[i]); i += 1
    if not packs:
        log("usage: blender -b --python pack_ingest.py -- [--out DIR] [--save-blend] "
            "<pack.gltf|pack.obj|pack-dir> [...]")
        sys.exit(2)
    summary = []
    for p in packs:
        rep = ingest_pack(p, out_dir=out_dir, save_blend=save_blend)
        summary.append(rep)
    log("\n== ALL PACKS (same script, zero pack-specific parameters) ==")
    log("%-26s %8s %6s %5s %5s %11s  %s"
        % ("pack", "meshes", "flat", "tile", "prop", "quarantine", "scale"))
    for r in summary:
        log("%-26s %8d %6d %5d %5d %11d  %s"
            % (r["pack"], r["meshes"], r["counts"]["WALLFLAT"], r["counts"]["TILE"],
               r["counts"]["PROP"], r["counts"]["Quarantine"],
               ",".join("x%g" % v for v in sorted(set(r["scale_factors"].values())))))


if __name__ == "__main__":
    main(sys.argv)
