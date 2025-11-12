# src/services/plano/plano_service.py
import pandas as pd
from typing import List
import re

class PlanoService:
    """
    Contiene la lógica para convertir un DataFrame procesado
    a un archivo de texto plano (.txt) con un formato específico.
    """

    def _generar_linea_encabezado(self, df: pd.DataFrame) -> str:
        """Genera la primera línea (encabezado) del archivo plano."""
        fecha_actual = pd.Timestamp.now().strftime('%Y%m%d')
        num_registros = len(df)
        
        # Suma la columna 'Valor', convierte a entero para quitar decimales, y añade '00'
        valor_total = df['Valor'].sum()
        valor_total_formateado = str(int(valor_total)) + '00'
        
        return f"1,{fecha_actual},{num_registros},{valor_total_formateado},0"

    def _formatear_descripcion(self, row: pd.Series, prefijo: str) -> str:
        """
        Crea la descripción de las cuotas basado en si la primera y última son iguales.
        Ej: "Cuota No. 5" o "Cuota No. 5 a Cuota No. 14"
        Ej: "Pago de Cuota No. 5" o "Pago de Cuota No. 5 a Cuota No. 14"
        """
        primera = row['Primera_Cuota_Atraso']
        ultima = row['Ultima_Cuota_Atraso']
        
        if primera == ultima:
            return f"{prefijo} No. {primera}"
        else:
            descriptor_base = prefijo.split(" ")[-1]
            return f"{prefijo} No. {primera} a {descriptor_base} No. {ultima}"
            # --- FIN DE LA CORRECCIÓN ---

    def _generar_lineas_datos(self, df: pd.DataFrame) -> List[str]:
        """Genera todas las líneas de datos (registros) del archivo plano."""
        lineas_datos = []
        
        for _, row in df.iterrows():
            # Formatear campos específicos
            desc_cuotas = self._formatear_descripcion(row, "Cuota")
            desc_pago = self._formatear_descripcion(row, "Pago de Cuota")
            fecha_atraso_formateada = row['Fecha_Atraso'].strftime('%Y%m%d')
            valor_formateado = str(int(row['Valor'])) + '00'
            
            # Construir la línea completa
            linea = (
                f"2,10791,1001,{row['Cedula_Cliente']},{row['Credito']},{desc_cuotas},"
                f"{row['Codigo']},{desc_pago},0,{fecha_atraso_formateada},{valor_formateado},"
                "0,0,0,0,0,0,0,0"
            )
            lineas_datos.append(linea)
            
        return lineas_datos

    def generar_archivo_plano(self, df: pd.DataFrame, ruta_guardado: str) -> bool:
        """
        Orquesta la creación del archivo .txt completo y lo guarda en la ruta especificada.
        """
        if df.empty:
            print("El DataFrame está vacío, no se generará el archivo plano.")
            return False
            
        try:
            linea_encabezado = self._generar_linea_encabezado(df)
            lineas_datos = self._generar_lineas_datos(df)
            
            with open(ruta_guardado, 'w', encoding='utf-8') as f:
                f.write(linea_encabezado + '\n')
                for linea in lineas_datos:
                    f.write(linea + '\n')
            return True
        except Exception as e:
            print(f"Error al generar o guardar el archivo plano: {e}")
            return False
        
    def _validar_y_formatear_correo(self, correo: any) -> str:
        """
        Valida si el valor es un correo electrónico simple (contiene '@').
        Devuelve el correo si es válido, o una cadena vacía si no lo es o es NaN.
        """
        if pd.isnull(correo):
            return ""
        
        correo_str = str(correo).strip()
        # Validación simple: debe contener '@' y un '.' después del '@'
        if '@' in correo_str and '.' in correo_str.split('@')[-1]:
            return correo_str
        
        return ""

    def _limpiar_nombre_cliente(self, nombre: str) -> str:
        """
        Limpia el nombre del cliente para la central:
        - Quita tildes (Á -> A)
        - Convierte Ñ -> N
        - Convierte todo a MAYÚSCULAS
        - Elimina caracteres especiales (puntos, comas, etc.)
        - Conserva solo letras (A-Z), números (0-9) y espacios.
        """
        if not isinstance(nombre, str) or pd.isnull(nombre):
            return ""
        
        nombre_limpio = str(nombre)
        
        # 1. Reemplazar tildes y caracteres especiales comunes
        reemplazos = {
            'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'Ñ': 'N', 'ñ': 'n',
            'Ü': 'U', 'ü': 'u',
            '.': '', ',': '', '-': '', '/': '',
            '(': '', ')': '', '#': '', "'": '',
            '`': '', '´': '' 
        }
        for k, v in reemplazos.items():
            nombre_limpio = nombre_limpio.replace(k, v)
            
        # 2. Convertir a mayúsculas
        nombre_limpio = nombre_limpio.upper()
        
        # 3. Eliminar cualquier caracter que no sea A-Z, 0-9, o espacio
        nombre_limpio = re.sub(r'[^A-Z0-9 ]', '', nombre_limpio)
        
        # 4. Colapsar múltiples espacios a uno solo y limpiar extremos
        nombre_limpio = re.sub(r'\s+', ' ', nombre_limpio).strip()
        
        return nombre_limpio

    def generar_plano_usuarios(self, df: pd.DataFrame, ruta_guardado: str) -> bool:
        """
        Genera un archivo plano (CSV) para la actualización de datos de usuarios
        con un formato específico.
        """
        if df.empty:
            print("El DataFrame de usuarios está vacío, no se generará el archivo.")
            return False

        try:
            lineas_a_escribir = []
            for _, row in df.iterrows():
                # Extraer y limpiar datos de las columnas requeridas
                cedula = row.get('Cedula_Cliente', '')
                nombre = row.get('Nombre_Cliente', '')
                correo = self._validar_y_formatear_correo(row.get('Correo'))

                # --- ¡NUEVO! ---
                # Aplicamos la limpieza al nombre antes de usarlo
                nombre_limpio = self._limpiar_nombre_cliente(nombre)
                # --- Fin de la adición ---

                linea = (
                    # Usamos la variable 'nombre_limpio' en lugar de 'nombre'
                    f"{cedula},01,{correo},,{nombre_limpio},,{correo},,,,,,"
                )
                lineas_a_escribir.append(linea)

            # Escribir todas las líneas al archivo de una vez
            with open(ruta_guardado, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lineas_a_escribir))
            
            return True
        except KeyError as e:
            print(f"Error de clave: La columna {e} no fue encontrada en el DataFrame de usuarios.")
            return False
        except Exception as e:
            print(f"Error al generar o guardar el plano de usuarios: {e}")
            return False
