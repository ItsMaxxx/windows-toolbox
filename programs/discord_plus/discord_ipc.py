"""
Kleiner Client für die lokale Schnittstelle der Discord-App (RPC über eine Named Pipe). Er kann nur, was
discord_plus braucht: verbinden, anmelden, den Sprachkanal abfragen und die Aktivität („Spielt …“) setzen.

So funktioniert die Schnittstelle (Doku: https://docs.discord.com/developers/topics/rpc):
  - Die Discord-App öffnet beim Start \\\\.\\pipe\\discord-ipc-0 (läuft Discord mehrfach, auch -1, -2, …).
  - Jede Nachricht ist ein Rahmen: 4 Byte Opcode, 4 Byte Länge (beides little-endian), dann JSON.
    Opcode 0 = Handshake, 1 = Befehl bzw. Antwort, 2 = Schließen, 3/4 = Ping/Pong.
  - Nach dem Handshake {"v": 1, "client_id": …} antwortet Discord mit dem Ereignis READY.
  - SET_ACTIVITY geht sofort. Was Daten deines Kontos liest (GET_SELECTED_VOICE_CHANNEL), erst nach der Anmeldung:
      1. AUTHORIZE: Discord zeigt in der App „… möchte auf dein Konto zugreifen“ – nach „Autorisieren“ kommt ein Code
      2. den Code bei discord.com gegen ein Token tauschen (dafür braucht es das Client-Secret): token_holen()
      3. AUTHENTICATE mit dem Token – danach sind die Befehle frei, bis zum Trennen der Verbindung
    Das Token gilt etwa eine Woche; mit dem refresh_token gibt es ohne Nachfrage ein neues.

Ohne Prüfung durch Discord dürfen nur der Besitzer der App und bis zu 50 eingetragene Tester sie so nutzen – für
die eigene App also genau richtig.
"""

import json
import struct
import urllib.error
import urllib.parse
import urllib.request
import uuid

PIPE = r"\\.\pipe\discord-ipc-{}"
TOKEN_URL = "https://discord.com/api/oauth2/token"
# Ohne eigenen User-Agent blockt Cloudflare vor discord.com Anfragen von Python manchmal ab
USER_AGENT = "windows-toolbox discord_plus (https://github.com/ItsMaxxx/windows-toolbox, 1.0)"
SCOPES = ["rpc", "identify"]

HANDSHAKE, FRAME, CLOSE, PING, PONG = range(5)


class DiscordFehler(Exception):
    """Discord hat einen Befehl abgelehnt (code wie in der Doku, z. B. 4006 = nicht angemeldet) oder die Anmeldung
    bei discord.com hat nicht geklappt (code None)."""

    def __init__(self, text, code=None):
        super().__init__(text)
        self.code = code


class Verbindung:
    """Eine Verbindung zur laufenden Discord-App. Wirft OSError, wenn Discord nicht läuft oder die Verbindung abbricht.
    Nicht threadsicher – nur aus einem Thread benutzen."""

    def __init__(self, client_id):
        self.client_id = client_id
        self.pipe = None
        for nummer in range(10):
            try:
                self.pipe = open(PIPE.format(nummer), "r+b", buffering=0)
                break
            except OSError:
                continue
        if self.pipe is None:
            raise FileNotFoundError("Discord läuft nicht (keine discord-ipc-Pipe gefunden)")
        try:
            self.senden(HANDSHAKE, {"v": 1, "client_id": client_id})
            op, antwort = self.empfangen()
            if op == CLOSE or antwort.get("evt") != "READY":
                # z. B. {"code": 4000, "message": "Invalid Client ID"}
                raise DiscordFehler(antwort.get("message") or "Discord hat die Verbindung abgelehnt",
                                    antwort.get("code"))
        except BaseException:
            self.schliessen()
            raise

    # --- Rahmen ---
    def senden(self, op, daten):
        body = json.dumps(daten).encode("utf-8")
        self.pipe.write(struct.pack("<II", op, len(body)) + body)

    def lesen(self, anzahl):
        daten = b""
        while len(daten) < anzahl:
            stueck = self.pipe.read(anzahl - len(daten))
            if not stueck:
                raise ConnectionResetError("Discord hat die Verbindung getrennt")
            daten += stueck
        return daten

    def empfangen(self):
        op, laenge = struct.unpack("<II", self.lesen(8))
        return op, json.loads(self.lesen(laenge))

    # --- Befehle ---
    def befehl(self, cmd, args=None):
        """Schickt einen Befehl und wartet auf die Antwort dazu. Gibt deren "data" zurück."""
        nonce = str(uuid.uuid4())
        self.senden(FRAME, {"cmd": cmd, "args": args or {}, "nonce": nonce})
        while True:
            op, antwort = self.empfangen()
            if op == PING:
                self.senden(PONG, antwort)
            elif op == CLOSE:
                raise ConnectionResetError(antwort.get("message") or "Discord hat die Verbindung geschlossen")
            elif antwort.get("nonce") == nonce:
                if antwort.get("evt") == "ERROR":
                    fehler = antwort.get("data") or {}
                    raise DiscordFehler(fehler.get("message") or "unbekannter Fehler", fehler.get("code"))
                return antwort.get("data")
            # alles andere (Ereignisse ohne Abo) überspringen

    def autorisieren(self):
        """AUTHORIZE – Discord fragt in der App nach. Wartet, bis du dort klickst; gibt den Code zurück."""
        return self.befehl("AUTHORIZE", {"client_id": self.client_id, "scopes": SCOPES})["code"]

    def anmelden(self, access_token):
        """AUTHENTICATE – gibt {"user": …, "application": {"name": …}, "expires": …} zurück."""
        return self.befehl("AUTHENTICATE", {"access_token": access_token})

    def sprachkanal(self):
        """Der Sprachkanal bzw. Anruf, in dem du gerade bist – oder None."""
        return self.befehl("GET_SELECTED_VOICE_CHANNEL")

    def server(self, guild_id):
        return self.befehl("GET_GUILD", {"guild_id": guild_id, "timeout": 5})

    def aktivitaet_setzen(self, pid, aktivitaet):
        """Setzt die Aktivität dieses Programms – None löscht sie. Sie verschwindet auch von selbst, sobald die
        Verbindung zu oder das Programm (pid) beendet ist."""
        args = {"pid": pid}
        if aktivitaet:
            args["activity"] = aktivitaet
        return self.befehl("SET_ACTIVITY", args)

    def schliessen(self):
        if self.pipe:
            try:
                self.pipe.close()
            except OSError:
                pass
            self.pipe = None


def token_holen(client_id, client_secret, **felder):
    """Tauscht bei discord.com einen Code (grant_type="authorization_code", code=…) oder ein refresh_token
    (grant_type="refresh_token", refresh_token=…) gegen ein Token. Beim Code gehört redirect_uri dazu – eine, die in
    der App unter OAuth2 → Redirects steht. Antwort: {"access_token", "refresh_token", "expires_in", …}.
    Wirft DiscordFehler mit Discords Begründung oder OSError (kein Internet)."""
    body = urllib.parse.urlencode({"client_id": client_id, "client_secret": client_secret, **felder}).encode()
    anfrage = urllib.request.Request(TOKEN_URL, data=body, headers={
        "Content-Type": "application/x-www-form-urlencoded", "User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(anfrage, timeout=15) as antwort:
            return json.loads(antwort.read())
    except urllib.error.HTTPError as fehler:
        try:
            info = json.loads(fehler.read())
            grund = info.get("error_description") or info.get("error") or str(info)
        except ValueError:
            grund = f"HTTP {fehler.code}"
        raise DiscordFehler(f"discord.com lehnt die Anmeldung ab: {grund}") from None
