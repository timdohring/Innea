# Innea — EU4 → EU5 port gap

What of the EU4 mod (`../Version 1.3 (1.33)/2226968141/`) has not reached EU5, and what it would
take to stop referencing it. Companion to `TODO.md`. Surveyed 2026-09-13.

## The headline

The EU4 mod is 8,373 files / 231 MB, which makes this look enormous. It is not:

| Slice | Size | Status |
|---|---|---|
| `map/` bitmaps | 132 MB (57%) | Superseded — the EU5 map exists |
| `gfx/` flags + art | 77 MB (33%) | Declined — flags stay procedural |
| `events/` | 2.2 MB | ~1,520 of 1,570 events are unmodified vanilla EU4; only ~50 authored |
| Everything else | ~20 MB | The real library — much already ported |

**~90% is already superseded or deliberately declined.** The real gap is a few hundred authored
definitions.

Two separate blockers: **content never ported**, and a **build-time dependency** — 5 of the 11
`map/gen_*.py` generators read the EU4 folder at runtime, so even ported content can't be
regenerated without it.

## System mapping

| EU4 | EU5 target | Fit |
|---|---|---|
| National ideas (433 sets) | `common/advances/` | Strong. EU4 gates them `trigger = { primary_culture = X }` — per **culture**, not tag. 433 sets vs Innea's 466 cultures. Vanilla ships 2,996 advances, 1,024 in 106 `country_<TAG>.txt` files |
| Personal deities (60) | `common/gods/` | Direct. Vanilla 118 gods / 12 files |
| Church aspects (51) | `common/religious_aspects/` | Direct. Vanilla 19 files |
| Institutions (11) | `common/institution/` | Direct. Vanilla 7 files |
| Ages (5) | `common/age/` | EU5 wants 6 ages to EU4's 5 |
| Formable nations (59) | `common/formable_countries/` | Strong. Vanilla 895 entries, keyed on `areas` — Innea has 123 |
| Trade nodes (122) | markets | ✅ done (112 after the 2026-09-13 pass) |
| Other decisions | **no EU5 system** | EU5 has no `decisions/`. Reinterpret → events or `country_interactions` |
| Mission trees | **no equivalent** | Non-issue — the EU4 mod authored **zero**; it blanked `missions/` and shipped the vanilla stub |
| Rebel types (69) | `movements` / `religious_factions` | Loose, needs design |
| Great projects (224) | **no target** | Needs a decision |
| Trade companies (99) | **no target** | Needs a decision |
| Flags (921 `.tga`) | procedural CoA | Declined |

## Already ported

Map and hierarchy · 863 countries · 4,822 province histories · 69 religions / 21 groups ·
466 cultures / 76 groups / 76 languages · 112 markets · 881 urban locations · 1,006 forts ·
development · 245 roads · 98 dependencies + 7 alliances · 8,690 localisation keys.

---

## To do

### Tier 0 — latent breakage and cheap wins

Things the mod already references but does not define.

- [ ] **Port the 51 church aspects** → `in_game/common/religious_aspects/`. All 69 religions set
      `religious_aspects = 1` and the mod defines **none**.
- [ ] **Add Innea holy sites.** All 16 vanilla files are neutralised (load-bearing — they crash on
      Earth locations) and nothing replaces them.
- [x] **`main_menu/common/modifier_type_definitions/` now exists** (2026-09-13) — created as part of
      the terrain fix below, declaring the three `<topography>_proximity_impact` types. Still only
      covers terrain; other custom modifier names remain undeclared.
- [x] **`topography/` and `vegetation/` are additive** (2026-09-13). Both vanilla copies deleted and
      replaced with `01_innea.txt` holding only Innea's entries (3 topographies, 2 vegetations),
      plus terrain colours, the modifier types above, and
      `static_modifiers/01_innea_capital_in_topography.txt` — which fixes the
      `capital_in_deadlands/glacial/volcanic` log errors. **Untested in-game.**
- [ ] **`in_game/common/goods/` is still a stale vanilla copy** (71 goods under vanilla's own
      filenames, so it replaces them). Unlike terrain it does carry retuned values, so it needs a
      diff before it can be split the same way. It also **fails to parse today** —
      `pdx_persistent_reader.cpp:289: Unexpected token: inflation` at lines 81 and 101 of
      `00_raw_materials.txt`, a field current EU5 no longer accepts. See also the fantasy-goods
      item in Tier 2.
- [ ] **Terrain graphics — PARKED, unsolved** (2026-09-13). Innea's 5 custom terrains match no
      biome rule and render as vanilla's fallback grass across 191 locations. Four approaches
      were tried across six launches and **none loaded**: an additive file in `gfx/terrain2/`,
      an additive file in `gfx/map/biome_definitions/`, renaming it to control load order, and
      finally overriding both vanilla base files outright. The decisive test was redefining
      vanilla's **own** `default_biome` as solid snow in the override — verified present in the
      install, no visible change — which shows **EU5 does not honour mod overrides of `gfx/`
      files at all**. `common/` overrides work fine, so the restriction is specific to `gfx/`.
      Worth asking the modding community rather than experimenting further.
      `map/gen_terrain_overrides.py` is kept, correct and ready, should a route be found.
      Innea's terrain is *functionally* right meanwhile — movement, modifiers and map-mode
      colours all work; only the rendered texture is vanilla.
- [ ] **Fix the 2026-09-13 live-log errors** — all 863 countries drop 2 policies + 2 estate
      privileges set by our own templates; 191 road splines unresolved; 114 areas mix sea and land.
- [ ] **Rename the mod** from `Tim Modding test` / `test_modding` to Innea.
- [ ] Fill the remaining empty setup files: `02_core`, `08_institutions`, `11_art`, `13_religion`,
      `15_international_organizations`, `16_wars`, `18`–`27` (16 of 25 still neutralised).

### Tier 1 — high value, direct fit, scriptable

Recommended order; each is a structural mapping and independently testable.

- [ ] **Church aspects** (51) — also clears the Tier 0 dangling reference
- [ ] **Personal deities** (60) → `common/gods/`, across 11 religions
- [ ] **Institutions** (11) → `common/institution/` — `dwarven_forges`, `elvish_renaissance`,
      `orcish_renaissance`, `starmetal`, `human_enlightenment` + 6. Also fills `08_institutions.txt`
- [ ] **Ages** (5) → `common/age/`
- [ ] **Formable nations** (59) → `common/formable_countries/` (55 `FormableNations.txt` +
      4 `OrkalNations.txt`)
- [ ] **Rulers** — 98 monarchs + 2 heirs into `05_characters.txt` / `04_dynasties.txt`. All 863 are
      `ruler = random` today and only 2 characters exist. *(Verified: 98/2 is correct — the EU4 mod
      really does define no more than that.)*
- [ ] **Event modifiers** (23) — 13 `harmonized_*`, 8 `birthplace_of_*`; tied to religions and
      institutions
- [ ] **National ideas** (433 sets) → `common/advances/`, culture-gated. **Do this last in the tier.**
      ⚠️ 403 of 433 have no localised name and the individual idea slots are placeholder text
      (`haaken1: "Idea 1"`, empty desc) — porting gives mechanical bonuses with no flavour, so
      naming is a design job, not a port job

### Tier 2 — design work, no clean mapping

- [ ] **Fantasy trade goods** — ~560 locations. The sheet's RGO column has 18 Innean goods that do
      not exist in EU5: `sturdy_grains` (69), `fungi` (57), `blackgrain` (49), `crystal` (45),
      `whales` (41), `red_sugar` (36), `ancient_artifacts` (35), `chofo` (31), `obsidian` (27),
      `dragon_hide` (24), `blue_copper` (24), `riverweed` (23), `fireiron` (22), `druh` (21),
      `wayda_silk` (16), `springwater` (14), `yv` (13), `khafri_peppers` (13). They were flattened
      onto vanilla goods during the map port — nothing is broken, but the fantasy economy is gone.
      **Highest-value item in this tier**
- [ ] **Great projects** (224 + 142 icons) — decide an EU5 target system first
- [ ] **Trade companies** (99) — decide a target
- [ ] **Rebel types** (69) — one per religion → `movements` / `religious_factions`
- [ ] **Authored events** (~50) — `Ashar.txt` (13 harmonization), `institutions.txt` (30),
      `Starmetal.txt`, `Halmskr.txt`. **Do not port the other ~1,520 — they are vanilla EU4**
- [ ] **Religion decisions** (56) → events / `country_interactions`
- [ ] **International organizations** — 5 trade leagues, 2 PUs, HRE (`emperor = AKK`), celestial
      emperor (`B4N`). `15_international_organizations.txt` is still empty
- [ ] **Pop stratification** — all 4,303 populated locations are `peasants` only
- [ ] **737 unpopulated locations** of 5,040

### Cut the build-time dependency

Orthogonal to content; can be done any time.

- [ ] **Freeze the 6 EU4 paths the generators read** into repo-tracked CSVs — one row per EU4
      province id, one per tag. Surface is 6,734 files / ~17.9 MB (7.7% of the mod), of which
      `history/provinces/` alone is 4,822 files. Consolidating avoids vendoring 18 MB of small files
      and lets the repo regenerate standalone.

      | Generator | EU4 path |
      |---|---|
      | `gen_countries.py` | `common/country_tags/`, `common/countries/`, `history/countries/`, `history/provinces/`, `localisation/innea_countries_l_english.yml` |
      | `gen_cities.py` | `history/provinces/` |
      | `gen_diplomacy.py` | `history/diplomacy/` |
      | `gen_localisation.py` | `localisation/*.yml` |
      | `gen_adjacencies_csv.py` | `map/adjacencies.csv` |

- [ ] ⚠️ **Decide the generator question separately.** Setup files are hand-edited now and several
      generators would destroy hand-made decisions — the 2026-09-13 session alone made 16 rank
      changes and 20 market reseats. Freezing inputs is safe; **re-running generators is not.**

### Not doing

Flags (procedural, decided) · mission trees (nothing authored) · ~1,520 vanilla leftover events ·
vanilla government reforms / policies / cb_types / on_actions / static modifiers · EU4 map bitmaps ·
`common/ideas/ideas to copy/` (a stashed vanilla reference, not content).

---

## When can the EU4 mod be archived?

After **Tier 1 + the dependency freeze**. At that point it is referenced only as design source for
Tier 2, and could move to external storage.

## Verifying each step

- Load test after each tier; compare `…\Europa Universalis V\logs\error.log` against the
  2026-09-13 baseline (which reaches in-game cleanly). `error.log` is overwritten each launch —
  prefer the snapshot under `crashes\<timestamp>\logs\`.
- Reference-integrity check per item: every referenced name must resolve. Reuse the market/city
  validator pattern (resolves against `named_locations/00_default.txt`, `default.map` water lists,
  `ports.csv`, `town_setups`, country ownership) and extend it to aspects, gods, institutions, goods.
- Counts must match across files — religions referencing aspects == aspects defined; formable
  `areas` == real areas in `definitions.txt`.
- Watch `watch_eu5.ps1` during load: flat memory plateau + CPU to idle = healthy; monotonic climb
  with frozen `debug.log` = unbounded loop, and the last log line names the stage.
