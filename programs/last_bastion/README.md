# Last Bastion – Anbindung an die Toolbox

Last Bastion ist ein Echtzeit-Strategiespiel (StarCraft × They Are Billions × Factorio) mit **eigenem Repository**,
getrennt von der Toolbox. Das Spiel, sein Design-Dokument (`DESIGN.md`) und die Regeln für Claude liegen dort.

Hier in der Toolbox liegt nur die **Seite** im Tab „Games“:

- **Spielordner:** Ohne Auswahl sucht die Seite `last-bastion` neben dem Toolbox-Ordner (z. B.
  `E:\Software\last-bastion`). Liegt das Spiel woanders, merkt sich „Spielordner wählen“ den Ordner in
  `data\last_bastion.json` („game_folder“).
- **Design-Dokument öffnen:** öffnet `DESIGN.md` aus dem Spielordner.
- **Spielen:** startet `dist\LastBastion.exe` aus dem Spielordner.

Pfade im Spiel-Repo, auf die sich die Seite verlässt (Abmachung, siehe `DESIGN.md` dort, Abschnitt 12.7):
`DESIGN.md` im Hauptordner und das gebaute Spiel unter `dist\LastBastion.exe`. Ändern sie sich, `GAME_EXE` bzw.
`DESIGN` oben in `last_bastion_gui.py` anpassen.

## Dateien

| Datei | Was |
|---|---|
| `last_bastion_gui.py` | Seite in der Toolbox: Spielordner, Design-Dokument, Spielen |
| `program.json` | Ausweis für die Toolbox (Name, Tab „Games“, Seite) – kein Skript, kein Starter |
| `i18n.json` | Texte der Seite auf Deutsch und Englisch |

## Einrichten

1. Spiel-Repo klonen, am einfachsten neben die Toolbox: `E:\Software\last-bastion`.
2. In der Toolbox auf das Zahnrad → bei **Last Bastion** auf **Installieren**. Die Seite erscheint im Tab „Games“.

## Stand

- **2026-10-15:** Konzept angelegt, Programm an die Toolbox angebunden (Seite, Starter, Platzhalter).
- **2026-10-15:** Das Spiel hat jetzt ein eigenes Repo (`DESIGN.md` ist dorthin umgezogen). Hier bleibt nur die Seite;
  Platzhalter `last_bastion.py` und Starter `LastBastion.exe` sind weg.
