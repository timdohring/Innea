# -*- coding: utf-8 -*-
"""Validate the generated country files. Must print ALL CHECKS PASS before shipping."""
import re, os, glob, collections

MOD  = r"C:\Users\timdo\OneDrive\Documents\Projects\Innea modding\EU5 Innea\wip mod folder"
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Europa Universalis V\game"
rd = lambda p: open(p, encoding='utf-8-sig', errors='replace').read()

C = rd(os.path.join(MOD, "main_menu", "setup", "start", "10_countries.txt"))
REG = "".join(rd(f) for f in glob.glob(os.path.join(MOD, "in_game", "setup", "countries", "*.txt")))
LOC = rd(os.path.join(MOD, "main_menu", "localization", "english", "innea_countries_l_english.yml"))

ok = True
def chk(label, cond, extra=""):
    global ok
    print("%-58s %s %s" % (label, "PASS" if cond else "FAIL", extra))
    ok &= bool(cond)

# ---- parse the country blocks
blocks = re.findall(r'^\t\t([A-Z][A-Z0-9]{2}) = \{ #(.*?)\n(.*?)^\t\t\}', C, re.S | re.M)
tags = [b[0] for b in blocks]
chk("country blocks parsed", len(tags) == 863, "%d" % len(tags))
chk("no duplicate tags", len(tags) == len(set(tags)),
    [t for t, n in collections.Counter(tags).items() if n > 1][:4])

# ---- tag registry
reg_tags = set(re.findall(r'^([A-Z][A-Z0-9]{2}) = \{', REG, re.M))
chk("every tag has a registry entry", not (set(tags) - reg_tags), sorted(set(tags) - reg_tags)[:4])
chk("no orphan registry entries", not (reg_tags - set(tags)), sorted(reg_tags - set(tags))[:4])

# ---- collision with vanilla
van = set(re.findall(r'^\s*([A-Z][A-Z0-9]{2}) = \{',
                     rd(os.path.join(GAME, "main_menu", "setup", "start", "10_countries.txt")), re.M))
chk("no tag collides with vanilla's %d" % len(van), not (set(tags) & van), sorted(set(tags) & van)[:6])

# ---- locations
named = set(re.findall(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*[0-9a-fA-F]{6}\s*$',
                       rd(os.path.join(MOD, "in_game", "map_data", "named_locations", "00_default.txt")), re.M))
dm = rd(os.path.join(MOD, "in_game", "map_data", "default.map"))
nonland = set()
for key in ("sea_zones", "lakes", "impassable_mountains"):
    for m in re.finditer(key + r'\s*=\s*\{([^}]*)\}', dm):
        nonland |= set(m.group(1).split())

owned = collections.defaultdict(list)
allrefs, caps = set(), {}
for tag, note, body in blocks:
    m = re.search(r'own_control_core = \{(.*?)\n\t\t\t\}', body, re.S)
    locs = m.group(1).split() if m else []
    for l in locs:
        owned[l].append(tag)
    allrefs |= set(locs)
    m = re.search(r'our_cores_conquered_by_others = \{(.*?)\n\t\t\t\}', body, re.S)
    if m:
        allrefs |= set(m.group(1).split())
    c = re.search(r'capital = (\S+)', body)
    if c:
        caps[tag] = c.group(1)
        allrefs.add(c.group(1))

chk("all %d referenced locations exist" % len(allrefs), not (allrefs - named), sorted(allrefs - named)[:4])
chk("no referenced location is sea/lake/wasteland", not (allrefs & nonland), sorted(allrefs & nonland)[:4])
dbl = {l: t for l, t in owned.items() if len(t) > 1}
chk("no location owned by two countries", not dbl, list(dbl.items())[:3])
chk("every country has a capital", len(caps) == len(tags), "%d/%d" % (len(caps), len(tags)))
badcap = [t for t, c in caps.items() if t not in [b[0] for b in blocks] or c not in
          [l for l, ts in owned.items() if t in ts]]
chk("every capital is inside its own territory", not badcap, badcap[:4])

# ---- includes
tpl = {os.path.basename(f)[:-4] for f in glob.glob(os.path.join(MOD, "main_menu", "setup", "templates", "*.txt"))}
inc = set(re.findall(r'include = "([a-z_0-9]+)"', C))
chk("every include resolves to a template", not (inc - tpl), sorted(inc - tpl)[:4])
chk("no unused template", not (tpl - inc), sorted(tpl - inc)[:4])

# ---- culture / religion resolve
cults = set()
for f in glob.glob(os.path.join(MOD, "in_game", "common", "cultures", "*.txt")):
    cults |= set(re.findall(r'^([a-z_0-9]+)\s*=\s*\{', rd(f), re.M))
rels = set()
for f in glob.glob(os.path.join(MOD, "in_game", "common", "religions", "*.txt")):
    rels |= set(re.findall(r'^([a-z_0-9]+)\s*=\s*\{', rd(f), re.M))
uc = set(re.findall(r'culture_definition\s*=\s*(\S+)', REG))
ur = set(re.findall(r'religion_definition\s*=\s*(\S+)', REG))
chk("all %d culture_definitions resolve" % len(uc), not (uc - cults), sorted(uc - cults)[:4])
chk("all %d religion_definitions resolve" % len(ur), not (ur - rels), sorted(ur - rels)[:4])

# ---- government / rank values are real
govt = set(re.findall(r'^([a-z_]+) = \{', rd(os.path.join(GAME, "in_game", "common", "government_types", "00_default.txt")), re.M))
ranks = set(re.findall(r'^([a-z_]+) = \{', rd(os.path.join(GAME, "in_game", "common", "country_ranks", "00_default.txt")), re.M))
ug = set(re.findall(r'^\ttype = (\S+)', "".join(rd(f) for f in glob.glob(os.path.join(MOD, "main_menu", "setup", "templates", "innea_*.txt"))), re.M))
ur2 = set(re.findall(r'country_rank = (\S+)', C))
chk("all government types are real", not (ug - govt), sorted(ug - govt)[:4])
chk("all country_ranks are real", not (ur2 - ranks), sorted(ur2 - ranks)[:4])

# ---- localisation
lt = set(re.findall(r'^ ([A-Z][A-Z0-9]{2}): ', LOC, re.M))
la = set(re.findall(r'^ ([A-Z][A-Z0-9]{2})_ADJ: ', LOC, re.M))
chk("every tag has a localised name", not (set(tags) - lt), sorted(set(tags) - lt)[:4])
chk("every tag has an adjective", not (set(tags) - la), sorted(set(tags) - la)[:4])

# ---- file shape
chk("current_age is present", "current_age = " in C)
chk("countries block is doubled", re.search(r'countries = \{\s*\n\tcountries = \{', C) is not None)
for lbl, t in (("10_countries", C), ("registry", REG)):
    chk("%s braces balanced" % lbl, t.count("{") == t.count("}"), "%d/%d" % (t.count("{"), t.count("}")))

print()
print("owned locations: %d | countries: %d | avg %.1f" %
      (len(owned), len(tags), len(owned) / max(1, len(tags))))
print("RESULT:", "ALL CHECKS PASS" if ok else "FAILURES ABOVE")
