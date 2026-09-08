# -*- mode: python ; coding: utf-8 -*-
#
# app-reportes.spec — build reproducible de la app de escritorio.
#
# MOTIVO: antes el empaquetado solo existía como un comentario en requirements
# con --onefile --add-data src;src, lo que NO incluía los motores usados por
# nombre ('xlsxwriter', 'xlrd') y copiaba código muerto. Este .spec es la única
# fuente de verdad:
#   * módulos en el PYZ (pathex al proyecto, sin copiar src como datos),
#   * hiddenimports de librerías que pandas usa por string (xlsxwriter/xlrd)
#     y de los módulos nativos de correos (Levenshtein / rapidfuzz),
#   * console=False (ventana, sin consola),
#   * icono .ico generado (src/icons/app.ico).
# Por defecto produce una CARPETA (onedir): arranca rápido y es la distribución
# más segura con antivirus corporativos. Para un único .exe:
#     set APP_REPORTES_ONEFILE=1  (o en PowerShell: $env:APP_REPORTES_ONEFILE=1)
#     pyinstaller --noconfirm --clean app-reportes.spec
import os
from PyInstaller.utils.hooks import collect_data_files

SPECPATH_ROOT = os.path.abspath(SPECPATH)  # raíz del repo (SPECPATH lo da PyInstaller)
ONEFILE = os.environ.get("APP_REPORTES_ONEFILE", "") == "1"

# MOTIVO: customtkinter carga sus temas y fuentes desde la carpeta 'assets'
# dentro del paquete; PyInstaller no los incluye por defecto, así que se
# agregan explícitamente como datos.
_CTK_DATA = collect_data_files("customtkinter")

a = Analysis(
    [os.path.join(SPECPATH_ROOT, "src", "app.py")],
    pathex=[SPECPATH_ROOT],
    binaries=[],
    datas=_CTK_DATA,
    hiddenimports=[
        # Motores de Excel usados SOLO como string (engine='...'); sin import
        # estático PyInstaller no los detecta y fallarían en runtime.
        "xlsxwriter",
        "xlrd",
        "openpyxl",
        # Recursos gráficos en memoria (PIL/ImageTk).
        "PIL.ImageTk",
        # Módulos nativos de distancia usados para validar correos.
        "Levenshtein",
        "rapidfuzz",
        "rapidfuzz.distance",
        "rapidfuzz.distance.Levenshtein",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Librerías del servidor/API que NO usa el escritorio (aligeran el .exe).
        "uvicorn", "starlette", "fastapi", "pydantic", "anyio", "watchfiles",
        "websockets", "python_multipart", "jinja2", "click", "h11", "sniffio",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=ONEFILE,
    name="app-reportes",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=os.path.join(SPECPATH_ROOT, "src", "icons", "app.ico"),
)

if ONEFILE:
    # Modo "un solo .exe": EXE ya incluye todo (sin carpeta de librerías).
    pass
else:
    # Modo "carpeta" (recomendado para instalar en varias PC): app-reportes/.
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="app-reportes",
    )
