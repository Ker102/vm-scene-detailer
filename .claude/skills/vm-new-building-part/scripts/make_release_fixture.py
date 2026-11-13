"""Make the FAKE release server folder that updater_test.py reads (never GitHub).
  python -I make_release_fixture.py <T> <PORT> <tag> <file> [<file> ...]
Writes <T>/serve/assets/<files> and two GitHub-style release JSONs:
  <T>/serve/repos/test/vm/releases/latest    (right sizes and sha256 digests)
  <T>/serve/repos/test/bad/releases/latest   (the add-on's digest is wrong)
Then serve it:  python -I -m http.server <PORT> --bind 127.0.0.1 --directory <T>/serve"""
import hashlib, json, os, shutil, sys

T, PORT, TAG, FILES = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
A = os.path.join(T, "serve", "assets")
os.makedirs(A, exist_ok=True)
assets = []
for f in FILES:
    name = os.path.basename(f)
    dst = os.path.join(A, name)
    if os.path.abspath(f) != os.path.abspath(dst):
        shutil.copy2(f, dst)
    h = hashlib.sha256()
    with open(dst, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    assets.append(dict(name=name, url=f"http://127.0.0.1:{PORT}/assets/{name}",
                       size=os.path.getsize(dst), digest="sha256:" + h.hexdigest()))
rel = dict(tag_name=TAG, html_url="https://example.invalid/release",
           body="Test release.\nThe engine library no longer carries the example assets.", assets=assets)
for repo, bad in (("vm", False), ("bad", True)):
    d = os.path.join(T, "serve", "repos", "test", repo, "releases")
    os.makedirs(d, exist_ok=True)
    r = json.loads(json.dumps(rel))
    if bad:
        for a in r["assets"]:
            if a["name"].endswith(".py"):
                a["digest"] = "sha256:" + "0" * 64
    with open(os.path.join(d, "latest"), "w") as fh:
        json.dump(r, fh)
print("FIXTURE", TAG, [(a["name"], a["size"]) for a in assets])
