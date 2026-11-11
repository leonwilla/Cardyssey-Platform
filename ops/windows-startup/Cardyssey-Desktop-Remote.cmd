@echo off
REM Wake Ubuntu and start the supervised remote connection. Service handles reconnects.
start "" /min wsl.exe -d Ubuntu --exec /usr/bin/systemctl --user start cardyssey-desktop-remote.service
