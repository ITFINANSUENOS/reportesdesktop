from tkinter import filedialog, messagebox
import threading
from pathlib import Path

# Importaciones de servcios y vistas
from src.views.base_view.base_mensual_tab_view import BaseMensualView
from src.services.base.processing_orchestrator_service import (
    ProcessingOrchestratorService,
)
from src.services.base.file_handler_service import FileHandlerService


class BaseMensualController:
    def __init__(self, view=None):
        self.view = view
        self.rutas_archivos = {}
        self.ruta_reporte_base = None
        # Instanciamos el servicio de archivos para usarlo después
        self.file_handler_service = FileHandlerService()

    def set_view(self, view):
        self.view = view

    def abrir_vista(self, parent):
        """Crea y muestra la ventana para cargar la base mensual."""
        if self.view is None or not self.view.winfo_exists():
            main_controller = getattr(self.view, "main_window_controller", None)
            self.view = BaseMensualView(parent, self, main_controller)
        self.view.deiconify()

    def seleccionar_archivo(self, tipo_archivo):
        """Abre un diálogo para seleccionar uno o varios archivos."""
        filetypes = [("Excel files", "*.xlsx *.XLSX *.xls *.XLS")]

        # Esta lógica de UI se mantiene en el controlador, lo cual es correcto.
        if tipo_archivo in ["ANALISIS", "R91", "VENCIMIENTOS", "R03"]:
            rutas = filedialog.askopenfilenames(
                title=f"Seleccione archivos para {tipo_archivo}", filetypes=filetypes
            )
        else:
            ruta_unica = filedialog.askopenfilename(
                title=f"Seleccione archivo para {tipo_archivo}", filetypes=filetypes
            )
            rutas = [ruta_unica] if ruta_unica else []

        if rutas:
            self.rutas_archivos[tipo_archivo] = list(rutas)
            display_text = Path(rutas[0]).name
            if len(rutas) > 1:
                display_text = f"{len(rutas)} archivos seleccionados"

            if self.view:
                self.view.actualizar_ruta_label(tipo_archivo, display_text)
            else:
                print("Error: La vista no ha sido asignada al controlador.")

            print(f"Archivos para {tipo_archivo}: {self.rutas_archivos[tipo_archivo]}")

    def seleccionar_reporte_base(self):
        """Abre un diálogo para seleccionar el archivo Excel del reporte anterior."""
        filetypes = [("Excel files", "*.xlsx *.xls")]
        ruta = filedialog.askopenfilename(
            title="Seleccione el Reporte de Excel Anterior", filetypes=filetypes
        )

        if ruta:
            self.ruta_reporte_base = ruta
            if self.view:
                self.view.base_report_path_label.config(
                    text=Path(ruta).name, style="Success.TLabel"
                )
            print(
                f"Reporte base para actualización seleccionado: {self.ruta_reporte_base}"
            )

    def procesar_archivos(self):
        """Inicia el procesamiento en un hilo separado para no congelar la UI."""
        self.view.procesar_button.config(state="disabled")
        self.view.actualizar_estado("Iniciando proceso...", 0)

        # El hilo ahora llamará a un método mucho más limpio.
        thread = threading.Thread(target=self._ejecutar_proceso_orquestado)
        thread.start()

    def _ejecutar_proceso_orquestado(self):
        """
        Orquesta el proceso utilizando servicios, manteniendo al controlador
        libre de lógica de negocio.
        """
        try:
            # 1. Recolectar datos de la UI
            modo_actualizacion = self.view.update_mode_var.get()
            start_date = self.view.start_date_entry.get() or None
            end_date = self.view.end_date_entry.get() or None

            lista_final_rutas = [
                ruta for lista in self.rutas_archivos.values() for ruta in lista
            ]

            # 2. Instanciar y ejecutar el servicio orquestador
            # Le pasamos el método de la vista como callback para que el servicio informe el progreso.
            orchestrator = ProcessingOrchestratorService(
                progress_callback=self.view.actualizar_estado
            )

            result_dataframes = orchestrator.execute_processing(
                file_paths=lista_final_rutas,
                update_mode=modo_actualizacion,
                base_report_path=self.ruta_reporte_base,
                start_date=start_date,
                end_date=end_date,
            )

            # 3. Gestionar el guardado del archivo (interacción con el usuario)
            self.view.actualizar_estado("Esperando para guardar el archivo...", 90)
            nombre_archivo_salida = filedialog.asksaveasfilename(
                title="Guardar reporte como...",
                defaultextension=".xlsx",
                filetypes=[
                    ("Archivos de Excel", "*.xlsx"),
                    ("Todos los archivos", "*.*"),
                ],
                initialfile="Reporte_Base.xlsx",
            )

            if not nombre_archivo_salida:
                self.view.actualizar_estado("Guardado cancelado por el usuario.", 0)
                messagebox.showinfo(
                    "Cancelado", "La operación de guardado fue cancelada."
                )
                return

            # 4. Delegar el guardado al servicio de archivos
            self.file_handler_service.save_report_to_excel(
                nombre_archivo_salida, result_dataframes
            )

            self.view.actualizar_estado("¡Éxito! Reporte guardado.", 100)
            messagebox.showinfo(
                "Proceso Completado",
                f"El reporte ha sido guardado exitosamente en:\n{nombre_archivo_salida}",
            )

        except (ValueError, IOError, Exception) as e:
            # Capturamos cualquier error de los servicios y lo mostramos al usuario.
            messagebox.showerror("Error en el Proceso", f"Ocurrió un error: {str(e)}")
            self.view.actualizar_estado(f"Error: {str(e)}", 0)
        finally:
            # Aseguramos que el botón se reactive siempre.
            if self.view and self.view.winfo_exists():
                self.view.procesar_button.config(state="normal")
