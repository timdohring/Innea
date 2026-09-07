# -*- coding: utf-8 -*-
"""Turn a hand-drawn road layer into main_menu/setup/start/09_roads.txt.

EU5 roads are not drawn geometry - `road_network = { a = b }` is just a set of neighbouring
location pairs. So a painted line only has to say which borders it crosses, and the order it
was drawn in is irrelevant: wherever two 4-adjacent road pixels sit in different locations,
that border gets a road. Junctions, branches and loops all fall out for free.

Input:  a PNG the same size as map_data/locations.png (16384x8192) with the roads painted on
        transparency - export just the road layer from locations.xcf.
Usage:  python map/gen_roads.py [path_to_roads.png]
"""
import os, re, sys, collections
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
MOD  = os.path.join(REPO, "wip mod folder")
MAPD = os.path.join(MOD, "in_game", "map_data")
SRC  = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "roads.png")
ALPHA_CUT = 128          # anti-aliased edge pixels below this are ignored
rd = lambda p: open(p, encoding='utf-8-sig', errors='replace').read()

# ---------------------------------------------------------------- reference data
name_by_hex = {int(m.group(2), 16): m.group(1) for m in re.finditer(
    r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([0-9a-fA-F]{6})\s*$',
    rd(os.path.join(MAPD, "named_locations", "00_default.txt")), re.M)}
dm = re.sub(r'#.*', '', rd(os.path.join(MAPD, "default.map")))
def lst(k):
    m = re.search(k + r'\s*=\s*\{(.*?)\}', dm, re.S)
    return set(m.group(1).split()) if m else set()
sea, lakes, waste = lst('sea_zones'), lst('lakes'), lst('impassable_mountains')
nonland = sea | lakes | waste

loc = np.asarray(Image.open(os.path.join(MAPD, "locations.png")).convert("RGB"), dtype=np.uint32)
H, W = loc.shape[:2]
lkey = (loc[:, :, 0] << 16) | (loc[:, :, 1] << 8) | loc[:, :, 2]
del loc

# ---------------------------------------------------------------- the drawing
img = Image.open(SRC)
if img.size != (W, H):
    sys.exit("roads.png is %dx%d but the map is %dx%d - export the layer at full canvas size"
             % (img.size[0], img.size[1], W, H))
if "A" in img.getbands():
    alpha = np.asarray(img.convert("RGBA"))[:, :, 3]
    road = alpha >= ALPHA_CUT
    soft = int(((alpha > 0) & (alpha < ALPHA_CUT)).sum())
else:
    a = np.asarray(img.convert("RGB"), dtype=np.uint32)
    k = (a[:, :, 0] << 16) | (a[:, :, 1] << 8) | a[:, :, 2]
    bg = np.bincount(k.ravel()).argmax()
    road = k != bg
    soft = 0
    print("no alpha channel - treating #%06x (the commonest colour) as background" % bg)
print("road pixels: %d" % int(road.sum()) + ("   (ignored %d anti-aliased edge pixels)" % soft if soft else ""))
if not road.any():
    sys.exit("nothing painted in %s" % SRC)

# ---------------------------------------------------------------- pixels -> edges
def crossings(ra, rb, ka, kb):
    m = ra & rb & (ka != kb)
    if not m.any():
        return []
    lo = np.minimum(ka[m], kb[m]); hi = np.maximum(ka[m], kb[m])
    return list(zip(lo.tolist(), hi.tolist()))

pairs = collections.Counter()
pairs.update(crossings(road[:, :-1], road[:, 1:], lkey[:, :-1], lkey[:, 1:]))
pairs.update(crossings(road[:-1, :], road[1:, :], lkey[:-1, :], lkey[1:, :]))
pairs.update(crossings(road[:, -1],  road[:, 0],  lkey[:, -1],  lkey[:, 0]))   # wrap_x seam

edges, dropped, unknown = set(), collections.Counter(), set()
for (a_, b_), n in pairs.items():
    A, B = name_by_hex.get(a_), name_by_hex.get(b_)
    if A is None: unknown.add("%06x" % a_)
    if B is None: unknown.add("%06x" % b_)
    if not (A and B):
        continue
    bad = [x for x in (A, B) if x in nonland]
    if bad:
        dropped[", ".join(sorted(bad))] += 1
        continue
    edges.add((A, B) if A < B else (B, A))

if unknown:
    print("!! road pixels over unnamed colours: %s" % " ".join(sorted(unknown)[:10]))
if dropped:
    print("!! %d border crossings dropped for touching non-land:" % sum(dropped.values()))
    for k, n in dropped.most_common(12):
        print("     %-40s %d crossing(s)" % (k, n))

# ---------------------------------------------------------------- report
adj = collections.defaultdict(set)
for a_, b_ in edges:
    adj[a_].add(b_); adj[b_].add(a_)
seen, comps = set(), []
for n in adj:
    if n in seen: continue
    st, c = [n], set()
    while st:
        x = st.pop()
        if x in c: continue
        c.add(x); st.extend(y for y in adj[x] if y not in c)
    seen |= c; comps.append(len(c))
comps.sort(reverse=True)
deg = collections.Counter(len(v) for v in adj.values())
print()
print("road edges: %d   locations on the network: %d" % (len(edges), len(adj)))
print("degree: %s" % dict(sorted(deg.items())))
print("components: %d   sizes: %s" % (len(comps), comps[:12]))
land_total = sum(1 for n in name_by_hex.values() if n not in nonland)
print("coverage: %.1f%% of %d land locations   (vanilla Earth runs 5.6%%)"
      % (100 * len(adj) / land_total, land_total))

# ---------------------------------------------------------------- write
dst = os.path.join(MOD, "main_menu", "setup", "start", "09_roads.txt")
L = ["# Innea starting road network.",
     "# Traced from the hand-drawn road layer in map/locations.xcf by map/gen_roads.py:",
     "# wherever the painted line crosses a border between two land locations, that pair gets a road.",
     "# Starting roads are level 1 (gravel_road) - 09_roads.txt carries no road type.",
     "", "road_network = {", ""]
by_first = collections.defaultdict(list)
for a_, b_ in sorted(edges):
    by_first[a_].append(b_)
for a_ in sorted(by_first):
    for b_ in sorted(by_first[a_]):
        L.append("\t%s = %s" % (a_, b_))
L += ["", "}", ""]
open(dst, "w", encoding="utf-8", newline="\r\n").write("\n".join(L))
print("\nwritten %d pairs to main_menu/setup/start/09_roads.txt" % len(edges))
