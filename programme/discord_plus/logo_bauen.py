"""
Baut discord_plus.ico aus logo_quelle.png: das Gesicht aus der Vorlage (hell auf Schwarz) weiß auf dem blauen
Discord-Kreis – Augen, Narbe und Mund bleiben ausgestanzt, wie beim Discord-Logo.

Nur nötig, wenn sich logo_quelle.png ändert:
    runtime\\python.exe programme\\discord_plus\\logo_bauen.py
Das Symbol steckt danach in DiscordPlus.exe (Starter) und runtime\\DiscordPlus.exe (Task-Manager) – beide legt
Setup.exe beim nächsten Einrichten neu an – und im Symbol im Infobereich.
"""

from pathlib import Path

from PIL import Image, ImageDraw

ORDNER = Path(__file__).resolve().parent
QUELLE = ORDNER / "logo_quelle.png"
ZIEL = ORDNER / "discord_plus.ico"

BLURPLE = (88, 101, 242, 255)            # Discord-Blau #5865F2
GESICHT = (255, 255, 255, 255)
GESICHT_BREITE = 0.64                    # Anteil am Kreis (beim Discord-Logo etwa so)
GROESSEN = (16, 20, 24, 32, 40, 48, 64, 128, 256)     # wie toolbox\programm.ico
GROSS = 1024                             # erst groß zeichnen, dann je Größe verkleinern (glatte Kanten)


def gesicht_maske():
    """Maske aus der Vorlage: hell (das Gesicht) = 255, schwarz (Hintergrund, Augen, Mund) = 0, Kanten dazwischen.
    Der Grünkanal reicht dafür – das Mint der Vorlage ist dort am hellsten."""
    gruen = Image.open(QUELLE).convert("RGB").getchannel("G")
    hellstes = gruen.getextrema()[1]
    maske = gruen.point(lambda v: min(255, round(v * 255 / (hellstes * 0.85))))    # Kanten leicht voller
    return maske.crop(maske.getbbox())


def logo(groesse=GROSS):
    bild = Image.new("RGBA", (groesse * 4, groesse * 4), (0, 0, 0, 0))     # 4-fach für einen glatten Kreisrand
    ImageDraw.Draw(bild).ellipse((0, 0, groesse * 4 - 1, groesse * 4 - 1), fill=BLURPLE)
    bild = bild.resize((groesse, groesse), Image.LANCZOS)

    maske = gesicht_maske()
    breite = round(groesse * GESICHT_BREITE)
    hoehe = round(breite * maske.height / maske.width)
    maske = maske.resize((breite, hoehe), Image.LANCZOS)
    links, oben = (groesse - breite) // 2, (groesse - hoehe) // 2
    bild.paste(Image.new("RGBA", (breite, hoehe), GESICHT), (links, oben), maske)
    return bild


def main():
    gross = logo()
    bilder = [gross.resize((g, g), Image.LANCZOS) for g in GROESSEN]
    bilder[-1].save(ZIEL, sizes=[(g, g) for g in GROESSEN], append_images=bilder[:-1])
    print(f"{ZIEL.name} angelegt ({', '.join(map(str, GROESSEN))} px)")


if __name__ == "__main__":
    main()
