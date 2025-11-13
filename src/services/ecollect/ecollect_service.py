import pandas as pd
from typing import List, Dict, Optional

class EcollectService:
    """
    Contiene toda la lógica de negocio para procesar los archivos de Ecollect.
    """

    def __init__(self, config: Dict):
        """
        Inicializa el servicio con la configuración necesaria.
        
        Args:
            config (Dict): El diccionario de configuración del modelo.
        """
        self.config = config.get("VENCIMIENTOS", {})
        if not self.config:
            raise ValueError("La configuración para 'VENCIMIENTOS' no fue encontrada.")

    def _load_and_prepare_file(self, file_path: str) -> Optional[pd.DataFrame]:
        """Carga y prepara un archivo Excel según la configuración."""
        try:
            df = pd.read_excel(
                file_path,
                usecols=self.config.get("usecols"),
                dtype={'MCNVINCULA': str, 'MCNNUMCRU1': str}
            )
            df.rename(columns=self.config.get("rename_map", {}), inplace=True)
            return df
        except FileNotFoundError:
            print(f"Error: El archivo no fue encontrado en la ruta {file_path}")
            return None
        except Exception as e:
            print(f"Ocurrió un error al leer el archivo: {e}")
            return None

    def process_vencimientos(self, file_paths: List[str]) -> Optional[pd.DataFrame]:
        """
        Orquesta el proceso de transformación para múltiples archivos de vencimientos.
        
        NUEVA LÓGICA:
        1. Procesa todos los clientes con cuotas vencidas o del mes actual (agrupando).
        2. Identifica clientes "anticipados" (sin cuotas en #1).
        3. Para los clientes anticipados, busca su *próxima* cuota futura y la reporta.
        """
        # --- Cargar y combinar todos los archivos en un solo DataFrame ---
        all_dfs = []
        for path in file_paths:
            df_temp = self._load_and_prepare_file(path)
            if df_temp is not None:
                all_dfs.append(df_temp)
        
        if not all_dfs:
            print("No se pudo cargar ningún archivo correctamente.")
            return None
            
        df = pd.concat(all_dfs, ignore_index=True)

        # --- 1. Crear columna 'Credito' ---
        df["Credito"] = df["Tipo_Credito"].astype(str) + "-" + df["Numero_Credito"].astype(str)

        # --- 2. Limpiar la columna 'Cuota_Vigente' ---
        df["Cuota_Vigente"] = pd.to_numeric(
            df["Cuota_Vigente"].astype(str).str[-2:], 
            errors='coerce'
        ).fillna(0).astype(int)

        # --- 3. Preparar Fechas y Ordenar ---
        df["Fecha_Cuota_Vigente"] = pd.to_datetime(df["Fecha_Cuota_Vigente"], errors='coerce')
        df.dropna(subset=["Fecha_Cuota_Vigente"], inplace=True)
        
        # Ordenar *todo* el DataFrame por fecha es crucial para la nueva lógica
        df.sort_values(by="Fecha_Cuota_Vigente", inplace=True)

        # --- 4. Dividir datos: (Pasado/Presente) vs (Futuro) ---
        fecha_fin_de_mes = pd.Timestamp.now() + pd.offsets.MonthEnd(0)
        
        cuotas_pasadas_y_presentes = df[df["Fecha_Cuota_Vigente"] <= fecha_fin_de_mes]
        cuotas_futuras = df[df["Fecha_Cuota_Vigente"] > fecha_fin_de_mes]

        # --- 5. Procesar Lógica Actual (Pasado y Presente) ---
        # Agrupar y agregar como antes
        grouped_presente = cuotas_pasadas_y_presentes.groupby(["Cedula_Cliente", "Credito"])
        
        agg_data_presente = pd.DataFrame() # Iniciar vacío
        
        if grouped_presente.groups:
            agg_data_presente = grouped_presente.agg(
                Primera_Cuota_Atraso=("Cuota_Vigente", "first"),
                Fecha_Atraso=("Fecha_Cuota_Vigente", "first"),
                Ultima_Cuota_Atraso=("Cuota_Vigente", "last"),
                Pago_Total=("Valor_Cuota", "sum"),
                Total_Intereses=("Intereses", "sum")
            ).reset_index()

        # --- 6. Procesar Nueva Lógica (Clientes Anticipados) ---
        
        # Identificar los créditos que ya procesamos
        creditos_ya_procesados = agg_data_presente.set_index(["Cedula_Cliente", "Credito"]).index
        
        # De las cuotas futuras, agrupar y tomar la *primera* (la más cercana)
        # Como el df ya está ordenado, .first() nos da la cuota correcta
        grouped_futuro = cuotas_futuras.groupby(["Cedula_Cliente", "Credito"])
        
        agg_data_futuro = pd.DataFrame() # Iniciar vacío
        
        if grouped_futuro.groups:
            proximas_cuotas = grouped_futuro.first().reset_index()
            
            # Filtrar para quedarnos solo con los que NO están en el set "presente"
            proximas_cuotas_filtradas = proximas_cuotas.set_index(["Cedula_Cliente", "Credito"])
            
            proximas_cuotas_filtradas = proximas_cuotas_filtradas[
                ~proximas_cuotas_filtradas.index.isin(creditos_ya_procesados)
            ]
            
            # Reformatear para que coincida con la estructura de agg_data_presente
            if not proximas_cuotas_filtradas.empty:
                agg_data_futuro = pd.DataFrame({
                    "Cedula_Cliente": proximas_cuotas_filtradas.index.get_level_values("Cedula_Cliente"),
                    "Credito": proximas_cuotas_filtradas.index.get_level_values("Credito"),
                    "Primera_Cuota_Atraso": proximas_cuotas_filtradas["Cuota_Vigente"],
                    "Fecha_Atraso": proximas_cuotas_filtradas["Fecha_Cuota_Vigente"], # Esta es ahora una fecha futura
                    "Ultima_Cuota_Atraso": proximas_cuotas_filtradas["Cuota_Vigente"],
                    "Pago_Total": proximas_cuotas_filtradas["Valor_Cuota"],
                    "Total_Intereses": proximas_cuotas_filtradas["Intereses"]
                })

        # --- 7. Combinar los dos resultados ---
        agg_data = pd.concat([agg_data_presente, agg_data_futuro], ignore_index=True)

        if agg_data.empty:
            print("No se encontraron cuotas para procesar (ni vencidas, ni actuales, ni futuras).")
            return pd.DataFrame()

        # --- 8. Agrupar por cliente y crédito para los cálculos (El resto es igual) ---
        # (Esta parte del código original se movió arriba y se adaptó)
        
        # --- 9. Duplicar filas para Intereses (Lógica de Códigos 0 y 40) ---
        pago_total_df = agg_data.copy()
        pago_total_df["Codigo"] = 0
        pago_total_df["Valor"] = pago_total_df["Pago_Total"]

        intereses_df = agg_data[agg_data["Total_Intereses"] > 0].copy()
        if not intereses_df.empty:
            intereses_df["Codigo"] = 40
            intereses_df["Valor"] = intereses_df["Total_Intereses"]

        final_df = pd.concat([pago_total_df, intereses_df], ignore_index=True)
        
        columnas_finales = [
            "Cedula_Cliente", "Credito", "Primera_Cuota_Atraso", "Fecha_Atraso",
            "Ultima_Cuota_Atraso", "Codigo", "Valor"
        ]
        # Asegurarse de que las columnas existen antes de seleccionarlas
        columnas_reales = [col for col in columnas_finales if col in final_df.columns]
        final_df = final_df[columnas_reales]
        
        final_df.sort_values(by=["Cedula_Cliente", "Credito", "Codigo"], inplace=True)
        
        return final_df

    def _generar_linea_encabezado(self, df: pd.DataFrame) -> str:
        """Genera la primera línea (encabezado) del archivo plano."""
        fecha_actual = pd.Timestamp.now().strftime('%Y%m%d')
        num_registros = len(df)
        
        valor_total = df['Valor'].apply(lambda x: int(x)).sum()
        valor_total_formateado = str(valor_total) + '00'
        
        return f"1,{fecha_actual},{num_registros},{valor_total_formateado},0"

    def _formatear_descripcion(self, row: pd.Series, prefijo: str) -> str:
        """
        Crea la descripción de las cuotas basado en si la primera y última son iguales.
        """
        primera = row['Primera_Cuota_Atraso']
        ultima = row['Ultima_Cuota_Atraso']
        
        if primera == ultima:
            return f"{prefijo} No. {primera}"
        else:
            descriptor_base = prefijo.split(" ")[-1]
            return f"{prefijo} No. {primera} a {descriptor_base} No. {ultima}"

    def _generar_lineas_datos(self, df: pd.DataFrame) -> List[str]:
        """Genera todas las líneas de datos (registros) del archivo plano."""
        lineas_datos = []
        
        for _, row in df.iterrows():
            desc_cuotas = self._formatear_descripcion(row, "Cuota")
            desc_pago = self._formatear_descripcion(row, "Pago de Cuota")
            fecha_atraso_formateada = row['Fecha_Atraso'].strftime('%Y%m%d')
            valor_formateado = str(int(row['Valor'])) + '00'
            
            linea = (
                f"2,10791,1001,{row['Cedula_Cliente']},{row['Credito']},{desc_cuotas},"
                f"{row['Codigo']},{desc_pago},0,{fecha_atraso_formateada},{valor_formateado},"
                "0,0,0,0,0,0,0,0"
            )
            lineas_datos.append(linea)
            
        return lineas_datos

    def generar_archivo_plano(self, df: pd.DataFrame, ruta_guardado: str) -> bool:
        """
        Orquesta la creación del archivo .txt completo y lo guarda en la ruta especificada.
        """
        if df.empty:
            print("El DataFrame está vacío, no se generará el archivo plano.")
            return False
            
        try:
            linea_encabezado = self._generar_linea_encabezado(df)
            lineas_datos = self._generar_lineas_datos(df)
            
            with open(ruta_guardado, 'w', encoding='utf-8') as f:
                f.write(linea_encabezado + '\n')
                for linea in lineas_datos:
                    f.write(linea + '\n')
            return True
        except Exception as e:
            print(f"Error al generar o guardar el archivo plano: {e}")
            return False