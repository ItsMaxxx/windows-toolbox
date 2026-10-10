// Gemeinsam für setup_exe.cs (Setup.exe, Uninstall.exe) und starter.cs (Toolbox.exe, HardwareMonitor.exe, …) –
// wird jeweils mit übersetzt. Ohne using-Zeilen, weil setup.ps1 diese Datei einfach hinten an starter.cs anhängt.

static class Argumente
{
    // Ein Argument so in Anführungszeichen setzen, wie Windows-Programme (auch Python und PowerShell) es wieder
    // auseinandernehmen: Backslashes vor einem " bzw. am Ende verdoppeln, " selbst als \" schreiben.
    public static string Quote(string arg)
    {
        System.Text.StringBuilder sb = new System.Text.StringBuilder("\"");
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
