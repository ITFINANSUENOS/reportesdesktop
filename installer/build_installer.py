#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
installer/build_installer.py — compila el instalador con Inno Setup.

Uso:
    python installer/build_installer.py            # usa la build ya existente en dist\\
    python installer/build_installer.py --rebuild  # recompila primero con PyInstaller

MOTIVO: unificar en un solo comando: (1) generar el .exe autocontenido y
(2) empaquetarlo en un instalador con accesos directos y desinstalador.
Resultado: dist\\instalador\\ReportesFinancieros-setup-1.0.0.exe
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = Path(__file__).resolve().parent
ISCC_CANDIDATES = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
    Path("C:/Program Files (x86)/Inno Setup 6/ISCC.exe"),
]


def find_iscc():
    for candidate in ISCC_CANDIDATES:
        if candidate.exists():
            return str(candidate)
    return None


def main():
    if "--rebuild" in sys.argv:
        print("Recompilando el .exe con PyInstaller...")
        code = subprocess.call([sys.executable, "build.py"], cwd=str(ROOT))
        if code != 0:
            return code

    iscc = find_iscc()
    if not iscc:
        print("No se encontró ISCC.exe. Instala Inno Setup: winget install JRSoftware.InnoSetup")
        return 1

    iss_file = SCRIPT_DIR / "app-reportes.iss"
    print("Compilando instalador con Inno Setup...")
    return subprocess.call([iscc, str(iss_file)], cwd=str(SCRIPT_DIR))


if __name__ == "__main__":
    sys.exit(main())
