# Levels

Jede `.json`-Datei hier ist ein Level (im Code heißen sie noch „difficulty“). Der Dateiname (ohne `.json`) ist sein
Schlüssel: Er steht im Spielstand und in `unlock.requires` anderer Levels – darum Dateien nicht einfach umbenennen.

**Aufbau:** A1 bis A6 führen nach und nach alle Tier-1-Gegner und Ereignisse ein, jedes mit eigenem Schwerpunkt
(A2 Nahkampf, A3 Fernkampf, A4 Artillerie und Carrier, A5 harte Wände, A6 alles). B1 bis B6 bringen die
**Evolutionen** (Tier 2) dazu, immer wahrscheinlicher (B1 Fat Guy und Cannoneer, B2 Shield, B3 Laser, B6 alles).
C1 bis C6 haben **nur noch Evolutionen** (direkt in `enemies`, ohne `evolutions`) und die neuen Gegner, jedes mit einem
Thema: C1 Commander, C2 Blitz (Shields, schnelle Wände), C3 Pusher, C4 atmende Arena, C5 Gefahren draußen (Totem, Nest,
Sturm) und Living Windows, C6 Chaos (alles, Zufallswellen alle 40 s).
Wer B6 schafft, schaltet C1 und **Survival** frei: endlos, erst Basics, dann alle Typen, ab 4:00 die Evolutionen, ab
7:00 Commander, Pusher und Living Windows, ab 8:00 Gefahren.

**Start:** Jedes Level beginnt sofort: erster Gegner nach 0,5 s (`first_spawn`) und als erste Phase 0–20 s ohne
Ansage `{ "spawn": { "basic": 4 }, "spawn_interval": "x0.5" }` – vier Basics gleich zu Beginn, dann halbe Abstände.
Ohne sie war in den ersten 30 s nur 17–45 % der Zeit ein Gegner im Fenster, mit ihr etwa 70 %.

**Cores:** `core_chance` ist so gewählt, dass ein Run bis zum `goal` etwa 12 Cores (A1) bis 95 Cores (B6) und weiter
bis etwa 155 (C6) bringt, gleichmäßig steigend – A1 0.18, A2 0.10, A3–A5 um 0.08, A6 0.06, B1–B4 um 0.07, B5 0.06,
B6 0.055, Survival 0.05. Spätere Level haben viel mehr Gegner, darum eine kleinere Chance. Wer mehr Gegner einbaut,
senkt die Chance mit. Die C-Level haben wieder eine größere (C1 0.2, C2 0.25, C3 0.2, C4 0.19, C5 0.18, C6 0.13): Ihre
Gegner sind zäh, bis zum Ziel sterben nur 400–1100 statt über 2000 wie in B6.

**Finale:** Jedes Level mit Ziel endet mit zwei Phasen, die genau beim `goal` aufhören – *Final wave!* (30–40 s vorher:
ein Schub Gegner, kürzere Abstände, mehr starke Typen – in A1–A6 nur Tier 1, in B1–B6 viele Evolutionen) und *Hold on!*
(15–20 s vorher: noch ein Schub; ab A4 dazu härtere Treffer, schnellere oder härtere Wände).

**Mit der Zeit:** Mehr HP, härtere Treffer und härtere Wände kommen als **periodische** Phasen (`every`): z. B. ab 2:00
alle 2:00 +1 HP. Sie laufen nach dem Ziel einfach weiter. Dazu hat jedes Level **nach dem Ziel** eine Zufallswelle alle
45 s (`one_of` aus den Wellen des Levels), atmet alle 80 s ein (`breathe`) und ab B1 kommt alle 2 Minuten eine
Gefahr (Totem, Nest oder Sturm). Mittendrin würfeln die meisten Level eine ihrer Wellen aus (`one_of`), damit nicht jeder
Run gleich ist.

**Steigerung:** Jedes Level ist schwerer als das davor – etwa ein Viertel bis ein Drittel mehr Gegnerlast (HP pro
Sekunde, gewichtet nach Gefährlichkeit, mit Schwärmen und Phasen), dazu mehr Druck im Finale und von den Wänden. Wer
eine Datei ändert, hält das am besten so. **Wellen-Ansagen** (*Chargers incoming!* …) holen immer gleich ein paar
Gegner dieses Typs dazu (`spawn`) und verkürzen meist die Abstände (`spawn_interval`) – nicht nur die Gewichte.

**Geschafft** ist ein Level, wenn man sein `goal` überlebt hat – das schaltet das nächste frei. Der Run läuft danach
weiter, bis das Schiff zerquetscht wird (die Bestzeit zählt trotzdem).

**Ändern:** Datei bearbeiten, speichern, im Spiel ins Spielmenü wechseln – die Dateien werden jedes Mal neu gelesen,
ein Neustart ist nicht nötig. **Neues Level:** eine Datei kopieren, umbenennen, `order` und `unlock` anpassen.

**Im Spielmenü** (Reiter *Levels*) steht jedes Level als Knopf. Eine neue Zeile beginnt, wenn sich die Zehnerstelle
von `order` ändert (1–6: A, 11–16: B, 21–26: C, 27: Survival – in der Reihe der C-Level). Die kleinen Anzeigen auf den Knöpfen und die Details darunter
ergeben sich aus der Datei: ein Quadrat pro Gegnertyp (Evolutionen mit dunklem Rahmen), ein Symbol pro Art von
Ereignis (Schwarm, Welle eines Typs, mehr Schaden, mehr HP, härtere Wände, Würfel für `one_of`, Stecknadel für
Points of Interest, sonstige Ansage). Unter *Numbers* stehen
die Grundwerte: Arena-Größe, wie schnell die Kanten einrücken und wie viel Zeit zwischen zwei Gegnern liegt (jeweils
Anfang bis Grenze und wann die Grenze erreicht ist – ohne Phasen), erster Gegner, Core-Chance. Bei den Ereignissen
stehen die Werte der Phasen dabei (z. B. *Faster spawns (×0.8)*). Nur `hints` schreibt man selbst.

**Fehler sind kein Absturz:** Fehlt ein Wert oder ist er ungültig, gilt der Standardwert (siehe `game/difficulty.py`),
und das Spielmenü zeigt die Probleme rot über den Knöpfen an. JSON kennt keine Kommentare – Erklärungen stehen hier.

Zeiten in Sekunden, Größen in Pixeln, Chancen von 0 bis 1 (0.01 = 1 %).

## Allgemein

| Schlüssel | Bedeutung |
|---|---|
| `name` | Name im Spiel |
| `description` | kurze Beschreibung neben dem Namen im Spielmenü |
| `order` | Reihenfolge im Spielmenü, kleinste zuerst; das erste ist das Start-Level eines neuen Spielstands. Die Zehnerstelle ist die Zeile im Reiter *Levels* |
| `goal` | so viele Sekunden überleben = Level geschafft (schaltet das nächste frei). `null` = endlos (Survival), kann nicht geschafft werden |
| `hints` | Liste kurzer Texte für das Spielmenü (*What to expect*), z. B. `["Many ranged units", "Very hard walls"]` |
| `core_chance` | Chance, dass ein getöteter Gegner einen Core fallen lässt (der Skilltree-Knoten *Core luck* kommt dazu) |

## `unlock` – wann das Level freigeschaltet ist

| Schlüssel | Bedeutung |
|---|---|
| `requires` | Schlüssel des Levels, das man zuerst schaffen muss (dessen `goal` überleben) – `null` = von Anfang an offen |

## `arena` – das Fenster

| Schlüssel | Bedeutung |
|---|---|
| `start_size` | `[Breite, Höhe]` am Start (der Knoten *Bigger arena* kommt dazu) |
| `shrink_speed` | so viele Pixel pro Sekunde rückt **jede** Kante am Anfang nach innen. Zum Vergleich: die Grundkanone schiebt 3 × 15 = 45 px/s zurück, alle vier Kanten zusammen schrumpfen 4 × `shrink_speed` … |
| `shrink_growth` | … plus so viel pro Minute Spielzeit … (optional, Standard 0) |
| `max_shrink_speed` | … höchstens so viel (Standard 60) |
| `armor` | Panzerung am Anfang in Pixeln (Standard 0), flach: jeder Stoß gegen eine Kante schiebt sie so viele Pixel weniger weit, mindestens `MIN_PUSH_SHARE` (10 %, `settings.py`) bleibt. Phasen können sie erhöhen |
| `push_falloff` | je weiter die Arena schon draußen ist, desto weniger bringt ein Stoß – pro Achse: links/rechts zählt die Breite, oben/unten die Höhe. Ein Stoß wird mal (Startgröße ÷ jetzige Größe) ^ `push_falloff` genommen, danach kommt die Panzerung ab. Bei 1: doppelt so breit wie am Start → halber Stoß, halb so breit → doppelter. 0 = aus (fehlt der Wert, ist er 0). Phasen können ihn ändern |

Beispiel A5: 10 px/s am Anfang, + 2 pro Minute – nach 5 Minuten 20 px/s, das ist auch die Obergrenze.
Fehlen `shrink_growth` und `max_shrink_speed`, schrumpft die Arena immer gleich schnell.

Panzerung ist flach: bei `armor` 7 schiebt die Gun 35 → 28 px, die Cannon 90 → 83, die Machine gun nur noch 6 → 0,6
(das Minimum) – viele kleine Stöße (Machine gun, Laser) verlieren viel, wenige große (Cannon, Rakete) kaum etwas.

`push_falloff` bei 800 px Startbreite, Gun-Stoß 35 px: bei 400 px Breite 70 px, bei 1600 px 17,5 px – bei
`push_falloff` 2 schon 140 bzw. 8,75 px. Die Startgröße ist die mit *Bigger arena*, so macht der Knoten den Anfang nicht
schwerer.

## `spawning` – wie oft Gegner kommen

| Schlüssel | Bedeutung |
|---|---|
| `first_spawn` | Sekunden bis zum ersten Gegner |
| `start_interval` | Sekunden zwischen zwei Gegnern am Anfang … |
| `min_interval` | … werden kürzer bis höchstens hierhin … |
| `interval_drop` | … um so viel pro gespielter Sekunde |

## `enemies` – welche Gegner ab wann

Eine Liste, ein Eintrag pro Gegnertyp. Bei jedem Spawn wird zufällig einer der Typen gewählt, deren Zeit schon gekommen
ist – mit `weight` gewichtet (50 gegen 10 = fünfmal so oft).

| Schlüssel | Bedeutung |
|---|---|
| `type` | `basic`, `charger`, `shooter`, `sniper`, `carrier`, `artillery`, `critter`, `commander`, `pusher`, `living_window` – oder direkt eine Evolution: `fat`, `cannoneer`, `shield`, `laser`, `cluster` (meist besser über `evolutions`) |
| `weight` | wie häufig im Vergleich zu den anderen … |
| `after` | … ab dieser Spielzeit … |
| `growth` | … plus so viel Gewicht pro Minute danach (optional, Standard 0) |

`growth` macht starke Gegner mit der Zeit häufiger: Sniper mit `weight` 10, `after` 60, `growth` 3 hat nach 5 Minuten
Spielzeit (4 Minuten nach seinem Start) Gewicht 10 + 4 × 3 = 22. Basics ohne `growth` bleiben bei 50, werden also
anteilig seltener.

## `evolutions` – Tier-2-Gegner statt Tier 1 (optional)

Es wird weiter nur der normale Typ gespawnt – aber jeder Gegner dieses Typs (einzeln oder im Schwarm) kommt mit
einer Chance als seine Evolution:

| Tier 1 | wird zu (Tier 2) |
|---|---|
| `basic` | `fat` – Fat Guy: größer, viel mehr HP |
| `shooter` | `cannoneer` – sehr langsam, riesige langsame Kanonenkugel mit massivem Schaden |
| `charger` | `shield` – der Schild-Gegner |
| `sniper` | `laser` – dickere Ziellinie, dann ein Strahl für eine halbe Sekunde statt einer Kugel |
| `artillery` | `cluster` – wirft Splittergranaten: am Aufschlag drei kleine Explosionen, weit verstreut |

Eine Liste, ein Eintrag pro Typ:

| Schlüssel | Bedeutung |
|---|---|
| `type` | der Tier-1-Typ (`basic`, `shooter`, `charger`, `sniper`, `artillery`) |
| `chance` | Chance am Anfang (0.1 = jeder zehnte) … |
| `after` | … ab dieser Spielzeit (vorher nie) … |
| `growth` | … plus so viel pro Minute danach (optional, Standard 0) … |
| `max_chance` | … höchstens so viel (Standard 1) |

```json
"evolutions": [
  { "type": "basic",   "chance": 0.08, "after": 0,  "growth": 0.03, "max_chance": 0.2 },
  { "type": "shooter", "chance": 0.08, "after": 20, "growth": 0.03, "max_chance": 0.2 }
]
```

Auf B1: Am Anfang ist jeder 12. Basic ein Fat Guy, nach 4 Minuten jeder fünfte (8 % + 4 × 3 % = 20 %, die Obergrenze).
Chargers und Sniper bleiben dort immer Tier 1, weil sie in der Liste fehlen.

## `enemy_stats` – eigene Gegnerwerte auf diesem Level (optional)

Wie im StarCraft-2-Editor, wo jede Map ihre eigenen Einheitenwerte hat: Hier lassen sich alle Werte aus
`data/enemies.json` nur für diese Stufe ändern (welche es gibt: `data/README.md`). Pro Gegnertyp ein Eintrag, `all`
gilt für jeden Typ, der den Wert hat.

| Schreibweise | Wirkung | Beispiel |
|---|---|---|
| Zahl | ersetzt den Wert | `"speed": 100` |
| `"+1"` / `"-1"` | addiert / zieht ab | `"base_hp": "+1"` |
| `"x1.5"` | multipliziert | `"contact_damage": "x1.5"` |

```json
"enemy_stats": {
  "all":     { "base_hp": "+1" },
  "charger": { "speed": 100, "charge_speed": "x1.2" }
}
```

Erst wird `all` angewendet, dann der eigene Eintrag des Typs. Würde ein Wert ungültig (z. B. `"-5"` auf 2 HP), bleibt
der Standard und das Spielmenü warnt.

## `phases` – Abschnitte im Run (optional)

Eine Liste. Jede Phase gilt von `from` bis `to` Sekunden Spielzeit und kann die Spawn-Gewichte ändern, die Gegner
buffen und sich ansagen.

| Schlüssel | Bedeutung |
|---|---|
| `from` | Beginn (Sekunden Spielzeit) |
| `to` | Ende – weglassen = bis zum Ende des Runs |
| `weights` | Änderungen an den Gewichten aus `enemies`, solange die Phase läuft |
| `enemy_stats` | Buffs auf alle Gegner, solange die Phase läuft – wie `enemy_stats` unten, aber nur `"+1"`, `"-1"`, `"x1.5"` |
| `announce` | Text, der zu Beginn oben im Spiel eingeblendet wird – weglassen = still |
| `arena` | Änderungen an der Arena, solange die Phase läuft: `armor`, `shrink_speed` und `push_falloff`, Schreibweise wie unten (`"+3"`, `"x1.5"`, Zahl) |
| `spawn` | Gegner, die **einmal** zu Beginn der Phase zusätzlich kommen, jeder an einer eigenen Stelle: `{ "shooter": 3 }` (ganze Zahlen) |
| `spawn_interval` | Zeit zwischen zwei Gegnern, solange die Phase läuft: `"x0.6"` = 40 % kürzer, `"-1"` = eine Sekunde kürzer, Zahl = genau so viele Sekunden. Darf unter `min_interval` gehen |
| `every` | wiederholt die Phase alle so viele Sekunden, ab `from` – jedes Mal so lang wie beim ersten Mal (`to` − `from`), ohne `to` gilt sie jedes Mal bis zum Ende (stapelt sich also). `one_of` würfelt bei jeder Wiederholung neu |
| `points` | Points of Interest, die **einmal** zu Beginn der Phase irgendwo draußen erscheinen: `{ "totem": 1 }` – `totem`, `nest`, `storm` (Gefahren) oder `chest`, `magnet`, `repair` (Funde). Was sie tun: `data/README.md` (`points.json`) |
| `breathe` | „atmende Arena“: Jede Kante rückt über die Dauer der Phase zusätzlich so viele Pixel ein und federt danach von selbst genauso weit zurück (ohne Panzerung und `push_falloff`). Wer währenddessen schiebt, hat danach mehr Platz. Nur in Phasen mit `to` |
| `one_of` | eine Liste von Möglichkeiten, von denen jeder Run **eine** auswürfelt – siehe unten |

Schreibweise bei `weights` wie bei `enemy_stats`: `"x3"` verdreifacht das Gewicht, `"+20"` addiert, eine Zahl ersetzt
es, `0` schaltet den Typ ab. `"x3"` auf einen Typ, dessen `after` noch nicht erreicht ist, bleibt 0 – `"+20"` holt ihn
dagegen schon früher.

`base_hp` und `size` gelten nur für Gegner, die während der Phase spawnen; alle anderen Werte (Tempo, Schaden, …) wirken
sofort auf alle. Eine Phase ohne `to` wirkt bis zum Ende – so steigen die HP mit der Zeit.

```json
"phases": [
  { "from": 150, "enemy_stats": { "all": { "base_hp": "+1" } } },
  { "from": 200, "to": 240, "weights": { "sniper": "x3" }, "announce": "Snipers incoming!" },
  { "from": 300, "enemy_stats": { "all": { "base_hp": "+1" } } }
]
```

Ab 2:30 haben alle neuen Gegner +1 HP, ab 5:00 +2. Von 3:20 bis 4:00 kommen dreimal so viele Sniper.

Eine Welle mit Paukenschlag – drei Shooter sofort, danach 20 Sekunden lang mehr Shooter und kürzere Abstände (A1):

```json
{ "from": 60, "to": 80, "weights": { "shooter": "x3" }, "spawn": { "shooter": 3 }, "spawn_interval": "x0.6",
  "announce": "Shooters incoming!" }
```

Mehr Schaden über die Zeit und härtere Wände – so stehen sie in den Dateien:

```json
{ "from": 180, "enemy_stats": { "all": { "contact_damage": "x1.25", "projectile_damage": "x1.25", "blast_damage": "x1.25" } },
  "announce": "Enemies hit harder!" },
{ "from": 240, "arena": { "armor": "+5" }, "announce": "The walls harden!" }
```

Mehrere Phasen ohne `to` stapeln sich: zweimal `"x1.25"` und `"x1.2"` ergibt das 1,5-fache, `"+3"` und `"+2"` ergibt 5.

Die Wände 6 Sekunden lang je 90 px einziehen lassen, danach federn sie zurück:

```json
{ "from": 200, "to": 206, "breathe": 90, "announce": "The arena breathes in!" }
```

### Periodisch: `every`

Statt jede Steigerung einzeln hinzuschreiben, wiederholt `every` eine Phase:

```json
{ "from": 120, "every": 120, "enemy_stats": { "all": { "base_hp": "+1" } }, "announce": "Enemies +1 HP" },
{ "from": 240, "to": 260, "every": 45, "spawn_interval": "x0.8", "one_of": [
  { "weights": { "charger": "x3" }, "spawn": { "charger": 4 }, "announce": "Chargers incoming!" },
  { "weights": { "basic": "x2" }, "spawn": { "basic": 10 }, "announce": "The horde is coming!" }
] }
```

Ab 2:00 alle zwei Minuten +1 HP (2:00, 4:00, 6:00 … – ohne `to`, also stapeln sie sich). Ab 4:00 alle 45 Sekunden
20 Sekunden lang eine Welle – jedes Mal neu ausgewürfelt. Im Spielmenü steht dahinter „– every 00:45“.

### Zufall: `one_of`

Damit ein Level nicht jedes Mal gleich abläuft: `one_of` ist eine Liste von Möglichkeiten. Zu Beginn jedes Runs wird
pro Phase **eine** davon ausgewürfelt und gilt dann zusätzlich zu dem, was direkt in der Phase steht. Eine Möglichkeit
darf alles enthalten, was eine Phase kann (`weights`, `enemy_stats`, `announce`, `arena`, `spawn`, `spawn_interval`,
`breathe`), dazu `weight`: wie wahrscheinlich sie im Vergleich zu den anderen ist (Standard 1, `0` schaltet sie ab).
`from` und `to` gelten für alle Möglichkeiten gleich und stehen nur in der Phase.

Listen (`weights`, `enemy_stats`, `arena`, `spawn`) kommen zu denen der Phase dazu; `announce`, `spawn_interval` und
`breathe` der Möglichkeit ersetzen die der Phase, falls beide einen haben.

```json
{ "from": 90, "to": 120, "spawn_interval": "x0.8", "one_of": [
  { "weights": { "charger": "x3" }, "spawn": { "charger": 4 }, "announce": "Chargers incoming!" },
  { "weights": { "shooter": "x3" }, "spawn": { "shooter": 3 }, "announce": "Shooters incoming!" },
  { "spawn": { "basic": 12 }, "breathe": 60, "announce": "Here they come!", "weight": 2 }
] }
```

Von 1:30 bis 2:00 kommen immer kürzere Abstände – dazu in einem von vier Runs eine Charger-Welle, in einem von vier
eine Shooter-Welle und in jedem zweiten 12 Basics, während die Wände einatmen. Im Spielmenü steht jede Möglichkeit
als eigene Zeile mit einem Würfel und ihrer Chance.

## `swarms` – Schwärme

Einmal pro Sekunde wird gewürfelt, ob ein ganzer Schwarm an einer Stelle auftaucht. `swarms` ist entweder **ein**
Eintrag `{ … }` oder eine **Liste** davon – dann würfelt jede Schwarmart für sich, mit eigener Chance und eigenem
`min_gap` (auf A6 z. B. Basic- und Charger-Schwärme). `[]` = keine Schwärme.

| Schlüssel | Bedeutung |
|---|---|
| `type` | Gegnertyp im Schwarm (wie oben) |
| `after` | keine Schwärme vor dieser Spielzeit |
| `start_chance` | Chance pro Sekunde am Anfang … |
| `chance_growth` | … plus so viel pro gespielter Sekunde … |
| `max_chance` | … höchstens so viel |
| `start_size` | Gegner pro Schwarm am Anfang … |
| `growth_time` | … einer mehr alle so viele Sekunden … |
| `max_size` | … höchstens so viele |
| `min_gap` | mindestens so viele Sekunden zwischen zwei Schwärmen dieser Art |
| `leader` | ein Gegnertyp, der **genau in der Mitte** des Schwarms mitkommt (meist `commander`) – die anderen stehen um ihn herum (optional) |
| `leader_chance` | in so einem Anteil der Schwärme kommt er (Standard 1 = immer) |

Am Fensterrand zeigt ein Schwarm außerhalb der Sicht kein Pünktchen pro Gegner, sondern **ein Schwarm-Symbol** in
seiner Farbe – je näher er kommt, desto größer.
