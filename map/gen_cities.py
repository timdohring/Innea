# -*- coding: utf-8 -*-
"""Generate 07_cities_and_buildings.txt (locations half) and the Innea town_setups.

Rank comes from the Information sheet's Center of Trade Level (col Q), the only authored
"importance" signal Innea has:   CoT 1 -> town,   CoT 2/3 -> city.
Setups are per culture GROUP x port/inland x town/city, and their guilds are chosen from
the goods the group's own urban locations actually produce.

The building_manager half is NOT generated: 2646 of vanilla's 2647 entries carry a
country tag, so it is blocked on 10_countries.txt.
"""
import csv, io, re, os, glob, collections

MOD  = r"C:\Users\timdo\OneDrive\Documents\Projects\Innea modding\EU5 Innea\wip mod folder"
MAPW = r"C:\Users\timdo\OneDrive\Documents\Projects\Innea modding\map"
rd = lambda p: open(p, encoding='utf-8-sig', errors='replace').read()

# Locations to promote to megalopolis. Everything else CoT 2/3 stays a city.
# Fuad is the only one: 1959k against 447k for the next candidate, the highest development
# in the world (76), and a market seat. Vanilla runs 3 across Earth's 20,794 locations.
MEGALOPOLIS = ["fuad"]

# Locations forced to city regardless of their Center of Trade level. A pinned location that
# is not otherwise urban (CoT 0) is pulled into the urban set. zuwar/bayd/sire are Fuad's
# suburbs - the same three damped in gen_pops.py to let Fuad outgrow its hinterland - and at
# 179k/339k/315k they are the metro ring around the world's only megalopolis.
PIN_CITY = ["zuwar", "bayd", "sire"]

# A guild is added to a group's setup when this share of the group's urban locations
# produces one of its input goods. Inputs were read off in_game/common/building_types/.
ADD_AT, LEVEL2_AT = 0.15, 0.40
# INFRASTRUCTURE is held to a weaker test: the group need only produce a matching good
# *somewhere* in its own lands, not in 15% of its locations. A location has exactly one
# raw_material, so stone/clay/iron are seldom any single location's primary RGO even though
# masonry and toolmaking are near-universal in a real town - a 15% share cut mason to 7% of
# groups against vanilla's 66%. These are fed by traded goods, not only local ones.
INFRASTRUCTURE = {"tools_guild", "mason", "pottery_guild", "tannery", "weapon_guild", "granary"}
# Their thresholds are not hand-picked: each is set to the quantile of the group
# territory-share distribution that reproduces vanilla's own frequency for that building
# (read live out of vanilla's 00_default.txt below). Which groups get it is still decided by
# their goods - only how many is matched to vanilla.
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Europa Universalis V\game"
GUILD_INPUTS = {
    "cloth_guild":          {"cotton", "wool", "fiber_crops"},
    "fine_cloth_guild":     {"wool", "silk", "dyes", "alum", "fur"},
    "brewery":              {"wheat", "millet", "fruit", "maize", "beeswax"},
    # wheat is a distillers input in vanilla but it is near-universal, and including it
    # put a distillery in 66% of groups against vanilla's own 21%. Liquor keys off the
    # sugar/rice/potato line instead.
    "distillers_guild":     {"sugar", "rice", "potato"},
    "winery":               {"fruit", "rice", "beeswax", "wine"},
    "paper_guild":          {"lumber", "fiber_crops"},
    "scriptorium":          {"dyes", "lumber"},
    "furniture_guild":      {"lumber", "dyes"},
    "lacquerware_guild":    {"lumber", "dyes"},
    "dyes_guild":           {"lumber", "alum"},
    "glass_guild":          {"lumber", "sand", "alum", "lead"},
    "jewelry_guild":        {"goods_gold", "silver", "copper", "ivory", "amber", "gems", "pearls"},
    "porcelain_guild":      {"clay", "coal"},
    "naval_supplies_guild": {"lumber", "fiber_crops", "tar"},
    # These six were a fixed core on the first pass, which put them on 100% of setups against
    # vanilla's 58-86% - plenty of vanilla towns simply lack a granary or a tannery. They have
    # real inputs like any other building, so they are gated on the group's goods too.
    # granary is the exception: it is a store, not a workshop, so it keys off food goods.
    "tools_guild":          {"iron", "stone", "copper", "tin"},
    "mason":                {"stone", "clay", "marble"},
    "pottery_guild":        {"clay", "lumber"},
    "tannery":              {"livestock", "sand", "tar", "wild_game", "fur"},
    "weapon_guild":         {"lumber", "stone", "coal", "gems", "iron"},
    "granary":              {"wheat", "millet", "rice", "maize", "legumes", "potato",
                             "livestock", "fish", "fruit"},
}
PORT_ONLY = {"naval_supplies_guild"}
# lacquerware shares its inputs with furniture, so the share rule alone put it in 23% of
# groups against vanilla's 3.5%. In vanilla it is an East-Asian building; here it is
# restricted to the Emean language family, which is the analogous part of the world.
FAMILY_ONLY = {"lacquerware_guild": {"human_emea"}}
# The only two buildings on every Innea town: trade and faith, the two that need no local
# input. Everything else is earned from the culture group's own goods.
CORE = [("marketplace", 1, 2), ("temple", 1, 1)]

# ---------------------------------------------------------------- inputs
id2hex = {}
for row in csv.reader(io.StringIO(open(os.path.join(MAPW, "location_def.csv"), encoding='latin-1').read()), delimiter=';'):
    if len(row) >= 4 and row[0].strip().isdigit():
        id2hex[int(row[0])] = "%02x%02x%02x" % (int(row[1]), int(row[2]), int(row[3]))
hex2name = {m.group(2).lower(): m.group(1) for m in re.finditer(
    r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([0-9a-fA-F]{6})\s*$',
    rd(os.path.join(MOD, "in_game", "map_data", "named_locations", "00_default.txt")), re.M)}
id2loc = {i: hex2name[h] for i, h in id2hex.items() if h in hex2name}

tpl = rd(os.path.join(MOD, "in_game", "map_data", "location_templates.txt"))
cul, rgo = {}, {}
for m in re.finditer(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{([^}]*)\}', tpl, re.M):
    b = m.group(2)
    c = re.search(r'culture\s*=\s*(\S+)', b)
    r = re.search(r'raw_material\s*=\s*(\S+)', b)
    if c: cul[m.group(1)] = c.group(1)
    if r: rgo[m.group(1)] = r.group(1)

# culture -> culture group (one file per group in common/cultures/), and
# culture -> language -> language family (one file per family in common/languages/)
c2g, c2l = {}, {}
for f in glob.glob(os.path.join(MOD, "in_game", "common", "cultures", "*.txt")):
    grp = os.path.basename(f)[:-4]
    t = rd(f)
    for m in re.finditer(r'^([a-z_0-9]+)\s*=\s*\{', t, re.M):
        c2g[m.group(1)] = grp
    for m in re.finditer(r'^([a-z_0-9]+)\s*=\s*\{(.*?)\n\}', t, re.S | re.M):
        lg = re.search(r'language\s*=\s*([a-z_0-9]+)', m.group(2))
        if lg: c2l[m.group(1)] = lg.group(1)
l2f = {}
for f in glob.glob(os.path.join(MOD, "in_game", "common", "languages", "01_innea_*.txt")):
    fam = os.path.basename(f)[len("01_innea_"):-4]
    for m in re.finditer(r'^([a-z_0-9]+)\s*=\s*\{', rd(f), re.M):
        l2f[m.group(1)] = fam
c2f = {c: l2f.get(l, "") for c, l in c2l.items()}

# location -> continent/subcontinent/region/area/province
toks = re.findall(r'[A-Za-z_][A-Za-z0-9_]*|\{|\}|=', rd(os.path.join(MOD, "in_game", "map_data", "definitions.txt")))
st, path, i = [], {}, 0
while i < len(toks):
    x = toks[i]
    if x == '{':
        i += 1; continue
    if x == '}':
        if st: st.pop()
        i += 1; continue
    if x == '=':
        i += 1; continue
    if i + 2 < len(toks) and toks[i+1] == '=' and toks[i+2] == '{':
        st.append(x); i += 3; continue
    path[x] = list(st); i += 1

ports = set()
for line in rd(os.path.join(MOD, "in_game", "map_data", "ports.csv")).splitlines():
    line = line.strip()
    if line and not line.startswith('#') and ';' in line:
        ports.add(line.split(';')[0].strip())

# ---------------------------------------------------------------- the urban set
rows = list(csv.reader(io.StringIO(rd(os.path.join(MAPW, "sheet_columns", "sheet_gid0.csv")))))
urban = {}
for r in [r for r in rows[2:] if r and r[0].strip().isdigit()]:
    loc = id2loc.get(int(r[0]))
    if not loc or loc not in path or len(path[loc]) < 4:
        continue
    try: cot = int(r[16] or 0)
    except ValueError: cot = 0
    if loc in PIN_CITY:
        cot = max(cot, 2)
    if cot < 1:
        continue
    grp = c2g.get(cul.get(loc, ""))
    if not grp:
        continue
    urban[loc] = dict(cot=cot, grp=grp, fam=c2f.get(cul.get(loc, ""), ""),
                      rgo=rgo.get(loc, ""), port=loc in ports,
                      name=(r[3].strip() or r[2].strip()), path=path[loc])

# ---------------------------------------------------------------- setups
bygrp = collections.defaultdict(list)
for loc, d in urban.items():
    bygrp[d['grp']].append(loc)

# Infrastructure is tested against the culture group's WHOLE territory, urban and rural, since
# a town is fed by its hinterland; the guilds stay scoped to the group's urban locations.
terr = collections.defaultdict(list)
for loc, c in cul.items():
    grp = c2g.get(c)
    if grp and rgo.get(loc):
        terr[grp].append(rgo[loc])
terr_share = {g: {gl: sum(1 for x in gs if x in GUILD_INPUTS[gl]) / len(gs)
                  for gl in INFRASTRUCTURE} for g, gs in terr.items()}

# vanilla's own frequency for each infrastructure building -> the threshold that reproduces it
_v = rd(os.path.join(GAME, "in_game", "common", "town_setups", "00_default.txt"))
_vs = re.findall(r'^([a-z_0-9]+) = \{(.*?)^\}', _v, re.S | re.M)
INFRA_CUT = {}
for gl in INFRASTRUCTURE:
    want = sum(1 for _, b in _vs if re.search(r'^\s+%s = \d' % gl, b, re.M)) / len(_vs)
    vals = sorted((terr_share[g].get(gl, 0.0) for g in bygrp), reverse=True)
    k = max(1, min(len(vals), round(want * len(vals))))
    INFRA_CUT[gl] = max(vals[k-1], 1e-9)

setups, used, profile = {}, {}, {}
for grp, locs in bygrp.items():
    goods = [urban[l]['rgo'] for l in locs]
    n = len(goods) or 1
    share = {gl: sum(1 for x in goods if x in ins) / n for gl, ins in GUILD_INPUTS.items()}
    for gl in INFRASTRUCTURE:
        ts = terr_share.get(grp, {}).get(gl, 0.0)
        # level 2 in a city when the hinterland leans heavily on that input
        share[gl] = (LEVEL2_AT if ts >= LEVEL2_AT else ADD_AT) if ts >= INFRA_CUT[gl] else 0.0
    fam = urban[locs[0]]['fam']
    extras = sorted([gl for gl, s in share.items()
                     if s >= ADD_AT
                     and fam in FAMILY_ONLY.get(gl, {fam})],
                    key=lambda gl: -share[gl])
    profile[grp] = (extras, share, n)
    base = grp[:-6] if grp.endswith("_group") else grp
    for is_port in (False, True):
        for tier in ("town", "city"):
            sel = [l for l in locs if urban[l]['port'] == is_port
                   and (urban[l]['cot'] == 1) == (tier == "town")]
            if not sel:
                continue
            name = "%s_%s%s" % (base, "port_" if is_port else "", tier)
            b = collections.OrderedDict()
            for k, tl, cl in CORE:
                b[k] = tl if tier == "town" else cl
            for gl in extras:
                if gl in PORT_ONLY and not is_port:
                    continue
                b[gl] = 2 if (tier == "city" and share[gl] >= LEVEL2_AT) else 1
            # wharf on port CITIES only. Vanilla puts one in 18% of its setups; giving every
            # port town one put it in 51% of ours. `dock` is dropped entirely - vanilla uses it
            # in 3 setups of 115, and like the forts it is a soldiers building.
            if is_port and tier == "city":
                b["wharf"] = 1
            # NO castle/stockade here. Both are forts (building_types/forts.txt, fort_level 1 and
            # 2, pop_type = soldiers). Vanilla places 667 of its 716 forts in building_manager
            # with a country tag, not in setups - and Innea has an authored Fort column in the
            # sheet (1005 locations) that a per-culture-group setup cannot express anyway.
            # Forts land with 10_countries.txt / building_manager.
            setups[name] = b
            for l in sel:
                used[l] = name

assert len(used) == len(urban), "%d of %d urban locations got no setup" % (len(used), len(urban))

# Collapse setups that ended up with identical building lists. Once forts and docks left the
# setups, a port variant only differs from its inland twin when the group earned a wharf or a
# naval_supplies_guild - otherwise the two are the same file text under two names.
canon = {}
for name in sorted(setups):
    sig = tuple(setups[name].items())
    canon[name] = canon.get(sig) or name
    canon.setdefault(sig, name)
canon = {n: canon[tuple(setups[n].items())] for n in setups}
merged = len(setups) - len(set(canon.values()))
used = {l: canon[n] for l, n in used.items()}
setups = {n: b for n, b in setups.items() if canon[n] == n}

# ---------------------------------------------------------------- write town_setups
L = ["# Innea town setups - one per culture group x port/inland x town/city.",
     "# Additive: adds new setups alongside vanilla's 114, overrides nothing.",
     "#",
     "# The core (marketplace/temple/tools_guild/mason/pottery_guild/tannery/granary/weapon_guild)",
     "# is on every setup. The guilds after it are chosen per culture group from the goods that",
     "# group's own urban locations produce: a guild is added when >=%d%% of them yield one of its" % (ADD_AT * 100),
     "# inputs, at level 2 in cities when >=%d%%. Inputs read from in_game/common/building_types/." % (LEVEL2_AT * 100),
     "# naval_supplies_guild is port-only. Generated by map/gen_cities.py - do not hand-edit.", ""]
for name in sorted(setups):
    L.append("%s = {" % name)
    for k, v in setups[name].items():
        L.append("\t%s = %d" % (k, v))
    L.append("}")
    L.append("")
os.makedirs(os.path.join(MOD, "in_game", "common", "town_setups"), exist_ok=True)
open(os.path.join(MOD, "in_game", "common", "town_setups", "01_innea.txt"),
     "w", encoding="utf-8", newline="\r\n").write("\n".join(L))

# ---------------------------------------------------------------- write 07
rank = {l: ("megalopolis" if l in MEGALOPOLIS else "city" if urban[l]['cot'] >= 2 else "town")
        for l in urban}
O = ["# Innea cities and towns.",
     "# rank comes from the Information sheet's Center of Trade Level: CoT 1 -> town, CoT 2/3 -> city.",
     "# town_setup is the culture group's setup from in_game/common/town_setups/01_innea.txt.",
     "# Generated by map/gen_cities.py - do not hand-edit.", "",
     "locations={", ""]
grouped = collections.defaultdict(list)
for l in urban:
    grouped[(urban[l]['path'][0], urban[l]['path'][2])].append(l)
for key in sorted(grouped):
    cont, region = key
    ls = sorted(grouped[key], key=lambda l: (rank[l] != "megalopolis", rank[l] != "city", l))
    O.append("\t# %s / %s (%d)" % (cont.replace("_continent", "").upper(), region, len(ls)))
    for l in ls:
        O.append("\t%-28s = { rank = %-12s town_setup = %-30s } # %s" %
                 (l, rank[l], used[l], urban[l]['name']))
    O.append("")
O += ["}", "",
      "# Unique and special buildings. Every vanilla entry here carries `tag = <COUNTRY>`",
      "# (2646 of 2647), so this half is blocked until 10_countries.txt exists.",
      "building_manager = {", "}", ""]
open(os.path.join(MOD, "main_menu", "setup", "start", "07_cities_and_buildings.txt"),
     "w", encoding="utf-8", newline="\r\n").write("\n".join(O))

# ---------------------------------------------------------------- report
c = collections.Counter(rank.values())
print("urban locations: %d  (town %d, city %d, megalopolis %d)" %
      (len(urban), c['town'], c['city'], c['megalopolis']))
print("pinned to city: %s" % ", ".join("%s (%s)" % (l, used[l]) for l in PIN_CITY if l in used))
print("culture groups:  %d   setups written: %d  (%d duplicates merged)" % (len(bygrp), len(setups), merged))
print("setups by shape: %s" % dict(collections.Counter(
    ("port_" if "_port_" in s else "") + s.rsplit("_", 1)[1] for s in setups)))
sizes = sorted(len(b) for b in setups.values())
print("buildings per setup: min %d  median %d  max %d" % (sizes[0], sizes[len(sizes)//2], sizes[-1]))
gc = collections.Counter()
for extras, share, n in profile.values():
    for e in extras:
        gc[e] += 1
print("guild frequency across %d groups: %s" % (len(profile), gc.most_common()))
