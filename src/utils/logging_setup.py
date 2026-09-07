# src/utils/logging_setup.py
#
# MOTIVO: al compilar con PyInstaller en modo "--windowed" no existe consola y
# `sys.stdout`/`sys.stderr` son None. Cualquier `print()` (y la app usa ~265)
# lanzaría AttributeError y, dentro de un hilo o callback, podría matarlo en
# silencio. Aquí se redirige la salida a un archivo de log en %LOCALAPPDATA%
# para que la app nunca se rompa por "no haber consola" y deje rastro en campo.
import os
import sys
import traceback
from pathlib import Path


def default_log_dir() -> Path:
    """Carpeta de logs: %LOCALAPPDATA%/app-reportes/logs (o junto al .exe si no existe)."""
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "app-reportes" / "logs"
    return Path.cwd() / "app-reportes" / "logs"


def init_logging(log_dir=None) -> Path:
    """
    Garantiza que stdout/stderr nunca sean None y deja un log persistente.

    - En modo consola (desarrollo): NO interfiere con la salida normal.
    - En modo windowed (sys.stdout es None): redirige stdout/stderr al log.
    """
    log_dir = Path(log_dir) if log_dir else default_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)

    # Hook de excepciones no capturadas: se guardan en el log (visible en campo).
    def _excepthook(exc_type, exc_value, exc_tb):
        try:
            with open(log_dir / "errores.log", "a", encoding="utf-8") as f:
                f.write("".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
        except Exception:
            pass
        if sys.__stderr__ is not None:
            traceback.print_exception(exc_type, exc_value, exc_tb)

    sys.excepthook = _excepthook

    if sys.stdout is None or sys.stderr is None:
        # Modo empaquetado sin consola: redirigimos a un archivo.
        log_file = log_dir / "run.log"
        handle = open(log_file, "a", encoding="utf-8", buffering=1)
        sys.stdout = handle
        sys.stderr = handle

    return log_dir


def log_exception_to_file(log_dir, exc: Exception) -> str:
    """Escribe una excepción al log y devuelve la ruta (para mostrarla al usuario)."""
    log_dir = Path(log_dir) if log_dir else default_log_dir()
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        with open(log_dir / "errores.log", "a", encoding="utf-8") as f:
            f.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    except Exception:
        pass
    return str(log_dir)
