import pandas as pd

class FinansuenosDataProcessorService:
    def __init__(self, df, ruta_correcciones, column_mapping):
        self.df = df
        self.ruta_correcciones = ruta_correcciones
        self.map = column_mapping  # Mapa de columnas genéricas a nombres reales

    def run_all_transformations(self):
        print("Servicio: Ejecutando todas las transformaciones...")
        self._correct_data_from_excel()
        self._update_data_from_sheets()
        self._clean_and_validate_data()
        self._apply_final_formatting()
        self._final_cleanup()         
        self._apply_padding_formats()
            
        print("Servicio: Transformaciones completadas.")
        return self.df
    
    def _correct_data_from_excel(self):
        print("  - Corrigiendo desde Excel...")
        # --- Parte A: Corregir Cédulas ---
        # Asegura que la columna de identificación en el DataFrame principal sea texto sin espacios.
        self.df['NUMERO DE IDENTIFICACION'] = self.df['NUMERO DE IDENTIFICACION'].astype(int)
        self.df[self.map['id_number']] = self.df[self.map['id_number']].astype(str).str.strip()

        df_cedulas = pd.read_excel(self.ruta_correcciones, sheet_name='Cedulas a corregir')
        
        # Estandariza las columnas en el archivo de corrección también.
        cedulas_malas = df_cedulas['CEDULA MAL'].astype(str).str.strip()
        cedulas_buenas = df_cedulas['CEDULA CORRECTA'].astype(str).str.strip()
        
        mapa_cedulas = pd.Series(cedulas_buenas.values, index=cedulas_malas).to_dict()
        self.df[self.map['id_number']] = self.df[self.map['id_number']].replace(mapa_cedulas)

        # --- Parte B: Actualizar campos 'CORREGIR' ---
        
        # <-- CORRECCIÓN: Lee el archivo una sola vez.
        df_vinculado = pd.read_excel(self.ruta_correcciones, sheet_name='Vinculado')
        # <-- CORRECCIÓN: Estandariza la columna de código antes de usarla como índice.
        df_vinculado['CODIGO'] = df_vinculado['CODIGO'].astype(str).str.strip()
        df_vinculado = df_vinculado.set_index('CODIGO')
        
        mapa_vinc = {
            self.map['full_name']: 'NOMBRE', 
            self.map['address']: 'DIRECCI', 
            self.map['email']: 'VINEMAIL', 
            self.map['phone']: 'TELEFONO'
        }
        
        for col_df, col_vinc in mapa_vinc.items():
            mascara = self.df[col_df].astype(str).str.strip().str.contains('CORREGIR', case=False, na=False)
            if mascara.any():
                # La columna 'id_number' ya está limpia y corregida gracias a los pasos anteriores.
                ids_a_buscar = self.df.loc[mascara, self.map['id_number']]
                valores_nuevos = ids_a_buscar.map(df_vinculado[col_vinc])
                self.df.loc[mascara, col_df] = valores_nuevos

        # --- Parte C: Actualizar Tipos de Identificación ---
        
        self.df[self.map['id_type']] = 1 # Valor por defecto
        df_tipos = pd.read_excel(self.ruta_correcciones, sheet_name='Tipos de identificacion')
        
        # Estandariza la columna de cédulas en el archivo de tipos.
        cedulas_tipos = df_tipos['CEDULA CORRECTA'].astype(str).str.strip()
        
        mapa_tipos = pd.Series(df_tipos['CODIGO CIFIN'].values, index=cedulas_tipos).to_dict()
        
        # La columna 'id_number' ya está limpia y corregida.
        self.df[self.map['id_type']] = self.df[self.map['id_number']].map(mapa_tipos).combine_first(self.df[self.map['id_type']])
        self.df[self.map['id_type']] = pd.to_numeric(self.df[self.map['id_type']], errors='coerce').astype('Int64').astype(str).str[:2].str.zfill(2)

    def _update_data_from_sheets(self):
        print("  - Actualizando desde FNZ001 y R05...")
        self.df[self.map['account_number']] = self.df[self.map['account_number']].astype(str).str.replace(' ', '').str[:20].str.ljust(20)
        
        df_fnz = pd.read_excel(self.ruta_correcciones, sheet_name='FNZ001', usecols=['DSM_TP', 'DSM_NUM', 'VLR_FNZ'])
        df_fnz['VLR_FNZ'] = (pd.to_numeric(df_fnz['VLR_FNZ'], errors='coerce').fillna(0) / 1000).astype(int)
        df_fnz['llave_base'] = df_fnz['DSM_TP'].astype(str).str.replace(' ', '') + df_fnz['DSM_NUM'].astype(str).str.replace(' ', '')
        tabla_fnz = pd.concat([pd.DataFrame({'FACTURA': df_fnz['llave_base'], 'VALOR': df_fnz['VLR_FNZ']}), pd.DataFrame({'FACTURA': df_fnz['llave_base'] + 'C1', 'VALOR': df_fnz['VLR_FNZ']}), pd.DataFrame({'FACTURA': df_fnz['llave_base'] + 'C2', 'VALOR': df_fnz['VLR_FNZ']})])
        mapa_fnz = pd.Series(tabla_fnz.VALOR.values, index=tabla_fnz.FACTURA.astype(str).str.ljust(20)).to_dict()
        self.df[self.map['initial_value']] = self.df[self.map['account_number']].map(mapa_fnz).combine_first(self.df[self.map['initial_value']])

        # 1. Leer las columnas correctas, incluyendo 'ABONO'
        df_r05 = pd.read_excel(self.ruta_correcciones, sheet_name='R05', usecols=['MCNTIPCRU2', 'MCNNUMCRU2', 'ABONO'])
        df_r05['ABONO'] = pd.to_numeric(df_r05['ABONO'], errors='coerce').fillna(0)
        df_r05['llave_base'] = df_r05['MCNTIPCRU2'].astype(str).str.replace(' ', '') + df_r05['MCNNUMCRU2'].astype(str).str.replace(' ', '')
        abonos_sumados = df_r05.groupby('llave_base')['ABONO'].sum().reset_index()
        abonos_sumados['ABONO'] = (abonos_sumados['ABONO'] / 1000).astype(int)
        # 6. Crear la tabla final con C1 y C2
        tabla_r05 = pd.concat([
            pd.DataFrame({'LLAVE': abonos_sumados['llave_base'], 'VALOR_ABONO': abonos_sumados['ABONO']}),
            pd.DataFrame({'LLAVE': abonos_sumados['llave_base'] + 'C1', 'VALOR_ABONO': abonos_sumados['ABONO']}),
            pd.DataFrame({'LLAVE': abonos_sumados['llave_base'] + 'C2', 'VALOR_ABONO': abonos_sumados['ABONO']})
        ])

        mapa_r05 = pd.Series(tabla_r05.VALOR_ABONO.values, index=tabla_r05.LLAVE.astype(str).str.ljust(20)).to_dict()
        columna_destino_key = 'actual_value_paid' 
        nuevos_valores = self.df[self.map['account_number']].map(mapa_r05).fillna(0).astype(int)
        self.df[self.map[columna_destino_key]] = nuevos_valores
        
        
    def _clean_and_validate_data(self):
        print("  - Limpiando y validando datos...")
        letter_replacements = {'Ñ':'N','Á':'A','É':'E','Í':'I','Ó':'O','Ú':'U','Ü':'U','Ÿ':'Y','Â':'A','Ã':'A','š':'S','©':'C',
                               'ñ':'N','á':'A','é':'E','í':'I','ó':'O','ú':'U','ü':'U','ÿ':'Y','â':'A','ã':'A'}
        
        chars_to_remove = ['@','°','|','¬','¡','“','#','$','%','&','/','(',')','=','‘','\\','¿','+','~','´´','´','[','{','^','-',
                           '_','.',':',',',';','<','>','Æ','±']

        string_cols = self.df.select_dtypes(include='object').columns.drop(self.map['email'], errors='ignore')
        for col in string_cols:
            self.df[col] = self.df[col].astype(str)
            for old, new in letter_replacements.items(): self.df[col] = self.df[col].str.replace(old, new, regex=False)
            for char in chars_to_remove: self.df[col] = self.df[col].str.replace(char, '', regex=False)
        
        for col_name in [self.map['open_date'], self.map['due_date']]:
            self.df[col_name] = pd.to_numeric(self.df[col_name], errors='coerce').fillna(0).astype('Int64').astype(str)
        self.df.loc[self.df[self.map['due_date']] < self.df[self.map['open_date']], self.map['due_date']] = self.df[self.map['open_date']]
        

        numeric_cols_keys = ['initial_value', 'balance_due', 'available_value', 'monthly_fee', 'arrears_value']
        # Obtiene los nombres reales de las columnas desde el mapa
        columnas_numericas = [self.map[k] for k in numeric_cols_keys if k in self.map]

        for col in columnas_numericas:
            self.df[col] = pd.to_numeric(self.df[col], errors='coerce').fillna(0)
            self.df.loc[self.df[col] <= 10, col] = 0
        self.df[columnas_numericas] = self.df[columnas_numericas].astype(int)
        
    def _final_cleanup(self):
        """
        Limpia CUALQUIER valor nulo o texto 'nan' restante en todas las
        columnas no numéricas justo antes de entregar el resultado.
        """
        print("  - Realizando limpieza final de valores nulos...")
        
        # 1. Define tus columnas numéricas para excluirlas
        numeric_keys = ['initial_value', 'balance_due', 'available_value', 'monthly_fee', 'arrears_value', 'actual_value_paid']
        columnas_numericas = [self.map[k] for k in numeric_keys if k in self.map]
        
        # 2. Identifica las columnas de texto a limpiar
        columnas_a_limpiar = self.df.columns.drop(columnas_numericas)
        
        # 3. Itera y limpia cada columna de texto de forma robusta
        for col in columnas_a_limpiar:

            self.df[col] = self.df[col].astype(str).str.strip()
            self.df[col] = self.df[col].replace(r'(?i)^nan$', '', regex=True).fillna('')    
            

    def _apply_final_formatting(self):
        print("  - Aplicando formatos finales...")
        
        col_ciudad = self.map['city']
        self.df[col_ciudad] = self.df[col_ciudad].astype(str).str.strip().str.upper()
        cond_ciudad_invalida = (
            self.df[col_ciudad].isin(['', '0', 'NAN', 'NONE']) |  # Valores vacíos/inválidos
            self.df[col_ciudad].str.isdigit() |                   # Solo números
            self.df[col_ciudad].isnull()                          # Valores nulos
        )
        self.df.loc[cond_ciudad_invalida, col_ciudad] = 'POPAYAN'
        
        # Departamento - siempre Cauca si no hay valor válido
        col_depto = self.map['department']
        self.df[col_depto] = self.df[col_depto].astype(str).str.strip().str.upper()
        cond_depto_invalido = (
            self.df[col_depto].isin(['', '0', 'NAN', 'NONE']) |   # Valores vacíos/inválidos
            self.df[col_depto].str.isdigit() |                    # Solo números
            self.df[col_depto].isnull()                           # Valores nulos
        )
        self.df.loc[cond_depto_invalido, col_depto] = 'CAUCA'
        
        self.df[self.map['full_name']] = self.df[self.map['full_name']].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip().str.upper()
        self.df[self.map['id_number']] = self.df[self.map['id_number']].astype(str)
        
        self.df.loc[self.df[self.map['id_number']] == '1118291452', self.map['full_name']] = 'FANDINO LAYNE ASTRID'
        self.df.loc[self.df[self.map['id_number']] == '1025529458', self.map['full_name']] = 'MARTINEZ MUNOZ JOSE MANUEL'
        self.df.loc[self.df[self.map['id_number']] == '25559122', self.map['full_name']] = 'RAMIREZ DE CASTRO MARIA ESTELLA'
        
        
        for key in ['home_phone', 'company_phone']:
            if key in self.map:
                col = self.map[key]
                self.df[col] = (
                    self.df[col].astype(str)
                    .str.replace(r'\D', '', regex=True)  # Elimina todo lo que no sea dígito
                    .replace('^0+$', ' ', regex=True)    # Reemplaza puros ceros por espacio
                    .str.strip()                         # Elimina espacios sobrantes
                )
                
                # 2. Definir condiciones de validez
                es_fijo_valido = self.df[col].str.len() == 7
                es_celular_valido = (self.df[col].str.len() == 10) & (self.df[col].str.startswith('3'))
                
                # 3. Marcar como inválido si no cumple NINGUNA de las dos condiciones
                mascara_invalida = ~(es_fijo_valido | es_celular_valido)
                self.df.loc[mascara_invalida, col] = '' # Reemplaza por vacío


        if 'phone' in self.map:
            col_celular = self.map['phone']
            # 1. Limpiar y dejar solo números
            self.df[col_celular] = self.df[col_celular].astype(str).str.replace(r'\D', '', regex=True)
            
            # 2. Definir la única condición de validez
            es_celular_valido = (self.df[col_celular].str.len() == 10) & (self.df[col_celular].str.startswith('3'))
            
            # 3. Marcar como inválido si NO cumple la condición
            mascara_invalida = ~es_celular_valido
            self.df.loc[mascara_invalida, col_celular] = ''

            self.df[self.map['email']] = self.df[self.map['email']].astype(str).str.strip()
            for placeholder in ['CORREGIR', 'PENDIENTE', 'NOTIENE', 'SINC', 'NN@', 'AAA@']:
                self.df.loc[self.df[self.map['email']].str.contains(placeholder, case=False, na=False), self.map['email']] = ''
            self.df.loc[~self.df[self.map['email']].str.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', na=False), self.map['email']] = ''
            
            self.df[self.map['periodicity']] = '05'
        
    def _final_cleanup(self):
        """
        Limpia CUALQUIER valor nulo o texto 'nan' restante en todas las
        columnas no numéricas justo antes de aplicar el padding.
        """
        print("  - Realizando limpieza final de valores nulos...")
        numeric_keys = ['initial_value', 'balance_due', 'available_value', 'monthly_fee', 'arrears_value', 'actual_value_paid']
        columnas_numericas = [self.map[k] for k in numeric_keys if k in self.map]
        columnas_a_limpiar = self.df.columns.drop(columnas_numericas)
        
        for col in columnas_a_limpiar:
            self.df[col] = self.df[col].astype(str).str.strip()
            self.df[col] = self.df[col].replace(r'(?i)^nan$', '', regex=True).fillna('')  
    
    def _apply_padding_formats(self):
        """
        Aplica los formatos de longitud fija (.ljust y .zfill) como último paso.
        """
        print("  - Aplicando formatos de longitud y relleno finales...")
        
        # Primero nos aseguramos que todas las columnas a rellenar sean de texto
        # para evitar errores.
        cols_to_pad = [
            'arrears_age', 'full_name', 'address', 'city', 'department',
            'email', 'phone', 'id_number','cellular'
        ]
        for key in cols_to_pad:
            if key in self.map:
                self.df[self.map[key]] = self.df[self.map[key]].astype(str)

        # Ahora aplicamos los formatos de longitud
        self.df[self.map['arrears_age']] = self.df[self.map['arrears_age']].str.zfill(2)
        self.df[self.map['full_name']] = self.df[self.map['full_name']].str.ljust(60)
        self.df[self.map['account_number']] = self.df[self.map['account_number']].str.ljust(20)
        self.df[self.map['address']] = self.df[self.map['address']].str.ljust(60)
        self.df[self.map['city']] = self.df[self.map['city']].str.ljust(20)
        self.df[self.map['department']] = self.df[self.map['department']].str.ljust(20)
        self.df[self.map['email']] = self.df[self.map['email']].str.ljust(60)
        self.df[self.map['phone']] = self.df[self.map['phone']].str.ljust(60)
        self.df[self.map['home_phone']] = self.df[self.map['home_phone']].str.ljust(20)
        self.df[self.map['company_phone']] = self.df[self.map['company_phone']].str.ljust(20)
        self.df[self.map['id_number']] = self.df[self.map['id_number']].str.zfill(15)          