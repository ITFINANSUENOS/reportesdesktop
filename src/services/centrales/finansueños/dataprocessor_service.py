import pandas as pd

class FinansuenosDataProcessorService:
    """Clase responsable de todas las transformaciones de datos."""
    def __init__(self, df, ruta_correcciones,column_map=None):
        self.df = df
        self.ruta_correcciones = ruta_correcciones
        self.column_map = column_map

    def run_all_transformations(self):
        """Ejecuta todos los pasos de limpieza y formato en orden."""
        print("Servicio: Ejecutando todas las transformaciones...")
        self._correct_data_from_excel()
        self._update_data_from_sheets()
        self._clean_and_validate_data()
        self._apply_final_formatting()
        print("Servicio: Transformaciones completadas.")
        return self.df

    def _correct_data_from_excel(self):
        """PASO 3: Realiza correcciones desde el archivo Excel."""
        print("  - Corrigiendo desde Excel...")
        # A. Corregir Cédulas
        df_cedulas = pd.read_excel(self.ruta_correcciones, sheet_name='Cedulas a corregir')
        mapa_cedulas = pd.Series(df_cedulas['CEDULA CORRECTA'].astype(str).str.strip().values, index=df_cedulas['CEDULA MAL'].astype(str).str.strip()).to_dict()
        self.df['NUMERO DE IDENTIFICACION'] = self.df['NUMERO DE IDENTIFICACION'].replace(mapa_cedulas)

        # B. Actualizar campos 'CORREGIR'
        df_vinculado = pd.read_excel(self.ruta_correcciones, sheet_name='Vinculado')
        df_vinculado['CODIGO'] = df_vinculado['CODIGO'].astype(str).str.strip()
        df_vinculado = df_vinculado.set_index('CODIGO')
        mapa_vinc = {'NOMBRE COMPLETO':'NOMBRE', 'DIRECCION DE CORRESPONDENCIA':'DIRECCI', 'CORREO ELECTRONICO':'VINEMAIL', 'CELULAR':'TELEFONO'}
        for col_df, col_vinc in mapa_vinc.items():
            mascara = self.df[col_df].astype(str).str.strip().str.contains('CORREGIR', case=False, na=False)
            if mascara.any():
                ids_a_buscar = self.df.loc[mascara, 'NUMERO DE IDENTIFICACION']
                valores_nuevos = ids_a_buscar.map(df_vinculado[col_vinc])
                self.df.loc[mascara, col_df] = valores_nuevos

        # C. Actualizar Tipos de Identificación
        self.df['TIPO DE IDENTIFICACION'] = 1
        df_tipos = pd.read_excel(self.ruta_correcciones, sheet_name='Tipos de identificacion')
        mapa_tipos = pd.Series(df_tipos['CODIGO DATA'].values, index=df_tipos['CEDULA CORRECTA'].astype(str).str.strip()).to_dict()
        self.df['TIPO DE IDENTIFICACION'] = self.df['NUMERO DE IDENTIFICACION'].map(mapa_tipos).combine_first(self.df['TIPO DE IDENTIFICACION'])

    def _update_data_from_sheets(self):
        """PASO 4: Actualiza desde FNZ001 y R05."""
        print("  - Actualizando desde FNZ001 y R05...")
        self.df['NUMERO DE LA CUENTA U OBLIGACION'] = self.df['NUMERO DE LA CUENTA U OBLIGACION'].astype(str).str.replace(' ', '').str.zfill(18)
        
        # A. Procesando FNZ001
        df_fnz = pd.read_excel(self.ruta_correcciones, sheet_name='FNZ001', usecols=['DSM_TP', 'DSM_NUM', 'VLR_FNZ'])
        df_fnz['VLR_FNZ'] = (pd.to_numeric(df_fnz['VLR_FNZ'], errors='coerce').fillna(0)).astype(int)
        df_fnz['llave_base'] = df_fnz['DSM_TP'].astype(str).str.strip() + df_fnz['DSM_NUM'].astype(str).str.strip()
        tabla_fnz = pd.concat([pd.DataFrame({'FACTURA': df_fnz['llave_base'], 'VALOR': df_fnz['VLR_FNZ']}), pd.DataFrame({'FACTURA': df_fnz['llave_base'] + 'C1', 'VALOR': df_fnz['VLR_FNZ']}), pd.DataFrame({'FACTURA': df_fnz['llave_base'] + 'C2', 'VALOR': df_fnz['VLR_FNZ']})])
        tabla_fnz['FACTURA'] = tabla_fnz['FACTURA'].astype(str).str.zfill(18)
        mapa_fnz = pd.Series(tabla_fnz.VALOR.values, index=tabla_fnz.FACTURA).to_dict()
        self.df['VALOR INICIAL'] = self.df['NUMERO DE LA CUENTA U OBLIGACION'].map(mapa_fnz).combine_first(self.df['VALOR INICIAL'])

        # B. Procesando R05
        df_r05 = pd.read_excel(self.ruta_correcciones, sheet_name='R05', usecols=['MCNTIPCRU2', 'MCNNUMCRU2', 'ABONO'])
        df_r05['ABONO'] = pd.to_numeric(df_r05['ABONO'], errors='coerce').fillna(0)
        df_r05['llave_base'] = df_r05['MCNTIPCRU2'].astype(str).str.strip() + df_r05['MCNNUMCRU2'].astype(str).str.strip()
        abonos_sumados = df_r05.groupby('llave_base')['ABONO'].sum().reset_index()

        tabla_r05 = pd.concat([
            pd.DataFrame({'LLAVE': abonos_sumados['llave_base'], 'VALOR_ABONO': abonos_sumados['ABONO']}),
            pd.DataFrame({'LLAVE': abonos_sumados['llave_base'] + 'C1', 'VALOR_ABONO': abonos_sumados['ABONO']}),
            pd.DataFrame({'LLAVE': abonos_sumados['llave_base'] + 'C2', 'VALOR_ABONO': abonos_sumados['ABONO']})
        ])

        # 6. Crear el mapa final: Llave -> Suma Total del Abono
        mapa_r05 = pd.Series(tabla_r05.VALOR_ABONO.values, index=tabla_r05.LLAVE.astype(str).str.ljust(20)).to_dict()
        self.df['VALOR SALDO MORA'] = self.df['NUMERO DE LA CUENTA U OBLIGACION'].map(mapa_r05).combine_first(self.df['VALOR SALDO MORA'])

    def _clean_and_validate_data(self):
        """PASO 5: Realiza limpieza y validaciones generales."""
        print("  - Limpiando y validando datos...")
        # A. Limpieza de caracteres de texto
        letter_replacements = {'Ñ':'N','Á':'A','É':'E','Í':'I','Ó':'O','Ú':'U','Ü':'U','Ÿ':'Y','Â':'A','Ã':'A','š':'S','©':'C','ñ':'N','á':'A','é':'E','í':'I','ó':'O','ú':'U','ü':'U','ÿ':'Y','â':'A','ã':'A'}
        chars_to_remove = ['@','°','|','¬','¡','“','#','$','%','&','/','(',')','=','‘','\\','¿','+','~','´´','´','[','{','^','-','_','.',':',',',';','<','>','Æ','±']
        string_cols = self.df.select_dtypes(include='object').columns.drop('CORREO ELECTRONICO', errors='ignore')
        for col in string_cols:
            self.df[col] = self.df[col].astype(str)
            for old, new in letter_replacements.items(): self.df[col] = self.df[col].str.replace(old, new, regex=False)
            for char in chars_to_remove: self.df[col] = self.df[col].str.replace(char, '', regex=False)
        
        # B. Limpieza y validación de fechas
        for col in ["FECHA APERTURA", "FECHA VENCIMIENTO", "FECHA DE PAGO"]:
            self.df[col] = pd.to_numeric(self.df[col], errors='coerce').fillna(0).astype('Int64').astype(str)
        condicion_fecha_invalida = self.df['FECHA VENCIMIENTO'] < self.df['FECHA APERTURA']
        self.df.loc[condicion_fecha_invalida, 'FECHA VENCIMIENTO'] = self.df['FECHA APERTURA']
        mascara_fecha_pago = (self.df['FECHA DE PAGO'].str.upper().str.contains('NA')) | (self.df['FECHA DE PAGO'] == '0')
        self.df.loc[mascara_fecha_pago, 'FECHA DE PAGO'] = '00000000'

        # C. Limpieza y validación de valores numéricos
        columnas_numericas = ["VALOR INICIAL", "VALOR SALDO DEUDA", "VALOR DISPONIBLE", "V CUOTA MENSUAL", "VALOR SALDO MORA"]
        for col in columnas_numericas:
            self.df[col] = pd.to_numeric(self.df[col], errors='coerce').fillna(0)
            if col != 'VALOR DISPONIBLE':
                self.df.loc[self.df[col] < 10000, col] = 0
        self.df['VALOR DISPONIBLE'] = 0
        self.df[columnas_numericas] = self.df[columnas_numericas].astype(int)

    def _apply_final_formatting(self):
        """PASO 6: Aplica el formato final de texto y longitud."""
        print("  - Aplicando formatos finales...")
        self.df['NOMBRE COMPLETO'] = self.df['NOMBRE COMPLETO'].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip().str.upper()
        replacements_map = {'1118291452':'FANDINO LAYNE ASTRID', '1025529458':'MARTINEZ MUNOZ JOSE MANUEL', '25559122':'RAMIREZ DE CASTRO MARIA ESTELLA'}
        for id_number, new_name in replacements_map.items():
            self.df.loc[self.df['NUMERO DE IDENTIFICACION'] == id_number, 'NOMBRE COMPLETO'] = new_name
        
        col_ciudad = 'CIUDAD CORRESPONDENCIA'
        self.df[col_ciudad] = self.df[col_ciudad].astype(str).fillna('')
        mascara_reemplazo_ciudad = (self.df[col_ciudad].str.strip() == '') | (self.df[col_ciudad].str.strip().str.upper() == 'N/A') | (self.df[col_ciudad].str.strip() == '0')
        self.df.loc[mascara_reemplazo_ciudad, col_ciudad] = 'POPAYAN'

        col_celular = 'CELULAR'
        self.df[col_celular] = self.df[col_celular].astype(str).str.replace(r'\D', '', regex=True)
        es_fijo_valido = (self.df[col_celular].str.len() == 7)
        es_celular_valido = (self.df[col_celular].str.len() == 10) & (self.df[col_celular].str.startswith('3'))
        self.df.loc[~(es_fijo_valido | es_celular_valido), col_celular] = ''
        
        col_email = 'CORREO ELECTRONICO'
        self.df[col_email] = self.df[col_email].astype(str).str.strip()
        placeholders_a_eliminar = ['CORREGIR', 'PENDIENTE', 'NOTIENE', 'SINC', 'NN@', 'AAA@']
        for placeholder in placeholders_a_eliminar:
            self.df.loc[self.df[col_email].str.contains(placeholder, case=False, na=False), col_email] = ''
        email_regex_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        self.df.loc[~self.df[col_email].str.match(email_regex_pattern, na=False), col_email] = ''

        # Formatos de longitud y valores fijos
        self.df['ESTADO ORIGEN DE LA CUENTA'] = '0'
        self.df['RESPONSABLE'] = self.df['RESPONSABLE'].astype(str).str.zfill(2)
        self.df['NOVEDAD'] = self.df['NOVEDAD'].astype(str).str.zfill(2)
        self.df['TOTAL CUOTAS'] = self.df['TOTAL CUOTAS'].astype(str).str.zfill(3)
        self.df['CUOTAS CANCELADAS'] = self.df['CUOTAS CANCELADAS'].astype(str).str.zfill(3)
        self.df['CUOTAS EN MORA'] = self.df['CUOTAS EN MORA'].astype(str).str.zfill(3)
        self.df['FECHA LIMITE DE PAGO'] = self.df['FECHA LIMITE DE PAGO'].astype(str)
        self.df['SITUACION DEL TITULAR'] = '0'
        self.df['EDAD DE MORA'] = self.df['EDAD DE MORA'].astype(str).str.zfill(3)
        self.df['FORMA DE PAGO'] = self.df['FORMA DE PAGO'].astype(str)
        self.df['FECHA ESTADO ORIGEN'] = self.df['FECHA ESTADO ORIGEN'].astype(str)
        self.df['ESTADO DE LA CUENTA'] = self.df['ESTADO DE LA CUENTA'].astype(str).str.zfill(2)
        self.df['FECHA ESTADO DE LA CUENTA'] = self.df['FECHA ESTADO DE LA CUENTA'].astype(str)
        self.df['ADJETIVO'] = '0'
        self.df['FECHA DE ADJETIVO'] = self.df['FECHA DE ADJETIVO'].astype(str).str.zfill(8)
        self.df['CLAUSULA DE PERMANENCIA'] = self.df['CLAUSULA DE PERMANENCIA'].astype(str).str.zfill(3)
        self.df['FECHA CLAUSULA DE PERMANENCIA'] = self.df['FECHA CLAUSULA DE PERMANENCIA'].astype(str).str.zfill(8)
        
        self.df['NOMBRE COMPLETO'] = self.df['NOMBRE COMPLETO'].str.ljust(45)
        self.df['DIRECCION DE CORRESPONDENCIA'] = self.df['DIRECCION DE CORRESPONDENCIA'].astype(str).str.ljust(60)
        self.df['CIUDAD CORRESPONDENCIA'] = self.df[col_ciudad].str.ljust(20)
        self.df['CORREO ELECTRONICO'] = self.df[col_email].str.ljust(60)
        self.df['CELULAR'] = self.df[col_celular].str.zfill(12)
        self.df['NUMERO DE IDENTIFICACION'] = self.df['NUMERO DE IDENTIFICACION'].str.zfill(11)
        self.df['TIPO DE IDENTIFICACION'] = self.df['TIPO DE IDENTIFICACION'].astype(int).astype(str)