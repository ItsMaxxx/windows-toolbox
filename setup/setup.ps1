<#
Setting up and removing the windows-toolbox. Called by Setup.exe or Uninstall.exe in the main folder – small
starters from setup\setup_exe.cs that are in the repo ready-made (double-clicking a .ps1 would only open it in the
editor). Rebuild after a change to setup_exe.cs: setup\build_setup_exe.ps1.

Which programs exist is in the manifests: toolbox\program.json and programs\<program>\program.json
(name, version, script, starter .exe, downloads). Steps 3 and 4 apply to every installed program.

Which programs are installed is in data\installed.json (without the Toolbox – it is always included). If the file
is missing, all count as installed: that's how it was before you could choose – and on the first setup all are
preselected this way. The Toolbox reads the same file and only shows installed programs.

Set up (without parameters) – first a small window: which language (from toolbox\languages.json, preselected: the
saved one or that of Windows – ends up in data\toolbox.json) and which programs? (Deselected ones that were
installed are removed.) Then everything that is missing after cloning:
  1. find Python $PythonVersion (or install it via winget) – exactly this version, no older or newer one
  2. create runtime\: our own Python in the project folder, with the packages from requirements.txt (fixed versions)
  3. two .exe files per program:
       - runtime\<Name>.exe: copy of pythonw.exe with its own name and icon, so it appears in the Task Manager as its
         own program instead of as "Python" (setup\make_exe.py)
       - the starter (Toolbox.exe in the main folder, HardwareMonitor.exe in the program folder): starts the copy with
         the script, all paths relative – double-click and shortcuts still work after moving the folder
         (setup\starter.cs, compiled with csc.exe from the .NET Framework of Windows)
  4. per program the downloads from program.json (fixed version, checksum), e.g. LibreHardwareMonitor into
     programs\hardware_monitor\lhm\
  5. shortcuts "$ShortcutName" to Toolbox.exe – on the desktop and in the Start menu, depending on the checkboxes in
     the window (unchecked: deleted). Without the window ("Set up again", "Update") they stay as they are;
     only one that points into nowhere after moving the folder points here again afterwards. One that you deleted
     yourself or moved somewhere else doesn't come back (to bring it back: checkbox in the window).
  6. only with the Hardware Monitor, with a UAC prompt: install PawnIO and set up the scheduled task HardwareMonitor
  7. everything as before: whatever setting up might touch is noted at the very beginning and restored at the end –
     even if something aborts on the way (Save-State / Restore-State): autostart on/off, whether the
     Hardware Monitor was running (then it runs again afterwards, with the new code), the settings files in data\.
     Programs without admin rights (e.g. Discord Plus) are quit beforehand and run again afterwards if they
     were running; their autostart entry (HKCU\...\Run) points here again after moving the folder.
     So an update never changes anything you set yourself.
  Every step checks first whether it is already done – so setting up can be run again anytime,
  e.g. after moving the folder (then only the task is set up again) or after a git pull.
  A running Toolbox is quit for it and started again at the end – with the new selection.

  -Programs <ids>   set up these programs in addition, without the window (comma-separated, e.g.
                    -Programs hardware_monitor – that's how "Install" in the Toolbox calls the script).
                    Steps 3–7 then only for these; 1–2 (Python, runtime\) are needed by all, they always run.
  -NoAdmin          only steps 1–5, without UAC prompt
  -Restart          without the window, the installed programs as before; if the Hardware Monitor was running,
                    restart it in step 7 in any case so it loads new code (after an update –
                    "Update" and "Set up again" in the Toolbox settings pass this)

-Uninstall – the counterpart: quit the Toolbox and all programs, delete task, autostart entries and shortcuts,
  on request
  delete everything generated and downloaded (runtime\, starters, downloads). data\ stays.
  PawnIO stays installed because other programs use it too (to remove: winget uninstall namazso.PawnIO).
  With -Programs <ids> only these programs: quit, delete task or autostart, delete starter and downloads, remove
  from data\installed.json – without asking ("Remove" in the Toolbox asks itself beforehand).

-Admin <steps> – internal: the part with admin rights. The script starts itself again for it after a UAC prompt
  (steps, comma-separated: pawnio, task, autostart-on, autostart-off, monitor-start, task-delete).

Layout of the folder: code = repo (toolbox\, programs\, setup\), runtime\ = disposable (Python and packages –
can be set up again anytime), data\ = settings (one .json per program) and logs.
#>
param([switch]$Uninstall, [string]$Programs, [switch]$NoAdmin, [switch]$Restart, [string]$Admin)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'         # progress bars slow Invoke-WebRequest down a lot

$Root       = Split-Path -Parent $PSScriptRoot
$Runtime    = Join-Path $Root 'runtime'
$RuntimePy  = Join-Path $Runtime 'python.exe'
$Icon       = Join-Path $Root 'toolbox\program.ico'    # default icon of the programs (⚒ on green); the Toolbox has
                                                     # its own ("icon" in toolbox\program.json)
$Csc        = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'

# Name of the shortcuts to Toolbox.exe (desktop, Start menu – step 5)
$ShortcutName = 'Windows Toolbox'

# Python: exactly this version (major.minor) – the fixed package versions in requirements.txt are tested with it.
# To switch: change it here, delete runtime\, run Setup.exe, test, adjust requirements.txt.
$PythonVersion = '3.14'

# Sets up the task via winutil.task_command() – the Toolbox uses the same command for "Set up task".
# (Without double quotes, Windows PowerShell 5.1 would mangle them when passing them to python.exe.)
$PyTask = 'import sys; sys.path.insert(0, sys.argv[1]); import winutil; ' +
          'r = winutil.powershell(winutil.task_command(*sys.argv[2:4])); ok = r is not None and r.returncode == 0; ' +
          'ok or print(r.stderr if r else None); sys.exit(0 if ok else 1)'


# ---------- Programs (from the program.json files) ----------
function Load-Texts($file) {
    <# Content of an i18n.json (ID -> language -> text) – or $null if it doesn't exist or is broken. #>
    if (-not (Test-Path $file)) { return $null }
    try { Get-Content -Raw -Encoding UTF8 $file | ConvertFrom-Json } catch { $null }
}

function Load-Program($file) {
    <# Reads a manifest and adds the finished paths: folder, script, starter (the .exe to double-click) and
       host (the pythonw.exe copy in runtime\ that the starter calls – same file name as the starter). #>
    $p = Get-Content -Raw -Encoding UTF8 $file | ConvertFrom-Json
    $folder = Split-Path -Parent $file
    $p | Add-Member Folder $folder
    $p | Add-Member Texts (Load-Texts (Join-Path $folder 'i18n.json'))    # name and description per language
    if ($p.starter) {                             # only for programs that run on their own (not just a page)
        $p | Add-Member ScriptPath (Join-Path $folder $p.script)
        $p | Add-Member StarterPath ([IO.Path]::GetFullPath((Join-Path $folder $p.starter)))
        $p | Add-Member HostPath (Join-Path $Runtime (Split-Path -Leaf $p.starter))
        $p | Add-Member IconPath $(if ($p.icon) { Join-Path $folder $p.icon } else { $Icon })
    }
    $p
}

$Toolbox   = Load-Program (Join-Path $Root 'toolbox\program.json')
$All       = @($Toolbox) + @(Get-ChildItem (Join-Path $Root 'programs\*\program.json') | ForEach-Object { Load-Program $_.FullName })
$Monitor   = $All | Where-Object id -eq 'hardware_monitor'

# Which programs are installed (without the Toolbox) – also read by toolbox.py (installed_ids)
$InstalledFile = Join-Path $Root 'data\installed.json'

function Get-Installed {
    <# IDs of the installed programs. If the file is missing (or broken): all. #>
    if (Test-Path $InstalledFile) {
        try { return @((Get-Content -Raw -Encoding UTF8 $InstalledFile | ConvertFrom-Json).programs | Where-Object { $_ }) }
        catch { }
    }
    @($All | Where-Object id -ne 'toolbox' | ForEach-Object id)
}

function Save-Installed($ids) {
    New-Item -ItemType Directory -Force (Split-Path -Parent $InstalledFile) | Out-Null
    $json = ConvertTo-Json @{ programs = @($ids) }
    [IO.File]::WriteAllText($InstalledFile, $json, (New-Object Text.UTF8Encoding $false))   # without BOM, for Python
}

# Language of the Toolbox and all programs: "language" in data\toolbox.json – also read by toolbox\i18n.py
$ToolboxFile = Join-Path $Root 'data\toolbox.json'
# Which languages exist (code -> name, in this order) – toolbox\i18n.py takes the same list
$LanguageList = Get-Content -Raw -Encoding UTF8 (Join-Path $Root 'toolbox\languages.json') | ConvertFrom-Json
$LanguageCodes = @($LanguageList.languages.PSObject.Properties.Name)

function Get-Translated($texts, $id, $otherwise) {
    <# Text $id from an i18n.json in every language: table code -> text. If a translation is missing, the
       fallback language, then $otherwise or the ID – like t() in toolbox\i18n.py. #>
    $row = if ($texts) { $texts.$id }
    $result = @{}
    foreach ($code in $LanguageCodes) {
        $text = if ($row) { $row.$code }
        if (-not $text -and $row) { $text = $row.($LanguageList.fallback) }
        if (-not $text) { $text = if ($otherwise) { $otherwise } else { $id } }
        $result[$code] = $text
    }
    $result
}

function Get-ToolboxSettings {
    <# Content of data\toolbox.json – or an empty object if it is missing or broken. #>
    if (Test-Path $ToolboxFile) {
        try { $s = Get-Content -Raw -Encoding UTF8 $ToolboxFile | ConvertFrom-Json; if ($s) { return $s } }
        catch { }
    }
    New-Object psobject
}

function Get-Language {
    <# Code from languages.json: the saved language – otherwise the Windows display language if it exists, otherwise
       the fallback language (English) – exactly like chosen() in toolbox\i18n.py. #>
    $saved = (Get-ToolboxSettings).language
    if ($saved -in $LanguageCodes) { return $saved }
    $system = (Get-UICulture).TwoLetterISOLanguageName
    if ($system -in $LanguageCodes) { $system } else { $LanguageList.fallback }
}

function Save-Language($language) {
    <# Writes "language" into data\toolbox.json; everything else in it stays as it is. #>
    New-Item -ItemType Directory -Force (Split-Path -Parent $ToolboxFile) | Out-Null
    $s = Get-ToolboxSettings
    $s | Add-Member -NotePropertyName language -NotePropertyValue $language -Force
    [IO.File]::WriteAllText($ToolboxFile, ($s | ConvertTo-Json), (New-Object Text.UTF8Encoding $false))
}

function Get-ProgramIds($text) {
    <# "a,b" from -Programs -> checked IDs. The Toolbox isn't part of it, it is always installed. #>
    $ids = @($text -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ -and $_ -ne 'toolbox' })
    foreach ($id in $ids) {
        if (-not ($All | Where-Object id -eq $id)) {
            throw "Unknown program: $id (known: $(($All | Where-Object id -ne 'toolbox' | ForEach-Object id) -join ', '))"
        }
    }
    $ids
}

# From the manifests – toolbox.py and hardware_monitor_settings.py read the same values
$TaskName  = $Monitor.task                       # scheduled task that starts the monitor at logon
$IpcPort   = $Monitor.port                       # remote control of the monitor
$GuiPort   = $Toolbox.port                       # remote control of the Toolbox


# ---------- Helpers ----------
function Step($text)  { Write-Host ""; Write-Host "== $text" -ForegroundColor Cyan }
function Ok($text)    { Write-Host "   [OK] $text" -ForegroundColor Green }
function Info($text)  { Write-Host "   $text" }
$Warnings = 0                                    # counted: with warnings the window stays open at the end
function Warn($text)  { $script:Warnings++; Write-Host "   [!] $text" -ForegroundColor Yellow }

function Send-MonitorCommand($command) {
    <# Sends a command to the running Hardware Monitor (like ipc() in hardware_monitor_gui.py) – $null if it
       isn't running. #>
    Send-Command $IpcPort $command
}

function Send-ToolboxCommand($command) {
    <# The same for the Toolbox ("status", "quit", "show" – see instance_server in toolbox.py). #>
    Send-Command $GuiPort $command
}

function Send-Command($port, $command) {
    try {
        $client = New-Object Net.Sockets.TcpClient
        $client.Connect('127.0.0.1', $port)
        $client.ReceiveTimeout = 1000
        $stream = $client.GetStream()
        $bytes = [Text.Encoding]::UTF8.GetBytes("$command`n")
        $stream.Write($bytes, 0, $bytes.Length)
        $answer = (New-Object IO.StreamReader($stream)).ReadLine()
        $client.Close()
        return $answer
    } catch {
        return $null
    }
}

function Stop-Monitor { Stop-Program $Monitor }

function Stop-Program($p) {
    <# Quits a program via its port ("port" in program.json) and waits up to 5 s for it. #>
    Send-Command $p.port 'quit' | Out-Null
    for ($i = 0; $i -lt 50 -and (Send-Command $p.port 'status'); $i++) { Start-Sleep -Milliseconds 100 }
}

function Get-OtherPrograms {
    <# Programs that run on their own without admin rights (e.g. Discord Plus): all with a port except Toolbox and
       Hardware Monitor – the script handles those two separately. #>
    @($All | Where-Object { $_.port -and $_.id -ne 'toolbox' -and $_.id -ne $Monitor.id })
}

# Autostart of the programs without admin rights: value "autostart" from program.json under HKCU\...\Run – that's
# also how winutil.set_autostart sets it (switch in the Toolbox)
$RunKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'

function Get-AutostartTarget($p) {
    <# What the autostart entry starts, e.g. "E:\...\DiscordPlus.exe" (with quotes) – $null = none. #>
    (Get-ItemProperty $RunKey -Name $p.autostart -ErrorAction SilentlyContinue).($p.autostart)
}

function Remove-Autostart($p) {
    if (Get-AutostartTarget $p) { Remove-ItemProperty $RunKey -Name $p.autostart; Ok 'autostart entry deleted' }
    else { Ok 'no autostart entry' }
}

function Stop-Toolbox {
    <# $true if the Toolbox was running (and is now quit). #>
    if (-not (Send-ToolboxCommand 'status')) { return $false }
    Send-ToolboxCommand 'quit' | Out-Null
    for ($i = 0; $i -lt 50 -and (Send-ToolboxCommand 'status'); $i++) { Start-Sleep -Milliseconds 100 }
    Start-Sleep -Milliseconds 500                 # the process still cleans up briefly after closing the port
    return $true
}

function Start-Toolbox {
    if (Test-Path $Toolbox.StarterPath) { Start-Process $Toolbox.StarterPath; return }
    $exe = if (Test-Path $Toolbox.HostPath) { $Toolbox.HostPath } else { Join-Path $Runtime 'pythonw.exe' }
    Start-Process $exe -ArgumentList "`"$($Toolbox.ScriptPath)`"" -WorkingDirectory $Toolbox.Folder
}

function Invoke-AsAdmin($steps) {
    <# Starts this script again with -Admin after a UAC prompt. $true if everything worked there. #>
    Info 'Windows is now asking for admin rights …'
    try {
        # Without -Wait: in Windows PowerShell that also waits for everything the admin run starts – after
        # monitor-start that means for the Hardware Monitor, i.e. forever. WaitForExit only waits for the window itself.
        $p = Start-Process powershell.exe -Verb RunAs -PassThru -ArgumentList '-NoProfile',
            '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"", '-Admin', ($steps -join ',')
        $null = $p.Handle                         # get the handle right away, otherwise the ExitCode is missing at the end
        $p.WaitForExit()
        return $p.ExitCode -eq 0
    } catch {
        Warn 'Admin rights declined.'
        return $false
    }
}

function Get-RelativePath($from, $to) {
    <# Path from folder $from to $to, e.g. "..\..\runtime" – for the starter, which then still fits after moving.
       (Windows PowerShell 5.1 has no [IO.Path]::GetRelativePath, hence via Uri.) #>
    $base = New-Object Uri ($from.TrimEnd('\') + '\')
    $rel = [Uri]::UnescapeDataString($base.MakeRelativeUri((New-Object Uri $to)).ToString()) -replace '/', '\'
    if ($rel) { $rel } else { '.' }
}

function Build-Starter($p) {
    <# Compiles setup\starter.cs (+ arguments.cs) for this program. Returns: message. It is only built if the generated
       source code or the icon has changed (csc creates a slightly different file on every run – a
       byte comparison wouldn't work). #>
    $folder = Split-Path -Parent $p.StarterPath
    $values = [ordered]@{
        '%NAME%' = $p.name; '%VERSION%' = $p.version; '%HOST%' = (Split-Path -Leaf $p.HostPath); '%COMPANY%' = 'Windows Toolbox'
        '%RUNTIME%' = (Get-RelativePath $folder $Runtime); '%SCRIPT%' = (Get-RelativePath $folder $p.ScriptPath)
    }
    $source = (Get-Content -Raw -Encoding UTF8 (Join-Path $PSScriptRoot 'starter.cs')) + "`r`n" +
              (Get-Content -Raw -Encoding UTF8 (Join-Path $PSScriptRoot 'arguments.cs'))
    foreach ($placeholder in $values.Keys) { $source = $source.Replace($placeholder, $values[$placeholder]) }
    # Checksum of the icon into the source code too – so it gets rebuilt after a new icon
    $source += "`r`n// Icon: $((Get-FileHash $p.IconPath -Algorithm SHA256).Hash)`r`n"
    $memo = Join-Path $Runtime "starter\$($p.id).cs"            # last compiled source code (belongs to runtime\)
    if ((Test-Path $p.StarterPath) -and (Test-Path $memo) -and
        (Get-Content -Raw -Encoding UTF8 $memo) -eq $source) { return "$(Split-Path -Leaf $p.StarterPath) is already up to date" }
    if (-not (Test-Path $Csc)) { throw "C# compiler not found ($Csc)" }

    New-Item -ItemType Directory -Force (Split-Path -Parent $memo) | Out-Null
    $tmp = Join-Path (Split-Path -Parent $memo) "$($p.id).tmp.cs"
    [IO.File]::WriteAllText($tmp, $source, (New-Object Text.UTF8Encoding $true))    # with BOM, otherwise no "ü" in csc
    $new = "$($p.StarterPath).new"
    $output = & $Csc /nologo /target:winexe /optimize+ "/win32icon:$($p.IconPath)" "/out:$new" $tmp 2>&1
    if ($LASTEXITCODE -ne 0) { throw "csc reports: $output" }
    Move-Item -Force $new $p.StarterPath
    Move-Item -Force $tmp $memo
    "$(Split-Path -Leaf $p.StarterPath) created"
}


# ---------- Shortcuts to Toolbox.exe ----------
# Key: folder name for [Environment]::GetFolderPath (also finds a desktop that OneDrive has moved;
# 'Programs' = Start menu of the user, without admin rights); value: what the location is called in the messages
$Locations = [ordered]@{ Desktop = 'Desktop'; Programs = 'Start menu' }

function Get-LocationFolder($location) { [Environment]::GetFolderPath($location) }

function Get-ShortcutPath($location) { Join-Path (Get-LocationFolder $location) "$ShortcutName.lnk" }

function Get-ShortcutTarget($location) {
    <# Where the shortcut points – $null if it doesn't exist. #>
    $path = Get-ShortcutPath $location
    if (-not (Test-Path -LiteralPath $path)) { return $null }
    (New-Object -ComObject WScript.Shell).CreateShortcut($path).TargetPath
}

function Test-OurShortcut($location) {
    <# Does it exist, and does it belong to this folder? If it points into nowhere (folder moved), it counts too. If it
       points to another Toolbox that still exists (second clone), it doesn't – that one is only replaced if you
       explicitly check it in the window, and never deleted. #>
    $target = Get-ShortcutTarget $location
    if ($null -eq $target) { return $false }
    -not $target -or $target -eq $Toolbox.StarterPath -or -not (Test-Path -LiteralPath $target)
}

function Install-Shortcuts($wish) {
    <# 5. $wish from the window: $true/$false per location. Without the window ($null) each stays as it is – only one
       that points into nowhere points to this folder again afterwards. #>
    Step "Shortcuts `"$ShortcutName`""
    foreach ($location in $Locations.Keys) {
        $where = $Locations[$location]
        $ours = Test-OurShortcut $location
        $should = if ($wish) { $wish[$location] } else { $ours }
        if ($should) {
            if ((Get-ShortcutTarget $location) -eq $Toolbox.StarterPath) { Ok "${where}: already there"; continue }
            if (-not (Test-Path $Toolbox.StarterPath)) { Warn "${where}: not created – Toolbox.exe is missing (see above)"; continue }
            $lnk = (New-Object -ComObject WScript.Shell).CreateShortcut((Get-ShortcutPath $location))
            $lnk.TargetPath = $Toolbox.StarterPath
            $lnk.WorkingDirectory = $Root
            $lnk.IconLocation = "$($Toolbox.StarterPath),0"    # the icon is inside Toolbox.exe
            $lnk.Save()
            Ok "${where}: created"
        } elseif ($ours) {
            Remove-Item -LiteralPath (Get-ShortcutPath $location) -Force
            Ok "${where}: deleted"
        } elseif (Get-ShortcutTarget $location) {
            Ok "${where}: points to another Toolbox – stays"
        } else {
            Ok "${where}: none"
        }
    }
}

function Remove-Shortcuts {
    <# For uninstalling – always, not only on request: after removing they would point into nowhere. Every shortcut
       to this Toolbox.exe on the desktop and in the Start menu (there also in subfolders) is deleted – also a
       renamed or moved one –, plus "$ShortcutName" if it points into nowhere (Test-OurShortcut).
       Shortcuts to another Toolbox stay. #>
    $shell = New-Object -ComObject WScript.Shell
    $paths = @(foreach ($location in $Locations.Keys) {
        Get-ChildItem -LiteralPath (Get-LocationFolder $location) -Filter *.lnk -File -Recurse:($location -eq 'Programs') -ErrorAction SilentlyContinue |
            Where-Object { $shell.CreateShortcut($_.FullName).TargetPath -eq $Toolbox.StarterPath } | ForEach-Object FullName
        if (Test-OurShortcut $location) { Get-ShortcutPath $location }
    }) | Select-Object -Unique
    if (-not $paths) { Ok 'none'; return }
    foreach ($path in $paths) {
        try { Remove-Item -LiteralPath $path -Force; Ok "deleted: $path" }
        catch { Warn "couldn't be deleted: $path" }
    }
}


# ---------- Selection window ----------
function Show-SelectionWindow($before) {
    <# Asks in a small window for the language (preselected: Get-Language) and which programs should be installed
       ($before is preselected). Plus two checkboxes for the shortcuts (step 5).
       Returns: Language = code from languages.json, Ids = the chosen IDs (without Toolbox, maybe empty),
       Shortcuts = $true/$false per location – or $null on Cancel.
       Texts: setup.… from toolbox\i18n.json, name and description of the programs from their i18n.json. It opens in
       the preselected language; a click on another one relabels everything right away.
       WinForms belongs to the .NET Framework of Windows – Python and thus tkinter don't exist at this point yet. #>
    Add-Type -AssemblyName System.Windows.Forms, System.Drawing
    # Scale ourselves instead of having Windows draw it blurry (at display scaling above 100 %)
    Add-Type -Namespace Toolbox -Name Dpi -MemberDefinition '[DllImport("user32.dll")] public static extern bool SetProcessDPIAware();'
    [Toolbox.Dpi]::SetProcessDPIAware() | Out-Null
    [Windows.Forms.Application]::EnableVisualStyles()

    $form = New-Object Windows.Forms.Form
    $s = $form.CreateGraphics().DpiX / 96                 # scaling for fixed pixel sizes
    $preselected = Get-Language
    $toolboxTexts = Load-Texts (Join-Path $Root 'toolbox\i18n.json')
    # All labels: control and its text per language – a click on a language sets them again
    $labels = New-Object Collections.ArrayList
    function Set-Label($control, $texts) {
        [void]$labels.Add([pscustomobject]@{ Control = $control; Texts = $texts })
        $control.Text = $texts[$preselected]
    }
    Set-Label $form (Get-Translated $toolboxTexts 'setup.title')
    $form.Icon = New-Object Drawing.Icon (Join-Path $Root 'toolbox\toolbox.ico')
    $form.Font = New-Object Drawing.Font('Segoe UI', 9)
    $form.FormBorderStyle = 'FixedDialog'
    $form.MaximizeBox = $form.MinimizeBox = $false
    $form.StartPosition = 'CenterScreen'
    $form.AutoSize = $true
    $form.AutoSizeMode = 'GrowAndShrink'
    $form.TopMost = $true                                 # don't disappear behind the console window
    $form.Add_Shown({ $form.Activate() })

    $list = New-Object Windows.Forms.TableLayoutPanel
    $list.AutoSize = $true
    $list.ColumnCount = 1
    $list.Padding = New-Object Windows.Forms.Padding ([int](14 * $s))
    $form.Controls.Add($list)

    function Add-Row($control, $marginTop = 0, $indent = 0) {
        $control.AutoSize = $true
        $control.Margin = New-Object Windows.Forms.Padding ([int]($indent * $s)), ([int]($marginTop * $s)), 0, 0
        $list.Controls.Add($control)
    }

    # Language of the Toolbox and all programs – it can be changed later in the Toolbox (⚙ → Appearance)
    $title = New-Object Windows.Forms.Label
    Set-Label $title (Get-Translated $toolboxTexts 'setup.language')
    $title.Font = New-Object Drawing.Font($form.Font, [Drawing.FontStyle]::Bold)
    Add-Row $title
    $languages = New-Object Windows.Forms.FlowLayoutPanel  # own container: the radio buttons exclude each other
    $languages.AutoSize = $true
    $languages.MaximumSize = New-Object Drawing.Size ([int](380 * $s)), 0     # many languages: into the next line
    $languageButtons = @()
    foreach ($language in $LanguageList.languages.PSObject.Properties) {      # one field per language from languages.json
        $button = New-Object Windows.Forms.RadioButton
        $button.Text = "$($language.Value) ($($language.Name.ToUpper()))"     # e.g. "Deutsch (DE)"
        $button.Tag = $language.Name
        $button.AutoSize = $true
        $button.Checked = $language.Name -eq $preselected
        $button.Add_CheckedChanged({                      # another language chosen: relabel everything right away
            if ($this.Checked) { foreach ($l in $labels) { $l.Control.Text = $l.Texts[$this.Tag] } }
        }.GetNewClosure())
        $languages.Controls.Add($button)
        $languageButtons += $button
    }
    Add-Row $languages 4

    $title = New-Object Windows.Forms.Label
    Set-Label $title (Get-Translated $toolboxTexts 'setup.programs')
    $title.Font = New-Object Drawing.Font($form.Font, [Drawing.FontStyle]::Bold)
    Add-Row $title 16

    $gray = [Drawing.SystemColors]::GrayText
    $checkboxes = @()
    foreach ($p in $All) {
        $box = New-Object Windows.Forms.CheckBox
        $name = Get-Translated $p.Texts 'program.name' $p.name
        foreach ($code in @($name.Keys)) { $name[$code] = "$($name[$code]) $($p.version)" }
        Set-Label $box $name
        $box.Tag = $p.id
        $box.Checked = $p.id -eq 'toolbox' -or $before -contains $p.id
        $box.Enabled = $p.id -ne 'toolbox'                # the Toolbox is always included
        Add-Row $box 10
        $checkboxes += $box
        if ($p.description) {
            $text = New-Object Windows.Forms.Label
            Set-Label $text (Get-Translated $p.Texts 'program.description' $p.description)
            $text.ForeColor = $gray
            $text.MaximumSize = New-Object Drawing.Size ([int](380 * $s)), 0      # wrap long texts
            Add-Row $text 0 18
        }
    }

    $selectAll = New-Object Windows.Forms.LinkLabel
    Set-Label $selectAll (Get-Translated $toolboxTexts 'setup.all')
    $selectAll.Add_LinkClicked({ foreach ($box in $checkboxes) { $box.Checked = $true } }.GetNewClosure())
    Add-Row $selectAll 12

    $hint = New-Object Windows.Forms.Label
    Set-Label $hint (Get-Translated $toolboxTexts 'setup.hint')
    $hint.ForeColor = $gray
    $hint.MaximumSize = New-Object Drawing.Size ([int](380 * $s)), 0
    Add-Row $hint 8

    $title = New-Object Windows.Forms.Label
    Set-Label $title (Get-Translated $toolboxTexts 'setup.shortcuts')
    $title.Font = New-Object Drawing.Font($form.Font, [Drawing.FontStyle]::Bold)
    Add-Row $title 16
    $locationBoxes = @{}                                  # location -> checkbox
    foreach ($location in $Locations.Keys) {
        $box = New-Object Windows.Forms.CheckBox
        Set-Label $box (Get-Translated $toolboxTexts $(if ($location -eq 'Desktop') { 'setup.desktop' } else { 'setup.start_menu' }))
        $box.Checked = Test-OurShortcut $location         # off on the first setup; unchecking deletes it
        Add-Row $box 6
        $locationBoxes[$location] = $box
    }

    $buttons = New-Object Windows.Forms.FlowLayoutPanel
    $buttons.FlowDirection = 'RightToLeft'
    $cancel = New-Object Windows.Forms.Button
    Set-Label $cancel (Get-Translated $toolboxTexts 'setup.cancel')
    $cancel.DialogResult = 'Cancel'
    $ok = New-Object Windows.Forms.Button
    Set-Label $ok (Get-Translated $toolboxTexts 'setup.install')
    $ok.DialogResult = 'OK'
    foreach ($button in $cancel, $ok) {
        $button.AutoSize = $true
        $button.MinimumSize = New-Object Drawing.Size ([int](88 * $s)), 0
        $buttons.Controls.Add($button)
    }
    $form.AcceptButton = $ok
    $form.CancelButton = $cancel
    Add-Row $buttons 14
    $buttons.Dock = 'Fill'                                # after Add-Row: buttons right-aligned across the full width

    $result = $form.ShowDialog()
    $ids = @($checkboxes | Where-Object { $_.Checked -and $_.Tag -ne 'toolbox' } | ForEach-Object { $_.Tag })
    $shortcuts = @{}
    foreach ($location in $Locations.Keys) { $shortcuts[$location] = $locationBoxes[$location].Checked }
    $language = ($languageButtons | Where-Object Checked | Select-Object -First 1).Tag
    $form.Dispose()
    if ($result -ne 'OK') { return $null }
    [pscustomobject]@{ Language = $language; Ids = $ids; Shortcuts = $shortcuts }
}


# ---------- State before setting up – is exactly the same afterwards (also after an update) ----------
function Get-Autostart {
    <# 'on' or 'off' (switch "Autostart" in the Toolbox) – $null if the task doesn't exist. #>
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $task) { $null } elseif ($task.State -eq 'Disabled') { 'off' } else { 'on' }
}

function Save-State {
    <# Notes at the very beginning what the user has set and setting up might touch –
       Restore-State restores it at the end:
       - autostart: the task lives in Windows, not in data\ – and Windows creates it enabled when setting it up again
       - whether the Hardware Monitor was running (whether the Toolbox was running, setting up notes itself: $toolboxWasRunning)
       - which other programs were running (Get-OtherPrograms) – setting up quits them, afterwards they run again
       - the settings files in data\ (setting up itself only writes installed.json there – the selection – and
         after the window the language into toolbox.json) #>
    $files = @{}
    foreach ($f in Get-ChildItem (Join-Path $Root 'data\*.json') -ErrorAction SilentlyContinue) {
        if ($f.Name -ne (Split-Path -Leaf $InstalledFile)) { $files[$f.Name] = [IO.File]::ReadAllText($f.FullName) }
    }
    $running = @(Get-OtherPrograms | Where-Object { Send-Command $_.port 'status' } | ForEach-Object id)
    [pscustomobject]@{ Autostart = Get-Autostart; MonitorWasRunning = [bool](Send-MonitorCommand 'status'); Running = $running
                       Files = $files }
}

function Test-JsonReadable($path) {
    try { $text = [IO.File]::ReadAllText($path); if (-not $text.Trim()) { return $false }; $null = $text | ConvertFrom-Json; $true }
    catch { $false }
}

function Restore-State($before, $monitorInstalled, $restartMonitor, $ids) {
    <# Restores what Save-State noted. Also runs if setting up aborts on the way.
       $monitorInstalled: Hardware Monitor is (still) installed. $restartMonitor: if it is running, restart it with the
       new code (-Restart after an update, quit in step 3 for the new .exe, task now points somewhere else).
       $ids: the installed programs (other programs only start again if they still belong to them). #>
    Step 'Everything as before? (autostart, running programs, settings)'
    $admin = @()                                  # what only works with admin rights – together in ONE UAC prompt

    # Autostart: exactly as before. If the task didn't exist yet, it is off (that's how task_command creates it).
    $should = if ($before.Autostart) { $before.Autostart } else { 'off' }
    $is = Get-Autostart
    if (-not $is) {
        if ($monitorInstalled -and $before.Autostart) { Warn "Task $TaskName is missing – run Setup.exe again." }
    } elseif ($is -eq $should) {
        Ok $(if ($before.Autostart) { "Autostart: $is – as before" } else { 'Autostart: off (turn it on in the Toolbox)' })
    } else {
        Info "Autostart is $is, was $should – setting it back"
        $admin += "autostart-$should"             # the task runs with admin rights -> change only with admin rights
    }

    # Hardware Monitor: if it was running before, it runs again afterwards (with the new code); if not, it stays off
    $running = [bool](Send-MonitorCommand 'status')
    if (-not $monitorInstalled) {
        # deselected or never installed – nothing to do
    } elseif (-not $before.MonitorWasRunning) {
        Ok $(if ($running) { 'Hardware Monitor is running' } else { 'Hardware Monitor: not started – as before (start it via the Toolbox)' })
    } elseif ($running -and -not $restartMonitor) {
        Ok 'Hardware Monitor is running – as before'
    } elseif (-not (Test-Path $Monitor.StarterPath)) {
        Warn "Hardware Monitor was running before, but $(Split-Path -Leaf $Monitor.StarterPath) is missing (see above) – run Setup.exe again."
    } else {
        if ($running) { Stop-Monitor }            # still running with the old code
        if ($is -eq 'on') {                       # via the task: without UAC prompt
            Start-ScheduledTask -TaskName $TaskName
            Ok $(if ($running) { 'Hardware Monitor restarted – was running before' } else { 'Hardware Monitor started again – was running before' })
        } else {
            $admin += 'monitor-start'             # autostart off -> needs admin rights for the CPU values
        }
    }

    # Other programs (without admin rights): setting up quit them – if one was running before, start it again now
    foreach ($p in Get-OtherPrograms | Where-Object { $before.Running -contains $_.id }) {
        if (Send-Command $p.port 'status') { Ok "$($p.name) is running – as before" }
        elseif ($ids -notcontains $p.id) { Ok "$($p.name): removed, no longer running" }
        elseif (-not (Test-Path $p.StarterPath)) { Warn "$($p.name) was running before, but $(Split-Path -Leaf $p.StarterPath) is missing (see above)." }
        else {
            try { Start-Process $p.StarterPath -WorkingDirectory $p.Folder; Ok "$($p.name) started again – was running before" }
            catch { Warn "$($p.name) didn't start: $_" }
        }
    }

    if ($admin.Count -gt 0) {
        $messages = @{ 'autostart-on' = 'Autostart: on – as before'; 'autostart-off' = 'Autostart: off – as before'
                       'monitor-start' = 'Hardware Monitor started again – was running before' }
        if ($NoAdmin) { Warn "skipped (-NoAdmin): $($admin -join ', ') – catch up in the Toolbox." }
        elseif (Invoke-AsAdmin $admin) { foreach ($s in $admin) { Ok $messages[$s] } }
        else { Warn 'Not everything could be restored – catch up in the Toolbox (Hardware Monitor page).' }
    }

    # Settings in data\: if a file is missing or broken, the one from before comes back
    $same = 0
    foreach ($name in $before.Files.Keys) {
        $path = Join-Path $Root "data\$name"
        if (-not (Test-JsonReadable $path)) {
            [IO.File]::WriteAllText($path, $before.Files[$name], (New-Object Text.UTF8Encoding $false))
            Ok "data\$name was gone or broken – restored"
        } elseif ([IO.File]::ReadAllText($path) -eq $before.Files[$name]) {
            $same++
        } else {                                  # e.g. window position that the monitor saves when quitting
            Info "data\${name}: saved by the program itself (e.g. when quitting)"
        }
    }
    if ($before.Files.Count -eq 0) { Ok 'Settings: none saved yet' }
    elseif ($same -eq $before.Files.Count) { Ok "Settings in data\: all $same files unchanged" }
}


# ---------- The part with admin rights (runs in its own window) ----------
function Invoke-AdminSteps($steps) {
    $ok = $true
    if ($steps -contains 'pawnio') {
        Step 'Install PawnIO'
        winget install --id namazso.PawnIO --exact --accept-package-agreements --accept-source-agreements | Out-Host
        if ($LASTEXITCODE -eq 0) { Ok 'installed' } else { Warn "winget reports code $LASTEXITCODE"; $ok = $false }
    }
    if ($steps -contains 'task') {
        Step "Set up task $TaskName"
        & $RuntimePy -B -c $PyTask (Join-Path $Root 'toolbox') $TaskName $Monitor.StarterPath | Out-Host
        if ($LASTEXITCODE -ne 0) { Warn 'failed'; $ok = $false } else { Ok 'set up' }
    }
    # Set back to how it was before setting up (Restore-State)
    if ($steps -contains 'autostart-on') {
        Step 'Turn autostart back on'
        try { Enable-ScheduledTask -TaskName $TaskName | Out-Null; Ok 'on, as before' }
        catch { Warn $_; $ok = $false }
    }
    if ($steps -contains 'autostart-off') {
        Step 'Turn autostart back off'
        try { Disable-ScheduledTask -TaskName $TaskName | Out-Null; Ok 'off, as before' }
        catch { Warn $_; $ok = $false }
    }
    if ($steps -contains 'monitor-start') {             # started with admin rights -> the monitor has them too
        Step 'Start Hardware Monitor again'
        try { Start-Process $Monitor.StarterPath -WorkingDirectory $Monitor.Folder; Ok 'started' }
        catch { Warn $_; $ok = $false }
    }
    if ($steps -contains 'task-delete') {
        Step "Delete task $TaskName"
        try { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false; Ok 'deleted' }
        catch { Warn $_; $ok = $false }
    }
    if (-not $ok) { Read-Host "`nPress Enter to close" | Out-Null }   # keep errors readable
    return $ok
}


# ---------- Set up ----------
function Find-Python {
    <# Registered Python $PythonVersion (64 bit) from the registry (PEP 514) – or $null.
       Other versions deliberately don't count: requirements.txt is only tested with $PythonVersion. #>
    foreach ($hive in 'HKCU:', 'HKLM:') {
        $exe = (Get-ItemProperty "$hive\Software\Python\PythonCore\$PythonVersion\InstallPath" `
                    -ErrorAction SilentlyContinue).ExecutablePath
        if ($exe -and (Test-Path $exe)) { return [pscustomobject]@{ Version = $PythonVersion; Exe = $exe } }
    }
    $null
}

function Get-RuntimeVersion {
    <# Major.minor of the Python in runtime\, e.g. "3.14". #>
    & $RuntimePy -c 'import sys; print(*sys.version_info[:2], sep=''.'')'
}

function Install-Toolbox {
    # Note what is set before anything happens – at the end it is exactly the same again (Restore-State)
    $stateBefore = Save-State

    # 0. Which programs: from -Programs, as before (-Restart) or from the window
    $before = Get-Installed
    $shortcuts = $null                            # only the window asks for them – otherwise they stay as they are
    if ($Programs) { $ids = @($before) + @(Get-ProgramIds $Programs) | Select-Object -Unique }
    elseif ($Restart) { $ids = $before }
    else {
        $choice = Show-SelectionWindow $before
        if ($null -eq $choice) { Write-Host 'Cancelled – nothing changed.'; return }
        $ids = $choice.Ids
        $shortcuts = $choice.Shortcuts
        Save-Language $choice.Language
        # belongs to the choice in the window, not to what Restore-State restores at the end
        $stateBefore.Files[(Split-Path -Leaf $ToolboxFile)] = [IO.File]::ReadAllText($ToolboxFile)
        Ok "Language: $($choice.Language)"
    }
    $ids = @($ids)
    Save-Installed $ids                           # save right away: if something below aborts, the choice still applies
    # Steps 3–7 for all chosen programs – with -Programs only for the named ones (the others are already
    # installed). Python and runtime\ (1–2) are needed by all, they are always checked.
    $Selection = @($All | Where-Object {
        if ($Programs) { (Get-ProgramIds $Programs) -contains $_.id } else { $_.id -eq 'toolbox' -or $ids -contains $_.id }
    })
    $withMonitor = $Selection -contains $Monitor

    # A running Toolbox keeps files in runtime\ locked (packages, Toolbox.exe) -> quit it first, restart it at the end
    $toolboxWasRunning = Stop-Toolbox
    if ($toolboxWasRunning) { Info 'Toolbox quit for the setup – will be started again at the end.' }
    # The same for other programs (they keep their .exe in runtime\ locked; afterwards they start with the new code)
    foreach ($p in Get-OtherPrograms | Where-Object { $stateBefore.Running -contains $_.id }) {
        Stop-Program $p
        Start-Sleep -Milliseconds 500             # the process still cleans up briefly after closing the port
        Info "$($p.name) quit for the setup – will be started again at the end."
    }

    # The steps themselves; restoring and the Toolbox start also come if something aborts on the way
    $run = @{ RestartMonitor = [bool]$Restart }   # restart the monitor (-Restart: after an update) – set by the steps
    try {
        Install-Steps $before $ids $Selection $withMonitor $run $shortcuts | Out-Host
    } finally {
        try { Restore-State $stateBefore ($ids -contains $Monitor.id) $run.RestartMonitor $ids }
        catch { Warn "Restoring failed: $_" }
        if ($toolboxWasRunning) { Start-Toolbox }
    }

    Write-Host ""
    if ($script:Warnings) {
        Write-Host "Done, but not everything worked – see the yellow [!] lines above." -ForegroundColor Yellow
    } elseif ($toolboxWasRunning) {
        Write-Host "Done. The Toolbox was started again." -ForegroundColor Green
    } else {
        Write-Host "Done. Start the Toolbox with Toolbox.exe." -ForegroundColor Green
    }
}

function Install-Steps($before, $ids, $Selection, $withMonitor, $run, $shortcuts) {
    foreach ($p in $All | Where-Object { $before -contains $_.id -and $ids -notcontains $_.id }) {
        Uninstall-Program $p                      # deselected in the window
    }

    # 1. Python
    Step "Python $PythonVersion"
    if (Test-Path $RuntimePy) {
        $present = Get-RuntimeVersion
        if ($present -eq $PythonVersion) { Ok 'runtime\ is already there – the installed Python is not needed' }
        else { Warn "runtime\ contains Python $present instead of $PythonVersion – to switch, delete runtime\ and set up again." }
    } else {
        $python = Find-Python
        if (-not $python) {
            Info "Python $PythonVersion not found – installing it via winget …"
            winget install --id "Python.Python.$PythonVersion" --exact --scope user --accept-package-agreements --accept-source-agreements
            $python = Find-Python
            if (-not $python) { throw "Python $PythonVersion could not be installed. Please install it from python.org and start again." }
        }
        Ok "Python $($python.Version): $($python.Exe)"
    }

    # 2. runtime\
    Step 'Our own Python in the project folder (runtime\)'
    if (-not (Test-Path $RuntimePy)) {
        $base = Split-Path -Parent $python.Exe
        Info "Copying $base …"
        # Without docs, tests, developer files and the installed packages (those come fresh in a moment)
        robocopy $base $Runtime /E /NFL /NDL /NJH /NJS /NP `
            /XD (Join-Path $base 'Doc') (Join-Path $base 'include') (Join-Path $base 'libs') `
                (Join-Path $base 'Scripts') (Join-Path $base 'Tools') (Join-Path $base 'Lib\site-packages') `
                (Join-Path $base 'Lib\test') __pycache__ `
            /XF *.pyc | Out-Null
        if ($LASTEXITCODE -ge 8) { throw "Copying failed (robocopy code $LASTEXITCODE)" }
        New-Item -ItemType Directory -Force (Join-Path $Runtime 'Lib\site-packages') | Out-Null

        # Python should only use what is in runtime\ – nothing from the installed Python or the user folder.
        # That way it is noticed right away when something is missing, instead of only on another PC.
        # ._pth file: fixed search paths, environment variables like PYTHONPATH don't count
        $dll = Get-ChildItem $Runtime -Filter 'python3*.dll' | Where-Object Name -ne 'python3.dll' | Select-Object -First 1
        "$($dll.BaseName).zip`r`nDLLs`r`nLib`r`nimport site`r`n" |
            Set-Content -Encoding ASCII (Join-Path $Runtime "$($dll.BaseName)._pth")
        # sitecustomize.py: takes the packages from %APPDATA%\Python out again (the ._pth file alone doesn't do that)
        "# Created by Setup.exe: don't use packages from the user folder (%APPDATA%\Python)`r`n" +
        "import site, sys`r`n" +
        "if site.getusersitepackages() in sys.path:`r`n" +
        "    sys.path.remove(site.getusersitepackages())`r`n" |
            Set-Content -Encoding ASCII (Join-Path $Runtime 'Lib\sitecustomize.py')

        Info 'Installing pip …'
        # Discard the output (among others the warning that runtime\Scripts isn't in the PATH – it isn't needed);
        # 'Continue', because PowerShell 5.1 otherwise treats text on stderr as an error
        $ErrorActionPreference = 'Continue'
        & $RuntimePy -m ensurepip --default-pip 2>&1 | Out-Null
        $ErrorActionPreference = 'Stop'
        if ($LASTEXITCODE -ne 0) { throw 'pip could not be set up' }
        Ok 'runtime\ created'
    }
    # Without ssl pip loads nothing from PyPI – e.g. if libcrypto-3.dll was missing when copying. Better abort clearly here.
    & $RuntimePy -c 'import ssl'
    if ($LASTEXITCODE -ne 0) { throw 'runtime\ is incomplete (ssl is missing) – delete the folder runtime\ and set up again' }
    Info 'Packages from requirements.txt (fixed versions) …'
    & $RuntimePy -m pip install --disable-pip-version-check --no-warn-script-location --quiet `
        -r (Join-Path $Root 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Packages could not be installed' }
    & $RuntimePy -c 'import tkinter, customtkinter, pystray, PIL, clr, pygame'
    if ($LASTEXITCODE -ne 0) { throw 'runtime\ is incomplete – delete the folder runtime\ and set up again' }
    Ok 'Packages complete'

    # 3. Per program: pythonw.exe copy with its own name and icon + starter
    foreach ($p in $Selection | Where-Object StarterPath) {
        Step "$($p.name): $(Split-Path -Leaf $p.StarterPath)"
        $message = & $RuntimePy -B (Join-Path $PSScriptRoot 'make_exe.py') $p.HostPath $p.name $p.IconPath
        # 2 = file locked because the program is running. We may quit the monitor briefly (step 7 restarts it),
        # but not the Toolbox – there the old file stays until the next setup.
        if ($LASTEXITCODE -eq 2 -and $p -eq $Monitor -and (Send-MonitorCommand 'status')) {
            Info 'Hardware Monitor is still running with the old file – quitting it briefly …'
            Stop-Monitor
            $run.RestartMonitor = $true
            # The process still cleans up briefly after the last IPC sign of life (closing LHM) – the file is
            # still locked that long. Retry for up to 10 s.
            for ($i = 0; $i -lt 20; $i++) {
                $message = & $RuntimePy -B (Join-Path $PSScriptRoot 'make_exe.py') $p.HostPath $p.name $p.IconPath
                if ($LASTEXITCODE -ne 2) { break }
                Start-Sleep -Milliseconds 500
            }
        }
        if ($LASTEXITCODE -eq 0) { Ok "runtime\$message" }
        elseif ($LASTEXITCODE -eq 2) { Warn "$message (e.g. close the Toolbox)" }
        else { Warn $message }

        try { Ok (Build-Starter $p) }
        catch { Warn "Starter not created: $_" }

        # Autostart without admin rights: an existing entry still points to the old location after moving
        if ($p.autostart) {
            $target = Get-AutostartTarget $p
            if (-not $target) { Ok 'Autostart: off (turn it on in the Toolbox)' }
            elseif ($target -eq "`"$($p.StarterPath)`"") { Ok 'Autostart: on' }
            else {
                Set-ItemProperty $RunKey -Name $p.autostart -Value "`"$($p.StarterPath)`""
                Ok "Autostart now points here (before: $target)"
            }
        }
    }

    # 4. Per program: downloads from program.json
    foreach ($p in $Selection) {
        foreach ($d in @($p.downloads | Where-Object { $_ })) {
            Step "$($d.name) $($d.version) for $($p.name)"
            $target = Join-Path $p.Folder $d.folder
            $checkFile = Join-Path $target $d.check_file
            if (Test-Path $checkFile) {
                $present = (Get-Item $checkFile).VersionInfo.ProductVersion -replace '\+.*$', ''
                if ($present -eq $d.version) { Ok 'already there' }
                else { Warn "$($d.folder)\ contains version $present instead of $($d.version) – stays that way (delete the folder to replace it)." }
            } else {
                $zip = Join-Path ([IO.Path]::GetTempPath()) "$($p.id)-$($d.folder)-$($d.version).zip"
                Info "Downloading $($d.url) …"
                Invoke-WebRequest $d.url -OutFile $zip -UseBasicParsing
                if ((Get-FileHash $zip -Algorithm SHA256).Hash -ne $d.sha256) {
                    Remove-Item $zip
                    throw 'Checksum of the downloaded file doesn''t match – download aborted.'
                }
                Expand-Archive $zip -DestinationPath $target -Force
                Remove-Item $zip
                Get-ChildItem $target -Recurse -File | Unblock-File    # remove the "from the internet" mark, otherwise .NET won't load the DLLs
                Ok "extracted to $target"
            }
        }
    }

    Install-Shortcuts $shortcuts

    if ($withMonitor) { Install-Monitor $run }
    # 7. (Re)start what was running before, autostart as before: Restore-State (in Install-Toolbox)
}

function Install-Monitor($run) {
    # 6. Admin rights: PawnIO and task
    Step 'PawnIO and autostart task'
    $steps = @()
    if (Get-Service PawnIO -ErrorAction SilentlyContinue) { Ok 'PawnIO is installed' }
    else { Info 'PawnIO is missing'; $steps += 'pawnio' }

    # The task starts the starter without arguments (like task_points_here in hardware_monitor_gui.py)
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    $taskFits = $task -and $task.Actions[0].Execute -eq $Monitor.StarterPath -and -not $task.Actions[0].Arguments
    if ($taskFits) { Ok "Task $TaskName points to this folder" }
    elseif (-not (Test-Path $Monitor.StarterPath)) { Warn "$($Monitor.StarterPath) is missing (see above) – task stays as it is" }
    elseif ($task) { Info "Task $TaskName still points to: $($task.Actions[0].Execute) $($task.Actions[0].Arguments)"; $steps += 'task' }
    else { Info "Task $TaskName is missing"; $steps += 'task' }
    # Autostart stays as it was: task_command turns the newly created task off again right away if it
    # was off before or missing; Restore-State checks it once more at the end

    if ($steps.Count -eq 0) {
        # nothing to do
    } elseif ($NoAdmin) {
        Warn 'skipped (-NoAdmin)'
    } elseif (Invoke-AsAdmin $steps) {
        Ok 'done'
        # A running monitor still came from the old task (different folder) -> restart it
        if ($steps -contains 'task') { $run.RestartMonitor = $true }
    } else {
        Warn 'Not everything worked – run Setup.exe again.'
    }
}


# ---------- Uninstall ----------
function Remove-Task {
    if (-not (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue)) {
        Ok "Task $TaskName doesn't exist"
        return
    }
    try {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Ok "Task $TaskName deleted"
    } catch {                                     # the task runs with admin rights – deleting it usually needs them too
        if (Invoke-AsAdmin @('task-delete')) { Ok "Task $TaskName deleted" } else { Warn "The task $TaskName is still there." }
    }
}

function Uninstall-Program($p) {
    <# Take a program out again: quit it, delete the task, delete starter, pythonw.exe copy and downloads.
       The code stays (belongs to the repo), the settings in data\ too – setting up makes it complete again. #>
    Step "Remove $($p.name)"
    $anything = $false
    if ($p.port -and (Send-Command $p.port 'status')) { Stop-Program $p; Ok 'quit'; $anything = $true }
    if ($p.id -eq $Monitor.id -and (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue)) {
        Remove-Task; $anything = $true
    }
    if ($p.autostart -and (Get-AutostartTarget $p)) { Remove-Autostart $p; $anything = $true }
    $paths = @($p.StarterPath, $p.HostPath, (Join-Path $Runtime "starter\$($p.id).cs")) +
             @(@($p.downloads | Where-Object { $_ }) | ForEach-Object { Join-Path $p.Folder $_.folder }) |
             Where-Object { $_ -and (Test-Path $_) }
    foreach ($path in $paths) {
        # A program that was just quit still holds on to its .exe briefly – retry for up to 10 s
        for ($i = 0; ; $i++) {
            try { Remove-Item $path -Recurse -Force; Ok "deleted: $path"; break }
            catch {
                if ($i -ge 20) { Warn "couldn't be deleted: $path"; break }
                Start-Sleep -Milliseconds 500
            }
        }
        $anything = $true
    }
    if (-not $anything) { Ok 'was not installed' }
}

function Uninstall-Programs {
    <# -Uninstall -Programs <ids>: only these programs. The Toolbox is quit for it and restarted afterwards,
       so it shows the changed selection. #>
    if (($Programs -split ',' | ForEach-Object { $_.Trim() }) -contains 'toolbox') {
        Warn 'The Toolbox itself is removed by Uninstall.exe without -Programs.'
    }
    $ids = @(Get-ProgramIds $Programs)
    if (-not $ids) { return }
    $toolboxWasRunning = Stop-Toolbox
    foreach ($p in $All | Where-Object { $ids -contains $_.id }) { Uninstall-Program $p }
    Save-Installed @(Get-Installed | Where-Object { $ids -notcontains $_ })

    Write-Host ""
    if ($toolboxWasRunning) {
        Start-Toolbox
        Write-Host "Done. The Toolbox was started again." -ForegroundColor Green
    } else {
        Write-Host "Done." -ForegroundColor Green
    }
}

function Uninstall-Toolbox {
    Step 'Quit Toolbox'
    if (Stop-Toolbox) { Ok 'quit' } else { Ok 'was not running' }

    Step 'Quit Hardware Monitor'
    if (Send-MonitorCommand 'status') { Stop-Monitor; Ok 'quit' } else { Ok 'was not running' }

    foreach ($p in Get-OtherPrograms) {
        Step "Quit $($p.name)"
        if (Send-Command $p.port 'status') { Stop-Program $p; Ok 'quit' } else { Ok 'was not running' }
    }

    Step "Delete task $TaskName"
    Remove-Task

    foreach ($p in $All | Where-Object autostart) {
        Step "Delete autostart of $($p.name)"
        Remove-Autostart $p
    }

    Step 'Delete shortcuts (desktop, Start menu)'
    Remove-Shortcuts

    Step 'Generated and downloaded files'
    $paths = @($Runtime) + @($All | ForEach-Object {
        $p = $_
        $p.StarterPath
        @($p.downloads | Where-Object { $_ }) | ForEach-Object { Join-Path $p.Folder $_.folder }
    }) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }
    if (-not $paths) {
        Ok 'nothing there'
    } else {
        $paths | ForEach-Object { Info $_ }
        if ((Read-Host '   Delete all of this? (y/n)') -match '^[yYjJ]') {
            try {
                $paths | ForEach-Object { Remove-Item -LiteralPath $_ -Recurse -Force }
                Ok 'deleted'
            } catch {
                Warn 'Not everything could be deleted – is the Toolbox still running? Then close it and try again.'
            }
        } else {
            Ok 'kept'
        }
    }

    Write-Host ""
    Write-Host "Done. You can delete the folder now (data\ contains your settings)." -ForegroundColor Green
    Write-Host "PawnIO stays installed (to remove: winget uninstall namazso.PawnIO)." -ForegroundColor Green
}


if ($Admin) { exit $(if (Invoke-AdminSteps ($Admin -split ',')) { 0 } else { 1 }) }
elseif ($Uninstall -and $Programs) { Uninstall-Programs }
elseif ($Uninstall) { Uninstall-Toolbox }
else { Install-Toolbox }
# Exit code for Setup.exe/Uninstall.exe: 0 = everything worked -> window closes by itself; 2 = done, but with
# warnings -> stays open so you can read them (1 = aborted, PowerShell does that itself on an error)
exit $(if ($Warnings) { 2 } else { 0 })
