# VM engine workflow (shared by every vm-* skill)

The source of truth is the repo: `build_engine.py` (generator, node groups,
library, checks), `VM_Tools_Addon.py` (add-on: Dress, presets, collection
wiring), `pack_ingest.py` (glTF/OBJ pack adapter) and `USAGE.txt` (the user's
run-book). `build/` is git-ignored scratch (probes, renders, stage).

## Standing rules (the user's)
- GitHub account **Ker102**. **No attribution lines** in commits or PRs. **Push only
  when the user says so.**
- Never touch the user's running Blender. Kill only your own PIDs, and only after
  checking the command line holds `build_engine.py` (or your probe script).
- Every test runs `blender -b --factory-startup`.
  Blender: `$HOME/AppData/Local/Programs/Blender Foundation/blender-5.2.2-windows-x64/blender.exe`
- RAM is tight (64 GB plus an 8 GB pagefile). Cycles or image loads die with
  `bad_alloc` / Malloc errors. Render at 900–1200 px with 16–48 samples, and one
  house visible per render. If it still runs out, ask the user to free memory.
  Never close their apps.
- Downloads: each in a new, empty directory; Python that reads them runs with `-I`.
  Sketchfab needs a login: never create accounts or enter credentials, the user
  downloads those. Poly Haven (CC0) is the default source. Put each asset in
  `~/Documents/ViperMeshAssets/props/<kind>/<id>/` with a `SOURCE.txt`
  (URL, licence, date).
- Before overwriting `~/Downloads/blender-engine`, compare mtimes: the user may have
  worked there. The user's TestFit scene lives only in
  `Downloads\blender-engine_v28_backup\VM_Starter.blend`.

## Editing the code
- `build_engine.py` is **LF** and about 15.7k lines. Edit it with a small Python
  script written to the scratchpad with the Write tool (bash heredocs with nested
  quotes break):
  ```python
  p = r"...\build_engine.py"; s = open(p, encoding="utf-8").read()
  def rep(a, b_):
      global s; assert s.count(a) == 1, a[:90]; s = s.replace(a, b_, 1)
  rep('''old''', '''new''')
  open(p, "w", encoding="utf-8", newline="").write(s)
  ```
  The Edit tool works too for one unique hunk.
- `VM_Tools_Addon.py` and `USAGE.txt` are **CRLF**. Normalise them to LF, edit, then
  restore CRLF. Never leave a file with mixed endings.
- **Socket order:** new sockets go after the existing ones in their panel.
  Modifiers and presets key on the interface identifier, and inserting a socket
  in the middle shifts the identifiers.
- Bump `ENGINE_VERSION` (one label, used everywhere) and add a `vX.YY` section
  to `USAGE.txt`, with the new check count in its header lines.

## Geometry Nodes builder idiom (inside `build_node_group()` / `build_roofcap_group()`)
`b.N(type, loc, **props)` makes a node, `b.L(out, in)` links,
`b.sock(name, type, panel, default, min, max, subtype, desc)` adds a socket and
`b.panel(...)` a panel. The helpers are `em(op,a,b)` (float math), `tm` (math),
`vmath(op,a,b)`, `tcmp(op,a,b)`, `tand / bor / bnot`, `tsw(cond,false,true)` /
`vsw` (switch), `v3(x,y,z)`, `sxyz(v)` (split), `rot`, `dnamed(name,type)` (named
attribute), `seed_node(b, seed_sock, offset)`, `random_loc()` (node location) and
`coll_count(sock)`.
Shared fields: `geo_f` (world scale factor: divide world-metre constants by it
when sampling in object space), `c_host` (host walls), `c_inst`, `c_trims`
(porch, balcony and trim geometry), `c_open` (opening faces), `o_real` (cutter
boxes), `has_open`, `gap_at`, `open_cut_at`, `is_fit`, `g_join`.
- Collection Info with Separate Children yields the children in **alphabetical
  order**, so name variants `_01 .. _NN` and rely on that order.
- Work in **world metres**. Every constant is a world distance, and an unapplied
  object scale must not stretch anything. The build's `world-space:` checks pin this.
- Seed every random value with `seed_node(...)` and a fresh offset, and key it on
  position, not on index, when instances can be deleted upstream (damage).
- **The groups are built in ~100-node subgroups (v2.31, `CHUNK_NODES`, `chunked_build`).**
  The builder code runs twice: a record pass, then the final pass into
  `.VM_SceneDetailer NN` / `.VM_RoofCap NN`. A node's inputs may come from
  another subgroup, and cross links are only wired at the end. So:
  - link only with `b.L(out, in)`, remove links only with
    `b.unlink(lambda lk: lk.from_node == x and lk.to_node == y)`,
    and use `b.last` for "the node just made". Never touch `b.ng.links`,
    `b.ng.nodes` or `socket.links`.
  - don't read link state (`is_linked`, `.links`) during the build, and don't
    create bpy data that must survive the record pass (it is deleted between passes).
  - the code must make the same nodes in the same order on both passes (no
    `random` without a fixed seed): the build stops if the two passes differ.
  - `VM_CHUNK=0` builds the old single flat tree (~1 h for VM_SceneDetailer),
    which is only useful to compare against.

## Tests
1. **Fast loop (in-file):** a `build/vXXX_test.py` that imports `build_engine`,
   rebuilds only the groups it needs, makes the assets in-file and prints
   numbers. 15–25 min. See `build/v229_test.py` for the pattern.
2. **From the built library (no rebuild):** copy `build/stage/VM_Assets.blend`, then
   use the add-on exactly as the user does: `vmt.import_engine(lib, [])`,
   `vmt.dress_object(ob, [])`, `setv(ob, mod, socket, value)` via
   `vmt.find_input`, `bpy.ops.vm.apply_preset(preset="lib:...")` (needs
   `view_layer.update()` and an active, selected object).
   - `scripts/scale_probe.py`: four odd-sized houses (tiny / big / tower /
     unapplied object scale) with every part on. It prints per pool the count,
     floating pieces, the world scale range and yard props inside or too far out.
   - `scripts/look_shots.py`: four dressed houses, front and corner views → PNGs
     and a contact sheet.
   - Read instances while iterating `dg.object_instances`. A stored `inst.object`
     goes stale after the loop.
   - Mesh attributes may be on the POINT domain even when they mark faces
     (`vm_trim`). Average them per face.
3. **Full build:** `bash .claude/skills/vm-new-building-part/scripts/run_build.sh build_vXXX > build/build_vXXX_summary.txt 2>&1`
   (the same script as `build/run_build.sh`; `build/` is not in git), run with
   `run_in_background` (not `&`). About 50 min. Read the `PASS N FAIL M` line
   and every FAIL. Outputs land in `build/stage/`.
4. **Look:** always render and *look* at the result before calling a part done.
   Send the user the contact sheet (SendUserFile). Numbers pass long before it looks right.

## Delivery (only after a green full build)
```bash
cp -f build/stage/*.blend build/stage/*.json build/stage/*.txt build/stage/*.py build/stage/*.png ~/Downloads/blender-engine/
cp -f build/stage/VM_Tools_Addon.py "$APPDATA/Blender Foundation/Blender/5.2/scripts/addons/VM_Tools_Addon.py"
```
Then commit locally (`vX.YY: <what the user sees>`, no attribution) and ask
before pushing.
