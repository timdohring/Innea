# -*- coding: utf-8 -*-
"""Compute the land adjacency graph of the Innea map from map_data/locations.png.

EU5 ships no adjacency list - map_data/adjacencies.csv holds only special crossings
(straits, 183 rows in vanilla, none in Innea), so neighbourhood is implicit in the bitmap.
This walks the 16384x8192 colour array, records every 4-neighbour colour transition, resolves
the colours to location names via map_data/named_locations/00_default.txt, and writes the
land-land pairs to map/location_adjacency.csv.

The map is wrap_x, so column 0 and column 16383 are neighbours too.
Sea zones, lakes and impassable mountains (from default.map) are excluded from the output but
still counted, so the summary can report which land locations are coastal or lake-side.
"""
import os, re, csv, collections
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
ROOT = os.path.dirname(os.path.abspath(__file__))
MOD  = os.path.join(os.path.dirname(ROOT), "wip mod folder")
MAPD = os.path.join(MOD, "in_game", "map_data")
rd = lambda p: open(p, encoding='utf-8-sig', errors='replace').read()

# ---------------------------------------------------------------- colour -> name
hex2name = {int(m.group(2), 16): m.group(1) for m in re.finditer(
    r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([0-9a-fA-F]{6})\s*$',
    rd(os.path.join(MAPD, "named_locations", "00_default.txt")), re.M)}
print("named locations: %d" % len(hex2name))

dm = re.sub(r'#.*', '', rd(os.path.join(MAPD, "default.map")))  # strip comments inside the lists
def lst(key):
    m = re.search(key + r'\s*=\s*\{(.*?)\}', dm, re.S)
    return set(m.group(1).split()) if m else set()
sea, lakes, waste = lst('sea_zones'), lst('lakes'), lst('impassable_mountains')
nonland = sea | lakes | waste
print("sea %d  lakes %d  wasteland %d  (non-land total %d)" % (
    len(sea), len(lakes), len(waste), len(nonland)))

# ---------------------------------------------------------------- the bitmap
img = Image.open(os.path.join(MAPD, "locations.png")).convert("RGB")
a = np.asarray(img, dtype=np.uint32)
h, w = a.shape[:2]
print("locations.png: %dx%d" % (w, h))
key = (a[:, :, 0] << 16) | (a[:, :, 1] << 8) | a[:, :, 2]
del a

# every 4-neighbour transition, plus the wrap_x seam
pairs = set()
def collect(x, y):
    m = x != y
    if not m.any():
        return
    lo = np.minimum(x[m], y[m]); hi = np.maximum(x[m], y[m])
    pairs.update(zip(lo.tolist(), hi.tolist()))

collect(key[:, :-1], key[:, 1:])     # horizontal
collect(key[:-1, :], key[1:, :])     # vertical
collect(key[:, -1],  key[:, 0])      # wrap_x seam
print("distinct colour-pair adjacencies: %d" % len(pairs))

# ---------------------------------------------------------------- resolve
edges, unknown = set(), collections.Counter()
for lo, hi in pairs:
    a_, b_ = hex2name.get(lo), hex2name.get(hi)
    if a_ is None: unknown["%06x" % lo] += 1
    if b_ is None: unknown["%06x" % hi] += 1
    if a_ and b_:
        edges.add((a_, b_) if a_ < b_ else (b_, a_))
if unknown:
    print("colours on the map with no name (%d): %s" % (
        len(unknown), " ".join(sorted(unknown)[:10])))

land_edges = sorted(e for e in edges if e[0] not in nonland and e[1] not in nonland)
print("edges total %d   land-land %d" % (len(edges), len(land_edges)))

with open(os.path.join(ROOT, "location_adjacency.csv"), "w", encoding="utf-8", newline="") as fh:
    wtr = csv.writer(fh)
    wtr.writerow(["a", "b"])
    wtr.writerows(land_edges)

# ---------------------------------------------------------------- summary
land = {n for n in hex2name.values() if n not in nonland}
adj = collections.defaultdict(set)
for a_, b_ in land_edges:
    adj[a_].add(b_); adj[b_].add(a_)
adj_any = collections.defaultdict(set)
for a_, b_ in edges:
    adj_any[a_].add(b_); adj_any[b_].add(a_)

deg = collections.Counter(len(adj.get(n, ())) for n in land)
print()
print("land locations: %d   with at least one land neighbour: %d" % (
    len(land), sum(1 for n in land if adj.get(n))))
print("land-neighbour degree: min %d  max %d  mean %.2f" % (
    min(deg.elements(), default=0), max(deg.elements(), default=0),
    sum(len(adj.get(n, ())) for n in land) / max(len(land), 1)))
iso = sorted(n for n in land if not adj.get(n))
print("island/isolated land locations (no land neighbour): %d" % len(iso))
if iso:
    print("   " + " ".join(iso[:40]) + (" ..." if len(iso) > 40 else ""))

seen, comps = set(), []
for n in land:
    if n in seen: continue
    stack, c = [n], set()
    while stack:
        x = stack.pop()
        if x in c: continue
        c.add(x); stack.extend(y for y in adj[x] if y not in c)
    seen |= c; comps.append(sorted(c))
comps.sort(key=len, reverse=True)
print("connected landmasses: %d   sizes: %s" % (
    len(comps), [len(c) for c in comps[:15]]))
touch_water = sum(1 for n in land if any(m in sea for m in adj_any[n]))
print("land locations touching a sea zone: %d" % touch_water)
landlocked_islands = [n for n in iso if not any(m in sea for m in adj_any.get(n, ()))]
print("isolated land locations NOT touching a sea zone: %d %s" % (
    len(landlocked_islands), " ".join(landlocked_islands[:20])))
print()
ghost = sorted(nonland - set(hex2name.values()))
if ghost:
    print("names in default.map that are NOT painted locations (%d): %s" % (
        len(ghost), " ".join(ghost)))
print("written: map/location_adjacency.csv")
