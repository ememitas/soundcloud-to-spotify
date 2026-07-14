@echo off
setlocal
title SoundCloud -> Spotify (Local Files)

for /f "tokens=2,*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USERPATH=%%B"
set "PATH=%PATH%;%USERPATH%"

echo Add a song to Spotify (Local Files)
echo Type a song name, or paste a SoundCloud link.
echo.

if "%~1"=="" (
    set /p "SONG=Song: "
) else (
    set "SONG=%~1"
)

echo.
python "%~dp0sc2spotify.py" "%SONG%"
echo.
pause
