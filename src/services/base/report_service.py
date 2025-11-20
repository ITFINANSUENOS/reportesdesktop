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
        asesores_sheets = dataframes_por_tipo.get("ASESORES", [])

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
            reporte_final['Zona'] = reporte_final['Zona'].astype(str).str.strip()
            matriz_cartera_df['Zona'] = matriz_cartera_df['Zona'].astype(str).str.strip()
            reporte_final = pd.merge(reporte_final, matriz_cartera_df.drop_duplicates('Zona'), on='Zona', how='left')
        if asesores_sheets:
            # Primero obtenemos todos los códigos de vendedor activos
            codigos_activos = []
            for item in asesores_sheets:
                if 'Codigo_Vendedor' in item["data"].columns:
                    # Convertimos a string, eliminamos espacios y decimales (.0)
                    codigos = item["data"]['Codigo_Vendedor'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
                    codigos_activos.extend(codigos.dropna().unique())
            # Convertimos a set para eliminar duplicados
            codigos_activos = set(codigos_activos)
            print(f"🔍 Total de vendedores activos encontrados: {len(codigos_activos)}")
            # 2. Preparamos la columna Codigo_Vendedor en el reporte para comparar
            reporte_final['Codigo_Vendedor_clean'] = (
                reporte_final['Codigo_Vendedor']
                .astype(str)
                .str.strip()
                .str.replace(r'\.0$', '', regex=True)
            )
            # 3. Creamos la columna Vendedor_Activo
            reporte_final['Vendedor_Activo'] = np.where(
                reporte_final['Codigo_Vendedor_clean'].isin(codigos_activos),
                'ACTIVO',
                'INACTIVO'
            )
            # 4. Eliminamos la columna temporal
            reporte_final.drop('Codigo_Vendedor_clean', axis=1, inplace=True)
    
            for item in asesores_sheets:
                info_df = item["data"]
                merge_key = item["config"]["merge_on"]
                if not info_df.empty and merge_key in reporte_final.columns:
                    # Convertir a string y eliminar decimales para la columna Codigo_Vendedor
                    info_df[merge_key] = pd.to_numeric(info_df[merge_key], errors='coerce').fillna(0).astype('int64').astype(str)
                    reporte_final[merge_key] = pd.to_numeric(reporte_final[merge_key], errors='coerce').fillna(0).astype('int64').astype(str)
                    # Asegurar el mismo formato en el reporte_final
                    reporte_final[merge_key] = reporte_final[merge_key].astype(str).str.replace(r'\.0$', '', regex=True)
                    reporte_final[merge_key] = reporte_final[merge_key].str.strip()
                    reporte_final = pd.merge(reporte_final, info_df.drop_duplicates(subset=merge_key), 
                                        on=merge_key, how='left')
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