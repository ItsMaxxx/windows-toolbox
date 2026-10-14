# Spieldaten

Was hier liegt, ändert das Spiel, ohne dass Code angefasst werden muss. Die Dateien werden jedes Mal neu gelesen, wenn
das **Spielmenü** öffnet – ändern, speichern, ins Spielmenü wechseln, ausprobieren. Fehler (Tippfehler, ungültige
Werte) zeigt das Spielmenü rot an; das Spiel nimmt dann den Standardwert, statt abzustürzen.

| Datei | Inhalt |
|---|---|
| `enemies.json` | Standardwerte jedes Gegnertyps (diese Seite) |
| `upgrades.json` | Shop im Run (Sterne) und Karten-Shop im Spielmenü (Cores) – siehe unten |
| `buildings.json` | Gebäude, die man im Run setzt – bisher der Wachturm (siehe unten) |
| `radar.json` | der Radar aus dem Skilltree (siehe unten) |
| `difficulties/*.json` | eine Datei pro Schwierigkeit – Arena, Cores, Spawns und eigene Gegnerwerte (`difficulties/README.md`) |

## Woher ein Gegnerwert kommt

Wie im StarCraft-2-Editor, wo jede Map eigene Einheitenwerte haben kann – jede Schicht überschreibt die vorige:

1. `enemies.json` – der Standard (fehlt hier ein Wert, gilt der Notfallwert in der Klasse in `game/enemies/`)
2. `enemy_stats` in der Schwierigkeitsdatei – eigene Werte nur auf dieser Stufe
3. Buffs während eines Runs – zeitlich begrenzt, flach und/oder als Faktor (`game/enemies/buff.py`)

## `enemies.json`

Ein Eintrag pro Gegnertyp: `basic`, `charger`, `shooter`, `sniper`, `carrier`, `critter`, `artillery`, `shield`.
Zeiten in Sekunden, Strecken und Größen in Pixeln, Tempo in Pixeln pro Sekunde, Winkel in Grad.

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
| `contact_damage` | Schaden bei Berührung (0 = harmlos) |

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
| `shot_damage` / `shot_speed` / `shot_size` | der Schuss |

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
| `shot_damage` / `shot_speed` / `shot_size` | der Schuss |

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
| `blast_damage` | Schaden, wenn das Schiff beim Einschlag im Kreis ist |

**Shield** – hält einen großen Schild vor sich, dreht sich sehr langsam und läuft nur in Schildrichtung (kommt also
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

**`upgrades`** – ein Eintrag pro Wert, den man verbessern kann (`move_speed`, `damage`, `attack_speed`, `wall_push`,
`shot_speed` (Projectile speed), `dash_distance`, `dash_cooldown`, `rocket_damage`, `blast_radius`, `rocket_wall_push`,
`rocket_cooldown`, `vision`). Gilt für beides: eine Stufe im Shop während des Runs und eine Karte im Karten-Shop.

| Wert | Bedeutung |
|---|---|
| `amount` | so viel ändert eine Stufe im Shop (negativ bei Cooldowns) |
| `card_amount` | so viel ändert eine Karte aus dem Karten-Shop – meist mehr als eine Stufe |
| `price` | Sterne für die erste Stufe in einem Run … |
| `price_step` | … und so viele mehr für jede weitere Stufe desselben Werts (10, 15, 20, …) |

**`card_shop`** – der Karten-Shop im Spielmenü (Reiter *Cards*), bezahlt mit Cores. Ganze Zahlen.

| Wert | Bedeutung |
|---|---|
| `offers` | so viele Karten werden gleichzeitig angeboten |
| `first_price` | Cores für eine Karte, solange die Sammlung leer ist … |
| `price_step` | … und so viele mehr für jede Karte, die schon in der Sammlung ist |
| `reroll_price` | Cores für neue Angebote |
| `sell_refund` | Cores zurück beim Verkaufen (Rechtsklick auf eine Karte der Sammlung → *Sell*) |
| `max_owned` | so viele Karten passen in die Sammlung |
| `max_active` | so viele davon können aktiv sein – aktive Karten wirken zu Beginn jedes Runs aufs Schiff |

## `buildings.json`

**`watchtower`** – der Wachturm. Im Skilltree freischalten (*Watchtower*, jede Stufe +1 Turm gleichzeitig), im Run
mit **B** werfen: Er fliegt vom Schiff aus in Mausrichtung, auch aus dem Spielfeld hinaus, und öffnet dort ein eigenes
kleines Fenster, das diese Stelle dauerhaft zeigt. Gegner können ihn zerstören, dann schließt sich das Fenster.

| Wert | Bedeutung |
|---|---|
| `max_hp` | Lebenspunkte |
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
