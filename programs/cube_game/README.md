# Cube Game

Du spielst eine **weiße Box**. In regelmäßigen Abständen tauchen **rote Cubes** auf; berührst du einen, kostet das
Leben. Steuerung vorerst nur **W A S D**.

Das Spiel ist ein **Lernprojekt**: Game Design und Programmierung von Grund auf, ohne fertige Engine (kein Godot,
Unity, Unreal – bewusst so entschieden). Später sollen eine eigene kleine Engine und ein eigener Map-Editor dazukommen,
nach dem Vorbild des StarCraft-2-Editors, sowie eines Shops für upgrades etc..

---

## Regeln für Claude (bitte zuerst lesen)

Diese Regeln gelten auf jedem PC und in jeder Sitzung. Hier stehen sie, weil `CLAUDE.md` und Claudes Memory nur lokal
liegen und nicht mit Git mitwandern.

- **Ich (Maximilian) schreibe den Code für Spiel, Engine und Editor selbst.** Claude schreibt **keinen** Spielcode und
  liefert keine fertigen Lösungen, nur auf anfrage.
- **Was Claude darf:** beraten, Konzepte erklären, Fragen beantworten, Fehlermeldungen erklären, meinen Code
  reviewen, Hinweise geben, auf die passende Doku zeigen.
- **Kleine Änderungen** an meinem Code (z. B. einen Fehler beheben, etwas umbenennen) nur, wenn ich ausdrücklich darum
  bitte, und dann mit Erklärung, was und warum.
- **Erst einen Tipp, dann die Lösung.** Wenn ich hänge, zuerst einen Denkanstoß geben, dann einen genaueren Hinweis;
  die vollständige Erklärung erst, wenn ich danach frage.
- **Ausnahme:** Die Anbindung an die Toolbox (`cube_game_gui.py`, `program.json`, Einträge in `setup\`) ist
  Infrastruktur und kein Teil der Übung; die darf Claude wie den Rest der Toolbox pflegen.
- Den Fahrplan unten und den Abschnitt **Stand** aktuell halten, damit die nächste Sitzung weiß, wo ich bin.

Zur Geschichte: Eine frühere Sitzung hatte schon ein komplett fertiges Cube Game geschrieben. Das habe ich am
11.10.2026 löschen lassen, weil ich es selbst bauen will.

---

## Ist Python schnell genug?

**Für dieses Spiel locker.** Ein paar hundert bewegte Rechtecke mit Kollisionsprüfung schafft Python mit pygame-ce
ohne Mühe bei 60 Bildern pro Sekunde. Das Spiel wird kaum über ein paar Dutzend Objekte hinauskommen.

**Wo Python an Grenzen stößt:** Reines Python ist bei Schleifen grob 10- bis 100-mal langsamer als C++, C# oder Rust.
Das merkt man erst bei *sehr vielen* Objekten, die *jedes Bild* etwas rechnen, zum Beispiel bei:

- Tausenden Einheiten, bei denen jede gegen jede auf Kollision geprüft wird (das sind n² Prüfungen),
- Wegfindung für viele Einheiten gleichzeitig (wie in einem RTS à la StarCraft),
- eigener Physik oder vielen Partikeln.

Meistens hilft dann ein **besserer Algorithmus** mehr als eine schnellere Sprache: Ein räumliches Gitter
(„Spatial Hash“) macht aus n² Prüfungen fast n. Danach kommen `numpy` für Massenrechnungen oder das Auslagern einzelner
heißer Stellen in Frage.

**Fazit:** Python ist zum Lernen eine gute Wahl, weil man schnell Ergebnisse sieht und sich auf Spielaufbau und Design
konzentriert. Was ich hier lerne (Game Loop, Delta-Time, Entities, Kollision, Szenen, datengetriebene Level,
Editor), funktioniert in C++/C#/Rust genauso. Falls die Engine irgendwann wirklich zu langsam wird, kann ich den Kern
in einer anderen Sprache neu schreiben und weiß dann schon, *was* ich baue.

---

## Technik: pygame-ce

[pygame-ce](https://pyga.me/) (Community-Fork von pygame) ist **keine Engine**, sondern eine dünne Schicht über SDL.
Es übernimmt nur das, was man ohne Betriebssystem-Programmierung nicht sinnvoll selbst machen kann:

| pygame-ce übernimmt | baue ich selbst |
|---|---|
| Fenster öffnen | Hauptschleife (Game Loop) und Zeitmessung |
| Tastatur, Maus, Controller abfragen | Eingabe-System (Tasten belegbar statt fest WASD) |
| Rechtecke, Bilder, Text zeichnen | Spieler, Gegner, Spawner, Schaden, Leben |
| Sound abspielen | Kollisionserkennung und -reaktion |
| Rechteck-/Vektor-Hilfen (`Rect`, `FRect`, `Vector2`) | Szenen (Menü, Spiel, Game Over, Editor) |
| | Kamera, Level-Format, Speichern/Laden, Map-Editor |

pygame-ce steht schon in `requirements.txt` und wird von `Setup.exe` in `runtime\` installiert (Version 2.5.8).
Doku: <https://pyga.me/docs/>.

---

## Dateien

| Datei | Inhalt |
|---|---|
| `cube_game.py` | **das Spiel – schreibe ich selbst** (zu Beginn leer) |
| `cube_game_gui.py` | Seite in der Toolbox (*Games → Cube Game*): nur der Knopf *Spielen* |
| `program.json` | Ausweis für die Toolbox: Name, Tab, Version, Skript, Starter |
| `CubeGame.exe` | Starter, legt `Setup.exe` an (nicht im Repo) |

Wenn `cube_game.py` zu groß wird (Faustregel: ab ca. 300–400 Zeilen oder wenn ich scrollen muss, um etwas zu
finden), teile ich es auf. Ein möglicher späterer Aufbau, **nicht** jetzt schon anlegen:

```
programs/cube_game/
├── cube_game.py        Einstieg: startet die Engine mit der ersten Szene
├── engine/             alles, was nicht speziell zum Cube Game gehört (wiederverwendbar)
├── spiel/              Spieler, Gegner, Szenen dieses Spiels
├── editor/             der Map-Editor
└── level/              Level als JSON-Dateien
```

---

## Starten

Zum Entwickeln im Terminal aus dem Hauptordner der Toolbox, damit Fehlermeldungen sichtbar sind:

```
runtime\python.exe programs\cube_game\cube_game.py
```

Über die Toolbox (*Spielen*) läuft das Spiel mit `pythonw` ohne Konsole. Ein Absturz ist dort unsichtbar, darum zum
Testen das Terminal nehmen.

---

## Fahrplan

Jeder Meilenstein ist klein genug für ein bis zwei Abende. Erst wenn einer läuft, kommt der nächste. Nach jedem
Meilenstein committen.

### Phase 1: Das Spiel zum Laufen bringen

**M1: Fenster und Game Loop**
Ein Fenster, das offen bleibt, bis man es schließt oder Esc drückt, und jedes Bild neu gezeichnet wird.
*Lernen:* die Hauptschleife „Eingaben → Update → Zeichnen“, `pygame.time.Clock`, FPS.
*Fertig, wenn:* ein leeres, farbiges Fenster stabil läuft und sauber schließt.

**M2: Die weiße Box**
Eine Box, die sich mit WASD bewegt und das Fenster nicht verlassen kann.
*Lernen:* Position und Geschwindigkeit, **Delta-Time** (Tempo × vergangene Zeit, damit das Spiel auf jedem PC
gleich schnell läuft), Tasten *gedrückt halten* vs. *einmal drücken*, warum schräg sonst schneller ist.
*Fertig, wenn:* die Bewegung bei 30 und bei 144 FPS gleich schnell ist.

**M3: Gegner erscheinen**
Rote Cubes erscheinen in festen Abständen (z. B. alle 1,5 s) und bewegen sich.
*Lernen:* Timer, Listen von Objekten, Klassen (Spieler und Gegner als eigene Klassen), Objekte wieder entfernen.
*Überlegen:* Wo erscheinen sie? Wohin fliegen sie? Das ist schon Game Design.

**M4: Kollision und Schaden**
Berührung kostet Leben, bei 0 ist Game Over.
*Lernen:* **AABB-Kollision** (zwei achsenparallele Rechtecke überlappen sich), was nach einem Treffer passiert (Gegner
weg? kurz unverwundbar?), Spielzustände.

**M5: Anzeige und Neustart**
Lebensanzeige, Zeit oder Punkte, Game-Over-Bildschirm, mit einer Taste neu starten.
*Lernen:* Text zeichnen, **Zustände** (spielt / Game Over) sauber trennen.

**M6: Rekord speichern**
Bestzeit überlebt das Schließen des Spiels.
*Lernen:* Dateien lesen/schreiben, JSON. Die Toolbox hat dafür `toolbox\storage.py`
(`daten.einstellungen("cube_game")` ergibt `data\cube_game.json`); danach kann die Toolbox-Seite den Rekord anzeigen.

### Phase 2: Game Design

**M7: Macht es Spaß?**
Jetzt nicht programmieren, sondern spielen und beobachten. Fragen: Wann wird es langweilig? Wann unfair? Ideen:
steigende Schwierigkeit, verschiedene Gegnertypen (schnell/klein, langsam/groß, verfolgend), Heil-Pickups, kurzes
Bildschirmwackeln und Aufblitzen bei Treffern („Game Feel“ bzw. „Juice“), Sound.
*Lernen:* Spielkurve, Feedback, Balancing. Alle Zahlen an einer Stelle sammeln, damit man schnell drehen kann.

### Phase 3: Die eigene Engine herauslösen

Erst jetzt, wenn ein Spiel läuft, sieht man, was wiederverwendbar ist. Eine Engine vorab zu planen geht fast immer
schief.

**M8: Szenen**
Menü, Spiel, Game Over (und später Editor) als eigene Szenen, zwischen denen die Engine wechselt.

**M9: Entities und Komponenten**
Statt „Spieler-Klasse“ und „Gegner-Klasse“ mit doppeltem Code: Objekte, die aus Bausteinen bestehen (Position,
Bewegung, Hitbox, Leben, Aussehen). Zum Vergleichen: Vererbung vs. Komposition vs. ECS.

**M10: Saubere Zeit und Eingabe**
Fester Zeitschritt für die Spiellogik („Fix Your Timestep“), Tastenbelegung aus einer Datei statt fest WASD, eventuell
Kamera, falls die Welt größer als das Fenster wird.

### Phase 4: Der Map-Editor (Vorbild StarCraft 2)

Der SC2-Editor besteht im Kern aus drei Teilen. So übertragen sie sich auf das Cube Game:

| SC2-Editor | im Cube Game |
|---|---|
| **Terrain-/Map-Editor**: Gelände, Objekte platzieren | Hindernisse, Wände, Spawnpunkte mit der Maus setzen |
| **Daten-Editor**: Werte jeder Einheit (Leben, Tempo, Schaden) | Gegnertypen als Datei statt im Code |
| **Trigger-Editor**: Ereignis → Bedingung → Aktion | z. B. „Wenn Zeit > 30 s → schicke einen Boss“ |

**M11: Level aus Dateien**
Das Spiel liest Level (Hindernisse, Spawnpunkte, Wellen) aus JSON statt aus dem Code. Das ist die Voraussetzung für
alles Weitere: **datengetrieben** arbeiten.

**M12: Editor-Modus**
Eigene Szene: Raster, mit der Maus Dinge setzen und löschen, speichern, laden, sofort testen.

**M13: Trigger**
Ein einfaches Ereignis-Bedingung-Aktion-System, das aus der Level-Datei kommt.

---

## Lernquellen

- **pygame-ce-Doku:** <https://pyga.me/docs/>
- **Game Programming Patterns** (Robert Nystrom), kostenlos online: <https://gameprogrammingpatterns.com/>.
  Besonders *Game Loop*, *Update Method*, *Component*, *State*, *Spatial Partition*.
- **Fix Your Timestep!** (Glenn Fiedler): <https://gafferongames.com/post/fix_your_timestep/>, für M10.
- **Red Blob Games** (Amit Patel): <https://www.redblobgames.com/>, für Raster, Wegfindung, Karten.
- **Handmade Hero** (Casey Muratori): eine Engine komplett von null in C, als Videoserie. Später, wenn mich
  interessiert, was unter pygame passiert.

---

## Stand

Hier trage ich ein, wo ich bin. Claude liest das zuerst.

- [ ] M1 Fenster und Game Loop
- [ ] M2 Die weiße Box
- [ ] M3 Gegner erscheinen
- [ ] M4 Kollision und Schaden
- [ ] M5 Anzeige und Neustart
- [ ] M6 Rekord speichern
- [ ] M7 Game Design
- [ ] M8–M10 Engine
- [ ] M11–M13 Editor

Notizen / offene Fragen:

- 13.10.2026 (Claude, auf Wunsch gebaut): Gegner überlappen nicht mehr und schieben sich gegenseitig
  (`engine/collision.py`: `push_apart`, `nearby_pairs` = Spatial Hash; schwere Gegner schieben stärker, ein
  anstürmender Charger rammt alles weg). Neuer Gegner **Carrier** (`game/enemies/carrier.py`) mit **Crittern**
  (`critter.py`, lassen keine Sterne fallen).
  Keine Obergrenze mehr für Gegner. Ab ca. 800 Gegnern wird die Logik zu langsam für 60 Ticks/s – ein Game Over
  (statt Mindestgröße des Fensters) würde das natürlich begrenzen.
- 13.10.2026 (Claude, auf Wunsch gebaut): **Game Over**, wenn das Fenster das Schiff zerquetscht (keine Mindestgröße
  mehr), Game-Over-Bildschirm (`game_over_scene.py`). **Cores** als Meta-Währung (1 % Drop, `core_pickup.py`),
  gespeichert in `data\cube_game.json` (`profile.py`). **Spielmenü** zwischen den Runs (`game_menu_scene.py`):
  Schiff, Schwierigkeit (`difficulty.py`), Skilltree (`skill_tree.py`). Shop, Dash und Rocket müssen erst
  freigeschaltet werden; Grundfeuerrate halbiert (3/s).
  Schwierigkeiten: nur Easy ist offen; 4:00 auf einer Stufe überleben schaltet die nächste frei.
- 13.10.2026: Schwierigkeiten sind jetzt **Dateien**: `data/difficulties/*.json` (Arena, Cores, Spawn-Tempo, welche
  Gegner ab welcher Sekunde, Schwärme). Erklärung aller Werte: `data/difficulties/README.md`. Werden beim Öffnen des
  Spielmenüs neu gelesen; Fehler darin zeigt das Spielmenü rot an. Vorstufe zu M11 (Level aus Dateien).
- 13.10.2026: Gegnerwerte (Grund- und Verhaltenswerte) in `data/enemies.json` (Erklärung: `data/README.md`), pro
  Schwierigkeit eigene Werte über `enemy_stats` (Zahl / "+1" / "x1.5", "all" für alle Typen) – wie Map-Daten im
  SC2-Editor. Normal: alle Gegner +1 HP. Buff-Grundgerüst (`game/enemies/buff.py`): zeitlich begrenzt, flach und/oder
  Faktor, pro Gegner oder für alle (`roster.buffs`); gebuffte Gegner leuchten pink. Noch nichts löst Buffs aus.
- 13.10.2026: **Mehrere Monitore**: die Arena kann sich über alle Bildschirme ausbreiten, aber nur dorthin, wo wirklich
  Bildschirm ist (keine Lücken, nicht unter Taskleisten; `engine/desktop.py`, `Desktop.covers()`). An/aus: Schalter
  „Arena auf allen Bildschirmen“ auf der Toolbox-Seite (Standard: aus). Die Engine zeichnet jetzt direkt in den Speicher des Fensters (kein Kopieren).
- 13.10.2026: Neuer Gegner **Artillery** (`game/enemies/artillery.py`): hält Sniper-Abstand, markiert die Position des
  Schiffs mit einem Kreis, der sich füllt, dann schlägt es ein (`game/artillery_strike.py`). Aussehen jetzt getrennt
  vom Verhalten: **`game/skins/`** (ein Skin pro Gegner), **`game/effects/`** (Explosion, Artillerie-Einschlag,
  Zielmarkierung, Buff-Leuchten).
  Schwärme erscheinen am Kartenrand (halb dahinter), mindestens `SWARM_GAP` (300 px) vom Fenster entfernt.
- 13.10.2026: **Shop im Run** (T): jeden Wert direkt verbessern, jede Stufe desselben Werts kostet mehr (+5 Sterne).
  **Karten-Shop** im Spielmenü (Reiter *Cards*, Cores): Angebote kaufen oder rerollen, Sammlung bis 12 Karten, bis 3
  aktiv – die wirken zu Beginn jedes Runs. Zahlen in `data/upgrades.json` (`game/shop.py`, `game/card_shop.py`,
  `game/card_panel.py`).

**Balance über den Run (Gegner werden stärker, Spieler skaliert nicht endlos).**
- Gegner-Gewichte wachsen pro Minute (`growth` in `enemies` der Schwierigkeitsdatei) – starke Typen werden häufiger.
- `phases` in der Schwierigkeitsdatei: Abschnitte mit eigenen Gewichten (`"sniper": "x3"`), Buffs (`max_hp "+1"` ohne
  Ende = HP steigen mit der Zeit) und optionaler Ansage oben im Bild. Umgesetzt im Spawner (Buffs als Roster-Buffs).
- `swarms` kann eine Liste sein: Hard hat zusätzlich Charger-Schwärme (ab 60 s, seltener und kleiner als Basic).
- Shop-Stufen (`amount`) sind schwächer, Karten haben einen eigenen Wert (`card_amount`). Eine Bremse gegen
  endloses Hochskalieren (z. B. Grundkanone als Maschinengewehr) gibt es bewusst noch nicht – die 20-%-Schwelle wurde
  wieder entfernt, das soll anders gelöst werden.

**Rand schrumpft mit der Zeit schneller, Projectile speed.**
- `arena` in der Schwierigkeitsdatei: `shrink_growth` (px/s mehr pro Minute) und `max_shrink_speed` (Obergrenze).
- Karte *Shot speed* heißt jetzt *Projectile speed* (Schlüssel `shot_speed` erst am 15.10.2026 umbenannt). Grundkanone
  880 statt 950 px/s. Karten wieder stärker als Shop-Stufen, außer Projectile speed (+150).

**Wachturm (erstes Gebäude).**
- Skilltree-Knoten *Watchtower* (unter Head start, 3/5/8 Cores, Stufe = Türme gleichzeitig). Im Run **B**: Turm fliegt
  420 px in Mausrichtung (bleibt auf dem Monitor), kostet Sterne (15, dann +10 je Turm).
- Gelandet öffnet er ein eigenes Fenster (`engine/view_window.py`, über `Engine.open_view`): randlos, ohne
  Taskleisteneintrag, nimmt nie den Fokus (`WS_EX_NOACTIVATE`), Klicks gehen durch, liegt über dem Hauptfenster.
  Die Szene zeichnet es in `draw_view()`; beim Szenenwechsel schließen alle. Ereignisse der Extrafenster ignoriert die
  Engine. Ohne Layered Window (Rückfall auf SDL) gibt es keine Extrafenster – der Turm steht dann nur in der Welt.
- HP, wird von Berührung, Schüssen und Artillerie getroffen; lockt Nahkampf-Gegner an (`enemy.lure`). Werte in
  `data/buildings.json`. Shop-Upgrade / Karte *Vision* vergrößert die Fenster (auch schon stehender Türme).
- Turmfenster und Spielfeld sind für Schüsse verbunden: Liegt hinter einer Kante ein Turmfenster, fliegt der Schuss
  hinein und trifft Gegner darin. Trifft er nichts, schiebt er beim Verlassen des Turmfensters die Kante, die er
  überquert hat (ein Schuss trifft oder schiebt, wie im Spielfeld). Raketen explodieren auch dort. Das Schiff bleibt im
  Spielfeld. Turmfenster liegen über dem Spielfenster (Owned Window: `GWLP_HWNDPARENT` = Hauptfenster).

**Rahmenlose Zusatzfenster, Radar.**
- Rahmen = Umriss aller Fenster zusammen (`PlayScene.draw_outline`, per Bitmaske): Wo Fenster sich überlappen oder
  berühren, verschmelzen die Kanten zu einer Linie mit Knick; ein einzelnes Fenster hat einfach seinen Rahmen.
  Hintergrund der Zusatzfenster außerhalb des Spielfelds fast schwarz mit Hauch Grau (Radar: Blau), darüber schwarz.
  Wo ein Zusatzfenster das Hauptfenster überdeckt, legt es dessen HUD/Hinweise darüber (`draw_ui_layer`,
  transparente Ebene, normal per Alpha darübergelegt).
- Radar (`game/radar.py`, Werte in `data/radar.json`): Skilltree *Radar* (unter Watchtower) + *Scan size / rate / time*
  (je 3 Stufen; Start 150 px, alle 4 s, 2,5 s offen). Automatisch: alle `cooldown` s ein hellblaues Fenster über der
  größten Gegnergruppe außerhalb der Sicht (Raster aus `size`-Zellen, volle Zelle gewinnt), `duration` s lang. Für
  Schüsse verbunden wie Turmfenster.
- Spielmenü 960 × 868 (Skilltree hat jetzt 5 Reihen; `INFO_TOP` rechnet sich aus der Zahl der Reihen).

**Sichtfeld = alle Fenster, Tastenanzeige, Pause.**
- Spielfeld + Zusatzfenster sind das Sichtfeld (`PlayScene.in_sight`): Ein Gegner, der ganz in einem davon war, gilt
  als gesehen – Artillerie in einem Turm- oder Radarfenster gräbt sich ein, wenn das Schiff in Reichweite ist.
- Zusatzfenster verschwinden in Pause, Inventar und Shop (`view.hidden`, `ViewWindow.hide`) und kommen beim
  Weiterspielen wieder.
- Tastenanzeige: W A S D, darunter die Tasten der freigeschalteten Fähigkeiten (SHIFT, SPACE, B) und rechts eine Maus,
  deren Tasten beim Schießen leuchten (`KeyOverlay`: breite Tasten, mehrere Tasten pro Kappe, `mouse_buttons`).

**Spielfeld als Standard (`game/field.py`).**
- `Field` = Arena + alle Zusatzfenster, die mit ihr verbunden sind (überlappend/berührend, auch über andere Fenster).
  Wird pro Abfrage neu gebaut (`PlayScene.field()`), es sind nur ein paar Rechtecke.
- Wand = der ganze Außenrand des Feldes (offene Teile der Arena-Kanten + Kanten der verbundenen Fenster, wo das Feld
  nicht weitergeht). Alles fragt das Feld: Schüsse jeder Art (`wall_hit`), Explosionen (`clamp`, `walls_within`: ein
  erreichtes Stück Arena-Kante schiebt diese, ein Stück Fensterwand die Kante, über die der Schuss kam – wie Kugeln),
  Mausbereich (`rects` → `Engine.confine_mouse`), Sichtfeld (`sight`, `sees`: Arena + alle Zusatzfenster, auch
  unverbundene) für „gesehen“, Randmarker, Spawns und Radar.
- Maus: ClipCursor auf das umschließende Rechteck, in Lücken zurück aufs nächste Rechteck (`LayeredWindow`);
  Position per `GetCursorPos`. Zusatzfenster sind nicht mehr durchklickbar (sonst landet ein Klick auf dem Desktop),
  werden aber nie aktiv: `WS_EX_NOACTIVATE`, dazu eine eigene Fensterprozedur vor SDLs, die auf
  `WM_MOUSEACTIVATE` mit `MA_NOACTIVATE` antwortet. Verliert das Hauptfenster trotzdem den Fokus an ein eigenes
  Fenster, holt die Engine ihn zurück, ohne dass die Szene es merkt (`Engine.internal_focus_loss`) – keine Pause.
- Spawner: keine Gegner in Zusatzfenstern, Schwärme halten `SWARM_GAP` auch zu ihnen.
- Das Schiff bleibt in der Arena.

**Blickrichtung, Belagerung, Schild-Gegner, Einstellung Tasten-Anzeige.**
- Gegner haben eine Blickrichtung (`enemy.aim`, `turn_towards`, `facing`). Shooter, Sniper und Artillery drehen sich mit
  `turn_speed` und schießen nur im `fire_cone`, in Blickrichtung (`shoot_ahead`).
- Artillery: Zustände laufen / aufbauen / belagert / abbauen (`deploy` 0…1, Füße fahren aus und ein). Mindestabstand
  `min_range`: zu nah oder außer Reichweite → abbauen, laufen (bei zu nah: zurückweichen), dann wieder aufbauen.
- Neuer Gegner `shield` (`game/enemies/shield.py`, Skin `game/skins/shield.py`): dreht langsam, läuft nur in
  Schildrichtung, Dash wie ein Charger. `blocks()` hält Kugeln von vorne auf (Funken: `game/effects/spark.py`, kein
  Wall-Push); Raketen explodieren auch am Schild und treffen ihn. Ab Easy 2:30, Normal 1:30, Hard 0:45.
- Toolbox-Seite: Bereich „Einstellungen“ mit „Tasten-Anzeige beim Start einblenden“. Gespeichert unter `"settings"` in
  `data\cube_game.json`; Seite und Spiel schreiben nur ihren eigenen Teil (frisch gelesen vor dem Schreiben).

**Schaden über die Zeit, Panzerung, Treffer von der abgewandten Seite.**
- Phasen können jetzt auch die Arena ändern (`"arena": {"armor": "+3", "shrink_speed": "x1.5"}`), solange sie laufen.
  `armor` (Startwert unter `arena`): jeder Wand-Push ist so viele Pixel kürzer, mindestens `MIN_PUSH` (0,5 px).
- In allen Schwierigkeiten: Phasen mit mehr Gegner-Schaden (`contact_damage`/`projectile_damage`/`blast_damage`
  x1.25, x1.2) und härteren Wänden, jeweils mit Ansage.
- Treffer (`Arena.hit`): die Gesamtschrumpfung bleibt, verteilt sich aber nach der Schiffsposition – die Kanten weit
  vom Schiff rücken mehr ein (`HIT_SIDE_BIAS` in settings.py: 0 = gleichmäßig wie früher, 1 = am Rand alles von
  gegenüber).

**Rückstoß und Betäubung.**
- Trifft der Ansturm des Schild-Gegners das Schiff (und der Treffer zählt), wird es `knockback` Pixel zurückgestoßen
  (schnell, dann abklingend) und `stun_time` Sekunden betäubt: keine Bewegung, keine Schüsse, keine Fähigkeiten, keine
  Türme – nur Zielen. Punkte kreisen über dem Schiff. Allgemein: `Ship.knock()`, Gegner-Hook `Enemy.on_hit_ship()`.

**14.10.2026 (Claude, auf Wunsch gebaut): Skilltree als Graph, Energie, vier Waffen, Loadout.**
- Skilltree (`game/skill_tree.py`, gezeichnet von `game/skill_tree_panel.py`): Shop in der Mitte, Äste sternförmig
  (Ship, Energy, Gun → Machine gun / Cannon, Laser, Dash, Rocket, Scouting). Kleine Kreise, Details im Tooltip.
  Knoten können mehrere Voraussetzungen haben (`requires` ist ein Tupel). Spielmenü jetzt 1300 × 900.
- **Energie**: beide Waffen teilen sie (`Ship.fire`); leer = feuern nur so schnell, wie sie nachlädt.
  Anzeige unten links. Upgrades: Skilltree *Max energy* / *Energy regen*, Shop-Karten gleichen Namens.
- **Waffen** in `game/weapons/` (Werte: `data/weapons.json`): Gun (Start, nur 3 Upgrades), Machine gun (Streuung;
  Damage/Attack speed erhöhen sie, Precision senkt sie), Cannon (Piercing, danach weniger Wall Push), Laser (hinter
  beiden Energie-Knoten; viele winzige Schüsse, als Strahl gezeichnet). `upgrade_factor`: wie stark Karten pro Waffe wirken.
  Schüsse treffen entlang ihres ganzen Wegs im Tick (`Projectile.touches`), schnelle fliegen nicht durch kleine Gegner.
- **Rakete** startet schwächer (7 s, 3 Schaden, Radius 110), 4 Upgrades im Skilltree; *Burning ground* (15 Cores)
  hinterlässt brennenden Boden (`game/effects/burning_ground.py`).
- **Loadout**-Reiter im Spielmenü (`game/loadout_panel.py`): Waffen per Drag & Drop in LMB/RMB, gespeichert als
  `loadout` im Profil. Mindestens eine Waffe bleibt drin.
- **Panzerung jetzt in Prozent** (`armor` 20 = jeder Push 20 % kürzer, höchstens `MAX_ARMOR` 90 %), statt Pixel
  abzuziehen – sonst traf sie den Laser mit seinen vielen kleinen Pushes viel härter. Werte umgerechnet
  (früher +3 px ≈ jetzt +20 %, +2 px ≈ +15 %, Hard-Start 1 px ≈ 5 %).
- Offen / Ideen: Schadens-Abfall nach dem Durchbohren (bisher nur der Wall Push).
- Ideen für **Tauschkarten** (Vorteil + Nachteil, noch nicht gebaut – bräuchten Prozent-Werte statt fester Beträge):
  Glass Cannon (+50 % Schaden / −30 % Wall push), Bulldozer (+60 % Wall push / −40 % Schaden), Overcharge
  (+40 % Attack speed / +50 % Energy use), Battery (+50 Max energy / −30 % Regen), Capacitor (+50 % Regen / −40 Max
  energy), Sniper (+100 % Projectile speed / −25 % Attack speed), Short fuse (−40 % Raketen-Cooldown / −30 % Blast
  radius), Afterburner (+50 % Dash-Distanz / +50 % Dash-Cooldown), **Greed** (höhere Core-Chance / Arena schrumpft
  15 % schneller), Heavy hull (Treffer quetschen 25 % weniger / −15 % Move speed).

**14.10.2026 (Claude, auf Wunsch gebaut): Levels statt Schwierigkeiten, Gegner-Evolutionen (Tier 2), Level-Anzeigen.**
- **Levels** A1–A6, B1–B6, Survival ersetzen Easy/Normal/Hard (`data/difficulties/a1.json` …; im Code weiter
  „difficulty“). Jedes Level hat ein `goal` (Sekunden überleben = geschafft, schaltet das nächste frei, `unlock.requires`);
  der Run läuft danach weiter, oben steht bis dahin „01:23 / 03:00“. Survival (`goal: null`) ist endlos, frei nach B6.
  Alte Bestzeiten auf Easy/Normal/Hard gelten nicht mehr – man startet bei A1.
- A-Reihe mit Schwerpunkten: A1 nur Basic + Shooter, A2 Nahkampf, A3 Fernkampf, A4 Artillerie + Carrier, A5 sehr harte
  Wände, A6 alles. B-Reihe genauso, plus Evolutionen mit steigender Chance (B1 Fat Guy + Cannoneer, B2 Shield, B3
  Laser, B4–B6 alle). Gegnerzahl, Grund-HP (`enemy_stats`) und Dauer steigen mit.
- **Evolutionen** (`evolutions` im Level, `roster.EVOLUTIONS`, `Spawner.create`): es wird weiter Tier 1 gespawnt, aber
  mit einer Chance (wachsend pro Minute) kommt stattdessen Tier 2 – auch in Schwärmen. Tier-2-Skins haben einen dunklen
  Innenrahmen (`Enemy.tier`, `draw_tier_frame`).
  - **Fat Guy** (`fat`, aus Basic): größer, 8 HP.
  - **Cannoneer** (`cannoneer`, aus Shooter): sehr langsam, riesige langsame Kanonenkugel (`CannonBall`), 4 Schaden.
  - **Shield** (aus Charger): der bestehende Schild-Gegner, jetzt nur noch als Evolution.
  - **Laser** (`laser`, aus Sniper): dickere Ziellinie, dann ein Strahl für 0,5 s (`game/laser_beam.py`); Berührung
    = Schaden (einmal pro Strahl, auch Wachtürme). Stirbt der Laser, erlischt der Strahl.
- **Reiter *Levels*** im Spielmenü (`game/level_panel.py`, jetzt der erste Reiter): ein Knopf pro Level mit kleinen
  Anzeigen (Farbquadrat pro Gegnertyp, Symbol pro Art von Ereignis, Haken = geschafft), darunter Details zum Level unter
  der Maus: `hints` aus der Datei, Gegner ab wann (Evolutionen mit Chance), Ereignisse mit Zeit. Symbole in
  `game/icons.py`.
- **Gegnerschaden in Pixeln** (`contact_damage`, `projectile_damage`, `blast_damage`): so weit rücken die Kanten bei
  einem Treffer im Schnitt ein (`Arena.hit`). Vorher Punkte × `HIT_SHRINK` (25) – die Werte sind umgerechnet (Basic 25,
  Sniper 50, Kanonenkugel 100), im Spiel ändert sich nichts. Wachtürme: 150 HP statt 6, Lebensbalken statt Kästchen.
- Ziele verlängert: A1 3:00, A2/A3 3:30, A4/A5 4:00, A6/B1 5:00, B2/B3 5:30, B4/B5 6:00, B6 7:00. Die Phasen (mehr
  HP, mehr Schaden, härtere Wände, Wellen) sind über das Level verteilt, die letzte kurz vor dem Ziel; zwei weitere
  kommen danach für alle, die weiterspielen.
- **Karten erst über den Skilltree:** neuer Knoten *Card shop* (4 Cores, unter *Core luck*, `skill_tree.CARD_SHOP`).
  Ohne ihn gibt es den Reiter *Cards* nicht und aktive Karten wirken nicht (`start_ship`).
- Grundwerte gesenkt: Schiff 320 → 280 px/s (`SHIP_SPEED`), Gun 1 → 0,8 Schuss/s (`data/weapons.json`).
- Offen: **Boss** (T1 bei A6, T2 bei B2 mit mehr Fähigkeiten) – kommt als eigener Schritt.
- 14.10.2026 (Claude, auf Wunsch gebaut): **Schiffswerte in `data/ships.json`** (`game/ship_data.py`): Größe, Tempo,
  Energie, Unverwundbarkeit nach Treffer, Farbe, Name – ein Eintrag pro Schiff, `ship` wählt das geflogene. Ersetzt
  `SHIP_SIZE`, `SHIP_SPEED`, `SHIP_COLOR`, `INVULNERABLE_TIME` in `settings.py` und `energy.max` / `energy.regen` in
  `data/weapons.json` (dort bleibt nur `energy.tree`). Die Arena stoppt jetzt bei der Größe des geflogenen Schiffs.
- 14.10.2026 (Claude, auf Wunsch gebaut): Phasen können **einmalig Gegner dazuholen** (`spawn`) und das
  **Spawn-Tempo ändern** (`spawn_interval`), solange sie laufen (`Spawner.start_phases`, `Spawner.interval`). A1: die
  Shooter-Welle ab 1:00 bringt sofort 3 Shooter, und 20 s lang kommen die Gegner 40 % schneller.
- 14.10.2026 (Claude, auf Wunsch gebaut): Reiter *Levels* zeigt unter *Numbers* die Grundwerte des Levels (Arena,
  Wände, Spawn-Abstand, erster Gegner, Cores – mit *Bigger arena* / *Core luck* des Spielstands), und die Ereignisse
  nennen die Werte ihrer Phase (`level_panel.numbers`, `change_text`).
- 14.10.2026 (Claude, auf Wunsch gebaut): **Skilltree komplett in `data/skilltree.json`**: pro Knoten `costs` (Cores pro
  Stufe, Listenlänge = Zahl der Stufen) und was eine Stufe bringt (`per_level`, bei der MG dazu `spread_per_level`,
  bei Burning ground dessen Werte). Ersetzt `tree`, `spread_per_upgrade`, `burning` und `energy` in `weapons.json`,
  die `*_per_level` in `radar.json` und `HEAD_START_STARS`, `ARENA_BONUS`, `CORE_LUCK_BONUS` im Code; auch die Türme
  pro Stufe *Watchtower* sind jetzt einstellbar. `weapon.apply_tree` → `upgrade`, angewendet in `skill_tree.py`.
  `Profile.level()` deckelt bei weniger Stufen.
- 14.10.2026 (Claude, auf Wunsch gebaut): **Fähigkeiten in `data/abilities.json`** (`game/ability_data.py`): Dash
  (Cooldown, Distanz, Dauer) und Rakete (bisher in `weapons.json`; neu auch Tempo, Beschleunigung, Größe), dazu je
  `min_cooldown` – ersetzt die festen Werte in `dash.py` / `rocket.py` und die Minima der Cooldown-Karten.
- 14.10.2026 (Claude, auf Wunsch): Gegnerwert `max_hp` heißt jetzt **`base_hp`** – in `data/enemies.json`, in
  `enemy_stats` der Level-Dateien und im Code – ebenso beim Wachturm (`buildings.json`).
- 14.10.2026 (Claude, auf Wunsch): **Finale in jedem Level** (A1–B6): Phasen *Final wave!* und *Hold on!* kurz vor dem
  Ziel, beide enden beim `goal` (`data/difficulties/README.md`, Abschnitt Aufbau). A1 bewusst milder; in A1–A6 nur
  Tier-1-Gegner (Evolutionen bleiben den B-Levels vorbehalten).
- 14.10.2026 (Claude, auf Wunsch gebaut): **Schwierigkeit steigt von Level zu Level** (A1 und A2 unverändert). Vorher
  war A3 kaum schwerer als A1 und B3 leichter als A6 – A2 hatte Schwärme und eine dauerhafte Phase `spawn_interval`
  `"x0.75"`, A3 bis B6 nicht. Jetzt wächst jedes Level um etwa ein Viertel bis ein Drittel (Gegner-HP pro Sekunde,
  gewichtet nach Gefährlichkeit, mit Schwärmen, Evolutionen und Phasen), dazu die Last im Finale und der Wanddruck
  (Schrumpftempo ÷ (1 − Panzerung)) – jeweils am Ende des Ziels gemessen. A5 behält die härtesten Wände bis dahin
  (Panzerung am Ende 45 statt 60 %, damit A6 und später darüber bleiben). Die Grundwerte stehen direkt in `spawning`,
  ohne versteckte Dauerphasen.
- 14.10.2026 (Claude, auf Wunsch gebaut): **Jede Wellen-Ansage holt Gegner dazu** – wie in A1/A2: Phasen mit `weights`
  und `announce` (*Chargers incoming!*, *Snipers incoming!*, *The horde is coming!* …) haben jetzt ein `spawn` und
  meist ein kürzeres `spawn_interval`. Survival: *Evolution begins!* bringt 3 Fat Guys und einen Cannoneer.
- 14.10.2026 (Claude, auf Wunsch gebaut): **Neue Schiffswerte** – in `data/ships.json` (Grundwert), im Shop (Sterne),
  als Karte und (außer Magnet) im Skilltree unter *Bigger arena*:
  - **Armor** (`armor`, %): jeder Treffer quetscht die Arena so viel Prozent weniger (`Ship.absorb`), höchstens
    `MAX_SHIP_ARMOR` (60 %). Nicht verwechseln mit der Panzerung der Wände (`arena.armor` im Level).
  - **Recovery** (`invulnerable_time`, s): länger unverwundbar nach einem Treffer, höchstens `MAX_INVULNERABLE_TIME` (3 s).
    Der Grundwert ist dafür von 1 auf 0,5 s gesunken.
  - **Magnet** (`magnet_radius`, px): Sterne und Cores werden von weiter her angezogen (ersetzt `MAGNET_RADIUS` in
    `star_pickup.py`).
  Karten können jetzt auch ein `maximum` haben (wie `minimum` bei Cooldowns). Der Shop hat drei Spalten (Ship | Weapons,
  Dash | Rocket, Watchtower), das Inventar und die Schiffsspalte im Spielmenü zeigen die neuen Werte.
- 14.10.2026 (Claude, auf Wunsch gebaut): **Shop nach Ausrüstung**: Der Shop im Run zeigt nur, was das Schiff hat –
  Ship, je ausgerüstete Waffe ein eigener Abschnitt (*Gun (LMB)*, *Cannon (RMB)* … in ihrer Farbe), Dash, Rocket und
  Watchtower erst, wenn freigeschaltet (statt „locked“). Die Waffen-Upgrades wirken nur auf die Waffe ihres Slots und
  haben je eigene Preise (`WeaponCard.for_slot`, `Shop.sections`). Karten aus dem Karten-Shop wirken weiter auf alle
  Waffen, weil sich das Loadout zwischen Runs ändern kann.
- 14.10.2026 (Claude, auf Wunsch gebaut): **Jedes Waffen-Upgrade gilt nur für eine Waffe** – jetzt auch die Karten:
  `damage`, `attack_speed`, `wall_push`, `projectile_speed` gibt es einmal pro Waffe (`damage:gun`, `damage:cannon` …,
  `WeaponCard`, `cards.make_cards`), mit dem Waffennamen im Band und ihrer Farbe. Eine aktive Karte wirkt nur, solange
  ihre Waffe in einem Slot ist (die Zeile unter den Karten sagt es sonst). Der Karten-Shop bietet sie für jede
  freigeschaltete Waffe an. Die Zahl auf der Karte ist, was sie dieser Waffe wirklich gibt (`card_amount` ×
  `upgrade_factor`, Laser-Schaden also +0,04). Die Zahlen in `upgrades.json` bleiben pro Wert, für alle Waffen gleich.
  Alte Spielstände: Waffenkarten von früher (für alle Waffen) werden zur Karte der Waffe in Slot 1 (`cards.saved_key`).
- 14.10.2026 (Claude, auf Wunsch gebaut): **Aktive Karten über den Skilltree**: Mit dem Karten-Shop ist erst **eine**
  Karte gleichzeitig aktiv (`max_active` 1 in `upgrades.json`). Der neue Knoten *Card slots* (unter *Card shop*,
  2 Stufen, 10 und 20 Cores) gibt je eine mehr, also höchstens 3 (`Profile.max_active_cards`). Alte Spielstände mit
  mehr aktiven Karten behalten die erste aktiv, die anderen sind inaktiv, bis die Slots gekauft sind.
- 14.10.2026 (Claude, auf Wunsch gebaut): **Panzerung überall flach** (`game/armor.py`): Wände, Schiff und – neu –
  Gegner ziehen einen festen Betrag ab statt Prozent, mit einem Rest, der immer bleibt (`MIN_PUSH_SHARE` 10 %,
  `MIN_HIT_SHARE` 25 %, `MIN_DAMAGE_SHARE` 15 % in `settings.py`; ersetzt `MAX_ARMOR` und `MAX_SHIP_ARMOR`). Wand-
  Panzerung der Level umgerechnet (Prozent × 0,35, auf 0,5 px gerundet: A5 7 px am Start, B6 bis über 20 px). Schiff:
  Shop +2 px, Karte +6 px, Skilltree +3 px pro Stufe. **Gegner-Panzerung** (`armor` in `enemies.json`, Standard 0 über
  `roster.COMMON_STATS`, wirkt in `Enemy.take_damage`): Fat Guy, Shield, Cannoneer 1, Carrier, Artillery 0,5.
  **Machine gun** dafür stark gegen Ungepanzerte, schwach gegen Panzerung und Wände (4 Schuss/s, 6 px Wall push,
  2,5 Energie), **Cannon** das Gegenteil (9 Schaden, 90 px Wall push, 0,5 Schuss/s, 25 Energie).
- 14.10.2026 (Claude, auf Wunsch gebaut): **Artillery als Katapult, sichtbare Granaten, Cluster (T2)**.
  - Die Artillery wirft mit einem Katapultarm statt mit dem Mörser (`arm`, `loaded`, `swing_arm` in
    `enemies/artillery.py`, gezeichnet in `skins/artillery.py`): Arm hinten mit Granate, schwingt in `swing_time` nach
    vorn, lässt senkrecht los, kurbelt beim Nachladen zurück.
  - Granaten fliegen sichtbar im Bogen mit Schatten (`ArtilleryStrike` mit `Arc`, `draw_air` über den Gegnern);
    Flugbahn einstellbar: `fill_time` (Flugzeit), `arc_height`, `arc_steepness`, `arc_peak`, dazu `shell_size`.
  - **Cluster** (`enemies/cluster.py`, Evolution der Artillery): Splittergranate ohne eigenen Schaden, platzt in 3
    Splitter (`split_…`-Werte, `Split`, `ArtilleryStrike.fragments`) mit kleinen Kreisen, weit verstreut. Kommt als
    Evolution in B4 (dort auch eine in *Artillery incoming!*), B5, B6 und Survival (ab 6:00).
- 14.10.2026 (Claude, auf Wunsch gebaut): Carrier: neuer Wert **`spawn_amount`** – so viele Critter setzt er nach der
  ersten Welle jedes Mal aus (Standard 1 wie bisher), nie über `max_critters`.
- 14.10.2026 (Claude, auf Wunsch gebaut): **`data/shop.json`** für alles, was man im Run mit Sternen kauft
  (`game/shop_data.py`): pro Upgrade `amount`, `price`, `price_step` (bisher in `upgrades.json`) und unter `watchtower`
  der Turmpreis (bisher in `buildings.json`). `upgrades.json` hat nur noch `card_amount` und die Regeln des
  Karten-Shops; liegt ein Wert in der falschen Datei, warnt das Spielmenü (`cards.read_numbers`).
- 14.10.2026 (Claude, auf Wunsch gebaut): **`shop.json` mit einem Eintrag pro Shop-Zeile**: jede Waffe hat ihre eigenen
  (`gun_damage`, `mg_damage`, `cannon_wall_push`, `laser_projectile_speed` …), dazu `rocket_blast_radius` und
  `watchtower_vision` (`card.shop_key`, `shop_data.read_upgrades`). `amount` ist genau, was eine Stufe der Waffe gibt –
  der `upgrade_factor` gilt nur noch für Karten; die Werte sind umgerechnet (z. B. `mg_damage` 0,15), im Spiel ändert
  sich nichts. Alte Namen meldet das Spielmenü mit dem neuen.
- 14.10.2026 (Claude, auf Wunsch gebaut): **Dash im Skilltree**: *Distance* (3 Stufen, +25 px) und *Charges* (2 Stufen,
  +1 Ladung) hinter *Dash* (`skill_tree.build_dash`, `Dash.upgrade`). Fähigkeiten können jetzt **Ladungen** haben
  (`Ability.max_charges`, `charges`): jede Nutzung nimmt eine, der Cooldown füllt eine nach der anderen auf – mit einer
  Ladung wie bisher. Grundwert `charges` des Dash in `abilities.json` (1). Die Fähigkeitenanzeige unten links zeigt
  z. B. „SHIFT  Dash  2/3  1.4s“, Inventar und Spielmenü die Zahl der Ladungen.
- 15.10.2026 (Claude, auf Wunsch): **Shot speed heißt überall Projectile speed** – auch die Schlüssel: Karte
  `projectile_speed` (`game/cards/projectile_speed.py`), Shop `gun_projectile_speed` …, Skilltree
  `mg_projectile_speed` / `cannon_projectile_speed`, Gegnerwert `projectile_speed` in `enemies.json`, Waffen-Attribut
  `Weapon.projectile_speed`. Alte Spielstände werden beim Laden umbenannt (`cards.RENAMED`, `profile.RENAMED_NODES`).
- 15.10.2026 (Claude, auf Wunsch): **Auch `shot_damage` und `shot_size` heißen jetzt `projectile_damage` /
  `projectile_size`** (Gegnerwerte in `enemies.json` und den Level-Dateien, Waffen-Attribut). Alte Namen in
  Datendateien meldet das Spielmenü mit dem neuen (`roster.RENAMED`).
- 15.10.2026 (Claude, auf Wunsch): **Cannon *Damage* kostet Energie**: jede Stufe +1 Energie pro Schuss
  (`energy_per_level` in `skilltree.json`). Nebenwirkungen von Knoten stehen jetzt allgemein in
  `skill_tree.SIDE_EFFECTS` (auch die Streuung der MG, `spread_per_level`).
- 15.10.2026 (Claude, auf Wunsch gebaut): **Minen** – Skilltree-Knoten *Mines* hinter *Charges* (Dash-Zweig,
  25 Cores): Jeder Dash lässt dort, wo er begann, eine Mine liegen (`game/mine.py`, `Dash.mines`). Sie geht hoch,
  wenn ein Gegner sie berührt oder die schrumpfende Wand sie erreicht – 3 Schaden, Explosionsradius 40 px,
  100 px Wall push, Größe 8 px (`mines` in `skilltree.json`, keine Upgrades). Für die Spielszene ist sie ein
  Spielerschuss, der sich nicht bewegt, und explodiert wie die Rakete (`PlayScene.explode`).
- 15.10.2026 (Claude, auf Wunsch gebaut): **Slow field** – Skilltree-Knoten hinter *Mines* (30 Cores): Die
  Explosion einer Mine lässt ein Feld zurück, in dem Gegner langsamer sind (20 %, 60 px Durchmesser, 3 s;
  `game/effects/slow_field.py`, `Enemy.slow` – gilt für jede Bewegung, das stärkste Feld zählt). Upgrades
  *Strength* (+5 %), *Size* (+15 px), *Duration* (+1 s), je 3 Stufen. Die Grundwerte von Mine und Slow field
  stehen jetzt in `abilities.json` (`mine`, `slow_field`), im Skilltree nur noch die Kosten. Der Skilltree ist
  etwas schmaler gesetzt (`UNIT` 70 statt 78 px), damit rechts Platz für die neuen Knoten ist.
- 15.10.2026 (Claude, auf Wunsch gebaut): **Burning ground** braucht jetzt *Cooldown*, *Blast radius* und *Damage*
  der Rakete **voll ausgebaut** (`Node.requires_max`, `Profile.missing`; Tooltip: „needs … (max)“). Schon gekauft
  bleibt gekauft. Neuer Knoten **Power** hinter *Mines* (3 Stufen, 6/12/20 Cores): +1 Schaden und +10 px
  Explosionsradius pro Stufe (`mine_power` in `skilltree.json`, `skill_tree.upgraded`; `SIDE_EFFECTS` kann jetzt
  auch `blast_radius_per_level`).
- 15.10.2026 (Claude, auf Wunsch gebaut): **Wachturm umgebaut**: unverwundbar statt Lebenspunkte (Gegnerschüsse,
  Strahlen und Artillerie gehen durch bzw. treffen ihn nicht), dafür **10 s Lebenszeit** nach der Landung
  (`lifetime`, Zeitbalken über ihm, blinkt in den letzten 2 s). Gegner in seinem Fenster (dünn umrandet) nehmen
  **+20 % Schaden** (`damage_bonus` in `buildings.json`, `PlayScene.expose_enemies`, `Enemy.damage_factor` – nach
  der Panzerung, Türme addieren sich nicht). Sichtfenster und Anlocken bleiben. `base_hp` und `hit_cooldown`
  sind weg (das Spielmenü meldet sie, falls sie noch in der Datei stehen).
- 15.10.2026 (Claude, auf Wunsch gebaut): **Zwischenspeicher für Bilder** (`engine/sprite_cache.py`): Was jedes Bild
  gleich aussieht, wird einmal gemalt und danach nur noch kopiert – Gegner-Körper (pro Größe, Tier, weiß beim
  Treffer), Buff-Rand, Lebenspunkte, Grund von *Burning ground* und *Slow field* (Glut/Ringe kommen live drauf,
  das Ausblenden macht `set_alpha`), Wachturm-Bereich und der Rand-Umriss der Zusatzfenster (nur neu, wenn ein
  Fenster sich bewegt). Sieht pixelgenau gleich aus (geprüft); gemessen pro 100 Gegner: Basic 0,84 → 0,28 ms,
  Shield 1,23 → 0,66 ms, Artillery 1,74 → 1,21 ms (Arm und Füße bleiben live gezeichnet); Rand-Umriss
  0,5 → 0,06 ms. Neue Hilfen: `PICTURES.get(key, make)`, `scratch(size)`, `load_picture(path)`.
- 15.10.2026 (Claude, auf Wunsch gebaut): **Eigene Gegner-Bilder**: `assets/images/<gegner>.png` (z. B.
  `shooter.png`, Schlüssel wie in `enemies.json`) ersetzt den Körper des Gegners – nach rechts blickend malen, er
  dreht sich mit (`TURN_STEP` 5°, die gedrehten Bilder werden beim ersten Bedarf gemacht und gespeichert), weiß beim
  Treffer, Seitenverhältnis bleibt. Kein Tier-Rahmen (Evolutionen haben eigene Dateien). Läufe, Lebenspunkte und
  Buff-Rand bleiben. Kaputte Datei = wieder das Quadrat. Anleitung und Knopf *Bilder-Ordner öffnen* auf der
  Toolbox-Seite. Gelesen beim Spielstart, nicht während des Spiels.
- 17.10.2026 (Claude, auf Wunsch gebaut): **Balance nach Bot-Tests** – nur Datendateien, kein Code. Getestet mit
  einem Bot, der die echte `PlayScene` ohne Fenster spielt (je 10 Runs pro Level mit meinem Spielstand und 6
  Kampagnen von einem neuen Spielstand bis B6, der Bot kauft im Shop und im Skilltree):
  - **Start:** In jedem Level kommt der erste Gegner nach 0,5 s, dazu eine Phase 0–20 s mit 4 Basics sofort und
    halben Abständen. Im Fenster ist jetzt in den ersten 30 s etwa 70 % der Zeit ein Gegner statt 30–45 %, und es gibt
    doppelt so viele Kills. Die A-Level werden dadurch kaum schwerer.
  - **Cores:** B-Level und Survival hatten `core_chance: 1` (600–1700 Cores pro Run, ein B-Run kaufte fast den halben
    Skilltree). Jetzt gibt es eine gleichmäßige Kurve: Ein Run bis zum Ziel bringt etwa 12 Cores in A1 und bis zu 95 in B6
    (Werte in `data/difficulties/README.md`). In den Test-Kampagnen waren nach A6 ca. 635, nach B3 ca. 1200 Cores
    ausgegeben, voll ist der Skilltree während B4.
  - **A2:** Die Wände ziehen langsamer (6 → 4 px/s am Anfang, Grenze 20 → 18). Dafür brauchte der Bot im Schnitt
    5 statt 16 Runs.
  - **B3:** Weniger Fernkampf: Shooter 30 → 22, Sniper 20 → 15 Gewicht (Wachstum 4 → 3), Chance auf Cannoneer
    höchstens 25 statt 35 %, auf Laser 30 statt 40 %. Vorher schaffte der Bot B3 in ca. 1 % der Runs, jetzt in 30–50 %.
  - **B1–B6:** Die „Enemies hit harder!“-Phasen vor dem Ziel stapeln sich weniger: ×1,1 statt ×1,2/×1,25, die letzte
    (*Hold on!*) ×1,15. Kurz vor dem Ziel treffen Gegner jetzt ×1,4 (B6: ×1,5) so hart statt ×1,7 (B6: ×2,25).
  - **Shop:** Die erste Stufe ist günstiger, 6 statt 10 Sterne und dann +4 statt +5 (`shop.json`, alle Preise
    ×0,6, jede Stufe einen Stern weniger mehr). Die Wachtürme kosten weiter 10.
  - Ergebnis in den Kampagnen: Alle 6 schaffen bis B4, 5 auch B5 (vorher war bei B3 Schluss). B4–B6 schafft der
    Bot selten (B4 4 %, B6 0 % pro Run), auch mit vollem Skilltree und besserem Zielen. Das liegt eher an seiner
    Spielweise als an einem einzelnen Wert (B4 mit Wandpanzerung 5 statt 7 war nicht leichter), darum habe ich dort
    nichts weiter geändert. **Selbst testen.**
  - Offen: Die häufigsten Treffer sind fast überall Shooter-Schüsse. Shooter feuern ab 520 px (`fire_range`), also oft
    von außerhalb des Fensters. Eine kleinere Reichweite wäre eine Idee. Ideen für die Wände (noch nicht gebaut):
    Wand-Reparatur im Shop, Wandbrecher-Gegner, Abprall-Schüsse, Gegner zerquetschen, „atmende“ Arena, Wand-Mine.
- 17.10.2026 (Claude, auf Wunsch gebaut): **Zufall in Phasen, atmende Arena, Dash ohne Schaden.**
  - **`one_of`** in einer Phase: eine Liste von Möglichkeiten (mit `weight`), jeder Run würfelt eine aus
    (`difficulty.chosen()`, beim Start im `Spawner`). Sie kommt zu dem dazu, was direkt in der Phase steht. Im
    Spielmenü steht jede Möglichkeit als eigene Zeile mit Würfel-Symbol (`draw_random_icon`) und ihrer Chance.
  - **`breathe`** in einer Phase (nur mit `to`): Jede Kante rückt über die Dauer zusätzlich so viele Pixel ein und
    federt danach genauso weit zurück (`Arena.breathe()`, über `pending`, ohne Panzerung und Falloff). Wer
    währenddessen schiebt, hat danach mehr Platz.
  - **Dash:** 0,2 s ab Beginn des Dashs trifft nichts das Schiff (`invulnerable_time` in `abilities.json`,
    `Ability.protects`, `Ship.hit`). Man kann durch Gegner und Schüsse dashen. Im Bot-Test ca. 10 % weniger Treffer
    in B.
  - Beides steht noch in keinem Level, Beispiele in `data/difficulties/README.md`.
  - Ideen (noch nicht gebaut): Gegner mit eigenem Fenster, Gegner, der das Hauptfenster verschiebt, Commander (bufft
    Gegner in seiner Nähe, auch mitten in Schwärmen), C-Level nur mit T2 und neuen Gegnern, Themen-Level, periodische
    Phasen („alle x Sekunden“), Points of Interest außerhalb des Fensters.
- 17.10.2026 (Claude, auf Wunsch gebaut): **Periodische Phasen, Commander, Pusher, Points of Interest, C-Level.**
  - **`every`** in einer Phase: wiederholt sie alle x Sekunden (`Spawner.repeat_phases`, jede Wiederholung eine eigene
    Phase, `one_of` würfelt neu). Im Spielmenü „– every 01:00“.
  - **Commander** (`game/enemies/commander.py`): Aura (dünner goldener Ring), Gegner darin werden schneller und treffen
    härter, goldener Rand (`Buff.source`/`Buff.color`, `Enemy.renew_buffs`, `Enemy.commands`). Schwärme können einen
    `leader` haben: Er steht genau in ihrer Mitte (`leader_chance`).
  - **Pusher** (`game/enemies/pusher.py`): kommt von jenseits des Kartenrands (`spawns_outside`), läuft durch andere
    Gegner (`Enemy.solid`), packt die Arena von außen und schiebt das ganze Fenster (`Arena.shove`; am Bildschirmrand wird
    es schmaler). Treffbar ist nur der Arm (sein `rect`), der Körper ist gepanzert. Eigenes kleines Fenster mit rotem
    Rahmen (`PlayScene.update_lookouts`, `Field` `lookouts`: nur Sicht, kein Spielfeld).
  - **Rand-Markierungen:** Ein Schwarm außerhalb der Sicht zeigt ein Schwarm-Symbol statt vieler Punkte, größer, je
    näher er ist (`Enemy.swarm`, `spawner.Swarm`). Points of Interest bekommen Pfeile mit „?“ bzw. ihrem Symbol.
  - **Points of Interest** (`game/points.py`, `data/points.json`): Funde (Sternentruhe, Magnet, Reparatur-Kit) über
    den neuen Skilltree-Zweig hinter dem Wachturm (*Points of interest*, *Magnet*, *Repair kit*, *More finds*), Gefahren
    (Totem, Nest, Sturm) über `points` in Level-Phasen. Unbekannt („?“), bis man sie sieht; erreicht, wenn Spielfeld oder
    Turmfenster sie überdecken. Radar-Upgrade *Find*: ein Teil der Scans deckt einen unentdeckten auf. Die Radar-Knoten
    im Skilltree sind dafür etwas nach rechts gerückt.
  - **Level neu** (alle Phasen): HP-, Schadens- und Wand-Steigerungen sind jetzt periodisch und laufen nach dem Ziel
    weiter. Die meisten Level würfeln eine Welle aus (`one_of`). A5, B4 und B6 atmen einmal vor dem Ziel. Nach dem Ziel
    kommen in jedem Level alle 45 s eine Zufallswelle, alle 80 s ein Atemzug und ab B1 alle 2 Minuten eine Gefahr.
  - **C1–C6** (nur Evolutionen und die neuen Gegner, je ein Thema: Commander, Blitz, Pusher, atmende Arena, Gefahren,
    Chaos). Freigeschaltet durch B6, wie Survival. Survival steht jetzt in der C-Reihe (`order` 27, 7 Knöpfe pro Reihe)
    und bringt ab 7:00 Commander und Pusher, ab 8:00 Gefahren.
  - **Living Window** (`game/enemies/living_window.py`): dockt an eine Kante an, gleitet um die Arena (Position als
    Strecke im Uhrzeigersinn), wächst, schickt Gegner heraus, platzt bei `max_size`. Größe = Leben, Treffer schrumpfen
    es. Eigenes Fenster wie der Pusher. In C5, C6 und Survival.
  - Bot-Test mit vollem Skilltree (Sekunden bis zum Zerquetschen): B4 ca. 230, B5 ca. 220, B6 ca. 155–170, C1–C6
    meist 110–150. A1–B3 wie vorher (neue Kampagnen bis B3 im Schnitt 29 Runs, wie vorher). Der Bot schafft ab B4
    kaum noch etwas, und in C streuen seine Zeiten stark (C3 zwischen 116 und 188 s bei kleinen Änderungen) – die
    C-Level müssen selbst angespielt werden.
