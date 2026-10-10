# Cube Game

Du spielst eine **weiße Box**. In regelmäßigen Abständen tauchen **rote Cubes** auf; berührst du einen, kostet das
Leben. Steuerung vorerst nur **W A S D**.

Das Spiel ist ein **Lernprojekt**: Game Design und Programmierung von Grund auf, ohne fertige Engine (kein Godot,
Unity, Unreal – bewusst so entschieden). Später sollen eine eigene kleine Engine und ein eigener Map-Editor dazukommen,
nach dem Vorbild des StarCraft-2-Editors.

---

## Regeln für Claude (bitte zuerst lesen)

Diese Regeln gelten auf jedem PC und in jeder Sitzung. Hier stehen sie, weil `CLAUDE.md` und Claudes Memory nur lokal
liegen und nicht mit Git mitwandern.

- **Ich (Maximilian) schreibe den Code für Spiel, Engine und Editor selbst.** Claude schreibt **keinen** Spielcode und
  liefert keine fertigen Lösungen, auch keine „nur als Beispiel“.
- **Was Claude darf:** beraten, Konzepte erklären, Fragen beantworten, Fehlermeldungen erklären, meinen Code
  reviewen, Hinweise geben, auf die passende Doku zeigen, Pseudocode bzw. Schritte in Worten beschreiben.
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

-
