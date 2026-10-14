"""Build an HFS disk image from a folder extracted from a classic Mac archive.

The port runs from the user's own copy of the original game: an HFS volume image
(see README). Sites ship the original compressed (.sit); unpacking its loose
files keeps both forks — the data fork is the file itself, the resource fork is
in the file's ..namedfork/rsrc (what `unar -k fork` writes on modern macOS).

Writes the same layout to an HFS image: the application file and the Data/
folder at the volume root. File types are best effort: nothing in src/mac gates
on them (loader and file manager open by name; PBGetFInfo only serves what the
catalog holds).

usage: tools/build_hfs.py <src-dir> <image.hfv> [volume-name]
Requires machfs (pip install machfs), as tools/extract_hfs.py does.
"""
import sys, os
import machfs

def forks(p):
    f = open(p, "rb"); data = f.read(); f.close()
    try:
        rsrc = open(p + "/..namedfork/rsrc", "rb").read()
    except FileNotFoundError:
        rsrc = b""
    return data, rsrc

src, out = sys.argv[1], sys.argv[2]
volname = sys.argv[3] if len(sys.argv) > 3 else "Prince2"
appname = "Prince of Persia 2"

v = machfs.Volume()
v.name = volname
dirs = {}
total = 0
for relpath, subdirs, files in os.walk(src):
    rel = os.path.relpath(relpath, src)
    parent = v if rel == "." else dirs[rel]
    for d in subdirs:
        key = os.path.relpath(os.path.join(relpath, d), src)
        parent[d] = dirs.setdefault(key, machfs.Folder())
    for name in files:
        p = os.path.join(relpath, name)
        if os.path.abspath(p) == os.path.abspath(out) or name.startswith("."):
            continue
        data, rsrc = forks(p)
        total += len(data) + len(rsrc)
        f = machfs.File(); f.data, f.rsrc = data, rsrc
        if rel == "." and name == appname:              # the application
            f.type, f.creator = b"APPL", b"PRIN"
        else:
            f.type, f.creator = b"rsrv", b"????"
        parent[name] = f
if total > 23 * 1024 * 1024:
    sys.exit("too much content for one 24 MB volume (%d fork bytes)" % total)
open(out, "wb").write(v.write(24 * 1024 * 1024))
print('wrote %s: volume "%s", %d fork bytes' % (out, volname, total))
