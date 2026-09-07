from tkinter import filedialog, messagebox

# MOTIVO (hilos): el reporte es pesado; se ejecuta en un hilo del TaskRunner
# sin congelar la UI (los diálogos/mensajes se canalizan al hilo principal).
from src.utils.task_runner import threaded
from src.services.anticipos.anticipos_service import AnticiposService

class AnticiposController:
    def __init__(self,view):
        self.view = view
        self.service = AnticiposService()

    def set_view(self, view):
        self.view = view    
    
    @threaded("anticipos")
    def start_report_generation(self,file_path):
        try:
            # MOTIVO (progreso global): reinicia la barra única al iniciar.
            self.view.update_display("Iniciando proceso...", 0)
            # Define una función para que el servicio actualice la UI
            def status_update_callback(message, progress):
                # La vista principal no tiene 'update_display', verificamos si existe.
                if hasattr(self.view, 'update_display'):
                    self.view.update_display(message, progress)
                elif hasattr(self.view, 'update_status'):
                    self.view.update_status(f"{message} ({progress}%)")

            # 1. Llama al servicio para que haga el trabajo pesado
            final_sheets = self.service.generate_report_data(file_path, status_update_callback)

            output_path = filedialog.asksaveasfilename(
                title="Guardar reporte de Anticipos como...",
                initialfile=self.service.config.output_filename,
                defaultextension=".xlsx"
            )
            if not output_path:
                self.view.update_display("Guardado cancelado.", 0)
                return
            
            # 2. Llama a un método del servicio para guardar el archivo
            self.view.update_display("Guardando archivo formateado...", 95)
            self.service.save_report(output_path, final_sheets,status_update_callback)
            
            messagebox.showinfo("Éxito", f"Reporte generado exitosamente en:\n{output_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error: {str(e)}")
        finally:
            self.view.update_display("Proceso finalizado.", 100)