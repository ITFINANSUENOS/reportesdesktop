# src/utils/file_utils.py
# Utilidades de archivos para robustez en producción.
import shutil
from pathlib import Path


def backup_file(path: str) -> str:
    """Copia 'path' a 'path.bak' (si existe) antes de modificarlo.

    MOTIVO: varios servicios actualizan EN SITIO archivos del usuario (Excel de
    correcciones de centrales, maestro de Ecollect). Si algo falla a mitad o el
    archivo queda corrupto, con el .bak el usuario no pierde su información.
    """
    src = Path(path)
    if not src.exists():
        return ""
    backup = src.with_name(src.name + ".bak")
    try:
        shutil.copy2(str(src), str(backup))
    except Exception:
        # Si no se puede respaldar, no bloqueamos: el intento de escritura
        # posterior sí informará del fallo.
        return ""
    return str(backup)
