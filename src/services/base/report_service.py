import pandas as pd
import numpy as np

from src.services.base.dataloader_service import DataLoaderService
from src.services.base.creditdetails_service import CreditDetailsService
from src.services.base.product_service import ProductsSalesService
from src.services.base.dataprocessor_service import ReportProcessorService
from src.services.base.metrics_calculation_service import MetricsCalculationService
from src.services.base.categorization_service import CategorizationService
from src.services.base.data_cleaning_service import DataCleaningService

class ReportService:
    """
    Servicio principal que orquesta la generación del reporte consolidado,
    utilizando los servicios especializados.
    """
    def __init__(self, config):
        self.config = config
        self.data_loader = DataLoaderService(config)
        self.credit_details = CreditDetailsService()
        self.products_sales = ProductsSalesService()
        self.report_processor = ReportProcessorService(config)
        self.metrics_service = MetricsCalculationService()
        self.categorization_service = CategorizationService()
        self.cleaning_service = DataCleaningService()

    def generate_consolidated_report(self, file_paths, orden_columnas, start_date=None, end_date=None, dataframes_preloaded=None):
        """
        Orquesta todo el proceso de ETL con la arquitectura correcta y de mejor rendimiento.
        """
        if dataframes_preloaded:
            print("\n⚙️  Usando dataframes precargados desde el modo de actualización...")
            dataframes_por_tipo = dataframes_preloaded
        else:
            print("\n⚙️  Cargando dataframes desde archivos...")
            dataframes_por_tipo = self.data_loader.load_dataframes(file_paths)

        # 2. Preparar dataframes individuales
        print("\n🔗 Limpiando y estandarizando llaves de todos los archivos...")
        r91_df = self.data_loader.create_credit_key(self.data_loader.safe_concat(dataframes_por_tipo.get("R91", [])))
        analisis_df = self.data_loader.create_credit_key(self.data_loader.safe_concat(dataframes_por_tipo.get("ANALISIS", [])))
        vencimientos_df = self.data_loader.create_credit_key(self.data_loader.safe_concat(dataframes_por_tipo.get("VENCIMIENTOS", [])))
        
        if not vencimientos_df.empty:
            print("\n📞 Procesando lógica de teléfonos para VENCIMIENTOS...")
            vencimientos_df = self.cleaning_service.unificar_telefonos_codeudores(
                vencimientos_df, 
                col_principal='Celular', 
                col_secundaria='Celular2',
                col_destino='Celular',
                valor_defecto='',
                solo_10_digitos=True
            )
        
        crtmp_df = self.data_loader.create_credit_key(self.data_loader.safe_concat(dataframes_por_tipo.get("CRTMPCONSULTA1", [])))
        fnz003_df = self.data_loader.create_credit_key(self.data_loader.safe_concat(dataframes_por_tipo.get("FNZ003", [])))
        sc04_df = self.data_loader.safe_concat(dataframes_por_tipo.get("SC04", []))
        fnz001_df = self.data_loader.create_credit_key(self.data_loader.safe_concat(dataframes_por_tipo.get("FNZ001", [])))
        r03_df = self.data_loader.create_credit_key(self.data_loader.safe_concat(dataframes_por_tipo.get("R03", [])))
        
        if not r03_df.empty:
            print("\n📞 Procesando lógica especial de teléfonos para R03...")
            r03_df = self.cleaning_service.unificar_telefonos_codeudores(
                r03_df, 
                col_principal='Telefono_Codeudor1', 
                col_secundaria='Movil_Codeudor1',    
                col_destino='Telefono_Codeudor1'
            )
            r03_df = self.cleaning_service.unificar_telefonos_codeudores(
                r03_df, 
                col_principal='Telefono_Codeudor2',
                col_secundaria='Movil_Codeudor2',   
                col_destino='Telefono_Codeudor2'
            )
            
        matriz_cartera_df = self.data_loader.safe_concat(dataframes_por_tipo.get("MATRIZ_CARTERA", []))
        metas_franjas_df = self.data_loader.safe_concat(dataframes_por_tipo.get("METAS_FRANJAS", []))
        asesores_sheets_data = dataframes_por_tipo.get("ASESORES", [])

        # ✨ Consolidar créditos duplicados (mismo crédito, mismo cliente)
        if not r91_df.empty:
            print("\n consolidating duplicate credits from R91...")
            
            # Columnas que se deben sumar
            columnas_a_sumar = [
                'Meta_Intereses', 'Meta_DC_Al_Dia', 'Meta_DC_Atraso',
                'Meta_Saldo', 'Meta_Atraso'
            ]
            # Columnas por las que se agrupará
            columnas_agrupacion = ['Credito', 'Cedula_Cliente']            
            # Asegurarnos de que las columnas a sumar existan en el DataFrame
            columnas_a_sumar_existentes = [col for col in columnas_a_sumar if col in r91_df.columns]
            # Crear el diccionario de agregación dinámicamente
            agg_dict = {col: 'sum' for col in columnas_a_sumar_existentes}
            # Para el resto de las columnas, mantener el primer valor
            for col in r91_df.columns:
                if col not in columnas_agrupacion and col not in columnas_a_sumar_existentes:
                    agg_dict[col] = 'first'
            # Aplicar el groupby y la agregación
            r91_df = r91_df.groupby(columnas_agrupacion, as_index=False).agg(agg_dict)
            print(f"✅ R91 consolidado. Total de registros únicos: {len(r91_df)}")
            
        if r91_df.empty: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
        reporte_final = r91_df.copy()
        print(f"📄 Reporte base creado con {len(reporte_final)} registros de R91 (sin eliminar duplicados).")
        
        # 3. Procesar vencimientos
        processed_vencimientos, negativos_vencimientos = self.credit_details.process_vencimientos_data(vencimientos_df)
        
        # 4. Unir datos al reporte base
        print("\n🔍 Uniendo resúmenes de información al reporte base...")
        if not processed_vencimientos.empty:
            reporte_final = pd.merge(reporte_final, processed_vencimientos, on='Credito', how='left')
        if not analisis_df.empty:
             reporte_final = pd.merge(reporte_final, analisis_df.drop_duplicates('Credito'), on='Credito', how='left', suffixes=('', '_Analisis'))
        if not r03_df.empty:
            reporte_final = pd.merge(reporte_final, r03_df.drop_duplicates('Credito'), on='Credito', how='left', suffixes=('', '_R03'))
            
        if not matriz_cartera_df.empty:
            print("\n🔍 Uniendo Matriz de Cartera por Zona y Credito...")
            reporte_final['Zona'] = reporte_final['Zona'].astype(str).str.strip()
            matriz_cartera_df['Zona'] = matriz_cartera_df['Zona'].astype(str).str.strip()
            matriz_cartera_df['Credito'] = (
                matriz_cartera_df['Credito']
                .astype(str)
                .str.strip()
                .str.replace(r'\.0$', '', regex=True)
            )
            reporte_final = pd.merge(
                reporte_final, 
                matriz_cartera_df.drop_duplicates(subset=['Zona', 'Credito']), 
                on=['Zona', 'Credito'], 
                how='left'
            )

        # --- LÓGICA DE ASESORES ---
        if asesores_sheets_data:
            print("\n🔍 Procesando archivo de Asesores (Multi-hoja)...")
            
            for i, item in enumerate(asesores_sheets_data):
                # 1. VALIDACIÓN DE ESTRUCTURA (Anti-Crash)
                # Si por alguna razón el DataLoader devolvió solo un DataFrame (sin config), lo saltamos o manejamos
                if not isinstance(item, dict):
                    print(f"⚠️ Advertencia: El item #{i} no es un diccionario válido. Saltando.")
                    continue

                # 2. EXTRACCIÓN SEGURA (Soluciona KeyError 'sheet_name')
                # Usamos .get() para que nunca falle si falta la llave
                config_item = item.get('config', {})
                df_hoja = item.get('data')
                
                # Extraemos el nombre desde 'config', no desde 'item'
                nombre_hoja = config_item.get('sheet_name', 'DESCONOCIDO')
                col_merge_config = config_item.get('merge_on')

                # Validaciones básicas
                if df_hoja is None or df_hoja.empty:
                    print(f"⚠️ La hoja '{nombre_hoja}' está vacía o no se cargó.")
                    continue
                
                if not col_merge_config:
                    print(f"⚠️ Saltando {nombre_hoja}: No tiene configuración 'merge_on'.")
                    continue

                # CASO 1: HOJA PRINCIPAL DE ASESORES
                if nombre_hoja == "ASESORES":
                    print(f"   ⚡ Aplicando lógica de Vendedor Activo a: {nombre_hoja}")
                    
                    # Verificar que la columna exista antes de operar
                    if col_merge_config not in df_hoja.columns:
                        print(f"❌ Error: Columna '{col_merge_config}' no encontrada en Excel.")
                        continue

                    # 3. LIMPIEZA DE LLAVE (Soluciona 'float has no len' indirectamente)
                    # Convertimos a string primero para quitar espacios, luego a numérico
                    # Esto evita errores si Windows leyó la columna como Texto con espacios o Float
                    try:
                        df_hoja[col_merge_config] = (
                            pd.to_numeric(df_hoja[col_merge_config], errors='coerce')
                            .fillna(0).astype(int)
                        )
                    except Exception as e:
                        print(f"❌ Error convirtiendo llave en {nombre_hoja}: {e}")
                        continue

                    # Calcular Vendedor Activo
                    codigos_activos = set(df_hoja[col_merge_config].unique())
                    print(f"      -> {len(codigos_activos)} vendedores activos detectados.")

                    # Preparar llave en el Reporte
                    col_temp_reporte = f"{col_merge_config}_Clean_Int"
                    reporte_final[col_temp_reporte] = (
                        pd.to_numeric(reporte_final[col_merge_config], errors='coerce')
                        .fillna(0).astype(int)
                    )

                    # Asignar estado
                    reporte_final['Vendedor_Activo'] = np.where(
                        reporte_final[col_temp_reporte].isin(codigos_activos),
                        'ACTIVO', 'INACTIVO'
                    )

                    # Merge
                    df_hoja = df_hoja.drop_duplicates(subset=[col_merge_config])
                    reporte_final = pd.merge(
                        reporte_final,
                        df_hoja,
                        left_on=col_temp_reporte,
                        right_on=col_merge_config,
                        how='left',
                        suffixes=('', '_Maestro')
                    )
                    
                    # Limpieza de columnas temporales
                    reporte_final.drop(col_temp_reporte, axis=1, inplace=True)
                    if f'{col_merge_config}_Maestro' in reporte_final.columns:
                        reporte_final.drop(f'{col_merge_config}_Maestro', axis=1, inplace=True)

                # CASO 2: OTRAS HOJAS (Centro Costos, etc.)
                else:
                    print(f"   🔗 Cruzando hoja auxiliar: {nombre_hoja}")
                    
                    if col_merge_config in reporte_final.columns:
                        # Limpieza Excel
                        df_hoja[col_merge_config] = (
                            pd.to_numeric(df_hoja[col_merge_config], errors='coerce')
                            .fillna(0).astype(int)
                        )
                        
                        # Limpieza Reporte
                        col_temp_reporte = f"{col_merge_config}_Temp_Merge"
                        reporte_final[col_temp_reporte] = (
                            pd.to_numeric(reporte_final[col_merge_config], errors='coerce')
                            .fillna(0).astype(int)
                        )

                        # Merge
                        df_hoja = df_hoja.drop_duplicates(subset=[col_merge_config])
                        reporte_final = pd.merge(
                            reporte_final,
                            df_hoja,
                            left_on=col_temp_reporte,
                            right_on=col_merge_config,
                            how='left',
                            suffixes=('', '_Aux')
                        )
                        
                        # Limpieza
                        reporte_final.drop(col_temp_reporte, axis=1, inplace=True)
                        if f'{col_merge_config}_Aux' in reporte_final.columns:
                            reporte_final.drop(f'{col_merge_config}_Aux', axis=1, inplace=True)
                    else:
                        print(f"      ⚠️ No se pudo cruzar {nombre_hoja}: Falta la columna {col_merge_config} en los datos base.")
        else:
             print("⚠️ Advertencia: No se cargó información de ASESORES.")
             reporte_final['Vendedor_Activo'] = 'SIN INFO'
            
        # 5. Aplicar transformaciones
        print("\n🚀 Iniciando transformaciones finales...")
        reporte_final['Empresa'] = np.where(reporte_final['Tipo_Credito'] == 'DF', 'FINANSUEÑOS', 'ARPESOD')
        
        reporte_final = self.products_sales.assign_sales_invoice(reporte_final, crtmp_df)
        reporte_final = self.products_sales.add_product_details(reporte_final, crtmp_df)
        reporte_final = self.credit_details.enrich_credit_details(reporte_final, sc04_df, fnz001_df)
        reporte_final = self.credit_details.clean_installment_data(reporte_final)
        reporte_final = self.categorization_service.map_call_center_data(reporte_final)
        reporte_final, negativos_fnz003 = self.metrics_service.calculate_balances(reporte_final, fnz003_df)
        reporte_final = self.metrics_service.calculate_goal_metrics(reporte_final, metas_franjas_df)
        reporte_final = self.credit_details.adjust_arrears_status(reporte_final)
        reporte_final = self.report_processor.filter_by_date_range(reporte_final, start_date, end_date)
        reporte_final, df_a_corregir = self.report_processor.finalize_report(reporte_final, orden_columnas)
        reporte_final = self.cleaning_service.run_cleaning_pipeline(reporte_final)
        
        reporte_negativos_final = pd.DataFrame() 
        lista_de_negativos = [df for df in [negativos_vencimientos, negativos_fnz003] if not df.empty]

        if lista_de_negativos:
            print("📊 Unificando reportes de créditos con valores negativos...")
            # Unimos todas las listas de créditos negativos
            todos_los_negativos = pd.concat(lista_de_negativos, ignore_index=True)
            # Preparamos la información de clientes del reporte final para el cruce
            info_clientes = reporte_final[['Credito', 'Cedula_Cliente', 'Nombre_Cliente']].drop_duplicates(subset=['Credito'])
            reporte_negativos_final = pd.merge(
                todos_los_negativos[['Credito', 'Observacion']].drop_duplicates(), 
                info_clientes, 
                on='Credito', 
                how='left'
            )
            # Seleccionamos y ordenamos las columnas finales para el reporte
            columnas_finales_negativos = ['Credito', 'Cedula_Cliente', 'Nombre_Cliente', 'Observacion']
            # Nos aseguramos que todas las columnas existan antes de seleccionarlas
            columnas_existentes = [col for col in columnas_finales_negativos if col in reporte_negativos_final.columns]
            reporte_negativos_final = reporte_negativos_final[columnas_existentes].drop_duplicates()
            
        return reporte_final, reporte_negativos_final, df_a_corregir