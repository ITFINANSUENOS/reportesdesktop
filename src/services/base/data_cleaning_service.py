import pandas as pd
import numpy as np
import re
import Levenshtein 

class DataCleaningService:
    """
    Servicio dedicado a la limpieza final de datos del reporte,
    aplicando validaciones estrictas y estandarizando valores.
    """
    def _tiene_diversidad(self, texto: str, umbral: int = 3) -> bool:
        """
        Verifica si el texto tiene un número mínimo de caracteres alfabéticos únicos.
        """
        if not isinstance(texto, str):
            return False
        letras_unicas = set(c for c in texto.lower() if c.isalpha())
        return len(letras_unicas) >= umbral

    def _es_correo_valido_estricto(self, correo: str) -> bool:
        """
        Valida un correo electrónico usando una lógica estricta y avanzada.
        """
        if not isinstance(correo, str) or not correo:
            return False
        correo = correo.strip()
        pattern = re.compile(
            r"^(?![.-])(?!(?:.*[.]{2}))[A-Z0-9._%+-ñÑ]{3,}@[A-Z0-9.-]{3,}\.[A-Z]{2,}$",
            re.IGNORECASE
        )
        if not pattern.match(correo):
            return False
        try:
            usuario, _ = correo.split('@', 1)
            usuario = usuario.lower()
        except ValueError:
            return False # No tiene un solo @

        if usuario.isdigit():
            return False
            
        if not self._tiene_diversidad(usuario):
            return False

        blacklist = [
            "notiene", "sincorreo", "pendiente", "corregir", "noregistra",
            "nulo", "ninguno", "vacio", "nodisponible"
        ]
        for item_prohibido in blacklist:
            # Comparamos si el usuario es muy similar a una palabra prohibida
            if Levenshtein.distance(usuario, item_prohibido) <= 2:
                return False

        return True

    def clean_email_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aplica la validación estricta a la columna 'Correo' y limpia los inválidos.
        """
        print("🧼 Limpiando la columna 'Correo' con validación estricta...")
        if 'Correo' in df.columns:
            # Creamos una máscara booleana: True para correos válidos, False para inválidos
            mask_validos = df['Correo'].apply(self._es_correo_valido_estricto)
            
            # Contamos cuántos se van a limpiar para informar al usuario
            invalid_count = (~mask_validos).sum()
            if invalid_count > 0:
                print(f"   - ⚠️ Se encontraron {invalid_count} correos inválidos que serán reemplazados.")
            
            # Reemplazamos los correos inválidos (donde la máscara es False) por NaN
            df.loc[~mask_validos, 'Correo'] = np.nan
        else:
            print("   - ℹ️ Columna 'Correo' no encontrada. Se omite la limpieza.")
            
        return df
    
    def _obtener_serie_valida(self, series: pd.Series, solo_10_digitos: bool = False) -> pd.Series:
        s_temp = series.astype(str)
        s_temp = s_temp.str.replace(r'\.0$', '', regex=True)
        telefonos_limpios = s_temp.str.replace(r'\D', '', regex=True)

        # Reglas de 10 dígitos (Celular y Fijo Nacional)
        es_celular_valido = (telefonos_limpios.str.len() == 10) & (telefonos_limpios.str.startswith('3'))
        es_fijo_nacional_valido = (telefonos_limpios.str.len() == 10) & (telefonos_limpios.str.startswith('60'))
        
        # Regla de 7 dígitos (Fijo Local)
        prefijos_fijos_validos = ('2', '4', '5', '6', '7', '8')
        es_fijo_local_valido = (telefonos_limpios.str.len() == 7) & (telefonos_limpios.str.startswith(prefijos_fijos_validos))
        
        no_son_repetidos = telefonos_limpios.apply(lambda x: len(set(x)) > 1 if len(x) > 0 else False)
        
        if solo_10_digitos:
            mask_formato_valido = (es_celular_valido | es_fijo_nacional_valido)
        else:
            mask_formato_valido = (es_celular_valido | es_fijo_nacional_valido | es_fijo_local_valido)


        mask_final_valido = mask_formato_valido & no_son_repetidos
        return telefonos_limpios.where(mask_final_valido, np.nan)

    def clean_phone_numbers(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Limpia y valida números de teléfono en columnas específicas.
        (Refactorizado para usar _obtener_serie_valida, manteniendo la funcionalidad original).
        """
        print("📞 Limpiando y validando números de teléfono (lógica estricta)...")
        columnas_telefono = ['Celular', 'Telefono_Codeudor1', 'Telefono_Codeudor2']
        
        for col in columnas_telefono:
            if col not in df.columns:
                continue # Si no existe, pasa silenciosamente como en tu original o imprime log
            
            mask_sin_codeudor = df[col] == 'SIN CODEUDOR'
            
            # Usamos la lógica centralizada
            serie_validada = self._obtener_serie_valida(df[col])
            
            # Asignamos
            df[col] = serie_validada
            
            # Relleno de NaNs según tu lógica original
            valor_relleno = '' if col == 'Celular' else 'SIN CODEUDOR'
            df[col] = df[col].fillna(valor_relleno)
            
            # Restauramos SIN CODEUDOR explícitos originales si es necesario
            df.loc[mask_sin_codeudor, col] = 'SIN CODEUDOR'
            
            print(f"   - ✅ Columna '{col}' procesada.")

        return df

    def unificar_telefonos_codeudores(self, df: pd.DataFrame, col_principal: str, col_secundaria: str, col_destino: str, valor_defecto: str = 'SIN CODEUDOR', solo_10_digitos: bool = False) -> pd.DataFrame:
        """
        Ahora acepta el parámetro 'solo_10_digitos' para pasarlo a la validación.
        """
        print(f"   - 🔄 Unificando teléfonos para {col_destino}...")
        
        # 1. Validar ambas columnas pasando el flag de estricto
        s_principal_valida = pd.Series(np.nan, index=df.index)
        if col_principal in df.columns:
            s_principal_valida = self._obtener_serie_valida(df[col_principal], solo_10_digitos=solo_10_digitos)

        s_secundaria_valida = pd.Series(np.nan, index=df.index)
        if col_secundaria and col_secundaria in df.columns:
            s_secundaria_valida = self._obtener_serie_valida(df[col_secundaria], solo_10_digitos=solo_10_digitos)
        
        # 2. Aplicar la lógica de selección
        df[col_destino] = np.where(
            s_principal_valida.notna(), 
            s_principal_valida, 
            s_secundaria_valida
        )
        
        # 3. Llenar vacíos
        df[col_destino] = df[col_destino].fillna(valor_defecto)
        
        return df
    
    def run_cleaning_pipeline(self, reporte_df: pd.DataFrame) -> pd.DataFrame:
        """
        Punto de entrada principal para ejecutar todos los pasos de limpieza.
        Por ahora, solo limpia los correos, pero puedes añadir más pasos aquí en el futuro.
        """
        print("\n--- 🧹 Iniciando pipeline de limpieza final ---")
        reporte_df = self.clean_email_column(reporte_df)
        reporte_df = self.clean_phone_numbers(reporte_df)
        print("--- ✅ Pipeline de limpieza final completado ---\n")
        return reporte_df