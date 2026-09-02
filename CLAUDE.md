# Innea — EU5 Total Conversion Mod

**Read this first every session.** It is the standing orientation file for this repo.
Deep debugging history lives in `DEBUG_SESSION_NOTES.md` next to this file — consult it before
re-investigating any load failure.

---

## 1. What this project is

**Innea** is a fantasy-world **total conversion for Europa Universalis V** — an entirely custom map and
setting, not historical Earth. It is a **port/remake of an existing EU4 mod**, "Innea: A Fantasy World"
(Steam Workshop `2226968141`, last EU4 release **v1.3 for EU4 1.33**), whose full content is kept on disk
one level up as the design source-of-truth to port from.

The EU5 side is currently at the **map-and-engine bring-up stage**: the custom map loads and the game runs,
but the world is deliberately empty (no countries, pops, markets, or characters yet). Building the EU5
game-start is the next major body of work.

---

## 2. Repository layout

**Repo root is `…\Innea modding\EU5 Innea`** — the repo contains the EU5 mod and its docs, nothing else
(git, branch `main`, remote `github.com/timdohring/Innea`).

### Inside the repo

| Path | What it is |
|---|---|
| `wip mod folder/` | **The EU5 mod itself.** Working source of truth; mirrors the mod folder the game loads. |
| `DEBUG_SESSION_NOTES.md` | Full engineering log of the EU5 load-failure investigation. **Essential reading.** |
| `TODO.md` | Working task list — game-start, religions, markets, map/engine, housekeeping. |
| `CLAUDE.md`, `README.md` | This orientation file and the repo readme. |

### Outside the repo — local working material one level up (`..\`)

Not version-controlled, but still central to the project. `map/` and the CSVs feed the mod directly;
`Version 1.3 (1.33)/` is what you port content *from*.

| Path | What it is |
|---|---|
| `../Version 1.3 (1.33)/2226968141/` | **The finished EU4 mod** — 933 country files, cultures, religions, ideas, events, decisions, missions, localisation, EU4 map. The content library to port from. |
| `../map/` | Map authoring workspace: GIMP sources (`Provinces.xcf` 193 MB, `locations.xcf`, `small_map.xcf`), the EU4→EU5 conversion CSVs, and `map_scripts/`. |
| `../map/map_scripts/*.py` | Python converters: `definition.py`, `province.py`, `location.py`, `default.py`, `ports.py`, `add_info_to_information_sheet.py` — turn the CSVs into EU5 `map_data` files. **Paths inside them are hardcoded absolute and still point at the old `Innea modding\map\` layout** — they keep working, but check them before assuming. |
| `../map/location_info.csv`, `location_def.csv`, `province_def.csv` | Per-location design data (dev, RGO, topography, vegetation, climate, religion, culture, NHS, forts, owners) and colour→id definitions. |
| `../updated_info.csv` (6009 rows) | Newer revision of the location design sheet. |
| `../default.txt` | Generated `Lakes` / `Water` / `Wasteland` lists for `default.map`. |
| `../external mod tools/Eu5_LocationDefinitionTool-master/` | Third-party C#/Avalonia EU5 location-definition GUI tool. |

**Note:** the whole tree is inside OneDrive. So are the game's logs. Expect sync-related file locking.

---

## 3. The EU5 mod

- **Live path the game loads:** `C:\Program Files (x86)\Steam\steamapps\common\Europa Universalis V\game\mod\test_modding`
- **Mod id/name** (`.metadata/metadata.json`): still the placeholder `"Tim Modding test"` / id `test`,
  version `1.0.0`, supported game version `1.0.*`. **Should be renamed to Innea** at some point.
- **Structure:** EU5's `in_game/` + `main_menu/` top-level layout (correct — vanilla uses it too).
- ⚠️ **The wip folder and the installed folder are synced by hand and currently differ:** `in_game/common/goods/*`
  (5 files + readme) exists only in the wip folder, i.e. the custom goods set has **not been tested in-game yet**.
  Always check which side is ahead before running.

### Map facts (verified)
- `locations.png` **16384×8192**, `wrap_x = yes`, `equator_y = 3340`.
- **5040 locations** after the polar split (was 5032). 1:1 named ↔ painted colours.
- Hierarchy in `definitions.txt`: `innea_continent > subcontinent > region > area > province = { locations }`.
- `named_locations/00_default.txt` format: `location_name = RRGGBB`.
- `location_templates.txt`: `name = { topography vegetation climate religion culture raw_material natural_harbor_suitability }`
  (last two optional).
- `ports.csv`: `LandProvince;SeaZone;x;y` (pixel coords).
- Locator coordinate map: `X = pixel_x + 0.5`, `Z = 8192 − pixel_y − 0.5`, `Y = 0`.
- Custom topographies added by Innea: `deadlands`, `glacial`, `volcanic`.

---

## 4. Current state — the mod loads and runs ✅

`MainMenu->Game` completes in ~22 s; the game runs in-game and exits cleanly. Getting there took a long debug
campaign; the resolution is in `DEBUG_SESSION_NOTES.md` §12–16.

**The one bug that mattered:** `anur_desert` and `ice_plain` were each painted as a single province spanning
**100 % of the map's columns** on a `wrap_x` map. A province with no seam has no unwrapped extent, so the
per-province extent pass allocated unboundedly (~0.5 GB/s, observed to 139 GB). Splitting them into 6 and 4
vertical bands fixed it. Secondary: vanilla `common/holy_sites/*` all name Earth locations and
`holy_site.cpp:345` null-derefs → neutralised with 16 empty overrides.

### Do NOT re-investigate (proven dead ends)
- **`nodes.dat`** — fully reverse-engineered; it is a **terrain LOD quadtree**, not a trade/pathfinding graph.
  Flattening it changed nothing. The flat version is kept only because it is *correct* for Innea.
- **`main_menu/setup/start/`** — emptying all 25 files moved the failure boundary by zero.
- **`map object locator "city"/"combat"/"unit_stack" is incomplete!`** — benign and unconditional; it still
  prints in successful runs.

### Deliberate debug neutralisations still in place
Files carrying a `# DEBUG NEUTRALISATION` header are **empty overrides of vanilla content**, not real content.
Delete a file to fall back to vanilla's version.
- All 25 `main_menu/setup/start/*.txt` → **this is why the world is empty.**
- All 16 `in_game/common/holy_sites/*.txt` → these ones are load-bearing (vanilla holy sites crash the game).

---

## 5. Open work, in priority order

**The actionable checklist lives in `TODO.md`.** This section is the narrative context behind it.

1. **Build the Innea game-start.** Replace the empty `main_menu/setup/start/` overrides with real Innea
   markets, countries, pops, characters, buildings, institutions, roads. Port from the EU4 mod at
   `../Version 1.3 (1.33)/2226968141/` — its `common/countries`, `history/`, `common/cultures`,
   `common/religions`. Vanilla's Earth game-start has
   **never actually run on this map** — every earlier run died before reaching it — so expect fresh failures
   the first time anything non-empty loads there.

   **Progress — `03_markets.txt` is done (2026-09-02):** no longer an empty override. All **122** EU4 trade
   nodes from `common/tradenodes/00_tradenodes.txt` became markets, one per node, all active. 90 sat on a
   land location and use it directly; **32 sat on a sea zone**, which cannot hold a market, and were reseated
   on a **coastal** land member of that node (must appear in `map_data/ports.csv`), chosen by name match with
   the node, then Centre-of-Trade level, then development. The file is grouped by continent/subcontinent,
   derived from `map_data/definitions.txt`. Six seats were reseated purely because the first choice turned out
   to be landlocked. Three of the eight continents (`menea`, `perlea`, `vulthark`) have no market at all —
   inherited from the EU4 node list, never a deliberate decision.

   **The EU4→EU5 id bridge — reuse this for every future port:**
   EU4 province id → RGB via `../map/location_def.csv` → 6-digit hex → EU5 location name via
   `map_data/named_locations/00_default.txt`. EU4 `map/definition.csv` and `location_def.csv` share ids
   and colours, so EU4 ids resolve directly. `../map/location_info.csv` adds per-id display name, dev,
   Centre-of-Trade level, religion, culture and owner. **Always** classify the resolved location against
   `default.map`'s `sea_zones`/`lakes`/`impassable_mountains` — EU4 puts content on sea provinces that
   EU5 requires on land.
   **Progress — religions are ported (2026-09-02, untested):** 21 groups / 69 religions from the EU4
   mod's single `common/religions/innea_religion.txt`, split EU5-style into one file per group.
   → `main_menu/common/named_colors/03_innea_religions.txt` (90 colour tokens, EU4 RGB verbatim — note
   `named_colors` is under `main_menu/`, the only such dir in the game),
   `in_game/common/religion_groups/01_innea.txt`, `in_game/common/religions/<group>.txt` × 21.
   EU4 modifiers were remapped to their nearest EU5 equivalent — 49 keys, 175 of 227 lines (77%), each
   keeping its EU4 original as a trailing comment; the rest are comments. Targets validated against
   `main_menu/common/modifier_type_definitions/` (2436 names). EU4-only mechanics
   (`defender_of_faith`, `fervor`, `personal_deity`, `heretic`, `allowed_conversion`, `on_convert`)
   are comments only. Still missing: localisation, gfx `tags`, `language`, and any pop using them.

   **Locations now carry real religions:** `map_data/location_templates.txt` had `religion = catholic` on
   all 4518 land templates; 4306 now hold their Innea religion, sourced from the EU4 mod's
   `history/provinces/` (its keys are already snake_case and match the ported names — a better source than
   `location_info.csv` labels). The 212 still on `catholic` are Perlea/Menea/Vulthark, three continents
   that were **never authored in the EU4 mod** — see `TODO.md` §7. `culture` there is still the `swedish`
   placeholder... superseded, see below.

   **Progress — cultures are ported and wired (2026-09-02, untested):** 466 cultures, 76 culture groups,
   76 languages, 8 language families, 550 colour tokens, from the EU4 mod's
   `common/cultures/innea_cultures.txt`. EU4 keeps name lists on the culture *group*, EU5 on the
   *language* — so each EU4 group became one language plus one culture group, and each EU4 culture an EU5
   culture pointing at it. Families are hybrid: lineage (elvish/dwarven/orcish/other non-human) where EU4's
   own group names imply one, geography otherwise. EU4 defines no culture colours, so all 466 were
   generated (one hue band per group). `location_templates.txt` now carries real cultures on 4306 land
   templates — **all 466 are placed**. `pamiri`/`uru` collided with vanilla and are prefixed `innea_`.
   Note EU5 also supports dialects nested inside a language (`dialects = { }`); the first pass does not
   use them — see `TODO.md` §3.

   **Additive, never overriding vanilla:** per the user's standing preference, ported content adds new
   Innea files alongside vanilla's rather than copying or emptying base-game files, so nothing goes stale
   on a patch. Name collisions are checked first — there were none for markets or religions.
2. **Test the custom `in_game/common/goods/`** set that is in the wip folder but not installed.
3. **Lakes are also listed in `sea_zones`** (all 34; vanilla keeps the lists disjoint) — unfixed, untested.
4. `layer=` values differ from vanilla for `city`/`unit_stack`/`vfx` locators.
5. `deadlands`/`glacial`/`volcanic` topography missing the `proximity` field → `<terrain>_proximity_impact`
   modifier never registers.
6. Localisation for 219 `unnamed_location_N` locations.
7. Rename the mod from `Tim Modding test` / `test_modding` to Innea.

### Known-benign log noise (ignore)
`area_preference.cpp: Invalid area/region …`, `goods.cpp: Unknown region/sub_continent/continent …`,
`formable_country … does not exist`, `common/institution/*` missing locations. All the same class: **vanilla
content referencing Earth geography that Innea does not define.**

---

## 6. Working practices

- **Logs:** `C:\Users\timdo\OneDrive\Documents\Paradox Interactive\Europa Universalis V\logs\`
  (`debug.log` is the most useful). ⚠️ `error.log` is **overwritten each launch** — a vanilla run hides the
  mod's errors. Prefer the per-crash snapshot in `…\Europa Universalis V\crashes\<timestamp>\logs\`.
- **Crash triage:** the crash folder's `debug.log` tail is the single best diagnostic.
- **Backups live OUTSIDE the mod tree:** `C:\Users\timdo\eu5_mod_backups\`.
  ⚠️ **Never leave `.bak` files inside glob-loaded dirs** like `map_data/named_locations/` — the game loads
  every file there and duplicates break the map.
- **Python:** 3.11 with Pillow, numpy, scikit-image, scipy available — used for PNG/palette work, colour→id
  arrays, and connected-components checks on the province bitmap.
- **Monitoring a run:** `watch_eu5.ps1` samples `eu5.exe` every 3 s (PrivateBytes, WorkingSet, CPU %,
  Responding, `debug.log` size). A **flat memory plateau with CPU dropping to idle = healthy load**;
  a **monotonic climb with a frozen `debug.log` = an unbounded loop**, and the last log line names the stage.
- **After changing map geometry, always re-validate:** named == templates == painted colours; every
  `sea_zones`/`lakes`/`impassable_mountains` entry resolves; `ports.csv` resolves; and **no province spans
  every map column** (the §4 bug).
- When something is fixed or a new dead end is proven, **append it to `DEBUG_SESSION_NOTES.md`** and update
  the open-items list here.
