import threading
import traceback
from tkinter import filedialog, messagebox
from src.views.datacredito_view import DataCreditoView
from src.models.datacredito_model import DataCreditoModel
from src.services.centrales.finansueños.dataprocessor_service import FinansuenosDataProcessorService
from src.services.centrales.arpesod.datacredito_service import ArpesodDataProcessorService

class DataCreditoController:
    def __init__(self):
        self.datacredito_view = None
        self.empresa_actual = None
        self.model = DataCreditoModel()
    
    def set_empresa_actual(self, empresa_actual):
        """Establece el tipo de empresa para usar el servicio correcto"""
        self.empresa_actual = empresa_actual.lower()
    
    def set_view(self, view):
        self.view = view

    def abrir_vista_datacredito(self, parent):
        if self.datacredito_view is None or not self.datacredito_view.top.winfo_exists():
            self.datacredito_view = DataCreditoView(parent, self)
            self.datacredito_view.top.grab_set()
        else:
            self.datacredito_view.top.lift()

    def run_processing_datacredito(self, view, plano_path, correcciones_path):   
        """Pide el archivo de salida e inicia el procesamiento en un hilo."""
        if not self.empresa_actual:
            messagebox.showerror("Error", "No se ha especificado el tipo de empresa")
            view.update_status("Error: Tipo de empresa no especificado")
            return
        
        output_path = filedialog.asksaveasfilename(
            title="Guardar archivo procesado como...",
            defaultextension=".xlsx",
            filetypes=[("Archivos de Excel", "*.xlsx")]
        )
        if not output_path:
            view.update_status("Proceso cancelado por el usuario.")
            return

        thread = threading.Thread(
            target=self._run_processing_thread,
            args=(view, plano_path, correcciones_path, output_path)
        )
        thread.start()

    def _run_processing_thread(self, view, plano_path, correcciones_path, output_path):
        """
        La función que se ejecuta en el hilo. 
        INTEGRA: Carga correcta (Arpesod/Finansueños) + Mapeo de columnas + Guardado ordenado.
        """
        print("DEBUG: --- El hilo ha iniciado correctamente ---", flush=True)
        try:
            view.update_status("Iniciando proceso Datacredito...")
            
            print(f"DEBUG: Cargando archivo plano: {plano_path}", flush=True)
            
            # --- CORRECCIÓN CRÍTICA: Pasar 'self.empresa_actual' ---
            # Esto es necesario para que el modelo sepa usar COLSPECS_ARPESOD
            self.model.load_plano_file(plano_path, self.empresa_actual)
            
            print(f"DEBUG: Archivo cargado. Empresa seleccionada: {self.empresa_actual}", flush=True)
            
            # --- DEFINICIÓN DEL MAPA DE COLUMNAS ---
            column_map = {
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
                'departament':'DEPARTAMENTO DE CORRESPONDENCIA'
            }

            # 2. SELECCIÓN DEL SERVICIO 
            df_crudo = self.model.df 
            processor = None 
            
            if self.empresa_actual == "arpesod":
                print("DEBUG: Intentando inicializar servicio ARPESOD...", flush=True)
                processor = ArpesodDataProcessorService(df_crudo, correcciones_path, column_map)
                print("DEBUG: Servicio ARPESOD inicializado.", flush=True)
                
            elif self.empresa_actual == "finansueños":
                print("DEBUG: Intentando inicializar servicio FINANSUEÑOS...", flush=True)
                processor = FinansuenosDataProcessorService(df_crudo, correcciones_path, column_map)
                print("DEBUG: Servicio FINANSUEÑOS inicializado.", flush=True)
            else:
                raise ValueError(f"Tipo de empresa no válido: {self.empresa_actual}")
            
            # 3. Ejecutar transformaciones
            print("DEBUG: Ejecutando run_all_transformations...", flush=True)
            if processor:
                df_procesado = processor.run_all_transformations()
                print("DEBUG: Transformaciones terminadas.", flush=True)
            else:
                raise ValueError("El procesador no se inicializó correctamente.")

            # 4. Actualizar el modelo con los datos procesados
            self.model.df = df_procesado
            
            # 5. Guardar datos
            print(f"DEBUG: Guardando en {output_path}...", flush=True)
            view.update_status("Datos procesados, guardando archivo...")
            
            # --- IMPORTANTE: Pasar empresa_actual para el reordenamiento de columnas ---
            self.model.save_processed_file(output_path, self.empresa_actual)
            
            print("DEBUG: Proceso finalizado con éxito.", flush=True)
            view.update_status(f"¡Éxito! Archivo guardado.")
            messagebox.showinfo("Proceso Completado", f"El archivo se guardó en:\n{output_path}")

        except Exception as e:
            print("\n" + "!"*50)
            print("ERROR FATAL EN EL HILO:")
            import traceback
            traceback.print_exc() 
            print("!"*50 + "\n", flush=True)
            
            error_message = f"Ocurrió un error interno: {e}"
            view.update_status("Error en el proceso.")
            messagebox.showerror("Error Crítico", error_message)
            
        finally:
            if view:
                view.after(5000, lambda: view.update_status("Listo para comenzar."))