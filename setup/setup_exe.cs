// Quelltext von Setup.exe und Uninstall.exe im Hauptordner – den beiden .exe, die im Repo liegen (alles andere
// baut erst Setup.exe). Beide machen nur eins: setup\setup.ps1 in einem Konsolenfenster ausführen.
//   Setup.exe       setup.ps1 [Argumente]              (z. B. Setup.exe -OhneAdmin, Setup.exe -Neustart)
//   Uninstall.exe   setup.ps1 -Entfernen [Argumente]   (übersetzt mit /define:ENTFERNEN)
// Neu bauen nach einer Änderung hier oder in argumente.cs: setup\setup_exe_bauen.ps1 ausführen und beide .exe
// committen.
//
// Was früher Einrichten.cmd / Entfernen.cmd taten, steht jetzt hier:
//   - Konsole auf UTF-8, damit Umlaute richtig erscheinen (früher chcp 65001)
//   - PSModulePath leeren: Aus einem PowerShell-7-Terminal gestartet, würde powershell.exe (5.1) sonst dessen Module
//     erben und z. B. Get-FileHash nicht finden
//   - am Ende, wenn das Fenster extra für uns aufging (Doppelklick, Toolbox), nicht im Terminal: hat alles geklappt,
//     schließt es sich nach 5 s von selbst – bei Warnungen oder Fehlern wartet es auf eine Taste
// Läuft ohne Adminrechte (asInvoker); setup.ps1 holt sie selbst per UAC, nur für die Schritte, die sie brauchen.

using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;

#if ENTFERNEN
[assembly: AssemblyTitle("Toolbox entfernen")]
#else
[assembly: AssemblyTitle("Toolbox einrichten")]
#endif
[assembly: AssemblyProduct("Toolbox")]

static class SetupExe
{
#if ENTFERNEN
    static readonly string Modus = "-Entfernen";
#else
    static readonly string Modus = "";
#endif

    [DllImport("kernel32.dll")]
    static extern uint GetConsoleProcessList(uint[] liste, uint anzahl);

    static int Main(string[] args)
    {
        Console.OutputEncoding = new UTF8Encoding(false);
        string ordner = AppDomain.CurrentDomain.BaseDirectory;
        string skript = Path.Combine(ordner, @"setup\setup.ps1");
        int code;
        if (!File.Exists(skript))
        {
            Console.WriteLine(skript + " fehlt – liegt diese .exe im Hauptordner der Toolbox?");
            code = 1;
        }
        else
        {
            StringBuilder argumente = new StringBuilder("-NoProfile -ExecutionPolicy Bypass -File " + Argumente.Quote(skript));
            if (Modus != "")
                argumente.Append(' ').Append(Modus);
            foreach (string arg in args)
                argumente.Append(' ').Append(Argumente.Quote(arg));

            ProcessStartInfo info = new ProcessStartInfo("powershell.exe", argumente.ToString());
            info.UseShellExecute = false;        // gleiche Konsole, gleiche Rechte
            info.WorkingDirectory = ordner;
            info.EnvironmentVariables["PSModulePath"] = "";
            using (Process p = Process.Start(info))
            {
                p.WaitForExit();
                code = p.ExitCode;
            }
        }

        // Nur wir (und evtl. powershell, schon beendet) hängen an der Konsole -> sie ging für uns auf und schlösse
        // sich sofort wieder. Hat alles geklappt (Code 0), noch kurz stehen lassen und dann von selbst schließen;
        // sonst (Warnungen: 2, Abbruch: 1) auf eine Taste warten, damit man lesen kann, was los war.
        if (GetConsoleProcessList(new uint[8], 8) <= 1)
        {
            Console.WriteLine();
            if (code == 0)
            {
                for (int s = 5; s > 0 && !Console.KeyAvailable; s--)
                {
                    Console.Write("\rDas Fenster schließt sich in " + s + " s (Taste drücken: sofort) ");
                    for (int i = 0; i < 10 && !Console.KeyAvailable; i++)
                        Thread.Sleep(100);
                }
            }
            else
            {
                Console.Write("Taste drücken zum Schließen …");
                Console.ReadKey(true);
            }
        }
        return code;
    }
}
