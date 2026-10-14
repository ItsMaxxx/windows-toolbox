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
- **Ausnahme:** Die Anbindung an die Toolbox (`cube_game_gui.py`, `programm.json`, Einträge in `setup\`) ist
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
| `programm.json` | Ausweis für die Toolbox: Name, Tab, Version, Skript, Starter |
| `CubeGame.exe` | Starter, legt `Setup.exe` an (nicht im Repo) |

Wenn `cube_game.py` zu groß wird (Faustregel: ab ca. 300–400 Zeilen oder wenn ich scrollen muss, um etwas zu
finden), teile ich es auf. Ein möglicher späterer Aufbau, **nicht** jetzt schon anlegen:

```
programme/cube_game/
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
runtime\python.exe programme\cube_game\cube_game.py
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
*Lernen:* Dateien lesen/schreiben, JSON. Die Toolbox hat dafür `toolbox\daten.py`
(`daten.einstellungen("cube_game")` ergibt `daten\cube_game.json`); danach kann die Toolbox-Seite den Rekord anzeigen.

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
  gespeichert in `daten\cube_game.json` (`profile.py`). **Spielmenü** zwischen den Runs (`game_menu_scene.py`):
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
  Bildschirm ist (keine Lücken, nicht unter Taskleisten; `engine/desktop.py`, `Desktop.covers()`). Abschalten:
  `ALL_MONITORS` in `settings.py`. Die Engine zeichnet jetzt direkt in den Speicher des Fensters (kein Kopieren).
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
- Karte *Shot speed* heißt jetzt *Projectile speed* (Schlüssel bleibt `shot_speed`, steht in Spielständen). Grundkanone
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
  `daten\cube_game.json`; Seite und Spiel schreiben nur ihren eigenen Teil (frisch gelesen vor dem Schreiben).

**Schaden über die Zeit, Panzerung, Treffer von der abgewandten Seite.**
- Phasen können jetzt auch die Arena ändern (`"arena": {"armor": "+3", "shrink_speed": "x1.5"}`), solange sie laufen.
  `armor` (Startwert unter `arena`): jeder Wand-Push ist so viele Pixel kürzer, mindestens `MIN_PUSH` (0,5 px).
- In allen Schwierigkeiten: Phasen mit mehr Gegner-Schaden (`contact_damage`/`shot_damage`/`blast_damage` x1.25, x1.2)
  und härteren Wänden, jeweils mit Ansage.
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
