#!/usr/bin/env python3
"""Interactive secret installation (no shell history / terminal echo / Git writes)."""
import getpass, os, stat, sys
from pathlib import Path

TARGET=Path.home()/'.config'/'cardyssey'/'capsolver.key'

def main():
    if not sys.stdin.isatty():
        print('Bitte interaktiv im Ubuntu-Terminal ausführen (keine Pipe).')
        return 2
    TARGET.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    TARGET.parent.chmod(0o700)
    print('CapSolver-Schlüssel eingeben (wird nicht angezeigt und nicht im Terminalverlauf gespeichert).')
    key=getpass.getpass('CapSolver API-Key: ').strip()
    if not key.startswith('CAP-') or len(key)<30 or not key.isascii() or any(ch.isspace() for ch in key):
        print('Ungültiges Schlüsselformat. Nichts gespeichert.')
        return 1
    fd=os.open(TARGET,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,'w',encoding='utf-8') as stream:
            stream.write(key+'\n')
    finally:
        pass
    key='' # never print key
    print('Schlüssel sicher gespeichert (Dateirechte 600).')
    import importlib.util
    source=Path(__file__).with_name('capsolver_preflight.py')
    spec=importlib.util.spec_from_file_location('capsolver_preflight',source)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    status=module.preflight()
    print('API-Status:',status['status'])
    if 'balanceUsd' in status:
        print('Verfügbares Guthaben (USD):',status['balanceUsd'])
    if 'errorCode' in status and status['errorCode']:
        print('API-Fehlercode:',status['errorCode'])
    print('Proxy eingerichtet:', 'Ja' if status['staticProxyConfigured'] else 'Nein')
    print('Es wurde keine Challenge gestartet und kein Guthaben verbraucht.')
    return 0 if status['status']=='API_ACCEPTED' else 1

if __name__=='__main__':
    raise SystemExit(main())
