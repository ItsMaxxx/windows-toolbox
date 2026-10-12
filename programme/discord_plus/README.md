# Discord Plus

Erweiterungen für Discord, die im Hintergrund laufen. Bisher eine Funktion:

**Call-Status** – zeigt in Discord „Im Call“ an, sobald du in einem Anruf oder Voice-Chat bist – auch für Freunde, die
den Server oder den Anruf gar nicht sehen können. Discord selbst zeigt Server-Voice-Chats nur Leuten mit Zugriff auf den Server und
private Anrufe niemandem.

Wie: Das Programm setzt eine eigene **Aktivität** (Rich Presence, „Spielt …“) – dieselbe Anzeige, die auch Spiele
nutzen. Die sehen alle, die auch sonst sehen, was du spielst. Ein *eigener Status* (der Text unter deinem Namen) ginge
nur mit deinem Konto-Token; Tools, die so als dein Konto handeln, verbietet Discord – Sperrgefahr. Deshalb nicht.

Läuft als eigenes Programm **ohne Adminrechte**, unsichtbar mit einem Symbol im Infobereich. Bedient und eingestellt
wird es über seine Seite in der Toolbox (*Allgemein → Discord Plus*) – dort steht auch die Anleitung zur einmaligen
Einrichtung.

## Dateien

| Datei | Inhalt |
|---|---|
| `discord_plus.py` | das Programm: fragt Discord ab, setzt die Aktivität, Symbol im Infobereich, Fernsteuerung durch die Toolbox |
| `discord_ipc.py` | spricht mit der Discord-App (Named Pipe) und mit discord.com (Anmeldung) |
| `discord_plus_einstellungen.py` | Startwerte, Laden/Speichern und **was** angezeigt wird (`aktivitaet()`) – gemeinsam für Programm und Seite |
| `discord_plus_gui.py` | Seite in der Toolbox: Status, Einrichtung mit Anleitung, Anzeige-Einstellungen, Vorschau, Autostart |
| `programm.json` | Ausweis: Name, Tab, Beschreibung, Version, Skript, Starter, Port, Name des Autostart-Eintrags |
| `DiscordPlus.exe` | Starter (legt `Setup.exe` an, nicht im Repo) |
| `discord_plus.ico` | Logo: Discord-Kreis mit dem Gesicht aus `logo_quelle.png` – in beiden `.exe` und im Infobereich |
| `logo_quelle.png`, `logo_bauen.py` | Vorlage und Skript, das daraus `discord_plus.ico` baut (nur nach einer neuen Vorlage nötig) |
| `daten/discord_plus.json` (im Hauptordner) | Einstellungen samt Client-ID und Client-Secret (nicht im Repo) |
| `daten/discord_plus_anmeldung.json` (im Hauptordner) | Anmeldung bei Discord (Token) – schreibt nur das Programm (nicht im Repo) |
| `daten/logs/discord_plus.log` (im Hauptordner) | Fehler und Hinweise (nicht im Repo) |

## Einrichtung

1. In der Toolbox: Zahnrad → *Programme* → Discord Plus *Installieren* (legt `DiscordPlus.exe` an).
2. Auf der Seite *Discord Plus* der Anleitung unter **Einrichtung (einmalig)** folgen: eine eigene App im
   [Developer Portal](https://discord.com/developers/applications) anlegen, Client-ID und Client-Secret eintragen,
   `http://localhost` als Redirect eintragen, *Verbinden* klicken und in Discord *Autorisieren*.
3. Testen: jemanden anrufen oder in einen Voice-Chat gehen. Unter *Status* steht dann „Discord meldet: …“.

Warum eine eigene App? Discord nimmt Aktivitäten nur von registrierten Apps an, und ihr Name steht hinter „Spielt“.
Ohne Prüfung durch Discord dürfen nur der Besitzer der App und bis zu 50 eingetragene Tester sie so nutzen – für
dich allein genau richtig. Das Client-Secret braucht es, um bei der Anmeldung den Code von Discord gegen ein Token zu
tauschen. Es bleibt auf diesem PC.

**Autostart**: Schalter auf der Toolbox-Seite. Er setzt einen Eintrag unter
`HKCU\Software\Microsoft\Windows\CurrentVersion\Run` (Name aus `"autostart"` in `programm.json`) – ohne UAC-Abfrage,
weil das Programm keine Adminrechte braucht. Im Task-Manager unter *Autostart* taucht er als „Discord Plus“ auf.
`Setup.exe` biegt ihn nach dem Verschieben des Ordners um, Entfernen und `Uninstall.exe` löschen ihn.

## So erkennt Windows es

`Setup.exe` legt zwei `.exe` an, beide mit dem Logo, der Dateibeschreibung „Discord Plus“ und dem Herausgeber
„Windows Toolbox“ (aus `"name"` und `"symbol"` in `programm.json`):

- `DiscordPlus.exe` hier im Ordner – der Starter. Ihn startet der Autostart; im Task-Manager unter *Autostart*
  steht er als „Discord Plus“ mit Logo.
- `runtime\DiscordPlus.exe` – das eigentliche Programm (`pythonw.exe` mit eigenem Namen und Symbol). Im Task-Manager
  steht es unter *Hintergrundprozesse* als „Discord Plus“ (nicht als „Python“), unter *Details* als `DiscordPlus.exe`.
  Unter *Apps* erscheinen nur Programme mit offenem Fenster – Discord Plus hat nur das Symbol im Infobereich.
  Auch in den Taskleisten-Einstellungen (*Weitere Symbole der Taskleiste*) heißt es so.

## Wie es funktioniert

- **Verbindung**: Die Discord-App öffnet beim Start eine Named Pipe `\\.\pipe\discord-ipc-0`. Darüber gehen
  JSON-Befehle hin und her ([RPC-Doku](https://docs.discord.com/developers/topics/rpc)).
- **Anmeldung** (einmal, über *Verbinden*): `AUTHORIZE` → Discord fragt in der App nach → Code → bei discord.com gegen
  ein Token tauschen → `AUTHENTICATE`. Das Token gilt etwa eine Woche und wird danach mit dem `refresh_token`
  erneuert, ohne Nachfrage. Von selbst fragt das Programm Discord nie nach einer Freigabe – mitten im Spiel poppt nichts auf.
- **Abfrage**: Alle 3 Sekunden `GET_SELECTED_VOICE_CHANNEL` – der Kanal, in dem du gerade bist, mit allen
  Teilnehmern. Das gilt für Server-Voice-Chats, private Anrufe und Gruppenanrufe.
- **Anzeige**: `aktivitaet()` in `discord_plus_einstellungen.py` baut daraus die Aktivität. Gesendet wird nur bei
  einer Änderung, weil Discord höchstens 5 Änderungen in 20 Sekunden erlaubt. Beim Auflegen wird sie gelöscht. Beendet
  sich das Programm, entfernt Discord sie von selbst.
- **Toolbox**: `status`, `reload`, `verbinden`, `abmelden`, `quit` über `127.0.0.1:47817` (Port aus `programm.json`).

## Starten und prüfen

Zum Testen mit Konsole (Fehler erscheinen dann im Terminal):

```
runtime\python.exe programme\discord_plus\discord_plus.py
```

Läuft es schon (Symbol im Infobereich), beendet sich ein zweiter Start sofort. Was schiefging, steht in
`daten\logs\discord_plus.log` und in der Statuszeile der Toolbox-Seite. Häufige Meldungen:

| Meldung | Ursache |
|---|---|
| Discord läuft nicht | Die Discord-App ist zu (im Browser geht es nicht). Das Programm wartet und verbindet sich von selbst. |
| Invalid Client ID | Client-ID falsch kopiert |
| invalid_client | Client-Secret falsch (oder im Portal neu erzeugt – dann das neue eintragen) |
| Invalid "redirect_uri" | `http://localhost` fehlt unter OAuth2 → Redirects (Schritt 3) |
| Nicht verbunden | Noch nie verbunden, oder die Anmeldung ist abgelaufen bzw. wurde in Discord widerrufen → *Verbinden* |

Die Anzeige ist da, aber keiner sieht sie? In Discord unter *Einstellungen → Aktivitätsprivatsphäre (Activity Privacy)* muss
„Meine Aktivität teilen“ (*Share my activity*) an sein.
