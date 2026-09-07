# -*- coding: utf-8 -*-
"""Generate main_menu/setup/start/14_development.txt.

EU5 does not store a development value per location. 14_development.txt is one additive
formula and every location's starting development is the sum of every term that matches it:
base + coastal*NHS + river*size + road + rank + vegetation + climate + topography
     + region + area + province + the location's own term.

Innea already has an authored development per location (the Information sheet's Total Dev,
which is EU4 tax+production+manpower). The design call is that Innea should sit a third below
that, so the target here is  sheet_dev * 2/3  - which lands almost exactly on vanilla Earth's
own distribution (median 8, p90 24, max 50).

The fit is layered the way vanilla's file is written, coarse to fine:
  1. vanilla's own geography/rank/road/coastal coefficients, kept verbatim
  2. a term per region   (32)
  3. a term per area     (123)
  4. a term per province (~950)
  5. the five terrain values Innea has and Earth does not, fitted
  6. a term per location, only where the layers above still miss by LOC_CUT
Each layer is fitted on the residual left by the one above, using the median so a few extreme
locations cannot drag a whole region.

Do not expect geography to carry this on its own. The authored dev spread INSIDE a single
province has a median of 10 and a p90 of 20, against an overall standard deviation of 6.8 -
neighbouring locations with identical terrain, climate, region and province routinely differ
by 10+ development. Geography alone (all 915 province terms included) still leaves a p90 error
of 7 and a worst case of 23, so the per-location layer carries real signal, not noise.

14 of Innea's 1047 province names contain a hyphen and no vanilla key does, so whether the
parser accepts them is untested. Those provinces are skipped and each of their 67 locations
gets its own term instead, whatever the cutoff.
"""
import os, re, csv, io, collections, statistics

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
MOD = os.path.join(REPO, "wip mod folder")
MAPD = os.path.join(MOD, "in_game", "map_data")
SETUP = os.path.join(MOD, "main_menu", "setup", "start")
MAPW = r"C:\Users\timdo\OneDrive\Documents\Projects\Innea modding\map"
rd = lambda p: open(p, encoding='utf-8-sig', errors='replace').read()

SCALE = 2.0 / 3.0          # "a third lower than the sheet"
LOC_CUT = 10               # emit a per-location term once the layers above miss by this much

# vanilla's coefficients, copied from the base game's 14_development.txt
BASE = -2
COASTAL, ROAD, CITY, TOWN = 5, 2, 5, 2
# River contributes 0.5 * river size. It is kept at vanilla's value even though it cannot be
# fitted: map_data/rivers.png is uniformly palette index 255 across all 134M pixels, so Innea
# has no rivers painted and the term adds nothing today. When rivers are drawn it will start
# adding up to +2.5 on the biggest of them, on top of the values fitted here.
RIVER = 0.5
VANILLA = {
    "grasslands": 1, "farmland": 3, "sparse": -1, "forest": -2, "woods": -1,
    "desert": -3, "jungle": -4,
    "tropical": -3, "subtropical": 2, "oceanic": 1, "arid": -4, "cold_arid": -3,
    "mediterranean": 2, "continental": 1, "arctic": -5,
    "flatland": 1, "mountains": -3, "hills": -2, "plateau": -1, "wetlands": -4,
}
# Innea has these and Earth does not - fitted below rather than guessed
INNEA_ONLY = ["deadlands", "glacial", "volcanic", "fungal", "dead"]

# ---------------------------------------------------------------- inputs
names = {m.group(1): m.group(2).lower() for m in re.finditer(
    r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([0-9a-fA-F]{6})\s*$',
    rd(os.path.join(MAPD, "named_locations", "00_default.txt")), re.M)}
h2n = {h: n for n, h in names.items()}
dm = re.sub(r'#.*', '', rd(os.path.join(MAPD, "default.map")))
def lst(k):
    m = re.search(k + r'\s*=\s*\{(.*?)\}', dm, re.S)
    return set(m.group(1).split()) if m else set()
nonland = lst('sea_zones') | lst('lakes') | lst('impassable_mountains')
land = {n for n in names if n not in nonland}

tpl = rd(os.path.join(MAPD, "location_templates.txt"))
info, nhs_bad = {}, []
for m in re.finditer(r'^([a-z_0-9]+) = \{([^}]*)\}', tpl, re.M):
    b = m.group(2)
    g = lambda k: (re.search(k + r' = (-?[a-z_0-9.]+)', b) or [None, None])[1]
    nhs = float(g('natural_harbor_suitability') or 0)
    # NHS multiplies coastal=5. Innea deliberately uses negative values (down to -0.5) as a
    # bad-harbour penalty, which vanilla never does, so those are kept. Anything outside
    # -1..1 is a decimal-point slip - a stray 75 is worth +375 development - and is refused.
    if not -1.0 <= nhs <= 1.0:
        nhs_bad.append((m.group(1), nhs))
        nhs = min(max(nhs, -1.0), 1.0)
    info[m.group(1)] = dict(topo=g('topography'), veg=g('vegetation'), cli=g('climate'), nhs=nhs)
if nhs_bad:
    print("!! natural_harbor_suitability outside 0..1, clamped: %s" % nhs_bad)

# hierarchy: continent > subcontinent > region > area > province
toks = re.findall(r'[A-Za-z_][A-Za-z0-9_\-]*|\{|\}|=', rd(os.path.join(MAPD, "definitions.txt")))
st, path, i = [], {}, 0
while i < len(toks):
    x = toks[i]
    if x in ('{', '}', '='):
        if x == '}' and st:
            st.pop()
        i += 1
        continue
    if i + 2 < len(toks) and toks[i + 1] == '=' and toks[i + 2] == '{':
        st.append(x)
        i += 3
        continue
    path[x] = list(st)
    i += 1
region = {n: p[2] for n, p in path.items() if len(p) > 2}
area = {n: p[3] for n, p in path.items() if len(p) > 3}
province = {n: p[4] for n, p in path.items() if len(p) > 4}
# a hyphen has never appeared in a vanilla development key; skip those provinces and let their
# locations be carried individually rather than risk a key the parser may not accept
HYPHEN = {p for p in province.values() if '-' in p}
province_ok = {n: p for n, p in province.items() if p not in HYPHEN}
forced = {n for n, p in province.items() if p in HYPHEN}

rank = {m.group(1): m.group(2) for m in re.finditer(
    r'^\s*([a-z_0-9]+)\s*=\s*\{[^}]*?rank\s*=\s*(\w+)', rd(os.path.join(SETUP, "07_cities_and_buildings.txt")), re.M)}
roads = set()
for m in re.finditer(r'^\s*([a-z_0-9]+)\s*=\s*([a-z_0-9]+)\s*$', rd(os.path.join(SETUP, "09_roads.txt")), re.M):
    roads.add(m.group(1)); roads.add(m.group(2))

# authored development, via the EU4 id bridge
id2hex = {}
for r in csv.reader(io.StringIO(open(os.path.join(MAPW, "location_def.csv"), encoding='latin-1').read()),
                    delimiter=';'):
    if len(r) >= 4 and r[0].strip().isdigit():
        id2hex[int(r[0])] = "%02x%02x%02x" % (int(r[1]), int(r[2]), int(r[3]))
target = {}
for r in list(csv.reader(io.StringIO(rd(os.path.join(MAPW, "sheet_columns", "sheet_gid0.csv")))))[2:]:
    if r and r[0].strip().isdigit():
        loc = h2n.get(id2hex.get(int(r[0])))
        if loc in land:
            try:
                target[loc] = float(r[7] or 0) * SCALE
            except ValueError:
                pass
print("land locations %d   with an authored dev %d" % (len(land), len(target)))
tv = sorted(target.values())
print("target dev: median %.1f  mean %.1f  p90 %.1f  max %.1f"
      % (statistics.median(tv), statistics.mean(tv), tv[9 * len(tv) // 10], tv[-1]))

# ---------------------------------------------------------------- layer 1: fixed geography
def fixed(n):
    d = info.get(n, {})
    v = BASE + COASTAL * d.get('nhs', 0)
    if n in roads:
        v += ROAD
    r = rank.get(n)
    if r in ('city', 'megalopolis'):
        v += CITY
    elif r == 'town':
        v += TOWN
    for k in (d.get('topo'), d.get('veg'), d.get('cli')):
        v += VANILLA.get(k, 0)
    return v

resid = {n: target[n] - fixed(n) for n in target}

# ---------------------------------------------------------------- layers 2-3: region, area
# Coarse to fine. Fitting terrain before geography lets the terrain terms absorb a whole
# region's offset, which produced nonsense like volcanic = +14.
def fit(keyf, resid):
    grp = collections.defaultdict(list)
    for n in resid:
        k = keyf.get(n)
        if k:
            grp[k].append(n)
    out = {}
    for k, ns in grp.items():
        out[k] = round(statistics.median(resid[n] for n in ns))
        for n in ns:
            resid[n] -= out[k]
    return out

reg_term = fit(region, resid)
area_term = fit(area, resid)
prov_term = fit(province_ok, resid)
print("region terms %d   area terms %d   province terms %d (skipped %d hyphenated, %d locations)"
      % (len(reg_term), len(area_term), len(prov_term), len(HYPHEN), len(forced)))

# ---------------------------------------------------------------- layer 4: Innea-only terrain
extra = {}
for k in INNEA_ONLY:
    grp = [n for n in resid if info.get(n, {}).get('topo') == k or info.get(n, {}).get('veg') == k]
    if grp:
        extra[k] = round(statistics.median(resid[n] for n in grp))
        for n in grp:
            resid[n] -= extra[k]
print("Innea-only terrain terms:", extra)

# how much does the geographic model explain on its own, before per-location patching?
pre = sorted(abs(v) for v in resid.values())
print("BEFORE per-location terms: median miss %.2f  p90 %.2f  max %.2f   within %d: %.0f%%"
      % (statistics.median(pre), pre[9 * len(pre) // 10], pre[-1], LOC_CUT,
         100 * sum(1 for e in pre if e < LOC_CUT) / len(pre)))

# ---------------------------------------------------------------- layer 5: per location
loc_term = {n: round(v) for n, v in resid.items()
            if (abs(v) >= LOC_CUT or n in forced) and round(v) != 0}
print("per-location terms %d of %d (cut |resid| >= %d, plus %d in hyphenated provinces)"
      % (len(loc_term), len(target), LOC_CUT, sum(1 for n in loc_term if n in forced)))

# ---------------------------------------------------------------- verify
final = {}
for n in target:
    v = fixed(n)
    d = info.get(n, {})
    for k in (d.get('topo'), d.get('veg')):
        v += extra.get(k, 0)
    v += (reg_term.get(region.get(n), 0) + area_term.get(area.get(n), 0)
          + prov_term.get(province_ok.get(n), 0) + loc_term.get(n, 0))
    final[n] = v
err = sorted(abs(final[n] - target[n]) for n in target)
fv = sorted(final.values())
print()
print("achieved: median %.1f  mean %.1f  p90 %.1f  min %.1f  max %.1f"
      % (statistics.median(fv), statistics.mean(fv), fv[9 * len(fv) // 10], fv[0], fv[-1]))
print("error vs target: median %.2f  p90 %.2f  max %.2f   within 1.0: %.0f%%"
      % (statistics.median(err), err[9 * len(err) // 10], err[-1],
         100 * sum(1 for e in err if e <= 1.0) / len(err)))
print("locations scoring below 0: %d (%.0f%%)" % (sum(1 for v in fv if v < 0), 100 * sum(1 for v in fv if v < 0) / len(fv)))

# ---------------------------------------------------------------- write
L = ["# Innea starting development.",
     "#",
     "# EU5 builds development from this one additive formula - every term that matches a",
     "# location is summed. Generated by map/gen_development.py.",
     "#",
     "# Fitted to the Information sheet's Total Dev * %.3f (the design call: Innea sits a third" % SCALE,
     "# below its EU4 numbers). The geography, rank, road and coastal coefficients are vanilla's",
     "# own, kept verbatim; region, area and province terms are fitted on the residual, and a",
     "# location gets its own term only where those still miss by %d or more." % LOC_CUT,
     "#",
     "# NOTE: `road` and `city`/`town` read 09_roads.txt and 07_cities_and_buildings.txt, so this",
     "# file must be regenerated whenever either of those changes.",
     "",
     "development = {",
     "",
     "\tbase = %d" % BASE,
     "",
     "\t#Waterways",
     "\tcoastal = %d # multiplies by natural harbor suitability" % COASTAL,
     "\triver = %s # multiplies by river size (1-8). No rivers are painted in rivers.png yet," % RIVER,
     "\t          # so this contributes nothing today - it is here for when they are.",
     "",
     "\t#Roads",
     "\troad = %d" % ROAD,
     "",
     "\t#location rank",
     "\tcity = %d" % CITY,
     "\ttown = %d" % TOWN,
     ""]
L.append("\t# vegetation")
for k in ["grasslands", "farmland", "sparse", "forest", "woods", "desert", "jungle"]:
    L.append("\t%s = %d" % (k, VANILLA[k]))
for k in ["fungal", "dead"]:
    if k in extra:
        L.append("\t%s = %d # Innea only" % (k, extra[k]))
L.append("")
L.append("\t# climate")
for k in ["tropical", "subtropical", "oceanic", "arid", "cold_arid", "mediterranean", "continental", "arctic"]:
    L.append("\t%s = %d" % (k, VANILLA[k]))
L.append("")
L.append("\t# topography")
for k in ["flatland", "mountains", "hills", "plateau", "wetlands"]:
    L.append("\t%s = %d" % (k, VANILLA[k]))
for k in ["deadlands", "glacial", "volcanic"]:
    if k in extra:
        L.append("\t%s = %d # Innea only" % (k, extra[k]))

cont_of = {}
for n, p in path.items():
    if len(p) > 2:
        cont_of[p[2]] = p[0]
L += ["", "\t# regions"]
for cont in sorted(set(cont_of.values())):
    rs = sorted(k for k in reg_term if cont_of.get(k) == cont)
    if not rs:
        continue
    L.append("\t#%s" % cont.replace("_continent", ""))
    for k in rs:
        L.append("\t%s = %d" % (k, reg_term[k]))

reg_of_area = {}
for n, p in path.items():
    if len(p) > 3:
        reg_of_area[p[3]] = p[2]
L += ["", "\t# areas"]
for r in sorted(set(reg_of_area.values())):
    as_ = sorted(k for k in area_term if reg_of_area.get(k) == r and area_term[k] != 0)
    if not as_:
        continue
    L.append("\t#%s" % r)
    for k in as_:
        L.append("\t%s = %d" % (k, area_term[k]))

area_of_prov = {}
for n, p in path.items():
    if len(p) > 4:
        area_of_prov[p[4]] = p[3]
L += ["", "\t# provinces"]
for ar in sorted(set(area_of_prov.values())):
    ps = sorted(k for k in prov_term if area_of_prov.get(k) == ar and prov_term[k] != 0)
    if not ps:
        continue
    L.append("\t#%s" % ar)
    for k in ps:
        L.append("\t%s = %d" % (k, prov_term[k]))

L += ["", "\t# individual locations",
      "\t# %d of these are in the %d hyphenated provinces skipped above; the rest are locations" % (
          sum(1 for n in loc_term if n in forced), len(HYPHEN)),
      "\t# the geography still misses by %d or more." % LOC_CUT]
for n in sorted(loc_term):
    L.append("\t%s = %d" % (n, loc_term[n]))
L += ["}", ""]
open(os.path.join(SETUP, "14_development.txt"), "w", encoding="utf-8", newline="\r\n").write("\n".join(L))
print("\nwritten %d lines to main_menu/setup/start/14_development.txt" % len(L))
