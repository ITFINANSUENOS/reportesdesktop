import pandas as pd
from pathlib import Path
import os

class ReportWriter:
    """Formatea y guarda los DataFrames procesados en un archivo Excel con estilos."""

    COLUMN_ORDER_EFECTY = [
        'No', 'Identificación', 'Valor', 'N° de Autorización', 'Fecha', 'Documento Cartera', 
        'C. Costo', 'Empresa', 'Valor Aplicar', 'Valor Anticipos', 'Valor Aprovechamientos', 
        'Casa cobranza', 'Empleado', 'Novedad','Cuentas ARP', 'Cuentas FS','SALDOS','VALIDACION ULTIMO SALDO'
    ]
    COLUMN_ORDER_BANCOLOMBIA = [
        'No.', 'Fecha', 'Detalle 1', 'Detalle 2', 'Referencia 1', 'Referencia 2', 'Valor', 
        'Documento Cartera', 'C. Costo', 'Empresa', 'Valor Aplicar', 'Valor Anticipos', 
        'Valor Aprovechamientos', 'Casa cobranza', 'Empleado', 'Novedad', 'Cuentas ARP', 
        'Cuentas FS','SALDOS','VALIDACION ULTIMO SALDO'
    ]
    # Nuevo orden para Ecollect basado en sus columnas de entrada
    COLUMN_ORDER_ECOLLECT = [
        '#TRANS', 'REFERENCIA 1', 'FECHA INICIO', 'CANAL DE PAGO', 'Valor',
        'Documento Cartera', 'C. Costo', 'Empresa', 'Valor Aplicar', 'Valor Anticipos',
        'Valor Aprovechamientos', 'Casa cobranza', 'Empleado', 'Novedad', 'Cuentas ARP',
        'Cuentas FS', 'SALDOS', 'VALIDACION ULTIMO SALDO'
    ]

    def save_report(self, output_path: str, df_bancolombia: pd.DataFrame, df_efecty: pd.DataFrame, df_ecollect: pd.DataFrame):
        if df_bancolombia.empty and df_efecty.empty and df_ecollect.empty:
            raise ValueError("No se encontraron datos de pago para generar el reporte.")

        # Aplicar formato y reordenamiento
        df_bancolombia = self._format_and_reorder_data(df_bancolombia, 'bancolombia')
        df_efecty = self._format_and_reorder_data(df_efecty, 'efecty')
        df_ecollect = self._format_and_reorder_data(df_ecollect, 'ecollect')

        final_path = Path(output_path)
        temp_dir = final_path.parent
        temp_file_path = temp_dir / f"temp_{os.getpid()}_{final_path.name}"
        
        try:
            with pd.ExcelWriter(temp_file_path, engine='xlsxwriter') as writer:
                
                wrote_something = False
                
                # Guardar Bancolombia
                if not df_bancolombia.empty:
                    styled_bancolombia = self._apply_styles(df_bancolombia)
                    styled_bancolombia.to_excel(writer, sheet_name='Bancolombia', index=False)
                    wrote_something = True
                
                # Guardar Efecty
                if not df_efecty.empty:
                    styled_efecty = self._apply_styles(df_efecty)
                    styled_efecty.to_excel(writer, sheet_name='Efecty', index=False)
                    wrote_something = True

                # Guardar Ecollect (NUEVO)
                if not df_ecollect.empty:
                    styled_ecollect = self._apply_styles(df_ecollect)
                    styled_ecollect.to_excel(writer, sheet_name='Ecollect', index=False)
                    wrote_something = True

                if not wrote_something:
                    pd.DataFrame({'Mensaje': ['No hay datos válidos para mostrar']}).to_excel(writer, sheet_name='Diagnóstico', index=False)
            
            os.replace(temp_file_path, final_path)
            print(f"✅ Reporte con estilos guardado exitosamente usando XlsxWriter en {final_path.resolve()}")

        except Exception as e:
            raise ValueError(f"❌ Error inesperado al guardar con XlsxWriter: {e}")
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                

    def _format_and_reorder_data(self, df: pd.DataFrame, df_type: str) -> pd.DataFrame:
        """Aplica formateo y reordena columnas antes de guardar."""
        if df.empty:
            return df

        # Formato de Fecha (Genérico)
        if 'Fecha' in df.columns:
            df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce').dt.strftime('%d/%m/%Y')
        
        # Formato específico para Ecollect
        if df_type == 'ecollect':
            if 'FECHA INICIO' in df.columns:
                df['FECHA INICIO'] = pd.to_datetime(df['FECHA INICIO'], errors='coerce').dt.strftime('%d/%m/%Y')

        # Formato específico de Bancolombia
        if df_type == 'bancolombia':
            if 'Referencia 1' in df.columns:
                df['Referencia 1'] = df['Referencia 1'].apply(self._clean_reference)
            if 'Referencia 2' in df.columns:
                df['Referencia 2'] = df['Referencia 2'].apply(self._clean_reference)

        # Selección de orden de columnas
        if df_type == 'bancolombia':
            order = self.COLUMN_ORDER_BANCOLOMBIA
        elif df_type == 'efecty':
            order = self.COLUMN_ORDER_EFECTY
        elif df_type == 'ecollect':
            order = self.COLUMN_ORDER_ECOLLECT
        else:
            order = df.columns.tolist()
        
        # Asegurar que todas las columnas existan para evitar errores
        for col in order:
            if col not in df.columns:
                df[col] = None 

        return df[order]

    def _apply_styles(self, df: pd.DataFrame):
        """Aplica todos los estilos condicionales a un DataFrame."""
        styler = df.style
        # Primero se aplica el resaltado por filas
        styler = styler.apply(self._highlight_accounts, axis=1)
        # Luego se aplica el resaltado por celdas
        styler = styler.apply(self._highlight_employees_and_duplicates, axis=None)
        return styler

    def _clean_reference(self, value):
        """Limpia los valores de las columnas de referencia."""
        try:
            return str(int(float(value))) if pd.notna(value) and value != '' else ''
        except (ValueError, TypeError):
            return str(value) # Devuelve el valor original si no se puede convertir

    def _highlight_accounts(self, row):
        """Resalta filas donde un cliente tiene múltiples carteras."""
        styles = [''] * len(row)
        if 'Cuentas ARP' in row and 'Cuentas FS' in row:
            arp, fs = row['Cuentas ARP'], row['Cuentas FS']
            if (arp >= 2) or (fs >= 2) or (arp >= 1 and fs >= 1):
                styles = ['background-color: lightcoral'] * len(row)
        return styles

    def _highlight_employees_and_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Resalta filas correspondientes a empleados o duplicados."""
        # Crea un DataFrame de estilos vacío con el mismo tamaño que el de datos
        styles = pd.DataFrame('', index=df.index, columns=df.columns)
        
        # Resaltar empleados
        if 'Empleado' in df.columns:
            empleado_mask = df['Empleado'].str.upper().str.strip() == 'SI'
            styles.loc[empleado_mask, :] = 'background-color: lightblue'
            
        # Resaltar duplicados en 'Documento Cartera'
        if 'Documento Cartera' in df.columns:
            dup_mask = df.duplicated('Documento Cartera', keep=False) & (df['Documento Cartera'] != 'SIN CARTERA')
            # Pinta de amarillo solo donde la condición dup_mask es verdadera,
            # respetando los colores ya aplicados a los empleados.
            styles.loc[dup_mask, :] = styles.loc[dup_mask, :].where(styles != '', 'background-color: yellow')

        return styles