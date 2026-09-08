import pandas as pd
from typing import Dict
from src.models.convenios_model import ConveniosConfig
# MOTIVO (bug de cruces): normaliza llaves numéricas ("1010.0" -> "1010").
from src.utils.data_clean import clean_key_series

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
        """Carga y filtra los datos del archivo Excel según la configuración.

        MOTIVO DEL CAMBIO: ya no se leen las hojas 'AC FS'/'AC ARP'. En su lugar
        se lee la hoja única 'CARTERA' y aquí se divide por empresa según el
        prefijo 'DF' (Finansueños) o no (Arpesod), entregando a los procesadores
        los mismos conjuntos internos 'AC FS' y 'AC ARP' de siempre.
        """
        try:
            self.validate_input_file(file_path)
            dfs = pd.read_excel(file_path, sheet_name=None)
            filtered_data = {}

            # Hojas auxiliares con config idéntica a la anterior.
            for sheet_name, columns in self.config.sheet_columns.items():
                if sheet_name not in dfs:
                    raise ValueError(f"Hoja '{sheet_name}' no encontrada.")

                df = dfs[sheet_name][columns].copy()
                if sheet_name in self.config.rename_columns:
                    df.rename(columns=self.config.rename_columns[sheet_name], inplace=True)
                filtered_data[sheet_name] = df

            # --- Hoja única de cartera (CARTERA) ---
            ac = self.config.ac_sheet_name
            if ac not in dfs:
                raise ValueError(f"Hoja '{ac}' no encontrada.")

            df_cartera = dfs[ac][list(self.config.ac_columns.keys())].copy()
            df_cartera.rename(columns=self.config.ac_columns, inplace=True)  # -> CEDULA/FACTURA/saldofac

            # Limpieza defensiva: solo registros con documento no vacío y sin
            # duplicados exactos (cédula + documento), para no alterar conteos.
            # Las llaves se normalizan ("1010.0" -> "1010") para que casen con
            # las referencias de los pagos.
            df_cartera['CEDULA'] = clean_key_series(df_cartera['CEDULA'])
            df_cartera['FACTURA'] = clean_key_series(df_cartera['FACTURA'])
            df_cartera = df_cartera[df_cartera['FACTURA'].notna() & (df_cartera['FACTURA'] != '') & (df_cartera['FACTURA'] != 'nan')]
            df_cartera = df_cartera.drop_duplicates(subset=['CEDULA', 'FACTURA'])

            # Separación por empresa (prefijo del documento).
            es_finansuenos = df_cartera['FACTURA'].str.startswith(self.config.ac_fs_prefix, na=False)
            df_fs = df_cartera[es_finansuenos].rename(columns=self.config.ac_fs_suffix_map)
            df_arp = df_cartera[~es_finansuenos].rename(columns=self.config.ac_arp_suffix_map)

            filtered_data['AC FS'] = df_fs   # Finansueños (prefijo DF)
            filtered_data['AC ARP'] = df_arp  # Arpesod (resto)

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
                        # MOTIVO (cruce): normalizar evita que "1010.0" no case con "1010".
                        dfs[sheet][col] = clean_key_series(dfs[sheet][col])
        return dfs
