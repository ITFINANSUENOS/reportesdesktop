from tkinter import filedialog, messagebox

# MOTIVO (hilos): el trabajo pesado se ejecuta en un hilo del TaskRunner y la
# UI (diálogos, estado, mensajes) ocurre siempre en el hilo principal.
from src.utils.task_runner import get_default_runner
from src.utils.file_utils import backup_file
from src.models.datacredito_model import DataCreditoModel
from src.services.centrales.finansueños.dataprocessor_service import FinansuenosDataProcessorService
from src.services.centrales.arpesod.datacredito_service import ArpesodDataProcessorService


class DataCreditoController:
    """Controlador de Datacrédito (compartido por ARPESOD y FINANSUEÑOS).

    MOTIVO del guard: como ambas sub-pestañas usan la MISMA instancia
    (controller/modelo), antes se podía lanzar dos procesos a la vez y mezclar
    'empresa_actual'/'df'. El TaskRunner lo impide con una clave única.
    """
    COLUMN_MAP = {
        'id_number': 'NUMERO DE IDENTIFICACION',
        'id_type': 'TIPO DE IDENTIFICACION',
        'full_name': 'NOMBRE COMPLETO',
        'account_number': 'NUMERO DE LA CUENTA U OBLIGACION',
        'initial_value': 'VALOR INICIAL',
        'email': 'CORREO ELECTRONICO',
        'city': 'CIUDAD CORRESPONDENCIA',
        'address': 'DIRECCION DE CORRESPONDENCIA',
        'open_date': 'FECHA APERTURA',
        'due_date': 'FECHA VENCIMIENTO',
        'payment_type': 'FORMA DE PAGO',
        'phone': 'CELULAR',
        'arrears_value': 'VALOR SALDO MORA',
        'responsable': 'RESPONSABLE',
        'novedad': 'NOVEDAD',
        'total_cuotas': 'TOTAL CUOTAS',
        'cuotas_canceladas': 'CUOTAS CANCELADAS',
        'cuotas_mora': 'CUOTAS EN MORA',
        'arrears_age': 'EDAD DE MORA',
        'estado_cuenta': 'ESTADO DE LA CUENTA',
        'fecha_adjetivo': 'FECHA DE ADJETIVO',
        'clausula': 'CLAUSULA DE PERMANENCIA',
        'fecha_clausula': 'FECHA CLAUSULA DE PERMANENCIA',
        'monthly_fee': 'V CUOTA MENSUAL',
        'departament': 'DEPARTAMENTO DE CORRESPONDENCIA',
    }

    def __init__(self):
        self.empresa_actual = None
        self.model = DataCreditoModel()
        self.view = None
        self.runner = None  # lo asigna la app (TaskRunner)

    def set_empresa_actual(self, empresa_actual):
        """Establece el tipo de empresa para usar el servicio correcto."""
        self.empresa_actual = empresa_actual.lower()

    def set_view(self, view):
        self.view = view

    def run_processing_datacredito(self, view, plano_path, correcciones_path):
        """Pide el archivo de salida y procesa en un hilo gestionado.

        MOTIVO: antes este método lanzaba su propio Thread que tocaba Tk
        (status, messagebox y view.after desde el hilo). Ahora el diálogo se pide
        aquí (hilo principal) y el trabajo lo ejecuta el TaskRunner.
        """
        if not self.empresa_actual:
            messagebox.showerror("Error", "No se ha especificado el tipo de empresa")
            view.update_status("Error: Tipo de empresa no especificado")
            return

        runner = getattr(self, "runner", None) or get_default_runner()
        if runner is None:
            # Sin runner (tests/preview): se ejecuta de forma síncrona.
            self._procesar(view, plano_path, correcciones_path, None)
            return

        if runner.is_busy("datacredito"):
            messagebox.showwarning(
                "Proceso en curso",
                "Ya hay un proceso de Datacrédito ejecutándose. Espera a que termine.")
            return

        output_path = filedialog.asksaveasfilename(
            title="Guardar archivo procesado como...",
            defaultextension=".xlsx",
            filetypes=[("Archivos de Excel", "*.xlsx")],
        )
        if not output_path:
            view.update_status("Proceso cancelado por el usuario.")
            return

        # MOTIVO (seguridad de datos): los servicios centrales actualizan el
        # Excel de correcciones EN SITIO; respaldarlo antes evita pérdidas.
        backup_file(correcciones_path)

        view.update_status("Iniciando proceso Datacredito...")
        view.report_progress(5)

        # El worker NO toca Tk: procesa, guarda el archivo y devuelve el estado.
        def worker():
            return self._procesar(view, plano_path, correcciones_path, output_path)

        runner.submit("datacredito", worker,
                      on_done=lambda _r: self._finalizar_ok(view, output_path),
                      on_error=lambda exc: self._finalizar_error(view, exc))

    # ------------------------------------------- trabajo pesado (worker)
    def _procesar(self, view, plano_path, correcciones_path, output_path):
        """
        Ejecuta la carga (ARPESOD/FINANSUEÑOS), el mapeo de columnas, las
        transformaciones y el guardado. No interactúa con la interfaz.
        """
        # Cargar el plano con el modelo (usa COLSPECS según la empresa).
        self.model.load_plano_file(plano_path, self.empresa_actual)
        df_crudo = self.model.df

        if self.empresa_actual == "arpesod":
            processor = ArpesodDataProcessorService(df_crudo, correcciones_path, self.COLUMN_MAP)
        elif self.empresa_actual == "finansueños":
            processor = FinansuenosDataProcessorService(df_crudo, correcciones_path, self.COLUMN_MAP)
        else:
            raise ValueError(f"Tipo de empresa no válido: {self.empresa_actual}")

        df_procesado = processor.run_all_transformations()
        self.model.df = df_procesado

        if output_path:
            self.model.save_processed_file(output_path, self.empresa_actual)

        view.update_status("Datos procesados, guardando archivo...")
        view.report_progress(85)
        return True

    # ------------------------------------------- callbacks (hilo principal)
    def _finalizar_ok(self, view, output_path):
        view.report_progress(100)
        view.update_status("¡Éxito! Archivo guardado.")
        messagebox.showinfo("Proceso Completado", f"El archivo se guardó en:\n{output_path}")
        view.update_status("Listo para comenzar.")

    def _finalizar_error(self, view, error):
        view.report_progress(0)
        view.update_status("Error en el proceso.")
        messagebox.showerror("Error Crítico", f"Ocurrió un error interno: {error}")
        view.update_status("Listo para comenzar.")
