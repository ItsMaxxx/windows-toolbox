// Source code of Setup.exe and Uninstall.exe in the main folder – the two .exe files that are in the repo (everything
// else is built by Setup.exe first). Both do only one thing: run setup\setup.ps1 in a console window.
//   Setup.exe       setup.ps1 [arguments]              (e.g. Setup.exe -NoAdmin, Setup.exe -Restart)
//   Uninstall.exe   setup.ps1 -Uninstall [arguments]   (compiled with /define:UNINSTALL)
// Rebuild after a change here or in arguments.cs: run setup\build_setup_exe.ps1 and commit both .exe files.
//
// What Einrichten.cmd / Entfernen.cmd used to do is now here:
//   - console to UTF-8 so umlauts appear correctly (formerly chcp 65001)
//   - clear PSModulePath: started from a PowerShell 7 terminal, powershell.exe (5.1) would otherwise inherit its
//     modules and e.g. not find Get-FileHash
//   - at the end, if the window opened just for us (double-click, Toolbox), not in the terminal: if everything
//     worked, it closes by itself after 5 s – on warnings or errors it waits for a key
// Runs without admin rights (asInvoker); setup.ps1 gets them itself via UAC, only for the steps that need them.

using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;

#if UNINSTALL
[assembly: AssemblyTitle("Uninstall Toolbox")]
#else
[assembly: AssemblyTitle("Set up Toolbox")]
#endif
[assembly: AssemblyProduct("Toolbox")]

static class SetupExe
{
#if UNINSTALL
    static readonly string Mode = "-Uninstall";
#else
    static readonly string Mode = "";
#endif

    [DllImport("kernel32.dll")]
    static extern uint GetConsoleProcessList(uint[] list, uint count);

    static int Main(string[] args)
    {
        Console.OutputEncoding = new UTF8Encoding(false);
        string folder = AppDomain.CurrentDomain.BaseDirectory;
        string script = Path.Combine(folder, @"setup\setup.ps1");
        int code;
        if (!File.Exists(script))
        {
            Console.WriteLine(script + " is missing – is this .exe in the main folder of the Toolbox?");
            code = 1;
        }
        else
        {
            StringBuilder arguments = new StringBuilder("-NoProfile -ExecutionPolicy Bypass -File " + Arguments.Quote(script));
            if (Mode != "")
                arguments.Append(' ').Append(Mode);
            foreach (string arg in args)
                arguments.Append(' ').Append(Arguments.Quote(arg));

            ProcessStartInfo info = new ProcessStartInfo("powershell.exe", arguments.ToString());
            info.UseShellExecute = false;        // same console, same rights
            info.WorkingDirectory = folder;
            info.EnvironmentVariables["PSModulePath"] = "";
            using (Process p = Process.Start(info))
            {
                p.WaitForExit();
                code = p.ExitCode;
            }
        }

        // Only we (and maybe powershell, already finished) are attached to the console -> it opened for us and would
        // close again right away. If everything worked (code 0), leave it up briefly and then close by itself;
        // otherwise (warnings: 2, aborted: 1) wait for a key so you can read what happened.
        if (GetConsoleProcessList(new uint[8], 8) <= 1)
        {
            Console.WriteLine();
            if (code == 0)
            {
                for (int s = 5; s > 0 && !Console.KeyAvailable; s--)
                {
                    Console.Write("\rThis window closes in " + s + " s (press a key: right away) ");
                    for (int i = 0; i < 10 && !Console.KeyAvailable; i++)
                        Thread.Sleep(100);
                }
            }
            else
            {
                Console.Write("Press a key to close …");
                Console.ReadKey(true);
            }
        }
        return code;
    }
}
