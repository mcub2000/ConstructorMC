@echo off
chcp 65001>nul
set "console=%~1"
color a
title Console
System\Python\python.exe System\Python\Main.py %console%