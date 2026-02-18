$WshShell = New-Object -ComObject WScript.Shell
$Desktop = [System.Environment]::GetFolderPath('Desktop')
$Shortcut = $WshShell.CreateShortcut("$Desktop\Overlord V2.lnk")
$Shortcut.TargetPath = "C:\Users\thatg\Desktop\Creator\launch_v2.bat"
$Shortcut.WorkingDirectory = "C:\Users\thatg\Desktop\Creator"
$Shortcut.Description = "Launch Overlord V2"
$Shortcut.IconLocation = "shell32.dll,21"
$Shortcut.WindowStyle = 1
$Shortcut.Save()
Write-Host "Shortcut created on Desktop!"
