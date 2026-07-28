Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "py -3 """ & CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\WelfareOn_Launcher.pyw""", 0, False
