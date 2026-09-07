# -*- coding: utf-8 -*-
"""Draft a starting road network as a PNG layer to import into map/locations.xcf.

Not authoritative - it is a base coat to redraw over. The real network is whatever ends up
painted on the roads layer; map/gen_roads.py reads that back into 09_roads.txt.

Method: least-cost paths over the land adjacency graph (map/gen_adjacency.py), weighted by
terrain, between the market seats of 03_markets.txt. A minimum spanning tree over the markets
of each landmass gives the trunk corridors; the most expensive MST links are then dropped
until coverage lands near vanilla Earth's 5.6% of land locations. Dropping the long hauls
first is also how road networks actually grow - dense cores connect before remote outposts.

The coverage budget is allocated PER LANDMASS, proportional to its land locations. A single
global budget is spent entirely on the biggest, densest continent and leaves the rest bare.

Lines are drawn centroid -> shared-border midpoint -> centroid so a road stays inside the two
locations it joins instead of clipping a third. The result is verified by re-detecting the
edges from the rendered pixels.
"""
import os, re, csv, heapq, collections
import numpy as np
from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None
ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
MOD = os.path.join(REPO, "wip mod folder")
MAPD = os.path.join(MOD, "in_game", "map_data")
rd = lambda p: open(p, encoding='utf-8-sig', errors='replace').read()
TARGET_COVERAGE = 0.056          # vanilla Earth: 1611 road locations / ~28.5k land
LINE_WIDTH = 3
LAND_TOTAL = 4518

# ---------------------------------------------------------------- terrain cost
# Relative effort of pushing a road through a location. Flat farmland is the baseline.
TOPO = {"flatland": 1.0, "hills": 1.8, "plateau": 1.5, "wetlands": 3.0,
        "mountains": 4.5, "volcanic": 3.5, "glacial": 4.0, "deadlands": 3.0}
VEG = {"farmland": 0.8, "grasslands": 1.0, "sparse": 1.2, "woods": 1.4, "forest": 1.8,
       "jungle": 3.0, "desert": 2.5, "fungal": 2.0, "dead": 2.5}

tpl = rd(os.path.join(MAPD, "location_templates.txt"))
cost = {}
for m in re.finditer(r'^([a-z_0-9]+) = \{([^}]*)\}', tpl, re.M):
    b = m.group(2)
    t = re.search(r'topography = (\w+)', b)
    v = re.search(r'vegetation = (\w+)', b)
    cost[m.group(1)] = (TOPO.get(t.group(1) if t else "", 2.0) *
                        VEG.get(v.group(1) if v else "", 1.5))

adj = collections.defaultdict(set)
for a, b in list(csv.reader(open(os.path.join(ROOT, "location_adjacency.csv"), encoding='utf-8')))[1:]:
    adj[a].add(b)
    adj[b].add(a)
markets = sorted(set(re.findall(r'add_market = ([a-z_0-9]+)',
                                rd(os.path.join(MOD, "main_menu", "setup", "start", "03_markets.txt")))))
markets = [m for m in markets if m in adj]
print("markets on a landmass with neighbours: %d" % len(markets))

# ---------------------------------------------------------------- least-cost paths
def dijkstra(src):
    dist = {src: 0.0}
    prev = {}
    pq = [(0.0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, 1e18):
            continue
        for v in adj[u]:
            nd = d + cost.get(v, 2.0)
            if nd < dist.get(v, 1e18):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    return dist, prev

paths = {s: dijkstra(s) for s in markets}
print("dijkstra done from %d seats" % len(markets))

# ---------------------------------------------------------------- MST over the markets
cand = []
for i, s in enumerate(markets):
    dist = paths[s][0]
    for t in markets[i + 1:]:
        if t in dist:
            cand.append((dist[t], s, t))
cand.sort()
parent = {m: m for m in markets}

def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x

mst = []
for w, s, t in cand:
    a, b = find(s), find(t)
    if a != b:
        parent[a] = b
        mst.append((w, s, t))
print("MST links over the market graph: %d" % len(mst))

def route(s, t):
    prev = paths[s][1]
    seq, x = [t], t
    while x != s:
        x = prev[x]
        seq.append(x)
    return seq[::-1]

# landmass of every location, so the budget can be shared out per continent
mass, seen, mid = {}, set(), 0
for n in sorted(adj):
    if n in seen:
        continue
    st, c = [n], set()
    while st:
        x = st.pop()
        if x in c:
            continue
        c.add(x)
        st.extend(y for y in adj[x] if y not in c)
    seen |= c
    for x in c:
        mass[x] = mid
    mid += 1
mass_size = collections.Counter(mass.values())

kept, edges, on_net = [], set(), set()
per_mass = collections.defaultdict(set)
for w, s, t in mst:                                   # cheapest links first
    seq = route(s, t)
    m = mass[s]
    budget = TARGET_COVERAGE * mass_size[m]
    if per_mass[m] and len(per_mass[m] | set(seq)) > budget:
        continue
    kept.append((w, s, t))
    edges |= {(a, b) if a < b else (b, a) for a, b in zip(seq, seq[1:])}
    on_net |= set(seq)
    per_mass[m] |= set(seq)
print("kept %d of %d links -> %d edges, %d locations (%.1f%% coverage)"
      % (len(kept), len(mst), len(edges), len(on_net), 100 * len(on_net) / LAND_TOTAL))
for m in sorted(per_mass, key=lambda k: -mass_size[k]):
    print("   landmass %2d: %5d land, %3d on the network (%.1f%%)"
          % (m, mass_size[m], len(per_mass[m]), 100 * len(per_mass[m]) / mass_size[m]))

# ---------------------------------------------------------------- geometry
name_by_hex, hex_by_name = {}, {}
for m in re.finditer(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([0-9a-fA-F]{6})\s*$',
                     rd(os.path.join(MAPD, "named_locations", "00_default.txt")), re.M):
    name_by_hex[int(m.group(2), 16)] = m.group(1)
    hex_by_name[m.group(1)] = int(m.group(2), 16)
a = np.asarray(Image.open(os.path.join(MAPD, "locations.png")).convert("RGB"), dtype=np.uint32)
H, W = a.shape[:2]
key = (a[:, :, 0] << 16) | (a[:, :, 1] << 8) | a[:, :, 2]
del a

codes = np.unique(key)
idx = np.searchsorted(codes, key)
cnt = np.bincount(idx.ravel(), minlength=len(codes))
ys, xs = np.mgrid[0:H, 0:W]
cy = np.bincount(idx.ravel(), weights=ys.ravel(), minlength=len(codes)) / cnt
cx = np.bincount(idx.ravel(), weights=xs.ravel(), minlength=len(codes)) / cnt
del ys, xs
centroid = {}
for i, c in enumerate(codes):
    nm = name_by_hex.get(int(c))
    if nm:
        centroid[nm] = (float(cx[i]), float(cy[i]))
# a centroid outside its own location (concave or seam-spanning) -> nearest pixel that is inside
fixed = 0
for nm in list(centroid):
    if nm not in on_net:
        continue
    x, y = centroid[nm]
    xi, yi = int(round(x)) % W, min(max(int(round(y)), 0), H - 1)
    if key[yi, xi] != hex_by_name[nm]:
        pts = np.argwhere(key == hex_by_name[nm])
        d = (pts[:, 0] - y) ** 2 + (pts[:, 1] - x) ** 2
        p = pts[int(np.argmin(d))]
        centroid[nm] = (float(p[1]), float(p[0]))
        fixed += 1
print("centroids: %d  (%d relocated to a real interior pixel)" % (len(centroid), fixed))

# medoid of every shared border, in one pass
def border_pairs(k1, k2, y, x):
    m = k1 != k2
    return (np.minimum(k1[m], k2[m]).astype(np.int64), np.maximum(k1[m], k2[m]).astype(np.int64),
            y[m].astype(np.int64), x[m].astype(np.int64))

Y, X = np.mgrid[0:H, 0:W]
chunks = [border_pairs(key[:, :-1], key[:, 1:], Y[:, :-1], X[:, :-1]),
          border_pairs(key[:-1, :], key[1:, :], Y[:-1, :], X[:-1, :])]
del Y, X
lo = np.concatenate([c[0] for c in chunks])
hi = np.concatenate([c[1] for c in chunks])
by = np.concatenate([c[2] for c in chunks])
bx = np.concatenate([c[3] for c in chunks])
del chunks
pk = lo * (1 << 25) + hi
order = np.argsort(pk, kind='stable')
pk, by, bx = pk[order], by[order], bx[order]
uniq = np.unique(pk)
starts = np.searchsorted(pk, uniq)
ends = np.append(starts[1:], len(pk))
border = {}
for s, e in zip(starts, ends):
    a_ = name_by_hex.get(int(pk[s] >> 25))
    b_ = name_by_hex.get(int(pk[s] & ((1 << 25) - 1)))
    if not (a_ and b_):
        continue
    my, mx = by[s:e], bx[s:e]
    j = int(np.argmin((my - my.mean()) ** 2 + (mx - mx.mean()) ** 2))   # medoid of the border
    border[(a_, b_) if a_ < b_ else (b_, a_)] = (int(mx[j]), int(my[j]))
print("shared borders measured: %d" % len(border))

# ---------------------------------------------------------------- render
img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
drawn, skipped = 0, 0
for a_, b_ in sorted(edges):
    if a_ not in centroid or b_ not in centroid or (a_, b_) not in border:
        skipped += 1
        continue
    ca, cb, mb = centroid[a_], centroid[b_], border[(a_, b_)]
    if abs(ca[0] - cb[0]) > W / 2:      # crosses the wrap seam - leave that one to be drawn by hand
        skipped += 1
        continue
    d.line([(int(ca[0]), int(ca[1])), mb, (int(cb[0]), int(cb[1]))],
           fill=(220, 40, 40, 255), width=LINE_WIDTH)
    drawn += 1
dst = os.path.join(ROOT, "roads_draft.png")
img.save(dst)
print("drew %d of %d edges (%d skipped) -> map/roads_draft.png" % (drawn, len(edges), skipped))

# ---------------------------------------------------------------- verify the render
road = np.asarray(img)[:, :, 3] >= 128

def cross(ra, rb, ka, kb):
    m = ra & rb & (ka != kb)
    return set(zip(np.minimum(ka[m], kb[m]).tolist(), np.maximum(ka[m], kb[m]).tolist()))

got = cross(road[:, :-1], road[:, 1:], key[:, :-1], key[:, 1:]) | \
      cross(road[:-1, :], road[1:, :], key[:-1, :], key[1:, :])
got = {(name_by_hex[a_], name_by_hex[b_]) for a_, b_ in got
       if a_ in name_by_hex and b_ in name_by_hex}
got = {(a_, b_) if a_ < b_ else (b_, a_) for a_, b_ in got}
print("\nverify: intended %d edges, the drawing reads back as %d" % (len(edges), len(got)))
print("        %d present, %d missed, %d extra (a line clipped a third location)"
      % (len(edges & got), len(edges - got), len(got - edges)))
