# EU5 "Tim Modding test" (Innea total-conversion) — Debug Session Notes

**Last worked:** 2026-08-30
**Status:** ✅ **THE MOD LOADS AND RUNS.** The memory runaway (old Open Blocker, §5) is fixed — cause was two provinces spanning 100 % of map columns on a `wrap_x` map (§12–13). `MainMenu->Game` now completes in ~22 s and the game runs in-game. Sections 5 and 10 record dead ends; read §12–16 for the resolution.

---

## 1. What this mod is
- A **custom total-conversion map** ("Innea" — a fantasy world, not historical Earth).
- Replaces the map: custom `locations.png` (16384×8192) + custom `definitions.txt` hierarchy (`innea_continent > subcontinent > region > area > province = { locations }`).
- ~**5032 locations** after fixes. `wrap_x = yes`, `equator_y = 3340`.
- Mod uses EU5's `in_game/` + `main_menu/` top-level folder structure (this is correct — vanilla uses it too).

## 2. Key paths
- **Mod:** `C:\Program Files (x86)\Steam\steamapps\common\Europa Universalis V\game\mod\test_modding`
- **Vanilla game (for comparison):** `...\Europa Universalis V\game\in_game\` and `...\game\main_menu\`
- **Logs (NOTE: under OneDrive!):** `C:\Users\timdo\OneDrive\Documents\Paradox Interactive\Europa Universalis V\logs\`
  - `debug.log` = load progress + parse errors (most useful); `game.log`, `error.log`.
  - The live `error.log` is **overwritten each launch** — a vanilla session will hide the mod's errors. Use the per-crash snapshot.
- **Crash snapshots:** `...\Europa Universalis V\crashes\Europa Universalis V<timestamp>\` — contains `exception.txt`, `meta.yml`, `minidump.dmp`, and a `logs\` subdir snapshotting debug/error/game at crash time. **The crash `logs\debug.log` tail is the single best diagnostic.**
- **Backups of edited files:** `...\AppData\Local\Temp\claude\...\scratchpad\eu5_backups\` — ⚠️ **session scratchpad, may be purged.** Contains `.bak` of location_templates, named_locations/00_default, definitions, default.map, and `locations.png.bak`. If still needed, copy somewhere stable.

## 3. Tooling used (already installed in this Python)
- Python 3.11 (Windows store) with **Pillow, numpy, scikit-image, scipy** installed.
- Read PNG dims/palette, build color→id arrays, connected-components (`skimage.measure.label`).
- CPU/RAM monitoring via PowerShell `Get-Process eu5` (`TotalProcessorTime`, `PrivateMemorySize64`, `WorkingSet64`, `Responding`).

---

## 4. Fixes APPLIED this session (in order; each pushed the load further)

### Fix 1 — `location_templates.txt` parse errors  ✅ DONE
- **40 lines** had `raw_material wheat` (missing `=`) → changed to `raw_material = wheat`.
- **3 lines** had invalid goods: `arman_mountains` (`mountain_wasteland`), `mount_azta` & `mount_huetlal` (`wasteland_or_sea`) → removed the bogus `raw_material` token (raw_material is optional; 515 vanilla-style wasteland templates omit it).
- Symptom fixed: `pdx_persistent_reader … Failed to read key reference: : wheat` and the first `C0000005` access violation (null RGO good).

### Fix 2 — 100 phantom locations  ✅ DONE
- `named_locations/00_default.txt` + `location_templates.txt` declared 100 locations with **no pixels on the map**: bare `unnamed_location`, `unnamed_location_1`–`_98`, and sea zone `windreef_banks`.
- Removed all 100 from both files. Also removed `windreef_banks` from `definitions.txt` (was in `icewind_sea_province = { icewind_waters windreef_banks }` → now `{ icewind_waters }`) and from `default.map` `sea_zones`.
- Symptom fixed: `pdx_assert … Failed to map indexes completely, will cause logic map issues`.
- Result: 5032 named = 5032 painted, exact 1:1.

### Fix 3 — black left-edge column in `locations.png`  ✅ DONE
- `locations.png` had an **8192-px black (0,0,0) vertical seam at x=0** (every row) = unmapped pixels.
- Filled x=0 from x=1 (neighbor province color). Also the original was **RGBA**; resaved as **RGB** (matches vanilla format).
- This was the actual cause of "Failed to map indexes completely" (the black column, not the phantoms — but both needed fixing).

### Fix 4 — blank `rivers.png`  ✅ DONE
- Mod shipped **no `rivers.png`**, so it fell back to vanilla's Earth rivers traced over Innea provinces.
- Created `rivers.png` = 16384×8192, **mode P, vanilla palette, all index 255** (= land / no rivers).
- **Did NOT fix the runaway** (rivers were not the cause) but is correct to keep.

### Fix 5 — generated map-object locators  ✅ DONE (but did not fix runaway; warning persists)
- `gfx/map/map_objects/generated_map_object_locators_{city,combat,unit_stack,vfx}.txt` were **0 bytes**; vanilla ships them fully populated. Mod had **no dock file**.
- Generated complete files from bitmap centroids: city=4635 (land only), combat/unit_stack/vfx=5032 (all), dock=1465 (from `ports.csv`). Header uses `generated_content=no`.
- **Game STILL logs `map object locator "city/dock/combat/unit_stack" is incomplete!`** → this warning is benign/unconditional; locators are a **red herring**, not the runaway cause.

---

## 5. OPEN BLOCKER — memory runaway during world finalization  ⛔ UNRESOLVED
- **Symptom:** After all parsing + map index + economy setup, in an **unlogged** finalization stage (after last log line ~`map object locator incomplete`), eu5 commits memory **linearly ~0.5 GB/s, unbounded** (observed climbing to **139 GB PrivateBytes**), high CPU (~650% = 6–7 cores), `Responding=True`. Pins 64 GB RAM at 100%, heads toward the ~165 GB commit limit. Not a freeze — a true allocation loop. Must be killed manually.
- **Prime suspect: `nodes.dat`.**
  - Mod's `map_data/nodes.dat` is **byte-identical to vanilla** (MD5 `406a0e7f122848fd714e33faae835d74`, 11,184,800 bytes).
  - It's a **binary graph of float world-coordinate node positions** (trade/market or pathfinding nodes) keyed to **vanilla Earth geography**, dropped unchanged on the Innea map.
  - A node graph pointing at Earth coords/provinces that don't exist on the custom map → plausible unbounded loop in node→province association / inter-node pathfinding during finalization. Timing matches.
- **Why not yet fixed:** `nodes.dat` format is undocumented binary; hand-crafting risks a reader crash. The correct fix is to **regenerate it in the EU5 in-game map editor / nudge tool** for the custom map (a GUI step, can't be scripted from here). Deleting it from the mod doesn't help (vanilla's identical copy loads via fallback).

### Suggested next steps (pick up here)
1. **Regenerate `nodes.dat` via the EU5 map editor** for the Innea map (proper fix). Likely also regenerate locators there.
2. If editor unavailable: experiment with a neutralized/minimal `nodes.dat` (risky) and see if the game regenerates it.
3. Confirm theory by monitoring: if a fixed `nodes.dat` stops the ~0.5 GB/s commit climb, that's it.

---

## 6. Other KNOWN issues (lower priority)
- **`deadlands` topography missing `proximity` field** → `pdx_assert … Modifier type definition deadlands_proximity_impact must exist in DB`. Mod's custom terrains `deadlands`/`glacial`/`volcanic` (in `in_game/common/topography/00_default.txt`, "Innea added" section) lack the `proximity = X` field that vanilla terrains have (which auto-registers `<terrain>_proximity_impact`). Add a `proximity` value to each custom terrain. Non-fatal ("code will try to use it") but should be fixed.
- **No `heightmap.heightmap`** in mod — OK. Vanilla's `map_data` lacks it too; height data lives as tiled PNGs in `gfx/terrain2/decals/`. Engine tolerates its absence.
- **Harmless vanilla-content warnings** (ignore — vanilla data referencing Earth provinces the custom map lacks): `formable_country` "… does not exist", `common/institution/*`, `common/holy_sites/*` "Could not find location …", `gfx/map/locators_override/locators_override.txt` "… is not a valid province name".

## 7. Useful reference facts (verified this session)
- **Map:** 16384×8192, wrap_x, equator_y=3340. 5032 locations, 5032 unique province colors (1:1). Connected-components ratio 1.1 (geometry clean — not fragmented).
- **`named_locations/00_default.txt` format:** `location_name = RRGGBB` (hex RGB matching the province color in `locations.png`).
- **`location_templates.txt` format:** `name = { topography = X vegetation = Y climate = Z religion = R culture = C raw_material = G natural_harbor_suitability = N }` (raw_material & natural_harbor_suitability optional).
- **`rivers.png`:** indexed (mode P), 256-color palette. idx **255 = white = land/no-river**, idx **254 = (255,0,128) = sea**, idx **0–11 = river markers** (source/merge/flow widths). Blank = all 255.
- **Locator file format** (`gfx/map/map_objects/generated_map_object_locators_*.txt`):
  ```
  game_object_locator={ name="city" clamp_to_water_level=no render_under_water=no
    generated_content=no layer="cities_layer"
    instances={ { id=<loc> position={ X 0.0 Z } rotation={ 0 0 0 1 } scale={ 1 1 1 } } ... } }
  ```
  Layers: city→`cities_layer`, combat/unit_stack→`unit_layer`, vfx→`vfx_layer`, dock→`""`.
  **Coordinate map:** `X = pixel_x + 0.5`, `Z = mapHeight(8192) − pixel_y − 0.5`, `Y = 0`.
- **`ports.csv`:** `LandProvince;SeaZone;x;y` where x,y are pixel coords (usable for dock locators).
- **`default.map`:** references `provinces="locations.png"`, `rivers="rivers.png"`, `topology="heightmap.heightmap"`, `setup="definitions.txt"`, `ports="ports.csv"`, `location_templates="location_templates.txt"`; plus `sea_zones`, `lakes`, `impassable_mountains` lists (all must reference locations defined in `definitions.txt`).
- ⚠️ **Never leave `.bak` files inside `map_data/named_locations/`** (or other glob-loaded dirs) — the game loads every file there and duplicates break the map. Keep backups OUTSIDE the mod tree.

---

## 8. `nodes.dat` REVERSE-ENGINEERED — 2026-08-30

**The format is now fully understood. It is NOT a trade/pathfinding node graph — it is a terrain LOD quadtree.**

### Layout
- **349,525 records × 32 bytes = 11,184,800 bytes.** 349525 = (4^10−1)/3 → a **complete quadtree of depth 9**, stored **breadth-first** (level 0 root, then 4, 16, … 262,144 leaves). Within a level, nodes are grouped by parent (Z-order), not raster order.
- Record:
  | offset | type | meaning |
  |---|---|---|
  | 0 | f32 | cell **x**, normalised to map *width* (512 distinct values) |
  | 4 | f32 | cell **y**, same normalisation |
  | 8 | f32 | cell **size** (1.0, 0.5, … 2^-9 — 10 distinct values) |
  | 12 | u32 | `0x0000FFFF` sentinel on empty nodes, else packed per-node bytes |
  | 16 | f32 | **LOD / bounding metric** — small over ocean, large over land |
  | 20 | u32 | packed per-node data (0 on flat cells) |
  | 24 | f32 | secondary metric (0 on flat cells) |
  | 28 | u32 | **1 = empty node, 0 = has data** |
- The quadtree is **square** but the map is 2:1 (16384×8192), so **exactly half the nodes (y ≥ 0.5) are empty** — 174,762 empty / 174,763 real. Innea is also 16384×8192, so this half-empty pattern is already correct for the mod.
- **Rendering `off16` for the 262,144 leaves onto a 512×512 grid draws Earth's continents** — proof the payload is baked from vanilla Earth terrain. (Script: `mk_flat_nodes.py` neighbours in the scratchpad.)

### "Flat cell" baseline (verified against vanilla)
The most common payload at each level is a featureless/ocean cell: everything zero except the f32 at offset 16, which **doubles exactly per level going up**:

| L | off16 bits | value | vanilla count |
|---|---|---|---|
| 9 | `0x3EFF8A14` | 0.49910 | 77,656 |
| 8 | `0x3F54F310` | 0.83184 | 19,276 |
| 7 | `0x3FD4F310` | 1.66368 | 4,339 |
| 6 | `0x4054F310` | 3.32736 | 881 |
| 5 | `0x40D4F310` | 6.65472 | 139 |
| 4 | `0x4154F310` | 13.3094 | 9 |
| 3..0 | +`1<<23` each | 26.6 / 53.2 / 106.5 / 213.0 | extrapolated |

(Level 9 breaks the doubling — leaves use their own constant, 1.2× the extrapolation.)

### What was done
- Generated **`nodes_flat.dat`**: vanilla's file with x/y/size and the empty-node sentinels preserved byte-for-byte, and every non-empty payload replaced by its level's flat baseline. 72,463 records changed (the other 102,300 already were flat). Installed as the mod's `map_data/nodes.dat`.
  - MD5 flat = `464f7a6bcf82defa25801a5838f94871`; MD5 vanilla = `406a0e7f122848fd714e33faae835d74`.
  - This is a **legitimate flat Innea world**, not a hack — every byte written is a byte pattern vanilla itself uses at that level.
- **Stable backup** (no longer in the volatile scratchpad): `C:\Users\timdo\eu5_mod_backups\2026-08-30_pre_nodes\map_data\` — full pre-change copy of the mod's `map_data`.

### Caveat on the theory
Because nodes.dat turned out to be a **terrain-LOD/rendering** structure rather than a trade-node graph, it is now a **weaker** suspect for the finalization memory runaway than section 5 assumed. The flat-nodes run is therefore mainly a **discriminating test**:
- runaway stops → nodes.dat confirmed, and the mod also gets a correct flat map;
- runaway persists → nodes.dat is **exonerated**, and the search moves to location-graph / adjacency / market-network generation (note `adjacencies.csv` is only 60 bytes, i.e. effectively empty, for 5032 locations).

### Monitoring
`scratchpad\watch_eu5.ps1` samples eu5.exe every 3 s (PrivateBytes, WorkingSet, CPU %, Responding, debug.log size) → `eu5_watch.csv`. Run with `-KillAtGB <n>` to auto-terminate above a threshold.

---

## 9. Run 2026-08-30 11:07 — flat `nodes.dat` — **runaway UNCHANGED. nodes.dat is EXONERATED.**

Curve (`eu5_watch.csv`): normal load 0–130 s peaking ~11 GB with frees, then from **t≈146 s the monotonic runaway**: +1.55 GB per 3 s = **0.52 GB/s**, CPU ~740 %, `Responding=True`, `debug.log` frozen at 237,390 bytes. Killed manually at **100.5 GB**. Identical to the 2026-06-30 run. **Section 5's prime suspect is wrong — the flat nodes.dat changed nothing.** (Keep it anyway: it's the correct flat Innea terrain instead of Earth's.)

**Last log lines before the hang** (`error.log` / `game.log`, 11:09:36 → 11:09:43):
1. `production_methods.cpp:526` — economy/production setup completes
2. `game_object_locators.cpp:1159` — `map object locator "city"/"combat"/"unit_stack" is incomplete!`
3. `game_object_locators.cpp:1307` — *"The locator for docks must be regenerated. In game, run `MapObjects.GenerateGameLocator dock`"*
4. …then **nothing**. Runaway begins.

## 10. NEW PRIME SUSPECT — the mod has **no game-start setup at all** ⛔

The mod is **24 files total**. Under `main_menu/` it ships exactly one: `setup/start/06_pops.txt`, **16 bytes**, containing `locations = {\n\n}`. Everything else in `main_menu/setup/start/` falls through to **vanilla's 10 MB Earth game-start**, which is then applied to the Innea map:

| vanilla file | size | content |
|---|---|---|
| `03_markets.txt` | 3.7 KB | `add_market = lubeck / venice / novgorod …` — **~100 markets, all Earth locations** |
| `10_countries.txt` | 1.58 MB | every Earth country and its locations |
| `05_characters.txt` | 2.47 MB | Earth rulers |
| `06_pops.txt` | 5.08 MB | **blanked by the mod → the world has ZERO pops** |
| `07_cities_and_buildings.txt` | 257 KB | buildings on Earth locations |
| `08_institutions.txt` | 662 KB | institution spread from Earth locations |
| `09_roads.txt` | 33 KB | road network between Earth locations |
| `25_area_preferences.txt`, `15_international_organizations.txt`, `12_diplomacy.txt`, … | | all Earth |

**Why this fits the symptom far better than nodes.dat:** market access in EU5 is a propagation over the location graph seeded from market centres. With **zero valid market centres** and **zero pops**, a "expand from each market until every location has access" pass has nothing to converge on — an unbounded, parallel, allocating loop with no logging. That is exactly a 0.5 GB/s climb on 7 cores after the economy stage.

Corroborating: **`market` appears 0 times in error.log** — the market stage produced no output at all, consistent with hanging inside it rather than reporting missing locations.

### Test now staged (run 2)
Wrote **empty overrides for all 25 remaining `main_menu/setup/start/*.txt`** into the mod (each is just its top-level key(s) with empty braces — e.g. `market_manager = {\n}`; `06_pops.txt` was already blank). Each file carries a `# DEBUG NEUTRALISATION` header; **delete a file to fall back to vanilla's version.**

- **Loads / no runaway** → cause is inside game-start setup. Bisect by deleting overrides back in halves; `03_markets.txt` is the first one to restore.
- **Still hangs** → cause is *before* game-start, i.e. in the map / economy / locator stage, and the search moves to `map_data`.

Caveat: an empty world (no countries, no pops) may itself misbehave; if it hangs, check whether the logs now reach *further* than 11:09:43 — that alone is signal.

Backup of the pre-change `main_menu/` tree: `C:\Users\timdo\eu5_mod_backups\2026-08-30_pre_nodes\main_menu\`.

---

## 11. Run 2026-08-30 11:19 — empty game-start — **runaway UNCHANGED. Game-start setup EXONERATED too.**

Same curve (onset t≈195 s, 0.52 GB/s, CPU ~720 %), and — decisively — **the logs stop at exactly the same place**: `game_object_locators.cpp` at 11:22:42, then silence. Emptying all 25 `setup/start` files moved the boundary by **zero**, so §10's market theory is wrong and the hang is at or before the **map-object locator stage**, not in world init.

The empty overrides are harmless and are left in place for now (they also silence a lot of Earth-content noise), but they are **not** the fix. Delete the folder to restore vanilla's game-start.

## 12. Static audit of `map_data` — found the real defect

Cross-validation (`validate.py`) came back clean on names: 5032 named = 5032 templates = 5032 painted colours, every `sea_zones`/`lakes`/`impassable_mountains` entry resolves, `ports.csv` fully resolves. But two geometry problems fell out:

### (a) ⛔ **Two provinces covered 100 % of the map's columns on a `wrap_x` map** — THE BUG
| | mod (before) | vanilla |
|---|---|---|
| largest province | **25.26 %** of map (`anur_desert`, 33.9 M px) | 5.07 % |
| provinces touching both x=0 and x=16383 | 2 | 54 |
| **greatest share of columns occupied** | **100 %** (`anur_desert`, `ice_plain`) | **35.1 %** |

`anur_desert` (south polar cap, y 5780..8191) and `ice_plain` (north cap, y 0..365) were each painted as **one province wrapping the entire cylinder**. Vanilla never does this — it always leaves a seam. A province present in every column **has no unwrapped extent**: any pass that walks the cylinder to find where the province stops never terminates. That is exactly an unbounded, parallel, unlogged allocation loop at the stage that computes per-province spatial extents — i.e. map objects / locators.

Both are `flatland_wasteland` (in `impassable_mountains`, no ports, no pops, no owner), so **splitting them has zero gameplay effect**.

### (b) lakes are also listed as sea zones
All **34** `lakes` entries also appear in `sea_zones`. Vanilla keeps the two lists **disjoint** (0 overlap). Not yet changed — fix after the split is evaluated.

### (c) minor
- `generated_map_object_locators_volcano_eruption.txt` in the mod is **3 bytes — a UTF-8 BOM and nothing else**, overriding vanilla's valid 7-instance file. A locator file with no `game_object_locator={}` block at all. Not yet changed.
- `layer=` values disagree with vanilla: mod uses `cities_layer`/`unit_layer`/`vfx_layer` for city/unit_stack/vfx where vanilla uses `""` (all are valid names in `layers.txt`; only `combat` matches). Not yet changed.
- `ports.csv` has a stray UTF-8 BOM mid-file before `varhall`, so that one row's land location fails to resolve.

## 13. FIX APPLIED — polar wastelands split (`split_polar.py`)

`anur_desert` → 6 vertical bands, `ice_plain` → 4. Band 0 keeps the original name and colour; 8 new locations added (`anur_desert_2..6`, `ice_plain_2..4`) with fresh unused colours. Updated: `locations.png` (resaved RGB), `named_locations/00_default.txt`, `location_templates.txt` (template cloned from the parent), `definitions.txt` and `default.map` (new names listed beside the parent, so they inherit `anurbis_province` / `ice_plain_province` and `impassable_mountains`), and the `city`/`combat`/`unit_stack`/`vfx` locator files (parents' instances recomputed, 8 appended).

**Verified after:**
- provinces **5040**, all painted colours named, all named have templates
- largest province **4.94 %** (was 25.26 %) — now under vanilla's 5.07 %
- **colours touching both x=0 and x=16383: 0** (was 2 at 100 % of columns)
- `impassable_mountains` 117 → 125; `ports.csv` still fully resolves

Backup of the pre-split tree: `C:\Users\timdo\eu5_mod_backups\2026-08-30_pre_split\in_game\`.

---

## 14. Run 2026-08-30 11:32 — after the polar split — ✅ **MEMORY RUNAWAY FIXED**

**The blocker from §5 is resolved.** Memory rose normally to ~11 GB, then **plateaued flat at 11.1–11.2 GB** while CPU fell from ~720 % to ~115 % (idle). No 0.5 GB/s climb, no unbounded allocation. Cause confirmed: **`anur_desert` and `ice_plain` each occupied 100 % of the map's columns on a `wrap_x` map** — a province with no seam has no unwrapped extent. Splitting them into 6 and 4 bands fixed it.

The load also got **further than it ever has**, past `game_object_locators.cpp` for the first time, to a brand-new stage:

```
[11:34:37] game_object_locators.cpp:1159 : map object locator "city" is incomplete!   (benign, as before)
[11:34:51] holy_site.cpp:345 : Invalid location for setting up holy site constantinople_holy_city_gnostic
```

…then **crash: `C0000005 EXCEPTION_ACCESS_VIOLATION`** (`crashes\Europa Universalis V20260830_153451\`, EU5 1.3.11). This is a *different, later* failure — real progress, not the old hang.

**Note the locator warnings are now definitively benign**: they still print, and the load continues past them. §5/§10 both mis-blamed the stage those warnings come from.

## 15. Fixes applied after run 3

1. **`common/holy_sites/*` neutralised** (16 empty override files under `in_game/common/holy_sites/`). Every vanilla holy site names an Earth location (`jerusalem`, `rome`, `constantinople`, …); `holy_site.cpp:345` logs "Invalid location" and then null-derefs. §6 listed these as "harmless warnings" — **they are not; they crash the game.** Each override carries a `# DEBUG NEUTRALISATION` header; delete to restore vanilla.
2. **`generated_map_object_locators_volcano_eruption.txt`** was 3 bytes (a UTF-8 BOM and nothing else) overriding vanilla's 7-instance file — a locator file with no `game_object_locator={}` block at all. Replaced with a valid block with empty `instances={}`.
3. `ports.csv` — **no defect after all.** The "stray mid-file BOM before `varhall`" in §12(c) was an artifact of the validator, not the file: the only BOM is the legitimate one at offset 0. File left byte-identical. Validator now reports ports.csv fully clean.

Still deliberately **not** changed, pending evidence:
- **lakes also listed in `sea_zones`** (all 34; vanilla keeps the lists disjoint). Held back because removing them is a behavioural change and nothing has complained about lakes yet.
- **`layer=`** values differing from vanilla for city/unit_stack/vfx.
- The empty `main_menu/setup/start/` overrides stay for now. **Important:** run 2 did *not* clear vanilla's Earth game-start — the old runaway happened *before* that stage was ever reached, so markets/countries/pops remain untested. They will matter again now that the load gets further.

---

## 16. Run 2026-08-30 11:38 — ✅ **THE MOD LOADS AND RUNS**

```
[11:38:35] Transition MainMenu->Game took: 23.322601 seconds
[11:39:21] Transition MainMenu->Game took: 21.330149 seconds
[11:42:08] Transition Game->MainMenu ... SplashScreen->Empty   (clean exit)
```

**`MainMenu->Game` completed — twice.** The session then sat in-game for ~3 minutes (11:39:21 → 11:42:08) and exited normally. **No crash folder was written.** Memory held flat at **12.9 GB** with CPU ~460 % (working, not runaway); `debug.log` kept growing throughout, i.e. the game was live, not stuck.

**error.log: 606 KB → 23.8 KB (258 lines).** Everything left is benign vanilla-content noise:
- 231 lines `area_preference.cpp: Invalid area/region …` (vanilla area preferences naming Earth areas)
- ~24 lines `goods.cpp: Unknown region/sub_continent/continent …` in `common/goods` demand modifiers (`iberia_region`, `south_asia`, `europe`, …)
- 3 `pdxinput_context.cpp` GUI messages

None are fatal. They are all the same class: **vanilla content referencing Earth geography that Innea does not define.**

### What actually fixed it (the whole chain)
1. **§13 — the real bug.** `anur_desert` (25.26 % of the map) and `ice_plain` occupied **100 % of the map's columns** on a `wrap_x` map. No seam ⇒ no unwrapped extent ⇒ unbounded allocation loop in the per-province extent pass. Split into 6 and 4 bands. **This alone stopped the runaway.**
2. **§15 — the crash after it.** Vanilla `common/holy_sites/*` all name Earth locations; `holy_site.cpp:345` logs "Invalid location" then null-derefs (`C0000005`). Neutralised with 16 empty overrides.
3. `generated_map_object_locators_volcano_eruption.txt` — was 3 bytes of BOM; replaced with a valid empty block.

### Dead ends (do not re-investigate)
- **`nodes.dat`** — fully reverse-engineered (§8), a terrain LOD quadtree, **not** a trade/pathfinding graph. Flattening it changed nothing (§9). The flat version is kept because it is correct for Innea, not because it fixed anything.
- **Game-start setup** (`main_menu/setup/start/`) — emptying all 25 files changed nothing (§11). *But see the caveat below.*
- **Map object locators** — the `"city"/"combat"/"unit_stack" is incomplete!` warnings are **benign and unconditional**. They still print in the successful run.

### Open items, in priority order
1. **The world is empty.** The empty `setup/start/` overrides are still in place, so there are **no countries, no pops, no markets, no characters**. This is why the load is clean. Building an Innea game-start is the next real task — and vanilla's Earth one (markets on `lubeck`/`venice`, countries owning Earth locations) has **never actually been exercised on this map**, because every earlier run died before reaching that stage. Expect new problems there.
2. **lakes are also listed in `sea_zones`** (all 34; vanilla keeps them disjoint) — still unfixed, still untested.
3. `layer=` values differ from vanilla for city/unit_stack/vfx.
4. `deadlands`/`glacial`/`volcanic` topography missing `proximity` (§6).
5. Cosmetic: 219 `unnamed_location_N` locations lack localisation.

### Backups
- `C:\Users\timdo\eu5_mod_backups\2026-08-30_pre_nodes\` — map_data + main_menu before any change today
- `C:\Users\timdo\eu5_mod_backups\2026-08-30_pre_split\in_game\` — before the polar split
- `C:\Users\timdo\eu5_mod_backups\scripts\` — `mk_flat_nodes.py`, `watch_eu5.ps1` (add `split_polar.py`, `validate.py`, `geom2.py` from the scratchpad if you want them kept)
