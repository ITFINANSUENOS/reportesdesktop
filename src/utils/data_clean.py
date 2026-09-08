# src/utils/data_clean.py
#
# Limpieza de LLAVES de cruce (cédulas, documentos, referencias).
#
# MOTIVO (bug de datos real): cuando un Excel guarda identificaciones como
# números (p. ej. 1010), pandas las lee como float y "1010".astype(str) da
# "1010.0". Eso NO casa contra el mismo valor leído como int ("1010"), y todos
# los cruces por cédula/documento fallan EN SILENCIO (todo queda SIN CARTERA).
# Esta utilidad normaliza la llave: los flotantes enteros pierden el ".0".
import pandas as pd


def clean_key(value) -> str:
    """Convierte un valor a cadena 'llave', normalizando numéricos enteros."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        if float(value).is_integer():
            return str(int(value))
        return str(value)
    return str(value).strip()


def clean_key_series(series: pd.Series) -> pd.Series:
    """Aplica clean_key a toda una Serie."""
    return series.map(clean_key)
