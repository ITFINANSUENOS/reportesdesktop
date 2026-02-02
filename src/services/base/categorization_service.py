import pandas as pd
import numpy as np

class CategorizationService:
    """
    Servicio simplificado. Ahora los Call Centers vienen asignados directamente
    por la Zona desde el archivo de configuración.
    Aquí solo calculamos las franjas de mora, limpiamos gestores y rangos de pago.
    """
    def map_call_center_data(self, reporte_df):
        print("📞 Estandarizando datos de Gestor y calculando Franjas...")

        # 1. Limpieza básica de Gestor
        if 'Gestor' in reporte_df.columns:
            mask_sin_gestor = reporte_df['Gestor'] == 'SIN GESTOR'
            reporte_df.loc[mask_sin_gestor, 'Gestor'] = 'CALL CENTER'
            
            # CORRECCIÓN 1: Evitamos el inplace=True para prevenir ChainedAssignmentError
            reporte_df['Gestor'] = reporte_df['Gestor'].fillna('OTRAS ZONAS')

        # 2. Validación de Días de Atraso
        if 'Dias_Atraso' not in reporte_df.columns:
            print("⚠️ Columna 'Dias_Atraso' no encontrada. Se saltan los cálculos.")
            return reporte_df
            
        reporte_df['Dias_Atraso'] = pd.to_numeric(reporte_df['Dias_Atraso'], errors='coerce').fillna(0)

        # 3. Calcular Franja Meta
        condiciones_mora = [
            reporte_df['Dias_Atraso'] == 0, 
            reporte_df['Dias_Atraso'].between(1, 30),
            reporte_df['Dias_Atraso'].between(31, 90), 
            reporte_df['Dias_Atraso'].between(91, 180),
            reporte_df['Dias_Atraso'].between(181, 360), 
            reporte_df['Dias_Atraso'] > 360
        ]
        valores_mora = ['AL DIA', '1 A 30', '31 A 90', '91 A 180','181 A 360','MAS DE 360']
        reporte_df['Franja_Meta'] = np.select(condiciones_mora, valores_mora, default='SIN INFO')
        
        # 4. Calcular Franja Cartera
        condiciones_cartera = [
            reporte_df['Dias_Atraso'] == 0, 
            reporte_df['Dias_Atraso'].between(1, 30),
            reporte_df['Dias_Atraso'].between(31, 60), 
            reporte_df['Dias_Atraso'].between(61, 90),
            reporte_df['Dias_Atraso'].between(91, 120), 
            reporte_df['Dias_Atraso'].between(121, 150),
            reporte_df['Dias_Atraso'].between(151, 180), 
            reporte_df['Dias_Atraso'].between(181, 210),
            reporte_df['Dias_Atraso'].between(211, 270), 
            reporte_df['Dias_Atraso'].between(271, 360),
            reporte_df['Dias_Atraso'] > 360
        ]
        valores_cartera = [
            'AL DIA', '1 A 30', '31 A 60', '61 A 90', '91 A 120', '121 A 150',
            '151 A 180', '181 A 210', '211 A 270', '271 A 360', 'MAS DE 360'
        ]
        reporte_df['Franja_Cartera'] = np.select(condiciones_cartera, valores_cartera, default='SIN INFO')
        
        # CORRECCIÓN 3: Llamamos a la función de rangos aquí mismo para que se ejecute
        reporte_df = self.calculate_last_payment_range(reporte_df)

        print("✅ Cálculo de franjas y categorización completado.")
        return reporte_df
    
    def calculate_last_payment_range(self, reporte_df):
        """
        Calcula el rango de tiempo desde el último pago inicial.
        """
        # CORRECCIÓN 2: Nombre exacto de la columna según base_model.py (Mayúsculas importan)
        col_fecha = 'Fecha_Ultimo_Pago_Inicial'  
        
        # Verificamos que la columna exista (intentando con ambas grafías por seguridad)
        if col_fecha not in reporte_df.columns:
            # Intento de fallback por si acaso
            if 'Fecha_Ultimo_pago_Inicial' in reporte_df.columns:
                col_fecha = 'Fecha_Ultimo_pago_Inicial'
            else:
                # Si no está, retornamos sin hacer nada (silencioso para no ensuciar log si no es crítico)
                return reporte_df

        print("📅 Calculando el rango de la fecha de último pago inicial...")
        
        # 1. Aseguramos datetime (usando .copy() para evitar warnings si es una vista)
        fechas = pd.to_datetime(reporte_df[col_fecha], errors='coerce')

        # 2. Definimos referencia (día 5 del mes actual)
        hoy = pd.Timestamp.now()
        fecha_referencia = hoy.replace(day=5)

        # 3. Fechas límite
        fecha_6_meses = fecha_referencia - pd.DateOffset(months=6)
        fecha_12_meses = fecha_referencia - pd.DateOffset(months=12)
        fecha_24_meses = fecha_referencia - pd.DateOffset(months=24)
        fecha_48_meses = fecha_referencia - pd.DateOffset(months=48)

        # 4. Condiciones
        condiciones_pago = [
            fechas > fecha_6_meses,
            fechas.between(fecha_12_meses, fecha_6_meses, inclusive='right'),
            fechas.between(fecha_24_meses, fecha_12_meses, inclusive='right'),
            fechas.between(fecha_48_meses, fecha_24_meses, inclusive='right'),
            (fechas <= fecha_48_meses) & (fechas.notna()) # Asegurar que no tome NaT
        ]
        
        valores_pago = [
            '6 MESES',
            '6 A 12 MESES',
            '1 a 2 AÑOS',
            '2 A 4 AÑOS',
            'MAS 4 AÑOS'
        ]

        # 5. Asignación
        reporte_df['Rango_Ultimo_pago_Inicial'] = np.select(
            condiciones_pago, 
            valores_pago, 
            default='SIN PAGO REGISTRADO'
        )
        
        return reporte_df