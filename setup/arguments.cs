// Shared by setup_exe.cs (Setup.exe, Uninstall.exe) and starter.cs (Toolbox.exe, HardwareMonitor.exe, …) –
// compiled along with each. No using lines, because setup.ps1 simply appends this file to the end of starter.cs.

static class Arguments
{
    // Put an argument in quotes the way Windows programs (also Python and PowerShell) take it apart again:
    // double the backslashes before a " or at the end, write " itself as \".
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
