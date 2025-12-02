import pandas as pd
import re
from rapidfuzz.distance import Levenshtein
class ArpesodDataProcessorService:
    """
    Servicio para procesar y transformar datos de Arpesod.
    Versión con LOGS DETALLADOS para monitoreo en consola.
    """
    def __init__(self, df, ruta_correcciones, column_mapping):
        self.df = df.copy() 
        self.ruta_correcciones = ruta_correcciones
        self.map = column_mapping

    # --- MÉTODOS AUXILIARES ---
    def _log(self, mensaje):
        """Ayuda a imprimir mensajes bonitos en la consola."""
        print(f"[ARPESOD SERVICE] {mensaje}")

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
        print("\n" + "="*60)
        self._log("INICIANDO PROCESO DE TRANSFORMACIÓN")
        self._log(f"Registros iniciales: {len(self.df)}")
        print("="*60)
        
        self._correct_data_from_excel()     # Paso 1
        self._update_data_from_sheets()     # Paso 2
        self._clean_and_validate_data()     # Paso 3
        self._apply_specific_corrections()  # Paso 4
        self._apply_final_formatting()      # Paso 5
        self._final_cleanup()               # Paso 6
        self._apply_padding_formats()       # Paso 7
        self._save_final_state_to_excel()   # Paso 8
        
        print("="*60)
        self._log("TRANSFORMACIONES COMPLETADAS EXITOSAMENTE")
        self._log(f"Registros finales: {len(self.df)}")
        print("="*60 + "\n")
        return self.df
    
    # --- PASO 1: FILTRADO Y GESTIÓN R91 ---
    def _correct_data_from_excel(self):
        print("\n>>> PASO 1: Gestión R91 y Filtrado de Exclusiones")
        try:
            df_R91 = pd.read_excel(self.ruta_correcciones, sheet_name='R91', usecols=['MCDZONA', 'MCDVINCULA', 'VINNOMBRE'], dtype=str)
            df_cedulas_existentes = pd.read_excel(self.ruta_correcciones, sheet_name='CEDULAS_NO_REPORTAR', dtype=str)
            df_facturas = pd.read_excel(self.ruta_correcciones, sheet_name='FACTURAS_ELIMINAR', dtype=str)
        except Exception as e:
            self._log(f"❌ ERROR LEYENDO EXCEL: {e}")
            return

        candidatos_nuevos = df_R91[df_R91['MCDZONA'] == '1CE'][['MCDVINCULA', 'VINNOMBRE']].copy()
        candidatos_nuevos.rename(columns={'MCDVINCULA': 'NIT', 'VINNOMBRE': 'NOMBRE'}, inplace=True)
        candidatos_nuevos['NIT'] = candidatos_nuevos['NIT'].str.strip()
        
        nits_existentes = set(df_cedulas_existentes['NIT'].astype(str).str.strip())
        nuevos_para_agregar = candidatos_nuevos[~candidatos_nuevos['NIT'].isin(nits_existentes)].drop_duplicates(subset=['NIT'])
        df_cedulas_completo = df_cedulas_existentes

        if not nuevos_para_agregar.empty:
            self._log(f"Detectados {len(nuevos_para_agregar)} nuevos registros '1CE'. Actualizando Excel...")
            df_cedulas_completo = pd.concat([df_cedulas_existentes, nuevos_para_agregar], ignore_index=True)
            try:
                with pd.ExcelWriter(self.ruta_correcciones, mode='a', engine='openpyxl', if_sheet_exists='replace') as writer:
                    df_cedulas_completo.to_excel(writer, sheet_name='CEDULAS_NO_REPORTAR', index=False)
                self._log("✅ Hoja 'CEDULAS_NO_REPORTAR' guardada.")
            except Exception as e:
                self._log(f"⚠️ No se pudo guardar el Excel: {e}")
        else:
            self._log("No hay nuevos registros '1CE' para agregar.")

        col_id = self.map['id_number']
        nits_eliminar = set(df_cedulas_completo['NIT'].astype(str).str.strip())
        registros_antes = len(self.df)
        self.df = self.df[~self.df[col_id].astype(str).str.strip().str.lstrip('0').isin(nits_eliminar)]
        eliminados_nit = registros_antes - len(self.df)
        self._log(f"Filas eliminadas por Cédula (Lista Negra): {eliminados_nit}")

        col_obligacion = self.map['account_number']
        facturas_eliminar = set(df_facturas['NUMERO DE LA CUENTA U OBLIGACION'].astype(str).str.strip())
        registros_antes = len(self.df)
        self.df = self.df[~self.df[col_obligacion].astype(str).str.strip().isin(facturas_eliminar)]
        eliminados_fac = registros_antes - len(self.df)
        self._log(f"Filas eliminadas por Factura: {eliminados_fac}")

    # --- PASO 2: CRUCE DE SALDOS ---
    def _update_data_from_sheets(self):
        print("\n>>> PASO 2: Cruce con SALDOS_INICIALES")
        COL_KEY_EXCEL = 'NUMERO DE LA CUENTA U OBLIGACION'
        COL_VAL_EXCEL = 'VALOR INICIAL'
        col_key_df = self.map['account_number']
        col_val_df = self.map['initial_value']

        try:
            df_saldos = pd.read_excel(self.ruta_correcciones, sheet_name='SALDOS_INICIALES', usecols=[COL_KEY_EXCEL, COL_VAL_EXCEL], dtype={COL_KEY_EXCEL: str})
            
            self.df['TEMP_MATCH_KEY'] = self.df[col_key_df].astype(str).str.strip().str.upper()
            df_saldos['KEY_CLEAN'] = df_saldos[COL_KEY_EXCEL].str.lstrip('0').str.strip().str.upper()
            df_saldos = df_saldos.drop_duplicates(subset=['KEY_CLEAN'])
            
            mapa_saldos = df_saldos.set_index('KEY_CLEAN')[COL_VAL_EXCEL].to_dict()
            self.df['VALOR_EXCEL_TEMP'] = self.df['TEMP_MATCH_KEY'].map(mapa_saldos)
            
            val_excel = pd.to_numeric(self.df['VALOR_EXCEL_TEMP'], errors='coerce').fillna(0)
            val_reporte = pd.to_numeric(self.df[col_val_df], errors='coerce').fillna(0)
            mask_coincidencia = self.df['VALOR_EXCEL_TEMP'].notna()
            diferencia = val_excel - val_reporte

            mask_actualizar = mask_coincidencia & (diferencia > 0)
            self.df.loc[mask_actualizar, col_val_df] = val_excel[mask_actualizar]
            if mask_actualizar.any():
                self._log(f"✅ Se actualizaron {mask_actualizar.sum()} registros (Excel > Reporte).")

            mask_negativos = mask_coincidencia & (diferencia < 0)
            if mask_negativos.any():
                df_neg = self.df[mask_negativos].copy()
                self._log(f"⚠️ Se encontraron {len(df_neg)} diferencias NEGATIVAS. Generando reporte...")
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
                self._log("No se encontraron diferencias negativas.")

        except Exception as e:
            self._log(f"❌ ERROR CRÍTICO CRUCE SALDOS: {e}")
        finally:
            if 'TEMP_MATCH_KEY' in self.df.columns: del self.df['TEMP_MATCH_KEY']
            if 'VALOR_EXCEL_TEMP' in self.df.columns: del self.df['VALOR_EXCEL_TEMP']

    # --- PASO 3: LIMPIEZA ---
    def _clean_and_validate_data(self):
        print("\n>>> PASO 3: Limpieza y Validación General")
        
        # A. LIMPIEZA DE CARACTERES (TEXTO)
        letter_replacements = {'Ñ':'N','Á':'A','É':'E','Í':'I','Ó':'O','Ú':'U'}
        chars = ['@','°','|','¬','¡','“','#','$','%','&','/','(',')','=','‘','\\','¿','+','~','´','[','{','^','-','_','.',':',',',';','<','>']
        string_cols = self.df.select_dtypes(include='object').columns.drop(self.map.get('email', ''), errors='ignore')
        
        for col in string_cols:
            self.df[col] = self.df[col].astype(str).str.upper()
            for old, new in letter_replacements.items(): 
                self.df[col] = self.df[col].str.replace(old, new, regex=False)
            for c in chars: 
                self.df[col] = self.df[col].str.replace(c, '', regex=False)
        self._log("Caracteres especiales eliminados.")

        # B. LIMPIEZA TIPO DE IDENTIFICACIÓN (NUEVA SOLICITUD)
        col_id_type = self.map.get('id_type', 'TIPO DE IDENTIFICACION') # Asegúrate que tu mapa tenga 'id_type'
        if col_id_type in self.df.columns:
            # Convertimos a string y quitamos espacios
            self.df[col_id_type] = self.df[col_id_type].astype(str).str.strip()
            # Valores permitidos
            permitidos = ['1', '2', '4']
            # Filtro: Lo que NO esté en permitidos -> '1'
            mask_invalido = ~self.df[col_id_type].isin(permitidos)
            if mask_invalido.any():
                self.df.loc[mask_invalido, col_id_type] = '1'
                self._log(f"Tipos de ID corregidos a '1': {mask_invalido.sum()}")

        # C. VALIDACIÓN DE FECHAS
        for col in [self.map.get('open_date', 'FECHA APERTURA'), self.map.get('due_date', 'FECHA VENCIMIENTO')]:
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(self.df[col], errors='coerce').fillna(0).astype('Int64').astype(str)
        
        cond_fechas = self.df[self.map.get('due_date', 'FECHA VENCIMIENTO')] < self.df[self.map.get('open_date', 'FECHA APERTURA')]
        if cond_fechas.any():
            self.df.loc[cond_fechas, self.map.get('due_date', 'FECHA VENCIMIENTO')] = self.df[self.map.get('open_date', 'FECHA APERTURA')]
            self._log(f"Corregidas {cond_fechas.sum()} fechas vencimiento < apertura.")

        # D. VALIDACIÓN NUMÉRICA (< 10000 -> 0)
        columnas_numericas = [
            "VALOR INICIAL", "VALOR SALDO DEUDA", "VALOR DISPONIBLE", 
            "V CUOTA MENSUAL", "VALOR SALDO MORA"
        ]
        
        for col in columnas_numericas:
            # 1. Buscar la columna (directa o mapeada)
            real_col = col
            if col not in self.df.columns:
                # Intento de búsqueda en mapa inverso
                for k, v in self.map.items():
                    if v == col and k in self.df.columns:
                        real_col = k
                        break
                
                # Si no existe, la creamos en 0
                if real_col not in self.df.columns:
                    self._log(f"⚠️ Columna numérica '{col}' no encontrada. Creando en 0.")
                    self.df[col] = 0
                    real_col = col

            # 2. Convertir a numérico (importante: coerce para volver NaN los textos raros)
            self.df[real_col] = pd.to_numeric(self.df[real_col], errors='coerce').fillna(0)

            # 3. Reglas de Negocio
            if col == 'VALOR DISPONIBLE':
                self.df[real_col] = 0 # Regla estricta
            else:
                # Regla: < 10000 se vuelve 0
                mask_menor = self.df[real_col] < 10000
                if mask_menor.any():
                    self.df.loc[mask_menor, real_col] = 0
                    self._log(f"   -> {real_col}: {mask_menor.sum()} valores < 10.000 corregidos a 0.")

            # 4. Asegurar entero para eliminar decimales (.0)
            self.df[real_col] = self.df[real_col].astype(int)

        self._log("Validación numérica completada.")

        # E. EMAILS
        c_email = self.map.get('email', 'CORREO ELECTRONICO')
        if c_email in self.df.columns:
            self.df[c_email] = self.df[c_email].astype(str).fillna('')
            inv = ~self.df[c_email].apply(self._es_correo_valido_estricto)
            self.df.loc[inv, c_email] = ''
            self._log(f"Correos invalidados: {inv.sum()}")

    # --- PASO 4: CORRECCIONES MANUALES ---
    def _apply_specific_corrections(self):
        print("\n>>> PASO 4: Correcciones Manuales (Hardcoded)")
        col_id = self.map['id_number']
        correcciones = {
            '1112221022': {
                'VALOR INICIAL': 2663000, 'VALOR SALDO DEUDA': 2036480, 'VALOR DISPONIBLE': '00000000000',
                'V CUOTA MENSUAL': 170000, 'VALOR SALDO MORA': 2036480, 'TOTAL CUOTAS': '014',
                'CUOTAS CANCELADAS': '005', 'CUOTAS EN MORA': '009'
            },
            '1114734271': {
                'VALOR INICIAL': 1533500, 'VALOR SALDO DEUDA': 905675, 'VALOR DISPONIBLE': '00000000000',
                'V CUOTA MENSUAL': 10500, 'VALOR SALDO MORA': 905675, 'TOTAL CUOTAS': '016',
                'CUOTAS CANCELADAS': '004', 'CUOTAS EN MORA': '012'
            },
            '6646420': {
                'VALOR INICIAL': 2874656, 'VALOR SALDO DEUDA': 1474656, 'VALOR DISPONIBLE': '00000000000',
                'V CUOTA MENSUAL': 154666, 'VALOR SALDO MORA': 1474656, 'TOTAL CUOTAS': '018',
                'CUOTAS CANCELADAS': '01'
            }
        }
        
        encontrados = 0
        for cedula, cambios in correcciones.items():
            mask = self.df[col_id].astype(str).str.strip().str.lstrip('0') == cedula
            if mask.any():
                encontrados += 1
                self._log(f"✔ Aplicando parches a cédula {cedula}")
                for col_name, valor in cambios.items():
                    if col_name not in self.df.columns: self.df[col_name] = ''
                    # IMPORTANTE: Forzamos a string para evitar FutureWarning
                    self.df.loc[mask, col_name] = str(valor)
        
        if encontrados == 0:
            self._log("No se encontraron las cédulas específicas en este lote.")

    # --- PASO 5: FORMATO FINAL ---
    def _apply_final_formatting(self):
        print("\n>>> PASO 5: Reglas de Negocio Finales")
        
        for col, default in [(self.map.get('city'), 'POPAYAN'), (self.map.get('department'), 'CAUCA')]:
            if col in self.df.columns:
                self.df[col] = self.df[col].astype(str).str.strip().str.upper()
                bad = self.df[col].isin(['', '0', 'NAN', 'NONE']) | self.df[col].str.isdigit() | self.df[col].isnull()
                self.df.loc[bad, col] = default
        
        if 'id_number' in self.map:
            c_name = self.map['full_name']
            col_id = self.map['id_number']
            self.df[col_id] = self.df[col_id].astype(str)
            nombres_fix = {'1118291452': 'FANDINO LAYNE ASTRID', '1025529458': 'MARTINEZ MUNOZ JOSE MANUEL', '25559122': 'RAMIREZ DE CASTRO MARIA ESTELLA'}
            for ced, nom in nombres_fix.items():
                self.df.loc[self.df[col_id].str.lstrip('0') == ced, c_name] = nom

        col_pago = self.map.get('payment_type', 'tipo_pago') 
        if col_pago in self.df.columns:
            self.df[col_pago] = self.df[col_pago].astype(str).str.strip()
            mask_02 = self.df[col_pago] == '02'
            if mask_02.any():
                self.df.loc[mask_02, col_pago] = '01'
                self._log(f"Tipos de pago corregidos (02->01): {mask_02.sum()}")

        self._log("Limpiando y validando teléfonos...")
        count_clean = 0
        for key in ['home_phone', 'company_phone', 'phone']:
            if key in self.map:
                col = self.map[key]
                self.df[col] = self.df[col].astype(str).str.replace(r'\D', '', regex=True).replace('^0+$', '', regex=True).str.strip()
                if key == 'phone': 
                    valid = (self.df[col].str.len() == 10) & self.df[col].str.startswith('3')
                else: 
                    valid = (self.df[col].str.len() == 7) | ((self.df[col].str.len() == 10) & self.df[col].str.startswith('3'))
                inval = ~valid
                if inval.any():
                    count_clean += inval.sum()
                    self.df.loc[inval, col] = ''
        self._log(f"Teléfonos borrados por formato inválido: {count_clean}")

        if 'periodicity' in self.map:
            self.df[self.map['periodicity']] = '05'

    def _final_cleanup(self):
        cols_skip = [self.map[k] for k in ['initial_value', 'balance_due', 'available_value', 'monthly_fee', 'arrears_value', 'actual_value_paid'] if k in self.map]
        cols_txt = self.df.columns.drop(cols_skip)
        for col in cols_txt:
            self.df[col] = self.df[col].astype(str).str.strip().replace(r'(?i)^nan$', '', regex=True).fillna('')

    def _apply_padding_formats(self):
        print("\n>>> PASO 7: Aplicando Longitudes Fijas (Padding)")
        
        # 1. FORZAR VALORES A '0' (Regla de Negocio Estricta)
        # Esto sobrescribe cualquier dato que venga del archivo plano original.
        cols_force_zero = [
            'VALOR DISPONIBLE', 
            'ESTADO ORIGEN DE LA CUENTA', 
            'SITUACION DEL TITULAR', 
            'ADJETIVO'
        ]
        
        for col in cols_force_zero:
            # Asignamos '0' a toda la columna. Si no existe, la crea.
            self.df[col] = '0'

        # 2. DEFINIR FORMATOS (Padding)
        # Agregamos 'VALOR DISPONIBLE' y 'V CUOTA MENSUAL' aquí para que tengan su longitud correcta.
        pads = {
            # --- ZFILL (Ceros a la izquierda) ---
            'arrears_age': ('zfill', 3),
            'account_number': ('zfill', 18),      # NUMERO DE LA CUENTA
            'phone': ('zfill', 12),               # CELULAR
            'id_number': ('zfill', 11),           # NUMERO IDENTIFICACION
            'responsable': ('zfill', 2),
            'novedad': ('zfill', 2),
            'total_cuotas': ('zfill', 3),
            'cuotas_canceladas': ('zfill', 3),
            'cuotas_mora': ('zfill', 3),
            'estado_cuenta': ('zfill', 2),
            'fecha_adjetivo': ('zfill', 8),
            'clausula': ('zfill', 3),
            'fecha_clausula': ('zfill', 8),
            'city': ('ljust', 20),
            'full_name':('ljust',45),# EDAD DE MORA
            'department': ('ljust', 20),
            'email': ('ljust', 60),
            'address':('ljust',60),
            'departament': ('ljust', 20),
            'company_phone': ('ljust', 20)
        }

        # 3. APLICAR FORMATOS
        for key, (metodo, length) in pads.items():
            col_name = key
            
            # A. Intentar buscar por mapa
            if key in self.map:
                col_name = self.map[key]
            
            # B. Verificar existencia y aplicar
            if col_name in self.df.columns:
                self.df[col_name] = self.df[col_name].astype(str).str.strip().replace(['nan', 'NaN', 'None'], '')
                
                if metodo == 'zfill':
                    self.df[col_name] = self.df[col_name].str.zfill(length)
                else: # ljust
                    self.df[col_name] = self.df[col_name].str.ljust(length)
            else:
                pass

        self._log("Padding aplicado y columnas limpiadas.")


    def _save_final_state_to_excel(self):
        print("\n>>> PASO 8: Actualizando Base de Datos (Excel)")
        try:
            c_cta = self.map['account_number']
            c_val = self.map['initial_value']
            df_exp = self.df[[c_cta, c_val]].copy()
            df_exp[c_cta] = df_exp[c_cta].astype(str).str.strip().str.lstrip('0')
            df_exp.columns = ['NUMERO DE LA CUENTA U OBLIGACION', 'VALOR INICIAL']
            
            with pd.ExcelWriter(self.ruta_correcciones, mode='a', engine='openpyxl', if_sheet_exists='replace') as writer:
                df_exp.to_excel(writer, sheet_name='SALDOS_INICIALES', index=False)
            self._log("✅ Hoja 'SALDOS_INICIALES' actualizada para la próxima ejecución.")
        except Exception as e:
            self._log(f"⚠️ No se pudo guardar SALDOS_INICIALES: {e}")