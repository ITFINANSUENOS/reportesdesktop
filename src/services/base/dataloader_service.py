from pathlib import Path
import pandas as pd

class DataLoaderService:
    """Servicio encargado de cargar y preparar los dataframes iniciales"""
    def __init__(self, config):
        self.config = config

    def load_dataframes(self, file_paths):
        """Lee todos los archivos de Excel y los convierte en DataFrames según la configuración."""
        dataframes_por_tipo = {key: [] for key in self.config.keys()}
        print("--- 🔄 Iniciando lectura de archivos ---")
        for ruta_archivo in file_paths:
            try:
                nombre_archivo = Path(ruta_archivo).name
                tipo_archivo_actual = self._get_file_type(nombre_archivo)
                
                if not tipo_archivo_actual:
                    print(f"⚠️  Archivo '{nombre_archivo}' omitido.")
                    continue

                config_actual = self.config[tipo_archivo_actual]
                
                if "sheets" in config_actual:
                    xls = pd.ExcelFile(ruta_archivo, engine='openpyxl')
                    for sheet_config in config_actual["sheets"]:
                        if sheet_config["sheet_name"] in xls.sheet_names:
                            try:
                                # MOTIVO (rendimiento): leer SOLO las columnas del
                                # config evita parsear todo el archivo.
                                df_hoja = pd.read_excel(xls, sheet_name=sheet_config["sheet_name"],
                                                        usecols=sheet_config["usecols"])
                            except ValueError:
                                # Columna config ausente en el Excel: lectura tolerante
                                # (mismo comportamiento que antes: se filtra luego).
                                df_hoja = pd.read_excel(xls, sheet_name=sheet_config["sheet_name"])
                            df_hoja.columns = df_hoja.columns.str.strip()
                            columnas_a_usar = [col for col in sheet_config["usecols"] if col in df_hoja.columns]
                            df_filtrado = df_hoja[columnas_a_usar].rename(columns=sheet_config["rename_map"])
                            dataframes_por_tipo[tipo_archivo_actual].append({"data": df_filtrado, "config": sheet_config})
                elif "new_names" in config_actual:
                    df = pd.read_excel(ruta_archivo, header=config_actual.get("header"), skiprows=config_actual.get("skiprows"), names=config_actual.get("new_names"))
                    dataframes_por_tipo[tipo_archivo_actual].append(df)
                else:
                    engine = 'xlrd' if ruta_archivo.upper().endswith('.XLS') else 'openpyxl'
                    try:
                        # MOTIVO (rendimiento): pasar usecols reduce memoria/tiempo.
                        df = pd.read_excel(ruta_archivo, engine=engine, usecols=config_actual["usecols"])
                    except ValueError:
                        df = pd.read_excel(ruta_archivo, engine=engine)
                    df.columns = df.columns.str.strip()
                    columnas_a_usar = [col for col in config_actual["usecols"] if col in df.columns]
                    df_filtrado = df[columnas_a_usar]
                    if tipo_archivo_actual == "R03":
                        df_filtrado = df_filtrado.replace('.', 'SIN CODEUDOR').fillna('SIN CODEUDOR')
                    df_renombrado = df_filtrado.rename(columns=config_actual["rename_map"])
                    dataframes_por_tipo[tipo_archivo_actual].append(df_renombrado)
                
                print(f"✅ Archivo '{nombre_archivo}' procesado como tipo '{tipo_archivo_actual}'.")
            except Exception as e:
                print(f"❌ Error procesando el archivo '{ruta_archivo}': {e}")
        
        return dataframes_por_tipo

    def _get_file_type(self, filename):
        """Determina el tipo de archivo usando múltiples estrategias para máxima robustez."""
        nombre_base = filename.split('.')[0].upper().replace(" ", "_")
        sorted_keys = sorted(self.config.keys(), key=len, reverse=True)

        for tipo in sorted_keys:
            clave_config = tipo.upper().replace(" ", "_")
            if nombre_base.startswith(clave_config):
                return tipo
            
            palabras_en_nombre = set(nombre_base.split('_'))
            palabras_en_clave = set(clave_config.split('_'))
            if palabras_en_clave.issubset(palabras_en_nombre):
                return tipo
        
        return None

    def create_credit_key(self, df):
        """Crea una llave 'Credito' robusta, limpiando espacios y estandarizando tipos."""
        if df.empty or not all(col in df.columns for col in ['Numero_Credito', 'Tipo_Credito']):
            return df
            
        df['Tipo_Credito'] = df['Tipo_Credito'].astype(str).str.strip().str.upper()
        df['Numero_Credito'] = pd.to_numeric(df['Numero_Credito'], errors='coerce').astype('Int64')
        df['Credito'] = df['Tipo_Credito'] + '-' + df['Numero_Credito'].astype(str).str.replace('<NA>', '', regex=False)
        return df

    def safe_concat(self, items):
        """Concatena dataframes de forma segura"""
        if not items: return pd.DataFrame()
        df_list = [item["data"] if isinstance(item, dict) else item for item in items]
        return pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()