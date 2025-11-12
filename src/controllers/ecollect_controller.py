from tkinter import filedialog
import pandas as pd
from src.services.ecollect.ecollect_service import EcollectService
from src.services.ecollect.plano_service import PlanoService
from src.services.ecollect.usuarios_service import UsuariosService
from src.services.ecollect.colaboradores_service import ColaboradoresService 
from src.models.ecollect_model import configuracion

# --- ¡NUEVO! ---
# Definimos las constantes de nuestro archivo .txt de usuarios aquí
# Formato: "CEDULA,01, CORREO,,NOMBRE CLIENTE,,CORREO..."
DELIMITADOR_TXT = ','
COL_ID_TXT = 0       # Posición de la cédula
COL_NOMBRE_TXT = 4   # Posición del nombre
COL_CORREO_TXT = 2   # Posición del correo
# --- FIN DE LO NUEVO ---

class EcollectController:
    def __init__(self):
        self.view = None
        self.ecollect_service = EcollectService(configuracion)
        self.plano_service = PlanoService()
        self.usuarios_service = UsuariosService(configuracion)
        self.colaboradores_service = ColaboradoresService(configuracion)
        self.rutas_archivos = {}

    def set_view(self, view):
        self.view = view

    def seleccionar_archivo(self, key: str, multiple: bool):
        # ... (Este método no cambia)
        if multiple:
            paths = filedialog.askopenfilenames(title=f"Seleccione archivo(s) para {key}")
            if paths:
                self.rutas_archivos[key] = list(paths)
                display_text = f"{len(paths)} archivo(s) seleccionado(s)"
                self.view.actualizar_ruta_label(key, display_text)
        else:
            path = filedialog.askopenfilename(title=f"Seleccione un archivo para {key}")
            if path:
                self.rutas_archivos[key] = path
                display_text = path.split('/')[-1]
                self.view.actualizar_ruta_label(key, display_text)

    def _normalizar_id(self, id_val):
        """
        Limpia un ID para la comparación, eliminando espacios,
        y el problemático '.0' que a veces añade Excel.
        """
        # ... (Este método no cambia)
        if pd.isna(id_val):
            return None 
        
        id_str = str(id_val).strip() 
        
        if id_str.endswith('.0'):
            id_str = id_str[:-2]
            
        return id_str

    # --- ¡MÉTODO MODIFICADO! ---
    # Este método ahora filtra ANTES y actualiza el Excel,
    # luego devuelve el DF de solo nuevos.
    def _filtrar_y_actualizar_maestro(self, df_todos_usuarios: pd.DataFrame, maestro_excel_path: str) -> tuple[pd.DataFrame, int]:
        """
        1. Carga el maestro Excel.
        2. Filtra el DataFrame de todos los usuarios para encontrar solo los nuevos.
        3. Actualiza el maestro Excel con esos nuevos usuarios.
        4. Devuelve el DataFrame de *solo* los nuevos usuarios y el conteo.
        """
        self.view.main_window.update_status("Paso 3.1: Cargando maestro Excel...")
        try:
            df_excel = pd.read_excel(maestro_excel_path)
            # Asegurarnos de que la columna de ID sea de tipo texto para la normalización
            if 'IDENTIFICACION' in df_excel.columns:
                 df_excel['IDENTIFICACION'] = df_excel['IDENTIFICACION'].astype(str)
        except FileNotFoundError:
            # Si no existe, creamos uno nuevo en memoria
            df_excel = pd.DataFrame(columns=['IDENTIFICACION', 'NOMBRE', 'CORREO'])
        
        # Normalizar IDs del Excel
        ids_existentes_brutos = df_excel['IDENTIFICACION'].apply(self._normalizar_id)
        ids_existentes = set(id_str for id_str in ids_existentes_brutos if id_str)
        self.view.main_window.update_status(f"Paso 3.2: {len(ids_existentes)} IDs cargados del maestro.")

        # --- Fase de Filtrado ---
        self.view.main_window.update_status("Paso 3.3: Filtrando clientes nuevos...")
        if 'Cedula_Cliente' not in df_todos_usuarios.columns:
            raise KeyError("El DataFrame de usuarios no contiene la columna 'Cedula_Cliente'")

        # Normalizar los IDs del DataFrame de usuarios para la comparación
        df_todos_usuarios['ID_Normalizado'] = df_todos_usuarios['Cedula_Cliente'].apply(self._normalizar_id)
        
        # Filtrar para obtener solo los nuevos
        df_nuevos = df_todos_usuarios[
            ~df_todos_usuarios['ID_Normalizado'].isin(ids_existentes) & 
            df_todos_usuarios['ID_Normalizado'].notna() &
            (df_todos_usuarios['ID_Normalizado'] != '')
        ].copy() # .copy() para evitar SettingWithCopyWarning

        total_nuevos = len(df_nuevos)
        self.view.main_window.update_status(f"Paso 3.4: Se encontraron {total_nuevos} clientes nuevos.")

        # --- Fase de Actualización (Escritura) ---
        if total_nuevos > 0:
            self.view.main_window.update_status(f"Paso 3.5: Actualizando maestro Excel con {total_nuevos} registros...")
            
            # Preparar los nuevos clientes para el Excel
            nuevos_para_excel_list = []
            for _, row in df_nuevos.iterrows():
                # Usamos los limpiadores de 'plano_service' para consistencia
                # (El controlador tiene acceso a self.plano_service)
                nombre_limpio = self.plano_service._limpiar_nombre_cliente(row['Nombre_Cliente'])
                correo_valido = self.plano_service._validar_y_formatear_correo(row['Correo'])
                
                nuevos_para_excel_list.append({
                    'IDENTIFICACION': row['ID_Normalizado'], # Usar el ID limpio
                    'NOMBRE': nombre_limpio,
                    'CORREO': correo_valido
                })

            df_nuevos_para_excel = pd.DataFrame(nuevos_para_excel_list)
            df_nuevos_para_excel.drop_duplicates(subset=['IDENTIFICACION'], keep='first', inplace=True)

            df_actualizado = pd.concat([df_excel, df_nuevos_para_excel], ignore_index=True)
            
            try:
                # Guardar de vuelta al archivo maestro
                df_actualizado.to_excel(maestro_excel_path, index=False)
                self.view.main_window.update_status(f"Paso 3.6: Maestro Excel actualizado.")
            except Exception as e:
                # ¡Error! El archivo puede estar abierto.
                 raise Exception(f"No se pudo guardar el Excel '{maestro_excel_path}'. ¿Está abierto? ({e})")

        # Devolver el DataFrame de *solo* los nuevos clientes
        # (El que tiene las columnas originales que 'plano_service' espera)
        return df_nuevos.drop(columns=['ID_Normalizado']), total_nuevos

    # --- ¡MÉTODO PRINCIPAL MODIFICADO! ---
    def iniciar_proceso_completo(self):
        """Orquesta la ejecución para CLIENTES con la nueva lógica de filtrado."""
        self.view.main_window.update_status("Iniciando proceso Clientes...")
        vencimientos_paths = self.rutas_archivos.get("PROCESO_VENCIMIENTOS")
        consulta_path = self.rutas_archivos.get("PROCESO_CONSULTA")
        maestro_path = self.rutas_archivos.get("PROCESO_MAESTRO_CLIENTES")

        if not vencimientos_paths or not consulta_path or not maestro_path:
            self.view.main_window.update_status("Error (Clientes): Por favor, seleccione todos los archivos (Vencimientos, Consulta y Maestro de Clientes).")
            return
            
        try:
            # --- PASO 1: (Sin cambios) ---
            self.view.main_window.update_status("Paso 1/3 (Clientes): Procesando plano de cartera...")
            df_cartera = self.ecollect_service.process_vencimientos(vencimientos_paths)
            if df_cartera is None or df_cartera.empty:
                self.view.main_window.update_status("Error (Clientes): No se encontraron datos para el plano de cartera.")
                return
            
            # (Lógica de guardar plano de cartera sin cambios)
            fecha_hoy_cartera = pd.Timestamp.now().strftime('%Y%m%d')
            nombre_sugerido_cartera = f"carga_cartera_{fecha_hoy_cartera}_10791 CLIENTES .txt"
            save_path_cartera = filedialog.asksaveasfilename(
                title="Guardar Plano de Cartera (Clientes) como...",
                initialfile=nombre_sugerido_cartera,
                defaultextension=".txt",
                filetypes=[("Archivos de Texto", "*.txt"), ("Todos los archivos", "*.*")]
            )
            if not save_path_cartera:
                self.view.main_window.update_status("Proceso Clientes cancelado (Paso 1).")
                return
            success_cartera = self.plano_service.generar_archivo_plano(df_cartera, save_path_cartera)
            if not success_cartera:
                self.view.main_window.update_status("Error (Clientes) al guardar el archivo de cartera.")
                return
            self.view.main_window.update_status(f"Paso 1/3 (Clientes) completado: Plano de cartera guardado.")

            # --- PASO 2: (Modificado) ---
            self.view.main_window.update_status("Paso 2/3 (Clientes): Cruzando datos de usuarios (TODOS)...")
            df_usuarios_TODOS = self.usuarios_service.crear_dataframe_usuarios(
                list(vencimientos_paths), consulta_path
            )
            if df_usuarios_TODOS is None or df_usuarios_TODOS.empty:
                self.view.main_window.update_status("Error (Clientes): No se pudo generar la lista de usuarios.")
                return
            self.view.main_window.update_status(f"Paso 2/3 (Clientes) completado: {len(df_usuarios_TODOS)} usuarios totales encontrados.")
            
            # --- PASO 3: (Nueva Lógica) ---
            # Filtrar, actualizar Excel, y obtener el DF de solo nuevos
            self.view.main_window.update_status("Paso 3/3 (Clientes): Filtrando clientes nuevos y actualizando maestro...")
            
            # Este método ahora hace el trabajo pesado:
            # Carga Excel, filtra, guarda Excel, y devuelve los nuevos.
            df_usuarios_NUEVOS, total_nuevos = self._filtrar_y_actualizar_maestro(
                df_usuarios_TODOS,
                maestro_path
            )
            
            if total_nuevos == 0:
                self.view.main_window.update_status("Proceso Clientes completado. No se encontraron clientes nuevos.")
                return # Termina el proceso, no hay .txt que generar

            # --- PASO 4 (era parte del 2): Guardar el .txt DE SOLO NUEVOS ---
            self.view.main_window.update_status(f"Generando plano de texto para los {total_nuevos} clientes nuevos...")
            fecha_hoy_usuarios = pd.Timestamp.now().strftime('%Y%m%d')
            # Actualizamos el nombre sugerido para reflejar que son solo nuevos
            nombre_sugerido_usuarios = f"USU10791_{fecha_hoy_usuarios} CLIENTES NUEVOS.txt"
            save_path_usuarios = filedialog.asksaveasfilename(
                title="Guardar Plano de Usuarios (SÓLO NUEVOS) como...", # Título actualizado
                initialfile=nombre_sugerido_usuarios,
                defaultextension=".txt",
                filetypes=[("Archivos de Texto", "*.txt"), ("CSV", "*.csv"), ("Todos los archivos", "*.*")]
            )
            if not save_path_usuarios:
                self.view.main_window.update_status("Proceso Clientes cancelado (Guardado de .txt).")
                self.view.main_window.update_status("NOTA: El archivo maestro de Excel SÍ FUE actualizado.")
                return
            
            # Pasamos el DataFrame FILTRADO al servicio
            success_usuarios = self.plano_service.generar_plano_usuarios(df_usuarios_NUEVOS, save_path_usuarios)
            
            if success_usuarios:
                self.view.main_window.update_status(f"¡Proceso Clientes completado! Plano .txt con {total_nuevos} nuevos clientes guardado.")
                self.view.main_window.update_status("El maestro Excel también fue actualizado.")
            else:
                self.view.main_window.update_status("Error (Clientes) al generar el plano de usuarios nuevos.")
                
        except Exception as e:
            error_msg = f"Error (Clientes) durante el procesamiento: {e}"
            self.view.main_window.update_status(error_msg)
            print(f"Error detallado (Clientes): {e}")

    # --- El proceso de Colaboradores no cambia ---
    def iniciar_proceso_colaboradores(self):
        # ... (Resto del método sin cambios) ...
        self.view.main_window.update_status("Iniciando proceso Colaboradores...")
        colaboradores_path = self.rutas_archivos.get("PROCESO_COLABORADORES")
        if not colaboradores_path:
            self.view.main_window.update_status("Error (Colaboradores): Por favor, seleccione el archivo de Colaboradores.")
            return
        try:
            # ... (Toda la lógica de colaboradores sigue igual) ...
            self.view.main_window.update_status("Paso 1/2 (Colaboradores): Procesando cartera...")
            df_cartera_colab = self.colaboradores_service.process_cartera(colaboradores_path)
            if df_cartera_colab is None or df_cartera_colab.empty:
                self.view.main_window.update_status("Error (Colaboradores): No se encontraron datos en la hoja 'CARTERA' o hubo un error al leerla.")
                return
            fecha_hoy_cartera = pd.Timestamp.now().strftime('%Y%m%d')
            nombre_sugerido_cartera = f"carga_cartera_{fecha_hoy_cartera}_10791 COLAB.txt"
            save_path_cartera = filedialog.asksaveasfilename(
                title="Guardar Plano de Cartera (Colaboradores) como...",
                initialfile=nombre_sugerido_cartera,
                defaultextension=".txt",
                filetypes=[("Archivos de Texto", "*.txt"), ("Todos los archivos", "*.*")]
            )
            if not save_path_cartera:
                self.view.main_window.update_status("Proceso Colaboradores cancelado (Paso 1).")
                return
            success_cartera = self.plano_service.generar_archivo_plano(df_cartera_colab, save_path_cartera)
            if not success_cartera:
                self.view.main_window.update_status("Error (Colaboradores) al guardar el archivo de cartera.")
                return
            self.view.main_window.update_status("Paso 1/2 (Colaboradores) completado: Plano de cartera guardado.")
            self.view.main_window.update_status("Paso 2/2 (Colaboradores): Procesando usuarios...")
            df_usuarios_colab = self.colaboradores_service.process_usuarios(colaboradores_path)

            if df_usuarios_colab is None or df_usuarios_colab.empty:
                self.view.main_window.update_status("Error (Colaboradores): No se encontraron datos en la hoja 'USUARIOS' o hubo un error al leerla.")
                return
            fecha_hoy_usuarios = pd.Timestamp.now().strftime('%Y%m%d')
            nombre_sugerido_usuarios = f"USU10791_{fecha_hoy_usuarios} COLAB.txt"
            save_path_usuarios = filedialog.asksaveasfilename(
                title="Guardar Plano de Usuarios (Colaboradores) como...",
                initialfile=nombre_sugerido_usuarios,
                defaultextension=".txt",
                filetypes=[("Archivos de Texto", "*.txt"), ("CSV", "*.csv"), ("Todos los archivos", "*.*")]
            )
            if not save_path_usuarios:
                self.view.main_window.update_status("Proceso Colaboradores cancelado (Paso 2).")
                return
            
            success_usuarios = self.plano_service.generar_plano_usuarios(df_usuarios_colab, save_path_usuarios)
            
            if success_usuarios:
                self.view.main_window.update_status("¡Proceso Colaboradores completado! Archivos generados.")
            else:
                self.view.main_window.update_status("Error (Colaboradores) al generar el plano de usuarios.")

        except Exception as e:
            error_msg = f"Error (Colaboradores) durante el procesamiento: {e}"
            self.view.main_window.update_status(error_msg)
            print(f"Error detallado (Colaboradores): {e}")