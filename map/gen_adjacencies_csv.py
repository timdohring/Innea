# -*- coding: utf-8 -*-
"""Port the EU4 mod's strait crossings into the EU5 mod's map_data/adjacencies.csv.

EU4 map/adjacencies.csv has 53 rows. 28 are land-sea-land straits that port directly; the
other 25 cross a wasteland or a lake and cannot be expressed as an EU5 `sea` adjacency - see
TODO.md, they are to be handled by map changes.

EU4 leaves start/stop at -1 (the engine picks the crossing point). EU5's own adjacencies.csv
gives real pixel coordinates on all 184 rows, so this computes them: for each pair it takes
the pixels of A that touch the Through sea zone, the pixels of B that touch it, and picks the
closest such pair - the narrowest point of the strait. wrap_x is honoured in the distance.
"""
import csv, io, re, os, collections
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
MOD  = os.path.join(REPO, "wip mod folder")
MAPD = os.path.join(MOD, "in_game", "map_data")
EU4  = r"C:\Users\timdo\OneDrive\Documents\Projects\Innea modding\Version 1.3 (1.33)\2226968141"
MAPW = r"C:\Users\timdo\OneDrive\Documents\Projects\Innea modding\map"
rd = lambda p: open(p, encoding='utf-8-sig', errors='replace').read()

# ---------------------------------------------------------------- the id bridge
id2hex = {}
for r in csv.reader(io.StringIO(open(os.path.join(MAPW, "location_def.csv"), encoding='latin-1').read()),
                    delimiter=';'):
    if len(r) >= 4 and r[0].strip().isdigit():
        id2hex[int(r[0])] = "%02x%02x%02x" % (int(r[1]), int(r[2]), int(r[3]))
name_by_hex, hex_by_name = {}, {}
for m in re.finditer(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([0-9a-fA-F]{6})\s*$',
                     rd(os.path.join(MAPD, "named_locations", "00_default.txt")), re.M):
    name_by_hex[m.group(2).lower()] = m.group(1)
    hex_by_name[m.group(1)] = int(m.group(2), 16)
id2loc = {i: name_by_hex[h] for i, h in id2hex.items() if h in name_by_hex}

dm = re.sub(r'#.*', '', rd(os.path.join(MAPD, "default.map")))
def lst(k):
    m = re.search(k + r'\s*=\s*\{(.*?)\}', dm, re.S)
    return set(m.group(1).split()) if m else set()
sea, lakes, waste = lst('sea_zones'), lst('lakes'), lst('impassable_mountains')

# ---------------------------------------------------------------- select the portable rows
rows = list(csv.reader(io.StringIO(open(os.path.join(EU4, "map", "adjacencies.csv"),
                                        encoding='latin-1').read()), delimiter=';'))
want, skipped = [], []
for r in rows[1:]:
    if not r or not r[0].strip().isdigit():
        continue
    F, T = id2loc.get(int(r[0])), id2loc.get(int(r[1]))
    TH = id2loc.get(int(r[3])) if r[3].strip().lstrip('-').isdigit() else None
    land = lambda n: n and n not in sea and n not in lakes and n not in waste
    if land(F) and land(T) and TH in sea and TH not in lakes:
        want.append((F, T, TH, int(r[0]), int(r[1]), int(r[3])))
    else:
        why = ("through wasteland" if TH in waste else "through lake" if TH in lakes else
               "endpoint not land" if not (land(F) and land(T)) else "unresolved")
        skipped.append((F, T, TH, why))
print("EU4 rows %d -> portable straits %d, skipped %d" % (len(rows) - 1, len(want), len(skipped)))
print("   skipped by reason:", dict(collections.Counter(x[3] for x in skipped)))

# ---------------------------------------------------------------- the bitmap
img = Image.open(os.path.join(MAPD, "locations.png")).convert("RGB")
a = np.asarray(img, dtype=np.uint32)
H, W = a.shape[:2]
key = (a[:, :, 0] << 16) | (a[:, :, 1] << 8) | a[:, :, 2]
del a, img
print("locations.png %dx%d" % (W, H))

def touching(mask_a, mask_s):
    """pixels of A that have a 4-neighbour in S (wrap_x aware)"""
    t = np.zeros_like(mask_a)
    t[:, :-1] |= mask_a[:, :-1] & mask_s[:, 1:]
    t[:, 1:]  |= mask_a[:, 1:]  & mask_s[:, :-1]
    t[:-1, :] |= mask_a[:-1, :] & mask_s[1:, :]
    t[1:, :]  |= mask_a[1:, :]  & mask_s[:-1, :]
    t[:, -1]  |= mask_a[:, -1]  & mask_s[:, 0]      # wrap seam
    t[:, 0]   |= mask_a[:, 0]   & mask_s[:, -1]
    return np.argwhere(t)                            # (y, x)

out = []
for F, T, TH, fid, tid, thid in want:
    ms = key == hex_by_name[TH]
    pa = touching(key == hex_by_name[F], ms)
    pb = touching(key == hex_by_name[T], ms)
    if not len(pa) or not len(pb):
        print("  !! %s / %s do not both touch %s - skipped" % (F, T, TH))
        continue
    # nearest pair, wrap_x aware; sets are coastline slivers so the O(n*m) is small
    dy = pa[:, 0][:, None] - pb[:, 0][None, :]
    dx = np.abs(pa[:, 1][:, None] - pb[:, 1][None, :])
    dx = np.minimum(dx, W - dx)
    d2 = dy.astype(np.int64) ** 2 + dx.astype(np.int64) ** 2
    i, j = np.unravel_index(np.argmin(d2), d2.shape)
    (sy, sx), (ty, tx) = pa[i], pb[j]
    out.append([F, T, "sea", TH, sx, sy, tx, ty,
                "EU4 %d-%d through %d, gap %.0fpx" % (fid, tid, thid, np.sqrt(d2[i, j]))])
    print("  %-22s %-22s %-24s gap %3.0f px" % (F, T, TH, np.sqrt(d2[i, j])))

dst = os.path.join(MAPD, "adjacencies.csv")
with open(dst, "w", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh, delimiter=';')
    w.writerow(["From", "To", "Type", "Through", "start_x", "start_y", "stop_x", "stop_y", "Comment"])
    w.writerows(sorted(out))
print("\nwritten %d rows to map_data/adjacencies.csv" % len(out))
