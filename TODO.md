# Innea — TODO

Working list for the EU5 total conversion. Orientation lives in `CLAUDE.md`; the load-failure
engineering log lives in `DEBUG_SESSION_NOTES.md`.

Standing rule for all ports: **add new Innea files alongside vanilla, never copy or empty base-game
files** — a copied vanilla file goes stale the next time Paradox patches. Check for name collisions
first; that is what makes additive safe.

---

## 1. Game-start (`main_menu/setup/start/`)

The world is empty because all 25 files there are empty overrides. Replacing them is the main body of
work. Vanilla's Earth game-start has **never actually run on this map**, so expect fresh failures the
first time anything non-empty loads.

- [x] **`03_markets.txt`** — 122 markets ported from the EU4 trade nodes, grouped by continent.
- [ ] `10_countries.txt` — port from `../Version 1.3 (1.33)/2226968141/common/countries` (933 files)
- [x] **`06_pops.txt`** — 4303 locations populated, **181.4M** total. First pass: the whole population of
      a location is a single `peasants` pop carrying that location's culture and religion.
      `size` is in **thousands** (vanilla Earth totals 393,896 = ~394 million).
      **Per-area totals are hand-authored in `map/area_population_targets.txt`** (118 areas, grouped
      subcontinent > region > area). Within each area the total is split by
      `dev^1.9 * (topography*vegetation*climate*rgo)^0.25 * jitter`.
      Terrain multipliers were *measured from vanilla itself* (median pop per attribute / world median)
      and live in `map/vanilla_multipliers.json`; jitter is a seeded lognormal (sigma 0.18) so the
      generator is deterministic — re-running produces a byte-identical file.
      Generator: `map/gen_pops.py`. Hand-pinned: `fuad` = 1000k, and `zuwar`+`bayd`+`sire` >= 1000k.
      All 118 area targets are hit exactly.
      - [ ] **Split those peasants into other pop types.** Vanilla's own data gives the rule: tribesmen
            share falls monotonically with location size (98% in the smallest decile, 8.8% in the
            largest), peasants rise 1.9% -> 78.5%. Elite pops are tiny by headcount world-wide —
            burghers 0.59%, clergy 0.06%, nobles 0.01%.
      - [ ] Use **Center of Trade Level** (sheet col Q) for burghers, and topography/vegetation/climate
            to push tribesmen up on marginal land.
      - [ ] Slaves are 7.5% of vanilla's world but that is Earth-specific. Innea hooks: the religion
            groups' `allow_rgo_slave_demand`, and the EU4 `slaver` culture (29 locations).
      - [ ] Revisit `WORLD = 81600`. It matches Earth's population *per populated location*
            (394M over 20,794 vs Innea's 4303) and lands on vanilla's distribution, but it is a design
            choice, not something the data settles.
      - [ ] **Why a power law:** development is a compressed scale, population is not. Innea's dev spans
            only 5.4x median-to-max where vanilla population spans 112x. gamma=2.3 was fitted to match
            vanilla's p75/p95 spread; linear would give a world with no real cities.
      - [ ] **Dead end — do not retry:** deriving pop *composition* from the tax/production/manpower
            split. Those are authored as near-equal thirds (33.6 / 33.6 / 32.8, sd ~0.055, 68% of
            locations within 8pp of even), so they carry no usable signal. Total Dev is the only
            meaningful development number in the sheet.
- [ ] `02_core.txt`
- [ ] `07_cities_and_buildings.txt`
- [ ] `05_characters.txt` / `04_dynasties.txt`
- [ ] `08_institutions.txt`
- [ ] `09_roads.txt`
- [ ] `13_religion.txt` — assign religions to locations/pops (see §2)
- [ ] `21_locations.txt`, `14_development.txt` — source data is in `../map/location_info.csv`
- [ ] the remaining `11`–`27` files

**Never load-tested.** Nothing non-empty has ever reached this stage. Run after the first real file
lands and watch for a fresh failure boundary.

## 2. Religions

Ported 2026-09-02: 21 groups / 69 religions, one file per group. Untested in-game.

- [x] **Location religions assigned** — `map_data/location_templates.txt`: 4306 of 4518 land templates
      now carry their real Innea religion (was `catholic` on every one). Source: EU4
      `history/provinces/` (4302, keys already match our religion names), `location_info.csv` (2),
      plus `mount_azta`/`mount_huetlal` set to `quatzalotl` from unanimous neighbours. All 69 religions
      are used. The 212 still on `catholic` are the unauthored continents — see §9.
- [ ] **Improve the `definition_modifier` values** — make them more balanced and more interesting.
      The current numbers are EU4's, mechanically remapped, not designed for EU5.
- [ ] **Add more `opinions`** for each religion — every one currently has an empty `opinions = {}`.
- [ ] **Add gfx `tags`** — no religion has any; vanilla uses e.g. `{ folk_european_gfx pagan_gfx
      permic_coa_gfx }`. Needs Innea gfx sets to exist, or a sensible vanilla set to borrow.
- [ ] **Actually implement some religions' mechanics.** Every EU4 mechanic came across as a comment
      only — `defender_of_faith`, `fervor`, `personal_deity`, `harmonized_modifier`, `crusade_name`,
      `on_convert`, `allowed_conversion`. Pick the flagship faiths and give them real EU5 systems.
- [ ] **Make heretic religions a real thing.** EU4 `heretic = { GREATMAN }` etc. is preserved as a
      comment on each religion but has no EU5 counterpart wired up.
- [ ] Localisation — all 90 names (69 religions + 21 groups) currently show as raw keys.
- [ ] Revisit the sign-flipped mappings: `build_cost`, `stability_cost_modifier`, `advisor_cost`,
      and `technology_cost`/`idea_cost`/`all_power_cost` → `research_speed_modifier`. EU4 phrases
      these as costs, EU5 as efficiencies, so the sign was inverted — confirm that reads right.
- [ ] Three EU4 keys collapse onto `research_speed_modifier`; where a religion had more than one they
      were summed onto a single line. Check those.
- [ ] 52 of 227 EU4 modifier lines had no EU5 counterpart and are comments — decide what, if anything,
      replaces them.
- [ ] `language` and `religious_school` fields are unset on every religion.

## 3. Cultures and languages

First pass done 2026-09-02: 466 cultures, 76 culture groups, 76 languages, 8 language families,
550 colour tokens. Ported from the EU4 mod's single `common/cultures/innea_cultures.txt`.
Untested in-game.

```
main_menu/common/named_colors/04_innea_cultures.txt
in_game/common/language_families/01_innea.txt        8 families
in_game/common/languages/01_innea_<family>.txt       8 files, 76 languages
in_game/common/culture_groups/01_innea.txt           76 groups
in_game/common/cultures/<group>.txt                  76 files, 466 cultures
```

Structure of the first pass: each EU4 culture group became one language (EU4 keeps name lists on the
group, EU5 on the language) plus one culture group; each EU4 culture became one EU5 culture pointing at
its group's language. Families are hybrid — lineage where EU4's own names imply one (elvish, dwarven,
orcish, other non-human), geography for the rest.

- [ ] **Overhaul language families / languages / dialects.** The first pass gives every EU4 culture group
      its own top-level language, which says the 10 elven peoples are as unrelated as Swedish is to
      Mandarin. EU5 supports a `dialects = { }` block nested inside a language, and cultures may point at
      either a language or a dialect. Vanilla's Scandinavian file is the model: one parent language
      holding `swedish_dialect`, `norwegian_dialect`, `danish_dialect`, `icelandic_dialect`, each with its
      own name lists and extras (`patronym_suffix_daughter`, `location_prefix`, `descendant_suffix`) and
      able to inherit via `fallback = <other_dialect>`.
      Best candidates: **one `elvish_language` with 10 dialects** (`high_elf` `river_elf` `ice_elf`
      `dark_elf` `fire_elf` `sea_elf` `wood_elf` `night_elf` `blue_elf` `lost_elf`), **dwarven**
      (`dverik` `wood_dwarf`), **orcish** (`orkal` `wood_orc`). Cultures keep one `language =` line each,
      just repointed — the culture files barely change.
      Scale check: dialects are the exception in vanilla, not the rule — only 31 of 532 languages have
      any, and 1819 of 2087 cultures point straight at a top-level language. The first pass is a
      legitimate shape, not a bug.
- [ ] **Revisit which cultures speak which language.** `language =` is one line per culture and freely
      repointable; a culture has exactly one language, but many cultures can share one (vanilla's
      `pama_nyungan_language` is shared by 130). So e.g. Ormian-speaking high elves just means pointing
      those elf cultures at `wuerdic_language`. What is *not* expressible: one culture speaking different
      languages in different places.
- [ ] **gfx `tags` are placeholders.** Required on every culture (all 2083 vanilla cultures have them),
      so something had to go there; currently a vanilla set keyed off continent — `european_gfx` for
      Innea, `middle_east_gfx` for Astrea, `east_asian_gfx` for Emea, `african_gfx` for Orea. That mapping
      is a guess, not design. Same open question as the religion `tags`.
- [ ] **Culture colours are generated, not authored.** EU4 defines no culture colours at all, so all 466
      were generated: one hue band per group, shades within it. Safe to hand-tune.
- [x] **Cultures wired to locations.** `location_templates.txt` had `culture = swedish` on all 4518 land
      templates; 4306 now carry their real Innea culture. Source: EU4 `history/provinces/` (4302),
      `location_info.csv` (1), plus `arman_mountains`→`kesh`, `mount_azta`/`mount_huetlal`→`avalean` from
      unanimous neighbours. **All 466 cultures are placed** — none is unused. The 212 left on `swedish`
      are exactly the same locations left on `catholic` (§9).
- [ ] Localisation — all 550 culture/language/family names show as raw keys.
- [ ] `country_modifier` / `location_modifier` / `character_modifier` are unset everywhere, matching
      vanilla practice (only 4 of 2083 cultures and 1 of 209 groups use them). Add only where meaningful.
- [ ] `lowborn` name lists are empty on all 76 languages.
- [ ] EU4's `primary = TAG` on all 466 cultures was not ported — it has no EU5 home on the culture. Keep
      it as reference data for the country port.
- [ ] Note: `pamiri` and `uru` collided with vanilla cultures once suffixed and are named
      `innea_pamiri_culture` / `innea_uru_culture`. Remember this when mapping CSV labels to cultures.

## 4. Investigate: sheet vs EU4 history disagreements

The mod's religion/culture assignments came from the EU4 mod's `history/provinces/`, but the Information
sheet's own Religion (M) and Culture (N) columns disagree on **33 rows out of ~4300**. One of the two
sources is wrong on each. The mod currently follows EU4 history.

**Religion — 8 rows**

| Sheet says | EU4 history says | Rows |
|---|---|---|
| `Yoneth` | `aaqan` | 7 (ids 126-128, 140-143) |
| `Old Yorr` | `zakritz` | 1 (id 1818, North Way) |

**Culture — 25 rows**

| Sheet says | EU4 history says | Rows |
|---|---|---|
| `Ãht` (mojibake) | `oht_culture` | 12 |
| `Dhoillbridic` | `dhoilbridic_culture` | 7 |
| `Derzian` | `murrian_culture` | 1 |
| `Kronnish` | `upper_sternian_culture` | 1 |
| `Goldtrader` | `axian_culture` | 1 |
| `Axian` | `goldtrader_culture` | 1 |
| `Ashlati` | `indrysian_culture` | 1 |
| `Indrysian` | `saith_culture` | 1 |

- [ ] `Ãht` (12 rows) is an **encoding artifact** in the sheet — a non-ASCII character mangled at some
      point. `oht_culture` is the real name. Fixing the sheet is probably all that is needed.
- [ ] `Dhoillbridic` vs `dhoilbridic` (7 rows) is a **one-letter spelling difference**. Decide which
      spelling is canonical and make both sides match.
- [ ] `Goldtrader`<->`Axian` look **swapped**, and `Ashlati`->`Indrysian`->`Saith` looks like a **shifted
      row** in one source. These are the ones worth actually looking at — they are not formatting.
- [ ] Decide the precedence rule going forward. If the sheet is the source of truth (it is), then
      `location_templates.txt` should be regenerated with the sheet as primary once these are resolved —
      but only after, since today the sheet is wrong on at least the 12 mojibake rows.
- [ ] Also note columns M/N are **human labels**, not engine keys: `Cult of the Sea` -> `sea_cult`,
      `House of the Dead` -> `dead_house`, `Dream Mother` -> `dreammother`, and M is internally
      inconsistent in casing (`Ojal`/`ojal`, `Sukkali`/`sukkali`, `Ametic`/`ametic`). The generated
      W/X columns hold the real keys.

## 5. Markets — follow-ups

- [x] **Three of eight continents have no market** (`menea`, `perlea`, `vulthark`) — explained: those
      continents were never authored in the EU4 mod at all. See §9. Not a porting gap.
- [ ] **Panoria has exactly one market**, `tyrven_bor`, on a dev-10 location. A whole continent's trade
      hangs off it.
- [ ] 12 of the 32 reseated markets are coastal but front a *different* body of water than the sea zone
      their EU4 node sat on. May be worth reseating onto a member that fronts the original zone.

## 6. Other content to port from EU4

Source: `../Version 1.3 (1.33)/2226968141/`

- [ ] Ideas → whatever the EU5 equivalent is
- [ ] Events, decisions, missions
- [ ] Localisation generally

## 7. Map and engine

- [ ] **Test the custom `in_game/common/goods/`** set — it is in the wip folder but **not installed**,
      so it has never been tested in-game.
- [ ] **Lakes are also listed in `sea_zones`** (all 34; vanilla keeps the lists disjoint) — unfixed,
      untested.
- [ ] `layer=` values differ from vanilla for `city` / `unit_stack` / `vfx` locators.
- [ ] `deadlands` / `glacial` / `volcanic` topography are missing the `proximity` field, so
      `<terrain>_proximity_impact` never registers.
- [ ] Localisation for 219 `unnamed_location_N` locations — 209 of them are in the three unauthored
      continents (§9), so naming them is really a design task, not a localisation one.


## 8. Housekeeping

- [ ] **Rename the mod** from `Tim Modding test` / `test_modding` to Innea (`.metadata/metadata.json`).
- [ ] **The wip folder and the installed folder are synced by hand and currently differ.** Always check
      which side is ahead before running. Installed path:
      `C:\Program Files (x86)\Steam\steamapps\common\Europa Universalis V\game\mod\test_modding`
- [ ] Decide whether `../map/updated_info.csv` (6009 rows) should supersede `location_info.csv`.

## 9. Perlea, Menea and Vulthark are unauthored

Discovered 2026-09-02 while assigning location religions. These three continents exist on the map and in
`definitions.txt`, but were **never given content in the EU4 mod**:

| Continent | Land locations | No religion | Named | Markets |
|---|---|---|---|---|
| Perlea | 80 | 80 (100%) | 0 | 0 |
| Menea | 66 | 66 (100%) | 0 | 0 |
| Vulthark | 63 | 63 (100%) | 0 | 0 |

All 209 are `unnamed_location_N`, all `flatland`, and every one sits in a province where *no* location has
a religion — so there is nothing to inherit from. Every other continent is 0% blank.

This single fact explains three separate items above: the three market-less continents, most of the 219
unnamed-location localisation entries, and 209 of the 212 templates still on `catholic`.

- [ ] Decide whether these three continents get designed, or are cut from the map.
- [ ] The remaining 3 blank named locations are `longfin`, `oceans_rise`, `reef_islands` — all hills in
      Coral Archipelago (Astrea), whose province is likewise entirely blank. Same class, smaller.
