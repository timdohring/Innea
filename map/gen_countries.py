# -*- coding: utf-8 -*-
"""Port the Innea countries from the EU4 mod into EU5.

Writes four things, all additive - nothing overrides a vanilla file except
10_countries.txt, which is already an empty override and cannot be additive
(vanilla's 2337 countries all sit on Earth locations that do not exist here):

  in_game/setup/countries/01_innea_<continent>.txt   the tag registry
  main_menu/setup/templates/innea_*.txt              the include templates
  main_menu/setup/start/10_countries.txt             the start blocks
  main_menu/localization/english/innea_countries_l_english.yml

Source of truth is the EU4 mod's history/, bridged id -> RGB -> EU5 location name.
The sheet's Owner column agrees with it on all 754 shared rows, so there is no
conflict to resolve (unlike religion and culture - see TODO.md section 4).
"""
import csv, io, re, os, glob, collections

MOD  = r"C:\Users\timdo\OneDrive\Documents\Projects\Innea modding\EU5 Innea\wip mod folder"
MAPW = r"C:\Users\timdo\OneDrive\Documents\Projects\Innea modding\map"
EU4  = r"C:\Users\timdo\OneDrive\Documents\Projects\Innea modding\Version 1.3 (1.33)\2226968141"
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Europa Universalis V\game"
rd = lambda p: open(p, encoding='utf-8-sig', errors='replace').read()

CURRENT_AGE = "age_1_traditions"

# EU4 government -> EU5 type. EU5 has exactly 5 (in_game/common/government_types/00_default.txt);
# EU4's 4 "native" countries have no EU5 counterpart and fold into tribe.
GOV = {"monarchy": "monarchy", "republic": "republic", "theocracy": "theocracy",
       "tribal": "tribe", "native": "tribe"}
# EU4 ranks run 1-6, EU5 has exactly 4 (in_game/common/country_ranks/00_default.txt).
RANK = {1: "rank_county", 2: "rank_duchy", 3: "rank_kingdom",
        4: "rank_kingdom", 5: "rank_empire", 6: "rank_empire"}
# Cultures collided with vanilla on import and were prefixed - see TODO.md section 3.
CULTURE_PREFIXED = {"pamiri", "uru"}
# Tags to never generate: Windows reserved device names. The EU4 mod's own country_tags
# file warns about these, and there is no reason to risk them.
RESERVED = {"CON", "PRN", "NUL", "AUX", "COM", "LPT", "AND", "NOT", "VAL",
            "RGB", "ADD", "ADM", "DIP", "MIL", "INF", "CAV", "ART"}

# ---------------------------------------------------------------- the id bridge
id2hex = {}
for row in csv.reader(io.StringIO(open(os.path.join(MAPW, "location_def.csv"), encoding='latin-1').read()), delimiter=';'):
    if len(row) >= 4 and row[0].strip().isdigit():
        id2hex[int(row[0])] = "%02x%02x%02x" % (int(row[1]), int(row[2]), int(row[3]))
hex2name = {m.group(2).lower(): m.group(1) for m in re.finditer(
    r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([0-9a-fA-F]{6})\s*$',
    rd(os.path.join(MOD, "in_game", "map_data", "named_locations", "00_default.txt")), re.M)}
id2loc = {i: hex2name[h] for i, h in id2hex.items() if h in hex2name}

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

# water and wasteland, so an owned location can be checked for being real land
dm = rd(os.path.join(MOD, "in_game", "map_data", "default.map"))
NONLAND = set()
for key in ("sea_zones", "lakes", "impassable_mountains"):
    for m in re.finditer(key + r'\s*=\s*\{([^}]*)\}', dm):
        NONLAND |= set(m.group(1).split())
ports = set()
for line in rd(os.path.join(MOD, "in_game", "map_data", "ports.csv")).splitlines():
    line = line.strip()
    if line and not line.startswith('#') and ';' in line:
        ports.add(line.split(';')[0].strip())

# ---------------------------------------------------------------- EU4 source data
tagfile = ""
for f in glob.glob(os.path.join(EU4, "common", "country_tags", "*.txt")):
    tagfile += rd(f) + "\n"
tag2name = dict(re.findall(r'^\s*([A-Z][A-Z0-9]{2})\s*=\s*"countries/([^"]+)\.txt"', tagfile, re.M))

color = {}
for tag, nm in tag2name.items():
    p = os.path.join(EU4, "common", "countries", nm + ".txt")
    if os.path.exists(p):
        m = re.search(r'^\s*color\s*=\s*\{\s*(\d+)\s+(\d+)\s+(\d+)\s*\}', rd(p), re.M)
        if m:
            color[tag] = tuple(int(x) for x in m.groups())

hist = {}
for f in glob.glob(os.path.join(EU4, "history", "countries", "*.txt")):
    # 64 of the 931 files spell the tag prefix in mixed case ("Alf - Alfmark.txt")
    tag = os.path.basename(f)[:3].upper()
    if not re.match(r'^[A-Z][A-Z0-9]{2}$', tag):
        continue
    t = rd(f)
    get = lambda k: (re.search(r'^\s*%s\s*=\s*(\S+)' % k, t, re.M) or [None, None])[1]
    hist[tag] = dict(gov=get("government"), rank=get("government_rank"),
                     capital=get("capital"), religion=get("religion"),
                     culture=get("primary_culture"))

owner, cores = {}, collections.defaultdict(set)
for f in glob.glob(os.path.join(EU4, "history", "provinces", "*.txt")):
    m = re.match(r'(\d+)', os.path.basename(f))
    if not m:
        continue
    pid = int(m.group(1)); t = rd(f)
    o = re.search(r'^\s*owner\s*=\s*([A-Z][A-Z0-9]{2})', t, re.M)
    if o:
        owner[pid] = o.group(1)
    for c in re.findall(r'^\s*add_core\s*=\s*([A-Z][A-Z0-9]{2})', t, re.M):
        cores[c].add(pid)

# ---------------------------------------------------------------- tag remap
vanilla_tags = set(re.findall(r'^\s*([A-Z][A-Z0-9]{2}) = \{',
                              rd(os.path.join(GAME, "main_menu", "setup", "start", "10_countries.txt")), re.M))
innea_tags = set(tag2name)
collide = sorted(innea_tags & vanilla_tags)
taken = set(vanilla_tags) | (innea_tags - set(collide)) | RESERVED
ALPHANUM = [chr(c) for c in range(65, 91)] + [str(d) for d in range(10)]

remap = {}
for tag in collide:
    cand = None
    for pos in (2, 1):                       # vary 3rd char, then 2nd - keep it recognisable
        for ch in ALPHANUM:
            t = tag[:pos] + ch + tag[pos+1:]
            if t not in taken:
                cand = t; break
        if cand:
            break
    if not cand:                             # exhausted: fall back to a scan
        for a in ALPHANUM[:26]:
            for b in ALPHANUM:
                for c in ALPHANUM:
                    t = a + b + c
                    if t not in taken:
                        cand = t; break
                if cand: break
            if cand: break
    assert cand, "no free tag for %s" % tag
    remap[tag] = cand
    taken.add(cand)

T = lambda tag: remap.get(tag, tag)          # EU4 tag -> EU5 tag

# ---------------------------------------------------------------- assemble countries
countries = {}
skipped = collections.Counter()
for tag in sorted(innea_tags):
    h = hist.get(tag)
    if not h:
        skipped["no history file"] += 1; continue
    own = sorted({id2loc[p] for p, o in owner.items() if o == tag and p in id2loc})
    own = [l for l in own if l not in NONLAND and l in path]
    if not own:
        skipped["holds no land"] += 1; continue
    cap = h["capital"]
    cap = id2loc.get(int(cap)) if cap and cap.isdigit() else None
    if cap not in own:                       # capital must be inside own territory
        cap = own[0] if not cap else (cap if cap in own else own[0])
    foreign = sorted({id2loc[p] for p in cores.get(tag, ()) if p in id2loc} - set(own))
    foreign = [l for l in foreign if l not in NONLAND and l in path]
    cul = h["culture"]
    if cul in CULTURE_PREFIXED:
        cul = "innea_%s_culture" % cul
    elif cul:
        cul = "%s_culture" % cul
    try:
        rk = RANK[int(h["rank"] or 1)]
    except (ValueError, KeyError):
        rk = "rank_county"
    gov = GOV.get(h["gov"], "monarchy")
    coastal = any(l in ports for l in own)
    countries[T(tag)] = dict(
        eu4=tag, own=own, foreign=foreign, capital=cap, rank=rk, gov=gov,
        culture=cul, religion=h["religion"], color=color.get(tag, (128, 128, 128)),
        continent=path[cap][0], coastal=coastal, name=tag2name.get(tag, tag))

# ---------------------------------------------------------------- templates
os.makedirs(os.path.join(MOD, "main_menu", "setup", "templates"), exist_ok=True)
SLIDERS = {
    "monarchy": [40, -30, -50, -40, -10, -10, 10, 0, -20, 0, 70, 20, -20],
    "republic": [25, 30, 20, 40, 10, -40, -20, -20, 40, 60, -80, -40, -60],
    "theocracy": [50, -40, -90, -50, -10, -10, 50, -20, 40, -20, 70, 30, 20],
    "tribe": [80, -80, -50, -60, 50, 50, 100, -75, 50, -80, 100, 60, 60],
}
SLIDER_NAMES = ["centralization_vs_decentralization", "traditionalist_vs_innovative",
                "spiritualist_vs_humanist", "aristocracy_vs_plutocracy",
                "serfdom_vs_free_subjects", "mercantilism_vs_free_trade",
                "belligerent_vs_conciliatory", "quality_vs_quantity",
                "offensive_vs_defensive", "land_vs_naval",
                "capital_economy_vs_traditional_economy", "individualism_vs_communalism",
                "outward_vs_inward"]
HEIR = {"monarchy": "cognatic_primogeniture", "republic": "oligarchic_elective",
        "theocracy": "theocratic_elective", "tribe": "tribal_oldest_male"}
PARLIAMENT = {"monarchy": "estate_parliament", "republic": "estate_parliament",
              "theocracy": "estate_parliament", "tribe": "assembly"}
TECH = {"monarchy": 3, "republic": 3, "theocracy": 3, "tribe": 1}
PRIVILEGE = {
    "monarchy": ["#nobles", "auxilium_et_consilium", "nobles_land_rights", "noble_marriage_rights",
                 "noble_fortification_licenses", "", "#clergy", "clergy_literacy_rights",
                 "clergy_enforced_unity", "", "#burghers", "market_fairs", "formal_guilds",
                 "building_roads_rights", "", "#commoners", "allow_hunting", "communal_lands"],
    "republic": ["#nobles", "elaborate_court_ceremonies", "", "#burghers", "market_fairs",
                 "formal_guilds", "building_roads_rights", "", "#commoners", "allow_hunting",
                 "communal_lands"],
    "theocracy": ["#nobles", "nobles_land_rights", "noble_fortification_licenses", "", "#clergy",
                  "clergy_literacy_rights", "clergy_enforced_unity", "clergy_strengthen_faith",
                  "clerical_advisory_council", "", "#burghers", "market_fairs", "formal_guilds",
                  "", "#commoners", "allow_hunting", "no_labor_sunday"],
    "tribe": ["tribes_tribal_levies", "tribes_allow_gatherings"],
}
# maritime_law and piracy_law are the only keys vanilla's _no_coast variants drop.
LAWS = {
    "monarchy": [("feudal_de_jure_law", "by_tradition"), ("medieval_levy_law", "peasant_levies"),
                 ("royal_court_customs_law", "aristocratic_court_policy"),
                 ("censorship", "limited_censorship"),
                 ("education_masses_law", "basic_religious_education"),
                 ("administrative_system", "feudal_administration"),
                 ("cultural_traditions_law", "martial_society"),
                 ("marriage_law", "monogamous_marriage"), ("heir_religion_law", "heir_same_religion"),
                 ("legal_code_law", "civil_law_policy"), ("maritime_law", "protect_trade_routes"),
                 ("piracy_law", "anti_piracy_policy"),
                 ("distribution_of_power_law", "dop_traditional_distribution_of_power"),
                 ("immigration_law", "open_borders_law"), ("mining_law", "nobles_mining_law"),
                 ("coin_laws", "gold_and_silver_coins")],
    "republic": [("censorship", "limited_censorship"),
                 ("republican_foundation_law", "republicanism_policy"),
                 ("education_masses_law", "basic_religious_education"),
                 ("administrative_system", "central_councils"),
                 ("cultural_traditions_law", "civil_society"),
                 ("marriage_law", "monogamous_marriage"), ("heir_religion_law", "heir_same_religion"),
                 ("legal_code_law", "civil_law_policy"), ("maritime_law", "protect_trade_routes"),
                 ("piracy_law", "anti_piracy_policy"),
                 ("distribution_of_power_law", "dop_traditional_distribution_of_power"),
                 ("immigration_law", "open_borders_law"), ("mining_law", "burghers_mining_law"),
                 ("coin_laws", "gold_and_silver_coins")],
    "theocracy": [("censorship", "strict_censorship"), ("theocratic_leadership", "clerical_state"),
                  ("holy_mission_law", "internal_mission_policy"),
                  ("education_masses_law", "theocratic_education"),
                  ("administrative_system", "central_councils"),
                  ("cultural_traditions_law", "civil_society"), ("marriage_law", "celibacy"),
                  ("heir_religion_law", "heir_special_succession"),
                  ("legal_code_law", "civil_law_policy"), ("maritime_law", "protect_trade_routes"),
                  ("piracy_law", "anti_piracy_policy"),
                  ("distribution_of_power_law", "dop_traditional_distribution_of_power"),
                  ("immigration_law", "open_borders_law"), ("mining_law", "nobles_mining_law"),
                  ("coin_laws", "gold_and_silver_coins")],
    "tribe": [("marriage_law", "polygyny"), ("heir_religion_law", "heir_same_religion")],
}
SEA_LAWS = {"maritime_law", "piracy_law"}


def government_template(gov, landlocked):
    L = ["# Innea %s%s. Generated by map/gen_countries.py - do not hand-edit." %
         (gov, ", landlocked" if landlocked else ""),
         "starting_technology_level = %d" % TECH[gov], "", "government = {",
         "\ttype = %s" % gov, "\their_selection = %s" % HEIR[gov], "",
         "\t#Societal Values"]
    for n, v in zip(SLIDER_NAMES, SLIDERS[gov]):
        L.append("\t%s = %d" % (n, v))
    L += ["\tparliament = {", "\t\tparliament_type = %s" % PARLIAMENT[gov], "\t}", "",
          "\t#Estate Privileges", "\tprivilege = {"]
    for p in PRIVILEGE[gov]:
        L.append("\t\t%s" % p if p else "")
    L += ["\t}", "", "\tlaws = {"]
    for k, v in LAWS[gov]:
        if landlocked and k in SEA_LAWS:
            continue
        L.append("\t\t%s = %s" % (k, v))
    L += ["\t}", "}", ""]
    return "\n".join(L)


templates = {}
for gov in ("monarchy", "republic", "theocracy"):
    templates["innea_%s" % gov] = government_template(gov, False)
    templates["innea_%s_landlocked" % gov] = government_template(gov, True)
templates["innea_tribe"] = government_template("tribe", False)   # tribe has no sea laws to drop

regions_by_continent = collections.defaultdict(set)
for loc, p in path.items():
    if len(p) >= 3:
        regions_by_continent[p[0]].add(p[2])
# Only continents that actually hold a country. Menea and Vulthark were never authored in
# the EU4 mod (TODO.md section 9), so they own nothing and need no map-knowledge template.
inhabited = {c["continent"] for c in countries.values()}
for cont, regs in regions_by_continent.items():
    if cont not in inhabited:
        continue
    short = cont.replace("_continent", "")
    L = ["# Innea starting map knowledge: %s. Generated by map/gen_countries.py." % short,
         "discovered_regions = {"]
    for r in sorted(regs):
        L.append("\t%s" % r)
    L += ["}", ""]
    templates["innea_expl_%s" % short] = "\n".join(L)

for name, body in templates.items():
    open(os.path.join(MOD, "main_menu", "setup", "templates", "%s.txt" % name),
         "w", encoding="utf-8", newline="\r\n").write(body)

# ---------------------------------------------------------------- tag registry
os.makedirs(os.path.join(MOD, "in_game", "setup", "countries"), exist_ok=True)
shard = collections.defaultdict(list)
for tag, c in countries.items():
    shard[c["continent"].replace("_continent", "")].append(tag)
for cont, tags in shard.items():
    L = ["# Innea country tag registry: %s." % cont,
         "# Additive - adds new tags alongside vanilla's, overrides nothing.",
         "# Generated by map/gen_countries.py - do not hand-edit.", ""]
    for tag in sorted(tags):
        c = countries[tag]
        r, g_, b = c["color"]
        dark = tuple(max(0, int(v * 0.55)) for v in c["color"])
        L.append("%s = {" % tag)
        L.append("\tcolor  = rgb { %d %d %d }" % (r, g_, b))
        L.append("\tcolor2 = rgb { %d %d %d }" % dark)
        if c["culture"]:
            L.append("\tculture_definition  = %s" % c["culture"])
        if c["religion"]:
            L.append("\treligion_definition = %s" % c["religion"])
        L.append("\tdifficulty = 2")
        L.append("}")
        L.append("")
    open(os.path.join(MOD, "in_game", "setup", "countries", "01_innea_%s.txt" % cont),
         "w", encoding="utf-8", newline="\r\n").write("\n".join(L))

# ---------------------------------------------------------------- 10_countries.txt
def wrap(locs, indent="\t\t\t"):
    out, line = [], []
    for l in locs:
        line.append(l)
        if len(line) == 5:
            out.append(indent + " ".join(line)); line = []
    if line:
        out.append(indent + " ".join(line))
    return out


O = ["# Innea countries, ported from the EU4 mod's history/.",
     "# %d countries; owner and cores come from history/provinces, government/rank/capital" % len(countries),
     "# from history/countries, bridged EU4 province id -> RGB -> EU5 location name.",
     "# Rulers are `ruler = random`: the EU4 mod only defines a monarch for 98 of 931 countries.",
     "# Generated by map/gen_countries.py - do not hand-edit.", "",
     "current_age = %s" % CURRENT_AGE, "",
     "countries = {",
     "\tcountries = {", ""]
grouped = collections.defaultdict(list)
for tag, c in countries.items():
    grouped[(c["continent"], path[c["capital"]][2])].append(tag)
for key in sorted(grouped):
    cont, region = key
    O.append("\t\t# ===== %s / %s (%d) =====" % (cont.replace("_continent", "").upper(), region, len(grouped[key])))
    for tag in sorted(grouped[key], key=lambda t: (-len(countries[t]["own"]), t)):
        c = countries[tag]
        note = c["name"] if c["eu4"] == tag else "%s, was %s" % (c["name"], c["eu4"])
        O.append("\t\t%s = { # %s" % (tag, note))
        O.append("\t\t\town_control_core = {")
        O += wrap(c["own"], "\t\t\t\t")
        O.append("\t\t\t}")
        if c["foreign"]:
            O.append("\t\t\tour_cores_conquered_by_others = {")
            O += wrap(c["foreign"], "\t\t\t\t")
            O.append("\t\t\t}")
        O.append('\t\t\tinclude = "innea_expl_%s"' % c["continent"].replace("_continent", ""))
        suffix = "" if (c["coastal"] or c["gov"] == "tribe") else "_landlocked"
        O.append('\t\t\tinclude = "innea_%s%s"' % (c["gov"], suffix))
        O.append("\t\t\tcountry_rank = %s" % c["rank"])
        O.append("\t\t\tgovernment = { ruler = random }")
        O.append("\t\t\tcapital = %s" % c["capital"])
        O.append("\t\t}")
    O.append("")
O += ["\t}", "}", ""]
open(os.path.join(MOD, "main_menu", "setup", "start", "10_countries.txt"),
     "w", encoding="utf-8", newline="\r\n").write("\n".join(O))

# ---------------------------------------------------------------- localisation
os.makedirs(os.path.join(MOD, "main_menu", "localization", "english"), exist_ok=True)
src = os.path.join(EU4, "localisation", "innea_countries_l_english.yml")
loc = {}
for m in re.finditer(r'^\s*([A-Z][A-Z0-9]{2})(_ADJ)?:\d*\s+"([^"]*)"', rd(src), re.M):
    loc[(m.group(1), bool(m.group(2)))] = m.group(3)
L = ["l_english:"]
missing = []
for tag in sorted(countries):
    c = countries[tag]
    nm = loc.get((c["eu4"], False))
    adj = loc.get((c["eu4"], True))
    if not nm:
        nm = c["name"]; missing.append(tag)
    L.append(' %s: "%s"' % (tag, nm))
    L.append(' %s_ADJ: "%s"' % (tag, adj or nm))
open(os.path.join(MOD, "main_menu", "localization", "english", "innea_countries_l_english.yml"),
     "w", encoding="utf-8-sig", newline="\r\n").write("\n".join(L) + "\n")

# ---------------------------------------------------------------- remap audit trail
# the repo's own map/ dir, not the external MAPW workspace - this is checked in
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tag_remap.csv"),
          "w", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["eu4_tag", "eu5_tag", "country", "reason"])
    for old in sorted(remap):
        w.writerow([old, remap[old], tag2name.get(old, ""), "collides with a vanilla EU5 tag"])

# ---------------------------------------------------------------- report
print("countries written: %d   (skipped: %s)" % (len(countries), dict(skipped)))
print("tags remapped: %d of %d Innea tags collided with vanilla's %d" %
      (len(remap), len(innea_tags), len(vanilla_tags)))
print("templates: %d   registry shards: %d   localisation entries: %d" %
      (len(templates), len(shard), 2 * len(countries)))
print("locations owned: %d   foreign cores: %d" %
      (sum(len(c["own"]) for c in countries.values()),
       sum(len(c["foreign"]) for c in countries.values())))
print("by rank:", dict(collections.Counter(c["rank"] for c in countries.values())))
print("by government:", dict(collections.Counter(c["gov"] for c in countries.values())))
print("landlocked (no port):", sum(1 for c in countries.values() if not c["coastal"]))
if missing:
    print("NO LOCALISATION for %d tags, fell back to the file name: %s" % (len(missing), missing[:8]))
