"""Test the add-on's 'Check for Updates' path against a FAKE release server (never GitHub).
  1. python -I make_release_fixture.py <T> <PORT> v2.36 VM_Tools_Addon.py <core>/VM_Assets.blend
        <core>/VM_ExampleAssets.blend     (the fake release JSONs + files, a good and a bad one)
     and copy the add-on to <T>/addon/VM_Tools_Addon.py
  2. python -I -m http.server <PORT> --bind 127.0.0.1   (in <T>/serve; asset urls use that port)
  3. blender -b --factory-startup --online-mode --python updater_test.py -- <T> <PORT>
The add-on is loaded from <T>/addon/VM_Tools_Addon.py (a COPY: the install replaces
it), the install folder is <T>/home (VM_UPDATE_DIR). Prints PASS/FAIL lines and
UPDATER TEST OK."""
import bpy, os, sys, importlib.util, json, hashlib
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
T = ARGS[0]
PORT = ARGS[1] if len(ARGS) > 1 else "8765"
os.environ["VM_UPDATE_API"] = f"http://127.0.0.1:{PORT}"
os.environ["VM_UPDATE_DIR"] = os.path.join(T, "home")
ADDON = os.path.join(T, "addon", "VM_Tools_Addon.py")
spec = importlib.util.spec_from_file_location("VM_Tools_Addon", ADDON)
vmt = importlib.util.module_from_spec(spec); sys.modules["VM_Tools_Addon"] = vmt; spec.loader.exec_module(vmt)
vmt.register()
FAILS = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name, detail, flush=True)
    if not ok:
        FAILS.append(name)


class FakeLayout:
    """Records what the panel draws (catches typos in the draw code headless)."""
    def __init__(self, log):
        self.log, self.alert, self.scale_y, self.enabled = log, False, 1.0, True

    def __getattr__(self, nm):
        def f(*a, **k):
            self.log.append((nm, k.get("text", a[0] if a and isinstance(a[0], str) else "")))
            if nm in ("box", "row", "column"):
                return FakeLayout(self.log)
            if nm == "operator":
                return type("Op", (), {})()
            return None
        return f


def draw(state):
    log = []
    vmt._UPD["status"] = state
    vmt._draw_updates(FakeLayout(log), bpy.context)
    return [t for _n, t in log if t]


check("online access on (--online-mode)", vmt.online_allowed())
check("the engine version is in bl_info", vmt.bl_info["version"][:2] == vmt.ver_tuple(vmt.ADDON_VERSION)[:2],
      f"{vmt.bl_info['version']} vs {vmt.ADDON_VERSION}")
# -- the check finds the release and wants both files when both are older
info = vmt.fetch_latest_release("test/vm")
check("fetch the latest release", info["latest"] == "v2.36" and set(info["assets"]) == {"VM_Tools_Addon.py", "VM_Assets.blend", "VM_ExampleAssets.blend"},
      (info["latest"], list(info["assets"])))
vmt._apply_check(info)
check("the result is kept for the next session", json.load(open(vmt._state_file()))["latest"] == "v2.36")
real_iv = vmt.installed_versions
check("same versions installed -> nothing wanted", vmt.wanted_assets() == [] or real_iv()[0] != "v2.36", vmt.wanted_assets())
vmt.installed_versions = lambda context=None: ("v2.35", "v2.35")
check("older add-on + library -> both wanted, examples NOT (opt-in off)", vmt.wanted_assets() == ["VM_Tools_Addon.py", "VM_Assets.blend"], vmt.wanted_assets())
real_exp = vmt.example_library_path
vmt.example_library_path = lambda context=None: ""          # no example file anywhere
vmt._UPD["include_examples_test"] = True
check("opt-in on, no example file -> examples wanted too", vmt.wanted_assets() == ["VM_Tools_Addon.py", "VM_Assets.blend", "VM_ExampleAssets.blend"], vmt.wanted_assets())
vmt._UPD["include_examples_test"] = False
txt = " | ".join(draw("available"))
check("panel offers the update", "v2.36 is available" in txt and "Download & Install" in txt, txt)
for st in ("idle", "uptodate", "checking", "downloading", "installed", "error"):
    vmt._UPD.update(error="could not check test/vm: HTTP Error 404", total=10, done=5)
    try:
        draw(st)
        check(f"panel draws in state '{st}'", True)
    except Exception as e:
        check(f"panel draws in state '{st}'", False, repr(e))
# -- a corrupted download is refused and nothing is replaced
before = hashlib.sha256(open(ADDON, "rb").read()).hexdigest()
bad = vmt.fetch_latest_release("test/bad")
vmt._apply_check(bad); vmt._UPD["done"] = 0
try:
    vmt._download_job(["VM_Tools_Addon.py"], "")
    check("a wrong checksum is refused", False)
except RuntimeError as e:
    check("a wrong checksum is refused", "checksum" in str(e), str(e))
check("... and the add-on is untouched", hashlib.sha256(open(ADDON, "rb").read()).hexdigest() == before)
# -- the real download + install
vmt._apply_check(info); vmt._UPD.update(done=0, cancel=False)
names = vmt.wanted_assets()
files = vmt._download_job(names, "")
check("both files downloaded with the right size", vmt._UPD["done"] == sum(info["assets"][n]["size"] for n in names),
      vmt._UPD["done"])
msg = vmt.install_downloaded(files)
print("INSTALLED", msg, flush=True)
lib = vmt.managed_library()
check("library installed in the managed folder", os.path.isfile(lib) and os.path.getsize(lib) == info["assets"]["VM_Assets.blend"]["size"], lib)
prefs = vmt._addon_prefs()
check("the add-on now reads that library", (prefs is None or prefs.library_path == lib), getattr(prefs, "library_path", None))
vmt.installed_versions = real_iv
vmt.LIBRARY_PATH_OVERRIDE = ""
check("library_path() finds it", os.path.normcase(vmt.library_path()) in
      (os.path.normcase(lib), os.path.normcase(os.path.expanduser("~/Downloads/blender-engine/VM_Assets.blend"))), vmt.library_path())
check("add-on replaced by the release file", hashlib.sha256(open(ADDON, "rb").read()).hexdigest()
      == info["assets"]["VM_Tools_Addon.py"]["digest"][7:])
check("the old add-on is kept", os.path.isfile(os.path.join(vmt.update_dir(), "VM_Tools_Addon_previous.py")))
# a second install of the library keeps the first as *_previous
vmt.installed_versions = lambda context=None: (vmt.ADDON_VERSION, "v2.35")
vmt._UPD["done"] = 0
vmt.install_downloaded(vmt._download_job(["VM_Assets.blend"], ""))
check("re-install keeps VM_Assets_previous.blend", os.path.isfile(os.path.join(os.path.dirname(lib), "VM_Assets_previous.blend")))
# -- a library whose engine version is not the tag is refused
vmt._UPD["latest"] = "v9.99"
try:
    vmt.install_downloaded({"VM_Assets.blend": lib})
    check("a library of the wrong version is refused", False)
except RuntimeError as e:
    check("a library of the wrong version is refused", "v9.99" in str(e), str(e))
# -- the optional example assets: only when ticked, installed next to the library
vmt._LIB_CACHE.clear()
vmt._UPD.update(latest="v2.36", include_examples_test=True, done=0, cancel=False, examples_sha="")
vmt.installed_versions = lambda context=None: (vmt.ADDON_VERSION, vmt.ADDON_VERSION)
check("only the examples wanted when the engine is current", vmt.wanted_assets() == ["VM_ExampleAssets.blend"], vmt.wanted_assets())
txt = " | ".join(draw("available"))
check("panel says the examples are ready", "Example assets ready to download" in txt, txt)
files = vmt._download_job(vmt.wanted_assets(), "")
msg = vmt.install_downloaded(files)
vmt._UPD["installed"] = sorted(files)
print("INSTALLED", msg, flush=True)
check("examples installed in the managed folder", os.path.isfile(vmt.managed_examples()), vmt.managed_examples())
check("... their sha256 is recorded", vmt._UPD["examples_sha"] == info["assets"]["VM_ExampleAssets.blend"]["digest"][7:]
      and json.load(open(vmt._state_file()))["examples_sha"] == vmt._UPD["examples_sha"])
txt = " | ".join(draw("installed"))
check("panel: examples installed, add them in a file", "Example assets installed" in txt and "Add Example Assets" in txt, txt)
vmt.example_library_path = real_exp
check("example_library_path() finds the managed copy", os.path.normcase(vmt.example_library_path() or "") in
      (os.path.normcase(vmt.managed_examples()), os.path.normcase(os.environ.get("VM_EXAMPLES", "") or "-")), vmt.example_library_path())
check("the same release -> examples not wanted again", vmt.wanted_assets() == [], vmt.wanted_assets())
vmt._UPD["assets"]["VM_ExampleAssets.blend"] = dict(vmt._UPD["assets"]["VM_ExampleAssets.blend"], digest="sha256:" + "1" * 64)
check("a release with NEW examples -> wanted again", vmt.wanted_assets() == ["VM_ExampleAssets.blend"], vmt.wanted_assets())
vmt._UPD["include_examples_test"] = False
check("... but not when the opt-in is off", vmt.wanted_assets() == [], vmt.wanted_assets())
print("UPDATER TEST", "OK" if not FAILS else f"{len(FAILS)} FAILED", flush=True)
os._exit(0)
