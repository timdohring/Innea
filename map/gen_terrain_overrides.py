# -*- coding: utf-8 -*-
"""Generate the two terrain overrides Innea's custom terrain needs.

!!  PARKED 2026-09-13 - THIS DOES NOT WORK. DO NOT RE-RUN EXPECTING RESULTS.  !!
EU5 does not appear to honour mod overrides of gfx/ files at all. The decisive test:
vanilla's OWN `default_biome` was redefined as 16 slots of solid Snow in the mod's
materials.txt override, at the correct path and filename, verified present in the installed
folder - and the map was unchanged. That rules out custom keys, rule matching, load order and
file naming; the override is simply never read. Overriding `common/` files works fine (the
capital_in_* static modifiers proved that), so the restriction is specific to gfx/.
The script is kept because it is correct and ready if a way to load these files is ever found.


WHY THESE ARE OVERRIDES AND NOT ADDITIVE FILES
----------------------------------------------
Proven 2026-09-13, do not re-test: neither `gfx/map/biome_definitions/` nor `gfx/terrain2/`
is glob-merged. A file placed beside vanilla's is *lexed* (it trips lexer.cpp:501 when it
lacks a BOM) but its contents are never used - both `biomes.txt` and `materials.txt` are
opened BY NAME. A diagnostic rule targeting a plain vanilla key (`topography = mountains`
-> a snow biome) produced no visible change, which ruled out every other explanation.

Without these overrides all 191 locations on deadlands/glacial/volcanic match NO biome rule
(190 of vanilla's 191 rules name a topography and none name Innea's) and fall through to
rule 000 -> default_biome -> fallback_material: one flat dead-grass texture.

This breaks the project's standing "never copy a base-game file" rule, so the copy is
GENERATED rather than hand-edited. After a Paradox patch, re-run this script and the
overrides pick up vanilla's new content automatically:

    python map/gen_terrain_overrides.py

The script refuses to write if anything no longer resolves, so a patch that renames a
material or restructures the files fails loudly instead of silently shipping stale content.
"""
import os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
MOD = os.path.join(REPO, "wip mod folder")
VAN = r"C:\Program Files (x86)\Steam\steamapps\common\Europa Universalis V\game"
rd = lambda p: open(p, encoding="utf-8-sig", errors="replace").read()

VAN_BIOMES = os.path.join(VAN, "in_game", "gfx", "map", "biome_definitions", "biomes.txt")
VAN_MATS = os.path.join(VAN, "in_game", "gfx", "terrain2", "materials.txt")
OUT_BIOMES = os.path.join(MOD, "in_game", "gfx", "map", "biome_definitions", "biomes.txt")
OUT_MATS = os.path.join(MOD, "in_game", "gfx", "terrain2", "materials.txt")

# ---------------------------------------------------------------- Innea's biomes
# 16 material slots, vanilla's order: the five topographies, coastline transition,
# rivers/lakes, borders/water transition, the two transitions, then six variations.
# Everything is built from vanilla's own 70 materials - no new textures yet.
SLOTS = ["flatland", "hills", "plateaus", "mountains", "wetlands", "coastline transition",
         "rivers/lakes", "borders/water transition", "transition vegetation",
         "transition climate", "variation 1.1", "variation 1.2", "variation 1.3",
         "variation 2.1", "variation 2.2", "variation 2.3"]

BIOMES = {
    # ashen, lifeless, pale
    "innea_deadlands_biome": [
        "base_sediment", "sediment_light_01", "sediment_heavy_01", "base_rock_light",
        "base_sediment", "dirt_transition_01", "sediment_light_01", "dirt_transition_01",
        "base_sediment", "base_sediment", "base_sediment", "sediment_light_01",
        "dirt_transition_01", "sediment_heavy_01", "base_sediment", "sediment_light_01"],
    # ice and snow - the only three ice materials vanilla has
    "innea_glacial_biome": [
        "Snow", "Snow", "ice_snow_variation_01", "Ice", "Ice", "ice_snow_variation_01",
        "Ice", "ice_snow_variation_01", "Snow", "Snow", "Snow", "ice_snow_variation_01",
        "Ice", "Snow", "ice_snow_variation_01", "Snow"],
    # dark basalt - real rock, not dirt
    "innea_volcanic_biome": [
        "base_rock_dark", "base_rock_dark", "base_rock_03", "base_rock_dark",
        "sediment_heavy_dark_01", "base_transition_dark", "sediment_dark_01",
        "base_transition_dark", "base_dirt_dark", "base_dirt_dark", "base_rock_dark",
        "sediment_heavy_dark_01", "base_rock_03", "base_dirt_dark", "base_rock_dark",
        "sediment_dark_01"],
    # dead vegetation: bare dark earth with the odd scrap of dead scatter
    "innea_dead_vegetation_biome": [
        "base_dirt", "base_dirt", "sediment_light_01", "base_rock", "base_dirt",
        "dirt_transition_01", "grass_scatter_dark_variation_01", "dirt_transition_01",
        "base_dirt", "base_dirt", "base_dirt", "dirt_transition_01",
        "grass_scatter_dark_variation_01", "base_dirt", "sediment_light_01", "base_dirt"],
    # fungal forest. NOTE: none of vanilla's 70 materials is purple, so this is as strange as
    # it gets without new art - dark dense woods. See TODO: custom terrain textures.
    "innea_fungal_biome": [
        "grass_wood_dense_01", "grass_wood_dense_02", "grass_dense_dark_variation_01",
        "base_rock_dark", "wetlands_dense_01", "dirt_dark_transition_01",
        "wetlands_dense_green_01", "dirt_dark_transition_01",
        "grass_dense_dark_variation_01", "grass_dense_dark_variation_01",
        "grass_wood_dense_01", "grass_dense_dark_variation_01", "grass_wood_dense_02",
        "grass_dense_dark_variation_01", "grass_wood_dense_01", "wetlands_dense_01"],
}

# Rule key -> (match key, match value, biome). Topography-only rules follow vanilla's own
# pattern for terrain whose look is dominated by the topography (its rules 188-191 do exactly
# this for dune_wasteland, mesa_wasteland, salt_pans and atoll).
RULES = [
    ("innea_deadlands",       "topography", "deadlands", "innea_deadlands_biome"),
    ("innea_glacial",         "topography", "glacial",   "innea_glacial_biome"),
    ("innea_volcanic",        "topography", "volcanic",  "innea_volcanic_biome"),
    ("innea_dead_vegetation", "vegetation", "dead",      "innea_dead_vegetation_biome"),
    ("innea_fungal",          "vegetation", "fungal",    "innea_fungal_biome"),
]

# TEMPORARY DIAGNOSTIC. Set True to redefine vanilla's own `default_biome` as solid snow.
# Innea's five terrains currently render as default_biome, so if this turns them white the
# materials.txt override IS being loaded and the fault is purely rule matching; if nothing
# changes, the override is not being read at all and the problem is elsewhere entirely.
# This touches only default_biome - every other vanilla biome is untouched.
PROBE_DEFAULT_BIOME_SNOW = False

BANNER = ("#\n"
          "# ==========================================================================\n"
          "#  INNEA OVERRIDE - GENERATED FILE, DO NOT HAND-EDIT\n"
          "#  Everything above this banner is vanilla's, copied verbatim.\n"
          "#  Everything below is Innea's, appended by map/gen_terrain_overrides.py.\n"
          "#  After a Paradox patch, re-run that script to pick up vanilla's changes.\n"
          "# ==========================================================================\n"
          "#\n")

# ---------------------------------------------------------------- validate
van_mats_txt = rd(VAN_MATS)
if "biomes = {" not in van_mats_txt:
    sys.exit("FAIL: vanilla materials.txt no longer has a 'biomes = {' block - structure changed")
mats_head, mats_biomes = van_mats_txt.split("biomes = {", 1)
known_mats = set(re.findall(r'name\s*=\s*"([^"]+)"', mats_head))
known_biomes = set(re.findall(r'\{\s*name\s*=\s*(\S+)\s*materials', mats_biomes))

problems = []
for name, mats in BIOMES.items():
    if len(mats) != 16:
        problems.append("%s has %d slots, expected 16" % (name, len(mats)))
    for m in mats:
        if m not in known_mats:
            problems.append("%s: material '%s' not in vanilla materials.txt" % (name, m))
    if name in known_biomes:
        problems.append("%s collides with a vanilla biome name" % name)

van_rules = rd(VAN_BIOMES)
existing_keys = set(re.findall(r'^(\S+)\s*=\s*$|^(\S+)\s*=\s*\{', van_rules, re.M))
existing_keys = {a or b for a, b in existing_keys}
defined = set()
for kind in ("topography", "vegetation"):
    d = os.path.join(MOD, "in_game", "common", kind)
    if os.path.isdir(d):
        for f in os.listdir(d):
            defined |= set(re.findall(r'^([a-z_0-9]+) = \{', rd(os.path.join(d, f)), re.M))
    defined |= set(re.findall(r'^([a-z_0-9]+) = \{',
                   rd(os.path.join(VAN, "in_game", "common", kind, "00_default.txt")), re.M))
for key, mk, mv, biome in RULES:
    if key in existing_keys:
        problems.append("rule key '%s' collides with a vanilla rule" % key)
    if mv not in defined:
        problems.append("rule '%s' matches %s='%s' which is not defined anywhere" % (key, mk, mv))
    if biome not in BIOMES:
        problems.append("rule '%s' points at unknown biome '%s'" % (key, biome))

if problems:
    print("REFUSING TO WRITE - %d problem(s):" % len(problems))
    for p in problems:
        print("   -", p)
    sys.exit(1)

# ---------------------------------------------------------------- write
def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8-sig", newline="\r\n").write(text.replace("\r\n", "\n"))

# 1. biomes.txt - vanilla's 191 rules verbatim, then Innea's appended
out = [van_rules.rstrip("\n"), "", BANNER]
for key, mk, mv, biome in RULES:
    out += ["%s =" % key, "{", "\t%s = %s" % (mk, mv), "\tbiome = %s" % biome, "}", ""]
write(OUT_BIOMES, "\n".join(out))

# 2. materials.txt - vanilla verbatim, Innea's biomes inserted before the closing brace
tail = mats_biomes.rstrip()
if not tail.endswith("}"):
    sys.exit("FAIL: could not find the closing brace of vanilla's biomes block")
inner = tail[:-1].rstrip()
blocks = [BANNER]
for name, mats in BIOMES.items():
    blocks.append("\t{")
    blocks.append("\t\tname = %s" % name)
    blocks.append("\t\tmaterials = {")
    blocks.append("")
    for i, (m, s) in enumerate(zip(mats, SLOTS)):
        if i in (6, 10):
            blocks.append("")
        blocks.append("\t\t\t%s\t#%s" % (m, s))
    blocks += ["", "\t\t}", "\t}", ""]
body = "biomes = {" + inner + "\n\n" + "\n".join(blocks) + "\n}\n"
if PROBE_DEFAULT_BIOME_SNOW:
    before = body
    body = re.sub(r'(\{\s*name\s*=\s*default_biome\s*materials\s*=\s*\{)[^}]*(\})',
                  r'\1\n\t\t\tSnow\n\t\t\tSnow\n\t\t\tSnow\n\t\t\tSnow\n\t\t\tSnow\n\t\t\tSnow\n\t\t\tSnow\n\t\t\tSnow\n\t\t\tSnow\n\t\t\tSnow\n\t\t\tSnow\n\t\t\tSnow\n\t\t\tSnow\n\t\t\tSnow\n\t\t\tSnow\n\t\t\tSnow\n\t\t\2',
                  body, count=1)
    if body == before:
        sys.exit("FAIL: probe could not find default_biome to patch")
    print("  !! PROBE ACTIVE: default_biome redefined as solid Snow !!")
write(OUT_MATS, mats_head + body)

print("vanilla: %d materials, %d biomes, %d rules" % (len(known_mats), len(known_biomes),
                                                      len(re.findall(r'^\d+\s*=', van_rules, re.M))))
print("wrote %s  (+%d rules)" % (os.path.relpath(OUT_BIOMES, REPO), len(RULES)))
print("wrote %s  (+%d biomes)" % (os.path.relpath(OUT_MATS, REPO), len(BIOMES)))
