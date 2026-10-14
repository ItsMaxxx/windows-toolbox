# Spieldaten

Was hier liegt, ändert das Spiel, ohne dass Code angefasst werden muss. Die Dateien werden jedes Mal neu gelesen, wenn
das **Spielmenü** öffnet – ändern, speichern, ins Spielmenü wechseln, ausprobieren. Fehler (Tippfehler, ungültige
Werte) zeigt das Spielmenü rot an; das Spiel nimmt dann den Standardwert, statt abzustürzen.

| Datei | Inhalt |
|---|---|
| `enemies.json` | Standardwerte jedes Gegnertyps (diese Seite) |
| `upgrades.json` | Shop im Run (Sterne) und Karten-Shop im Spielmenü (Cores) – siehe unten |
| `weapons.json` | Waffen, Energie und Rakete: Grundwerte und was jede Skilltree-Stufe bringt – siehe unten |
| `buildings.json` | Gebäude, die man im Run setzt – bisher der Wachturm (siehe unten) |
| `radar.json` | der Radar aus dem Skilltree (siehe unten) |
| `difficulties/*.json` | eine Datei pro Level (A1 … B6, Survival) – Ziel, Arena, Cores, Spawns, Evolutionen und eigene Gegnerwerte (`difficulties/README.md`) |

## Woher ein Gegnerwert kommt

Wie im StarCraft-2-Editor, wo jede Map eigene Einheitenwerte haben kann – jede Schicht überschreibt die vorige:

1. `enemies.json` – der Standard (fehlt hier ein Wert, gilt der Notfallwert in der Klasse in `game/enemies/`)
2. `enemy_stats` in der Level-Datei – eigene Werte nur auf diesem Level
3. Buffs während eines Runs – zeitlich begrenzt, flach und/oder als Faktor (`game/enemies/buff.py`)

## `enemies.json`

Ein Eintrag pro Gegnertyp: `basic`, `charger`, `shooter`, `sniper`, `carrier`, `critter`, `artillery` (Tier 1) und
ihre Evolutionen (Tier 2, mit dunklem Rahmen im Würfel): `fat` (aus Basic), `cannoneer` (aus Shooter), `shield` (aus
Charger), `laser` (aus Sniper). Wann eine Evolution statt Tier 1 kommt, steht im Level (`evolutions`).
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
| `max_hp` | Lebenspunkte (ein Kästchen über dem Gegner pro Punkt) |
| `speed` | Lauftempo |
| `size` | Kantenlänge des Würfels (auch die Hitbox; Größere schieben Kleinere weg) |
| `contact_damage` | Schaden in Pixeln bei Berührung (0 = harmlos) |

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
| `spawn_interval` | Sekunden zwischen zwei Crittern |
| `max_critters` | so viele dürfen pro Carrier gleichzeitig leben |
| `first_wave` | so viele kommen beim ersten Mal auf einmal |

**Artillery** – läuft auf das Schiff zu. Sobald sie einmal ganz in einem Fenster war (Spielfeld, Turm- oder
Radarfenster) und das Schiff zwischen `min_range` und `fire_range` ist, baut sie auf: Die Füße fahren aus, ab da
bewegt sie sich nicht mehr (auch nicht durch andere Gegner). Kommt das Schiff näher als `min_range` oder geht es aus
der Reichweite, baut sie ab (rückwärts) und läuft wieder – bei zu wenig Abstand von dir weg.

| Wert | Bedeutung |
|---|---|
| `fire_range` | baut höchstens in diesem Abstand auf (wenn schon gesehen) und feuert … |
| `min_range` | … und mindestens in diesem; näher: abbauen und zurückweichen |
| `setup_time` / `pack_time` | Sekunden zum Aufbauen (dann sofort schussbereit) / Abbauen |
| `turn_speed` / `fire_cone` | siehe oben – der Lauf dreht sich zum Schiff |
| `reload_time` | Sekunden zwischen zwei Schüssen |
| `fill_time` | so lange füllt sich der rote Kreis, bevor es einschlägt (die Warnung) |
| `aim_spread` | der Kreis landet zufällig bis zu so weit neben dem Schiff (0 = genau auf das Schiff) |
| `blast_radius` | Radius des Kreises |
| `blast_damage` | Schaden in Pixeln, wenn das Schiff beim Einschlag im Kreis ist |

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

## `upgrades.json`

**`upgrades`** – ein Eintrag pro Wert, den man verbessern kann (`move_speed`, `max_energy`, `energy_regen`, `damage`, `attack_speed`, `wall_push`,
`shot_speed` (Projectile speed), `dash_distance`, `dash_cooldown`, `rocket_damage`, `blast_radius`, `rocket_wall_push`,
`rocket_cooldown`, `vision`). Gilt für beides: eine Stufe im Shop während des Runs und eine Karte im Karten-Shop.

| Wert | Bedeutung |
|---|---|
| `amount` | so viel ändert eine Stufe im Shop (negativ bei Cooldowns) |
| `card_amount` | so viel ändert eine Karte aus dem Karten-Shop – meist mehr als eine Stufe |
| `price` | Sterne für die erste Stufe in einem Run … |
| `price_step` | … und so viele mehr für jede weitere Stufe desselben Werts (10, 15, 20, …) |

**`card_shop`** – der Karten-Shop im Spielmenü (Reiter *Cards*), bezahlt mit Cores. Ganze Zahlen. Erst
nutzbar, wenn der Skilltree-Knoten *Card shop* gekauft ist – vorher wirken auch aktive Karten nicht.

| Wert | Bedeutung |
|---|---|
| `offers` | so viele Karten werden gleichzeitig angeboten |
| `first_price` | Cores für eine Karte, solange die Sammlung leer ist … |
| `price_step` | … und so viele mehr für jede Karte, die schon in der Sammlung ist |
| `reroll_price` | Cores für neue Angebote |
| `sell_refund` | Cores zurück beim Verkaufen (Rechtsklick auf eine Karte der Sammlung → *Sell*) |
| `max_owned` | so viele Karten passen in die Sammlung |
| `max_active` | so viele davon können aktiv sein – aktive Karten wirken zu Beginn jedes Runs aufs Schiff |

## `weapons.json`

Ein Abschnitt pro Waffe (`gun`, `machine_gun`, `cannon`, `laser`), dazu `energy` und `rocket`. Welche Waffe in welchem
Slot liegt, wählt man im Spielmenü (Reiter *Loadout*); freigeschaltet werden sie im Skilltree (die Gun ist immer da).

**`energy`** – beide Waffen teilen sich die Energie des Schiffs. Jeder Schuss kostet Energie, sie lädt ständig nach.
Ist sie leer, schießen die Waffen nur noch so schnell, wie sie nachlädt (keine Sperre).

| Wert | Bedeutung |
|---|---|
| `max` | so viel Energie hat das Schiff (voll zu Beginn) |
| `regen` | so viel kommt pro Sekunde zurück |
| `tree` | was eine Stufe der Skilltree-Knoten *Max energy* (`max`) und *Energy regen* (`regen`) dazugibt |

**Jede Waffe**

| Wert | Bedeutung |
|---|---|
| `damage` | Schaden pro Schuss |
| `attack_speed` | Schüsse pro Sekunde |
| `projectile_speed` / `projectile_size` | Tempo (px/s) und Durchmesser (px) der Schüsse |
| `wall_push` | so viele Pixel schiebt ein Schuss die Wand, die er trifft |
| `energy_use` | Energie pro Schuss |
| `tree` | was eine Stufe ihrer Skilltree-Upgrades dazugibt (negativ = weniger, z. B. `energy_use`) |
| `upgrade_factor` | wie stark Shop-Stufen und Karten bei dieser Waffe wirken, pro Karte (`damage`, `attack_speed`, `wall_push`, `projectile_speed`; fehlt einer, gilt 1). Die Karten geben jeder Waffe denselben Wert – eine Waffe mit vielen winzigen Schüssen braucht daher einen kleinen Faktor. |

**Eigene Werte**

| Waffe | Wert | Bedeutung |
|---|---|---|
| `machine_gun` | `spread` | Streuung in Grad (ganzer Kegel); `tree.spread` ist das Upgrade *Precision* (negativ) |
| `machine_gun` | `spread_per_upgrade` | so viel Streuung kommt mit jeder Skilltree-Stufe *Damage* und *Attack speed* dazu |
| `cannon` | `piercing` | durch so viele Gegner fliegt ein Schuss (voller Schaden), am nächsten bleibt er hängen |
| `cannon` | `pierced_push` | erreicht er danach die Wand, schiebt er nur noch so viel davon – pro durchbohrtem Gegner (0.5: halb, dann ein Viertel …) |
| `laser` | – | sieht aus wie ein Dauerstrahl, sind aber `attack_speed` winzige Schüsse pro Sekunde; alle Werte gelten pro Schuss (Inventar und Loadout zeigen sie pro Sekunde) |

**`rocket`** – `cooldown`, `damage`, `blast_radius`, `wall_push` wie oben; `tree` für die vier Raketen-Upgrades im
Skilltree. `burning` ist der Knoten *Burning ground*: Die Explosion hinterlässt brennenden Boden.

| Wert | Bedeutung |
|---|---|
| `burning.duration` | so viele Sekunden brennt er |
| `burning.damage_per_second` | Schaden pro Sekunde an jedem Gegner darin (in Stößen alle 0,5 s) |
| `burning.radius` | sein Radius als Anteil des Explosionsradius (0.8 = 80 %) |

## `buildings.json`

**`watchtower`** – der Wachturm. Im Skilltree freischalten (*Watchtower*, jede Stufe +1 Turm gleichzeitig), im Run
mit **B** werfen: Er fliegt vom Schiff aus in Mausrichtung, auch aus dem Spielfeld hinaus, und öffnet dort ein eigenes
kleines Fenster, das diese Stelle dauerhaft zeigt. Gegner können ihn zerstören, dann schließt sich das Fenster.

| Wert | Bedeutung |
|---|---|
| `max_hp` | Lebenspunkte – in derselben Einheit wie der Schaden der Gegner (Pixel): 150 = sechs Berührungen eines Basic (je 25). Über dem Turm ein Lebensbalken |
| `size` | Kantenlänge des Turms (auch die Hitbox; Gegner werden aus ihm herausgeschoben, er selbst bewegt sich nie) |
| `vision` | Kantenlänge seines Fensters in Pixeln (Upgrade *Vision* im Shop und als Karte macht es größer) |
| `throw_range` | so weit fliegt er vom Schiff weg |
| `throw_time` | Sekunden in der Luft |
| `price` | Sterne für den ersten Turm eines Runs … |
| `price_step` | … und so viele mehr für jeden weiteren |
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
| `size` | Kantenlänge des Fensters in Pixeln … |
| `size_per_level` | … plus so viel pro Stufe *Scan size* |
| `cooldown` | Sekunden vom Ende eines Scans bis zum nächsten … |
| `cooldown_per_level` | … plus so viel pro Stufe *Scan rate* (negativ = öfter) … |
| `min_cooldown` | … aber nie kürzer als das |
| `duration` | Sekunden, die ein Scan offen bleibt … |
| `duration_per_level` | … plus so viel pro Stufe *Scan time* |
