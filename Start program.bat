@echo off
set console=0

chcp 65001>nul
if not exist System goto File_error

if %console% == 0 powershell.exe -Command "Start-Process cmd.exe -ArgumentList '/c System\Start.bat %console%' -WindowStyle Hidden"||goto Error
if %console% NEQ 0 System\Start.bat %console%||goto Error

exit /b 0

:Error
echo An error occurred.
call :MsgBox "The program failed to start for unknown reasons, please check the programs system files" "Error" "Error"
pause>nul
exit

:File_error
echo An error occurred.
echo The program could not be started due to missing system files. You may have not unpacked the program from the archive
call :MsgBox "Программа не может быть запущена из-за отсутствия системных файлов. Возможно, вы не распаковали программу из архива" "Error" "Error"
exit

:MsgBox
setlocal
set "Message=%~1"
set "Title=%~2"
set "Status=%~3"
set "stat=0"

if /i "%Status%"=="Error" set "stat=16"
if /i "%Status%"=="Info" set "stat=64"

set "VBSFile=%temp%\temp_message_%random%.vbs"

echo Set WShell = CreateObject("WScript.Shell") > "%VBSFile%"
echo WShell.Popup "%Message%", 0, "%Title%", %stat% >> "%VBSFile%"

"%VBSFile%"

del "%VBSFile%"
endlocal
exit /b