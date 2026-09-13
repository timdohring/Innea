# -*- coding: utf-8 -*-
"""Generate Innea's 18 custom trade goods, their colours, localisation, and place them on the map.

THE PROBLEM
-----------
The map port mapped the Information sheet's RGO column onto vanilla EU5 goods. 19 Innean goods
had no counterpart and were ALL flattened to `wheat` - 580 locations. Dragonshore, Firehold and
Upper/Lower Dragon Vale grow wheat. The sheet's RGO column is the source of truth, so every one
is recoverable via the usual EU4 id -> RGB -> location bridge.

Three sheet RGOs were mapped correctly and are left alone: sturdy_grains->millet,
potatoes->potato, gold->goods_gold. One is folded: wayda_silk -> vanilla silk (EU5 models a
"fancier variant" downstream in production - its own pair is cloth/fine_cloth, both `produced` -
never as a duplicate raw material, and silk is already the input to production_fine_cloth).

NO BONUSES. EU4 gave each good a `modifier`/`province` block; EU5 goods have no modifier block at
all, only demand/price/AI tuning. Design decision: dropped. These are purely economic goods.

PRICING METHOD
--------------
NOT a blind rank-map of EU4's prices. EU5 prices every food staple at 1 regardless of rarity
(wheat, rice, fish, millet, legumes are all 1), so rank-mapping would put blackgrain near 3 and
break the food economy. Instead each good is CLASSIFIED, then priced to match EU5's own norms for
that class, using EU4's relative ordering only to break ties within a class:

    staple food      1 - 2   (vanilla: wheat 1, fish 1, livestock 1.5, beeswax 2)
    industrial       2 - 3   (vanilla: coal 2, iron 3, copper 3, lead 3)
    luxury           4 - 6   (vanilla: silk 4, gems 4, saffron 5, pepper 5, fine_cloth 6)

Run:  python map/gen_goods.py
"""
import os, re, csv, io, sys, collections

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
MOD = os.path.join(REPO, "wip mod folder")
MAPW = r"C:\Users\timdo\OneDrive\Documents\Projects\Innea modding\map"
VAN = r"C:\Program Files (x86)\Steam\steamapps\common\Europa Universalis V\game"
rd = lambda p: open(p, encoding="utf-8-sig", errors="replace").read()

# name: (method, price, food, class, colour, display name, note)
#   method: farming | forestry | gathering | hunting | mining
#   food:   None, or a food value calibrated against vanilla (rice 10, wheat 8, fish 5, fruit 4,
#           wild_game 3.5, beeswax 2.5, fur 2)
#   class:  staple | industrial | luxury  - drives the demand profile written below
GOODS = {
    # ---- staple food: cheap, broad demand across the lower pop types
    "shellfish":   ("gathering", 1,   5.0, "staple",     (214, 168, 160), "Shellfish",
                    "coastal forage; vanilla fish is the model"),
    "blackgrain":  ("farming",   1,   7.0, "staple",     ( 58,  46,  38), "Blackgrain",
                    "a dark staple grain; priced as wheat"),
    "fungi":       ("gathering", 2,   3.5, "staple",     (130,  74, 156), "Fungi",
                    "matches terrain_fungal purple"),
    "riverweed":   ("gathering", 1,   2.5, "staple",     ( 92, 138,  86), "Riverweed",
                    "river forage"),
    # ---- industrial: mined or worked, feed buildings rather than pops
    "obsidian":    ("mining",    2,  None, "industrial", ( 32,  30,  36), "Obsidian",
                    "volcanic glass; cheapest of the minerals in EU4 too"),
    "blue_copper": ("mining",    3,  None, "industrial", ( 62, 146, 158), "Blue Copper",
                    "a DIFFERENT metal to copper - intended for building inputs"),
    "fireiron":    ("mining",    4,  None, "industrial", (198,  84,  44), "Fireiron",
                    "dearer than iron (3); a worked/magical metal"),
    "crystal":     ("mining",    4,  None, "industrial", (168, 222, 232), "Crystals",
                    "priced with gems (4)"),
    "whales":      ("hunting",   3,   3.0, "industrial", ( 58,  78, 104), "Whales",
                    "oil and meat; part food, part industrial"),
    "chofo":       ("farming",   3,  None, "industrial", (150, 140,  74), "Chofo",
                    "a worked crop; EU4 tied it to manpower recovery"),
    # ---- luxury: dear, demanded by the wealthy
    "jade":        ("mining",    4,  None, "luxury",     ( 84, 168, 118), "Jade",
                    "priced with gems"),
    "red_sugar":   ("farming",   4,  None, "luxury",     (156,  40,  46), "Red Sugar",
                    "dearer than vanilla sugar (3) - deliberately not sugar"),
    "druh":        ("gathering", 4,  None, "luxury",     (140, 118, 150), "Druh",
                    "incense-like; EU4 tied it to religious unity"),
    "springwater": ("gathering", 4,  None, "luxury",     (176, 214, 234), "Springwater",
                    "a luxury drink; EU4 tied it to ruler lifespan"),
    "ancient_artifacts": ("gathering", 5, None, "luxury", (198, 160,  76), "Ancient Artifacts",
                    "excavated, not produced; finite in flavour if not in rules"),
    "dragon_hide": ("hunting",   5,  None, "luxury",     (112,  38,  34), "Dragon Hide",
                    "the rarest hunt; priced with saffron/pepper"),
    "khafri_peppers": ("farming", 5, None, "luxury",     (186,  72,  38), "Khafri Peppers",
                    "a DIFFERENT spice to pepper, not a variant"),
    "yv":          ("mining",    6,  None, "luxury",     (126,  74, 176), "Yv",
                    "dearest in EU4 (7); priced with fine_cloth (6)"),
}
FOLD = {"wayda_silk": "silk"}          # sheet RGO -> vanilla good, no new definition
LEAVE = {"sturdy_grains", "potatoes", "gold"}   # already mapped correctly by the map port

# Optional extra blocks per good, written verbatim into its definition. This is where regional
# flavour goes - the demand modifiers, winter/topography tuning, AI weighting.
#
# The *_demand_modifier keys take a LITERAL key from map_data/definitions.txt, so Innea's are
# `orea_continent`, `orea_subcontinent`, `orea_region` - not bare `orea`. (Vanilla has both
# shapes: `europe`, but also `atlantic_ocean_continent`.) A value of 2 means "demand here is
# doubled", exactly as vanilla does `continent_demand_modifier = { europe = 2 }` on wheat.
#
# Valid modifier scopes: continent_demand_modifier, sub_continent_demand_modifier,
# region_demand_modifier, climate_demand_modifier, topography_demand_modifier,
# winter_demand_modifier, disease_demand_modifier.
#
# Which goods get one, and at which level, was measured from where they actually sit on the map:
# the TIGHTEST geography holding >=90% of a good's locations gets x2, else the tightest holding
# >=70% gets x1.5. Ten of the eighteen are too scattered to qualify and deliberately have none
# (crystal 69%, ancient_artifacts 66%, fireiron 64%, blackgrain 63%, whales 61%, jade 59%, plus
# shellfish, obsidian, blue_copper and springwater - all below 70% even at continent level).
# Vanilla's magnitudes for comparison: wine x2 by region, liquor x2, amber x1.5, pepper x1.5.
#
# REGION IS THE TIGHTEST SCOPE EU5 HAS - there is no area or province demand modifier. The full
# set is continent / sub_continent / region, plus climate, topography, winter, disease and
# market_unavailability. A good confined to a single area can only be pinned to its region.
#
# Several regions can be listed in one block, as vanilla does for wine
# (iberia_region = 2 italy_region = 2 balkan_region = 2) and liquor (six keys).
EXTRA = {
    # --- single place, x2
    # riverweed is 100% in ONE AREA (rivwoudn_basin_area) - region is as tight as EU5 allows.
    "riverweed":      "\tregion_demand_modifier = {\n\t\theartlands_region = 2\n\t}\n",        # 100%
    "khafri_peppers": "\tregion_demand_modifier = {\n\t\tmajukistan_region = 2\n\t}\n",        # 100%
    "druh":           "\tregion_demand_modifier = {\n\t\tavatrea_region = 2\n\t}\n",           # 90%
    # chofo is 100% Orean. orea_subcontinent is equally 100% (Orea has one subcontinent), so
    # continent is used as the clearer of the two.
    "chofo":          "\tcontinent_demand_modifier = {\n\t\torea_continent = 2\n\t}\n",        # 100%

    # --- spread across several regions: name the regions rather than widen the scope
    # fungi: top 3 regions hold 75% (sun_coast 35, midlands 28, avatrea 12)
    "fungi":          ("\tregion_demand_modifier = {\n"
                       "\t\tsun_coast_region = 2\n"
                       "\t\tmidlands_region = 2\n"
                       "\t\tavatrea_region = 2\n\t}\n"),
    # dragon_hide is the most diffuse of the eight - 14 areas across 8 regions. These 5 hold 83%,
    # so a gentler x1.5 rather than x2.
    "dragon_hide":    ("\tregion_demand_modifier = {\n"
                       "\t\twaking_earth_region = 1.5\n"
                       "\t\taltvarik_mountains_region = 1.5\n"
                       "\t\turen_nai_region = 1.5\n"
                       "\t\tsun_coast_region = 1.5\n"
                       "\t\tanhya_region = 1.5\n\t}\n"),

    # --- continent, x1.5
    "red_sugar":      "\tcontinent_demand_modifier = {\n\t\tastrea_continent = 1.5\n\t}\n",    # 89% - just under the x2 line
    # yv: deliberately none. 77% at subcontinent but only 46% in its best region, so any region
    # list would be arbitrary and the subcontinent scope was judged too broad.
}

# Goods pops do NOT buy for their own needs - they are building/army inputs.
# Vanilla omits exactly this class from pop_demand: iron, copper, tin, lead, steel, stone, clay,
# cotton, silk, wool, tar, sand, alum, dyes, fiber_crops, saltpeter, cannons, naval_supplies,
# slaves_goods (19 of its 74). Ours follow the same rule. Note vanilla DOES list gems and marble,
# so crystal and jade belong in the demand list.
NOT_POP_DEMANDED = {
    "obsidian",     # priced 2, like unlisted clay/stone
    "blue_copper",  # a copper analogue, and intended as a building input
    "fireiron",     # an iron/steel analogue
}

# Demand profiles by class, modelled on vanilla goods of the same character.
DEMAND = {
    "staple": ("\tdemand_add = {\n\t\tall = 0.001\n\t\tpeasants = 0.002\n"
               "\t\tlaborers = 0.002\n\t\tsoldiers = 0.002\n\t}\n"
               "\tdemand_multiply = {\n\t\ttribesmen = 0\n\t}\n"),
    "industrial": ("\tdemand_add = {\n\t\tall = 0.0005\n\t\tburghers = 0.002\n\t}\n"
                   "\ttransport_cost = 1\n"),
    "luxury": ("\tdemand_add = {\n\t\tupper = 0.05\n\t}\n"
               "\tdemand_multiply = {\n\t\tnobles = 10\n\t\ttribesmen = 0\n\t\tslaves = 0\n\t}\n"
               "\twealth_impact_threshold = {\n\t\tall = 1.0\n\t}\n"),
}

# 01_innea.txt is HAND-EDITED from 2026-09-13 onward - prices, food values, transport_cost and
# ai_rgo_size_importance were tuned by hand. Regenerating would silently destroy that work, so it
# is refused unless you explicitly opt in. The other outputs (colours, localisation, pop_demands,
# location_templates) are still safe to regenerate.
PROTECT_GOODS_FILE = True

def write(path, text):
    if PROTECT_GOODS_FILE and os.path.basename(path) == "01_innea.txt":
        print("SKIPPED %s - hand-edited, protected by PROTECT_GOODS_FILE." % os.path.basename(path))
        print("        Set PROTECT_GOODS_FILE = False only if you mean to discard those edits.")
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8-sig", newline="\r\n").write(text.replace("\r\n", "\n"))

# ---------------------------------------------------------------- validate against vanilla
van_goods, van_colors = set(), set()
d = os.path.join(VAN, "in_game", "common", "goods")
for f in os.listdir(d):
    if f.endswith(".txt"):
        van_goods |= set(re.findall(r'^([a-z_0-9]+)\s*=\s*\{', rd(os.path.join(d, f)), re.M))
nc = os.path.join(VAN, "main_menu", "common", "named_colors")
for f in os.listdir(nc):
    van_colors |= set(re.findall(r'^\s*([a-z_0-9]+)\s*=\s*(?:rgb|hsv360)', rd(os.path.join(nc, f)), re.M))

problems = []
for g in GOODS:
    if g in van_goods:
        problems.append("'%s' collides with a vanilla good" % g)
    if "goods_" + g in van_colors:
        problems.append("colour token goods_%s collides with vanilla" % g)
for src, dst in FOLD.items():
    if dst not in van_goods:
        problems.append("fold target '%s' is not a vanilla good" % dst)
# every geography key named in EXTRA must exist in definitions.txt, or the modifier is dead script
_toks = re.findall(r'[A-Za-z_][A-Za-z0-9_]*|\{|\}|=',
                   rd(os.path.join(MOD, "in_game", "map_data", "definitions.txt")))
_st, _geo, _i = [], set(), 0
while _i < len(_toks):
    _x = _toks[_i]
    if _x in ("{", "=", "}"):
        if _x == "}" and _st: _st.pop()
        _i += 1; continue
    if _i + 2 < len(_toks) and _toks[_i+1] == "=" and _toks[_i+2] == "{":
        _geo.add(_x); _st.append(_x); _i += 3; continue
    _i += 1
for g, block in EXTRA.items():
    if g not in GOODS:
        problems.append("EXTRA names '%s', which is not a good" % g)
    for key in re.findall(r'^\s*([a-z_0-9]+)\s*=\s*[0-9.]+', block, re.M):
        if key not in _geo:
            problems.append("%s: geography '%s' is not in definitions.txt" % (g, key))
if problems:
    print("REFUSING TO WRITE:")
    for p in problems: print("   -", p)
    sys.exit(1)

# ---------------------------------------------------------------- 1. the goods
L = ["# Innea's custom trade goods. ADDITIVE - vanilla's 74 are untouched.",
     "#",
     "# Generated by map/gen_goods.py. Safe to hand-tune: re-running overwrites, so put any",
     "# lasting change in the generator's GOODS table rather than here.",
     "#",
     "# No good carries a modifier block - EU5 goods have none (only demand/price/AI tuning),",
     "# so EU4's per-good bonuses were deliberately dropped.",
     ""]
for cls in ("staple", "industrial", "luxury"):
    L.append("# ===== %s =====" % cls.upper())
    L.append("")
    for g, (method, price, food, c, rgb, disp, note) in GOODS.items():
        if c != cls: continue
        L.append("%s = {   # %s" % (g, note))
        L.append("\tmethod = %s" % method)
        L.append("\tcategory = raw_material")
        L.append("\tcolor = goods_%s" % g)
        L.append("\tdefault_market_price = %g" % price)
        if food is not None:
            L.append("\tfood = %s" % food)
        L.append(DEMAND[cls].rstrip("\n"))
        if g in EXTRA:
            L.append(EXTRA[g].rstrip("\n"))
        L.append("}")
        L.append("")
write(os.path.join(MOD, "in_game", "common", "goods", "01_innea.txt"), "\n".join(L))

# ---------------------------------------------------------------- 2. colours
C = ["# Colours for Innea's 18 custom trade goods. ADDITIVE.", "colors = {"]
for g, (_, _, _, _, rgb, disp, _) in GOODS.items():
    C.append("\tgoods_%-20s = rgb { %3d %3d %3d }\t# %s" % (g, rgb[0], rgb[1], rgb[2], disp))
C += ["}", ""]
write(os.path.join(MOD, "main_menu", "common", "named_colors", "06_innea_goods.txt"), "\n".join(C))

# ---------------------------------------------------------------- 3. localisation
Y = ["l_english:", "", "# Innea trade goods. Names come from the EU4 mod's innea_tradegoods_l_english.yml.", ""]
for g, (_, _, _, _, _, disp, _) in GOODS.items():
    Y.append(' %s: "%s"' % (g, disp))
Y.append("")
write(os.path.join(MOD, "main_menu", "localization", "english", "innea_goods_l_english.yml"), "\n".join(Y))

# ---------------------------------------------------------------- 4. put them on the map
id2hex = {}
for r in csv.reader(io.StringIO(open(os.path.join(MAPW, "location_def.csv"), encoding="latin-1").read()), delimiter=";"):
    if len(r) >= 4 and r[0].strip().isdigit():
        id2hex[int(r[0])] = "%02x%02x%02x" % (int(r[1]), int(r[2]), int(r[3]))
h2n = {m.group(2).lower(): m.group(1) for m in re.finditer(
    r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([0-9a-fA-F]{6})\s*$',
    rd(os.path.join(MOD, "in_game", "map_data", "named_locations", "00_default.txt")), re.M)}
id2loc = {i: h2n[h] for i, h in id2hex.items() if h in h2n}

sheet = {}
for r in list(csv.reader(io.StringIO(rd(os.path.join(MAPW, "sheet_columns", "sheet_gid0.csv")))))[2:]:
    if r and r[0].strip().isdigit() and len(r) > 8:
        loc = id2loc.get(int(r[0]))
        if loc and r[8].strip():
            sheet[loc] = r[8].strip()

TPL = os.path.join(MOD, "in_game", "map_data", "location_templates.txt")
tpl = rd(TPL)
changed = collections.Counter()
def fix(m):
    loc, body = m.group(1), m.group(2)
    want = sheet.get(loc)
    target = want if want in GOODS else FOLD.get(want)
    if not target:
        return m.group(0)
    cur = re.search(r'raw_material\s*=\s*(\S+)', body)
    if not cur or cur.group(1) == target:
        return m.group(0)
    changed[(cur.group(1), target)] += 1
    return m.group(0).replace("raw_material = " + cur.group(1), "raw_material = " + target, 1)
tpl_new = re.sub(r'^([a-z_0-9]+) = \{([^}]*)\}', fix, tpl, flags=re.M)
open(TPL, "w", encoding="utf-8-sig", newline="\r\n").write(tpl_new)

# ---------------------------------------------------------------- 5. pop demand override
# `pop_demand` is a SINGLE named block listing which goods pops buy for their own needs. A second
# file redefining it would most likely replace vanilla's 55 rather than merge, silently stripping
# pop demand from the whole vanilla economy - so this is a generated override of the file, built
# from vanilla's current copy. Re-run after a Paradox patch to pick up their changes.
VAN_POP = os.path.join(VAN, "in_game", "common", "goods_demand", "pop_demands.txt")
pop = rd(VAN_POP)
m = re.search(r'^(pop_demand\s*=\s*\{)(.*?)^(\})', pop, re.M | re.S)
if not m:
    sys.exit("FAIL: could not find the pop_demand block in vanilla's pop_demands.txt")
listed = set(re.findall(r'^\s*([a-z_0-9]+)\s*=\s*[0-9.]+', m.group(2), re.M))
add = [g for g in GOODS if g not in NOT_POP_DEMANDED]
dupes = [g for g in add if g in listed]
if dupes:
    sys.exit("FAIL: already in vanilla's pop_demand: %s" % dupes)
block = (m.group(2).rstrip() + "\n\n"
         "\t############################\n"
         "\t# Innea - added by map/gen_goods.py. Everything above is vanilla's, verbatim.\n"
         "\t# Omitted deliberately (building/army inputs, as vanilla omits iron/copper/stone):\n"
         "\t#   " + ", ".join(sorted(NOT_POP_DEMANDED)) + "\n"
         "\t############################\n"
         + "".join("\t%s = 1\n" % g for g in add))
write(os.path.join(MOD, "in_game", "common", "goods_demand", "pop_demands.txt"),
      pop[:m.start(2)] + block + pop[m.end(2):])

print("%s goods/01_innea.txt            %d goods"
      % ("PROTECTED (not written)" if PROTECT_GOODS_FILE else "wrote                 ", len(GOODS)))
print("wrote goods_demand/pop_demands.txt  vanilla %d + %d Innea = %d (omitted %d)"
      % (len(listed), len(add), len(listed) + len(add), len(NOT_POP_DEMANDED)))
print("wrote named_colors/06_innea_goods   %d colours" % len(GOODS))
print("wrote innea_goods_l_english.yml     %d keys" % len(GOODS))
print("\nlocation_templates.txt: %d locations re-assigned" % sum(changed.values()))
for (a, b), n in changed.most_common():
    print("   %-10s -> %-20s %4d" % (a, b, n))
