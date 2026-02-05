import pandas as pd
import numpy as np

class NovedadesService:
    def __init__(self, config):
        self.config = config

    def aplicar_novedades(self, df_base, df_novedades):
        """
        Procesa el df_novedades y devuelve dos reportes:
        1. El df_base enriquecido con columnas de resumen de novedades.
        2. Un nuevo df con el detalle completo de todas las novedades, sin filas duplicadas.
        """
        print("🔄 Aplicando novedades y creando reportes...")
        
        if df_novedades.empty:
            print("⚠️ Archivo de novedades vacío. No se aplicarán cambios.")
            df_base['Cantidad_Novedades'] = 0
            df_base['Fecha_Ultima_Novedad'] = None
            return df_base, pd.DataFrame()

        # --- 1. Preparar el DataFrame de Novedades Detallado ---
        # Aseguramos datetime
        df_novedades['Fecha_Novedad'] = pd.to_datetime(df_novedades['Fecha_Novedad'], errors='coerce')
        df_novedades.dropna(subset=['Cedula_Cliente', 'Fecha_Novedad'], inplace=True)
        df_novedades['Cedula_Cliente'] = df_novedades['Cedula_Cliente'].astype(str).str.strip()

        # --- SOLUCIÓN AL AUMENTO DE FILAS ---
        info_cliente = df_base[['Cedula_Cliente', 'Nombre_Cliente']].copy()
        info_cliente['Cedula_Cliente'] = info_cliente['Cedula_Cliente'].astype(str).str.strip()
        info_cliente['Nombre_Cliente'] = info_cliente['Nombre_Cliente'].astype(str).str.strip()
        info_cliente.drop_duplicates(subset=['Cedula_Cliente'], keep='first', inplace=True)
        
        reporte_novedades_detallado = pd.merge(df_novedades, info_cliente, on='Cedula_Cliente', how='left')             
        
        # --- 4. Preparar el Reporte Base Enriquecido (con resúmenes) ---
        df_base_enriquecido = df_base.copy()
        df_base_enriquecido['Cedula_Cliente'] = df_base_enriquecido['Cedula_Cliente'].astype(str).str.strip()

        resumen_novedades = df_novedades.groupby('Cedula_Cliente').agg(
            Cantidad_Novedades=('Novedad', 'count'),
            Fecha_Ultima_Novedad=('Fecha_Novedad', 'max')
        ).reset_index()

        df_base_enriquecido = pd.merge(df_base_enriquecido, resumen_novedades, on='Cedula_Cliente', how='left')
        
        # --- CORRECCIÓN CRÍTICA AQUÍ ---
        # Reemplazamos el inplace=True por asignación directa y encadenada
        df_base_enriquecido['Cantidad_Novedades'] = df_base_enriquecido['Cantidad_Novedades'].fillna(0).astype(int)
        
        print("📅 Formateando fechas (eliminando la hora)...")
        if 'Fecha_Ultima_Novedad' in df_base_enriquecido.columns:
            df_base_enriquecido['Fecha_Ultima_Novedad'] = pd.to_datetime(df_base_enriquecido['Fecha_Ultima_Novedad'], errors='coerce').dt.date
        
        for col in ['Fecha_Novedad', 'Fecha_Compromiso']:
            if col in reporte_novedades_detallado.columns:
                reporte_novedades_detallado[col] = pd.to_datetime(reporte_novedades_detallado[col], errors='coerce').dt.date
        
        print("🔄 Agrupando tipos de novedad en 'OTRAS GESTIONES'...")

        # 1. Definimos los códigos que NO queremos agrupar.
        codigos_especiales = ['C02', 'C04', 'C03', 'C10']
        if 'Codigo_Novedad' in reporte_novedades_detallado.columns:
            reporte_novedades_detallado.loc[
                ~reporte_novedades_detallado['Codigo_Novedad'].isin(codigos_especiales),
                'Tipo_Novedad'
            ] = 'OTRAS GESTIONES'
        
        # --- BLINDAJE EXTRA: Fecha Compromiso ---
        # Convertimos a object para que acepte el texto "SIN COMPROMISO" sin error
        if 'Fecha_Compromiso' in reporte_novedades_detallado.columns:
            reporte_novedades_detallado['Fecha_Compromiso'] = reporte_novedades_detallado['Fecha_Compromiso'].astype(object)
            
            reporte_novedades_detallado.loc[
                reporte_novedades_detallado['Tipo_Novedad'] != 'COMPROMISO DE PAGO', 
                'Fecha_Compromiso'
            ] = 'SIN COMPROMISO'
    
        # Reordenar columnas para la hoja de novedades
        columnas_novedades = [
            'Empresa','Cedula_Cliente', 'Nombre_Cliente', 'Fecha_Novedad', 'Usuario_Novedad',
            'Telefono_Cliente','Celular_Cliente', 'Codigo_Novedad',
            'Tipo_Novedad', 'Novedad','Valor','Fecha_Compromiso'
        ]
        columnas_existentes = [col for col in columnas_novedades if col in reporte_novedades_detallado.columns]
        reporte_novedades_detallado = reporte_novedades_detallado.reindex(columns=columnas_existentes)
                                
        print("✅ Reportes de Novedades generados.")
        return df_base_enriquecido, reporte_novedades_detallado