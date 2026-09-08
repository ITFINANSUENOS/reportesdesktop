import pandas as pd
from typing import Dict
from src.models.anticipos_model import AnticiposConfig
# MOTIVO (bug de cruces): normaliza llaves numéricas ("1010.0" -> "1010").
from src.utils.data_clean import clean_key_series

class AnticiposDataLoader:
    """Se encarga de cargar, validar y preparar los datos desde el archivo Excel."""

    def __init__(self, config: AnticiposConfig):
        self.config = config

    def load_and_filter_data(self, file_path: str) -> Dict[str, pd.DataFrame]:
        """Carga, valida y filtra los datos del archivo Excel según la configuración.

        MOTIVO DEL CAMBIO: las hojas 'AC FS'/'AC ARP' se reemplazaron por la hoja
        única 'CARTERA'. Aquí se divide por empresa según el prefijo 'DF' del
        documento (DF = Finansueños = 'AC FS'; resto = Arpesod = 'AC ARP') y se
        entregan a los procesadores los mismos conjuntos internos de siempre.
        """
        try:
            self._validate_input_file(file_path)
            dfs = pd.read_excel(file_path, sheet_name=None)

            filtered_data = {}
            for sheet_name, columns in self.config.sheet_columns.items():
                if sheet_name not in dfs:
                    raise ValueError(f"Hoja '{sheet_name}' no encontrada en el archivo.\n")

                df = dfs[sheet_name][columns].copy()
                if sheet_name in self.config.rename_columns:
                    df.rename(columns=self.config.rename_columns[sheet_name], inplace=True)
                filtered_data[sheet_name] = df

            # --- Hoja única de cartera (CARTERA) ---
            ac = self.config.ac_sheet_name
            if ac not in dfs:
                raise ValueError(f"Hoja '{ac}' no encontrada en el archivo.\n")

            df_cartera = dfs[ac][list(self.config.ac_columns.keys())].copy()
            df_cartera.rename(columns=self.config.ac_columns, inplace=True)  # -> CEDULA/FACTURA/saldofac

            # Limpieza defensiva (documentos vacíos y duplicados exactos).
            # Las llaves se normalizan ("1010.0" -> "1010") para que casen con ONLINE.
            df_cartera['CEDULA'] = clean_key_series(df_cartera['CEDULA'])
            df_cartera['FACTURA'] = clean_key_series(df_cartera['FACTURA'])
            df_cartera = df_cartera[df_cartera['FACTURA'].notna() & (df_cartera['FACTURA'] != '') & (df_cartera['FACTURA'] != 'nan')]
            df_cartera = df_cartera.drop_duplicates(subset=['CEDULA', 'FACTURA'])

            es_finansuenos = df_cartera['FACTURA'].str.startswith(self.config.ac_fs_prefix, na=False)
            df_fs = df_cartera[es_finansuenos].rename(columns=self.config.ac_fs_suffix_map)
            df_arp = df_cartera[~es_finansuenos].rename(columns=self.config.ac_arp_suffix_map)

            filtered_data['AC FS'] = df_fs    # Finansueños (prefijo DF)
            filtered_data['AC ARP'] = df_arp  # Arpesod (resto)

            return filtered_data
        except Exception as e:
            raise ValueError(f"Error al cargar datos:\n {e}")

    def _validate_input_file(self, file_path: str) -> bool:
        """Valida que el archivo Excel contenga todas las hojas requeridas."""
        try:
            with pd.ExcelFile(file_path) as xls:
                sheets = xls.sheet_names
                missing_sheets = [s for s in self.config.required_sheets if s not in sheets]
                if missing_sheets:
                    raise ValueError(f"Faltan hojas requeridas: \n {', '.join(missing_sheets)}")
            return True
        except Exception as e:
            raise ValueError(f"Error al validar el archivo: \n {e}")
