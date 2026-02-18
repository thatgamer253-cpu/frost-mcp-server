$WshShell = New-Object -comObject WScript.Shell
$DesktopPath = [System.Environment]::GetFolderPath('Desktop')
$Shortcut = $WshShell.CreateShortcut("$DesktopPath\Overlord V2.lnk")
$Shortcut.TargetPath = "pythonw"
$Shortcut.Arguments = """$($PWD.Path)\creator_v2.py"""
$Shortcut.IconLocation = """$($PWD.Path)\assets\icon.ico"""
$Shortcut.WorkingDirectory = "$($PWD.Path)"
$Shortcut.Save()
Write-Host "Shortcut created: $DesktopPath\Overlord V2.lnk"
