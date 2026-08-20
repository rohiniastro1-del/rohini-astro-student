Option Explicit

Dim shell, fileSystem, appRoot, command
Set shell = CreateObject("WScript.Shell")
Set fileSystem = CreateObject("Scripting.FileSystemObject")
appRoot = fileSystem.GetParentFolderName(WScript.ScriptFullName)
command = "powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File """ & appRoot & "\start_dev.ps1"""
shell.Run command, 0, False
