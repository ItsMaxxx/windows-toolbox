"""Platzhalter-Seite für Tabs, in denen es noch kein Programm gibt."""

import customtkinter as ctk

from .base import MUTED, ToolPage


class PlatzhalterPage(ToolPage):
    def build(self):
        card = self.section("Noch nichts hier")
        ctk.CTkLabel(
            card, anchor="w", justify="left", wraplength=620, text_color=MUTED,
            text=(f"Dieser Eintrag ist nur ein Platzhalter für den Tab „{self.info.category}“.\n"
                  "Sobald es hier ein Programm gibt, erscheinen an dieser Stelle seine Einstellungen."),
        ).grid(row=2, column=0, columnspan=3, sticky="ew", padx=18, pady=(0, 16))
