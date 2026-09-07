from tkinter import messagebox, filedialog

# MOTIVO (hilos): el procesamiento es pesado y no debe congelar la UI; se
# ejecuta en un hilo del TaskRunner (los diálogos/mensajes van al hilo principal).
from src.utils.task_runner import threaded
from src.utils.file_utils import backup_file
from src.models.cifin_model import CifinModel
from src.services.centrales.finansueños.cifin_service import FinansuenosDataProcessorService
from src.services.centrales.arpesod.cifin_service import ArpesodDataProcessorService

class CifinController:
    # MOTIVO: se eliminó el import de CifinView (vista huérfana que nadie abría).
    # El flujo real de CIFIN ocurre desde la pestaña "Centrales de Riesgo".
    def __init__(self):
        self.model = CifinModel()
        self.view = None
        self.empresa_actual = None
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
            'actual_value_paid':'valor_real_pagado'
        }
        
    def set_empresa_actual(self, empresa_actual ):
        """Establece el tipo de empresa para usar el servicio correcto"""
        self.empresa_actual = empresa_actual.lower()
    

    def set_view(self, view):
        """
        Guarda una referencia a la vista para que el controlador 
        pueda comunicarse con ella (ej. para actualizar un mensaje de estado).
        """
        self.view = view    

    def _report_progress(self, percent):
        """Envía el avance a la barra única del pie (vía la vista de centrales)."""
        view = getattr(self, "view", None)
        if view is not None and hasattr(view, "report_progress"):
            view.report_progress(percent)

    @threaded("cifin")
    def run_processing(self, txt_path, corrections_path):
        """
        Método para procesar los archivos sin necesidad de una vista específica
        """
        # MOTIVO (seguridad de datos): los servicios de centrales actualizan el
        # Excel de correcciones en sitio; respaldarlo antes evita pérdidas.
        backup_file(corrections_path)
        self._report_progress(5)

        try:
            # 1. Cargar archivo plano
            df_cargado = self.model.load_plano_file(txt_path)
            if df_cargado is None:
                raise ValueError("No se pudo cargar el archivo plano.")
            
            # 2. Crear el servicio específico según la empresa
            if self.empresa_actual == "arpesod":
                procesador = ArpesodDataProcessorService(df_cargado, corrections_path, self.column_map)
            elif self.empresa_actual == "finansueños":
                procesador = FinansuenosDataProcessorService(df_cargado, corrections_path, self.column_map)
            else:
                raise ValueError(f"Tipo de empresa no válido: {self.empresa_actual}")
            
            # 3. Ejecutar transformaciones
            df_transformado = procesador.run_all_transformations()
            self._report_progress(80)

            # 4. Guardar el resultado
            output_path = filedialog.asksaveasfilename(
                title="Guardar reporte como",
                filetypes=[("Archivos Excel", "*.xlsx")],
                defaultextension=".xlsx"
            )

            if output_path:
                self.model.df = df_transformado
                if self.model.guardar_en_excel(output_path):
                    self._report_progress(100)
                    messagebox.showinfo("Éxito", f"El reporte ha sido generado en:\n{output_path}")
                else:
                    raise ValueError("No se pudo guardar el archivo Excel.")
            else:
                self._report_progress(0)
                messagebox.showinfo("Información", "Guardado cancelado por el usuario.")

        except Exception as e:
            self._report_progress(0)
            messagebox.showerror("Error en el Proceso", f"Ocurrió un error:\n{e}")
