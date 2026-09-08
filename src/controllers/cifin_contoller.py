from tkinter import messagebox, filedialog

# MOTIVO (hilos/UI): el flujo corre en un hilo del TaskRunner, pero TODOS los
# diálogos y mensajes ocurren en el hilo principal. La vista se pasa por
# parámetro (igual que Datacrédito) para no depender de un self.view compartido
# entre las sub-pestañas ARPESOD/FINANSUEÑOS.
from src.utils.task_runner import get_default_runner
from src.utils.file_utils import backup_file
from src.models.cifin_model import CifinModel
from src.services.centrales.finansueños.cifin_service import FinansuenosDataProcessorService
from src.services.centrales.arpesod.cifin_service import ArpesodDataProcessorService


class CifinController:
    def __init__(self):
        self.model = CifinModel()
        self.view = None
        self.empresa_actual = None
        self.runner = None  # lo asigna la app (TaskRunner)
        self.column_map = {
            'id_number': 'NUMERO DE IDENTIFICACION',
            'id_type': 'tipo_identificacion',
            'full_name': 'nombre_tercero',
            'address': 'direccion_casa',
            'email': 'correo_electronico',
            'phone': 'numero_celular',
            'home_phone': 'telefono_casa',
            'company_phone': 'telefono_empresa',
            'account_number': 'numero_obligacion',
            'initial_value': 'valor_inicial',
            'payment_date': 'fecha_pago',
            'open_date': 'fecha_inicio',
            'due_date': 'fecha_terminacion',
            'city': 'ciudad_casa',
            'department': 'departamento_casa',
            'balance_due': 'valor_saldo',
            'available_value': 'cargo_fijo',
            'monthly_fee': 'valor_cuota',
            'arrears_value': 'valor_mora',
            'arrears_age': 'edad_mora',
            'periodicity': 'periodicidad',
            'actual_value_paid': 'valor_real_pagado'
        }

    def set_empresa_actual(self, empresa_actual):
        """Establece el tipo de empresa para usar el servicio correcto."""
        self.empresa_actual = empresa_actual.lower()

    def set_view(self, view):
        """Compatible con la API antigua; el flujo real pasa la vista por parámetro."""
        self.view = view

    def run_processing(self, view, txt_path, corrections_path):
        """Pide el archivo de salida (main) y procesa en un hilo del TaskRunner.

        MOTIVO: antes los diálogos se abrían dentro del worker (riesgo de
        timeout) y la vista se resolvía por self.view (FINANSUEÑOS siempre).
        Ahora la vista del clic se pasa explícitamente.
        """
        if not self.empresa_actual:
            messagebox.showerror("Error", "No se ha especificado el tipo de empresa")
            view.update_status("Error: Tipo de empresa no especificado")
            return

        runner = getattr(self, "runner", None) or get_default_runner()
        if runner is None:
            self._procesar_y_finalizar_sync(view, txt_path, corrections_path)
            return

        if runner.is_busy("cifin"):
            messagebox.showwarning(
                "Proceso en curso", "Ya hay un proceso de CIFIN ejecutándose. Espera a que termine.")
            return

        output_path = filedialog.asksaveasfilename(
            title="Guardar reporte como",
            filetypes=[("Archivos Excel", "*.xlsx")],
            defaultextension=".xlsx",
            initialfile="Reporte_CIFIN.xlsx",
        )
        if not output_path:
            view.update_status("Proceso cancelado por el usuario.")
            return

        # MOTIVO (seguridad de datos): los servicios actualizan el Excel de
        # correcciones en sitio; respaldarlo antes evita pérdidas.
        backup_file(corrections_path)
        view.update_status("Iniciando proceso CIFIN...")
        view.report_progress(5)

        def worker():
            # El worker NO toca la UI: procesa y guarda el archivo.
            return self._procesar(view, txt_path, corrections_path, output_path)

        runner.submit("cifin", worker,
                      on_done=lambda _r: self._finalizar_ok(view, output_path),
                      on_error=lambda exc: self._finalizar_error(view, exc))

    # ------------------------------------------------------ trabajo (worker)
    def _procesar(self, view, txt_path, corrections_path, output_path):
        """Carga, transforma y guarda. Sin interacción con la interfaz."""
        df_cargado = self.model.load_plano_file(txt_path)
        if df_cargado is None:
            raise ValueError("No se pudo cargar el archivo plano.")

        if self.empresa_actual == "arpesod":
            procesador = ArpesodDataProcessorService(df_cargado, corrections_path, self.column_map)
        elif self.empresa_actual == "finansueños":
            procesador = FinansuenosDataProcessorService(df_cargado, corrections_path, self.column_map)
        else:
            raise ValueError(f"Tipo de empresa no válido: {self.empresa_actual}")

        df_transformado = procesador.run_all_transformations()
        view.report_progress(80)
        self.model.df = df_transformado
        if not self.model.guardar_en_excel(output_path):
            raise ValueError("No se pudo guardar el archivo Excel.")
        view.report_progress(100)
        return True

    # ------------------------------------------------- callbacks (hilo principal)
    def _finalizar_ok(self, view, output_path):
        view.update_status("¡Éxito! Reporte CIFIN guardado.")
        messagebox.showinfo("Éxito", f"El reporte ha sido generado en:\n{output_path}")
        view.update_status("Listo para comenzar.")

    def _finalizar_error(self, view, error):
        view.update_status("Error en el proceso.")
        messagebox.showerror("Error en el Proceso", f"Ocurrió un error:\n{error}")
        view.update_status("Listo para comenzar.")

    def _procesar_y_finalizar_sync(self, view, txt_path, corrections_path):
        """Fallback sin runner: mismo flujo pero síncrono (no usado en la app real)."""
        backup_file(corrections_path)
        try:
            output_path = filedialog.asksaveasfilename(
                title="Guardar reporte como", filetypes=[("Archivos Excel", "*.xlsx")],
                defaultextension=".xlsx", initialfile="Reporte_CIFIN.xlsx")
            if not output_path:
                view.update_status("Proceso cancelado por el usuario.")
                return
            self._procesar(view, txt_path, corrections_path, output_path)
            self._finalizar_ok(view, output_path)
        except Exception as e:
            self._finalizar_error(view, e)
