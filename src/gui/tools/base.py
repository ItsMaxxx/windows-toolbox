"""
Grundbausteine für Programmseiten in der Toolbox.

Eine neue Programmseite ist eine Unterklasse von ToolPage, die in build() ihre Bereiche
mit self.section(...) anlegt. Eingetragen wird sie in tools/__init__.py.
"""

from dataclasses import dataclass

import customtkinter as ctk

# Farben jeweils als (hell, dunkel) – CustomTkinter nimmt automatisch die passende
CARD = ("gray99", "gray18")
BUTTON_OFF = ("gray80", "gray26")     # Farbe für gerade nicht nutzbare Knöpfe
MUTED = ("gray40", "gray62")
GOOD = ("#1f9d55", "#4ade80")
BAD = ("#c0392b", "#f87171")
WARN = ("#b7791f", "#fbbf24")


@dataclass
class ToolInfo:
    id: str               # eindeutiger Kurzname, z. B. "hardware_monitor"
    name: str             # Anzeige in der Seitenleiste
    category: str         # Tab, in dem das Programm erscheint
    description: str      # Untertitel auf der Programmseite
    page: type            # Klasse der Programmseite (Unterklasse von ToolPage)


class ToolPage(ctk.CTkScrollableFrame):
    """Eine scrollbare Seite im Hauptbereich mit Titel, Untertitel und Bereichen ("Karten")."""

    def __init__(self, master, app, info):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.info = info
        self.columnconfigure(0, weight=1)
        self._row = 0

        ctk.CTkLabel(self, text=info.name, font=ctk.CTkFont(size=24, weight="bold"),
                     anchor="w").grid(row=self._next_row(), column=0, sticky="ew", padx=24, pady=(20, 0))
        if info.description:
            ctk.CTkLabel(self, text=info.description, text_color=MUTED, anchor="w", justify="left",
                         wraplength=640).grid(row=self._next_row(), column=0, sticky="ew", padx=24, pady=(2, 8))
        self.build()

    def _next_row(self):
        self._row += 1
        return self._row

    def section(self, title, hint=None):
        """Legt einen Bereich (Karte) an und gibt den Rahmen für seinen Inhalt zurück."""
        card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12)
        card.grid(row=self._next_row(), column=0, sticky="ew", padx=24, pady=(10, 4))
        card.columnconfigure(1, weight=1)
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=15, weight="bold"), anchor="w").grid(
            row=0, column=0, columnspan=3, sticky="ew", padx=18, pady=(14, 0 if hint else 8))
        if hint:
            ctk.CTkLabel(card, text=hint, text_color=MUTED, anchor="w", justify="left", wraplength=620,
                         font=ctk.CTkFont(size=12)).grid(row=1, column=0, columnspan=3, sticky="ew",
                                                          padx=18, pady=(0, 8))
        return card

    def row_label(self, card, row, text, pady=6):
        """Beschriftung links in einer Zeile; pady sollte zu dem Element rechts daneben passen."""
        ctk.CTkLabel(card, text=text, anchor="w").grid(row=row, column=0, sticky="w", padx=(18, 12), pady=pady)

    # --- Wird von der Toolbox aufgerufen; Unterklassen können das überschreiben ---
    def build(self):
        """Inhalt der Seite anlegen."""

    def on_show(self):
        """Seite wird sichtbar (z. B. Status-Abfragen starten)."""

    def on_hide(self):
        """Seite wird verlassen oder das Fenster versteckt (Abfragen stoppen)."""
