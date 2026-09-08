from tkinter import filedialog, messagebox
from pathlib import Path

# MOTIVO (hilos): tkinter no es thread-safe. El trabajo pesado corre en un hilo
# gestionado por TaskRunner y TODO lo que toca la UI ocurre en el hilo principal.
from src.utils.task_runner import get_default_runner
from src.services.base.processing_orchestrator_service import ProcessingOrchestratorService
from src.services.base.file_handler_service import FileHandlerService


class BaseMensualController:
    def __init__(self, view=None):
        self.view = view
        self.rutas_archivos = {}
        self.ruta_reporte_base = None
        self.runner = None  # lo asigna la app al arrancar (TaskRunner)
        self.file_handler_service = FileHandlerService()

    def set_view(self, view):
        self.view = view

    def seleccionar_archivo(self, tipo_archivo):
        """Abre un diálogo para seleccionar uno o varios archivos (hilo principal)."""
        filetypes = [("Excel files", "*.xlsx *.XLSX *.xls *.XLS")]

        if tipo_archivo in ["ANALISIS", "R91", "VENCIMIENTOS", "R03"]:
            rutas = filedialog.askopenfilenames(title=f"Seleccione archivos para {tipo_archivo}", filetypes=filetypes)
        else:
            ruta_unica = filedialog.askopenfilename(title=f"Seleccione archivo para {tipo_archivo}", filetypes=filetypes)
            rutas = [ruta_unica] if ruta_unica else []

        if rutas:
            self.rutas_archivos[tipo_archivo] = list(rutas)
            display_text = Path(rutas[0]).name
            if len(rutas) > 1:
                display_text = f"{len(rutas)} archivos seleccionados"

            if self.view:
                self.view.actualizar_ruta_label(tipo_archivo, display_text)

    def seleccionar_reporte_base(self):
        """Abre un diálogo para seleccionar el archivo Excel del reporte anterior."""
        filetypes = [("Excel files", "*.xlsx *.xls")]
        ruta = filedialog.askopenfilename(title="Seleccione el Reporte de Excel Anterior", filetypes=filetypes)

        if ruta:
            self.ruta_reporte_base = ruta
            if self.view:
                # MOTIVO: el campo es un Entry con StringVar (estilo común de la UI).
                self.view.base_report_path_var.set(Path(ruta).name)

    # ------------------------------------------------------------ proceso
    def procesar_archivos(self):
        """Inicia el procesamiento en un hilo sin congelar la UI.

        MOTIVO: antes los valores de la UI se leían desde el hilo y los diálogos
        se abrían dentro del worker (riesgo de cuelgues). Ahora se capturan los
        datos en el hilo principal y se delega el trabajo pesado al TaskRunner.
        """
        view = self.view
        if view is None:
            return

        runner = getattr(self, "runner", None) or get_default_runner()
        if runner is None:
            # Sin runner (tests/preview): ejecución síncrona como antes.
            self._procesar_sync()
            return

        if runner.is_busy("base_mensual"):
            messagebox.showwarning("Proceso en curso", "Ya hay un proceso de Base Mensual ejecutándose.")
            return

        # 1. Capturar datos de la UI en el hilo principal (antes se hacía en el hilo).
        modo_actualizacion = view.update_mode_var.get()
        start_date = view.start_date_entry.get() or None
        end_date = view.end_date_entry.get() or None
        lista_final_rutas = [ruta for lista in self.rutas_archivos.values() for ruta in lista]

        view.procesar_button.configure(state="disabled")
        view.actualizar_estado("Iniciando proceso...", 0)

        # 2. Trabajo pesado en un hilo; el progreso llega por actualizar_estado
        #    (método marcado @main_thread, así que se ejecuta en el hilo principal).
        def worker():
            orchestrator = ProcessingOrchestratorService(
                progress_callback=view.actualizar_estado)
            return orchestrator.execute_processing(
                file_paths=lista_final_rutas,
                update_mode=modo_actualizacion,
                base_report_path=self.ruta_reporte_base,
                start_date=start_date,
                end_date=end_date,
            )

        runner.submit("base_mensual", worker,
                      on_done=lambda result: self._guardar_y_finalizar(result, view),
                      on_error=lambda exc: self._manejar_error(exc, view))

    def _procesar_sync(self):
        """Fallback sin runner: mismo flujo pero síncrono (no usado en la app real)."""
        try:
            self._guardar_y_finalizar(
                ProcessingOrchestratorService(
                    progress_callback=self.view.actualizar_estado).execute_processing(
                        file_paths=[r for l in self.rutas_archivos.values() for r in l],
                        update_mode=self.view.update_mode_var.get(),
                        base_report_path=self.ruta_reporte_base,
                        start_date=self.view.start_date_entry.get() or None,
                        end_date=self.view.end_date_entry.get() or None),
                self.view)
        except Exception as e:
            self._manejar_error(e, self.view)

    # ------------------------------------------ callbacks (hilo principal)
    def _guardar_y_finalizar(self, result_dataframes, view):
        """Pide dónde guardar (main) y delega la escritura pesada a un worker.

        MOTIVO (bug): guardar el Excel con estilos por celda en el hilo principal
        congelaba la UI y podía hacer que otros workers alcanzaran el timeout.
        Ahora el diálogo se pide aquí y la escritura corre en un hilo del runner.
        """
        runner = getattr(self, "runner", None) or get_default_runner()
        view.actualizar_estado("Esperando para guardar el archivo...", 90)

        nombre_archivo_salida = filedialog.asksaveasfilename(
            title="Guardar reporte como...",
            defaultextension=".xlsx",
            filetypes=[("Archivos de Excel", "*.xlsx"), ("Todos los archivos", "*.*")],
            initialfile="Reporte_Base.xlsx",
        )
        if not nombre_archivo_salida:
            view.actualizar_estado("Guardado cancelado por el usuario.", 0)
            messagebox.showinfo("Cancelado", "La operación de guardado fue cancelada.")
            self._reactivar_boton(view)
            return

        def _guardar_ahora():
            self.file_handler_service.save_report_to_excel(nombre_archivo_salida, result_dataframes)
            return True

        def _ok(_r):
            view.actualizar_estado("¡Éxito! Reporte guardado.", 100)
            messagebox.showinfo("Proceso Completado",
                                f"El reporte ha sido guardado exitosamente en:\n{nombre_archivo_salida}")
            self._reactivar_boton(view)

        if runner is None:
            try:
                _guardar_ahora()
                _ok(None)
            except Exception as e:
                self._manejar_error(e, view)
            return

        view.actualizar_estado("Guardando archivo...", 95)
        if not runner.submit("base_mensual_save", _guardar_ahora,
                             on_done=_ok, on_error=lambda exc: self._manejar_error(exc, view)):
            # Fallback ante carrera rara en el runner.
            try:
                _guardar_ahora()
                _ok(None)
            except Exception as e:
                self._manejar_error(e, view)

    def _manejar_error(self, error, view):
        """Muestra el error y deja la UI lista (hilo principal)."""
        try:
            if view is not None and view.winfo_exists():
                view.actualizar_estado(f"Error: {error}", 0)
                messagebox.showerror("Error en el Proceso", f"Ocurrió un error: {error}")
        finally:
            self._reactivar_boton(view)

    def _reactivar_boton(self, view):
        """Rehabilita el botón de proceso (solo desde el hilo principal)."""
        if view is not None:
            try:
                view.procesar_button.configure(state="normal")
            except Exception:
                pass
