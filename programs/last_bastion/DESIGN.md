# Last Bastion – Design Document

> **Working title.** A real-time strategy survival game: StarCraft's unit control, They Are Billions' hordes and run
> structure, Factorio's production chains and power grid – in 30-minute rounds.
>

---

## Contents

1. [Pitch and pillars](#1-pitch-and-pillars)
2. [What we take from each game](#2-what-we-take-from-each-game)
3. [Core loops](#3-core-loops)
4. [A round, minute by minute](#4-a-round-minute-by-minute)
5. [Economy](#5-economy)
6. [Buildings](#6-buildings)
7. [Units and control](#7-units-and-control)
8. [The horde](#8-the-horde)
9. [Map generation](#9-map-generation)
10. [Home screen and meta progression](#10-home-screen-and-meta-progression)
11. [UI and controls](#11-ui-and-controls)
12. [Technical notes](#12-technical-notes)
13. [Prototype roadmap](#13-prototype-roadmap)
14. [Open questions](#14-open-questions)
15. [Idea parking lot](#15-idea-parking-lot)

---

## 1. Pitch and pillars

>*Build a compact industrial colony, command an elite strike force, and survive 30 minutes against a world being
swallowed by the horde.*

### Design pillars

Every feature has to serve at least one pillar. If it serves none, it goes to the [parking lot](#15-idea-parking-lot).

| # | Pillar | What it means in practice |
|---|---|---|
| 1 | **The factory is the base – and the base is the target.** | Power lines, machines and houses are both your economy and your weak spot. Expanding production makes you stronger *and* louder. |
| 2 | **An army, not a blob – lots of control.** | A StarCraft-sized army (≈ 50–120 units, as many as your economy can pay for) against a TAB-sized horde (thousands). Every unit matters and has something to click. |
| 3 | **One run, one story.** | 30 minutes, clear escalation, a known climax (attack waves + the final one). Win or lose, the round tells a story. |

### Who is it for?

- People who love StarCraft's control but don't want PvP stress or 300 APM.
- People who love TAB's tension but want more to *do* with their army.
- People who love Factorio's satisfaction but don't have 40 hours per save.

---

## 2. What I take from each game

| Source | Take | Leave out |
|---|---|---|
| **They Are Billions** | Huge hordes, infection cascades (one breach → chain reaction), known attack waves, run-based rounds, colony home screen, difficulty modifiers as score %, unit upkeep in gold, active pause | Stat-check blob armies, punishing one-save rule (❓ maybe as an "Ironman" option) |
| **StarCraft** | Control groups, smart-casting, unit abilities, hard counters, rally points, attack-move, crisp unit responsiveness | PvP, APM pressure, three asymmetric factions (scope!) |
| **Factorio** | Ore patches, simple production chains, power grid, pollution for nest/zombie attacks (in that sense units firing should produce pollution too) | Belts, hundreds of items, megabase scale, multi-hour sessions |
| **Anno** *(bonus)* | Houses that upgrade by being supplied with goods | Trade routes, ships, diplomacy |

---

## 3. Core loops

The game runs on four loops at different time scales. Each must be fun on its own.

| Time scale | Loop | Player feeling |
|---|---|---|
| **Seconds** | Select units → give orders → use abilities → watch the result | "My army does exactly what I want." |
| **Minutes** | Place machines → connect power → supply houses → earn gold → pay for army and defences | "My colony is growing and humming." |
| **One round (≈ 30 min)** | Scout → expand → survive waves → prepare → final wave | "That was close – and I made it." |
| **Across rounds** | Win → unlock tech / regions / modifiers → harder round | "Next time I'll try the other strategy." |

---

## 4. A round, minute by minute

The skeleton every system has to fit into. If a phase has nothing interesting happening, a system is missing.

| Minute | Phase | What happens | Threat |
|---|---|---|---|
| 0–5 | **Landing** | Command center lands. Scout with the starting squad, find ore and fields, first houses, first market. | Stragglers only (single zombies wandering in). |
| 5–12 | **Setting up** | First production chains, power grid, first walls. Barracks, first real units. | First mini-horde, drawn by your **noise**. |
| 12–20 | **Expansion** | Tier 2 houses, second ore field, workshops. Army clears a **nest** or **point of interest** for loot. | Mid-round wave from a random direction. **Creep** starts spreading. |
| 20–27 | **Preparing** | Late tech, heavy defences, scaling up. Banner: *"Final wave in 5:00 – from the north-east"*. | Hordes get special zombies, nests expand. |
| 27–30 | **Final wave** | Everything comes at once, including giants. | Survive = win. |

Optional: **endless mode** afterwards (score keeps counting, waves keep growing).

---

## 5. Economy

### 5.1 Resources and items

Keep it to **about 10 item types**. More doesn't fit into 30 minutes.

| Tier | Item | Made from | Used for |
|---|---|---|---|
| Raw | **Wood** | Lumber camp (forest) | Early buildings, walls |
| Raw | **Stone** | Quarry (rock) | Walls, towers |
| Raw | **Iron ore** | Drill on ore patch | → Iron |
| Raw | **Coal** | Drill on coal patch | Power plant, smelter fuel |
| Raw | **Food** | Farm, fishery, hunter | Houses |
| 1 | **Iron** | Smelter (ore + coal) | Buildings, tools, ammo |
| 1 | **Energy** | Power plant (coal) / later wind, solar | Machines, houses, towers |
| 2 | **Tools** | Workshop (iron + wood) | Tier 2 houses, units |
| 2 | **Ammo** | Armory (iron + coal) | Units and towers with guns ❓ (could also be "free") |
| 3 | **Medicine** | Lab (food + energy) ❓ | Tier 3 houses, healing |
| — | **Gold** | Houses (taxes) | Buying units and their **upkeep** (7.2), research, buildings |

### 5.2 How it all connects

```
 Iron ore ──┐
 Coal ──────┼──► Smelter ──► Iron ──┬──► Workshop ──► Tools ──────┐
 Coal ──────┴──► Power plant ──► Energy ──────────────────────────┤
 Wood ─────────────────────────────┘                              │
 Food ────────────────────────────────────────────────────────────┼──► Houses ──► Gold, workers
                                                                  │                    │
                                                    Medicine ─────┘                    ▼
                                                                         Barracks / Factory ──► Units
                                                                                                  │
                                                                     every unit costs gold/min ◄──┘ (upkeep)

 Every machine ──► NOISE ──► attracts zombies (see 8.3)
```

### 5.3 Houses (the key system)

Houses link economy and army – this is what makes the Factorio part matter in a short round.

| House tier | Needs (per minute, first guess) | Gives | Unlocks |
|---|---|---|---|
| **Shack** | Food | 2 gold/min, 2 colonists | Basic infantry |
| **House** | Food, energy, tools | 5 gold/min, 4 colonists | Vehicles, tier 2 towers |
| **Apartment** | Food, energy, tools, medicine | 10 gold/min, 6 colonists | Elite units, tier 3 research |

- A house that isn't supplied stops paying gold. You can downgrade it if you have to. 
- The same gold pays for the army's **upkeep** (7.2). There is no supply cap: the army is as big as your income
  allows, so every gold is a choice between growing the colony and growing the army.
- Houses are delivered to by a **distribution radius** around a market/warehouse (TAB-like, simpler).

### 5.4 Logistics (no belts)

- Like TAB: what gathering buildings produce goes straight into the **colony stock**. Production buildings take their
  inputs from it and put their outputs back. No belts, no item routing.
- The Factorio part is in the **production chains** (ore + coal → iron → tools …) and the **power grid**, not in
  moving items around.
- Warehouses raise the storage limit; markets supply houses within their radius (5.3).

### 5.5 Power

- Power poles connect machines into a grid (Factorio).
- Not enough power → every machine on that grid slows down proportionally. Towers and houses on the grid suffer too.
- Destroyed poles split the grid → a zombie breach in one corner can black out half the base. (Pillar 1.)

### 5.6 Colonists

The colony should look alive, like in TAB: **colonists** walk around between their houses and workplaces.

- Houses provide colonists, and gathering/production buildings need a number of **workers** (like TAB). Without
  enough workers, a building doesn't run.
- Colonists **walk visibly** from house to workplace and back, along roads where there are some (❓ roads make them
  faster). They can't be controlled.
- **Danger ❓:** a zombie that catches a colonist turns them into a zombie. A breach inside the base then spreads among
  the colonists as well as the buildings. Alternative: purely decorative colonists that run into the nearest
  house when zombies are close.
- Number: a few hundred at most. Enough to look busy; each one only needs simple path-finding to its two targets.

---

## 6. Buildings

First draft. Costs/stats come later in a data file (like the cube game's JSON files).

| Category | Building | Notes |
|---|---|---|
| **Core** | Command center | Start building. Small storage, produces workers ❓, losing it = losing the game |
| **Housing** | Tent → House → Apartment | can be upgraded when materials ready and the next tier item is supplied |
| **Gathering** | Lumber camp, quarry, drill, farm, fishery | Placed on/near the right tile type |
| **Production** | Smelter, workshop, armory, lab | Take inputs from the colony stock (5.4) |
| **Logistics** | Warehouse, market | Warehouse = more storage; market = supply radius for houses |
| **Power** | Power pole, coal plant, wind turbine, solar field, battery | Wind/solar = quieter but weaker |
| **Military** | Barracks, factory (vehicles), tech lab, airfield ❓ | Production queue + rally point |
| **Defence** | Wood wall, stone wall, gate, watchtower (can put in 4 ranged units), ballista tower, flame tower, tesla tower, mine field | Towers use ammo/energy |
| **Special** | Radar (reveals part of the map), sound dampener (less noise), cleanser (removes pollution), beacon (lure zombies to a kill zone) | |

**Infection (from TAB):** If zombies damage a building enough they infect it. This Spawns more zombies (amount and type depending on the building). Breaches should feel catastrophical. Same concept as TAB in the sense of hp and shield for implementation. (shield down = building infected, can be damaged more until destroyed)

---

## 7. Units and control

### 7.1 Control (the StarCraft part)

The most important feel of the whole game. **Highest priority**

- Box select, click select, double-click = all of that type on screen, Shift = add/remove.
- **Control groups** 1–0 (Ctrl+number = set, number = select, number twice = jump camera).
- **Attack-move** (A + click), move, stop, hold position, patrol.
- **Smart-casting**: ability key casts it with the best-suited unit of the selection, not all of them.
- **Rally points** for production buildings (also onto a unit or into a control group ❓).
- **Formations** ❓: units keep their relative positions when moving as a group (StarCraft 2 "magic box").
- **Active pause** (Space): give orders while paused. Makes micro accessible without high APM.

### 7.2 Unit roster (first draft)

Small army, strong units. The infantry is taken from **TAB**, while the support units and vehicles come from
**StarCraft**. Each unit has **a role** and **one active ability** (TAB units have none, so these are new ❓).

| Unit | From | Tier | Upkeep (gold/min) | Role | Ability | Noise | Counters | Weak against |
|---|---|---|---|---|---|---|---|---|
| **Ranger** | TAB | 1 | 1 | Fast, cheap, bow, weak damage | *Sprint*: short speed burst ❓ | Silent | Single runners, scouting | Masses, brutes |
| **Soldier** | TAB | 1 | 2 | Rifle all-rounder, the army's backbone | *Stim* (SC marine): faster attack and movement, costs HP | Loud | Walkers, runners | Swarms when clumped, brutes |
| **Sniper** | TAB | 2 | 3 | Very long range, slow fire, huge damage per shot | *Headshot*: one big shot, long cooldown | Very loud | Brutes, spitters, screamers | Anything that reaches it |
| **Flamethrower** | TAB (Lucifer) | 2 | 3 | Short-range cone, sets the ground on fire | *Burn ground*: area denial + removes creep | Loud | Swarms, dense packs | Spitters (range), brutes |
| **Medic** | SC | 2 | 2 | No attack; heals nearby infantry automatically (energy) | *Restoration*: removes acid, slow and burning | Silent | – (support) | Being targeted |
| **Machine gunner** | – (mech) | 3 | 5 | Walker/mech with a gun that has to **spin up** first | *Keep spinning*: toggle, stays spun up without a target | Very loud | Large hordes, holding a line | Brutes, getting surprised |
| **Siege tank** | SC | 3 | 6 | Primitive artillery, can **only shoot when sieged** | *Siege / unsiege* | Very loud | Hordes at long range, nests | Anything up close, flanking |

#### Upkeep instead of supply (like TAB)

- Every unit costs gold once when it's built **and then every minute** (upkeep, first guesses in the table). There is
  **no supply cap**.
- The army's size is limited only by your income. More soldiers means less gold for houses, research and defences, and
  the other way round. That's the choice between economy and army.
- **Dismiss** a unit to stop its upkeep (no refund), e.g. after the final wave is over in endless mode or when the
  economy breaks down.
- When gold runs out, see **Debt** below.

#### Debt: what happens when gold runs out

Gold can go **below zero**. The deeper the debt, the worse it gets, so the player sees the problem growing instead of
being punished all at once:

| Stage | When (first guess) | Effect |
|---|---|---|
| **0. Broke** | Gold reaches 0 | No new units, buildings or research. Upkeep keeps running → debt. |
| **1. Grumbling** | Debt > 0 | Unpaid units fight worse: −15 % damage and attack speed. |
| **2. Unrest** | Debt > 1 minute of upkeep | −30 %, and units move slower. |
| **3. Desertion** | Debt > 2 minutes of upkeep | Every ≈ 10 s one unit **deserts** (leaves the map), picked at random but weighted (see below). |

- **Who deserts:** every unit has a chance, weighted by
  `weight = upkeep × (3 if not a veteran, else 1)` (first guess). So expensive units and non-veterans are the most
  likely to leave. A sniper (upkeep 3, non-veteran → 9) is three times as likely to desert as a veteran sniper (3) and
  nine times as likely as a veteran ranger (1).
- Paying the debt off (back to ≥ 0) removes the penalties right away. Deserted units don't come back.
- Alerts warn before each stage (*"The soldiers haven't been paid – morale is dropping"*), and the HUD shows the gold
  in red with the time until the next stage.
- → Veterans are much less likely to leave, so the units you kept alive with good micro usually stay with you.
- Size to plan for: ≈ 50–120 units (a mixed army probably ends up around 60–80). Control groups and selection have
  to handle that without trouble (StarCraft 2 handles 200 supply).

**Noise per unit** links the army to the noise system (8.3): rangers can go out quietly, while snipers, machine gunners
and tanks give away where they are – like in TAB.

#### Siege tank: weaker and cruder than StarCraft's

- **Unsieged:** drives slowly and **can't shoot at all**. It needs an escort.
- **Sieging up** takes ≈ 4 s (StarCraft: ≈ 3 s), unsieging ≈ 3 s, and it can't defend itself during either.
- **Sieged:** long range, splash damage, slow rate of fire. It has a **minimum range**: zombies that reach it are safe from
  it. Splash also hits your own units and buildings ❓.
- Less damage and a smaller splash radius than in StarCraft, because ammo is crude (makeshift shells) ❓.
- → The classic StarCraft pattern: tanks sieged behind the wall, infantry in front of them.

#### Machine gunner: spin-up

- When it starts firing it shoots at **≈ 25 %** of its full rate and reaches **100 % after ≈ 3 s** of continuous
  fire.
- With no target for ≈ 2 s it spins down again.
- *Keep spinning* keeps it at full speed without a target, at the cost of energy and **constant noise**. That's a
  trade-off: be ready for the wave, or draw it in.
- → Strong when holding a line and weak against sudden attacks. That's where you pair it with soldiers.

#### Look: StarCraft-like skins ❓

TAB's roles with a StarCraft-*like* look of our own design (inspired by StarCraft, nothing copied):

| Unit | Look |
|---|---|
| Ranger | Light armour, hood, bow – like a Reaper without a jetpack |
| Soldier | Bulky power armour like a marine, but more makeshift |
| Sniper | Slim suit with a helmet visor, like a Ghost |
| Flamethrower | Heavy armour with tanks on the back, like a Firebat |
| Medic | White armour with a red cross, like StarCraft's medic |
| Machine gunner | Small two-legged walker with a minigun |
| Siege tank | Patched-together tank with a crane-like gun |

As in the cube game, unit pictures could be **swappable PNG files** in an `images` folder, so changing a skin means
replacing a file.

### 7.3 Veterancy

Units gain XP from **killed enemies**. With enough XP a unit becomes a **veteran**, and that's the only level: more HP
and damage, plus a visible mark (e.g. a chevron).

- Every killed zombie gives XP (more for tougher types, e.g. walker 1, brute 10, giant 100 ❓). The XP is **split among
  all your units nearby** (radius ≈ sight range ❓), not just the one that made the kill.
- Veterans count as **half a share**. They still take part of the XP even though it does nothing for them. Otherwise,
  in a group of veterans, the whole horde's XP would go to the last few non-veterans.
- Split: each unit gets `XP × own share / sum of all shares` (share 1 = normal, 0.5 = veteran).
  Example: 10 XP, 3 normal units + 2 veterans → total shares 4 → normal units get 2.5 each, veterans 1.25 each. The
  veterans' part is simply used up.
- → Fresh units fighting next to veterans level up at a sensible pace, without instantly becoming veterans.

Makes losing a squad hurt and saving it with micro rewarding. Veterans are also less likely to desert when you're in
debt (7.2). How much XP is needed ❓, probably per unit type, in the data files.

---

## 8. The horde

### 8.1 Zombie types

| Zombie | Behaviour | Why it exists |
|---|---|---|
| **Walker** | Slow, weak, *lots* of them | The mass. Tests your walls. |
| **Runner** | Fast, weak | Punishes gaps and lone units. |
| **Brute** | Slow, huge HP, smashes walls | Needs focus fire (snipers). |
| **Spitter** | Ranged acid, outranges short-range units | Forces you to push out instead of turtling. |
| **Screamer** | Calls nearby zombies when it sees you | Turns a small fight into a big one – kill it first! |
| **Crawler** | Burrows under walls ❓ | Punishes pure wall-turtling. |
| **Swarm** | Tiny, fast, many, explodes on contact | Counters clumped armies (spread out!). |
| **Giant** (like TAB's) | Rare, huge, very slow, enormous HP, smashes through walls and buildings, hits units in an area | Appears in late waves and the final wave. A wall alone won't stop it – it needs the whole army. No other bosses. |

### 8.2 Waves

- **Ambient:** single zombies roam all the time.
- **Noise waves:** your noise attracts groups (see 8.3) – you cause these yourself.
- **Scripted waves:** at fixed times (e.g. minute 10, 18, 24) from a random but *announced* direction (30 s warning).
- **Final wave:** announced 5 minutes ahead, with direction. Everything, including giants.

### 8.3 Noise (Factorio's pollution × TAB's noise)

- Every machine, tower shot and explosion makes **noise**. Noise spreads over the map like Factorio's pollution cloud
  (per map chunk, spreads to neighbours, fades over time).
- Zombies and nests "drink" noise: when enough noise reaches them, they start moving towards its source.
- → Expanding production makes you stronger **and** more noticeable. Quiet tech (wind, solar, dampeners) becomes a real
  strategic choice.
- Noise overlay toggle (like the pollution map in Factorio) so the player can see it.

### 8.4 Creep (like StarCraft's, but for the zombies)

- **Nests** spread creep on the ground around them, slowly growing over the round.
- On creep: you can't build, your units are slowed, zombies regenerate.
- Burning it (flamethrowers, cleanser building) removes it. Destroying the nest stops the spread.
- Gives the army an offensive job instead of only defending.

---

## 9. Map generation

A mix of Factorio (noise-based terrain with resource patches) and TAB (hand-feeling regions with points of interest).

### 9.1 Steps

1. **Height + moisture noise** (Perlin/Simplex) → biomes: grassland, forest, rock, swamp, water, ruins.
2. **Start area:** guaranteed safe-ish zone with wood, stone, a small iron + coal patch and farmland nearby.
3. **Resource patches:** Factorio-style blobs, richer and larger the further from the start. Sometimes a rich patch
   right next to a nest (risk/reward).
4. **Chokepoints:** rivers, cliffs and forests create natural lanes – the map should have some places that are
   "obviously" good to wall off.
5. **Nests:** placed with minimum distance to the start, more of them towards the map edges.
6. **Points of interest** (TAB's villages): abandoned towns, crashed supply drops, old bunkers. Guarded by zombies,
   reward = gold, items, a free unit, a blueprint.
7. **Final wave direction** chosen at map creation (and maybe hinted at by where the big nests are).

### 9.2 Map sizes (first guess)

| Size | Tiles | Zombies at peak |
|---|---|---|
| Small | 128 × 128 | ~1,000 |
| Medium | 192 × 192 | ~3,000 |
| Large | 256 × 256 | ~6,000 |

- **Seeds:** every map has a seed; same seed = same map (good for sharing).
- **Fog of war:** unexplored (black) / explored but not visible (grey) / visible.

---

## 10. Home screen and meta progression

### 10.1 Home screen (TAB-like)

- A **world map** split into **regions** (each a biome with its own threats).
- Pick a region → **round setup screen**:
  - Map size, zombie density, final wave strength, time until final wave, starting resources.
  - Each setting changes the **score multiplier** (TAB's %). Higher difficulty = higher score.
- Buttons: *New round*, *Continue*, *Regions*, *Research*, *Records*, *Settings*.

### 10.2 Meta progression (like TAB, but without a campaign)

In TAB, research and unlocks belong to the campaign. Here they come from the **normal rounds**:

- **Research points** after every round. How many depends on the score (difficulty % × result), and a lost round
  gives a few too.
- They're spent in a persistent **research tree**, as in TAB's campaign: unlocking new units, buildings and upgrades
  for later rounds.
- **Regions unlock** like TAB's survival maps: win the previous region at ≥ a certain difficulty % (each region =
  new biome, new zombie type or mechanic).
- Records per region: best score, fastest win, highest difficulty.

### 10.3 Other modes

- **Endless** (would be nice): after the final wave the round keeps going, waves keep growing, and the score counts
  how long you last.
- **Co-op** ❓ (very expensive technically – decide early, see [open questions](#14-open-questions)).
- No campaign and no daily challenge planned.

---

## 11. UI and controls

### 11.1 Screen layout (StarCraft-style)

```
┌───────────────────────────────────────────────────────────────────┐
│ Gold 1250 (+40/min)     Iron 210  Energy +12  │ Final wave 12:40 │  ← top bar
│                                                                   │
│                                                                   │
│                          game view                                │
│                                                                   │
│                                                                   │
├──────────┬───────────────────────────────────────┬────────────────┤
│ minimap  │  selection (portraits / unit info)    │ command card   │
│ + noise  │                                       │ (abilities,    │
│ overlay  │                                       │  build menu)   │
└──────────┴───────────────────────────────────────┴────────────────┘
```

### 11.2 Keys (first draft)

| Key | Action |
|---|---|
| Left click / drag | Select / box select |
| Right click | Smart command (move, attack, gather, enter) |
| A, S, H, P | Attack-move, stop, hold, patrol |
| Q W E R | Abilities (command card grid) |
| B | Build menu |
| Ctrl + 1–0 / 1–0 | Set / select control group |
| Space | Pause (orders still possible) |
| F1–F4 | Camera bookmarks |
| Tab | Toggle noise / creep overlay |
| WASD / screen edge | Move camera |

### 11.3 Feedback

- Alerts with jump-to-location: *"Building under attack"*, *"House downgraded"*, *"Wave incoming from the west"*.
- Edge-of-screen arrows towards fights.
- Clear sound cues per event (important when hundreds of things happen at once).

---

## 12. Technical notes

### 12.1 The hard parts

| Problem | Why it's hard | Usual solution |
|---|---|---|
| **Thousands of zombies pathing to the base** | A* per zombie is far too slow | **Flow fields**: one field per target, computed once, every zombie just follows the arrows. |
| **Collisions between thousands of units** | Each vs. each = n² checks | **Spatial hash / grid**: only check neighbours in the same cell. |
| **Drawing thousands of sprites** | Many draw calls per frame | Sprite batching, cache rotated sprites (the cube game's sprite cache is the same idea), only draw what's on screen. |
| **Group movement that feels good** | Units bump into each other, clump, block corridors | Steering behaviours (separation, cohesion), formation offsets. |
| **Determinism** (for seeds, replays, co-op) | Floating point, random order | Fixed tick rate, own random generator with seed. |

### 12.2 Language: Rust or a C language ❓

No Python: thousands of zombies with collision and path-finding are exactly where Python reaches its limits (see the
cube game's README). It'll be **Rust or one of the C languages**, with my own engine on top of a thin library
(window, input, drawing, sound), like pygame-ce in the cube game. All four are fast enough for the horde.

| Language | Thin library (like pygame-ce) | Pro | Con |
|---|---|---|---|
| **Rust** | macroquad, SDL2 (`sdl2` crate), wgpu | Very fast, no crashes from memory bugs, `cargo` makes libraries and builds easy, ECS fits well (`hecs`, `bevy_ecs`) | Steepest learning curve: the borrow checker fights the usual "objects point at each other" game code, so think in data (ECS) from the start |
| **C++** | SDL2/SDL3, SFML, raylib | Industry standard, most game-dev tutorials and books, full control | Memory bugs crash or corrupt silently, build setup (CMake, libraries) is a pain on Windows |
| **C#** | Raylib-cs, MonoGame, SDL2-CS | Easiest of the four coming from Python, fast enough, great tools (Visual Studio/Rider), garbage collector | Garbage collector can cause small stutters if you create many objects per frame (avoid with pools/structs) |
| **C** | raylib, SDL2 | Simple language, raylib is made for learning | The most manual work: no classes, no generics, managing every allocation yourself |

**Decide before prototype step 1**, since the language affects everything after it. A good test is to build step 1 (unit
control) as a small throwaway prototype in your top two candidates.

**Toolbox connection:** the launcher currently starts `last_bastion.py`. With a compiled language the toolbox page
starts the built `.exe` instead. That's a small change in `last_bastion_gui.py` and `program.json`.

### 12.3 Graphics: the TAB look

TAB is **2D**: units and buildings are pictures drawn from 3D models (pre-rendered sprites), shown from a fixed,
tilted camera on a square grid. Any library that can draw many pictures quickly can do this, including **Raylib-cs**:

| Part of the look | How with raylib |
|---|---|
| Thousands of animated zombies | Sprite sheets in a few large **texture atlases**. raylib batches quads automatically, and as long as the texture doesn't change it draws tens of thousands per frame in a handful of draw calls. |
| Units facing any direction | Render 8 or 16 directions per animation (mirror left/right to save half). That's how TAB does it. |
| Depth (who's in front) | Sort by the y position at the feet before drawing (painter's algorithm). |
| Fog of war, light, night, fire glow | **Render textures** + **shaders** (GLSL): draw a light or visibility map, blend it over the world. |
| Muted, gritty colours | A colour-grading shader over the finished picture. |
| Particles (fire, blood, muzzle flash) | Own small particle system, drawn in the same batch. |
| UI | raygui exists but is basic. The StarCraft-style HUD (11.1) will mostly be custom-made. |

**The actual hard part is the art, not the code:** every unit needs its animations (walk, attack, die) × directions as
pictures. The usual way is to model and animate in **Blender**, then render all directions automatically into sprite
sheets with a script. That's a lot of pictures, but it's done once per unit, and placeholder art (coloured shapes, as in
the cube game) is enough for all prototypes.

**Performance:** 120 units + a few hundred colonists are negligible next to thousands of zombies. The horde decides
the performance, see 12.1.

### 12.4 Data-driven from the start

Like the cube game's `data/*.json`: units, zombies, buildings, recipes, waves and map settings live in JSON files, not in
code. Balancing then means editing numbers, not code.

---

## 13. Prototype roadmap

Riskiest and most fun-critical first. Each step should end in something playable.

| Step | Goal | Done when |
|---|---|---|
| **1. Unit control** | Select, control groups, move, attack-move, one ability, against a few dummy zombies | Moving 10 units *feels good* |
| **2. Horde stress test** | 2,000+ zombies flowing towards a point with flow fields + spatial hash | Stable 60 FPS |
| **3. Walls, towers, infection** | Build walls/towers on a grid, zombies attack them, infection spreads | A breach feels dangerous |
| **4. Machines and production chains** | Drill → colony stock → smelter → workshop, with power | A small chain runs by itself |
| **5. Houses, gold, upkeep** | Houses consume and pay gold, units cost upkeep, downgrade | Economy and army are linked |
| **6. Map generation** | Noise terrain, patches, nests, POIs, fog of war | Two seeds feel different |
| **7. Noise and creep** | Noise attracts waves, nests spread creep | Expanding is a real decision |
| **8. Full round** | Timeline from section 4, final wave, win/lose | A 30-minute round can be played start to finish |
| **9. Home screen and meta** | Regions, round setup, score %, research | The "one more round" feeling |
| **10. Polish** | Sounds, effects, alerts, balancing, tutorial | Someone else can play it without help |

---

## 14. Open questions

| # | Question | Options | Decision |
|---|---|---|---|
| 1 | Language? | Rust, C++, C# or C – own engine, no Python (12.2) | Before prototype step 1 |
| 2 | Perspective? | 2D top-down (Factorio) or isometric (TAB) | |
| 3 | Singleplayer only, or co-op later? | Co-op needs determinism / networking from the start | |
| 4 | Supply houses by belt or by radius? | Belts (deep) vs. warehouse radius (simple) | Radius around a market – no belts at all (2026-10-15) |
| 5 | Workers as units or invisible? | StarCraft-style workers vs. Factorio-style automatic | |
| 6 | Ammo as an item? | Adds logistics depth vs. more micromanagement | |
| 7 | Pause or slow-mo? | Full active pause (TAB) vs. 0.5× slow-mo | |
| 8 | Hero unit? | Yes (one per round, levels up) / no | |
| 9 | Save rule? | Free saving / one autosave (TAB) / both as options | |
| 10 | Meta progression: power or sidegrades? | | Like TAB: research tree with unlocks and upgrades (2026-10-15) |
| 11 | Final name? | *Last Bastion* is a working title | |
| 12 | Gold runs out? | Units fight worse (morale) / units desert / only no new purchases | Debt in stages: fight worse, then desert one by one at random, weighted towards expensive and non-veteran units (7.2, 2026-10-15) |

---

## 15. Idea parking lot

Ideas that don't serve a pillar yet, or are too big for now. Not deleted – parked.

- **Day/night cycle:** more zombies at night, lights cost energy but reduce danger.
- **Weather:** fog reduces sight, storms knock out solar.
- **Trains** for late-game logistics between distant ore fields.
- **Drones** that deliver items (late tech).
- **Refugees** arriving mid-round: accept them (more houses needed) or turn them away.
- **Infected refugees** – one of them might be a carrier. 😈
- **Mutations:** each round the horde gets a random modifier ("runners are faster", "brutes explode").
- **Map editor** like the one planned for the cube game (StarCraft 2 editor as a model).
- **Mod support** via the JSON data files.
- **Replays** (needs determinism, see 12.1).
- **Belts** (Factorio-style item transport): taken out on 2026-10-15, replaced by the colony stock (5.4).
- **Units from the first draft (taken out of the roster on 2026-10-15):**
  - *Scout*: fast, long sight, *Flare* reveals an area. Partly covered by the ranger now.
  - *Engineer*: repairs and builds in the field, deploys a temporary turret.
  - *Grenadier*: area burst with *Cluster grenade*.
  - *Hero*: one per round, levels up, 2–3 abilities (see open question 8).
