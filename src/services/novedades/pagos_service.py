import pandas as pd
import numpy as np

class PagosService:

    def _buscar_comision(self, cumplimiento, franja_col, df_comisiones):
        if df_comisiones is None or df_comisiones.empty:
            return 0
        for index, row in df_comisiones.iterrows():
            limite_inferior = row['Rango_Inferior']
            limite_superior = row['Rango_Superior']
            if pd.isna(limite_superior):
                limite_superior = float('inf')
            if limite_inferior <= cumplimiento < limite_superior:
                return row[franja_col]
        return 0

    def _buscar_comision_tr(self, cumplimiento, recaudo_meta_tr, es_gestor, tabla_recaudo_gestores, tabla_recaudo_cobradores):
        tabla_a_usar = tabla_recaudo_gestores if es_gestor else tabla_recaudo_cobradores
        if tabla_a_usar is None or tabla_a_usar.empty:
            return 0
        columna_valor = 'TTL RECAUDO'
        for index, row in tabla_a_usar.iterrows():
            limite_inferior = row['Rango_Inferior']
            limite_superior = row['Rango_Superior']
            if pd.isna(limite_superior):
                limite_superior = float('inf')
            if limite_inferior <= cumplimiento < limite_superior:
                valor_base = row[columna_valor]
                if es_gestor:
                    return valor_base
                else:
                    return recaudo_meta_tr * valor_base
        return 0

    def generar_reporte_pagos(self, df_analisis_cartera, datos_nomina):
        print("🔄 Generando reporte de pagos completo...")
        
        # --- Limpieza y preparación (Igual que antes) ---
        df_analisis_cartera = df_analisis_cartera.copy()
        columnas_numericas = ['Meta_$', 'Recaudo_Meta', 'Total_Recaudo_Sin_Anti', 'Meta_T.R_$']
        for col in columnas_numericas:
            if col in df_analisis_cartera.columns:
                df_analisis_cartera[col] = pd.to_numeric(df_analisis_cartera[col], errors='coerce').fillna(0)
        
        columnas_texto = ['Zona', 'Regional_Cobro', 'Franja_Meta', 'Cobrador', 'Gestor', 'Credito']
        for col in columnas_texto:
            if col in df_analisis_cartera.columns:
                df_analisis_cartera[col] = df_analisis_cartera[col].astype(str).str.strip().str.upper().replace('NAN', '')

        franjas_validas = ['1 A 30', '31 A 90', '91 A 180', '181 A 360']
        df_filtrado = df_analisis_cartera[df_analisis_cartera['Franja_Meta'].isin(franjas_validas)].copy()
        zonas_a_omitir = ['1CE', 'CEC', 'CL1', 'CL2', 'CL3', 'CL4']
        df_filtrado = df_filtrado[~df_filtrado['Zona'].isin(zonas_a_omitir)]

        # --- Agrupaciones (Igual que antes) ---
        df_agrupado_franjas_zonas = df_filtrado.groupby(['Regional_Cobro', 'Zona', 'Cobrador', 'Franja_Meta']).agg({'Meta_$': 'sum', 'Recaudo_Meta': 'sum'}).reset_index()
        df_agrupado_franjas_gestores = df_filtrado.groupby(['Gestor', 'Franja_Meta']).agg({'Meta_$': 'sum', 'Recaudo_Meta': 'sum'}).reset_index()
        df_unico_credito = df_filtrado.drop_duplicates(subset=['Credito'])
        df_totales_zonas = df_unico_credito.groupby(['Regional_Cobro', 'Zona', 'Cobrador']).agg({'Total_Recaudo_Sin_Anti': 'sum', 'Meta_T.R_$': 'sum'}).reset_index()
        df_totales_gestores = df_unico_credito.groupby(['Gestor']).agg({'Total_Recaudo_Sin_Anti': 'sum', 'Meta_T.R_$': 'sum'}).reset_index()
        gestor_regional_map = df_filtrado.groupby('Gestor')['Regional_Cobro'].unique().apply(lambda x: ' / '.join(sorted(x))).to_dict()

        # --- Pivots (Igual que antes) ---
        df_pivot_zonas = df_agrupado_franjas_zonas.pivot_table(index=['Regional_Cobro', 'Zona', 'Cobrador'], columns='Franja_Meta', values=['Meta_$', 'Recaudo_Meta'], aggfunc='sum', fill_value=0)
        df_pivot_zonas.columns = [f'{val}_{franja}' for val, franja in df_pivot_zonas.columns]
        df_pivot_zonas.reset_index(inplace=True)

        df_pivot_gestores = df_agrupado_franjas_gestores.pivot_table(index=['Gestor'], columns='Franja_Meta', values=['Meta_$', 'Recaudo_Meta'], aggfunc='sum', fill_value=0)
        df_pivot_gestores.columns = [f'{val}_{franja}' for val, franja in df_pivot_gestores.columns]
        df_pivot_gestores.reset_index(inplace=True)

        # --- MODIFICACIÓN IMPORTANTE: AGREGAR 'CC' AL HEADER ---
        print("🏗️ Creando estructura del reporte final...")
        header = [
            ('ZONA', ''), ('REGIONAL', ''), ('NOMBRE', ''), ('CC', ''), 
            ('1 A 30', 'META_$'), ('1 A 30', 'Recaudo_Meta'), ('1 A 30', 'Cumplimiento_%'), ('1 A 30', 'Comision'),
            ('31 A 90', 'META_$'), ('31 A 90', 'Recaudo_Meta'), ('31 A 90', 'Cumplimiento_%'), ('31 A 90', 'Comision'),
            ('91 A 180', 'META_$'), ('91 A 180', 'Recaudo_Meta'), ('91 A 180', 'Cumplimiento_%'), ('91 A 180', 'Comision'),
            ('181 A 360', 'META_$'), ('181 A 360', 'Recaudo_Meta'), ('181 A 360', 'Cumplimiento_%'), ('181 A 360', 'Comision'),
            ('TOTALES', 'Recaudo_Meta_TR'), ('TOTALES', 'META_TR$'), ('TOTALES', 'Cumplimiento_TR%'), ('TOTALES', 'Comision_TR'),
            ('PAGO FINAL', 'BASICO'), ('PAGO FINAL', 'COMISIONES'), ('PAGO FINAL', 'TOTAL_PAGAR')
        ]
        franjas_map = {'1 A 30': '1 A 30', '31 A 90': '31 A 90', '91 A 180': '91 A 180', '181 A 360': '181 A 360'}
        
        # --- Construcción de df_final ---
        df_zonas_final = pd.merge(df_pivot_zonas, df_totales_zonas, on=['Regional_Cobro', 'Zona', 'Cobrador'], how='left')
        df_gestores_final = pd.merge(df_pivot_gestores, df_totales_gestores, on=['Gestor'], how='left')
        df_gestores_final['Regional_Cobro'] = df_gestores_final['Gestor'].map(gestor_regional_map)
        
        df_final = pd.concat([df_zonas_final, df_gestores_final], ignore_index=True)
        df_final.rename(columns={'Zona': 'ZONA', 'Regional_Cobro': 'REGIONAL', 'Cobrador': 'NOMBRE_COBRADOR', 'Gestor': 'NOMBRE_GESTOR', 'Total_Recaudo_Sin_Anti': 'Recaudo_Meta_TR', 'Meta_T.R_$': 'META_TR$'}, inplace=True)
        
        # Unificar Nombres
        df_final['NOMBRE'] = df_final['NOMBRE_COBRADOR'].fillna(df_final['NOMBRE_GESTOR'])
        df_final['ZONA'] = df_final['ZONA'].fillna('GESTOR')
        df_final.drop(columns=['NOMBRE_COBRADOR', 'NOMBRE_GESTOR'], inplace=True)

        # --- NUEVO: CRUCE DE CÉDULAS EN EL REPORTE FINAL ---
        print("🆔 Asignando cédulas al reporte final...")
        if datos_nomina and 'CEDULAS' in datos_nomina and not datos_nomina['CEDULAS'].empty:
            df_cedulas = datos_nomina['CEDULAS']
            # Aseguramos mayúsculas para el cruce
            df_final['NOMBRE_JOIN'] = df_final['NOMBRE'].astype(str).str.strip().str.upper()
            
            # Hacemos el Merge
            df_final = pd.merge(df_final, df_cedulas, left_on='NOMBRE_JOIN', right_on='NOMBRE', how='left')
            
            # Limpieza post-merge (df_cedulas trae columna 'NOMBRE' que se duplica como 'NOMBRE_y')
            if 'NOMBRE_y' in df_final.columns:
                df_final.drop(columns=['NOMBRE_y'], inplace=True)
            if 'NOMBRE_x' in df_final.columns:
                df_final.rename(columns={'NOMBRE_x': 'NOMBRE'}, inplace=True)
            
            # Llenamos CC vacías con guión o vacío
            df_final['CC'] = df_final['CC'].fillna('')
        else:
            df_final['CC'] = ''
        
        # --- Mapeo al DataFrame con MultiIndex ---
        df_reporte = pd.DataFrame(columns=pd.MultiIndex.from_tuples(header))
        
        # Columnas de texto incluyendo la nueva CC
        df_reporte[('ZONA', '')] = df_final['ZONA']
        df_reporte[('REGIONAL', '')] = df_final['REGIONAL']
        df_reporte[('NOMBRE', '')] = df_final['NOMBRE']
        df_reporte[('CC', '')] = df_final['CC']  # <--- MAPEAMOS LA DATA A LA COLUMNA

        # --- (Resto del código: Llenado de métricas, cálculos, etc.) ---
        for franja_reporte, franja_pivot in franjas_map.items():
            meta_col, recaudo_col = f'Meta_$_{franja_pivot}', f'Recaudo_Meta_{franja_pivot}'
            df_reporte[(franja_reporte, 'META_$')] = df_final.get(meta_col, 0)
            df_reporte[(franja_reporte, 'Recaudo_Meta')] = df_final.get(recaudo_col, 0)
        
        df_reporte[('TOTALES', 'Recaudo_Meta_TR')] = df_final.get('Recaudo_Meta_TR', 0)
        df_reporte[('TOTALES', 'META_TR$')] = df_final.get('META_TR$', 0)
        df_reporte = df_reporte.fillna(0)
        
        # Cálculos de porcentajes
        for franja in franjas_map.keys():
            meta = pd.to_numeric(df_reporte[(franja, 'META_$')], errors='coerce')
            recaudo = pd.to_numeric(df_reporte[(franja, 'Recaudo_Meta')], errors='coerce')
            porcentaje_decimal = np.where(meta != 0, recaudo / meta, 0)
            df_reporte[(franja, 'Cumplimiento_%')] = [f"{format(x * 100, '.2f')}%".replace('.', ',') for x in porcentaje_decimal]
        
        meta_tr = pd.to_numeric(df_reporte[('TOTALES', 'META_TR$')], errors='coerce')
        recaudo_tr = pd.to_numeric(df_reporte[('TOTALES', 'Recaudo_Meta_TR')], errors='coerce')
        porcentaje_tr = np.where(meta_tr != 0, recaudo_tr / meta_tr, 0)
        df_reporte[('TOTALES', 'Cumplimiento_TR%')] = [f"{format(x * 100, '.2f')}%".replace('.', ',') for x in porcentaje_tr]

        # Cálculos de comisiones
        print("💰 Calculando comisiones...")
        if datos_nomina:
            tabla_com_gestores = datos_nomina['GESTORES']['Comisiones']
            tabla_com_cobradores = datos_nomina['COBRADORES']['Comisiones']
            mapa_franjas_comision = {'1 A 30': '1-30', '31 A 90': '31-90', '91 A 180': '91-180', '181 A 360': '181-360'}
            for franja_reporte, franja_comision in mapa_franjas_comision.items():
                cumplimiento_numerico = df_reporte[(franja_reporte, 'Cumplimiento_%')].str.replace('%', '').str.replace(',', '.').astype(float) / 100
                comisiones_calculadas = [self._buscar_comision(cumplimiento_numerico[idx], franja_comision, tabla_com_gestores if row[('ZONA', '')] == 'GESTOR' else tabla_com_cobradores) for idx, row in df_reporte.iterrows()]
                df_reporte[(franja_reporte, 'Comision')] = comisiones_calculadas
            
            tabla_rec_gestores = datos_nomina['GESTORES']['Recaudo']
            tabla_rec_cobradores = datos_nomina['COBRADORES']['Recaudo']
            cumplimiento_tr_numerico = df_reporte[('TOTALES', 'Cumplimiento_TR%')].str.replace('%', '').str.replace(',', '.').astype(float) / 100
            comisiones_tr_calculadas = [self._buscar_comision_tr(cumplimiento_tr_numerico[idx], row[('TOTALES', 'Recaudo_Meta_TR')], row[('ZONA', '')] == 'GESTOR', tabla_rec_gestores, tabla_rec_cobradores) for idx, row in df_reporte.iterrows()]
            df_reporte[('TOTALES', 'Comision_TR')] = comisiones_tr_calculadas
        else:
            for franja_reporte in franjas_map.keys():
                df_reporte[(franja_reporte, 'Comision')] = 0
            df_reporte[('TOTALES', 'Comision_TR')] = 0

        # Pago Final
        print("💵 Calculando pago final...")
        columnas_comision_franjas = [col for col in df_reporte.columns if col[1] == 'Comision']
        df_reporte[('PAGO FINAL', 'COMISIONES')] = df_reporte[columnas_comision_franjas].sum(axis=1) + df_reporte[('TOTALES', 'Comision_TR')]
        
        basico_primario = 1423500
        df_reporte[('PAGO FINAL', 'BASICO')] = basico_primario
        
        for idx, row in df_reporte[df_reporte[('ZONA', '')] == 'GESTOR'].iterrows():
            nombre_gestor = row[('NOMBRE', '')]
            if nombre_gestor in ['JENNY ORDOÑEZ', 'LEONARDO CEBALLOS']:
                basico_garantizado = 1600000 if nombre_gestor == 'JENNY ORDOÑEZ' else 2200000
                base_calculo = 1600000 if nombre_gestor == 'LEONARDO CEBALLOS' else basico_primario
                total_temp = base_calculo + row[('PAGO FINAL', 'COMISIONES')]
                nueva_comision = total_temp - basico_garantizado
                df_reporte.loc[idx, ('PAGO FINAL', 'COMISIONES')] = max(0, nueva_comision)
                df_reporte.loc[idx, ('PAGO FINAL', 'BASICO')] = basico_garantizado
            elif nombre_gestor == 'DARVIS IDROBO':
                cumplimiento_31_90 = float(row[('31 A 90', 'Cumplimiento_%')].replace('%', '').replace(',', '.'))
                basico_darbis = 2000000 if cumplimiento_31_90 > 95 else 1800000
                df_reporte.loc[idx, ('PAGO FINAL', 'BASICO')] = basico_darbis
        
        df_reporte[('PAGO FINAL', 'TOTAL_PAGAR')] = df_reporte[('PAGO FINAL', 'BASICO')] + df_reporte[('PAGO FINAL', 'COMISIONES')]

        # Ordenamiento
        print("📊 Ordenando reporte final...")
        df_reporte['sort_key_gestor'] = np.where(df_reporte[('ZONA', '')] == 'GESTOR', 1, 0)
        all_regionals = df_reporte[('REGIONAL', '')].unique()
        regionals_to_group = ['SANTANDER', 'VALLE', 'SANTANDER / VALLE']
        other_regionals = sorted([r for r in all_regionals if r not in regionals_to_group])
        custom_order = other_regionals + regionals_to_group
        df_reporte['sort_key_regional'] = pd.Categorical(df_reporte[('REGIONAL', '')], categories=custom_order, ordered=True)
        df_reporte = df_reporte.sort_values(by=['sort_key_regional', 'sort_key_gestor', ('ZONA', '')]).reset_index(drop=True)
        df_reporte.drop(columns=['sort_key_gestor', 'sort_key_regional'], inplace=True)

        # Formato Moneda
        print("💰 Aplicando formato de moneda...")
        columnas_moneda = [
            ('1 A 30', 'META_$'), ('1 A 30', 'Recaudo_Meta'), ('1 A 30', 'Comision'),
            ('31 A 90', 'META_$'), ('31 A 90', 'Recaudo_Meta'), ('31 A 90', 'Comision'),
            ('91 A 180', 'META_$'), ('91 A 180', 'Recaudo_Meta'), ('91 A 180', 'Comision'),
            ('181 A 360', 'META_$'), ('181 A 360', 'Recaudo_Meta'), ('181 A 360', 'Comision'),
            ('TOTALES', 'Recaudo_Meta_TR'), ('TOTALES', 'META_TR$'), ('TOTALES', 'Comision_TR'),
            ('PAGO FINAL', 'BASICO'), ('PAGO FINAL', 'COMISIONES'), ('PAGO FINAL', 'TOTAL_PAGAR')
        ]
        for col in columnas_moneda:
            if col in df_reporte.columns:
                df_reporte[col] = pd.to_numeric(df_reporte[col], errors='coerce').fillna(0)
                df_reporte[col] = df_reporte[col].apply(lambda x: f"$ {int(round(x, 0)):,}".replace(',', '.'))
        
        print("✅ Reporte final generado con CÉDULAS.")
        return df_reporte