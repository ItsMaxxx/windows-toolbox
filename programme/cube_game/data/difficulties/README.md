# Schwierigkeitsstufen

Jede `.json`-Datei hier ist eine Schwierigkeitsstufe. Der Dateiname (ohne `.json`) ist ihr Schlüssel: Er steht im
Spielstand und in `unlock.requires` anderer Stufen – darum Dateien nicht einfach umbenennen.

**Ändern:** Datei bearbeiten, speichern, im Spiel ins Spielmenü wechseln – die Dateien werden jedes Mal neu gelesen,
ein Neustart ist nicht nötig. **Neue Stufe:** eine Datei kopieren, umbenennen, `order` und `unlock` anpassen.

**Fehler sind kein Absturz:** Fehlt ein Wert oder ist er ungültig, gilt der Standardwert (siehe `game/difficulty.py`),
und das Spielmenü zeigt die Probleme rot über den Knöpfen an. JSON kennt keine Kommentare – Erklärungen stehen hier.

Zeiten in Sekunden, Größen in Pixeln, Chancen von 0 bis 1 (0.01 = 1 %).

## Allgemein

| Schlüssel | Bedeutung |
|---|---|
| `name` | Name im Spiel |
| `description` | kurze Beschreibung unter den Knöpfen im Spielmenü |
| `order` | Reihenfolge im Spielmenü, kleinste zuerst; die erste ist die Startstufe eines neuen Spielstands |
| `core_chance` | Chance, dass ein getöteter Gegner einen Core fallen lässt (der Skilltree-Knoten *Core luck* kommt dazu) |

## `unlock` – wann die Stufe freigeschaltet ist

| Schlüssel | Bedeutung |
|---|---|
| `requires` | Schlüssel der Stufe, auf der man zuerst überleben muss – `null` = von Anfang an offen |
| `survive` | so lange muss man dort überleben (Standard 240 = 4:00) |

## `arena` – das Fenster

| Schlüssel | Bedeutung |
|---|---|
| `start_size` | `[Breite, Höhe]` am Start (der Knoten *Bigger arena* kommt dazu) |
| `shrink_speed` | so viele Pixel pro Sekunde rückt **jede** Kante am Anfang nach innen. Zum Vergleich: die Grundkanone schiebt 3 × 15 = 45 px/s zurück, alle vier Kanten zusammen schrumpfen 4 × `shrink_speed` … |
| `shrink_growth` | … plus so viel pro Minute Spielzeit … (optional, Standard 0) |
| `max_shrink_speed` | … höchstens so viel (Standard 60) |
| `armor` | Panzerung am Anfang (Standard 0): jeder Stoß gegen eine Kante schiebt sie so viele Pixel weniger weit, mindestens aber 0,5 px – wie Rüstung in StarCraft. Phasen können sie erhöhen |

Beispiel Normal: 14 px/s am Anfang, + 2 pro Minute – nach 5 Minuten 24 px/s, ab 6 Minuten die Obergrenze 26 px/s.
Fehlen `shrink_growth` und `max_shrink_speed` (wie gerade auf Hard), schrumpft die Arena immer gleich schnell.

Panzerung: Die Grundkanone schiebt mit 15 px; bei `armor` 3 sind es noch 12, bei 15 nur noch 0,5. Schwache, schnelle
Schüsse leiden also mehr darunter als starke (Rakete: 120 → 117).

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
| `type` | `basic`, `charger`, `shooter`, `sniper`, `carrier`, `artillery`, `shield` oder `critter` |
| `weight` | wie häufig im Vergleich zu den anderen … |
| `after` | … ab dieser Spielzeit … |
| `growth` | … plus so viel Gewicht pro Minute danach (optional, Standard 0) |

`growth` macht starke Gegner mit der Zeit häufiger: Sniper mit `weight` 10, `after` 60, `growth` 3 hat nach 5 Minuten
Spielzeit (4 Minuten nach seinem Start) Gewicht 10 + 4 × 3 = 22. Basics ohne `growth` bleiben bei 50, werden also
anteilig seltener.

## `enemy_stats` – eigene Gegnerwerte auf dieser Stufe (optional)

Wie im StarCraft-2-Editor, wo jede Map ihre eigenen Einheitenwerte hat: Hier lassen sich alle Werte aus
`data/enemies.json` nur für diese Stufe ändern (welche es gibt: `data/README.md`). Pro Gegnertyp ein Eintrag, `all`
gilt für jeden Typ, der den Wert hat.

| Schreibweise | Wirkung | Beispiel |
|---|---|---|
| Zahl | ersetzt den Wert | `"speed": 100` |
| `"+1"` / `"-1"` | addiert / zieht ab | `"max_hp": "+1"` |
| `"x1.5"` | multipliziert | `"contact_damage": "x1.5"` |

```json
"enemy_stats": {
  "all":     { "max_hp": "+1" },
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
| `arena` | Änderungen an der Arena, solange die Phase läuft: `armor` und `shrink_speed`, Schreibweise wie unten (`"+3"`, `"x1.5"`, Zahl) |

Schreibweise bei `weights` wie bei `enemy_stats`: `"x3"` verdreifacht das Gewicht, `"+20"` addiert, eine Zahl ersetzt
es, `0` schaltet den Typ ab. `"x3"` auf einen Typ, dessen `after` noch nicht erreicht ist, bleibt 0 – `"+20"` holt ihn
dagegen schon früher.

`max_hp` und `size` gelten nur für Gegner, die während der Phase spawnen; alle anderen Werte (Tempo, Schaden, …) wirken
sofort auf alle. Eine Phase ohne `to` wirkt bis zum Ende – so steigen die HP mit der Zeit.

```json
"phases": [
  { "from": 150, "enemy_stats": { "all": { "max_hp": "+1" } } },
  { "from": 200, "to": 240, "weights": { "sniper": "x3" }, "announce": "Snipers incoming!" },
  { "from": 300, "enemy_stats": { "all": { "max_hp": "+1" } } }
]
```

Ab 2:30 haben alle neuen Gegner +1 HP, ab 5:00 +2. Von 3:20 bis 4:00 kommen dreimal so viele Sniper.

Mehr Schaden über die Zeit und härtere Wände – so stehen sie in den Dateien:

```json
{ "from": 180, "enemy_stats": { "all": { "contact_damage": "x1.25", "shot_damage": "x1.25", "blast_damage": "x1.25" } },
  "announce": "Enemies hit harder!" },
{ "from": 240, "arena": { "armor": "+3" }, "announce": "The walls harden!" }
```

Mehrere Phasen ohne `to` stapeln sich: zweimal `"x1.25"` und `"x1.2"` ergibt das 1,5-fache, `"+3"` und `"+2"` ergibt 5.

## `swarms` – Schwärme

Einmal pro Sekunde wird gewürfelt, ob ein ganzer Schwarm an einer Stelle auftaucht. `swarms` ist entweder **ein**
Eintrag `{ … }` oder eine **Liste** davon – dann würfelt jede Schwarmart für sich, mit eigener Chance und eigenem
`min_gap` (auf Hard z. B. Basic- und Charger-Schwärme). `[]` = keine Schwärme.

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
