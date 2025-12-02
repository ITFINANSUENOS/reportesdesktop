from tkinter import messagebox, filedialog
from src.models.cifin_model import CifinModel
from src.views.cifin_view import CifinView
from src.services.centrales.finansueños.cifin_service import FinansuenosDataProcessorService
from src.services.centrales.arpesod.cifin_service import ArpesodDataProcessorService

class CifinController:
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

    def open_cifin_window(self, parent):
        if self.view is None or not self.view.top.winfo_exists():
            self.view = CifinView(parent, self)
            # Llama a grab_set() sobre .top
            self.view.top.grab_set()
        else:
            # Llama a lift() sobre .top
            self.view.top.lift()
            
    def run_processing(self, txt_path, corrections_path):
        """
        Método para procesar los archivos sin necesidad de una vista específica
        """
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
            
            # 4. Guardar el resultado
            output_path = filedialog.asksaveasfilename(
                title="Guardar reporte como",
                filetypes=[("Archivos Excel", "*.xlsx")],
                defaultextension=".xlsx"
            )

            if output_path:
                self.model.df = df_transformado
                if self.model.guardar_en_excel(output_path):
                    messagebox.showinfo("Éxito", f"El reporte ha sido generado en:\n{output_path}")
                else:
                    raise ValueError("No se pudo guardar el archivo Excel.")
            else:
                messagebox.showinfo("Información", "Guardado cancelado por el usuario.")

        except Exception as e:
            messagebox.showerror("Error en el Proceso", f"Ocurrió un error:\n{e}")
