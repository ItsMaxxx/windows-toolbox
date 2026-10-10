"""Platzhalter-Seite für Tabs, in denen es noch kein Programm gibt."""

from base import Section, Text, ToolPage


class PlatzhalterPage(ToolPage):
    def layout(self):
        return [Section("Noch nichts hier",
                        Text(f"Dieser Eintrag ist nur ein Platzhalter für den Tab „{self.info.category}“.\n"
                             "Sobald es hier ein Programm gibt, erscheinen an dieser Stelle seine Einstellungen."))]
