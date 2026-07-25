@echo off
echo Test 1: start http://localhost:8000
start http://localhost:8000
if %ERRORLEVEL% neq 0 echo ECHEC 1: %ERRORLEVEL%
pause

echo Test 2: explorer http://localhost:8000
explorer http://localhost:8000
if %ERRORLEVEL% neq 0 echo ECHEC 2: %ERRORLEVEL%
pause

echo Test 3: rundll32
rundll32 url.dll,FileProtocolHandler http://localhost:8000
if %ERRORLEVEL% neq 0 echo ECHEC 3: %ERRORLEVEL%
pause

echo Test 4: cmd /c start
cmd /c start http://localhost:8000
if %ERRORLEVEL% neq 0 echo ECHEC 4: %ERRORLEVEL%
pause
