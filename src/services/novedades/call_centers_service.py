import pandas as pd
import numpy as np

class CallCenterService:
    """
    Servicio para generar reportes de rendimiento, llamadas y mensajería
    específicos para Call Centers.
    """

    def _cargar_call_center_sheets(self, rutas_call_center, config):
        """
        Método auxiliar para cargar todas las hojas de los archivos de Call Center.
        """
        config_cc = config.get("CALL_CENTER", {})
        if not config_cc or "sheets" not in config_cc:
            print("❌ Error: La configuración para 'CALL_CENTER' no es válida.")
            return None, None, None

        # Encontrar configuraciones
        config_llamadas = next((item for item in config_cc['sheets'] if item["sheet_name"] == "Llamadas_Call"), None)
        config_flujos = next((item for item in config_cc['sheets'] if item["sheet_name"] == "Flujos"), None)
        config_mensajes = next((item for item in config_cc['sheets'] if item["sheet_name"] == "Mensajeria_Call"), None)

        lista_llamadas, lista_flujos, lista_mensajes = [], [], []

        for path in rutas_call_center:
            try:
                # Cargar hoja de llamadas (si existe config)
                if config_llamadas:
                    df_llamadas = pd.read_excel(
                        path,
                        sheet_name=config_llamadas["sheet_name"],
                        usecols=config_llamadas["usecols"]
                    ).rename(columns=config_llamadas["rename_map"])
                    lista_llamadas.append(df_llamadas)

                # Cargar hoja de flujos (si existe config)
                if config_flujos:
                    df_flujos = pd.read_excel(
                        path,
                        sheet_name=config_flujos["sheet_name"],
                        usecols=config_flujos["usecols"]
                    ).rename(columns=config_flujos["rename_map"])
                    lista_flujos.append(df_flujos)
                
                # Cargar hoja de mensajería (si existe config)
                if config_mensajes:
                    df_mensajes = pd.read_excel(
                        path,
                        sheet_name=config_mensajes["sheet_name"],
                        usecols=config_mensajes["usecols"]
                    ).rename(columns=config_mensajes["rename_map"])
                    lista_mensajes.append(df_mensajes)

            except Exception as e:
                print(f"⚠️ Error leyendo el archivo {path}. Hoja no encontrada o error: {e}")
                # Continuamos por si otros archivos sí son correctos
                pass

        # Concatenar los DataFrames
        df_llamadas_total = pd.concat(lista_llamadas, ignore_index=True) if lista_llamadas else pd.DataFrame()
        df_flujos_total = pd.concat(lista_flujos, ignore_index=True) if lista_flujos else pd.DataFrame()
        df_mensajes_total = pd.concat(lista_mensajes, ignore_index=True) if lista_mensajes else pd.DataFrame()
        
        return df_llamadas_total, df_flujos_total, df_mensajes_total

    def generar_reporte_llamadas(self, rutas_call_center, config):
        """
        Carga los datos de llamadas y flujos, los une por extensión
        y genera un reporte detallado de llamadas.
        """
        print("🔄 Iniciando la generación del Reporte de Llamadas...")
        if not rutas_call_center:
            print("⚠️ No se proporcionaron archivos de Call Center.")
            return pd.DataFrame()

        try:
            # Usamos el método auxiliar para cargar los datos
            df_llamadas_total, df_flujos_total, _ = self._cargar_call_center_sheets(rutas_call_center, config)

            if df_llamadas_total.empty or df_flujos_total.empty:
                print("⚠️ No se pudieron cargar datos de 'Llamadas_Call' o 'Flujos'. Abortando Reporte de Llamadas.")
                return pd.DataFrame()
            
            # --- Lógica de limpieza de Duracion_Llamada ---
            print("🧹 Limpiando la columna 'Duracion_Llamada'...")
            if 'Duracion_Llamada' in df_llamadas_total.columns:
                df_llamadas_total['Duracion_Original_Str'] = df_llamadas_total['Duracion_Llamada'].astype(str)
                
                extracted_seconds = df_llamadas_total['Duracion_Llamada'].astype(str).str.extract(r'^(\d+)')
                numeric_seconds = pd.to_numeric(extracted_seconds[0], errors='coerce').fillna(0)
                df_llamadas_total['Duracion_Llamada'] = numeric_seconds.astype(int)
                
                if 'Estado_Llamada' in df_llamadas_total.columns:
                    df_llamadas_total['Estado_Llamada'] = np.where(
                        (df_llamadas_total['Estado_Llamada'] == 'ANSWERED') & (df_llamadas_total['Duracion_Llamada'] < 30),
                        'FAILED',
                        df_llamadas_total['Estado_Llamada']
                    )
            
            # --- Lógica de unión para Reporte de Llamadas ---
            df_llamadas_total['Extension_Llamada'] = df_llamadas_total['Extension_Llamada'].astype(str)
            df_flujos_total['Extension_Llamada'] = df_flujos_total['Extension_Llamada'].astype(str)
            
            df_flujos_para_llamadas = df_flujos_total.drop_duplicates(subset=['Extension_Llamada'])

            df_reporte = pd.merge(
                df_llamadas_total,
                df_flujos_para_llamadas,
                on='Extension_Llamada',
                how='left'
            )
            
            # Restaurar formato original de Duración
            if 'Duracion_Original_Str' in df_reporte.columns:
                df_reporte['Duracion_Llamada'] = df_reporte['Duracion_Original_Str']
                df_reporte.drop(columns=['Duracion_Original_Str'], inplace=True)

            if 'Flujo_Truora' in df_reporte.columns:
                df_reporte.drop(columns=['Flujo_Truora'], inplace=True)
            
            return df_reporte

        except Exception as e:
            print(f"❌ Ocurrió un error al generar Reporte de Llamadas: {e}")
            return pd.DataFrame()

    def generar_reporte_mensajes(self, rutas_call_center, config):
        """
        Carga los datos de mensajería y flujos, los une por Flujo_Truora
        y genera un reporte detallado de mensajes.
        """
        print("🔄 Iniciando la generación del Reporte de Mensajes...")
        if not rutas_call_center:
            print("⚠️ No se proporcionaron archivos de Call Center.")
            return pd.DataFrame()
            
        try:
            _, df_flujos_total, df_mensajes_total = self._cargar_call_center_sheets(rutas_call_center, config)

            if df_mensajes_total.empty or df_flujos_total.empty:
                print("⚠️ No se pudieron cargar datos de 'Mensajeria_Call' o 'Flujos'. Abortando Reporte de Mensajes.")
                return pd.DataFrame()

            # --- Lógica de unión para Reporte de Mensajes ---
            df_mensajes_total['Flujo_Truora'] = df_mensajes_total['Flujo_Truora'].astype(str)

            columnas_flujo = ['Flujo_Truora', 'Call_Center', 'Nombre_Call']
            df_flujos_para_mensajes = df_flujos_total[columnas_flujo].copy()
            
            df_flujos_para_mensajes['Flujo_Truora'] = df_flujos_para_mensajes['Flujo_Truora'].astype(str)
            df_flujos_para_mensajes.drop_duplicates(subset=['Flujo_Truora'], inplace=True)

            df_reporte = pd.merge(
                df_mensajes_total,
                df_flujos_para_mensajes,
                on='Flujo_Truora',
                how='left'
            )
            return df_reporte

        except Exception as e:
            print(f"❌ Ocurrió un error al generar Reporte de Mensajes: {e}")
            return pd.DataFrame()

    def _limpiar_y_preparar_datos(self, df):
        """
        Realiza una limpieza inicial de los datos necesarios para el reporte.
        """
        print("🧹 Limpiando y preparando datos para el reporte de Call Centers...")
        df_copy = df.copy()
        columnas_numericas = ['Meta_General', 'Meta_$', 'Recaudo_Meta']
        for col in columnas_numericas:
            if col in df_copy.columns:
                df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce').fillna(0)
            else:
                df_copy[col] = 0
        columnas_texto = [
            'Zona', 'Cobrador', 'Call_Center_Apoyo', 'Nombre_Call_Center', 'Franja_Meta'
        ]
        for col in columnas_texto:
            if col in df_copy.columns:
                df_copy[col] = df_copy[col].astype(str).str.strip().str.upper().replace('NAN', '')
            else:
                df_copy[col] = ''          
        return df_copy

    def generar_reporte_call_center(self, df_analisis_cartera):
        """
        Genera un reporte consolidado del rendimiento de los Call Centers.
        [MODIFICADO] Usa lógica unificada (Cascada) para sumar Zona + Apoyo.
        """
        print("🔄 Iniciando la generación del reporte de Call Centers (Lógica Unificada)...")
        df = self._limpiar_y_preparar_datos(df_analisis_cartera)
        
        # Definimos los Call Centers a analizar
        all_call_centers = [f'CL{i}' for i in range(1, 10)]

        # --- LÓGICA DE CASCADA (Waterflow) ---
        # 1. Prioridad: Lo que está en Zona y está 'AL DIA'
        mask_zona_al_dia = (
            (df['Zona'].isin(all_call_centers)) & 
            (df['Franja_Meta'] == 'AL DIA')
        )
        df_zona = df[mask_zona_al_dia].copy()
        
        # 2. Resto: Lo que está en Apoyo y NO fue capturado en Zona
        # Esto asegura que sumamos las 34 cuentas extras
        mask_apoyo_general = df['Call_Center_Apoyo'].isin(all_call_centers)
        mask_apoyo_final = mask_apoyo_general & (~mask_zona_al_dia)
        
        df_apoyo = df[mask_apoyo_final].copy()

        print(f"📊 Registros Zona (Al Día): {len(df_zona)} | Registros Apoyo (Extra): {len(df_apoyo)}")

        # --- NORMALIZACIÓN DE COLUMNAS PARA UNIR ---
        # Estandarizamos nombres para poder sumar
        df_zona_norm = df_zona.rename(columns={
            'Zona': 'CALL_CENTER_ID',
            'Cobrador': 'NOMBRE_AGENTE',
            'Meta_General': 'META_UNIFICADA'
        })[['CALL_CENTER_ID', 'NOMBRE_AGENTE', 'META_UNIFICADA', 'Recaudo_Meta']].copy()
        
        df_apoyo_norm = df_apoyo.rename(columns={
            'Call_Center_Apoyo': 'CALL_CENTER_ID',
            'Nombre_Call_Center': 'NOMBRE_AGENTE',
            'Meta_$': 'META_UNIFICADA'
        })[['CALL_CENTER_ID', 'NOMBRE_AGENTE', 'META_UNIFICADA', 'Recaudo_Meta']].copy()

        # --- CONCATENACIÓN ---
        df_total_unificado = pd.concat([df_zona_norm, df_apoyo_norm], ignore_index=True)

        if df_total_unificado.empty:
            print("⚠️ No se encontraron datos para el reporte unificado.")
            return pd.DataFrame(columns=[
                'CALL_CENTER', 'NOMBRE', 'META_$', 'Recaudo_Meta', 'Faltante', 'Cumplimiento_%'
            ])

        # --- AGRUPACIÓN FINAL ---
        agg_total = df_total_unificado.groupby(['CALL_CENTER_ID', 'NOMBRE_AGENTE']).agg(
            Meta_Total=('META_UNIFICADA', 'sum'),
            Recaudo_Total=('Recaudo_Meta', 'sum')
        ).reset_index()

        # --- CÁLCULOS DE KPI ---
        agg_total['Faltante'] = agg_total['Meta_Total'] - agg_total['Recaudo_Total']
        
        cumplimiento_decimal = np.where(
            agg_total['Meta_Total'] > 0,
            agg_total['Recaudo_Total'] / agg_total['Meta_Total'],
            0
        )
        agg_total['Cumplimiento_%'] = [f"{format(x * 100, '.2f')}%".replace('.', ',') for x in cumplimiento_decimal]

        # --- FORMATO FINAL ---
        agg_total.rename(columns={
            'CALL_CENTER_ID': 'CALL_CENTER', 
            'NOMBRE_AGENTE': 'NOMBRE',
            'Meta_Total': 'META_$',
            'Recaudo_Total': 'Recaudo_Meta'
        }, inplace=True)

        print("💰 Aplicando formato de moneda...")
        columnas_moneda = ['META_$', 'Recaudo_Meta', 'Faltante']
        for col in columnas_moneda:
            if col in agg_total.columns:
                agg_total[col] = agg_total[col].apply(lambda x: f"$ {int(round(x, 0)):,}".replace(',', '.'))

        # Ordenar
        columnas_finales = [
            'CALL_CENTER', 'NOMBRE', 'META_$', 'Recaudo_Meta', 'Faltante', 'Cumplimiento_%'
        ]
        df_reporte = agg_total[columnas_finales].sort_values(by='CALL_CENTER').reset_index(drop=True)
        
        print("✅ Reporte de Call Centers generado exitosamente.")
        return df_reporte