import pandas as pd
import numpy as np
from typing import Dict
from src.models.convenios_model import ConveniosConfig

class DataProcessor:
    """Contiene toda la lógica de negocio para procesar y transformar los datos."""

    BANCOLOMBIA_SHEET_NAME = 'PAGOS BANCOLOMBIA'
    EFECTY_SHEET_NAME = 'PAGOS EFECTY'
    ECOLLECT_SHEET_NAME = 'PAGOS ECOLLECT'

    def __init__(self, config: ConveniosConfig):
        self.config = config

    def process_payment_type(self, dfs: Dict[str, pd.DataFrame], payment_type: str) -> pd.DataFrame:
        """Orquesta el procesamiento para un tipo de pago (Bancolombia, Efecty o Ecollect)."""
        
        # Selección dinámica de la hoja según el tipo
        if payment_type == 'bancolombia':
            payment_df_name = self.BANCOLOMBIA_SHEET_NAME
        elif payment_type == 'efecty':
            payment_df_name = self.EFECTY_SHEET_NAME
        elif payment_type == 'ecollect':
            payment_df_name = self.ECOLLECT_SHEET_NAME
        else:
            print(f"Tipo de pago desconocido: {payment_type}")
            return pd.DataFrame()
        
        if payment_df_name not in dfs or dfs[payment_df_name].empty:
            print(f"DEBUG: Hoja '{payment_df_name}' está vacía o no se encontró. No se procesará.")
            return pd.DataFrame()

        df = dfs[payment_df_name].copy()
        
        print(f"\n--- Iniciando proceso para: {payment_type.upper()} ---")
        print(f"Paso 0: Filas iniciales: {len(df)}")
        
        df = self._perform_merges(df, dfs, payment_type)
        print(f"Paso 1: Filas después de TODOS los merges: {len(df)}")

        df = self._calculate_final_columns(df)
        print(f"Paso 2: Filas después de calcular columnas: {len(df)}")

        df = self._cleanup_dataframe(df)
        print(f"Paso 3: Filas después de la limpieza final: {len(df)}")
        print("--------------------------------------------------")

        return df

    def _perform_merges(self, df: pd.DataFrame, dfs: Dict, payment_type: str) -> pd.DataFrame:
        """Realiza todas las fusiones de datos necesarias."""
        merge_conf = self.config.merge_config[payment_type]

        # Fusiones iniciales
        df = self._merge_dataframes(df, dfs['EMPLEADOS ACTUALES'], *merge_conf['empleados'])
        df = self._merge_dataframes(df, dfs['AC FS'], *merge_conf['ac_fs'])
        df = self._merge_dataframes(df, dfs['AC ARP'], *merge_conf['ac_arp'])

        # Conteo y fusión de cuentas para cada tipo
        for ac_type in ['FS', 'ARP']:
            key_col_name = self.config.merge_config[payment_type][f'ac_{ac_type.lower()}'][0]
            id_col_name = f'CEDULA_{ac_type}'
            count_col_name = f'CANTIDAD CUENTAS {ac_type}'
            
            counts_df = self._count_accounts(dfs[f'AC {ac_type}'], id_col_name, count_col_name)
            df = self._merge_dataframes(df, counts_df, left_on=key_col_name, right_on=id_col_name, how='left')
            df[count_col_name] = df[count_col_name].fillna(0).astype(int)

        # Determinar Factura Final
        df['TOTAL_CUENTAS'] = df['CANTIDAD CUENTAS FS'] + df['CANTIDAD CUENTAS ARP']
        factura_original = np.where(df['FACTURA_FS'].notna(), df['FACTURA_FS'], df['FACTURA_ARP'])
        df['FACTURA FINAL'] = np.where(df['TOTAL_CUENTAS'] > 1, 'Mas de una cartera', factura_original).astype(str)
        df['FACTURA FINAL'].replace('nan', 'SIN CARTERA', inplace=True)
        
        # Eliminar duplicados basándose en las columnas originales del archivo de pago
        # Nota: Usamos la lógica dinámica para detectar el nombre de la hoja original
        original_sheet_name = ''
        if payment_type == 'bancolombia': original_sheet_name = self.BANCOLOMBIA_SHEET_NAME
        elif payment_type == 'efecty': original_sheet_name = self.EFECTY_SHEET_NAME
        elif payment_type == 'ecollect': original_sheet_name = self.ECOLLECT_SHEET_NAME
        
        df.drop_duplicates(subset=list(dfs[original_sheet_name].columns), keep='first', inplace=True)

        # Fusión de saldos unificados
        df_saldos_unificados = pd.concat([
            dfs['AC FS'][['FACTURA_FS', 'SALDO_FS', 'CENTRO_COSTO_FS']].rename(columns={'FACTURA_FS': 'FACTURA', 'SALDO_FS': 'SALDO', 'CENTRO_COSTO_FS': 'CENTRO COSTO'}),
            dfs['AC ARP'][['FACTURA_ARP', 'SALDO_ARP', 'CENTRO_COSTO_ARP']].rename(columns={'FACTURA_ARP': 'FACTURA', 'SALDO_ARP': 'SALDO', 'CENTRO_COSTO_ARP': 'CENTRO COSTO'})
        ], ignore_index=True).drop_duplicates(subset='FACTURA')
        df = self._merge_dataframes(df, df_saldos_unificados, left_on='FACTURA FINAL', right_on='FACTURA')

        # Fusión con casa de cobranza y codeudores
        casa_cobranza_sin_duplicados = dfs['CASA DE COBRANZA'].drop_duplicates(subset=[merge_conf['casa_cobranza'][1]])
        df = self._merge_dataframes(df, casa_cobranza_sin_duplicados, *merge_conf['casa_cobranza'])
        df = self._merge_dataframes(df, dfs['CODEUDORES'], *merge_conf['codeudores'])

        return df

    def _calculate_final_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula todas las columnas derivadas para el reporte final."""
        # ECOLLECT suele usar 'VALOR' (mayúscula) mientras otros usan 'Valor'. Normalizamos si es necesario.
        if 'VALOR' in df.columns and 'Valor' not in df.columns:
             df.rename(columns={'VALOR': 'Valor'}, inplace=True)

        df.rename(columns={'SALDO': 'SALDOS'}, inplace=True)
        df['SALDOS'] = pd.to_numeric(df['SALDOS'], errors='coerce').fillna(0)
        df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce').fillna(0)
        df.loc[df['FACTURA FINAL'] == 'Mas de una cartera', 'SALDOS'] = 0

        df['VALIDACION ULTIMO SALDO'] = np.where((df['SALDOS'] - df['Valor']) <= 0, 'pago total', (df['SALDOS'] - df['Valor']).astype(str))
        
        df['EMPLEADO'] = df['ESTADO_EMPLEADO'].fillna('NO')
        df['CASA COBRANZA'] = df['CASA COBRANZA'].fillna('SIN CASA DE COBRANZA')
        df['CODEUDOR'] = df['CODEUDOR'].fillna('SIN CODEUDOR')

        novedad_conds = [df['CASA COBRANZA'] != 'SIN CASA DE COBRANZA', df['CODEUDOR'] != 'SIN CODEUDOR', df['VALIDACION ULTIMO SALDO'] == 'pago total']
        novedad_vals = [df['CASA COBRANZA'], 'Codeudor:' + df['CODEUDOR'], 'Pago total']
        df['Novedad'] = np.select(novedad_conds, novedad_vals, default='Sin novedad')

        empresa_conds = [
            (df['FACTURA FINAL'] != 'SIN CARTERA') & df['FACTURA FINAL'].str.startswith('DF', na=False),
            (df['FACTURA FINAL'] != 'SIN CARTERA') & ~df['FACTURA FINAL'].str.startswith('DF', na=False),
            (df['FACTURA FINAL'] == 'SIN CARTERA') & (df['CODEUDOR'] != 'SIN CODEUDOR') & df['CODEUDOR'].str.startswith('DF', na=False),
            (df['FACTURA FINAL'] == 'SIN CARTERA') & (df['CODEUDOR'] != 'SIN CODEUDOR') & ~df['CODEUDOR'].str.startswith('DF', na=False)
        ]
        df['Empresa'] = np.select(empresa_conds, ['Finansueños', 'Arpesod', 'Finansueños', 'Arpesod'], default='')

        df['Valor Aplicar'] = np.where((df['VALIDACION ULTIMO SALDO'] == 'pago total') & (df['SALDOS'] != 0), df['SALDOS'], df['Valor'])
        
        dif_aprovechamiento = df['Valor'] - df['SALDOS']
        df['Valor Aprovechamientos'] = np.where((dif_aprovechamiento > 0) & (dif_aprovechamiento <= 10000), dif_aprovechamiento, 0)
        
        dif_anticipo = df['Valor'] - df['Valor Aplicar']
        df['Valor Anticipos'] = np.where(dif_anticipo >= 10000, dif_anticipo, 0)

        return df

    def _cleanup_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Elimina columnas temporales y renombra las finales para presentación."""
        cols_to_drop = [
            'ESTADO_EMPLEADO', 'CEDULA_FS', 'FACTURA_FS', 'CEDULA_ARP', 'FACTURA_ARP', 
            'TOTAL_CUENTAS', 'SALDO_FS', 'SALDO_ARP', 'CENTRO_COSTO_FS', 'CENTRO_COSTO_ARP',
            'vincedula', 'FACTURA', 'DOCUMENTO_CODEUDOR', 'FACTURA_x', 'FACTURA_y',
            'CEDULA_FS_x', 'CEDULA_ARP_x', 'CEDULA_FS_y', 'CEDULA_ARP_y'
        ]
        df.drop(columns=[col for col in cols_to_drop if col in df.columns], inplace=True, errors='ignore')
        
        df.rename(columns={
            'FACTURA FINAL': 'Documento Cartera', 'CENTRO COSTO': 'C. Costo',
            'CASA COBRANZA': 'Casa cobranza', 'EMPLEADO': 'Empleado',
            'CANTIDAD CUENTAS ARP': 'Cuentas ARP', 'CANTIDAD CUENTAS FS': 'Cuentas FS'
        }, inplace=True)

        return df

    def _merge_dataframes(self, main_df: pd.DataFrame, to_merge: pd.DataFrame, left_on: str, right_on: str, how: str = 'left'):
        """Realiza un merge entre DataFrames de forma segura."""
        return main_df.merge(to_merge, how=how, left_on=left_on, right_on=right_on)

    def _count_accounts(self, df: pd.DataFrame, id_column: str, count_column_name: str) -> pd.DataFrame:
        """Cuenta ocurrencias en una columna y devuelve un DataFrame."""
        counts = df[id_column].value_counts().reset_index()
        counts.columns = [id_column, count_column_name]
        return counts