import pandas as pd
import re
from rapidfuzz.distance import Levenshtein
class ArpesodDataProcessorService:
    """
    Servicio para procesar y transformar datos de Arpesod.
    Versión CORREGIDA para manejar índices y ceros a la izquierda.
    """
    def __init__(self, df, ruta_correcciones, column_mapping):
        self.df = df.copy() 
        self.ruta_correcciones = ruta_correcciones
        self.map = column_mapping

    def _tiene_diversidad(self, texto: str, umbral: int = 3) -> bool:
        if not isinstance(texto, str): return False
        letras_unicas = set(c for c in texto.lower() if c.isalpha())
        return len(letras_unicas) >= umbral

    def _es_correo_valido_estricto(self, correo: str) -> bool:
        if not isinstance(correo, str) or not correo: return False
        correo = correo.strip()
        pattern = re.compile(r"^(?![.-])(?!(?:.*[.]{2}))[A-Z0-9._%+-ñÑ]{3,}@[A-Z0-9.-]{3,}\.[A-Z]{2,}$", re.IGNORECASE)
        if not pattern.match(correo): return False
        try:
            usuario, _ = correo.split('@', 1)
            usuario = usuario.lower()
        except ValueError: return False 
        if usuario.isdigit() or not self._tiene_diversidad(usuario): return False
        
        blacklist = ["notiene", "sincorreo", "pendiente", "corregir", "noregistra", "nulo", "ninguno", "vacio", "nodisponible"]
        for item_prohibido in blacklist:
            if Levenshtein.distance(usuario, item_prohibido) <= 2: return False
        return True

    # --- ORQUESTADOR ---
    def run_all_transformations(self):
        print("Servicio: Ejecutando todas las transformaciones...")
        self._correct_data_from_excel()     # Filtra filas
        self._update_data_from_sheets()     # Cruce de saldos (REPARADO)
        self._clean_and_validate_data()     # Limpieza general
        
        # Correcciones específicas antes del formato final
        self._apply_specific_corrections()  
        
        self._apply_final_formatting()      # Formatos Arpesod
        self._final_cleanup()               # Quitar nulos
        self._apply_padding_formats()       # Padding final
        self._save_final_state_to_excel()   # Guardar base
        
        print("Servicio: Transformaciones completadas.")
        return self.df
    
    # --- PASO 1: FILTRADO ---
    def _correct_data_from_excel(self):
        print("  - Corrigiendo y filtrando datos desde Excel...")
        try:
            df_R91 = pd.read_excel(self.ruta_correcciones, sheet_name='R91', usecols=['MCDZONA', 'MCDVINCULA', 'VINNOMBRE'], dtype=str)
            df_cedulas = pd.read_excel(self.ruta_correcciones, sheet_name='CEDULAS_NO_REPORTAR', usecols=['NIT', 'NOMBRE'], dtype=str)
            df_facturas = pd.read_excel(self.ruta_correcciones, sheet_name='FACTURAS_ELIMINAR', dtype=str)
        except Exception as e:
            print(f"❌ ERROR leyendo Excel correcciones: {e}")
            return

        cedulas_1CE = df_R91[df_R91['MCDZONA'] == '1CE'][['MCDVINCULA', 'VINNOMBRE']].rename(columns={'MCDVINCULA': 'NIT', 'VINNOMBRE': 'NOMBRE'})
        df_cedulas_completo = pd.concat([df_cedulas, cedulas_1CE]).drop_duplicates(subset=['NIT'])
        
        nits_eliminar = set(df_cedulas_completo['NIT'].astype(str).str.strip())
        col_id = self.map['id_number']
        
        # Usamos lstrip('0') para que coincida aunque el archivo plano tenga ceros
        self.df = self.df[~self.df[col_id].astype(str).str.strip().str.lstrip('0').isin(nits_eliminar)]
        
        facturas_eliminar = set(df_facturas['NUMERO DE LA CUENTA U OBLIGACION'].astype(str).str.strip())
        col_obligacion = self.map['account_number']
        self.df = self.df[~self.df[col_obligacion].astype(str).str.strip().isin(facturas_eliminar)]

    # --- PASO 2: CRUCE DE SALDOS (REPARADO) ---
    def _update_data_from_sheets(self):
        """
        Actualiza valores usando mapeo directo para evitar el error de índices.
        """
        print("  - Actualizando desde SALDOS_INICIALES (Método Seguro)...")
        COL_KEY_EXCEL = 'NUMERO DE LA CUENTA U OBLIGACION'
        COL_VAL_EXCEL = 'VALOR INICIAL'
        col_key_df = self.map['account_number'] # 'numero_obligacion'
        col_val_df = self.map['initial_value']  # 'valor_inicial'

        try:
            df_saldos = pd.read_excel(self.ruta_correcciones, sheet_name='SALDOS_INICIALES', usecols=[COL_KEY_EXCEL, COL_VAL_EXCEL], dtype={COL_KEY_EXCEL: str})
            # 1. Preparar llave limpia en el DataFrame (temporal)
            # Quitamos espacios para que coincida con la llave limpia del Excel
            self.df['TEMP_MATCH_KEY'] = self.df[col_key_df].astype(str).str.strip().str.upper()
            # 2. Preparar diccionario de búsqueda desde Excel
            # Limpiamos la llave del Excel (quitamos ceros a la izquierda y espacios)
            df_saldos['KEY_CLEAN'] = df_saldos[COL_KEY_EXCEL].str.lstrip('0').str.strip().str.upper()
            # Eliminamos duplicados en el Excel para evitar errores de mapeo
            df_saldos = df_saldos.drop_duplicates(subset=['KEY_CLEAN'])
            # Creamos un diccionario { 'CUENTA': VALOR }
            mapa_saldos = df_saldos.set_index('KEY_CLEAN')[COL_VAL_EXCEL].to_dict()
            # 3. Mapear el valor del Excel a una columna temporal en self.df
            # Esto respeta el índice original de self.df y evita el crash "not in index"
            self.df['VALOR_EXCEL_TEMP'] = self.df['TEMP_MATCH_KEY'].map(mapa_saldos)
            # 4. Cálculos y Lógica
            # Convertimos a numérico
            val_excel = pd.to_numeric(self.df['VALOR_EXCEL_TEMP'], errors='coerce').fillna(0)
            val_reporte = pd.to_numeric(self.df[col_val_df], errors='coerce').fillna(0)
            # Solo nos interesan las filas donde HUBO coincidencia (VALOR_EXCEL_TEMP no es NaN o nulo)
            mask_coincidencia = self.df['VALOR_EXCEL_TEMP'].notna()
            diferencia = val_excel - val_reporte
            # CASO A: Actualizar (Excel > Reporte)
            # Usamos los índices originales de self.df directamente
            mask_actualizar = mask_coincidencia & (diferencia > 0)
            self.df.loc[mask_actualizar, col_val_df] = val_excel[mask_actualizar]
            
            cant = mask_actualizar.sum()
            if cant > 0:
                print(f"    -> Se actualizaron {cant} registros con valor del Excel.")

            # CASO B: Reportar Negativos (Excel < Reporte)
            mask_negativos = mask_coincidencia & (diferencia < 0)
            
            if mask_negativos.any():
                df_neg = self.df[mask_negativos].copy()
                print(f"    -> Se encontraron {len(df_neg)} diferencias negativas.")
                
                # Buscamos el valor original del excel para el reporte (estético)
                reporte = pd.DataFrame({
                    'LLAVE_CRUCE': df_neg['TEMP_MATCH_KEY'],
                    'OBLIGACION_REPORTE': df_neg[col_key_df],
                    'VALOR_TU_REPORTE': val_reporte[mask_negativos],
                    'VALOR_EN_EXCEL': val_excel[mask_negativos],
                    'DIFERENCIA': diferencia[mask_negativos]
                })
                
                with pd.ExcelWriter(self.ruta_correcciones, mode='a', engine='openpyxl', if_sheet_exists='replace') as writer:
                    reporte.to_excel(writer, sheet_name='SALDOS_NEGATIVOS', index=False)
            else:
                print("    -> No se encontraron diferencias negativas.")

        except Exception as e:
            print(f"❌ ERROR CRÍTICO en cruce de saldos: {e}")
        finally:
            # Limpieza de columnas temporales
            if 'TEMP_MATCH_KEY' in self.df.columns: del self.df['TEMP_MATCH_KEY']
            if 'VALOR_EXCEL_TEMP' in self.df.columns: del self.df['VALOR_EXCEL_TEMP']

    # --- PASO 3: LIMPIEZA GENERAL ---
    def _clean_and_validate_data(self):
        print("  - Limpiando y validando datos...")
        letter_replacements = {'Ñ':'N','Á':'A','É':'E','Í':'I','Ó':'O','Ú':'U'}
        chars = ['@','°','|','¬','¡','“','#','$','%','&','/','(',')','=','‘','\\','¿','+','~','´','[','{','^','-','_','.',':',',',';','<','>']

        # Ojo: Excluimos email de esta limpieza agresiva
        string_cols = self.df.select_dtypes(include='object').columns.drop(self.map.get('email', ''), errors='ignore')
        
        for col in string_cols:
            self.df[col] = self.df[col].astype(str).str.upper()
            for old, new in letter_replacements.items(): self.df[col] = self.df[col].str.replace(old, new, regex=False)
            for c in chars: self.df[col] = self.df[col].str.replace(c, '', regex=False)
        
        # Fechas
        for col in [self.map['open_date'], self.map['due_date']]:
            self.df[col] = pd.to_numeric(self.df[col], errors='coerce').fillna(0).astype('Int64').astype(str)
        
        # Números
        cols_num = [self.map[k] for k in ['initial_value', 'balance_due', 'available_value', 'monthly_fee', 'arrears_value'] if k in self.map]
        for col in cols_num:
            self.df[col] = pd.to_numeric(self.df[col], errors='coerce').fillna(0)
            self.df.loc[self.df[col] <= 10, col] = 0
            self.df[col] = self.df[col].astype(int)

        # Emails
        print("    -> Validando correos...")
        c_email = self.map['email']
        self.df[c_email] = self.df[c_email].astype(str).fillna('')
        inv = ~self.df[c_email].apply(self._es_correo_valido_estricto)
        self.df.loc[inv, c_email] = ''
        print(f"      -> Se borraron {inv.sum()} correos inválidos.")

    # --- PASO 4: CORRECCIONES MANUALES (NUEVO) ---
    def _apply_specific_corrections(self):
        """
        Aplica parches manuales a cédulas específicas.
        SOLUCIÓN: Usa .lstrip('0') para encontrar las cédulas en el archivo plano.
        """
        print("  - Aplicando correcciones manuales específicas...")
        col_id = self.map['id_number'] # 'NUMERO DE IDENTIFICACION'

        # Diccionario con nombres de columna REALES del Modelo (español)
        correcciones = {
            '1112221022': {
                'cuotas_pagadas': '004', 'cuotas_pactadas': '016', 'cuotas_mora': '012',
                'valor_inicial': '2663', 'valor_mora': '2036', 'valor_saldo': '2036',
                'valor_cuota': '170', 'cargo_fijo': '170', 'linea_credito': '003',
                'tipo_contrato': '001', 'estado_contrato': '001', 'vigencia_contrato': '01',
                'numero_meses_contrato': '016', 'obligacion_reestructurada': '02', 'plazo': '08'
            },
            '1114734271': {
                'cuotas_pactadas': '014', 'cuotas_mora': '009', 'valor_inicial': '1533',
                'valor_mora': '906', 'valor_saldo': '906', 'valor_cuota': '105',
                'cargo_fijo': '105', 'linea_credito': '003', 'tipo_contrato': '001',
                'estado_contrato': '001', 'vigencia_contrato': '01', 'numero_meses_contrato': '014',
                'obligacion_reestructurada': '02', 'plazo': '08'
            },
            '6646420': {
                'cuotas_pagadas': '010', 'cuotas_pactadas': '018', 'cuotas_mora': '008',
                'valor_inicial': '2874', 'valor_mora': '1475', 'valor_saldo': '1475',
                'valor_cuota': '155', 'cargo_fijo': '155', 'linea_credito': '003',
                'tipo_contrato': '001', 'estado_contrato': '001', 'vigencia_contrato': '01',
                'numero_meses_contrato': '018', 'obligacion_reestructurada': '02', 'plazo': '08', 'edad_mora':'14'
            }
        }
        for cedula, cambios in correcciones.items():
            # CLAVE DEL ÉXITO: .lstrip('0') ignora los ceros del archivo plano para comparar
            mask = self.df[col_id].astype(str).str.strip().str.lstrip('0') == cedula
            
            if mask.any():
                print(f"    ✅ Cédula {cedula} encontrada. Aplicando cambios...")
                for col_name, valor in cambios.items():
                    # Si la columna no existe en el DF, la creamos vacía
                    if col_name not in self.df.columns:
                        self.df[col_name] = ''
                    
                    # Asignamos el valor como texto
                    self.df.loc[mask, col_name] = str(valor)
            else:
                print(f"    ⚠️ Cédula {cedula} NO encontrada (verificó: {cedula}).")

    # --- PASO 5: FORMATO FINAL ---
    def _apply_final_formatting(self):
        """
        Aplica formatos específicos y reglas de negocio:
        1. Ciudades por defecto.
        2. Corrección de tipo de pago (02 -> 01).
        3. Limpieza y validación diferenciada de teléfonos fijos y celulares.
        """
        print("  - Aplicando formatos finales y validaciones de negocio...")
        
        # 1. Formato de Ciudad y Departamento
        for col, default in [(self.map.get('city'), 'POPAYAN'), (self.map.get('department'), 'CAUCA')]:
            if col in self.df.columns:
                self.df[col] = self.df[col].astype(str).str.strip().str.upper()
                bad = self.df[col].isin(['', '0', 'NAN', 'NONE']) | self.df[col].str.isdigit() | self.df[col].isnull()
                self.df.loc[bad, col] = default
        
        # 2. Formato de Nombre y Cédula
        if 'full_name' in self.map:
            c_name = self.map['full_name']
            self.df[c_name] = self.df[c_name].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip().str.upper()
        
        if 'id_number' in self.map:
            self.df[self.map['id_number']] = self.df[self.map['id_number']].astype(str)
            # Parches de nombres específicos
            nombres_fix = {'1118291452': 'FANDINO LAYNE ASTRID', '1025529458': 'MARTINEZ MUNOZ JOSE MANUEL', '25559122': 'RAMIREZ DE CASTRO MARIA ESTELLA'}
            col_id = self.map['id_number']
            for ced, nom in nombres_fix.items():
                self.df.loc[self.df[col_id].str.lstrip('0') == ced, c_name] = nom

        # 3. NUEVO: REGLA TIPO DE PAGO (02 -> 01)
        # Buscamos la columna. Puede estar mapeada o llamarse 'tipo_pago' directamente
        col_pago = self.map.get('payment_type', 'tipo_pago') 
        
        if col_pago in self.df.columns:
            # Aseguramos que sea string y quitamos espacios
            self.df[col_pago] = self.df[col_pago].astype(str).str.strip()
            # Aplicamos el reemplazo
            mask_02 = self.df[col_pago] == '02'
            if mask_02.any():
                print(f"    -> Se corrigieron {mask_02.sum()} registros de 'tipo_pago' (02 -> 01).")
                self.df.loc[mask_02, col_pago] = '01'

        # 4. NUEVO: VALIDACIÓN DE TELÉFONOS DIFERENCIADA
        # A. Limpieza inicial (quitar todo lo que no sea números)
        phone_keys = ['home_phone', 'company_phone', 'phone']
        for key in phone_keys:
            if key in self.map:
                col = self.map[key]
                self.df[col] = self.df[col].astype(str).str.replace(r'\D', '', regex=True).replace('^0+$', '', regex=True).str.strip()

        # B. Validación para CASA y EMPRESA (Admiten fijos de 7 Y celulares de 10 empezando por 3)
        for key in ['home_phone', 'company_phone']:
            if key in self.map:
                col = self.map[key]
                # Regla: Longitud 7  O  (Longitud 10 Y Empieza por 3)
                es_fijo = self.df[col].str.len() == 7
                es_celular_valido = (self.df[col].str.len() == 10) & self.df[col].str.startswith('3')
                
                # Lo que NO cumpla ninguna de las dos, se borra
                self.df.loc[~(es_fijo | es_celular_valido), col] = ''

        # C. Validación para CELULAR (Solo admite 10 dígitos empezando por 3)
        if 'phone' in self.map: # 'numero_celular'
            col = self.map['phone']
            # Regla: Estrictamente 10 dígitos Y Empieza por 3
            es_celular_estricto = (self.df[col].str.len() == 10) & self.df[col].str.startswith('3')
            
            # Lo que no cumpla, se borra
            self.df.loc[~es_celular_estricto, col] = ''

        # Periodicidad fija
        if 'periodicity' in self.map:
            self.df[self.map['periodicity']] = '05'

    def _final_cleanup(self):
        # Quita 'nan' textual
        cols_skip = [self.map[k] for k in ['initial_value', 'balance_due', 'available_value', 'monthly_fee', 'arrears_value', 'actual_value_paid'] if k in self.map]
        cols_txt = self.df.columns.drop(cols_skip)
        for col in cols_txt:
            self.df[col] = self.df[col].astype(str).str.strip().replace(r'(?i)^nan$', '', regex=True).fillna('')

    def _apply_padding_formats(self):
        print("  - Aplicando padding final...")
        # Usamos los nombres del mapa para aplicar padding
        pads = {
            'arrears_age': ('zfill', 2), 'full_name': ('ljust', 60),
            'account_number': ('ljust', 20), 'address': ('ljust', 60),
            'city': ('ljust', 20), 'department': ('ljust', 20),
            'email': ('ljust', 60), 'phone': ('ljust', 60),
            'home_phone': ('ljust', 20), 'company_phone': ('ljust', 20),
            'id_number': ('zfill', 15)
        }
        for k, (metodo, l) in pads.items():
            if k in self.map:
                c = self.map[k]
                self.df[c] = self.df[c].astype(str)
                if metodo == 'zfill': self.df[c] = self.df[c].str.zfill(l)
                else: self.df[c] = self.df[c].str.ljust(l)

    def _save_final_state_to_excel(self):
        print("  - Guardando estado limpio en SALDOS_INICIALES...")
        try:
            c_cta = self.map['account_number']
            c_val = self.map['initial_value']
            
            df_exp = self.df[[c_cta, c_val]].copy()
            # Limpieza crítica para el futuro
            df_exp[c_cta] = df_exp[c_cta].astype(str).str.strip().str.lstrip('0')
            
            df_exp.columns = ['NUMERO DE LA CUENTA U OBLIGACION', 'VALOR INICIAL']
            
            with pd.ExcelWriter(self.ruta_correcciones, mode='a', engine='openpyxl', if_sheet_exists='replace') as writer:
                df_exp.to_excel(writer, sheet_name='SALDOS_INICIALES', index=False)
        except Exception as e:
            print(f"⚠️ No se pudo guardar SALDOS_INICIALES: {e}")