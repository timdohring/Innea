# -*- coding: utf-8 -*-
"""Generate the Innea localisation files under main_menu/localization/english/.

Everything EU5 needs a display name for, sourced from the EU4 mod wherever it already has one:

  locations   5040  <- the Information sheet's Name column, else EU4 PROV<id> via the id bridge.
                       The sheet leads because EU4's prov_names drifts by one id across part of
                       the sea zones (our black_bay, id 1328, is "Gulf of Suez" there - an
                       unedited base-EU4 leftover - while "Black Bay" sits on 1329). The two
                       agree on 4769 of 5032; the 41 that differ are listed in
                       map/loc_name_conflicts.txt for review, since EU4 is the better reading
                       in several of them (Easterly vs the sheet's "Easerly", and so on).
  religions     69  \\
  religion grps 21  /  <- EU4 innea_religion_l_english.yml, key for key (100% covered)
  cultures     466  \\
  culture grps  76   >- EU4 innea_cultures_l_english.yml, key minus the _culture/_language suffix
  languages     76  /
  continents     8  \\
  subcontinents 10   |
  regions       32   >- EU4 has NO usable source: its own area/region keys are a different
  areas        123   |  naming scheme entirely (a_vriltra_area, brythawn_superregion) with zero
  provinces   1047  /   overlap, so these are prettified from the EU5 key.
  dynasties      2  <- hand-written

Not generated, deliberately:
  * town setups - vanilla localises 0 of its own 115, they are never shown by name
  * markets - a market takes its name from its seat location (GetMarket.GetName), no key of its own

Files are written additively as innea_*.yml alongside vanilla's, never overriding one, and with
the UTF-8 BOM every Paradox localisation file needs.
"""
import os, re, csv, io, glob, collections

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
MOD = os.path.join(REPO, "wip mod folder")
MAPD = os.path.join(MOD, "in_game", "map_data")
OUT = os.path.join(MOD, "main_menu", "localization", "english")
EU4 = r"C:\Users\timdo\OneDrive\Documents\Projects\Innea modding\Version 1.3 (1.33)\2226968141"
MAPW = r"C:\Users\timdo\OneDrive\Documents\Projects\Innea modding\map"
rd = lambda p: open(p, encoding='utf-8-sig', errors='replace').read()

SMALL = {"of", "the", "and", "in", "on", "at", "by", "for", "a", "an"}

def pretty(key, *strip):
    """altvarik_mountains_region -> Altvarik Mountains"""
    for s in strip:
        if key.endswith(s):
            key = key[:-len(s)]
    words = [w for w in key.split("_") if w]
    out = []
    for i, w in enumerate(words):
        out.append(w if (w in SMALL and i) else w.capitalize())
    return " ".join(out)

# ---------------------------------------------------------------- sources
eu4 = {}
for f in sorted(glob.glob(os.path.join(EU4, "localisation", "*.yml"))):
    for m in re.finditer(r'^\s*([A-Za-z_0-9]+):\d*\s*"(.*)"\s*$', rd(f), re.M):
        eu4.setdefault(m.group(1), m.group(2))
print("EU4 localisation keys available: %d" % len(eu4))

id2hex = {}
for r in csv.reader(io.StringIO(open(os.path.join(MAPW, "location_def.csv"), encoding='latin-1').read()),
                    delimiter=';'):
    if len(r) >= 4 and r[0].strip().isdigit():
        id2hex[int(r[0])] = "%02x%02x%02x" % (int(r[1]), int(r[2]), int(r[3]))
h2n = {m.group(2).lower(): m.group(1) for m in re.finditer(
    r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([0-9a-fA-F]{6})\s*$',
    rd(os.path.join(MAPD, "named_locations", "00_default.txt")), re.M)}
loc2id = {h2n[h]: i for i, h in id2hex.items() if h in h2n}
locations = sorted(h2n.values())

sheet = {}
for r in list(csv.reader(io.StringIO(rd(os.path.join(MAPW, "sheet_columns", "sheet_gid0.csv")))))[2:]:
    if r and r[0].strip().isdigit():
        l = h2n.get(id2hex.get(int(r[0])))
        if l and r[2].strip():
            sheet[l] = r[2].strip()

def read_keys(pat):
    s = set()
    for f in glob.glob(pat):
        s |= set(re.findall(r'^([a-z_0-9]+) = \{', rd(f), re.M))
    return s

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
level = collections.defaultdict(set)
for l, p in path.items():
    for n, node in enumerate(p):
        level[n].add(node)

# ---------------------------------------------------------------- build entries
stats = collections.Counter()

def from_eu4(key, *strip):
    k = key
    for s in strip:
        if k.endswith(s):
            k = k[:-len(s)]
    if k in eu4:
        stats["EU4"] += 1
        return eu4[k]
    stats["generated"] += 1
    return pretty(key, *strip)

# locations: the sheet leads, EU4's province name fills the gaps
BAND = re.compile(r'^(anur_desert|ice_plain)_\d+$')
loc_entries, loc_src, conflicts = [], collections.Counter(), []
for l in locations:
    p = eu4.get("PROV%d" % loc2id.get(l, -1))
    sh = sheet.get(l)
    if p and sh and p != sh:
        conflicts.append((l, sh, p))
    if BAND.match(l):
        # the polar/desert split bands are one wasteland cut into strips for the engine's sake,
        # so they all carry the same name
        v = pretty(l.rsplit("_", 1)[0]); src = "band"
    elif l.startswith("unnamed_location") or sh == l:
        # no authored name anywhere - a readable placeholder beats echoing the raw key
        v = pretty(l); src = "placeholder"
    elif sh:
        v = sh; src = "sheet"
    elif p:
        v = p; src = "EU4 PROV"
    else:
        v = pretty(l); src = "placeholder"
    loc_src[src] += 1
    loc_entries.append((l, v))
print("locations: %s" % dict(loc_src))
_hdr = ["# Locations where the Information sheet and the EU4 mod disagree on the name.",
        "# The sheet's value is what was written; EU4's is shown for review.",
        "# %-24s %-28s %s" % ("location", "sheet (used)", "EU4 prov_names"), ""]
_rows = ["  %-24s %-28s %s" % c for c in sorted(conflicts)]
open(os.path.join(ROOT, "loc_name_conflicts.txt"), "w", encoding="utf-8",
     newline="\r\n").write("\n".join(_hdr + _rows) + "\n")
print("  sheet/EU4 name conflicts: %d -> map/loc_name_conflicts.txt" % len(conflicts))

religions = sorted(read_keys(MOD + "/in_game/common/religions/*.txt"))
rel_groups = sorted(read_keys(MOD + "/in_game/common/religion_groups/*.txt"))
cultures = sorted(read_keys(MOD + "/in_game/common/cultures/*.txt"))
cul_groups = sorted(os.path.basename(f)[:-4] for f in glob.glob(MOD + "/in_game/common/cultures/*.txt"))
languages = sorted(read_keys(MOD + "/in_game/common/languages/01_innea_*.txt"))
families = sorted(os.path.basename(f)[len("01_innea_"):-4]
                  for f in glob.glob(MOD + "/in_game/common/languages/01_innea_*.txt"))
dynasties = sorted(re.findall(r'^\t([a-z_0-9]+) = \{',
                              rd(os.path.join(MOD, "main_menu", "setup", "start", "04_dynasties.txt")), re.M))

def write(fname, header, entries):
    L = ["l_english:", "", "# " + header, ""]
    for k, v in entries:
        L.append(' %s: "%s"' % (k, v.replace('"', "'")))
    L.append("")
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, fname), "w", encoding="utf-8-sig", newline="\r\n").write("\n".join(L))
    print("  %-46s %5d keys" % (fname, len(entries)))

print("\nwriting:")
write("innea_location_names_l_english.yml",
      "Location names from the Information sheet, with EU4 PROV<id> filling any gap. The sheet "
      "leads because EU4 prov_names drifts by one id across part of the sea zones. The 41 "
      "names the two sources disagree on are listed in map/loc_name_conflicts.txt.",
      loc_entries)
write("innea_religion_l_english.yml",
      "Religions and religion groups, from the EU4 mod (every key was already localised there).",
      [(k, from_eu4(k)) for k in rel_groups] + [(k, from_eu4(k)) for k in religions])
write("innea_cultural_and_languages_l_english.yml",
      "Cultures, languages and language families. EU4 where present, generated from the key otherwise.",
      [(k, from_eu4(k, "_culture")) for k in cultures] +
      [(k, from_eu4(k, "_language")) for k in languages] +
      [(k, pretty(k)) for k in families])
write("innea_culture_groups_l_english.yml",
      "Culture groups, from the EU4 mod's own group names where it had them.",
      [(k, from_eu4(k)) for k in cul_groups])
write("innea_region_names_l_english.yml",
      "Continents, subcontinents and regions. The EU4 mod's region keys are a different naming "
      "scheme with zero overlap, so these are generated from the EU5 key.",
      [(k, pretty(k, "_continent")) for k in sorted(level[0])] +
      [(k, pretty(k, "_subcontinent")) for k in sorted(level[1])] +
      [(k, pretty(k, "_region")) for k in sorted(level[2])])
write("innea_area_l_english.yml", "Areas, generated from the EU5 key.",
      [(k, pretty(k, "_area")) for k in sorted(level[3])])
write("innea_province_names_l_english.yml", "Provinces, generated from the EU5 key.",
      [(k, pretty(k, "_province")) for k in sorted(level[4])])
write("innea_dynasty_names_l_english.yml", "Dynasties behind the two personal unions.",
      [(k, {"of_keltran_dynasty": "of Keltran", "sa_maea_dynasty": "sa Maea"}.get(k, pretty(k, "_dynasty")))
       for k in dynasties])

print("\nnon-location entries: %d from EU4, %d generated from the key"
      % (stats["EU4"], stats["generated"]))
