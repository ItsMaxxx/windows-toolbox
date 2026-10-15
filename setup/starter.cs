// Template for the starter .exe of each program (Toolbox.exe, HardwareMonitor.exe, …).
// setup.ps1 replaces the %PLACEHOLDERS% with the values from the program.json and compiles it with csc.exe – the
// C# compiler that already comes with the .NET Framework on Windows 10/11 (no extra tool needed).
//
// The starter does only one thing: start runtime\<Name>.exe (pythonw.exe with its own name, see make_exe.py) with the
// program's script and quit. All paths are relative to the starter's location – that's why double-click and
// shortcuts still work after moving the folder, and no arguments are needed.
// It passes on additional arguments (e.g. --after <pid> when the Toolbox restarts).
// If it is started with admin rights (Task Scheduler, UAC), the program runs with admin rights too.

using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text;
using System.Windows.Forms;

[assembly: AssemblyTitle("%NAME%")]            // file description (Explorer, Task Manager)
[assembly: AssemblyProduct("Toolbox")]
[assembly: AssemblyCompany("%COMPANY%")]       // publisher (Task Manager → Startup apps)
[assembly: AssemblyFileVersion("%VERSION%")]

static class Starter
{
    const string Name = "%NAME%";
    const string Runtime = @"%RUNTIME%";       // folder with our own Python, relative to the starter
    const string Host = "%HOST%";              // pythonw.exe copy with its own name in runtime\
    const string Script = @"%SCRIPT%";         // relative to the starter

    [STAThread]
    static int Main(string[] args)
    {
        string folder = AppDomain.CurrentDomain.BaseDirectory;
        string runtime = Path.GetFullPath(Path.Combine(folder, Runtime));
        string host = Path.Combine(runtime, Host);
        if (!File.Exists(host))
            host = Path.Combine(runtime, "pythonw.exe");
        string script = Path.GetFullPath(Path.Combine(folder, Script));

        if (!File.Exists(host) || !File.Exists(script))
        {
            MessageBox.Show((File.Exists(script) ? "runtime\\ is missing" : script + " is missing") +
                            " – please run Setup.exe first.", Name,
                            MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return 1;
        }

        StringBuilder arguments = new StringBuilder(Arguments.Quote(script));
        foreach (string arg in args)
            arguments.Append(' ').Append(Arguments.Quote(arg));

        ProcessStartInfo info = new ProcessStartInfo(host, arguments.ToString());
        info.UseShellExecute = false;          // this way it inherits the starter's rights (admin rights too)
        info.WorkingDirectory = Path.GetDirectoryName(script);
        try
        {
            Process.Start(info);
        }
        catch (Exception error)
        {
            MessageBox.Show("Start failed: " + error.Message, Name, MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
        return 0;
    }
}
