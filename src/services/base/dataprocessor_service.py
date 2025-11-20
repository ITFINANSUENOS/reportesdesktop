import pandas as pd
import numpy as np

# ¡Importamos los nuevos servicios!
from src.services.base.data_quality_audit_service import DataQualityAuditService

class ReportProcessorService:
    """
    Orquesta los pasos finales de procesamiento del reporte,
    delegando tareas específicas a servicios especializados y
    manejando el formateo y la limpieza final.
    """
    def __init__(self, config):
        self.config = config
        # Instanciamos los servicios que este orquestador va a utilizar
        self.quality_audit_service = DataQualityAuditService()
        # NOTA: MetricsCalculationService y CategorizationService se llamarán
        # desde el ReportService principal, antes de llegar aquí.

    def filter_by_date_range(self, reporte_df, start_date, end_date):
        """
        Filtra el reporte por un rango de fechas. (Sin cambios)
        """
        if not start_date or not end_date:
            return reporte_df

        print(f"🔍 Aplicando filtro de fecha: desde {start_date} hasta {end_date}")
        df = reporte_df.copy()
        df['Fecha_Cuota_Vigente'] = pd.to_datetime(df['Fecha_Cuota_Vigente'], format='%d/%m/%Y', errors='coerce')
        start_date_dt = pd.to_datetime(start_date, format='%d/%m/%Y', errors='coerce')
        end_date_dt = pd.to_datetime(end_date, format='%d/%m/%Y', errors='coerce')

        if pd.isna(start_date_dt) or pd.isna(end_date_dt):
            print("⚠️ Formato de fecha inválido. Se omite el filtro.")
            return reporte_df

        mask = (df['Fecha_Cuota_Vigente'] >= start_date_dt) & (df['Fecha_Cuota_Vigente'] <= end_date_dt)
        filtered_df = df[mask]
        print(f"✅ Filtro aplicado. {len(filtered_df)} registros encontrados en el rango.")
        return filtered_df

    def finalize_report(self, reporte_df, orden_columnas):
        """
        Realiza la auditoría, el formateo y la reestructuración final del reporte.
        """
        print("🧹 Realizando transformaciones y limpieza final...")
        
        # 1. Ejecutar la auditoría de calidad usando el servicio especializado
        df_a_corregir = self.quality_audit_service.run_audit(reporte_df)

        # 2. Aplicar formateo de presentación
        reporte_df = self._format_dates(reporte_df)
        reporte_df = self._fill_final_na(reporte_df)
        reporte_df = self._format_percentages(reporte_df)
        reporte_df = self._clean_leader_info(reporte_df)

        # 3. Limpiar y reordenar columnas
        print("🏗️ Reordenando columnas según la configuración...")
        columnas_a_eliminar = [
            'Saldo_Factura', 'Tipo_Credito', 'Numero_Credito', 'Meta_DC_Al_Dia', 
            'Meta_DC_Atraso', 'Meta_Atraso','Movil_Codeudor1','Movil_Codeudor2','Celular2',
            *[col for col in reporte_df.columns if col.endswith(('_Analisis', '_R03', '_Venc', '_display'))]
        ]
        reporte_df.drop(columns=columnas_a_eliminar, inplace=True, errors='ignore')
        
        columnas_actuales = reporte_df.columns.tolist()
        columnas_ordenadas = [col for col in orden_columnas if col in columnas_actuales]
        columnas_restantes = [col for col in columnas_actuales if col not in columnas_ordenadas]
        
        final_df = reporte_df[columnas_ordenadas + columnas_restantes]

        return final_df, df_a_corregir

    # Los siguientes son métodos privados de apoyo para la finalización
    def _format_dates(self, df):
        print("📅 Formateando fechas a solo día/mes/año...")
        columnas_de_fecha = [
            'Fecha_Cuota_Vigente', 'Fecha_Cuota_Atraso', 'Fecha_Facturada', 
            'Fecha_Desembolso', 'Fecha_Ultima_Novedad', 'Fecha_Ultimo_Pago_Inicial'
        ]
        for col in columnas_de_fecha:
            if col in df.columns:
                mask_no_anticipado = df[col] != 'ANTICIPADO'
                df.loc[mask_no_anticipado, col] = pd.to_datetime(
                    df.loc[mask_no_anticipado, col], errors='coerce'
                ).dt.date
        return df

    def _fill_final_na(self, df):
        print(" Aplicando valores por defecto y formato de presentación...")
        columnas_vencimiento = {
            'Fecha_Cuota_Vigente': 'VIGENCIA EXPIRADA', 'Cuota_Vigente': 'VIGENCIA EXPIRADA',
            'Valor_Cuota_Vigente': 'VIGENCIA EXPIRADA', 'Fecha_Cuota_Atraso': 'SIN MORA',
            'Primera_Cuota_Mora': 'SIN MORA', 'Valor_Cuota_Atraso': 0, 'Valor_Vencido': 0
        }
        ref_col_anticipado = 'Cuota_Vigente'
        for col, default_value in columnas_vencimiento.items():
            if col in df.columns:
                mask = df[col].isnull() & (df[ref_col_anticipado] != 'ANTICIPADO')
                df.loc[mask, col] = default_value

        mask_no_fns = df['Empresa'] != 'FINANSUEÑOS'
        for col in ['Saldo_Avales', 'Saldo_Interes_Corriente']:
            if col in df.columns:
                df[col] = df[col].astype(object)
                df.loc[mask_no_fns, col] = 'NO APLICA'
        return df

    def _format_percentages(self, df):
        print("✨ Formateando columnas de porcentaje...")
        for col in ['Meta_%', 'Meta_T.R_%']:
            if col in df.columns:
                numeric_col = pd.to_numeric(df[col].astype(str).str.replace('%', ''), errors='coerce')
                numeric_col = np.where(numeric_col > 1, numeric_col / 100, numeric_col).round(4)
                df[col] = (numeric_col * 100).round(0).astype(int).astype(str) + '%'
        return df
    
    def _clean_leader_info(self, df):
        print("👔 Limpiando y completando la columna 'Lider_Zona' y 'Movil_Lider'")
        if 'Lider_Zona' in df.columns and 'Regional_Venta' in df.columns:
            is_numeric_mask = pd.to_numeric(df['Lider_Zona'], errors='coerce').notna()
            df.loc[is_numeric_mask, 'Lider_Zona'] = np.nan
            
            mapa_moviles = {}
            if 'Movil_Lider' in df.columns:
                mapa_df = df.dropna(subset=['Lider_Zona', 'Movil_Lider']).drop_duplicates(subset=['Lider_Zona'])
                mapa_moviles = pd.Series(mapa_df['Movil_Lider'].values, index=mapa_df['Lider_Zona']).to_dict()

            def fill_with_mode(series):
                mode_val = series.mode()
                return series.fillna(mode_val.iloc[0]) if not mode_val.empty else series
            df['Lider_Zona'] = df.groupby('Regional_Venta')['Lider_Zona'].transform(fill_with_mode)
            if 'Movil_Lider' in df.columns:
                df['Movil_Lider'] = df['Lider_Zona'].map(mapa_moviles)
            df['Lider_Zona'].fillna('NO ASIGNADO', inplace=True)
            if 'Movil_Lider' in df.columns:
                df['Movil_Lider'].fillna('NO ASIGNADO', inplace=True)
        return df