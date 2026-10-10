// Vorlage für die Starter-.exe jedes Programms (Toolbox.exe, HardwareMonitor.exe, …).
// setup.ps1 ersetzt die %PLATZHALTER% mit den Werten aus der programm.json und übersetzt das mit csc.exe – dem
// C#-Compiler, der bei Windows 10/11 im .NET Framework schon dabei ist (kein zusätzliches Werkzeug nötig).
//
// Der Starter macht nur eins: runtime\<Name>.exe (pythonw.exe mit eigenem Namen, siehe exe_anlegen.py) mit dem Skript
// des Programms starten und sich beenden. Alle Pfade sind relativ zum Ort des Starters – deshalb funktionieren
// Doppelklick und Verknüpfungen auch nach dem Verschieben des Ordners, und es braucht keine Argumente.
// Zusätzliche Argumente reicht er weiter (z. B. --nach <pid> beim Neustart der Toolbox).
// Wird er mit Adminrechten gestartet (Aufgabenplanung, UAC), läuft auch das Programm mit Adminrechten.

using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text;
using System.Windows.Forms;

[assembly: AssemblyTitle("%NAME%")]            // Dateibeschreibung (Explorer, Task-Manager)
[assembly: AssemblyProduct("Toolbox")]
[assembly: AssemblyFileVersion("%VERSION%")]

static class Starter
{
    const string Name = "%NAME%";
    const string Runtime = @"%RUNTIME%";       // Ordner mit dem eigenen Python, relativ zum Starter
    const string Host = "%HOST%";              // pythonw.exe-Kopie mit eigenem Namen in runtime\
    const string Skript = @"%SKRIPT%";         // relativ zum Starter

    [STAThread]
    static int Main(string[] args)
    {
        string ordner = AppDomain.CurrentDomain.BaseDirectory;
        string runtime = Path.GetFullPath(Path.Combine(ordner, Runtime));
        string host = Path.Combine(runtime, Host);
        if (!File.Exists(host))
            host = Path.Combine(runtime, "pythonw.exe");
        string skript = Path.GetFullPath(Path.Combine(ordner, Skript));

        if (!File.Exists(host) || !File.Exists(skript))
        {
            MessageBox.Show((File.Exists(skript) ? "runtime\\ fehlt" : skript + " fehlt") +
                            " – bitte zuerst Setup.exe ausführen.", Name,
                            MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return 1;
        }

        StringBuilder argumente = new StringBuilder(Quote(skript));
        foreach (string arg in args)
            argumente.Append(' ').Append(Quote(arg));

        ProcessStartInfo info = new ProcessStartInfo(host, argumente.ToString());
        info.UseShellExecute = false;          // erbt so die Rechte des Starters (auch Adminrechte)
        info.WorkingDirectory = Path.GetDirectoryName(skript);
        try
        {
            Process.Start(info);
        }
        catch (Exception fehler)
        {
            MessageBox.Show("Start fehlgeschlagen: " + fehler.Message, Name, MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
        return 0;
    }

    // Ein Argument so in Anführungszeichen setzen, wie Windows-Programme (auch Python) es wieder auseinandernehmen:
    // Backslashes vor einem " bzw. am Ende verdoppeln, " selbst als \" schreiben.
    static string Quote(string arg)
    {
        StringBuilder sb = new StringBuilder("\"");
        int backslashes = 0;
        foreach (char c in arg)
        {
            if (c == '\\') { backslashes++; continue; }
            sb.Append('\\', c == '"' ? backslashes * 2 + 1 : backslashes);
            backslashes = 0;
            sb.Append(c);
        }
        sb.Append('\\', backslashes * 2).Append('"');
        return sb.ToString();
    }
}
