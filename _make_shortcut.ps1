$ws = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$lnk = $ws.CreateShortcut("$desktop\Overlord Creator.lnk")
$lnk.TargetPath = "C:\Users\thatg\Desktop\Creator\launch_overlord.bat"
$lnk.WorkingDirectory = "C:\Users\thatg\Desktop\Creator"
$lnk.Description = "Overlord Agent - AI Code Generator"
$lnk.Save()
Write-Host "Desktop shortcut created!"
