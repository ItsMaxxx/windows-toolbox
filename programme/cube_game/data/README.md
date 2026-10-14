# Spieldaten

Was hier liegt, ändert das Spiel, ohne dass Code angefasst werden muss. Die Dateien werden jedes Mal neu gelesen, wenn
das **Spielmenü** öffnet – ändern, speichern, ins Spielmenü wechseln, ausprobieren. Fehler (Tippfehler, ungültige
Werte) zeigt das Spielmenü rot an; das Spiel nimmt dann den Standardwert, statt abzustürzen.

| Datei | Inhalt |
|---|---|
| `ships.json` | Grundwerte des Schiffs – und künftiger Schiffe (siehe unten) |
| `skilltree.json` | jeder Skilltree-Knoten: was er kostet und was eine Stufe bringt (siehe unten) |
| `enemies.json` | Standardwerte jedes Gegnertyps (diese Seite) |
| `shop.json` | was man im Run mit Sternen kauft: die Upgrades im Shop (T) und die Wachtürme (B) – siehe unten |
| `upgrades.json` | Karten-Shop im Spielmenü (Cores): was eine Karte bringt, Regeln des Shops – siehe unten |
| `weapons.json` | Grundwerte der Waffen – siehe unten |
| `abilities.json` | Grundwerte der Fähigkeiten: Dash und Rakete (siehe unten) |
| `buildings.json` | Gebäude, die man im Run setzt – bisher der Wachturm (siehe unten) |
| `radar.json` | Grundwerte des Radars aus dem Skilltree (siehe unten) |
| `difficulties/*.json` | eine Datei pro Level (A1 … B6, Survival) – Ziel, Arena, Cores, Spawns, Evolutionen und eigene Gegnerwerte (`difficulties/README.md`) |

## `ships.json`

Unter `ships` steht ein Eintrag pro Schiff, `ship` sagt, welches geflogen wird (eine Auswahl im Spielmenü gibt es noch
nicht). Ein neues Schiff ist einfach ein neuer Eintrag – Werte, die er weglässt, nimmt er vom eingebauten Standard
(`DEFAULTS` in `game/ship_data.py`):

```json
"ships": {
  "standard": { … },
  "tank": { "name": "Tank", "size": 40, "speed": 200, "max_energy": 160, "color": [60, 200, 90] }
}
```

Das sind die Grundwerte zu Beginn eines Runs – Skilltree, Shop und Karten kommen obendrauf.

| Wert | Bedeutung |
|---|---|
| `name` | Name des Schiffs |
| `size` | Kantenlänge (auch die Hitbox, ein Quadrat). Die Arena wird höchstens so klein – dann ist das Schiff zerquetscht |
| `speed` | Flugtempo in Pixeln pro Sekunde |
| `max_energy` | so viel Energie hat es (voll zu Beginn) – beide Waffen teilen sie, jeder Schuss kostet `energy_use` |
| `energy_regen` | so viel Energie kommt pro Sekunde zurück |
| `invulnerable_time` | nach einem Treffer so viele Sekunden unverwundbar (es blinkt) – höchstens `MAX_INVULNERABLE_TIME` (3 s, `settings.py`) |
| `armor` | Panzerung des Schiffs in Pixeln, flach: jeder Treffer quetscht die Arena so viel weniger (Basic 25 bei `armor` 9 → 16 px, Kanonenkugel 100 → 91) – stark gegen viele kleine Treffer. Mindestens `MIN_HIT_SHARE` (25 %, `settings.py`) eines Treffers bleibt |
| `magnet_radius` | so nah müssen Sterne und Cores sein, damit sie zum Schiff gezogen werden |
| `color` | Farbe als `[Rot, Grün, Blau]`, je 0 … 255 |

## `skilltree.json`

Ein Eintrag pro Knoten, alles an einer Stelle: was er kostet und was er bewirkt. Die anderen Dateien enthalten nur die
Grundwerte (ohne Upgrades).

```json
"gun_damage":     { "costs": [2, 3, 5], "per_level": 0.4 },
"burning_ground": { "costs": [15], "duration": 3, "damage_per_second": 1.5, "radius": 0.8 },
```

**`costs`** – die Cores für jede Stufe, als Liste. Die Länge der Liste ist die Zahl der Stufen: `[2, 3, 5]` = drei
Stufen für 2, 3 und 5 Cores, `[4]` = ein Knoten ohne Stufen. Ganze Zahlen, 0 = gratis.

**`per_level`** – so viel bringt **eine** Stufe; mit drei Stufen also das Dreifache. Negativ = weniger (z. B.
Energieverbrauch, Cooldown). Fehlt ein Wert oder ein ganzer Knoten, gilt der eingebaute.

| Knoten | `per_level` wirkt auf |
|---|---|
| `head_start` | Sterne zu Beginn jedes Runs |
| `bigger_arena` | `[breiter, höher]` in Pixeln |
| `core_luck` | Chance auf einen Core pro Kill (0.005 = +0,5 %) |
| `max_energy` / `energy_regen` | Energie des Schiffs / Energie pro Sekunde (Grundwerte in `ships.json`) |
| `armor` / `recovery` | den gleichnamigen Wert des Schiffs in `ships.json`: `armor` (px), `invulnerable_time` (s) |
| `gun_…`, `mg_…`, `cannon_…`, `laser_…` | den gleichnamigen Wert der Waffe in `weapons.json`: `damage`, `attack_speed`, `energy_use` (`…_energy`), `wall_push`, `projectile_speed` (`…_shot_speed`), `spread` (`mg_precision`), `piercing` (`cannon_piercing`) |
| `mg_attack_speed` / `mg_damage` | dazu `spread_per_level`: so viel Grad mehr Streuung pro Stufe |
| `dash_distance` / `dash_charges` | `distance` (px) / `charges` (Dashes auf Vorrat) des Dash (Grundwerte in `abilities.json`) |
| `rocket_cooldown` / `rocket_radius` / `rocket_damage` / `rocket_wall_push` | `cooldown` (s), `blast_radius` (px), `damage`, `wall_push` der Rakete (Grundwerte in `abilities.json`) |
| `watchtower` | so viele Türme mehr gleichzeitig |
| `card_slots` | so viele Karten mehr gleichzeitig aktiv (dazu `max_active` in `upgrades.json`) |
| `radar_size` / `radar_cooldown` / `radar_duration` | Fenstergröße (px) / Zeit zwischen Scans (s, negativ = öfter) / Dauer eines Scans (s) |

Knoten, die nur etwas freischalten (`shop`, `card_shop`, `dash`, `rocket`, `machine_gun`, `cannon`, `laser`, `radar`),
haben nur `costs`. **`burning_ground`** hat statt `per_level` die Werte des brennenden Bodens:

| Wert | Bedeutung |
|---|---|
| `duration` | so viele Sekunden brennt er |
| `damage_per_second` | Schaden pro Sekunde an jedem Gegner darin (in Stößen alle 0,5 s) |
| `radius` | sein Radius als Anteil des Explosionsradius (0.8 = 80 %) |

Die Beschreibungen von *Head start*, *Bigger arena*, *Core luck* und *Watchtower* und die Tooltips der Upgrades zeigen
die Werte aus dieser Datei.

Weniger Stufen als vorher: Ein Spielstand mit mehr gekauften Stufen zählt nur so viele, wie der Knoten jetzt hat –
gespeichert bleibt die alte Zahl, mit mehr Stufen ist sie wieder da. Ausgegebene Cores gibt es nicht zurück.

## Woher ein Gegnerwert kommt

Wie im StarCraft-2-Editor, wo jede Map eigene Einheitenwerte haben kann – jede Schicht überschreibt die vorige:

1. `enemies.json` – der Standard (fehlt hier ein Wert, gilt der Notfallwert in der Klasse in `game/enemies/`)
2. `enemy_stats` in der Level-Datei – eigene Werte nur auf diesem Level
3. Buffs während eines Runs – zeitlich begrenzt, flach und/oder als Faktor (`game/enemies/buff.py`)

## `enemies.json`

Ein Eintrag pro Gegnertyp: `basic`, `charger`, `shooter`, `sniper`, `carrier`, `critter`, `artillery` (Tier 1) und
ihre Evolutionen (Tier 2, mit dunklem Rahmen im Würfel): `fat` (aus Basic), `cannoneer` (aus Shooter), `shield` (aus
Charger), `laser` (aus Sniper), `cluster` (aus Artillery). Wann eine Evolution statt Tier 1 kommt, steht im Level
(`evolutions`).
Zeiten in Sekunden, Strecken und Größen in Pixeln, Tempo in Pixeln pro Sekunde, Winkel in Grad.

**Schaden ans Schiff ist in Pixeln** (`contact_damage`, `shot_damage`, `blast_damage`): So weit rücken die Kanten der
Arena bei einem Treffer im Schnitt ein – Breite und Höhe werden je um das Doppelte kleiner. Die Kanten weit weg vom
Schiff rücken mehr ein, die nahen weniger (`HIT_SIDE_BIAS` in `settings.py`). Zum Vergleich: ein Basic macht 25, die
Grundkanone schiebt eine Kante pro Schuss um 18 zurück. Wachtürme verlieren dieselbe Zahl an Lebenspunkten.

**Blickrichtung (Shooter, Sniper, Artillery, Shield):** Diese Gegner drehen sich mit begrenztem Tempo zum Schiff und
handeln nur nach vorne. Wer schnell genug um sie herumfliegt, entkommt ihnen.

| Wert | Bedeutung |
|---|---|
| `turn_speed` | so viele Grad pro Sekunde dreht er sich zum Schiff |
| `fire_cone` | schießt nur, wenn das Schiff in diesem Kegel vor ihm ist (ganzer Öffnungswinkel); der Schuss geht in Blickrichtung |

**Alle Typen**

| Wert | Bedeutung |
|---|---|
| `base_hp` | Lebenspunkte (ein Kästchen über dem Gegner pro Punkt) |
| `speed` | Lauftempo |
| `size` | Kantenlänge des Würfels (auch die Hitbox; Größere schieben Kleinere weg) |
| `contact_damage` | Schaden in Pixeln bei Berührung (0 = harmlos) |
| `armor` | Panzerung, flach (Standard 0): jeder Treffer des Spielers macht so viel weniger Schaden, mindestens `MIN_DAMAGE_SHARE` (15 %, `settings.py`) bleibt. Gun 2 gegen `armor` 1 → 1, Machine gun 1 → 0,15, Cannon 9 → 8. Gepanzert: Fat Guy, Shield, Cannoneer (1), Carrier, Artillery (0,5) |

**Charger**

| Wert | Bedeutung |
|---|---|
| `charge_range` | ab diesem Abstand zum Schiff holt er aus |
| `windup_time` | so lange zeigt die Warnlinie, wohin er stürmt |
| `charge_speed` / `charge_time` | Tempo und Dauer des Ansturms |
| `recover_time` | so lange steht er danach still |
| `charge_mass` | so viel schwerer ist er beim Ansturm (rammt andere weg) |

**Shooter**

| Wert | Bedeutung |
|---|---|
| `shooting_distance` | näher als das geht er nicht ran |
| `fire_range` | schießt, wenn das Schiff höchstens so weit weg ist |
| `fire_interval` | Sekunden zwischen zwei Schüssen |
| `turn_speed` / `fire_cone` | siehe oben |
| `shot_damage` / `shot_speed` / `shot_size` | der Schuss: Schaden in Pixeln, Tempo, Durchmesser |

**Sniper**

| Wert | Bedeutung |
|---|---|
| `preferred_distance` | Wunschabstand zum Schiff … |
| `close_in` / `back_off` | … geht näher ran, wenn er weiter als Wunsch + `close_in` weg ist, weicht zurück, wenn näher als Wunsch − `back_off` |
| `fire_range` | zielt, wenn das Schiff höchstens so weit weg ist (und im `fire_cone` vor ihm) |
| `turn_speed` | so schnell dreht sich der Laser mit |
| `aim_time` | so lange ist der Laser sichtbar … |
| `lock_time` | … davon die letzten Sekunden folgt er nicht mehr (der Moment zum Ausweichen) |
| `reload_time` | Pause nach dem Schuss |
| `shot_damage` / `shot_speed` / `shot_size` | der Schuss: Schaden in Pixeln, Tempo, Durchmesser |

**Carrier**

| Wert | Bedeutung |
|---|---|
| `preferred_distance` / `close_in` / `back_off` | Abstand halten wie beim Sniper |
| `spawn_range` | setzt Critter aus, wenn das Schiff höchstens so weit weg ist |
| `spawn_interval` | Sekunden zwischen zwei Mal Aussetzen |
| `max_critters` | so viele dürfen pro Carrier gleichzeitig leben |
| `first_wave` | so viele kommen beim ersten Mal auf einmal … |
| `spawn_amount` | … und so viele jedes weitere Mal (nie mehr, als bis `max_critters` Platz ist) |

**Artillery** – läuft auf das Schiff zu. Sobald sie einmal ganz in einem Fenster war (Spielfeld, Turm- oder
Radarfenster) und das Schiff zwischen `min_range` und `fire_range` ist, baut sie auf: Die Füße fahren aus, ab da
bewegt sie sich nicht mehr (auch nicht durch andere Gegner). Kommt das Schiff näher als `min_range` oder geht es aus
der Reichweite, baut sie ab (rückwärts) und läuft wieder – bei zu wenig Abstand von dir weg.

Sie ist ein Katapult: Der Arm liegt hinten, mit einer Granate in der Schale. Beim Schuss schwingt er nach vorn
(`swing_time`), lässt oben los und schlägt gegen den Querbalken; während des Nachladens kurbelt sie ihn zurück. Die
Granate fliegt sichtbar im Bogen (mit Schatten am Boden) – solange füllt sich der rote Kreis am Ziel. Höhe wird von
oben gesehen so gezeigt, dass die Granate weiter oben auf dem Bildschirm gezeichnet wird.

| Wert | Bedeutung |
|---|---|
| `fire_range` | baut höchstens in diesem Abstand auf (wenn schon gesehen) und feuert … |
| `min_range` | … und mindestens in diesem; näher: abbauen und zurückweichen |
| `setup_time` / `pack_time` | Sekunden zum Aufbauen (dann sofort schussbereit) / Abbauen |
| `turn_speed` / `fire_cone` | siehe oben – das Katapult dreht sich zum Schiff |
| `reload_time` | Sekunden zwischen zwei Schüssen |
| `fill_time` | so viele Sekunden fliegt die Granate – so lange füllt sich der rote Kreis (die Warnung) |
| `aim_spread` | der Kreis landet zufällig bis zu so weit neben dem Schiff (0 = genau auf das Schiff) |
| `blast_radius` | Radius des Kreises |
| `blast_damage` | Schaden in Pixeln, wenn das Schiff beim Einschlag im Kreis ist |
| `swing_time` | Sekunden, die der Arm zum Vorschwingen braucht (die Granate fliegt los, wenn er senkrecht steht) |
| `arc_height` | **Flugbahn:** so viele Pixel steigt die Granate am höchsten Punkt … |
| `arc_steepness` | … plus so viele pro Pixel Wurfweite (0.15: ein Wurf über 600 px steigt 90 px höher) |
| `arc_peak` | wo auf dem Weg sie am höchsten ist: 0.5 in der Mitte, kleiner = steil hoch und lang herab, größer = flach hoch und steil herab (0.05 … 0.95) |
| `shell_size` | Durchmesser der Granate in Pixeln (in der Luft etwas größer) |

**Cluster** – die Evolution der Artillery: dunkler, mehr HP, gepanzert. Baut auf und wirft genau wie die Artillery
(dieselben Werte, auch die Flugbahn), aber eine **Splittergranate**: Wo sie aufkommt, schadet sie nicht selbst (nur ein
dünner Ring zeigt die Stelle) – sie platzt in `split_count` Splitter, die weit auseinanderspringen, jeder mit einem
eigenen kleinen roten Kreis, der sich füllt, solange er fliegt. `blast_radius` und `blast_damage` hat sie nicht.

| Wert | Bedeutung |
|---|---|
| `split_count` | so viele Splitter (gleichmäßig rundherum, etwas zufällig verdreht) |
| `split_spread` / `split_min_spread` | jeder landet höchstens / mindestens so weit von der Aufschlagstelle |
| `split_radius` | Radius des Kreises eines Splitters |
| `split_damage` | Schaden in Pixeln, wenn das Schiff im Kreis eines Splitters ist |
| `split_time` | Sekunden, die ein Splitter fliegt (so lange füllt sich sein Kreis) |
| `split_arc_height` | so hoch springt ein Splitter |

**Fat Guy** – die Evolution des Basic: nur die vier Grundwerte (größer, viel mehr HP), sonst wie ein Basic.

**Cannoneer** – die Evolution des Shooters: verhält sich wie ein Shooter, aber sehr langsam und mit einer riesigen
Kanonenkugel, die langsam fliegt und massiv Schaden macht. Dieselben Werte wie beim Shooter (`shooting_distance`,
`fire_range`, `fire_interval`, `turn_speed`, `fire_cone`, `shot_damage`, `shot_speed`, `shot_size`).

**Laser** – die Evolution des Snipers: zielt wie ein Sniper (dieselben Werte außer `shot_speed`/`shot_size`), die
Linie ist dicker. Statt einer Kugel feuert er einen Strahl entlang der Linie; wer ihn berührt, solange er an ist, nimmt
Schaden (einmal pro Strahl). Solange der Strahl an ist, bewegt und dreht er sich nicht. Stirbt er, erlischt der Strahl.

| Wert | Bedeutung |
|---|---|
| `shot_damage` | Schaden in Pixeln, wenn der Strahl das Schiff (oder einen Wachturm) berührt |
| `beam_time` | so viele Sekunden ist der Strahl an |
| `beam_width` | Dicke des Strahls in Pixeln |

**Shield** – die Evolution des Chargers: hält einen großen Schild vor sich, dreht sich sehr langsam und läuft nur in Schildrichtung (kommt also
im Bogen). Der Schild blockt Kugeln von vorne (mit Funken, ohne Wand-Push), Explosionen treffen ihn von jeder Seite.
Ist das Schiff vor dem Schild und nah genug, lädt er auf (Warnlinie) und stürmt mit dem Schild voran – wie ein
stärkerer Charger.

| Wert | Bedeutung |
|---|---|
| `turn_speed` | Drehtempo in Grad pro Sekunde (langsam) |
| `shield_width` | Länge des Schilds quer vor dem Körper |
| `shield_arc` | Kugeln, die den Körper aus diesem Kegel von vorne treffen, blockt er auch |
| `dash_range` / `dash_cone` | lädt auf, wenn das Schiff höchstens so weit weg und in diesem Kegel vor ihm ist |
| `windup_time` | so lange zeigt die Warnlinie, wohin er stürmt |
| `dash_speed` / `dash_time` | Tempo und Dauer des Ansturms |
| `recover_time` | so lange steht er danach still – der Moment, um ihn zu umfliegen |
| `dash_mass` | so viel schwerer ist er beim Ansturm |
| `knockback` / `stun_time` | trifft der Ansturm das Schiff: so viele Pixel Rückstoß und so viele Sekunden betäubt (nicht bewegen, schießen, Fähigkeiten) |

## `shop.json`

Alles, was man während eines Runs mit Sternen kauft.

**`upgrades`** – ein Eintrag pro Zeile im Shop (T), die Leerzeilen in der Datei trennen die Abschnitte:

| Abschnitt | Einträge |
|---|---|
| Ship | `move_speed`, `max_energy`, `energy_regen`, `armor`, `recovery`, `magnet` |
| jede Waffe | `gun_…`, `mg_…`, `cannon_…`, `laser_…` mit `damage`, `attack_speed`, `wall_push`, `shot_speed` (Projectile speed), z. B. `mg_damage` |
| Dash | `dash_distance`, `dash_cooldown` |
| Rocket | `rocket_damage`, `rocket_blast_radius`, `rocket_wall_push`, `rocket_cooldown` |
| Watchtower | `watchtower_vision` |

Eine Waffe steht nur im Shop, wenn sie ausgerüstet ist, Dash, Rocket und Watchtower erst, wenn freigeschaltet.

| Wert | Bedeutung |
|---|---|
| `amount` | genau so viel ändert eine Stufe (negativ bei Cooldowns) – bei Waffen ohne `upgrade_factor` |
| `price` | Sterne für die erste Stufe in einem Run … |
| `price_step` | … und so viele mehr für jede weitere Stufe desselben Werts (10, 15, 20, …) |

Fehlt ein Eintrag, gilt der eingebaute Wert (bei Waffen der allgemeine mal ihr `upgrade_factor`). Alte Namen wie
`damage` oder `blast_radius` ignoriert das Spiel – das Spielmenü sagt, wie sie jetzt heißen.

**`watchtower`** – die Wachtürme (B):

| Wert | Bedeutung |
|---|---|
| `price` | Sterne für den ersten Turm eines Runs … |
| `price_step` | … und so viele mehr für jeden weiteren |

## `upgrades.json`

**`upgrades`** – pro Kartentyp nur **`card_amount`**: so viel ändert eine Karte aus dem Karten-Shop – meist mehr als
eine Stufe im Shop. Die Namen sind die Kartentypen (`damage`, `blast_radius`, `vision` …, nicht die Shop-Einträge): Die
Waffenkarten gibt es zwar pro Waffe (*Cannon: Damage*, wirkt nur, solange die Cannon in einem Slot ist), ihr Wert steht
aber einmal hier und gilt für jede Waffe mal deren `upgrade_factor` (`weapons.json`). Steht hier noch `amount`, `price`
oder `price_step`, wird es ignoriert (das Spielmenü sagt, dass es in `shop.json` gehört).

**`card_shop`** – der Karten-Shop im Spielmenü (Reiter *Cards*), bezahlt mit Cores. Ganze Zahlen. Den Reiter gibt
es erst, wenn der Skilltree-Knoten *Card shop* gekauft ist – vorher wirken auch aktive Karten nicht.

| Wert | Bedeutung |
|---|---|
| `offers` | so viele Karten werden gleichzeitig angeboten |
| `first_price` | Cores für eine Karte, solange die Sammlung leer ist … |
| `price_step` | … und so viele mehr für jede Karte, die schon in der Sammlung ist |
| `reroll_price` | Cores für neue Angebote |
| `sell_refund` | Cores zurück beim Verkaufen (Rechtsklick auf eine Karte der Sammlung → *Sell*) |
| `max_owned` | so viele Karten passen in die Sammlung |
| `max_active` | so viele davon können aktiv sein (der Skilltree-Knoten *Card slots* gibt mehr) – aktive Karten wirken zu Beginn jedes Runs aufs Schiff |

## `weapons.json`

Ein Abschnitt pro Waffe (`gun`, `machine_gun`, `cannon`, `laser`) – die Grundwerte; was die
Skilltree-Upgrades dazugeben, steht in `skilltree.json`. Welche Waffe in welchem Slot liegt, wählt man im Spielmenü
(Reiter *Loadout*); freigeschaltet werden sie im Skilltree (die Gun ist immer da).

Beide Waffen teilen sich die Energie des Schiffs (`max_energy`, `energy_regen` in `ships.json`). Jeder Schuss kostet
`energy_use`, sie lädt ständig nach. Ist sie leer, schießen die Waffen nur noch so schnell, wie sie nachlädt.

**Jede Waffe**

| Wert | Bedeutung |
|---|---|
| `damage` | Schaden pro Schuss |
| `attack_speed` | Schüsse pro Sekunde |
| `projectile_speed` / `projectile_size` | Tempo (px/s) und Durchmesser (px) der Schüsse |
| `wall_push` | so viele Pixel schiebt ein Schuss die Wand, die er trifft |
| `energy_use` | Energie pro Schuss |
| `upgrade_factor` | wie stark Karten aus dem Karten-Shop bei dieser Waffe wirken (die Shop-Stufen haben eigene Einträge in `shop.json`), pro Karte (`damage`, `attack_speed`, `wall_push`, `projectile_speed`; fehlt einer, gilt 1). Die Karten geben jeder Waffe denselben Wert – eine Waffe mit vielen winzigen Schüssen braucht daher einen kleinen Faktor. |

**Eigene Werte**

| Waffe | Wert | Bedeutung |
|---|---|---|
| `machine_gun` | `spread` | Streuung in Grad (ganzer Kegel) |
| `cannon` | `piercing` | durch so viele Gegner fliegt ein Schuss (voller Schaden), am nächsten bleibt er hängen |
| `cannon` | `pierced_push` | erreicht er danach die Wand, schiebt er nur noch so viel davon – pro durchbohrtem Gegner (0.5: halb, dann ein Viertel …) |
| `laser` | – | sieht aus wie ein Dauerstrahl, sind aber `attack_speed` winzige Schüsse pro Sekunde; alle Werte gelten pro Schuss (Inventar und Loadout zeigen sie pro Sekunde) |

## `abilities.json`

Die Fähigkeiten in den beiden Slots: `dash` (Shift) und `rocket` (Leertaste). Beide schaltet man im Skilltree frei; was
dessen Upgrades dazugeben, steht in `skilltree.json`, was Shop-Stufen bringen, in `shop.json`, was Karten bringen, in `upgrades.json`.

| Wert | Bedeutung |
|---|---|
| `cooldown` | Sekunden, bis die Fähigkeit wieder bereit ist (mit mehreren Ladungen: bis eine Ladung zurück ist) … |
| `min_cooldown` | … nie kürzer als das, egal wie viele Upgrades und Karten |

**`dash`** – ein kurzer Sprung in Laufrichtung (im Stand: zur Maus). Durch Wände kommt man nicht.

| Wert | Bedeutung |
|---|---|
| `distance` | so viele Pixel weit |
| `duration` | so viele Sekunden dauert der Sprung (kleiner = schneller) |
| `charges` | so viele Dashes auf Vorrat (Standard 1, der Skilltree-Knoten *Charges* gibt mehr): jeder Dash nimmt eine Ladung, der `cooldown` füllt eine nach der anderen wieder auf. Ein neuer Dash geht erst, wenn der vorige vorbei ist |

**`rocket`** – fliegt dorthin, wo die Maus beim Abschuss war, und explodiert dort. Der brennende Boden (*Burning
ground*) steht in `skilltree.json`.

| Wert | Bedeutung |
|---|---|
| `damage` | Schaden an jedem Gegner im Explosionsradius |
| `blast_radius` | Radius der Explosion in Pixeln |
| `wall_push` | so weit schiebt die Explosion jede Kante in ihrem Radius |
| `speed` / `acceleration` | Tempo beim Abschuss (px/s), plus so viel pro Sekunde Flugzeit |
| `size` | Durchmesser der Rakete in Pixeln |

## `buildings.json`

**`watchtower`** – der Wachturm. Im Skilltree freischalten (*Watchtower*, jede Stufe +1 Turm gleichzeitig), im Run
mit **B** werfen: Er fliegt vom Schiff aus in Mausrichtung, auch aus dem Spielfeld hinaus, und öffnet dort ein eigenes
kleines Fenster, das diese Stelle dauerhaft zeigt. Gegner können ihn zerstören, dann schließt sich das Fenster.

| Wert | Bedeutung |
|---|---|
| `base_hp` | Lebenspunkte – in derselben Einheit wie der Schaden der Gegner (Pixel): 150 = sechs Berührungen eines Basic (je 25). Über dem Turm ein Lebensbalken |
| `size` | Kantenlänge des Turms (auch die Hitbox; Gegner werden aus ihm herausgeschoben, er selbst bewegt sich nie) |
| `vision` | Kantenlänge seines Fensters in Pixeln (Upgrade *Vision* im Shop und als Karte macht es größer) |
| `throw_range` | so weit fliegt er vom Schiff weg |
| `throw_time` | Sekunden in der Luft |
| `hit_cooldown` | nach einem Treffer so viele Sekunden unverwundbar |
| `lure_range` | Nahkampf-Gegner (Basic, Charger, Critter) in diesem Umkreis, die näher am Turm als am Schiff sind, greifen den Turm an |

Was ihm schadet: berührende Gegner (ihr `contact_damage`), gegnerische Schüsse, Artillerie-Einschläge.

Überlappt oder berührt sein Fenster das Spielfeld, fliegen deine Schüsse durch die Kante hinein und treffen Gegner
darin. Trifft ein Schuss dort nichts, schiebt er beim Verlassen des Turmfensters die Kante, die er überquert hat. Das
Turmfenster liegt über dem Spielfenster. Außerhalb des Spielfelds ist sein Hintergrund fast schwarz mit einem Hauch
Grau. Der Rahmen läuft um alle Fenster zusammen: Wo Turmfenster und Spielfeld sich treffen, verschmelzen ihre Kanten
zu einer Linie mit Knick.

## `radar.json`

Der Radar (Skilltree *Radar* unter *Watchtower*, darunter *Scan size*, *Scan rate*, *Scan time*) arbeitet von selbst:
Alle `cooldown` Sekunden sucht er die größte Gegnergruppe außerhalb deiner Sicht (nicht im Spielfeld, nicht in einem
Turmfenster) und öffnet darüber für `duration` Sekunden ein Fenster – Hintergrund fast schwarz mit einem Hauch Blau,
Rahmen wie beim Turmfenster. Ist
draußen kein Gegner, schaut er jede Sekunde wieder. Solange es offen ist, fliegen Schüsse hinein wie in ein Turmfenster.

| Wert | Bedeutung |
|---|---|
| `size` | Kantenlänge des Fensters in Pixeln |
| `cooldown` | Sekunden vom Ende eines Scans bis zum nächsten … |
| `min_cooldown` | … nie kürzer als das, auch mit *Scan rate* |
| `duration` | Sekunden, die ein Scan offen bleibt |

Was *Scan size*, *Scan rate* und *Scan time* pro Stufe dazugeben, steht in `skilltree.json`.
