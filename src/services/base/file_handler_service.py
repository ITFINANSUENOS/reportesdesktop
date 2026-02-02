import pandas as pd
from typing import Dict, Optional

class FileHandlerService:
    """
    Servicio dedicado a la lectura y escritura de archivos,
    especialmente formatos como Excel.
    """

    def read_excel_base(self, file_path: str) -> Optional[pd.DataFrame]:
        """
        Lee un archivo Excel y lo devuelve como un DataFrame de pandas.
        Maneja posibles errores durante la lectura.
        """
        try:
            print(f"📖 Leyendo archivo base desde: {file_path}")
            return pd.read_excel(file_path, dtype=str)
        except Exception as e:
            print(f"Error al leer el archivo Excel base: {e}")
            raise ValueError(f"No se pudo leer el archivo Excel base: {e}")

    def _apply_styles(self, val: str) -> str:
        """Aplica estilos de fondo a las celdas según su valor."""
        if val == 'CORREGIR':
            return 'background-color: #FFCDD2'  # Rojo claro
        if val == 'BIEN':
            return 'background-color: #C8E6C9'  # Verde claro
        return 'background-color: #FFFFFF'      # Blanco

    def save_report_to_excel(self, output_path: str, reports: Dict[str, pd.DataFrame]):
        """
        Guarda múltiples DataFrames en un único archivo Excel, cada uno en una hoja.
        """
        print(f"💾 Guardando reporte en {output_path}...")
        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Guardar el reporte principal
                main_report = reports.get('reporte_final')
                if main_report is not None and not main_report.empty:
                    main_report.to_excel(writer, sheet_name='Reporte Consolidado', index=False)
                    print("  - Hoja 'Reporte Consolidado' guardada.")

                # Guardar créditos negativos si existen
                negative_report = reports.get('reporte_negativos')
                if negative_report is not None and not negative_report.empty:
                    negative_report.to_excel(writer, sheet_name='Creditos_Negativos', index=False)
                    print("  - Hoja 'Creditos_Negativos' añadida.")

                # Guardar registros para corregir con estilos si existen
                corrections_report = reports.get('reporte_correcciones')
                if corrections_report is not None and not corrections_report.empty:
                    print("  - 🎨 Aplicando estilos a la hoja de correcciones...")
                    
                    # --- CORRECCIÓN DE COMPATIBILIDAD PANDAS ---
                    styler = corrections_report.style
                    
                    # Intentamos usar .map (Pandas nuevo), si falla usamos .applymap (Pandas viejo)
                    if hasattr(styler, "map"):
                         styled_df = styler.map(self._apply_styles)
                    else:
                         styled_df = styler.applymap(self._apply_styles)
                    
                    styled_df.to_excel(writer, sheet_name='Registros_Para_Corregir', index=False)
                    print("  - ✅ Hoja 'Registros_Para_Corregir' añadida con colores.")
        except Exception as e:
            print(f"Error al guardar el archivo Excel: {e}")
            # Importante: Imprimimos el tipo de error para debug
            import traceback
            traceback.print_exc()
            raise IOError(f"No se pudo guardar el archivo Excel: {e}")