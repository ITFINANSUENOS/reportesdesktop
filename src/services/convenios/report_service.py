import os
import pandas as pd
from pathlib import Path

# Escritura con openpyxl (replica el formato final de las plantillas:
# encabezado congelado, colores, anchos, fuentes y fechas reales dd/mm/yyyy).
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

# ---------------------------------------------------------------------------
# ReportWriter - Convenios
# ---------------------------------------------------------------------------
# MOTIVO DEL CAMBIO (estructura final):
#   Las plantillas 'Bancolombia - plantilla.xlsx' y 'Efecty - plantilla - copia.xlsx'
#   definen el ORDEN y FORMATO finales de cada hoja. Este escritor:
#     * ubica cada columna en la posición de la plantilla,
#     * renombra encabezados (p. ej. 'Valor Aplicar' -> 'Vr a Aplicar'),
#     * parte el documento 'DF-14566' en 'Documento' (DF) y 'Numero' (14566),
#     * deja 'C. Costo' vacía (la hoja CARTERA ya no aporta centro de costo),
#     * conserva las columnas analíticas (Cuentas ARP/FS, SALDOS, VALIDACION)
#       AL FINAL de cada hoja,
#     * guarda fechas reales con formato dd/mm/yyyy.
#   No cambia NINGUNA regla de cálculo: solo presentación/orden.
# ---------------------------------------------------------------------------


class ReportWriter:
    """Formatea y guarda los DataFrames procesados con la estructura final."""

    # --- Especificación de columnas por canal: (encabezado, columna_fuente) ---
    # columna_fuente = None  -> columna vacía
    # columna_fuente = 'DOC_TIPO'/'DOC_NUM' -> documento partido
    # 'Fecha' -> se guarda como fecha real dd/mm/yyyy
    SPEC_BANCOLOMBIA = [
        ('No', 'No.'),                     # número original del pago
        ('Identificación', 'Referencia 1'),  # la plantilla muestra la referencia como identificación
        ('Valor', 'Valor'),
        ('Ref 2', 'Referencia 2'),
        ('Fecha', 'Fecha'),
        ('Documento', 'DOC_TIPO'),          # tipo del documento (p. ej. 'DF')
        ('Numero', 'DOC_NUM'),              # número del documento (p. ej. 14566)
        ('C, Costo', None),                 # vacío: la fuente ya no trae centro de costo
        ('Empresa', 'Empresa'),
        ('Vr a Aplicar', 'Valor Aplicar'),
        ('Detalle 1', 'Detalle 1'),
        ('Detalle 2', 'Detalle 2'),
        ('Valor Anticipos', 'Valor Anticipos'),
        ('Valor Aprovechamientos', 'Valor Aprovechamientos'),
        ('Casa cobranza', 'Casa cobranza'),
        ('Empleado', 'Empleado'),
        ('Novedad', 'Novedad'),
        ('Ref 1', 'Referencia 1'),
        (',', None),                        # columna de la plantilla (se mantiene vacía)
    ]

    SPEC_EFECTY = [
        ('No', 'No'),
        ('Identificación', 'Identificación'),
        ('Valor', 'Valor'),
        ('N° de Autorización', 'N° de Autorización'),
        ('Fecha', 'Fecha'),
        ('Documento Cartera', 'DOC_TIPO'),
        ('Numero', 'DOC_NUM'),
        ('C. Costo', None),
        ('Empresa', 'Empresa'),
        ('Vr a Aplicar', 'Valor Aplicar'),
        ('Valor Anticipos', 'Valor Anticipos'),
        ('Valor Aprovechamientos', 'Valor Aprovechamientos'),
        ('Casa cobranza', 'Casa cobranza'),
        ('Empleado', 'Empleado'),
        ('Novedad', 'Novedad'),
    ]

    # Columnas analíticas que la plantilla no trae pero se conservan al final.
    ANALYTIC_COLUMNS = ['Cuentas ARP', 'Cuentas FS', 'SALDOS', 'VALIDACION ULTIMO SALDO']

    # --- Anchos de columna tomados de las plantillas ---
    WIDTH_BANCOLOMBIA = {
        'No': 4.6, 'Identificación': 14.0, 'Valor': 15.9, 'Ref 2': 12.4,
        'Fecha': 13.3, 'Documento': 14.3, 'Numero': 11.1, 'C, Costo': 14.7,
        'Empresa': 14.6, 'Vr a Aplicar': 12.4, 'Detalle 1': 32.9, 'Detalle 2': 14.0,
        'Valor Anticipos': 15.4, 'Valor Aprovechamientos': 23.4, 'Casa cobranza': 14.9,
        'Empleado': 11.1, 'Novedad': 36.0, 'Ref 1': 14.0, ',': 6.6,
    }
    WIDTH_EFECTY = {
        'No': 4.1, 'Identificación': 13.9, 'Valor': 15.3, 'N° de Autorización': 13.3,
        'Fecha': 13.3, 'Documento Cartera': 15.3, 'Numero': 15.3, 'C. Costo': 9.7,
        'Empresa': 15.3, 'Vr a Aplicar': 13.9, 'Valor Anticipos': 14.3,
        'Valor Aprovechamientos': 17.9, 'Casa cobranza': 17.9, 'Empleado': 11.4,
        'Novedad': 31.3,
    }

    # --- Estilos (replicando las plantillas) ---
    FONT_HEADER = Font(name='Maiandra GD', size=10, bold=True)
    FONT_DATA = Font(name='Maiandra GD', size=10)
    FILL_GREEN = PatternFill(start_color='FF92D050', end_color='FF92D050', fill_type='solid')
    FILL_ORANGE = PatternFill(start_color='FFFFC000', end_color='FFFFC000', fill_type='solid')
    ALIGN_HEADER = Alignment(horizontal='center', vertical='center', wrap_text=True)
    THIN = Side(style='thin', color='FF000000')
    BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

    # --- Resaltado de filas (se restaura el comportamiento previo del reporte) ---
    # MOTIVO: el escritor anterior coloreaba filas para alertar visualmente:
    #   rojo  -> cliente con más de una cartera,
    #   azul  -> empleado (Empleado = SI),
    #   amarillo -> documento duplicado.
    # Se puede desactivar con una sola constante si se quiere un Excel limpio.
    RESALTAR_COLORES = True
    FILL_LIGHT_RED = PatternFill(start_color='FFF08080', end_color='FFF08080', fill_type='solid')
    FILL_LIGHT_BLUE = PatternFill(start_color='FFADD8E6', end_color='FFADD8E6', fill_type='solid')
    FILL_YELLOW = PatternFill(start_color='FFFFFF00', end_color='FFFFFF00', fill_type='solid')

    ORANGE_HEADERS = {'Documento', 'Numero', 'Documento Cartera'}

    def save_report(self, output_path: str, df_bancolombia: pd.DataFrame, df_efecty: pd.DataFrame,
                    df_ecollect: pd.DataFrame):
        """Guarda un único Excel con una hoja por canal (estructura de plantilla)."""
        if df_bancolombia.empty and df_efecty.empty and df_ecollect.empty:
            raise ValueError("No se encontraron datos de pago para generar el reporte.")

        final_path = Path(output_path)
        temp_path = final_path.parent / f"temp_{os.getpid()}_{final_path.name}"

        wb = Workbook()
        if wb.active is not None:
            wb.remove(wb.active)  # quitar hoja por defecto

        wrote_something = False
        for sheet_name, df in (("Bancolombia", df_bancolombia),
                               ("Efecty", df_efecty),
                               ("Ecollect", df_ecollect)):
            if df.empty:
                # MOTIVO: hoy se omiten los canales sin datos (comportamiento previo).
                continue
            self._write_sheet(wb, sheet_name, df)
            wrote_something = True

        if not wrote_something:
            raise ValueError("No se encontraron datos de pago para generar el reporte.")

        wb.save(temp_path)
        try:
            os.replace(temp_path, final_path)
        except PermissionError:
            # MOTIVO (robustez): en Windows no se puede sobrescribir un archivo
            # abierto en Excel. Se avisa claro para que el usuario lo cierre.
            raise ValueError(
                f"No se pudo guardar el reporte porque '{final_path.name}' está abierto. "
                "Ciérralo en Excel e inténtalo de nuevo.")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        print(f"Reporte con estilos guardado correctamente (formato plantilla): {final_path.resolve()}")

    # ------------------------------------------------------------- internos
    def _write_sheet(self, workbook, sheet_name: str, df: pd.DataFrame):
        """Escribe una hoja con el orden/formato de la plantilla correspondiente."""
        spec = self.SPEC_BANCOLOMBIA if sheet_name == 'Bancolombia' else (
            self.SPEC_EFECTY if sheet_name == 'Efecty' else None)

        if spec is None:
            # Ecollect aún no tiene plantilla: se mantiene el DataFrame tal cual.
            spec = [(col, col) for col in df.columns]

        # (1) Reordenar/re-mapear columnas al orden objetivo (+ analíticas al final).
        out = self._build_ordered_frame(df, spec)

        ws = workbook.create_sheet(title=sheet_name)

        # (2) Encabezado
        for col_idx, header in enumerate(out.columns, start=1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = self.FONT_HEADER
            cell.alignment = self.ALIGN_HEADER
            cell.border = self.BORDER
            cell.fill = self.FILL_ORANGE if header in self.ORANGE_HEADERS else self.FILL_GREEN
            width_map = self.WIDTH_BANCOLOMBIA if sheet_name == 'Bancolombia' else (
                self.WIDTH_EFECTY if sheet_name == 'Efecty' else {})
            ws.column_dimensions[cell.column_letter].width = width_map.get(header, 14.0)

        # (3) Datos (con fuente de plantilla, bordes y fechas dd/mm/yyyy)
        row_fills = self._compute_row_fills(out) if self.RESALTAR_COLORES else None
        is_date_col = {c: (h == 'Fecha') for c, h in enumerate(out.columns)}
        for seq, values in enumerate(out.itertuples(index=False, name=None)):
            row_idx = seq + 2
            fill = row_fills[seq] if row_fills else None
            for col_idx, value in enumerate(values, start=1):
                cell = ws.cell(row=row_idx, column=col_idx)
                if value is None or (isinstance(value, float) and pd.isna(value)):
                    value = None
                cell.value = value
                cell.font = self.FONT_DATA
                cell.border = self.BORDER
                if fill is not None:
                    cell.fill = fill
                if is_date_col[col_idx - 1] and value is not None:
                    cell.number_format = 'DD/MM/YYYY'

        ws.freeze_panes = 'A2'

    def _compute_row_fills(self, out: pd.DataFrame):
        """Decide el color de cada fila de datos (mismas reglas que el reporte viejo).

        Devuelve una lista alineada con las filas de 'out' (None = sin color).
        """
        n = len(out)
        fills = [None] * n
        if n == 0:
            return fills

        def has(col):
            return col in out.columns

        # Rojo: cliente con más de una cartera (ARP o FS con 2+ cuentas, o en ambas).
        multi = None
        if has('Cuentas ARP') and has('Cuentas FS'):
            arp = pd.to_numeric(out['Cuentas ARP'], errors='coerce').fillna(0)
            fs = pd.to_numeric(out['Cuentas FS'], errors='coerce').fillna(0)
            multi = (arp >= 2) | (fs >= 2) | ((arp >= 1) & (fs >= 1))

        # Azul: fila de empleado.
        empleado = None
        if has('Empleado'):
            empleado = out['Empleado'].astype(str).str.upper().str.strip() == 'SI'

        # Amarillo: documento duplicado (el documento ahora va partido en
        # 'Documento' + 'Numero'; se reconstruye la llave para detectarlo igual).
        dup = None
        key = None
        if has('Documento Cartera'):
            key = out['Documento Cartera'].astype(str).str.strip()
        elif has('Documento') and has('Numero'):
            key = (out['Documento'].astype(str) + '-' + out['Numero'].astype(str)).str.strip()
        if key is not None:
            valido = key.notna() & (key != '') & (key != '-') & (key.str.upper() != 'NAN')
            dup = key.duplicated(keep=False) & valido

        for i in range(n):
            if multi is not None and bool(multi.iloc[i]):
                fills[i] = self.FILL_LIGHT_RED
            elif empleado is not None and bool(empleado.iloc[i]):
                fills[i] = self.FILL_LIGHT_BLUE
            elif dup is not None and bool(dup.iloc[i]):
                fills[i] = self.FILL_YELLOW
        return fills

    def _build_ordered_frame(self, df: pd.DataFrame, spec) -> pd.DataFrame:
        """Construye el DataFrame final en el orden exacto de la plantilla."""
        doc_series = df['Documento Cartera'] if 'Documento Cartera' in df.columns else None

        ordered = {}
        for header, source in spec:
            if source is None:
                ordered[header] = None
            elif source == 'DOC_TIPO':
                ordered[header] = doc_series.map(self._doc_tipo) if doc_series is not None else None
            elif source == 'DOC_NUM':
                ordered[header] = doc_series.map(self._doc_numero) if doc_series is not None else None
            elif source == 'Fecha' and 'Fecha' in df.columns:
                ordered[header] = self._coerce_date(df['Fecha'])
            else:
                ordered[header] = df[source] if source in df.columns else None

        out = pd.DataFrame(ordered)

        # Columnas analíticas al final (si existen en el resultado procesado).
        for col in self.ANALYTIC_COLUMNS:
            if col in df.columns:
                out[col] = df[col].values

        return out

    @staticmethod
    def _coerce_date(series) -> pd.Series:
        """Convierte fechas a datetime real.

        MOTIVO: las fechas del archivo vienen en formato DD/MM/AAAA (colombiano)
        pero a veces como texto y a veces ya como fecha de Excel. Se fuerza el
        formato día-primero para evitar que '15/06/2026' se lea como 06/15/2026.
        """
        if pd.api.types.is_datetime64_any_dtype(series):
            return pd.to_datetime(series, errors='coerce')
        converted = pd.to_datetime(series, format='%d/%m/%Y', errors='coerce')
        # Si alguna no coincide con el formato, se intenta el parseo genérico.
        if converted.isna().any():
            fallback = pd.to_datetime(series, errors='coerce')
            return converted.fillna(fallback)
        return converted

    @staticmethod
    def _doc_tipo(value):
        """Extrae el tipo del documento: 'DF-14566' -> 'DF'."""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        s = str(value).strip()
        return s.split('-', 1)[0] if '-' in s else ''

    @staticmethod
    def _doc_numero(value):
        """Extrae el número del documento: 'DF-14566' -> 14566."""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        s = str(value).strip()
        if '-' not in s:
            return ''
        numero = s.split('-', 1)[1]
        return int(numero) if numero.isdigit() else numero
