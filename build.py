#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
build.py — compila la app con PyInstaller usando app-reportes.spec.

Uso:
    python build.py            # modo carpeta (dist/app-reportes/) [recomendado]
    python build.py --onefile  # un solo .exe (dist/app-reportes.exe)

MOTIVO: centraliza la build reproducible (misma config, hiddenimports e ícono
en todas las PCs/CI) en lugar de flags sueltos.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    onefile = "--onefile" in sys.argv
    if onefile:
        os.environ["APP_REPORTES_ONEFILE"] = "1"
    else:
        os.environ.pop("APP_REPORTES_ONEFILE", None)

    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "app-reportes.spec"]
    print("Ejecutando:", " ".join(cmd))
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    sys.exit(main())
