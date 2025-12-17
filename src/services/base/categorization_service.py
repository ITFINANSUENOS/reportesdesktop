import pandas as pd
import numpy as np

class CategorizationService:
    """
    Servicio simplificado. Ahora los Call Centers vienen asignados directamente
    por la Zona desde el archivo de configuración.
    Aquí solo calculamos las franjas de mora y limpiamos gestores.
    """
    def map_call_center_data(self, reporte_df):
        print("📞 Estandarizando datos de Gestor y calculando Franjas...")

        # 1. Limpieza básica de Gestor (Igual que antes)
        if 'Gestor' in reporte_df.columns:
            reporte_df.loc[reporte_df['Gestor'] == 'SIN GESTOR', 'Gestor'] = 'CALL CENTER'
            reporte_df['Gestor'].fillna('OTRAS ZONAS', inplace=True)

        # 2. Validación de Días de Atraso
        if 'Dias_Atraso' not in reporte_df.columns:
            print("⚠️ Columna 'Dias_Atraso' no encontrada. Se saltan los cálculos.")
            return reporte_df
            
        reporte_df['Dias_Atraso'] = pd.to_numeric(reporte_df['Dias_Atraso'], errors='coerce').fillna(0)

        # 3. Calcular Franja Meta (Necesario para tu reporte final)
        condiciones_mora = [
            reporte_df['Dias_Atraso'] == 0, reporte_df['Dias_Atraso'].between(1, 30),
            reporte_df['Dias_Atraso'].between(31, 90), reporte_df['Dias_Atraso'].between(91, 180),
            reporte_df['Dias_Atraso'].between(181, 360), reporte_df['Dias_Atraso'] > 360
        ]
        valores_mora = ['AL DIA', '1 A 30', '31 A 90', '91 A 180','181 A 360','MAS DE 360']
        reporte_df['Franja_Meta'] = np.select(condiciones_mora, valores_mora, default='SIN INFO')
        
        # 4. Calcular Franja Cartera (Necesario para tu reporte final)
        condiciones_cartera = [
            reporte_df['Dias_Atraso'] == 0, reporte_df['Dias_Atraso'].between(1, 30),
            reporte_df['Dias_Atraso'].between(31, 60), reporte_df['Dias_Atraso'].between(61, 90),
            reporte_df['Dias_Atraso'].between(91, 120), reporte_df['Dias_Atraso'].between(121, 150),
            reporte_df['Dias_Atraso'].between(151, 180), reporte_df['Dias_Atraso'].between(181, 210),
            reporte_df['Dias_Atraso'].between(211, 270), reporte_df['Dias_Atraso'].between(271, 360),
            reporte_df['Dias_Atraso'] > 360
        ]
        valores_cartera = [
            'AL DIA', '1 A 30', '31 A 60', '61 A 90', '91 A 120', '121 A 150',
            '151 A 180', '181 A 210', '211 A 270', '271 A 360', 'MAS DE 360'
        ]
        reporte_df['Franja_Cartera'] = np.select(condiciones_cartera, valores_cartera, default='SIN INFO')
        
        # NOTA: Ya NO hacemos el mapeo complejo de Call Center aquí.
        # Como hiciste el rename_map en la configuración, las columnas:
        # 'Call_Center_Apoyo', 'Nombre_Call_Center' y 'Telefono_Call_Center'
        # YA EXISTEN en el reporte_df gracias al merge en ReportService.

        print("✅ Cálculo de franjas completado. (Asignación de CC viene directa por Zona)")
        return reporte_df
    
    def calculate_last_payment_range(self, reporte_df):
        """
        Calcula el rango de tiempo desde el último pago inicial hasta una fecha de referencia.
        Crea la columna 'Rango_Ultimo_pago_Inicial'.
        """
        print("📅 Calculando el rango de la fecha de último pago inicial...")

        # Verificamos que la columna necesaria exista
        if 'Fecha_Ultimo_pago_Inicial' not in reporte_df.columns:
            print("   - ⚠️ Columna 'Fecha_Ultimo_pago_Inicial' no encontrada. Se omite el cálculo del rango.")
            return reporte_df
        
        # 1. Aseguramos que la columna sea del tipo datetime
        reporte_df['Fecha_Ultimo_pago_Inicial'] = pd.to_datetime(reporte_df['Fecha_Ultimo_pago_Inicial'], errors='coerce')

        # 2. Definimos la fecha de referencia (día 5 del mes actual)
        hoy = pd.Timestamp.now()
        fecha_referencia = hoy.replace(day=5)

        # 3. Calculamos las fechas límite
        fecha_6_meses = fecha_referencia - pd.DateOffset(months=6)
        fecha_12_meses = fecha_referencia - pd.DateOffset(months=12)
        fecha_24_meses = fecha_referencia - pd.DateOffset(months=24)
        fecha_48_meses = fecha_referencia - pd.DateOffset(months=48)

        # 4. Definimos las condiciones de clasificación
        condiciones_pago = [
            reporte_df['Fecha_Ultimo_pago_Inicial'] > fecha_6_meses,
            reporte_df['Fecha_Ultimo_pago_Inicial'].between(fecha_12_meses, fecha_6_meses, inclusive='right'),
            reporte_df['Fecha_Ultimo_pago_Inicial'].between(fecha_24_meses, fecha_12_meses, inclusive='right'),
            reporte_df['Fecha_Ultimo_pago_Inicial'].between(fecha_48_meses, fecha_24_meses, inclusive='right'),
            reporte_df['Fecha_Ultimo_pago_Inicial'] <= fecha_48_meses
        ]
        
        # 5. Definimos los valores para cada rango
        valores_pago = [
            '6 MESES',
            '6 A 12 MESES',
            '1 a 2 AÑOS',
            '2 A 4 AÑOS',
            'MAS 4 AÑOS'
        ]

        # 6. Creamos la columna usando np.select
        reporte_df['Rango_Ultimo_pago_Inicial'] = np.select(
            condiciones_pago, 
            valores_pago, 
            default='SIN PAGO REGISTRADO'
        )
        
        print("✅ Rango de último pago inicial calculado.")
        return reporte_df