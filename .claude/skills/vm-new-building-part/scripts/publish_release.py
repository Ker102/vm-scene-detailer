"""Publish a VM engine release that the add-on's 'Check for Updates' finds.
  blender -b --factory-startup --python .claude/skills/vm-new-building-part/scripts/publish_release.py -- [repo:owner/name] [notes:FILE] [publish]
Checks first that the files agree on ONE version - build_engine.ENGINE_VERSION, the add-on's
ADDON_VERSION and bl_info, and the engine_version inside the library - (a mismatch makes every
user's Blender offer the same update forever, or refuse the download), that the library is
the CORE one (no example objects) and that VM_ExampleAssets.blend carries its VM_ExampleInfo,
then prints the `gh release create` command. Only with `publish` does it run it: a release is
PUBLIC on a public repo - ask the user before every publish (the user's rule: push / publish
only on ask).
Files: the delivered VM_Tools_Addon.py, VM_Assets.blend (core) and VM_ExampleAssets.blend
(optional examples) from ~/Downloads/blender-engine. The example file is uploaded with the
display label 'VM_ExampleAssets.blend (optional examples) [<fp>]'; when the latest release already has an example file with the same
fingerprint, THAT file is downloaded and re-uploaded unchanged, so its sha256 stays the same
and the add-on does not offer users the same 140 MB again. The notes always end with the
CC-BY credits of the example assets (taken from VM_ExampleInfo)."""
import bpy, os, re, sys, json, subprocess, tempfile, importlib.util
HERE = r"C:\Users\krist\Desktop\main-projects\Projects\vm-scene-detailer"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
D = os.path.expanduser(os.path.join("~", "Downloads", "blender-engine"))
ADDON, LIB, EX = (os.path.join(D, f) for f in ("VM_Tools_Addon.py", "VM_Assets.blend", "VM_ExampleAssets.blend"))
spec = importlib.util.spec_from_file_location("VM_Tools_Addon", ADDON)
vmt = importlib.util.module_from_spec(spec); sys.modules["VM_Tools_Addon"] = vmt; spec.loader.exec_module(vmt)
REPO = next((a[5:] for a in ARGS if a.startswith("repo:")), vmt.UPDATE_REPO)
NOTES = next((a[6:] for a in ARGS if a.startswith("notes:")), None)
eng = re.search(r'^ENGINE_VERSION\s*=\s*"([^"]+)"', open(os.path.join(HERE, "build_engine.py"), encoding="utf-8").read(), re.M).group(1)
lib_v = vmt.library_info(LIB).get("engine_version", "")
same_repo = open(os.path.join(HERE, "VM_Tools_Addon.py"), "rb").read() == open(ADDON, "rb").read()
vals = dict(build=eng, addon=vmt.ADDON_VERSION, bl_info="v%d.%d" % vmt.bl_info["version"][:2], library=lib_v)
print("VERSIONS", vals, "| delivered add-on == repo copy:", same_repo)
if len(set(vals.values())) != 1 or not same_repo:
    raise SystemExit("NOT PUBLISHING: the versions differ or the delivered add-on is not the repo's")
# the library must be the core one: its example collections are empty
with bpy.data.libraries.load(LIB, link=False) as (src, dst):
    dst.collections = ["VM_Doors", "VM_Windows", "VM_Yard"]
n_ex = sum(len(c.all_objects) for c in dst.collections if c is not None)
info = vmt.example_info(EX) if os.path.isfile(EX) else {}
print("CORE library example objects:", n_ex, "| examples:", info.get("fingerprint"), len(info.get("credits", [])), "credits")
if n_ex or not info.get("collections") or not info.get("fingerprint"):
    raise SystemExit("NOT PUBLISHING: VM_Assets.blend still holds example objects, or VM_ExampleAssets.blend "
                     "is missing / has no VM_ExampleInfo (run the build's delivery or split_library.py)")
tag = eng
LABEL = f"VM_ExampleAssets.blend (optional examples) [{info['fingerprint']}]"
tmp = tempfile.mkdtemp(prefix="vm_release_")
# re-use the previous example file while the examples did not change
ex_file = EX
try:
    prev = json.loads(subprocess.run(["gh", "release", "view", "--repo", REPO, "--json", "tagName,assets"],
                                     capture_output=True, text=True, check=True).stdout)
    old = next((a for a in prev.get("assets", []) if a.get("name") == vmt.EXAMPLES_ASSET), None)
    if old and f"[{info['fingerprint']}]" in (old.get("label") or ""):
        subprocess.run(["gh", "release", "download", prev["tagName"], "--repo", REPO, "-p", vmt.EXAMPLES_ASSET,
                        "-D", tmp], check=True)
        ex_file = os.path.join(tmp, vmt.EXAMPLES_ASSET)
        print("EXAMPLES unchanged since", prev["tagName"], "- re-uploading that file (same sha256)")
    else:
        print("EXAMPLES new or changed - uploading the delivered file")
except (subprocess.CalledProcessError, FileNotFoundError) as e:
    print("EXAMPLES no previous release to compare with:", e)
body = open(NOTES, encoding="utf-8").read().rstrip() if NOTES else f"VM engine {tag}."
body += ("\n\n## Files\n- `VM_Tools_Addon.py` - the add-on (Edit > Preferences > Add-ons > Install).\n"
         "- `VM_Assets.blend` - the engine library: node groups, presets, the engine's own tile, damage "
         "and debris pools. Doors, windows and yard collections are empty: put your own objects in "
         "them, or add the examples.\n"
         "- `VM_ExampleAssets.blend` - OPTIONAL example doors, windows and yard props / plants used in "
         "the demo builds (VM Tools > 'Add Example Assets'; tick 'Include example assets' to let "
         "'Check for Updates' download it).\n\n## Example asset credits\n")
for c in info["credits"]:
    body += f"- {c['asset']}: \"{c['title']}\" by {c['author']} ({c['url']}), {c['license']}\n"
notes_file = os.path.join(tmp, "notes.md")
open(notes_file, "w", encoding="utf-8").write(body)
cmd = ["gh", "release", "create", tag, ADDON, LIB, f"{ex_file}#{LABEL}",
       "--repo", REPO, "--title", f"VM engine {tag}", "--notes-file", notes_file]
print("NOTES\n" + body)
print("COMMAND", " ".join(f'"{c}"' if " " in c else c for c in cmd))
if "publish" in ARGS:
    r = subprocess.run(cmd)
    print("PUBLISHED" if r.returncode == 0 else f"gh failed ({r.returncode})")
