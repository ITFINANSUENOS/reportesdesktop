import os
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
        # ... (Este método no cambia)
        if pd.isna(id_val):
            return None 
        id_str = str(id_val).strip() 
        if id_str.endswith('.0'):
            id_str = id_str[:-2]
        return id_str

    # --- ¡MÉTODO MODIFICADO! ---
    # Ahora devuelve TRES valores:
    # 1. df_nuevos (para el .txt)
    # 2. df_nuevos_para_excel (para el reporte Excel)
    # 3. total_nuevos (conteo)
    def _filtrar_y_actualizar_maestro(self, df_todos_usuarios: pd.DataFrame, maestro_excel_path: str) -> tuple[pd.DataFrame, pd.DataFrame, int]:
        """
        1. Carga el maestro Excel.
        2. Filtra el DataFrame de todos los usuarios para encontrar solo los nuevos.
        3. Actualiza el maestro Excel con esos nuevos usuarios.
        4. Devuelve el DataFrame de *solo* los nuevos (columnas originales)
           Y el DataFrame de nuevos (listo para Excel) y el conteo.
        """
        self.view.main_window.update_status("Paso 3.1: Cargando maestro Excel...")
        
        # --- ¡NUEVO! Inicializar df_nuevos_para_excel aquí ---
        df_nuevos_para_excel = pd.DataFrame() 
        
        try:
            df_excel = pd.read_excel(maestro_excel_path)
            if 'IDENTIFICACION' in df_excel.columns:
                 df_excel['IDENTIFICACION'] = df_excel['IDENTIFICACION'].astype(str)
        except FileNotFoundError:
            df_excel = pd.DataFrame(columns=['IDENTIFICACION', 'NOMBRE', 'CORREO'])
        
        ids_existentes_brutos = df_excel['IDENTIFICACION'].apply(self._normalizar_id)
        ids_existentes = set(id_str for id_str in ids_existentes_brutos if id_str)
        self.view.main_window.update_status(f"Paso 3.2: {len(ids_existentes)} IDs cargados del maestro.")

        self.view.main_window.update_status("Paso 3.3: Filtrando clientes nuevos...")
        if 'Cedula_Cliente' not in df_todos_usuarios.columns:
            raise KeyError("El DataFrame de usuarios no contiene la columna 'Cedula_Cliente'")

        df_todos_usuarios['ID_Normalizado'] = df_todos_usuarios['Cedula_Cliente'].apply(self._normalizar_id)
        
        df_nuevos = df_todos_usuarios[
            ~df_todos_usuarios['ID_Normalizado'].isin(ids_existentes) & 
            df_todos_usuarios['ID_Normalizado'].notna() &
            (df_todos_usuarios['ID_Normalizado'] != '')
        ].copy()

        total_nuevos = len(df_nuevos)
        self.view.main_window.update_status(f"Paso 3.4: Se encontraron {total_nuevos} clientes nuevos.")

        if total_nuevos > 0:
            self.view.main_window.update_status(f"Paso 3.5: Actualizando maestro Excel con {total_nuevos} registros...")
            
            nuevos_para_excel_list = []
            for _, row in df_nuevos.iterrows():
                nombre_limpio = self.plano_service._limpiar_nombre_cliente(row['Nombre_Cliente'])
                correo_valido = self.plano_service._validar_y_formatear_correo(row['Correo'])
                
                nuevos_para_excel_list.append({
                    'IDENTIFICACION': row['ID_Normalizado'],
                    'NOMBRE': nombre_limpio,
                    'CORREO': correo_valido
                })

            # ¡Guardamos esto para devolverlo!
            df_nuevos_para_excel = pd.DataFrame(nuevos_para_excel_list)
            df_nuevos_para_excel.drop_duplicates(subset=['IDENTIFICACION'], keep='first', inplace=True)

            df_actualizado = pd.concat([df_excel, df_nuevos_para_excel], ignore_index=True)
            
            try:
                # Esta lógica de guardar en el maestro original se mantiene
                df_actualizado.to_excel(maestro_excel_path, index=False)
                self.view.main_window.update_status(f"Paso 3.6: Maestro Excel actualizado.")
            except Exception as e:
                 raise Exception(f"No se pudo guardar el Excel '{maestro_excel_path}'. ¿Está abierto? ({e})")

        # --- ¡CAMBIO EN EL RETURN! ---
        return df_nuevos.drop(columns=['ID_Normalizado']), df_nuevos_para_excel, total_nuevos

    # --- ¡MÉTODO PRINCIPAL MODIFICADO! ---
    def iniciar_proceso_completo(self):
        """Orquesta la ejecución para CLIENTES con la nueva lógica de guardado."""
        self.view.main_window.update_status("Iniciando proceso Clientes...")
        vencimientos_paths = self.rutas_archivos.get("PROCESO_VENCIMIENTOS")
        consulta_path = self.rutas_archivos.get("PROCESO_CONSULTA")
        maestro_path = self.rutas_archivos.get("PROCESO_MAESTRO_CLIENTES")

        if not vencimientos_paths or not consulta_path or not maestro_path:
            self.view.main_window.update_status("Error (Clientes): Por favor, seleccione todos los archivos (Vencimientos, Consulta y Maestro de Clientes).")
            return
            
        # --- ¡NUEVO! PASO 0: Pedir el directorio de guardado UNA SOLA VEZ ---
        self.view.main_window.update_status("Paso 0: Seleccione la carpeta de destino...")
        base_save_dir = filedialog.askdirectory(
            title="Seleccione la carpeta donde se guardará la subcarpeta 'planos-ecollect'"
        )
        if not base_save_dir:
            self.view.main_window.update_status("Proceso Clientes cancelado (Paso 0).")
            return

        # Crear la carpeta de salida
        output_folder = os.path.join(base_save_dir, "planos-ecollect")
        try:
            os.makedirs(output_folder, exist_ok=True)
        except Exception as e:
            self.view.main_window.update_status(f"Error al crear carpeta de salida: {e}")
            return
        
        self.view.main_window.update_status(f"Archivos se guardarán en: {output_folder}")
        # --- FIN DE LO NUEVO ---

        try:
            # --- PASO 1: (Modificado el guardado) ---
            self.view.main_window.update_status("Paso 1/4 (Clientes): Procesando plano de cartera...")
            df_cartera = self.ecollect_service.process_vencimientos(vencimientos_paths)
            if df_cartera is None or df_cartera.empty:
                self.view.main_window.update_status("Error (Clientes): No se encontraron datos para el plano de cartera.")
                return
            
            # --- ¡MODIFICADO! Ya no pregunta, usa la ruta generada ---
            fecha_hoy_cartera = pd.Timestamp.now().strftime('%Y%m%d')
            nombre_sugerido_cartera = f"carga_cartera_{fecha_hoy_cartera}_10791 CLIENTES .txt"
            save_path_cartera = os.path.join(output_folder, nombre_sugerido_cartera)
            
            success_cartera = self.plano_service.generar_archivo_plano(df_cartera, save_path_cartera)
            if not success_cartera:
                self.view.main_window.update_status("Error (Clientes) al guardar el archivo de cartera.")
                return
            self.view.main_window.update_status(f"Paso 1/4 (Clientes) completado: Plano de cartera guardado.")

            # --- PASO 2: (Sin cambios) ---
            self.view.main_window.update_status("Paso 2/4 (Clientes): Cruzando datos de usuarios (TODOS)...")
            df_usuarios_TODOS = self.usuarios_service.crear_dataframe_usuarios(
                list(vencimientos_paths), consulta_path
            )
            if df_usuarios_TODOS is None or df_usuarios_TODOS.empty:
                self.view.main_window.update_status("Error (Clientes): No se pudo generar la lista de usuarios.")
                return
            self.view.main_window.update_status(f"Paso 2/4 (Clientes) completado: {len(df_usuarios_TODOS)} usuarios totales encontrados.")
            
            # --- PASO 3: (Modificado el return) ---
            self.view.main_window.update_status("Paso 3/4 (Clientes): Filtrando clientes nuevos y actualizando maestro...")
            
            # --- ¡MODIFICADO! Captura los 3 valores ---
            df_usuarios_NUEVOS, df_excel_NUEVOS, total_nuevos = self._filtrar_y_actualizar_maestro(
                df_usuarios_TODOS,
                maestro_path
            )
            
            if total_nuevos == 0:
                self.view.main_window.update_status("Proceso Clientes completado. No se encontraron clientes nuevos.")
                return # Termina el proceso, no hay más archivos que generar

            # --- PASO 4: Generar .txt y .xlsx de NUEVOS ---
            
            # --- ¡NUEVO! Guardar el Excel de nuevos clientes ---
            self.view.main_window.update_status(f"Paso 4.1: Generando Excel de {total_nuevos} clientes nuevos...")
            fecha_hoy_excel = pd.Timestamp.now().strftime('%Y%m%d')
            nombre_excel_nuevos = f"reporte_nuevos_clientes_{fecha_hoy_excel}.xlsx"
            save_path_excel_nuevos = os.path.join(output_folder, nombre_excel_nuevos)
            
            try:
                df_excel_NUEVOS.to_excel(save_path_excel_nuevos, index=False)
                self.view.main_window.update_status(f"Reporte Excel de nuevos clientes guardado.")
            except Exception as e:
                # No detener el proceso, solo advertir
                self.view.main_window.update_status(f"Advertencia: No se pudo guardar el Excel de nuevos clientes: {e}")

            # --- ¡MODIFICADO! Guardar el .txt de nuevos ---
            self.view.main_window.update_status(f"Paso 4.2: Generando plano de texto para los {total_nuevos} clientes nuevos...")
            fecha_hoy_usuarios = pd.Timestamp.now().strftime('%Y%m%d')
            nombre_sugerido_usuarios = f"USU10791_{fecha_hoy_usuarios} CLIENTES NUEVOS.txt"
            
            # Ya no pregunta, usa la ruta generada
            save_path_usuarios = os.path.join(output_folder, nombre_sugerido_usuarios)
            
            success_usuarios = self.plano_service.generar_plano_usuarios(df_usuarios_NUEVOS, save_path_usuarios)
            
            if success_usuarios:
                self.view.main_window.update_status(f"¡Proceso Clientes completado! Plano .txt y Reporte .xlsx guardados.")
                self.view.main_window.update_status("El maestro Excel también fue actualizado.")
            else:
                self.view.main_window.update_status("Error (Clientes) al generar el plano de usuarios nuevos.")
                
        except Exception as e:
            error_msg = f"Error (Clientes) durante el procesamiento: {e}"
            self.view.main_window.update_status(error_msg)
            print(f"Error detallado (Clientes): {e}")

    # --- ¡MÉTODO MODIFICADO! (Aplicando la misma lógica de guardado) ---
    def iniciar_proceso_colaboradores(self):
        """Orquesta la ejecución para COLABORADORES con la nueva lógica de guardado."""
        self.view.main_window.update_status("Iniciando proceso Colaboradores...")
        colaboradores_path = self.rutas_archivos.get("PROCESO_COLABORADORES")
        if not colaboradores_path:
            self.view.main_window.update_status("Error (Colaboradores): Por favor, seleccione el archivo de Colaboradores.")
            return

        # --- ¡NUEVO! PASO 0: Pedir el directorio de guardado UNA SOLA VEZ ---
        self.view.main_window.update_status("Paso 0: Seleccione la carpeta de destino...")
        base_save_dir = filedialog.askdirectory(
            title="Seleccione la carpeta donde se guardará la subcarpeta 'planos-ecollect'"
        )
        if not base_save_dir:
            self.view.main_window.update_status("Proceso Colaboradores cancelado (Paso 0).")
            return

        # Crear la carpeta de salida
        output_folder = os.path.join(base_save_dir, "planos-ecollect")
        try:
            os.makedirs(output_folder, exist_ok=True)
        except Exception as e:
            self.view.main_window.update_status(f"Error al crear carpeta de salida: {e}")
            return
        
        self.view.main_window.update_status(f"Archivos se guardarán en: {output_folder}")
        # --- FIN DE LO NUEVO ---
        
        try:
            # --- PASO 1: (Modificado el guardado) ---
            self.view.main_window.update_status("Paso 1/2 (Colaboradores): Procesando cartera...")
            df_cartera_colab = self.colaboradores_service.process_cartera(colaboradores_path)
            if df_cartera_colab is None or df_cartera_colab.empty:
                self.view.main_window.update_status("Error (Colaboradores): No se encontraron datos en la hoja 'CARTERA'.")
                return
            
            # --- ¡MODIFICADO! ---
            fecha_hoy_cartera = pd.Timestamp.now().strftime('%Y%m%d')
            nombre_sugerido_cartera = f"carga_cartera_{fecha_hoy_cartera}_10791 COLAB.txt"
            save_path_cartera = os.path.join(output_folder, nombre_sugerido_cartera)
            
            success_cartera = self.plano_service.generar_archivo_plano(df_cartera_colab, save_path_cartera)
            if not success_cartera:
                self.view.main_window.update_status("Error (Colaboradores) al guardar el archivo de cartera.")
                return
            self.view.main_window.update_status("Paso 1/2 (Colaboradores) completado: Plano de cartera guardado.")

            # --- PASO 2: (Modificado el guardado) ---
            self.view.main_window.update_status("Paso 2/2 (Colaboradores): Procesando usuarios...")
            df_usuarios_colab = self.colaboradores_service.process_usuarios(colaboradores_path)

            if df_usuarios_colab is None or df_usuarios_colab.empty:
                self.view.main_window.update_status("Error (Colaboradores): No se encontraron datos en la hoja 'USUARIOS'.")
                return
            
            # --- ¡MODIFICADO! ---
            fecha_hoy_usuarios = pd.Timestamp.now().strftime('%Y%m%d')
            nombre_sugerido_usuarios = f"USU10791_{fecha_hoy_usuarios} COLAB.txt"
            save_path_usuarios = os.path.join(output_folder, nombre_sugerido_usuarios)
            
            success_usuarios = self.plano_service.generar_plano_usuarios(df_usuarios_colab, save_path_usuarios)
            
            if success_usuarios:
                self.view.main_window.update_status("¡Proceso Colaboradores completado! Archivos generados.")
            else:
                self.view.main_window.update_status("Error (Colaboradores) al generar el plano de usuarios.")

        except Exception as e:
            error_msg = f"Error (Colaboradores) durante el procesamiento: {e}"
            self.view.main_window.update_status(error_msg)
            print(f"Error detallado (Colaboradores): {e}")