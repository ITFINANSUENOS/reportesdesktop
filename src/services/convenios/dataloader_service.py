import pandas as pd
from typing import Dict
from src.models.convenios_model import ConveniosConfig

class DataLoader:
    """Se encarga de cargar, validar y preparar los datos desde el archivo Excel."""

    def __init__(self, config: ConveniosConfig):
        self.config = config

    def validate_input_file(self, file_path: str) -> bool:
        """Valida que el archivo Excel contenga todas las hojas requeridas."""
        try:
            with pd.ExcelFile(file_path) as xls:
                sheets = xls.sheet_names
                missing_sheets = [s for s in self.config.required_sheets if s not in sheets]
                if missing_sheets:
                    raise ValueError(f"Faltan hojas requeridas: {', '.join(missing_sheets)}")
            return True
        except Exception as e:
            raise ValueError(f"Error al validar archivo: {e}")

    def load_and_filter_data(self, file_path: str) -> Dict[str, pd.DataFrame]:
        """Carga y filtra los datos del archivo Excel según la configuración."""
        try:
            self.validate_input_file(file_path)
            dfs = pd.read_excel(file_path, sheet_name=None)
            filtered_data = {}
            for sheet_name, columns in self.config.sheet_columns.items():
                if sheet_name not in dfs:
                    raise ValueError(f"Hoja '{sheet_name}' no encontrada.")
                
                df = dfs[sheet_name][columns].copy()
                if sheet_name in self.config.rename_columns:
                    df.rename(columns=self.config.rename_columns[sheet_name], inplace=True)
                filtered_data[sheet_name] = df
            return filtered_data
        except Exception as e:
            raise ValueError(f"Error al cargar datos: {e}")

    def prepare_data(self, dfs: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Pre-procesa los DataFrames, convirtiendo columnas clave a string."""
        string_columns = {
            'PAGOS BANCOLOMBIA': ['Referencia 1', 'Referencia 2'], 
            'PAGOS EFECTY': ['Identificación'],
            'PAGOS ECOLLECT': ['REFERENCIA 1'],
            'EMPLEADOS ACTUALES': ['vincedula'],
            'AC FS': ['CEDULA_FS', 'FACTURA_FS'],
            'AC ARP': ['CEDULA_ARP', 'FACTURA_ARP'], 
            'CASA DE COBRANZA': ['FACTURA'],
            'CODEUDORES': ['DOCUMENTO_CODEUDOR']
        }
        for sheet, cols in string_columns.items():
            if sheet in dfs:
                for col in cols:
                    if col in dfs[sheet].columns:
                        dfs[sheet][col] = dfs[sheet][col].astype(str)
        return dfs