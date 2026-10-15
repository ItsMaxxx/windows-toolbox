# Last Bastion

Echtzeit-Strategie ums Überleben: Einheitensteuerung wie in **StarCraft**, Horden und Rundenaufbau wie in
**They Are Billions**, Ressourcen-Logistik wie in **Factorio** – in Runden von etwa 30 Minuten. *Last Bastion* ist ein
Arbeitstitel.

Stand: **Konzept**. Das ganze Design steht in [DESIGN.md](DESIGN.md) (auf Englisch) – in der Toolbox öffnet es der
Knopf „Design-Dokument öffnen“ auf der Seite von Last Bastion.

---

## Regeln für Claude (bitte zuerst lesen)

Wie beim Cube Game – hier noch einmal, weil `CLAUDE.md` und Claudes Memory nur lokal liegen:

- **Ich (Maximilian) schreibe den Code für das Spiel selbst.** Claude schreibt **keinen** Spielcode und liefert keine
  fertigen Lösungen, nur auf Anfrage.
- **Was Claude darf:** beraten, Konzepte erklären, das Design-Dokument mit mir weiterentwickeln, Fragen beantworten,
  Fehlermeldungen erklären, meinen Code reviewen, auf die passende Doku zeigen.
- **Erst einen Tipp, dann die Lösung.**
- **Ausnahme:** Die Anbindung an die Toolbox (`last_bastion_gui.py`, `program.json`, `i18n.json`, Einträge in
  `setup\`) ist Infrastruktur; die darf Claude wie den Rest der Toolbox pflegen. Ebenso `DESIGN.md`.
- `last_bastion.py` ist bis zum ersten Prototyp nur ein Platzhalter (zeigt einen Hinweis) – den ersetze ich selbst.

---

## Dateien

| Datei | Was |
|---|---|
| `DESIGN.md` | Design-Dokument: Säulen, Ablauf einer Runde, Wirtschaft, Einheiten, Zombies, Karte, Fahrplan, offene Fragen |
| `last_bastion.py` | Einstiegspunkt des Spiels (noch Platzhalter) – den startet `LastBastion.exe` |
| `LastBastion.exe` | Starter (legt Setup.exe an), damit der Task-Manager „Last Bastion“ statt „Python“ zeigt |
| `last_bastion_gui.py` | Seite in der Toolbox: Design-Dokument, Spielen, Ordner |
| `program.json` | Ausweis für die Toolbox (Name, Tab „Games“, Skript, Starter) |
| `i18n.json` | Texte der Seite und des Platzhalters auf Deutsch und Englisch |

## Einrichten

Neue Programme sind nach dem Klonen bzw. nach einem Update noch nicht eingerichtet: In der Toolbox auf das Zahnrad →
bei **Last Bastion** auf **Installieren**. Setup baut dann `LastBastion.exe`, und das Spiel erscheint im Tab „Games“.

## Fahrplan

Die Prototyp-Schritte stehen in [DESIGN.md, Abschnitt 13](DESIGN.md#13-prototype-roadmap) – zuerst die
Einheitensteuerung, dann der Horden-Stresstest. Davor fällt die Wahl der Sprache: Rust oder C/C++/C#, kein Python
(DESIGN.md, Abschnitt 12.2). Mit einer kompilierten Sprache startet die Toolbox-Seite später die gebaute `.exe` statt
`last_bastion.py` (kleine Änderung in `last_bastion_gui.py` und `program.json`).

## Stand

- **2026-10-15:** Konzept als `DESIGN.md` angelegt, Programm an die Toolbox angebunden (Seite, Starter, Platzhalter).
  Offene Grundsatzfragen: Sprache, Perspektive, Einzelspieler/Koop (DESIGN.md, Abschnitt 14).
- **2026-10-15:** Einheiten überarbeitet (TAB-Infanterie, SC-Medic, Siege Tank, MG-Schütze); Blight heißt jetzt Creep;
  keine Bosse (nur Riesen wie in TAB); keine Förderbänder; Meta-Fortschritt wie in TAB ohne Kampagne; Endlos-Modus
  statt Kampagne/Daily Challenge; Sprache Rust oder C-Familie.
