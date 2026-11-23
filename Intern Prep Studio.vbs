' Double-click this file to start Intern Prep Studio without a console window.
' Closing the app window stops everything a few seconds later.
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
appDir = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = appDir
sh.Run "python """ & appDir & "\launcher.pyw""", 0, False
